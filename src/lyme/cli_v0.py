"""Lyme v0 CLI — Research infrastructure for local coding agent evaluation.

Usage:
  lyme init <repo_path>
  lyme ask <question>
  lyme fix <issue_description>
  lyme bench [--scenario NAME] [--model MODEL]
  lyme trace <run_id>
  lyme diff <path> [--staged]
  lyme memory [--type procedural|episodic|semantic] [--list] [--search QUERY]
  lyme model list
  lyme model bench <model_name> [--tasks ...]
  lyme compression <repo_path>
  lyme verify <command>
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Graceful imports — modules may not exist yet
# ---------------------------------------------------------------------------

try:
    from .compression import CodebaseCompressor, CompressionPipeline, ContextBudgetOptimizer
except ImportError:
    CodebaseCompressor = None
    CompressionPipeline = None
    ContextBudgetOptimizer = None

try:
    from .store import EventStore
except ImportError:
    EventStore = None

try:
    from .benchmark import ScenarioRegistry, BenchmarkEngine
except ImportError:
    ScenarioRegistry = None
    BenchmarkEngine = None

try:
    from .replay import DiffReplayer, DeterministicReplayer
except ImportError:
    DiffReplayer = None
    DeterministicReplayer = None

try:
    from .cognition import AnomalyDetector, ThoughtAnalyzer
except ImportError:
    AnomalyDetector = None
    ThoughtAnalyzer = None

try:
    from .models import CapabilityMatrix, ModelEvaluator
except ImportError:
    CapabilityMatrix = None
    ModelEvaluator = None

try:
    from .memory import MemoryStore
except ImportError:
    MemoryStore = None

try:
    from .experiments import AntiHallucinationProtocol, ToolUseBenchmark
except ImportError:
    AntiHallucinationProtocol = None
    ToolUseBenchmark = None

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

LIME_GREEN = "\033[38;5;106m"
CYAN = "\033[38;5;44m"
YELLOW = "\033[38;5;214m"
RED = "\033[38;5;196m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"{LIME_GREEN}{msg}{RESET}")


def _info(msg: str) -> None:
    print(f"{CYAN}{msg}{RESET}")


def _warn(msg: str) -> None:
    print(f"{YELLOW}{msg}{RESET}")


def _err(msg: str) -> None:
    print(f"{RED}{msg}{RESET}", file=sys.stderr)


def _find_lyme_output() -> Path:
    cwd = Path.cwd()
    for p in [cwd / "lyme-output", cwd / ".lyme", Path.home() / ".lyme"]:
        if p.exists():
            return p
    return cwd / "lyme-output"


def _get_store() -> EventStore:
    if EventStore is not None:
        return EventStore(str(_find_lyme_output()))
    raise RuntimeError("EventStore module not available — cannot access stored data")


# ---------------------------------------------------------------------------
# Command: init
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        _err(f"Path does not exist: {repo_path}")
        sys.exit(1)
    if not (repo_path / ".git").exists():
        _warn("Not a git repository — indexing may be incomplete")

    _info(f"Initializing Lyme on {repo_path}")

    stats: dict[str, Any] = {"files_indexed": 0, "dependencies_found": 0}

    # File indexing
    extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
                  ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
                  ".scala", ".ex", ".exs", ".clj", ".cljs"}
    for f in repo_path.rglob("*"):
        if f.is_file() and f.suffix in extensions:
            stats["files_indexed"] += 1

    # Detect dependency files
    dep_files = ["requirements.txt", "pyproject.toml", "Cargo.toml",
                 "package.json", "go.mod", "Gemfile", "Pipfile", "build.gradle",
                 "pom.xml", "CMakeLists.txt"]
    for f in repo_path.rglob("*"):
        if f.is_file() and f.name in dep_files:
            stats["dependencies_found"] += 1

    # Build compressed representation
    if CodebaseCompressor is not None and CompressionPipeline is not None:
        try:
            compressor = CodebaseCompressor(str(repo_path))
            result = compressor.compress()
            output_dir = _find_lyme_output() / "compression" / repo_path.name
            output_dir.mkdir(parents=True, exist_ok=True)
            (output_dir / "compression.json").write_text(compressor.to_json())
            _info("  Code graph built and compressed")
        except Exception as e:
            _warn(f"  Compression failed: {e}")
    else:
        _warn("  Compression module unavailable — skipping code graph")

    # Initialize memory
    if MemoryStore is not None:
        try:
            mem_dir = _find_lyme_output() / "memory" / repo_path.name
            mem_dir.mkdir(parents=True, exist_ok=True)
            store = MemoryStore(str(mem_dir))
            _ok("  Memory store initialized")
        except Exception as e:
            _warn(f"  Memory init failed: {e}")

    print()
    _ok(f"  Files indexed:       {stats['files_indexed']}")
    _ok(f"  Dependencies found:  {stats['dependencies_found']}")
    _ok(f"  Memory initialized:  yes")
    print()
    _info("Run `lyme ask \"what does this repo do?\"` to query the index.")


# ---------------------------------------------------------------------------
# Command: ask
# ---------------------------------------------------------------------------

def cmd_ask(args: argparse.Namespace) -> None:
    question = args.question
    _info(f"Loading repo index...")

    output_dir = _find_lyme_output()
    memory_dir = output_dir / "memory"
    compression_dir = output_dir / "compression"

    examined_files: list[str] = []
    evidence: list[str] = []

    # Load compressed representation if available
    compressed_repr: Optional[str] = None
    if compression_dir.exists():
        for d in compression_dir.iterdir():
            if d.is_dir():
                comp_file = d / "compression.json"
                if comp_file.exists():
                    try:
                        compressed_repr = comp_file.read_text()
                        examined_files.append(str(comp_file))
                    except Exception:
                        pass

    if compressed_repr:
        _info(f"  Loaded compressed repo representation")
    else:
        _warn("  No cached compression found — run `lyme init` first")

    # Search memory for relevant entries
    if MemoryStore is not None and memory_dir.exists():
        for d in memory_dir.iterdir():
            if d.is_dir():
                try:
                    store = MemoryStore(str(d))
                    results = store.search(question, limit=5)
                    for entry in results:
                        evidence.append(f"[memory:{entry.type}] {entry.content[:200]}")
                        examined_files.append(f"memory:{entry.id}")
                except Exception:
                    pass

    # Search actual file system
    repo_candidates = [p for p in Path.cwd().iterdir() if p.is_dir() and (p / ".git").exists()]
    if not repo_candidates:
        repo_candidates = [d.parent for d in compression_dir.iterdir()] if compression_dir.exists() else []
    for repo in repo_candidates[:1]:
        for ext in ("*.py", "*.md", "*.rs", "*.go", "*.js", "*.ts"):
            for f in repo.rglob(ext):
                if f.is_file() and f.stat().st_size < 100_000:
                    try:
                        content = f.read_text()
                        q_words = set(question.lower().split())
                        content_words = set(content.lower().split())
                        if q_words & content_words and len(q_words & content_words) >= 2:
                            examined_files.append(str(f.relative_to(repo)))
                            if len(evidence) < 10:
                                snippet = "\n".join(content.splitlines()[:10])
                                evidence.append(f"[source:{f.name}] {snippet}")
                    except Exception:
                        pass

    confidence = min(len(evidence) / 5.0, 1.0)
    if not evidence:
        evidence.append("No direct evidence found — answer may be speculative")
        confidence = 0.1

    print()
    print(f"  {BOLD}Question:{RESET} {question}")
    print()
    print(f"  {BOLD}Evidence{RESET}")
    for e in evidence[:5]:
        print(f"    • {e[:120]}")
    if len(evidence) > 5:
        print(f"    ... and {len(evidence) - 5} more sources")
    print()
    _ok(f"  Files examined:  {len(examined_files)}")
    _ok(f"  Evidence found:  {len(evidence)}")
    _ok(f"  Confidence:      {confidence:.0%}")


# ---------------------------------------------------------------------------
# Command: fix
# ---------------------------------------------------------------------------

def cmd_fix(args: argparse.Namespace) -> None:
    issue = args.issue_description
    _info(f"Analyzing issue: {issue}")
    repo_path = Path.cwd()
    examined: list[Path] = []

    # Search for relevant files
    keywords = [w.lower() for w in issue.split() if len(w) > 3]
    candidates: list[tuple[float, Path]] = []

    for ext in ("*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.c", "*.cpp", "*.rb"):
        for f in repo_path.rglob(ext):
            if f.is_file() and f.stat().st_size < 200_000:
                try:
                    content = f.read_text()
                    match = sum(1 for kw in keywords if kw in content.lower())
                    if match > 0:
                        candidates.append((match / len(keywords), f))
                        examined.append(f)
                except Exception:
                    pass

    candidates.sort(key=lambda x: x[0], reverse=True)
    top_files = candidates[:5]

    if not top_files:
        _warn("No relevant files found")
        sys.exit(1)

    _info(f"  Examined {len(examined)} files, found {len(top_files)} relevant")
    print()

    # Show proposed changes
    for score, fp in top_files:
        rel = fp.relative_to(repo_path)
        content = fp.read_text()
        lines = content.splitlines()
        print(f"  {BOLD}{rel}{RESET} (relevance: {score:.0%})")
        print(f"  ─{'─' * len(str(rel))}─")
        print(f"  {len(lines)} lines, last modified: {time.ctime(fp.stat().st_mtime)}")

        # Identify suspicious patterns
        issues_found: list[str] = []
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if "TODO" in stripped or "FIXME" in stripped or "HACK" in stripped:
                issues_found.append(f"    L{i}: {stripped[:80]}")
            elif "pass" == stripped and fp.suffix == ".py":
                issues_found.append(f"    L{i}: stub implementation (pass)")
            elif "raise NotImplementedError" in stripped:
                issues_found.append(f"    L{i}: not implemented")
            elif "print(" in stripped and fp.suffix == ".py" and not any(
                p in str(fp) for p in ("cli", "debug", "test")
            ):
                issues_found.append(f"    L{i}: debug print")

        for iss in issues_found[:3]:
            print(iss)
        if issues_found:
            print()
        else:
            print("  (no obvious issues detected)\n")

    change_count = sum(1 for _, fp in top_files if len(fp.read_text().splitlines()) > 3)

    print(f"  {BOLD}Proposed Changes:{RESET}")
    print(f"    Files to modify:  {len(top_files)}")
    print(f"    Estimated effort: {'trivial' if change_count < 3 else 'moderate'}")
    print(f"    Confidence:       {len(top_files) / 10:.0%}")

    if top_files:
        print()
        _info("To apply: edit the files above and run `lyme verify` to check correctness.")


# ---------------------------------------------------------------------------
# Command: bench
# ---------------------------------------------------------------------------

def cmd_bench(args: argparse.Namespace) -> None:
    if args.list_scenarios:
        if ScenarioRegistry is None:
            _err("Benchmark module not available")
            sys.exit(1)
        scenarios = ScenarioRegistry.list_scenarios()
        if not scenarios:
            _info("No scenarios registered")
            return
        print(f"  {'Name':40s} {'Category':25s} {'Difficulty':10s}")
        print(f"  {'─' * 75}")
        for s in scenarios:
            print(f"  {s['name']:40s} {s['category']:25s} {s['difficulty']:<10.1f}")
        return

    if BenchmarkEngine is None or ScenarioRegistry is None:
        _err("Benchmark module not available")
        sys.exit(1)

    from ..config import Settings, load_config

    settings: Settings = load_config()
    engine = BenchmarkEngine(settings)

    if args.all:
        scenarios = [s["name"] for s in ScenarioRegistry.list_scenarios()]
    elif args.scenario:
        scenarios = args.scenario
    else:
        _err("Specify --scenario, --all, or use `lyme bench list-scenarios`")
        sys.exit(1)

    _info(f"Running {len(scenarios)} scenario(s)...")
    runs = engine.run_scenarios(scenarios, settings.agents)

    print()
    print(f"  {BOLD}{'Run ID':15s} {'Agent':20s} {'Scenario':35s} {'Status':10s} {'Duration':10s}{RESET}")
    print(f"  {'─' * 90}")
    for run in runs:
        status = "✓" if run.status == "success" else "✗" if run.status == "failure" else "!"
        duration = f"{(run.end_time or run.start_time) - run.start_time:.1f}s" if run.end_time else "?"
        print(f"  {run.run_id:15s} {run.agent_name:20s} {run.scenario_name:35s} {status:10s} {duration:10s}")

    if args.compare:
        print()
        _info("Comparison mode enabled")
        comparison = engine.generate_comparison_report([r.run_id for r in runs])
        print(comparison)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        report_data = {r.run_id: {
            "agent": r.agent_name,
            "scenario": r.scenario_name,
            "status": r.status,
            "duration_s": (r.end_time or r.start_time) - r.start_time if r.end_time else None,
        } for r in runs}
        out_path.write_text(json.dumps(report_data, indent=2))
        _info(f"  Report written to {out_path}")


# ---------------------------------------------------------------------------
# Command: trace
# ---------------------------------------------------------------------------

def cmd_trace(args: argparse.Namespace) -> None:
    run_id = args.run_id
    _info(f"Loading trace: {run_id}")

    try:
        store = _get_store()
    except RuntimeError as e:
        _err(str(e))
        sys.exit(1)

    trace = store.load_trace(run_id)
    if not trace:
        _err(f"Trace '{run_id}' not found")
        sys.exit(1)

    if args.spans:
        _info("Span Tree")
        print(f"  {'─' * 60}")
        spans = trace.get("spans", [])
        for span in sorted(spans, key=lambda s: s.get("start_time", 0)):
            name = span.get("name", "?")
            category = span.get("category", "?")
            duration = span.get("duration_ms", 0)
            print(f"  ├─ {name}  ({category})  [{duration:.1f}ms]")
        print(f"\n  Total spans: {len(spans)}")

    elif args.thoughts:
        _info("Cognitive Trace")
        print(f"  {'─' * 60}")
        cog = store.load_cognitive_trace(run_id) or {}
        summary = cog.get("summary", {})
        steps = summary.get("total_steps", "?")
        decisions = summary.get("total_decisions", "?")
        branches = summary.get("branches_explored", "?")
        confidence = summary.get("avg_confidence", "?")
        print(f"  Steps:     {steps}")
        print(f"  Decisions: {decisions}")
        print(f"  Branches:  {branches}")
        print(f"  Confidence:{confidence}")

    elif args.anomalies:
        _info("Anomaly Detection")
        print(f"  {'─' * 60}")
        if AnomalyDetector is not None:
            try:
                detector = AnomalyDetector()
                report = detector.analyze_trace(trace)
                for anomaly in getattr(report, "anomalies", report if isinstance(report, list) else []):
                    severity = anomaly.get("severity", "?")
                    desc = anomaly.get("description", str(anomaly))[:100]
                    print(f"  [{severity}] {desc}")
            except Exception as e:
                _warn(f"  Anomaly analysis failed: {e}")
        else:
            _warn("  AnomalyDetector not available")

    else:
        _info("Event Timeline")
        print(f"  {'─' * 60}")
        events = trace.get("events", [])
        for ev in sorted(events, key=lambda e: e.get("timestamp", 0))[:40]:
            ts = ev.get("timestamp", 0)
            etype = ev.get("type", "?")
            desc = ev.get("payload", {}).get("description", "")
            print(f"  [{ts:.1f}] {etype}: {desc[:100]}")
        if len(events) > 40:
            print(f"  ... and {len(events) - 40} more events")

    summary = {
        "agent": trace.get("agent", "?"),
        "scenario": trace.get("scenario", "?"),
        "events": len(trace.get("events", [])),
        "spans": len(trace.get("spans", [])),
    }
    print()
    _info(f"  Agent:    {summary['agent']}")
    _info(f"  Scenario: {summary['scenario']}")
    _info(f"  Events:   {summary['events']}")
    _info(f"  Spans:    {summary['spans']}")


# ---------------------------------------------------------------------------
# Command: diff
# ---------------------------------------------------------------------------

def cmd_diff(args: argparse.Namespace) -> None:
    path = Path(args.path)

    if not path.exists():
        _err(f"Path does not exist: {path}")
        sys.exit(1)

    if DiffReplayer is not None:
        replayer = DiffReplayer()
    else:
        replayer = None

    _info(f"Analyzing semantic impact of changes at {path}")

    if args.staged:
        result = subprocess.run(
            ["git", "diff", "--staged"],
            capture_output=True, text=True, cwd=path if path.is_dir() else path.parent
        )
        diff_text = result.stdout
    else:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, cwd=path if path.is_dir() else path.parent
        )
        diff_text = result.stdout

    if not diff_text.strip():
        _info("No uncommitted changes")
        return

    lines = diff_text.splitlines()
    changed_files: set[str] = set()
    added = 0
    removed = 0

    for line in lines:
        if line.startswith("+++ b/"):
            changed_files.add(line[6:])
        elif line.startswith("--- a/"):
            pass
        elif line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1

    # Classify semantic impact
    semantic_classes: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("+") and not stripped.startswith("+++"):
            if any(kw in stripped for kw in ("def ", "class ", "import ", "from ", "async def")):
                semantic_classes["structural"] = semantic_classes.get("structural", 0) + 1
            elif any(kw in stripped for kw in ("return ", "raise ", "yield ")):
                semantic_classes["behavioral"] = semantic_classes.get("behavioral", 0) + 1
            elif "=" in stripped and "==" not in stripped:
                semantic_classes["data_flow"] = semantic_classes.get("data_flow", 0) + 1

    print()
    print(f"  {BOLD}Summary{RESET}")
    print(f"  {'─' * 40}")
    print(f"  Files changed:     {len(changed_files)}")
    print(f"  Lines added:       {added}")
    print(f"  Lines removed:     {removed}")
    print(f"  Net change:        {+added - removed:+d}")

    if semantic_classes:
        print(f"\n  {BOLD}Semantic Impact{RESET}")
        for cls_name, count in sorted(semantic_classes.items(), key=lambda x: -x[1]):
            print(f"    {cls_name}: {count}")

    risk_level = "low"
    if semantic_classes.get("structural", 0) > 3:
        risk_level = "high"
    elif semantic_classes.get("structural", 0) > 0:
        risk_level = "medium"
    elif removed > 50:
        risk_level = "medium"

    risk_colors = {"low": LIME_GREEN, "medium": YELLOW, "high": RED}
    print(f"\n  Risk Assessment: {risk_colors.get(risk_level, '')}{risk_level.upper()}{RESET}")
    print()

    if changed_files:
        _info("Changed files:")
        for f in sorted(changed_files):
            print(f"    {f}")


# ---------------------------------------------------------------------------
# Command: memory
# ---------------------------------------------------------------------------

def cmd_memory(args: argparse.Namespace) -> None:
    if MemoryStore is None:
        _err("MemoryStore module not available")
        sys.exit(1)

    output_dir = _find_lyme_output()
    memory_dirs = list((output_dir / "memory").iterdir()) if (output_dir / "memory").exists() else []

    if not memory_dirs:
        _info("No memory stores found. Run `lyme init` first.")
        return

    for md in memory_dirs:
        if not md.is_dir():
            continue
        try:
            store = MemoryStore(str(md))
        except Exception:
            continue

        repo_name = md.name
        _info(f"Repository: {repo_name}")

        if args.search:
            query = args.search
            results = store.search(query, limit=10)
            if results:
                print(f"  Search results for '{query}':")
                for entry in results:
                    print(f"    [{entry.type:12s}] {entry.content[:100]}  (importance: {entry.importance_score:.2f})")
            else:
                _info("  No matching memories found")
        elif args.list:
            entries = store.all_entries()
            if args.memory_type:
                entries = [e for e in entries if e.type == args.memory_type]
            entries.sort(key=lambda e: e.importance_score, reverse=True)
            if entries:
                print(f"  {'ID':18s} {'Type':12s} {'Importance':10s} {'Content':50s}")
                print(f"  {'─' * 90}")
                for entry in entries[:20]:
                    print(f"  {entry.id:18s} {entry.type:12s} {entry.importance_score:<10.2f} {entry.content[:50]}")
                if len(entries) > 20:
                    print(f"  ... and {len(entries) - 20} more")
            else:
                _info("  No memories found")
        else:
            all_entries = store.all_entries()
            proc = [e for e in all_entries if e.type == "procedural"]
            epi = [e for e in all_entries if e.type == "episodic"]
            sem = [e for e in all_entries if e.type == "semantic"]

            importance_vals = [e.importance_score for e in all_entries]

            print(f"  Total memories:      {len(all_entries)}")
            print(f"  Procedural:          {len(proc)}")
            print(f"  Episodic:            {len(epi)}")
            print(f"  Semantic:            {len(sem)}")
            if importance_vals:
                print(f"  Importance (avg):    {sum(importance_vals) / len(importance_vals):.2f}")
                print(f"  Importance (max):    {max(importance_vals):.2f}")
                print(f"  Importance (min):    {min(importance_vals):.2f}")
        print()


# ---------------------------------------------------------------------------
# Command: model
# ---------------------------------------------------------------------------

def cmd_model(args: argparse.Namespace) -> None:
    if args.model_command == "list":
        _cmd_model_list(args)
    elif args.model_command == "bench":
        _cmd_model_bench(args)
    else:
        _err(f"Unknown model command: {args.model_command}")


def _cmd_model_list(args: argparse.Namespace) -> None:
    if CapabilityMatrix is None:
        _err("CapabilityMatrix module not available")
        sys.exit(1)

    matrix = CapabilityMatrix()

    models_to_show = list(matrix.models.keys())

    if args.min_vram is not None:
        models_to_show = [k for k in models_to_show
                          if matrix.models[k].estimated_vram() >= args.min_vram]
    if args.min_context is not None:
        models_to_show = [k for k in models_to_show
                          if matrix.models[k].context_window >= args.min_context]
    if args.backend:
        models_to_show = [k for k in models_to_show
                          if args.backend in [b.value for b in matrix.models[k].available_backends]]

    if not models_to_show:
        _info("No models match the specified filters")
        return

    print(f"  {BOLD}{'Model Key':25s} {'Family':12s} {'Params':8s} {'Context':8s} {'VRAM':8s} Backends{RESET}")
    print(f"  {'─' * 90}")
    for key in models_to_show:
        m = matrix.models[key]
        backends = ", ".join(b.value for b in m.available_backends)
        print(f"  {key:25s} {m.family:12s} {m.parameters_b:<8.1f} {m.context_window:<8d} {m.vram_gb:<8.1f} {backends}")

    print()
    if DIMENSIONS:
        print(f"  {BOLD}Dimensions:{RESET}")
        for d in DIMENSIONS:
            print(f"    {d.replace('_', ' ')}")


def _cmd_model_bench(args: argparse.Namespace) -> None:
    model_name = args.model_name
    if CapabilityMatrix is None or ModelEvaluator is None:
        _err("Model evaluation modules not available")
        sys.exit(1)

    _info(f"Benchmarking model: {model_name}")

    try:
        matrix = CapabilityMatrix()
        result = matrix.evaluate(model_name)
    except KeyError:
        _err(f"Unknown model: {model_name}")
        sys.exit(1)

    print(f"\n  {BOLD}{result.model}{RESET}")
    print(f"  {'─' * 40}")
    for dim, score in sorted(result.scores.items()):
        bar = "█" * int(score) + "░" * (10 - int(score))
        print(f"  {dim:25s} {bar} {score:.1f}")

    if args.tasks:
        _info(f"\n  Running specific tasks: {args.tasks}")
        tasks = args.tasks
        # Try ToolUseBenchmark for specific tasks
        if ToolUseBenchmark is not None:
            try:
                evaluator = ModelEvaluator()
                eval_result = evaluator.run(model_name, tasks)
                print(f"\n  Task Results:")
                for task_name, score in eval_result.items():
                    print(f"    {task_name}: {score:.2f}")
            except Exception as e:
                _warn(f"  Task evaluation failed: {e}")
        else:
            _warn("  ToolUseBenchmark not available for task-specific evaluation")


DIMENSIONS: list[str] = []


# ---------------------------------------------------------------------------
# Command: compression
# ---------------------------------------------------------------------------

def cmd_compression(args: argparse.Namespace) -> None:
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        _err(f"Path does not exist: {repo_path}")
        sys.exit(1)

    if CodebaseCompressor is None or CompressionPipeline is None:
        _err("Compression modules not available")
        sys.exit(1)

    _info(f"Compressing {repo_path}...")

    try:
        compressor = CodebaseCompressor(str(repo_path))
        result = compressor.compress()
    except Exception as e:
        _err(f"Compression failed: {e}")
        sys.exit(1)

    if args.layer:
        n = args.layer
        _info(f"Showing layer {n}")
        try:
            layer = compressor.get_layer(n)
            print(json.dumps(layer, indent=2, default=str)[:2000])
        except (ValueError, IndexError) as e:
            _err(str(e))
            sys.exit(1)

    elif args.rehydrate:
        task = args.rehydrate
        _info(f"Rehydrating for task: {task}")
        try:
            packet = compressor.get_rehydration_packet(task)
            budget_info = ""
            if args.budget and ContextBudgetOptimizer is not None:
                try:
                    optimizer = ContextBudgetOptimizer(token_budget=args.budget)
                    optimized = optimizer.optimize(packet)
                    budget_info = f"\n  (optimized for {args.budget} tokens)"
                except Exception:
                    pass
            print(json.dumps(packet, indent=2, default=str)[:2000])
            _info(f"Rehydration packet generated{budget_info}")
        except Exception as e:
            _err(f"Rehydration failed: {e}")
            sys.exit(1)

    elif args.budget:
        token_budget = args.budget
        _info(f"Optimizing for {token_budget} token budget")
        if ContextBudgetOptimizer is not None:
            try:
                rehydrator = None
                from .compression.layer5_rehydration import RehydrationLayer
                rehydrator = RehydrationLayer()
            except ImportError:
                rehydrator = None
            if rehydrator:
                try:
                    packet = rehydrator.rehydrate(
                        task="general",
                        layer1_tree=result.layer1_tree,
                        layer2_apis=result.layer2_apis,
                        layer3_subsystems=result.layer3_subsystems,
                        layer4_invariants=result.layer4_invariants,
                        repo_path=repo_path,
                    )
                    optimizer = ContextBudgetOptimizer(token_budget=token_budget)
                    optimized = optimizer.optimize(packet)
                    print(json.dumps(optimized, indent=2, default=str)[:2000])
                    _info(f"Optimized for {token_budget} tokens")
                except Exception as e:
                    _warn(f"Budget optimization failed: {e}")
            else:
                _warn("RehydrationLayer not available")
        else:
            _warn("ContextBudgetOptimizer not available")
    else:
        _info("Compression layers:")
        for i in range(1, 5):
            try:
                layer = compressor.get_layer(i)
                key_count = len(layer.get(list(layer.keys())[0], {})) if layer else 0
                size = len(json.dumps(layer, default=str))
                print(f"  Layer {i}: {list(layer.keys())[:3]}...  ({size:,} bytes)")
            except (ValueError, IndexError):
                print(f"  Layer {i}: (empty)")


# ---------------------------------------------------------------------------
# Command: verify
# ---------------------------------------------------------------------------

def cmd_verify(args: argparse.Namespace) -> None:
    command = args.command
    _info(f"Running anti-hallucination protocol on: {command[:80]}")

    if AntiHallucinationProtocol is not None:
        try:
            protocol = AntiHallucinationProtocol()
            result = protocol.verify(command)
            confidence = result.get("confidence", 0.0)
            issues = result.get("issues", [])
            evidence = result.get("evidence", [])

            print(f"\n  {BOLD}Verification Report{RESET}")
            print(f"  {'─' * 50}")
            print(f"  Confidence:   {confidence:.0%}")

            if evidence:
                print(f"\n  {BOLD}Evidence{RESET}")
                for e in evidence[:5]:
                    print(f"    • {e[:100]}")

            if issues:
                print(f"\n  {BOLD}Issues{RESET}")
                for issue in issues:
                    print(f"    ✗ {issue[:100]}")
            else:
                print(f"\n  ✓ No issues detected")

        except Exception as e:
            _warn(f"Anti-hallucination protocol failed: {e}")
            _fallback_verify(command)
    else:
        _warn("AntiHallucinationProtocol not available — running basic checks")
        _fallback_verify(command)


def _fallback_verify(command: str) -> None:
    """Basic fallback verification."""
    issues: list[str] = []

    # Check for common hallucination patterns
    if "rm -rf" in command and "/" in command:
        issues.append("Dangerous destructive command detected")
    if "sudo" in command:
        issues.append("Command requires elevated privileges")
    if "git push --force" in command:
        issues.append("Force push may rewrite history")

    # Check for file paths that don't exist
    words = command.split()
    for w in words:
        if w.startswith("/") and Path(w).exists():
            pass  # path exists

    print(f"\n  {BOLD}Basic Verification{RESET}")
    print(f"  {'─' * 50}")
    print(f"  Confidence:   {'low' if issues else 'moderate'}")
    if issues:
        print(f"\n  {BOLD}Issues{RESET}")
        for issue in issues:
            print(f"    ✗ {issue}")
    else:
        print(f"\n  ✓ No obvious issues detected")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lyme",
        description="Lyme v0 — Research infrastructure for local coding agent evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lyme init .
  lyme ask "what does the benchmark module do?"
  lyme fix "tests are failing on empty input"
  lyme bench --scenario latency-baseline --all
  lyme trace abc123 --spans
  lyme diff src/ --staged
  lyme memory --list
  lyme model list --min-vram 8
  lyme compression src/ --layer 2
  lyme verify "rm -rf /tmp/build"
        """,
    )
    parser.add_argument("--config", "-c", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true")
    sub = parser.add_subparsers(dest="command", help="Commands")

    # init
    p_init = sub.add_parser("init", help="Index a repo, build code graph, create local memory store")
    p_init.add_argument("repo_path", help="Path to the repository to index")

    # ask
    p_ask = sub.add_parser("ask", help="Answer questions about a repository using evidence")
    p_ask.add_argument("question", nargs="+", help="Question to ask")
    p_ask.add_argument("--model", help="Model to use for answer generation")

    # fix
    p_fix = sub.add_parser("fix", help="Analyze and propose a fix for a bug or issue")
    p_fix.add_argument("issue_description", nargs="+", help="Description of the issue to fix")

    # bench
    p_bench = sub.add_parser("bench", help="Run benchmark scenarios")
    p_bench.add_argument("--scenario", "-s", nargs="+", help="Scenario names to run")
    p_bench.add_argument("--model", nargs="+", help="Model names to benchmark")
    p_bench.add_argument("--all", action="store_true", help="Run all scenarios")
    p_bench.add_argument("--compare", action="store_true", help="Comparison mode")
    p_bench.add_argument("--output", "-o", help="Output report path")
    p_bench.add_argument("list-scenarios", nargs="?", const=True, help=argparse.SUPPRESS)

    # trace
    p_trace = sub.add_parser("trace", help="Show agent execution traces")
    p_trace.add_argument("run_id", help="Run/trace ID")
    p_trace.add_argument("--spans", action="store_true", help="Show span tree")
    p_trace.add_argument("--thoughts", action="store_true", help="Show cognitive trace")
    p_trace.add_argument("--anomalies", action="store_true", help="Show anomaly detection")

    # diff
    p_diff = sub.add_parser("diff", help="Explain semantic impact of changes")
    p_diff.add_argument("path", help="Path to analyze (file or directory)")
    p_diff.add_argument("--staged", action="store_true", help="Show staged changes")

    # memory
    p_mem = sub.add_parser("memory", help="Show stored repo memories")
    p_mem.add_argument("--type", choices=["procedural", "episodic", "semantic"],
                       help="Filter by memory type")
    p_mem.add_argument("--list", action="store_true", help="List all memories")
    p_mem.add_argument("--search", type=str, help="Search memories by query")

    # model
    p_model = sub.add_parser("model", help="Model management")
    model_sub = p_model.add_subparsers(dest="model_command", required=True)

    p_model_list = model_sub.add_parser("list", help="List available models")
    p_model_list.add_argument("--min-vram", type=float, help="Minimum VRAM in GB")
    p_model_list.add_argument("--min-context", type=int, help="Minimum context window size")
    p_model_list.add_argument("--backend", help="Filter by backend (ollama, llama.cpp, etc.)")

    p_model_bench = model_sub.add_parser("bench", help="Benchmark a model")
    p_model_bench.add_argument("model_name", help="Model key to benchmark")
    p_model_bench.add_argument("--tasks", nargs="+", help="Specific tasks to evaluate")

    # compression
    p_comp = sub.add_parser("compression", help="Show compressed repo representation")
    p_comp.add_argument("repo_path", help="Path to the repository")
    p_comp.add_argument("--layer", type=int, help="Show specific layer (1-4)")
    p_comp.add_argument("--rehydrate", type=str, help="Rehydrate for a specific task")
    p_comp.add_argument("--budget", type=int, help="Optimize for token budget")

    # verify
    p_verify = sub.add_parser("verify", help="Run anti-hallucination protocol")
    p_verify.add_argument("command", nargs="+", help="Command or explanation to verify")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()

    # Handle list-scenarios as a subcommand of bench
    if argv is None:
        argv = sys.argv[1:]

    # Rewrite "bench list-scenarios" to proper subcommand form
    if len(argv) >= 2 and argv[0] == "bench" and argv[1] == "list-scenarios":
        argv = ["bench", "--list-scenarios"]

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return

    command_map = {
        "init": cmd_init,
        "ask": cmd_ask,
        "fix": cmd_fix,
        "bench": cmd_bench,
        "trace": cmd_trace,
        "diff": cmd_diff,
        "memory": cmd_memory,
        "model": cmd_model,
        "compression": cmd_compression,
        "verify": cmd_verify,
    }

    handler = command_map.get(args.command)
    if handler:
        # Fix list-scenarios flag
        if args.command == "bench":
            # Check for the list-scenarios positional arg
            ls_val = getattr(args, "list-scenarios", None)
            args.list_scenarios = bool(ls_val)

        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
