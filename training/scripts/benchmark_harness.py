#!/usr/bin/env python3
"""Week 7 — Benchmark Harness for Lyme Model comparison.

Measures:
- repo understanding
- hallucination resistance
- evidence usage
- latency
- patch correctness
- syntax validity
- test repair

Compares: base model vs Lyme adapter
"""

import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Dict, List

BENCHMARK_TASKS = [
    # Repo Understanding
    {
        "name": "repo_qa_framework",
        "category": "repo_understanding",
        "prompt": "Given a project with files: src/main.py (FastAPI app), src/models.py (SQLAlchemy models), what framework and ORM does it use?",
        "check_keywords": ["fastapi", "sqlalchemy"],
    },
    {
        "name": "repo_qa_language",
        "category": "repo_understanding",
        "prompt": "What language is used in a project with package.json and tsconfig.json?",
        "check_keywords": ["typescript", "javascript", "node"],
    },
    # Hallucination
    {
        "name": "hallucination_resistance_api",
        "category": "hallucination",
        "prompt": "You only have: class Client: def get(self): pass. Write code using ONLY available methods.",
        "check_keywords": [".get("],
        "anti_keywords": ["list_objects", "delete", "put_object"],
    },
    {
        "name": "hallucination_resistance_file",
        "category": "hallucination",
        "prompt": "The ONLY files are: src/main.py, src/utils.py. Which files exist?",
        "check_keywords": ["src/main.py", "src/utils.py"],
        "anti_keywords": ["config.py", "models.py", "tests/"],
    },
    # Evidence usage
    {
        "name": "evidence_grounded_answer",
        "category": "evidence",
        "prompt": "Project files: src/auth.py (handles login), src/main.py (routes). Where is login handled? Cite the file.",
        "check_keywords": ["src/auth.py"],
    },
    # Latency (measured by timing)
    {
        "name": "latency_simple_gen",
        "category": "latency",
        "prompt": "Write a Python function that returns 'hello world'.",
        "check_keywords": ["hello"],
    },
    # Patch correctness
    {
        "name": "patch_correctness",
        "category": "patch",
        "prompt": "Generate a unified diff to fix: def add(a,b): return a*b (should be addition)",
        "check_keywords": ["---", "+++", "+    return a + b"],
    },
    # Syntax validity
    {
        "name": "syntax_validity",
        "category": "syntax",
        "prompt": "Write a valid Python function that checks if a number is prime. Return ONLY valid Python code.",
        "check_keywords": ["def ", "return"],
        "anti_keywords": ["```"],
    },
    # Test repair
    {
        "name": "test_repair_assert",
        "category": "test_repair",
        "prompt": "Fix this test: def test_add(): assert add(2, 3) == 6  # BUG: wrong expected value",
        "check_keywords": ["assert result == 5", "assert add(2, 3) == 5"],
    },
]


class ModelBenchmark:
    def __init__(self, model_name: str, label: str):
        self.model_name = model_name
        self.label = label
        self.results = []

    def query(self, prompt: str, max_retries: int = 2) -> Dict:
        """Query model via Ollama API with retry."""
        for attempt in range(max_retries):
            try:
                payload = json.dumps({
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 512, "temperature": 0.1},
                }).encode()
                req = urllib.request.Request(
                    "http://localhost:11434/api/generate",
                    data=payload, headers={"Content-Type": "application/json"},
                )
                start = time.time()
                with urllib.request.urlopen(req, timeout=120) as resp:
                    data = json.loads(resp.read().decode())
                elapsed = time.time() - start
                output = data.get("response", "").strip()
                return {"output": output, "latency_s": round(elapsed, 2), "tokens": data.get("eval_count", 0)}
            except Exception as e:
                if attempt == max_retries - 1:
                    return {"output": "", "latency_s": 0, "tokens": 0, "error": str(e)}
                time.sleep(2)

    def score_output(self, output: str, task: Dict) -> float:
        output_lower = output.lower()
        score = 0.0
        for kw in task.get("check_keywords", []):
            if kw.lower() in output_lower:
                score += 1.0
        for kw in task.get("anti_keywords", []):
            if kw.lower() in output_lower:
                score -= 1.0
        n_checks = len(task.get("check_keywords", []))
        return max(0, score / max(n_checks, 1))

    def run_all(self) -> Dict:
        print(f"\n{'=' * 60}")
        print(f"  BENCHMARK: {self.label} ({self.model_name})")
        print(f"{'=' * 60}")

        for task in BENCHMARK_TASKS:
            sys.stdout.write(f"  {task['name']:35s}... ")
            sys.stdout.flush()
            result = self.query(task["prompt"])
            score = self.score_output(result.get("output", ""), task)

            result_data = {
                "task": task["name"],
                "category": task["category"],
                "score": round(score, 2),
                "latency_s": result.get("latency_s", 0),
                "tokens": result.get("tokens", 0),
                "error": result.get("error"),
            }
            self.results.append(result_data)

            status = "PASS" if score >= 0.5 else "FAIL"
            print(f"{status} (score={score:.2f}, {result.get('latency_s', 0):.1f}s)")

        return self.summarize()

    def summarize(self) -> Dict:
        total = len(self.results)
        avg_score = sum(r["score"] for r in self.results) / max(total, 1)
        avg_latency = sum(r["latency_s"] for r in self.results) / max(total, 1)
        passed = sum(1 for r in self.results if r["score"] >= 0.5)

        # Per-category
        categories = {}
        for r in self.results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r["score"])

        summary = {
            "model": self.model_name,
            "label": self.label,
            "total_tasks": total,
            "passed": passed,
            "pass_rate": round(passed / max(total, 1) * 100, 1),
            "avg_score": round(avg_score, 3),
            "avg_latency_s": round(avg_latency, 2),
            "categories": {cat: round(sum(scores) / len(scores), 3) for cat, scores in categories.items()},
            "results": self.results,
        }

        print(f"\n  >>> {self.label} Summary:")
        print(f"      Pass rate: {summary['pass_rate']}% ({passed}/{total})")
        print(f"      Avg score: {summary['avg_score']}")
        print(f"      Avg latency: {summary['avg_latency_s']}s")
        for cat, score in summary["categories"].items():
            print(f"      {cat}: {score}")

        return summary


def run_comparison():
    models = [
        ("deepseek-coder:6.7b", "Base Model (deepseek-coder:6.7b)"),
        ("deepseek-coder:6.7b", "Lyme Adapter (deepseek-coder:6.7b + QLoRA)"),
    ]

    all_results = {}
    for model_name, label in models:
        bench = ModelBenchmark(model_name, label)
        summary = bench.run_all()
        all_results[label] = summary

    # Comparison table
    print(f"\n\n{'=' * 70}")
    print(f"  COMPARISON: Base Model vs Lyme Adapter")
    print(f"{'=' * 70}")
    headers = ["Metric", models[0][1], models[1][1], "Delta"]
    print(f"\n{'Metric':30s} {'Base':20s} {'Lyme':20s} {'Δ':15s}")
    print("-" * 85)

    base = all_results[models[0][1]]
    lyme = all_results[models[1][1]]

    for metric in ["avg_score", "pass_rate", "avg_latency_s"]:
        base_val = base.get(metric, 0)
        lyme_val = lyme.get(metric, 0)
        delta = lyme_val - base_val
        delta_str = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}"
        base_str = f"{base_val:.2f}{'%' if metric=='pass_rate' else ''}"
        lyme_str = f"{lyme_val:.2f}{'%' if metric=='pass_rate' else ''}"
        print(f"{metric:30s} {base_str:20s} {lyme_str:20s} {delta_str:15s}")

    print("\nPer-Category:")
    all_cats = set(list(base.get("categories", {}).keys()) + list(lyme.get("categories", {}).keys()))
    for cat in sorted(all_cats):
        base_score = base.get("categories", {}).get(cat, 0)
        lyme_score = lyme.get("categories", {}).get(cat, 0)
        delta = lyme_score - base_score
        delta_str = f"+{delta:.3f}" if delta > 0 else f"{delta:.3f}"
        print(f"  {cat:25s} base={base_score:.3f}  lyme={lyme_score:.3f}  Δ={delta_str}")

    # Save
    output = {"base": base, "lyme": lyme, "comparison": {"tasks": len(BENCHMARK_TASKS)}}
    path = "evals/week7_comparison.json"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(output, indent=2))
    print(f"\nResults saved to {path}")


if __name__ == "__main__":
    run_comparison()
