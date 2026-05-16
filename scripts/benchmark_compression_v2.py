"""WEEK 58: Context Compression for Small Models.

Compares three context strategies on a larger codebase:
1. Raw context (full file contents)
2. Current Lyme compression (structured JSON output)
3. New small-model compression (natural language packets)
"""

import sys, time, json, subprocess, tempfile, os, textwrap
from pathlib import Path
sys.path.insert(0, "src")

from lyme.compression.codebase_compressor import CodebaseCompressor
from lyme_model.amplify.assembler import SmallModelContextAssembler
from lyme_model.amplify.integration import AmplificationLayer

# A medium-sized test project (~15 files) to stress compression
TEST_FILES = {}
for i in range(15):
    TEST_FILES[f"module_{i:02d}.py"] = f'''
"""Module {i} in the test project."""
from typing import Optional, List
import json
import os

class Service{i}:
    """Service class for domain {i}."""
    def __init__(self, config: dict = None):
        self.config = config or {{}}
        self.data = {{}}
    
    def process(self, item: dict) -> dict:
        """Process an item through domain {i} logic."""
        result = {{"id": item.get("id"), "domain": {i}, "status": "processed"}}
        if "value" in item:
            result["computed"] = item["value"] * {i + 1}
        return result
    
    def validate(self, item: dict) -> bool:
        """Validate item for domain {i}."""
        return "id" in item and "value" in item

class Repository{i}:
    """Data access for domain {i}."""
    def __init__(self, connection: str = "default"):
        self.connection = connection
    
    def find(self, item_id: str) -> Optional[dict]:
        return self.data.get(item_id)
    
    def save(self, item: dict) -> bool:
        self.data[item["id"]] = item
        return True

def create_{i}(config: dict) -> Service{i}:
    """Factory for domain {i} service."""
    return Service{i}(config)
'''

# Main app file that uses all modules
TEST_FILES["app.py"] = """
from typing import List, Optional
from module_00 import Service0, Repository0
from module_01 import Service1, Repository1
from module_02 import Service2, Repository2
from module_03 import Service3, Repository3
from module_04 import Service4, Repository4
from module_05 import Service5, Repository5

class Application:
    def __init__(self):
        self.services = {}
        self.repos = {}
    
    def initialize(self):
        for i in range(6):
            svc_class = eval(f"Service{i}")
            repo_class = eval(f"Repository{i}")
            self.services[i] = svc_class()
            self.repos[i] = repo_class()
    
    def process_all(self, items: List[dict]) -> List[dict]:
        results = []
        for item in items:
            domain = hash(item.get("id", "")) % 6
            svc = self.services[domain]
            if svc.validate(item):
                result = svc.process(item)
                self.repos[domain].save(item)
                results.append(result)
        return results

def main():
    app = Application()
    app.initialize()
    items = [{"id": f"item_{i}", "value": i} for i in range(10)]
    results = app.process_all(items)
    print(f"Processed {len(results)} items")

if __name__ == "__main__":
    main()
"""

# Test files
TEST_FILES["test_app.py"] = """
from app import Application

def test_initialize():
    app = Application()
    app.initialize()
    assert len(app.services) == 6

def test_process_all():
    app = Application()
    app.initialize()
    items = [{"id": "test_1", "value": 5}]
    results = app.process_all(items)
    assert len(results) == 1
    assert results[0]["status"] == "processed"
"""

# Config
TEST_FILES["config.yaml"] = """
app:
  name: test-project
  version: 1.0.0
  services: 6
database:
  connection: default
  pool_size: 10
"""

TASKS = [
    {
        "name": "architecture",
        "question": "Describe the architecture of this project. What are the main components and how do they interact?",
        "keywords": ["Service", "Repository", "Application", "module", "domain", "factory", "process"],
    },
    {
        "name": "change-impact",
        "question": "If I want to add a new module_06 with Service6 and Repository6, what files need to change and what code needs to be added?",
        "keywords": ["app", "Application", "process_all", "services", "repos", "module_06", "import"],
    },
    {
        "name": "bug-finding",
        "question": "Find potential issues in this codebase. Look for error handling, type safety, and design problems.",
        "keywords": ["error", "exception", "validate", "type", "safety", "missing", "handle"],
    },
    {
        "name": "summary",
        "question": "Write a brief README summary of this project explaining its purpose and structure to a new developer.",
        "keywords": ["service", "module", "domain", "process", "item", "test", "Application"],
    },
]


def create_test_project(temp_dir: Path):
    repo = temp_dir / "testproject"
    repo.mkdir()
    for name, content in TEST_FILES.items():
        (repo / name).write_text(textwrap.dedent(content).strip() + "\n")
    return repo


def build_raw_context(repo_path: Path) -> str:
    parts = ["Project files:\n"]
    for name in sorted(TEST_FILES.keys()):
        content = (repo_path / name).read_text()
        parts.append(f"--- {name} ---\n{content}")
    return "\n".join(parts)


def get_compression(repo_path: Path):
    compressor = CodebaseCompressor()
    return compressor.compress(str(repo_path))


def build_compressed_text(result) -> str:
    """Current Lyme compression: convert to a prompt-friendly format."""
    parts = ["Compressed project structure:\n"]
    # L1: Tree
    l1 = result.layer1_tree
    parts.append(f"Files: {l1.get('total_files', '?')}")
    # L2: APIs
    l2 = result.layer2_apis
    modules = l2.get("modules", [])
    for mod in modules:
        path = mod.get("path", mod.get("file", "?"))
        funcs = mod.get("functions", [])
        classes = mod.get("classes", [])
        parts.append(f"\nFile: {path}")
        for cls in classes:
            parts.append(f"  Class: {cls.get('name', '?')}")
            for m in cls.get("methods", []):
                parts.append(f"    Method: {m.get('name', '?')}")
        for func in funcs:
            parts.append(f"  Function: {func.get('name', '?')}")
    # L3: Subsystems
    l3 = result.layer3_subsystems
    clusters = l3.get("clusters", [])
    if clusters:
        parts.append("\nSubsystems:")
        for cl in clusters:
            parts.append(f"  {cl.get('name', '?')}: {', '.join(cl.get('files', []))}")
    # L4: Invariants  
    l4 = result.layer4_invariants
    invariants = l4.get("invariants", [])
    if invariants:
        parts.append("\nInvariants:")
        for inv in invariants[:8]:
            parts.append(f"  {inv.get('description', str(inv)[:80])}")
    return "\n".join(parts)


def build_small_model_packet(repo_path: Path, task_type: str, task_q: str) -> str:
    """New small-model compression using Lyme Model's amplification layer."""
    amp = AmplificationLayer(max_tokens=1024)
    compressor = CodebaseCompressor()
    result = compressor.compress(str(repo_path))
    result_dict = result.to_dict()
    
    amp_result = amp.amplify(
        task_type=task_type,
        task_description=task_q,
        target_files=list(TEST_FILES.keys()),
        compression_result=result_dict,
    )
    return amp_result.context_packet.to_text()


def query_model(model_name: str, prompt: str, timeout: int = 90) -> dict:
    try:
        start = time.time()
        proc = subprocess.run(
            ["ollama", "run", model_name, prompt],
            capture_output=True, text=True, timeout=timeout
        )
        elapsed = time.time() - start
        return {"output": proc.stdout.strip(), "time_s": round(elapsed, 2)}
    except subprocess.TimeoutExpired:
        return {"output": "", "time_s": timeout, "error": "timeout"}
    except Exception as e:
        return {"output": "", "time_s": 0, "error": str(e)}


def evaluate(output: str, keywords: list) -> dict:
    ol = output.lower()
    hits = sum(1 for kw in keywords if kw.lower() in ol)
    return {"keyword_score": round(hits / len(keywords) * 100, 1), "hit_count": hits, "total": len(keywords)}


def main():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = create_test_project(Path(tmpdir))

        raw_ctx = build_raw_context(repo_path)
        raw_tokens = len(raw_ctx.split())

        compression = get_compression(repo_path)
        compressed_ctx = build_compressed_text(compression)
        compressed_tokens = len(compressed_ctx.split())

        model_name = "deepseek-coder:6.7b"
        results = {"context_stats": {}, "runs": []}

        print("=" * 60)
        print("COMPRESSION COMPARISON (Week 58)")
        print("=" * 60)
        print(f"Repo: 15 modules + app + tests + config (17 files)")
        print(f"Raw context: {raw_tokens} tokens")
        print(f"Compressed (Lyme L1-L4): {compressed_tokens} tokens")
        print(f"Model: {model_name}")
        print()

        for task in TASKS:
            print(f"\n--- {task['name']} ---")

            for strategy, ctx, label in [
                ("raw", raw_ctx, "RAW"),
                ("lyme", compressed_ctx, "LYME COMPRESS"),
            ]:
                prompt = f"{ctx}\n\nQuestion: {task['question']}\nAnswer:"
                result = query_model(model_name, prompt)
                eval_result = evaluate(result["output"], task["keywords"])
                status = "OK" if eval_result["keyword_score"] >= 50 else "WEAK"

                print(f"  {label:15s}: {eval_result['keyword_score']:5.1f}% ({result['time_s']:5.1f}s) [{status}]")

                results["runs"].append({
                    "task": task["name"],
                    "strategy": strategy,
                    "score": eval_result["keyword_score"],
                    "tokens": len(ctx.split()),
                    "time_s": result["time_s"],
                    "hit_count": eval_result["hit_count"],
                    "total_keywords": eval_result["total"],
                })

        # Also test small-model packet
        print(f"\n--- small-model packet (new) ---")
        for task in TASKS:
            packet_text = build_small_model_packet(repo_path, task["name"], task["question"])
            prompt = f"{packet_text}\n\nQuestion: {task['question']}\nAnswer:"
            result = query_model(model_name, prompt)
            eval_result = evaluate(result["output"], task["keywords"])
            status = "OK" if eval_result["keyword_score"] >= 50 else "WEAK"
            print(f"  {task['name']:15s}: {eval_result['keyword_score']:5.1f}% ({result['time_s']:5.1f}s) [{status}]")
            results["runs"].append({
                "task": task["name"],
                "strategy": "small_model_packet",
                "score": eval_result["keyword_score"],
                "tokens": len(packet_text.split()),
                "time_s": result["time_s"],
                "hit_count": eval_result["hit_count"],
                "total_keywords": eval_result["total"],
            })

        # Summary
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        strategies = ["raw", "lyme", "small_model_packet"]
        for strat in strategies:
            runs = [r for r in results["runs"] if r["strategy"] == strat]
            avg = sum(r["score"] for r in runs) / len(runs)
            avg_time = sum(r["time_s"] for r in runs) / len(runs)
            avg_tokens = sum(r["tokens"] for r in runs) / len(runs)
            name = {"raw": "Raw", "lyme": "Lyme Compress", "small_model_packet": "Small Model"}[strat]
            print(f"  {name:15s}: avg {avg:5.1f}%  time {avg_time:5.1f}s  tokens {avg_tokens:5.0f}")

        results["context_stats"] = {"raw_tokens": raw_tokens, "lyme_tokens": compressed_tokens}
        outpath = "lyme-output/sprint-weeks-53-72/compression-comparison-results.json"
        with open(outpath, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nSaved to {outpath}")


if __name__ == "__main__":
    main()
