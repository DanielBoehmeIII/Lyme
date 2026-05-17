"""Week 1 — Base Model Benchmark

Measures candidate coding models on:
- VRAM usage
- Inference speed (tokens/sec)
- Coding quality (Q&A, bug finding, code gen, test repair)
- Context handling
- Local usability

Output: base-model comparison table and selection recommendation.
"""

import sys
import time
import json
import subprocess
import re
from pathlib import Path
from typing import Optional, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

CANDIDATE_MODELS = [
    "qwen2.5-coder:7b",
    "qwen2.5-coder:14b",
    "deepseek-coder:6.7b",
    "starcoder2:7b",
    "codellama:7b",
    "codellama:7b-code",
    "phi3:mini",
]

# Quality benchmark tasks
QUALITY_TASKS = [
    {
        "name": "repo-qa",
        "category": "repo_understanding",
        "prompt": (
            "I have a Python project with these files:\n"
            "- src/main.py (FastAPI app with /users and /items endpoints)\n"
            "- src/models.py (User and Item SQLAlchemy models)\n"
            "- src/database.py (DB connection and session)\n"
            "- tests/test_api.py (pytest test cases)\n\n"
            "Questions:\n"
            "1. What framework is used for the API?\n"
            "2. What database ORM is used?\n"
            "3. How many models are defined?\n"
            "4. What testing framework is used?\n\n"
            "Answer concisely."
        ),
        "checks": [
            ("fastapi", 1.0),
            ("sqlalchemy", 1.0),
            ("2", 0.5),
            ("pytest", 1.0),
        ],
    },
    {
        "name": "bug-finding",
        "category": "bug_detection",
        "prompt": (
            "Find all bugs in this Python code:\n\n"
            "```python\n"
            "def calculate_average(numbers):\n"
            "    total = sum(numbers)\n"
            "    return total / len(numbers)\n\n"
            "def get_user(user_id, db):\n"
            "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
            "    return db.execute(query)\n\n"
            "def save_data(data, filename):\n"
            "    f = open(filename, 'w')\n"
            "    f.write(json.dumps(data))\n"
            "    return True\n"
            "```\n\n"
            "List each bug with its line and explanation."
        ),
        "checks": [
            ("zero", 0.7),
            ("division by zero", 1.0),
            ("sql injection", 1.0),
            ("file", 0.5),
            ("close", 0.7),
        ],
    },
    {
        "name": "code-generation",
        "category": "code_generation",
        "prompt": (
            "Write a Python function called `merge_sorted` that merges two sorted lists into one sorted list. "
            "Include type hints and a docstring. Return ONLY the code."
        ),
        "checks": [
            ("def merge_sorted", 1.0),
            ("->", 0.5),
            ("List", 0.3),
            ("type hint", 0.3),
        ],
    },
    {
        "name": "test-repair",
        "category": "testing",
        "prompt": (
            "This test has bugs. Fix it:\n\n"
            "```python\n"
            "from calculator import add, divide\n\n"
            "def test_add():\n"
            "    result = add(2, 3)\n"
            "    assert result == 6  # BUG\n\n"
            "def test_divide():\n"
            "    result = divide(10, 0)  # BUG\n"
            "    assert result == 2\n"
            "```\n\n"
            "Return the corrected test code."
        ),
        "checks": [
            ("assert result == 5", 1.0),
            ("zero", 0.5),
            ("divide", 0.3),
        ],
    },
    {
        "name": "hallucination-resistance",
        "category": "hallucination",
        "prompt": (
            "This is the only API available:\n\n"
            "```python\n"
            "class CloudClient:\n"
            "    def list_buckets(self):\n"
            "        return ['bucket1', 'bucket2']\n"
            "    def get_object(self, bucket, key):\n"
            "        return {'data': 'content'}\n"
            "```\n\n"
            "Write code to list all buckets and download all objects. "
            "Only use methods that actually exist."
        ),
        "checks": [
            ("list_buckets", 1.0),
            ("get_object", 1.0),
            ("list_objects", -1.0),
        ],
    },
    {
        "name": "multi-file-reasoning",
        "category": "reasoning",
        "prompt": (
            "Three files in a project:\n\n"
            "FILE auth.py imports User from models. User has hardcoded password check.\n"
            "routes.py calls auth.login with user input.\n\n"
            "Identify all security issues. Be specific."
        ),
        "checks": [
            ("hardcoded", 1.0),
            ("password", 0.5),
            ("security", 0.5),
            ("plain", 0.5),
        ],
    },
    {
        "name": "unified-diff",
        "category": "patch_generation",
        "prompt": (
            "Generate a unified diff to fix this bug:\n\n"
            "Current code:\n"
            "```python\n"
            "def get_user(user_id, db):\n"
            "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
            "    return db.execute(query)\n"
            "```\n\n"
            "Fix: Use parameterized query instead of string concatenation.\n\n"
            "Output ONLY a valid unified diff."
        ),
        "checks": [
            ("---", 0.5),
            ("+++", 0.5),
            ("@", 0.3),
            ("paramet", 0.5),
            ("? ", -0.5),
        ],
    },
    {
        "name": "tool-use",
        "category": "tool_use",
        "prompt": (
            "You have these tools:\n"
            "- read_file(path): read a file\n"
            "- grep_search(pattern): search code\n"
            "- edit_file(path, old, new): edit a file\n\n"
            "You need to find where 'SECRET_KEY' is defined and change it.\n"
            "Show the sequence of tool calls you would make."
        ),
        "checks": [
            ("grep_search", 1.0),
            ("SECRET_KEY", 0.7),
            ("read_file", 0.5),
            ("edit_file", 0.5),
        ],
    },
]


def get_gpu_memory_usage() -> Dict:
    """Get current GPU memory usage via nvidia-smi."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi", "--query-gpu=index,name,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True, text=True, timeout=10,
        )
        lines = result.stdout.strip().split("\n")
        gpus = []
        for line in lines:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 5:
                gpus.append({
                    "index": int(parts[0]),
                    "name": parts[1],
                    "memory_total_mb": int(parts[2]),
                    "memory_used_mb": int(parts[3]),
                    "memory_free_mb": int(parts[4]),
                })
        return {"gpus": gpus}
    except Exception as e:
        return {"error": str(e)}


def measure_vram_with_model(model_name: str) -> Dict:
    """Measure VRAM usage when a model is loaded in Ollama."""
    baseline = get_gpu_memory_usage()

    # Ensure model is loaded by sending a small prompt
    try:
        proc = subprocess.run(
            ["ollama", "run", model_name, "say 'hello' and nothing else"],
            capture_output=True, text=True, timeout=120,
        )
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass

    time.sleep(2)
    loaded = get_gpu_memory_usage()
    vram_info = {}
    if "gpus" in baseline and "gpus" in loaded:
        for bg, lg in zip(baseline["gpus"], loaded["gpus"]):
            if bg["index"] == lg["index"]:
                vram_info = {
                    "baseline_used_mb": bg["memory_used_mb"],
                    "loaded_used_mb": lg["memory_used_mb"],
                    "vram_delta_mb": lg["memory_used_mb"] - bg["memory_used_mb"],
                    "total_mb": bg["memory_total_mb"],
                }
    return vram_info


def measure_inference_speed(model_name: str) -> Dict:
    """Measure prompt processing and generation speed via Ollama API."""
    import urllib.request

    prompts = [
        "Write a Python function to reverse a string.",
        "Explain what a decorator is in Python.",
        "Write a fastapi endpoint that returns a list of users.",
    ]

    total_prompt_tokens = 0
    total_gen_tokens = 0
    total_time = 0.0
    results = []

    for prompt in prompts:
        try:
            payload = json.dumps({
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 256, "temperature": 0.2},
            }).encode()

            req = urllib.request.Request(
                "http://localhost:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )

            start = time.time()
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read().decode()
                data = json.loads(body)
            elapsed = time.time() - start

            eval_count = data.get("eval_count", 0)
            prompt_eval_count = data.get("prompt_eval_count", 0)
            total_prompt_tokens += prompt_eval_count
            total_gen_tokens += eval_count
            total_time += elapsed

            results.append({
                "prompt_tokens": prompt_eval_count,
                "generated_tokens": eval_count,
                "time_s": round(elapsed, 2),
                "tok_s": round(eval_count / elapsed, 1) if elapsed > 0 else 0,
            })

        except Exception as e:
            results.append({"error": str(e)})

    avg_tok_s = round(total_gen_tokens / total_time, 1) if total_time > 0 else 0
    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_generated_tokens": total_gen_tokens,
        "total_time_s": round(total_time, 2),
        "avg_tokens_per_second": avg_tok_s,
        "results": results,
    }


def score_output(output: str, checks: List) -> float:
    """Score model output against weighted checks."""
    score = 0.0
    max_score = 0.0
    output_lower = output.lower()

    for keyword, weight in checks:
        if weight < 0:
            if keyword in output_lower:
                score += weight
        max_score += abs(weight) if weight > 0 else 0
        if weight > 0 and keyword in output_lower:
            score += weight

    return score / max_score if max_score > 0 else 0.0


def run_quality_task(model_name: str, task: Dict) -> Dict:
    """Run a single quality task against a model."""
    try:
        proc = subprocess.run(
            ["ollama", "run", model_name, task["prompt"]],
            capture_output=True, text=True, timeout=120,
        )
        elapsed = proc.returncode
        output = proc.stdout.strip()
        score = score_output(output, task["checks"])
        return {
            "task": task["name"],
            "category": task["category"],
            "score": round(score, 3),
            "time_s": 0,
            "output_length": len(output),
        }
    except subprocess.TimeoutExpired:
        return {"task": task["name"], "category": task["category"], "score": 0.0, "time_s": 120, "output_length": 0, "error": "timeout"}
    except Exception as e:
        return {"task": task["name"], "category": task["category"], "score": 0.0, "time_s": 0, "output_length": 0, "error": str(e)}


def benchmark_all():
    results = {}

    for model_name in CANDIDATE_MODELS:
        print(f"\n{'=' * 70}")
        print(f"BENCHMARKING: {model_name}")
        print(f"{'=' * 70}")

        # 1. VRAM measurement
        print(f"\n  [1/4] Measuring VRAM usage...")
        vram = measure_vram_with_model(model_name)

        # 2. Inference speed
        print(f"  [2/4] Measuring inference speed...")
        speed = measure_inference_speed(model_name)

        # 3. Quality tasks
        print(f"  [3/4] Running {len(QUALITY_TASKS)} quality tasks...")
        quality_results = []
        for task in QUALITY_TASKS:
            sys.stdout.write(f"    {task['name']}... ")
            sys.stdout.flush()
            result = run_quality_task(model_name, task)
            quality_results.append(result)
            print(f"score={result['score']:.2f}")

        # 4. Compile results
        avg_quality = (
            sum(r["score"] for r in quality_results) / len(quality_results)
            if quality_results else 0
        )
        model_size_bytes = vram.get("vram_delta_mb", 0)
        model_size_gb = round(model_size_bytes / 1024, 1) if model_size_bytes else 0

        results[model_name] = {
            "vram": vram,
            "speed": speed,
            "quality": {
                "tasks": quality_results,
                "avg_score": round(avg_quality, 3),
            },
        }

        print(f"\n  >>> Summary for {model_name}:")
        print(f"      VRAM delta: {vram.get('vram_delta_mb', 'N/A')} MB")
        print(f"      Speed: {speed.get('avg_tokens_per_second', 'N/A')} tok/s")
        print(f"      Quality: {avg_quality:.2f}")

    return results


def print_comparison_table(results: Dict):
    """Print a formatted comparison table."""
    print(f"\n\n{'=' * 90}")
    print("  BASE MODEL COMPARISON TABLE")
    print(f"{'=' * 90}")

    header = f"{'Model':28s} {'Size':8s} {'Speed':8s} {'Quality':8s} {'VRAM Δ':10s} {'Reliability':12s}"
    print(f"\n{header}")
    print("-" * 90)

    sorted_models = sorted(
        results.keys(),
        key=lambda m: results[m]["quality"]["avg_score"],
        reverse=True,
    )

    for model_name in sorted_models:
        r = results[model_name]
        vram_delta = r.get("vram", {}).get("vram_delta_mb", 0)
        vram_str = f"{vram_delta}MB" if vram_delta else "N/A"
        speed = r.get("speed", {}).get("avg_tokens_per_second", 0)
        speed_str = f"{speed:.1f}t/s" if speed else "N/A"
        quality = r.get("quality", {}).get("avg_score", 0)
        quality_str = f"{quality:.2f}"

        # Model size from Ollama
        model_size_str = "?"

        reliability = "HIGH" if quality >= 0.6 else ("MEDIUM" if quality >= 0.4 else "LOW")

        print(
            f"{model_name:28s} {model_size_str:8s} {speed_str:8s} {quality_str:8s} {vram_str:10s} {reliability:12s}"
        )

    print("-" * 90)
    print(f"\n{'=' * 90}")


def generate_recommendation(results: Dict) -> str:
    """Generate primary/fallback model recommendation based on benchmarks."""
    scored = []
    for model_name, r in results.items():
        quality = r.get("quality", {}).get("avg_score", 0)
        speed = r.get("speed", {}).get("avg_tokens_per_second", 0)
        vram = r.get("vram", {}).get("vram_delta_mb", 0)
        # Composite score: quality weighted highest, speed second, vram efficiency third
        composite = (quality * 0.6) + (min(speed / 30, 1.0) * 0.25) + (max(0, 1 - vram / 8192) * 0.15)
        scored.append((model_name, composite, quality, speed, vram))

    scored.sort(key=lambda x: x[1], reverse=True)
    primary = scored[0]
    fallback = scored[1] if len(scored) > 1 else None

    lines = []
    lines.append(f"\n{'=' * 90}")
    lines.append("  BASE MODEL SELECTION RECOMMENDATION")
    lines.append(f"{'=' * 90}")
    lines.append("")
    lines.append(f"  PRIMARY:   {primary[0]}")
    lines.append(f"             Composite Score: {primary[1]:.3f}")
    lines.append(f"             Quality: {primary[2]:.3f}, Speed: {primary[3]:.1f} tok/s, VRAM: {primary[4]} MB")
    if fallback:
        lines.append("")
        lines.append(f"  FALLBACK:  {fallback[0]}")
        lines.append(f"             Composite Score: {fallback[1]:.3f}")
        lines.append(f"             Quality: {fallback[2]:.3f}, Speed: {fallback[3]:.1f} tok/s, VRAM: {fallback[4]} MB")

    lines.append("")
    lines.append(f"  Full ranking:")
    for i, (m, comp, q, s, v) in enumerate(scored, 1):
        lines.append(f"    {i}. {m:28s} (composite={comp:.3f}, quality={q:.3f}, speed={s:.1f}t/s, vram={v}MB)")
    lines.append("")
    lines.append(f"{'=' * 90}")

    return "\n".join(lines)


def save_results(results: Dict, output_path: str = "lyme-output/week1_base_model_comparison.json"):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)

    # Also save a human-readable summary
    summary_path = output_path.replace(".json", "_summary.md")
    with open(summary_path, "w") as f:
        f.write("# Week 1 — Base Model Comparison\n\n")
        f.write("| Model | Quality | Speed (t/s) | VRAM (MB) |\n")
        f.write("|-------|---------|-------------|-----------|\n")
        for model_name in sorted(results.keys(), key=lambda m: results[m]["quality"]["avg_score"], reverse=True):
            r = results[model_name]
            q = r.get("quality", {}).get("avg_score", 0)
            s = r.get("speed", {}).get("avg_tokens_per_second", 0)
            v = r.get("vram", {}).get("vram_delta_mb", 0)
            f.write(f"| {model_name} | {q:.3f} | {s:.1f} | {v} |\n")

    print(f"\nResults saved to {output_path}")
    print(f"Summary saved to {summary_path}")


if __name__ == "__main__":
    print("=" * 70)
    print("  LYME MODEL — WEEK 1: BASE MODEL BENCHMARK")
    print("=" * 70)
    print(f"\nCandidates: {', '.join(CANDIDATE_MODELS)}")
    print(f"Tasks: {len(QUALITY_TASKS)} quality benchmarks")
    print()

    results = benchmark_all()
    print_comparison_table(results)
    recommendation = generate_recommendation(results)
    print(recommendation)
    save_results(results)
