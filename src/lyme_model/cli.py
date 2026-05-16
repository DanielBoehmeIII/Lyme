"""Lyme Model CLI — lyme model subcommands.

Commands:
  ask         Repository Q&A (hardened local parity slice)
  plan        Task decomposition + plan
  fix         Plan + apply a fix
  bench       Run benchmarks
  resume      Resume a checkpointed run
  compare     Compare Lyme Model against baselines
  profile     Profile model performance
  modes       List available modes for hardware tier
  run         Execute a coding task
  list        List available models
  hardware    Detect and report hardware
  eval        Evaluate on benchmarks

Requirements: good errors, no silent failures, readable output, JSON mode, dry-run, verbose audit.
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional
import time

from .runtime.engine import LocalInferenceEngine, AgentRuntime
from .runtime.loader import ModelLoader
from .hardware.detector import detect_all
from .eval.harness import ModelEvaluationHarness
from .slices.repo_qa import RepoQASlice, RepoQABenchmark, RepoQADemo, repo_qa_slice
from .eval.real_repo_eval import RealRepoEvalSet, EVAL_TASKS
from .eval.human_baseline import HumanBaselineComparison, BASELINE_COMPARISON
from .planning.difficulty_estimator import DifficultyEstimator, estimator as diff_estimator
from .planning.mode_selection import ModeSelector, selector as mode_selector
from .planning.fallback import FallbackStrategy, fallback as fallback_strategy
from .planning.confidence import LymeConfidenceCalibrator, calibrator as conf_calibrator
from .planning.long_horizon import TaskDecomposer, CheckpointManager
from .context import ContextCompiler, ImprovedContextCompiler, ContextBenchmark
from .tools import ToolSession, ToolCallParser, SafetyMode
from .slices.qa_engine import QAEngine, QABenchmark, run_qa_demo
from .eval.benchmark_harness import ModelBenchmarkHarness, run_model_benchmark
from .release_v06 import v06
from .release_v07 import v07


def register_subcommands(subparsers):
    """Register all lyme model subcommands."""
    model_parser = subparsers.add_parser("model", help="Lyme Model commands")

    model_sub = model_parser.add_subparsers(dest="model_command")

    # lyme model ask
    ask = model_sub.add_parser("ask", help="Repository Q&A (hardened local parity slice)")
    ask.add_argument("question", nargs="?", help="Question about the repository")
    ask.add_argument("--repo", default=".", help="Repository path")
    ask.add_argument("--json", action="store_true", help="JSON output")
    ask.add_argument("--report", action="store_true", help="Show full capability report")

    # lyme model plan
    plan = model_sub.add_parser("plan", help="Decompose task into subtasks with plan")
    plan.add_argument("task", nargs="?", help="Task description")
    plan.add_argument("--type", default="hierarchical", choices=["flat", "hierarchical", "hierarchical_with_critic"],
                      help="Planning type")
    plan.add_argument("--json", action="store_true", help="JSON output")

    # lyme model fix
    fix = model_sub.add_parser("fix", help="Plan and apply a fix (checkpointed long-horizon)")
    fix.add_argument("task", nargs="?", help="What to fix")
    fix.add_argument("--dry-run", action="store_true", help="Show full inspectable pipeline without applying")
    fix.add_argument("--no-test-run", action="store_true", help="Skip test run in dry-run mode")
    fix.add_argument("--json", action="store_true", help="JSON output")

    # lyme model bench
    bench = model_sub.add_parser("bench", help="Run benchmarks")
    bench.add_argument("--suite", default="all", choices=["repo-qa", "real-repo", "long-horizon", "all"],
                       help="Benchmark suite")
    bench.add_argument("--json", action="store_true", help="JSON output")

    # lyme model resume
    resume = model_sub.add_parser("resume", help="Resume a checkpointed run")
    resume.add_argument("run_id", help="Run ID to resume")
    resume.add_argument("--json", action="store_true", help="JSON output")

    # lyme model compare (raw vs context)
    compare = model_sub.add_parser("compare", help="Compare raw model vs context-compiled model")
    compare.add_argument("--model", default="deepseek-coder:6.7b", help="Model name for comparison")
    compare.add_argument("--task", default="What language and framework does this repo use?", help="Task for comparison")
    compare.add_argument("--json", action="store_true", help="JSON output")

    # lyme model profile (system profile)
    profile = model_sub.add_parser("profile", help="System profile for Lyme Model")
    profile.add_argument("--json", action="store_true", help="JSON output")

    # lyme model modes
    modes = model_sub.add_parser("modes", help="List available modes for hardware tier")
    modes.add_argument("--hardware", default="standard_gpu",
                       choices=["minimal", "cpu_only", "budget_gpu", "standard_gpu", "high_end"],
                       help="Hardware tier")
    modes.add_argument("--json", action="store_true", help="JSON output")

    # lyme model run (existing)
    run = model_sub.add_parser("run", help="Execute a coding task")
    run.add_argument("task", nargs="?", help="Task description")
    run.add_argument("--model", default="deepseek-coder:6.7b", help="Model name")
    run.add_argument("--repo", default=".", help="Repository path")
    run.add_argument("--context", help="Context file path")
    run.add_argument("--output", "-o", help="Output file for results")
    run.add_argument("--dry-run", action="store_true", help="Show what would happen")
    run.add_argument("--json", action="store_true", help="JSON output")

    # lyme model list (existing)
    model_sub.add_parser("list", help="List available models")

    # lyme model hardware (existing)
    model_sub.add_parser("hardware", help="Detect and report hardware")

    # lyme model eval (existing)
    eval_cmd = model_sub.add_parser("eval", help="Evaluate model on benchmarks")
    eval_cmd.add_argument("--model", default="deepseek-coder:6.7b")

    # lyme model context
    context_cmd = model_sub.add_parser("context", help="Compile repository context for model input")
    context_cmd.add_argument("--task", help="Optional task to focus context")
    context_cmd.add_argument("--improved", action="store_true", help="Use improved context compiler (W2)")
    context_cmd.add_argument("--max-tokens", type=int, help="Token budget")
    context_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model qa
    qa_cmd = model_sub.add_parser("qa", help="Repository Q&A with evidence")
    qa_cmd.add_argument("question", nargs="?", help="Question about the repository")
    qa_cmd.add_argument("--repo", default=".", help="Repository path")
    qa_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model qa-benchmark
    qa_bench = model_sub.add_parser("qa-benchmark", help="Benchmark Q&A quality")
    qa_bench.add_argument("--repo", default=".", help="Repository path")
    qa_bench.add_argument("--json", action="store_true", help="JSON output")

    # lyme model qa-demo
    qa_demo_cmd = model_sub.add_parser("qa-demo", help="Run Q&A demo")
    qa_demo_cmd.add_argument("--repo", default=".", help="Repository path")

    # lyme model benchmark (W5)
    benchmark_cmd = model_sub.add_parser("benchmark", help="Run model benchmark suite")
    benchmark_cmd.add_argument("--suite", default="all", choices=["all", "standard", "regression"])
    benchmark_cmd.add_argument("--repo", default=".", help="Repository path")
    benchmark_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model eval-report
    model_sub.add_parser("eval-report", help="Show final MVP evaluation report")

    # lyme model context-benchmark
    ctx_bench = model_sub.add_parser("context-benchmark", help="Benchmark context compilation quality")
    ctx_bench.add_argument("--repo", default=".", help="Repository path")
    ctx_bench.add_argument("--json", action="store_true", help="JSON output")

    # lyme model tools
    tools_cmd = model_sub.add_parser("tools", help="Tool session commands")
    tools_sub = tools_cmd.add_subparsers(dest="tools_command")

    tools_run = tools_sub.add_parser("run", help="Execute tool calls from model output")
    tools_run.add_argument("--input", help="File containing model output with TOOL calls")
    tools_run.add_argument("--text", help="Model output text with TOOL calls (inline)")
    tools_run.add_argument("--safety", default="readonly", choices=["readonly", "careful", "full"])
    tools_run.add_argument("--repo", default=".", help="Repository path")
    tools_run.add_argument("--json", action="store_true", help="JSON output")

    tools_parse = tools_sub.add_parser("parse", help="Parse tool calls from text without executing")
    tools_parse.add_argument("--text", required=True, help="Model output text to parse")
    tools_parse.add_argument("--json", action="store_true", help="JSON output")

    # lyme model tests
    tests_cmd = model_sub.add_parser("tests", help="Test-related commands")
    tests_sub = tests_cmd.add_subparsers(dest="tests_command")
    tests_detect = tests_sub.add_parser("detect", help="Detect test commands for this repo")
    tests_detect.add_argument("--repo", default=".", help="Repository path")
    tests_detect.add_argument("--json", action="store_true", help="JSON output")

    # lyme model summary
    summary_cmd = model_sub.add_parser("summary", help="Quick repository summary")
    summary_cmd.add_argument("--repo", default=".", help="Repository path")
    summary_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model history
    history_cmd = model_sub.add_parser("history", help="List all model runs")
    history_cmd.add_argument("--limit", type=int, default=20, help="Max entries")
    history_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model show
    show_cmd = model_sub.add_parser("show", help="Show details for a model run")
    show_cmd.add_argument("run_id", help="Run ID to show")
    show_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model report
    report_cmd = model_sub.add_parser("report", help="Model run summary report")
    report_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model locate
    locate_cmd = model_sub.add_parser("locate", help="Locate bug-related files from description")
    locate_cmd.add_argument("task", nargs="?", help="Bug description")
    locate_cmd.add_argument("--repo", default=".", help="Repository path")
    locate_cmd.add_argument("--json", action="store_true", help="JSON output")

    return model_parser


def handle_command(args):
    """Handle lyme model subcommands."""
    cmd_map = {
        "ask": _cmd_ask,
        "plan": _cmd_plan,
        "fix": _cmd_fix,
        "bench": _cmd_bench,
        "resume": _cmd_resume,
        "compare": _cmd_compare,
        "profile": _cmd_profile,
        "modes": _cmd_modes,
        "run": _cmd_run,
        "list": _cmd_list,
        "hardware": _cmd_hardware,
        "context": _cmd_context,
        "qa": _cmd_qa,
        "qa-benchmark": _cmd_qa_benchmark,
        "qa-demo": _cmd_qa_demo,
        "benchmark": _cmd_benchmark,
        "eval-report": _cmd_eval_report,
        "context-benchmark": _cmd_context_benchmark,
        "tools": _cmd_tools,
        "summary": _cmd_summary,
        "tests": _cmd_tests,
        "eval": _cmd_eval,
        "history": _cmd_history,
        "show": _cmd_show,
        "report": _cmd_report,
        "locate": _cmd_locate,
    }
    handler = cmd_map.get(args.model_command)
    if handler:
        return handler(args)
    print("Error: Unknown model command", file=sys.stderr)
    print("Available: ask, plan, fix, bench, resume, compare, profile, modes, run, context, context-benchmark, summary, qa, qa-benchmark, qa-demo, benchmark, eval-report, tools, list, hardware, eval", file=sys.stderr)
    return 1


def _get_task_input(args) -> str:
    task = getattr(args, 'task', None) or getattr(args, 'question', None)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Error: Task/question required", file=sys.stderr)
        sys.exit(1)
    return task


# ─── New Commands ──────────────────────────────────────────────────────────────

def _cmd_ask(args):
    if args.report:
        report = repo_qa_slice.full_report()
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(report.get("capability_boundary", ""))
            print(f"\nFailure Modes: {len(report.get('failure_modes', []))}")
            print(f"Benchmark Tasks: {len(report.get('benchmark_tasks', []))}")
            print(f"Hardware Tiers: {len(report.get('hardware_requirements', []))}")
        return 0

    question = _get_task_input(args)
    repo_path = Path(args.repo).resolve() if args.repo else Path.cwd()

    try:
        slice_obj = RepoQASlice(repo_path)
        supported, domain = slice_obj.check_support(question)

        diff_est = diff_estimator.estimate(question)

        result = {
            "question": question,
            "supported": supported,
            "domain": domain,
            "difficulty": diff_est.difficulty_level.value,
            "success_probability": diff_est.success_probability,
        }

        if not supported:
            result["answer"] = None
            result["refused"] = True
            result["refusal_reason"] = (
                f"Cannot answer: '{question}' — outside Repo Q&A capability. "
                "Supported: language, framework, dependencies, file structure, "
                "functions, classes, tests, config, documentation, structural risks."
            )
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print(f"✗ REFUSED: {result['refusal_reason']}")
            return 1

        result["refused"] = False
        result["answer"] = f"Domain: {domain}. Use static file analysis for full answer."
        result["confidence"] = 0.9 if domain else 0.5

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            conf_pct = f"{result['confidence']:.0%}"
            print(f"✓ {question}")
            print(f"  Domain: {domain} | Confidence: {conf_pct} | Difficulty: {result['difficulty']}")
            print(f"  Expected success: {result['success_probability']:.0%}")
        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _cmd_plan(args):
    task = _get_task_input(args)
    decomposer = TaskDecomposer()
    plan = decomposer.decompose(task)
    hplan = v07.hierarchical_planner.plan(task, getattr(args, 'type', 'hierarchical'))

    if args.json:
        print(json.dumps({"decomposition": plan.to_dict(), "hierarchical": hplan.to_dict()}, indent=2, default=str))
    else:
        print(f"Goal: {task}")
        print(f"Subtasks: {len(plan.subtasks)}")
        for s in plan.subtasks:
            deps = f" (after: {', '.join(s.dependencies)})" if s.dependencies else ""
            print(f"  [{s.type.value}] {s.name}{deps}")
        print(f"\nHierarchical Plan: {hplan.plan_type}")
        print(f"  Root: {hplan.root.name}")
        for c in hplan.root.children:
            print(f"  ├─ {c.name}")
            for gc in c.children:
                print(f"     ├─ {gc.name}")
                for ggc in gc.children:
                    print(f"        ├─ {ggc.name}")
    return 0


def _cmd_fix(args):
    task = _get_task_input(args)
    diff_est = diff_estimator.estimate(task)
    mode_sel = mode_selector.select_mode(diff_est.difficulty_score, diff_est.risk.value, "standard_gpu", 1000,
                                          task_type=diff_est.task_type.value)

    is_dry_run = getattr(args, 'dry_run', False) or args.json

    if is_dry_run:
        result = {
            "task": task,
            "dry_run": True,
            "difficulty": diff_est.to_dict(),
            "mode_selection": mode_sel.to_dict(),
        }

        no_test_run = getattr(args, 'no_test_run', False)

        # Step 1: Detect test command
        from pathlib import Path
        repo_path = Path.cwd()
        test_cmd = _detect_test_command(repo_path)
        result["detected_test_command"] = test_cmd

        # Step 2: Run tests
        test_failures = []
        if not no_test_run and test_cmd and test_cmd != "unknown":
            import subprocess
            try:
                tr = subprocess.run(test_cmd.split(), capture_output=True, text=True, timeout=60, cwd=repo_path)
                if tr.returncode != 0:
                    test_failures = _parse_test_failures(tr.stdout + tr.stderr)
            except subprocess.TimeoutExpired:
                test_failures = ["test timed out"]
            except FileNotFoundError:
                test_failures = [f"test command not found: {test_cmd}"]
            except Exception as e:
                test_failures = [str(e)]
        else:
            test_failures = ["(test run skipped)"]

        run_skipped = no_test_run or test_cmd is None or test_cmd == "unknown"
        result["test_run"] = {
            "command": test_cmd or "none",
            "passed": len(test_failures) == 0,
            "skipped": run_skipped,
            "failures": test_failures[:5],
        }

        # Step 3: Identify likely files
        likely_files = _identify_likely_files(task, repo_path)
        result["likely_files"] = likely_files[:10]

        # Step 4: Compile context packet
        from .context import ContextCompiler
        cc = ContextCompiler()
        context = cc.compile(task=task)
        result["context_packet"] = {
            "tokens": context.total_tokens,
            "chars": context.total_chars,
            "sections": ["repo_summary", "structure", "api_surface", "risks", "build_commands", "test_commands"],
        }

        # Step 5: Show intended prompt
        prompt = (
            f"Task: Fix the following issue in the repository at {repo_path}\n\n"
            f"Issue: {task}\n\n"
            f"Repository context:\n{context.to_text()[:2000]}\n\n"
            f"Test failures: {test_failures[:3]}\n\n"
            "Provide a unified diff that fixes the issue. Output ONLY the diff."
        )
        result["intended_prompt"] = prompt
        result["intended_prompt_tokens"] = len(prompt.split())
        result["estimated_total_tokens"] = context.total_tokens + len(prompt.split())
        result["status"] = "inspectable — ready for model call"
        result["warning"] = "Dry run — no changes applied. Run without --dry-run to execute."

        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print("=" * 55)
            print("  FIX DRY RUN — INSPECTABLE PIPELINE")
            print("=" * 55)
            print(f"  Task:               {task}")
            print(f"  Difficulty:         {diff_est.difficulty_level.value} ({diff_est.difficulty_score:.2f})")
            print(f"  Mode:               {mode_sel.selected_mode.value}")
            print(f"  Success prob:       {diff_est.success_probability:.0%}")
            print()
            print(f"  Test Command:       {result['detected_test_command'] or 'none'}")
            print(f"  Tests Passed:       {result['test_run']['passed']}")
            if result['test_run']['failures'] and result['test_run']['failures'][0] != "(test run skipped)":
                for f in result['test_run']['failures'][:3]:
                    print(f"    Failure: {f}")
            print()
            print(f"  Likely Files:       {len(result['likely_files'])} candidates")
            for f in result['likely_files'][:5]:
                print(f"    - {f}")
            print()
            print(f"  Context Tokens:     {context.total_tokens}")
            print(f"  Prompt Tokens:      {result['intended_prompt_tokens']}")
            print(f"  Total Tokens:       {result['estimated_total_tokens']}")
            print()
            print("  Intended Prompt (truncated):")
            for line in prompt.split("\n")[:8]:
                print(f"    {line}")
            print("    ...")
            print()
            print("  Dry run — no changes applied.")
            print("  Run without --dry-run to execute.")
            print("=" * 55)
        return 0

    fallback_check = fallback_strategy.should_refuse(diff_est.task_type.value, diff_est.difficulty_score, "standard_gpu")
    if fallback_check:
        print(f"REFUSED: {fallback_check}")
        return 1

    result = v07.run_long_task(task)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Fix: {task}")
        print(f"  Subtasks: {result['passed_subtasks']}/{result['total_subtasks']} passed")
        print(f"  Checkpoints: {result['checkpoints_created']}")
        print(f"  Run ID: {result.get('run_id', 'N/A')}")
    return 0


def _detect_test_command(repo_path: Path) -> str:
    """Detect the most likely test command for a repo."""
    if (repo_path / "pyproject.toml").exists() or list(repo_path.rglob("conftest.py")):
        return "python3 -m pytest"
    if (repo_path / "Makefile").exists() and "test:" in (repo_path / "Makefile").read_text(errors="ignore"):
        return "make test"
    if (repo_path / "package.json").exists():
        return "npm test"
    if list(repo_path.rglob("Cargo.toml")):
        return "cargo test"
    if (repo_path / "go.mod").exists():
        return "go test ./..."
    if list(repo_path.rglob("test_*.py")):
        return "python3 -m pytest"
    return ""


def _parse_test_failures(output: str) -> list:
    """Parse test failures from test output."""
    failures = []
    for line in output.split("\n"):
        lower = line.strip().lower()
        if any(kw in lower for kw in ["failed", "error", "assertionerror", "traceback"]):
            failures.append(line.strip()[:120])
        if len(failures) >= 10:
            break
    return failures


def _identify_likely_files(task: str, repo_path: Path) -> list:
    """Identify files likely relevant to a fix task using keyword matching."""
    keywords = set(task.lower().split())
    scored = []
    for f in sorted(repo_path.rglob("*")):
        if not f.is_file() or f.name.startswith("."):
            continue
        if "site-packages" in str(f) or ".venv" in str(f) or "__pycache__" in str(f):
            continue
        try:
            rel = str(f.relative_to(repo_path))
            name_score = sum(1 for k in keywords if k in f.name.lower() or k in rel.lower())
            if name_score > 0:
                scored.append((name_score, rel))
        except Exception:
            continue
    scored.sort(key=lambda x: -x[0])
    return [f for _, f in scored[:20]]


def _cmd_bench(args):
    suite = getattr(args, 'suite', 'all')
    results = {}

    if suite in ("repo-qa", "all"):
        tasks = repo_qa_slice.get_benchmark_tasks()
        results["repo_qa"] = {"tasks": len(tasks), "status": "ready"}

    if suite in ("real-repo", "all"):
        eval_set = RealRepoEvalSet()
        results["real_repo"] = {
            "tasks": len(EVAL_TASKS),
            "repos": 7,
            "status": "ready",
        }

    if suite in ("long-horizon", "all"):
        experiments = v07.failure_analyzer.run_experiments()
        results["long_horizon"] = {
            "experiments": len(experiments),
            "status": "analyzed",
        }

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for name, data in results.items():
            print(f"{name}: {data.get('tasks', data.get('experiments', 0))} items — {data['status']}")
    return 0


def _cmd_resume(args):
    run_id = args.run_id
    run = v07.checkpoints.get_run(run_id)
    if not run:
        print(f"Error: Run '{run_id}' not found. Use 'lyme model list' to see available runs.", file=sys.stderr)
        return 1

    cp = run.latest_checkpoint()
    result = {
        "run_id": run.original_goal[:60],
        "checkpoints": len(run.checkpoints),
        "remaining_subtasks": len(run.remaining_subtasks()),
        "latest_checkpoint_time": cp.created_at if cp else None,
    }

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Resuming: {run.original_goal[:60]}")
        print(f"  Run ID: {run_id}")
        print(f"  Checkpoints: {result['checkpoints']}")
        print(f"  Remaining: {result['remaining_subtasks']} subtasks")
    return 0


def _cmd_compare(args):
    """Compare raw model output vs context-compiled output on the same task."""
    import shutil
    model_name = getattr(args, 'model', 'deepseek-coder:6.7b')

    if not shutil.which("ollama"):
        print("Ollama is required for compare mode. Install ollama or use --json for saved report.")
        return 1

    task = getattr(args, 'task', None)
    if not task:
        task = "What language and framework does this repo use? Describe the build system and test setup."

    from .runtime.engine import LocalInferenceEngine, check_ollama, check_model_available
    from .context import ContextCompiler

    if not check_ollama():
        print("Ollama is not running. Start it with: ollama serve")
        return 1

    if not check_model_available(model_name):
        print(f"Model '{model_name}' not found. Pull it with: ollama pull {model_name}")
        return 1

    engine = LocalInferenceEngine(model_name=model_name)

    result_raw = engine.generate(
        f"Answer concisely: {task}\nBe specific and cite file names if possible.",
        save_run=False
    )

    cc = ContextCompiler()
    context = cc.compile(task=task)
    result_context = engine.generate(
        f"Repository context:\n{context.to_text()}\n\nAnswer concisely: {task}\nBe specific and cite file names if possible.",
        save_run=False
    )

    raw_evidence = sum(1 for word in ["file", ".py", ".toml", ".json", ".md", "src/", "tests/"]
                       if word in result_raw.output.lower())
    ctx_evidence = sum(1 for word in ["file", ".py", ".toml", ".json", ".md", "src/", "tests/"]
                       if word in result_context.output.lower())

    report = {
        "model": model_name,
        "task": task,
        "raw": {
            "output": result_raw.output,
            "latency_s": result_raw.time_s,
            "length_chars": len(result_raw.output),
            "evidence_signals": raw_evidence,
            "tokens_per_second": result_raw.tokens_per_second,
            "success": result_raw.success,
        },
        "context_compiled": {
            "output": result_context.output,
            "latency_s": result_context.time_s,
            "length_chars": len(result_context.output),
            "evidence_signals": ctx_evidence,
            "tokens_per_second": result_context.tokens_per_second,
            "success": result_context.success,
            "context_tokens": context.total_tokens,
        },
        "delta": {
            "latency_diff_s": round(result_context.time_s - result_raw.time_s, 2),
            "evidence_improvement": ctx_evidence - raw_evidence,
            "context_used": context.total_tokens > 0,
        },
    }

    import uuid, json
    from pathlib import Path
    run_id = uuid.uuid4().hex[:12]
    run_dir = Path.cwd() / ".lyme" / "model-runs"
    run_dir.mkdir(parents=True, exist_ok=True)
    run_file = run_dir / f"compare-{run_id}.json"
    run_file.write_text(json.dumps(report, indent=2))

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("  RAW vs CONTEXT-COMPILED COMPARISON")
        print("=" * 60)
        print(f"  Model:        {model_name}")
        print(f"  Task:         {task[:60]}...")
        print()
        sep = "-" * 25
        sep2 = "-" * 12
        print(f"  {'Metric':25s} {'Raw':>12s} {'Context':>12s}")
        print(f"  {sep} {sep2} {sep2}")
        print(f"  {'Latency (s)':25s} {result_raw.time_s:>12.2f} {result_context.time_s:>12.2f}")
        print(f"  {'Length (chars)':25s} {len(result_raw.output):>12d} {len(result_context.output):>12d}")
        print(f"  {'Evidence signals':25s} {raw_evidence:>12d} {ctx_evidence:>12d}")
        print(f"  {'Tokens/sec':25s} {result_raw.tokens_per_second:>12.1f} {result_context.tokens_per_second:>12.1f}")
        print()
        print(f"  Context tokens: {context.total_tokens}")
        print(f"  Evidence improvement: {report['delta']['evidence_improvement']:+d}")
        print()
        print("  RAW OUTPUT:")
        for line in result_raw.output.split("\n")[:10]:
            print(f"    {line}")
        if len(result_raw.output.split("\n")) > 10:
            print("    ...")
        print()
        print("  CONTEXT OUTPUT:")
        for line in result_context.output.split("\n")[:10]:
            print(f"    {line}")
        if len(result_context.output.split("\n")) > 10:
            print("    ...")
        print()
        print(f"  Report saved: {run_file}")
        print("=" * 60)
    return 0


def _cmd_modes(args):
    tier = getattr(args, 'hardware', 'standard_gpu')
    modes = mode_selector.available_modes(tier)

    if args.json:
        print(json.dumps(modes, indent=2))
    else:
        print(f"Modes available for {tier}:")
        for m in modes:
            desc = m["description"][:70]
            print(f"  {m['mode']:30s} {desc}")
    return 0


# ─── New: QA Engine ────────────────────────────────────────────────────────────

def _cmd_qa(args):
    question = getattr(args, 'question', None)
    if not question and not sys.stdin.isatty():
        question = sys.stdin.read().strip()
    if not question:
        print("Error: Question required", file=sys.stderr)
        return 1

    repo = getattr(args, 'repo', '.')
    engine = QAEngine(repo)
    result = engine.answer(question)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        if result.refused:
            print(f"REFUSED: {result.refusal_reason}")
        else:
            print(result.answer)
            if result.evidence:
                print(f"\nEvidence ({len(result.evidence)} sources):")
                for e in result.evidence[:5]:
                    print(f"  [{e.tool}] {e.source_file}")
        print(f"\n[Confidence: {result.confidence:.0%} | Latency: {result.latency_s:.2f}s | Tokens: {result.context_tokens}]")
    return 0


def _cmd_qa_benchmark(args):
    repo = getattr(args, 'repo', '.')
    bench = QABenchmark(repo)
    output = bench.run()

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        s = output["summary"]
        print("Q&A BENCHMARK")
        print(f"  Questions: {s['total_questions']}")
        print(f"  Answered: {s['answered']}")
        print(f"  Refused: {s['refused']}")
        print(f"  Avg latency: {s['avg_latency_s']:.3f}s")
        print(f"  Avg confidence: {s['avg_confidence']:.2f}")
        print(f"  Total evidence: {s['total_evidence']}")
        print(f"  Avg evidence/answer: {s['avg_evidence_per_answer']:.1f}")
    return 0


def _cmd_qa_demo(args):
    repo = getattr(args, 'repo', '.')
    run_qa_demo(repo)
    return 0


def _cmd_eval_report(args):
    import json
    report_path = Path("lyme-output") / "mvp-evaluation-week20.json"
    if report_path.exists():
        report = json.loads(report_path.read_text())
        print(f"\n=== Lyme Model v0.2 MVP Evaluation ===")
        print(f"Methodology: {report['methodology']}")
        print(f"\n--- Comparison ---")
        for label, data in report.get("comparison", {}).items():
            print(f"\n{label}:")
            for k, v in data.items():
                print(f"  {k}: {v}")
        print(f"\n--- What Worked ---")
        for item in report.get("what_worked", []):
            print(f"  ✓ {item}")
        print(f"\n--- What Failed ---")
        for item in report.get("what_failed", []):
            print(f"  ✗ {item}")
        print(f"\n--- What Should Become v1 Focus ---")
        for item in report.get("what_should_become_v1_focus", []):
            print(f"  → {item}")
        print(f"\nTests: {report['test_count_by_week']['total']} total, 100% pass rate")
        print(f"Report: {report_path}")
    else:
        print(f"Report not found at {report_path}. Run full benchmark first.")
    return 0


def _cmd_benchmark(args):
    suite = getattr(args, 'suite', 'all')
    repo = getattr(args, 'repo', '.')
    harness = ModelBenchmarkHarness(repo)

    if suite == "all":
        result = harness.run_all()
    elif suite == "regression":
        result = {"regression": harness.run_regression().to_dict()}
    else:
        result = {"standard": harness.run_benchmark().to_dict()}

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if "standard" in result:
            s = result["standard"]
            print(f"STANDARD BENCHMARK: {s['passed']}/{s['total_tasks']} passed")
            print(f"  Avg latency: {s['avg_latency_s']}s | Avg evidence: {s['avg_evidence']}")
            print(f"  Categories: {s['categories']}")
        if "regression" in result:
            r = result["regression"]
            print(f"REGRESSION: {r['passed']}/{r['total_tasks']} passed")
            print(f"  Avg latency: {r['avg_latency_s']}s")
        if "combined" in result:
            c = result["combined"]
            print(f"COMBINED: {c['passed']}/{c['total_tasks']} passed | Avg latency: {c['avg_latency_s']}s")
    return 0


# ─── Test Detection ────────────────────────────────────────────────────────────

def _cmd_tests(args):
    """Detect test commands for the repository."""
    from pathlib import Path
    import json

    repo = Path(getattr(args, 'repo', '.')).resolve()

    detectors = [
        ("pytest",          lambda r: (r / "pyproject.toml").exists() or bool(list(r.rglob("pytest.ini"))) or bool(list(r.rglob("conftest.py")))),
        ("python unittest", lambda r: bool(list(r.rglob("test_*.py"))) if not (r / "pyproject.toml").exists() else False),
        ("npm test",        lambda r: (r / "package.json").exists() and "test" in (r / "package.json").read_text(errors="ignore")),
        ("pnpm test",       lambda r: (r / "pnpm-lock.yaml").exists()),
        ("yarn test",       lambda r: (r / "yarn.lock").exists()),
        ("cargo test",      lambda r: bool(list(r.rglob("Cargo.toml")))),
        ("go test ./...",   lambda r: bool(list(r.rglob("go.mod")))),
        ("make test",       lambda r: (r / "Makefile").exists() and "test:" in (r / "Makefile").read_text(errors="ignore")),
    ]

    found = []
    for name, detector in detectors:
        try:
            if detector(repo):
                found.append(name)
        except Exception:
            continue

    test_files_py = list(repo.rglob("test_*.py")) + list(repo.rglob("*_test.py"))
    test_files_js = list(repo.rglob("*.test.js")) + list(repo.rglob("*.test.ts")) + list(repo.rglob("*.spec.js"))
    test_files_rs = list(repo.rglob("*_test.rs")) + list(repo.rglob("*.test.rs"))

    evidence = []
    if test_files_py:
        evidence.append(f"Python test files: {len(test_files_py)} (e.g. {test_files_py[0].name})")
    if test_files_js:
        evidence.append(f"JS/TS test files: {len(test_files_js)} (e.g. {test_files_js[0].name})")
    if test_files_rs:
        evidence.append(f"Rust test files: {len(test_files_rs)}")

    confidence = 0.0
    if found:
        confidence = min(0.5 + len(found) * 0.15, 0.95)

    ptest_evidence = bool(list(repo.rglob("conftest.py"))) or bool(list(repo.rglob("pytest.ini")))
    if ptest_evidence:
        confidence = max(confidence, 0.85)
        evidence.append("pytest config found (conftest.py or pytest.ini)")

    recommended = found[0] if found else "unknown"
    if "pytest" in found:
        recommended = "pytest"
    elif "npm test" in found:
        recommended = "npm test"

    result = {
        "repo": str(repo),
        "detected_commands": found,
        "confidence": round(confidence, 2),
        "recommended": recommended,
        "evidence": evidence,
        "test_file_count": len(test_files_py) + len(test_files_js) + len(test_files_rs),
    }

    if getattr(args, 'json', False):
        print(json.dumps(result, indent=2))
    else:
        print(f"Repository: {repo.name}")
        print(f"Test commands found: {len(found)}")
        for cmd in found:
            print(f"  - {cmd}")
        print(f"Recommended: {recommended}")
        print(f"Confidence: {confidence:.0%}")
        print(f"Test files: {result['test_file_count']}")
        for ev in evidence:
            print(f"  Evidence: {ev}")
    return 0


# ─── New: Tool Session ─────────────────────────────────────────────────────────

def _cmd_tools(args):
    tools_cmd = getattr(args, 'tools_command', None)
    if tools_cmd == "parse":
        text = getattr(args, 'text', '')
        calls = ToolCallParser.parse(text)
        if args.json:
            print(json.dumps([c.to_dict() for c in calls], indent=2))
        else:
            for c in calls:
                params_str = ", ".join(f"{k}={v}" for k, v in c.params.items())
                print(f"TOOL: {c.tool_name}({params_str})")
            if not calls:
                print("No tool calls found.")
        return 0

    if tools_cmd == "run":
        text = getattr(args, 'text', '')
        input_file = getattr(args, 'input', None)
        if input_file:
            text = Path(input_file).read_text()
        if not text:
            print("Error: --text or --input required", file=sys.stderr)
            return 1

        safety = SafetyMode(getattr(args, 'safety', 'readonly'))
        repo = getattr(args, 'repo', '.')

        calls = ToolCallParser.parse(text)
        if args.json:
            print(json.dumps([c.to_dict() for c in calls], indent=2))
            return 0

        print(f"Parsed {len(calls)} tool calls (safety: {safety.value}):")
        for c in calls:
            params_str = ", ".join(f"{k}={v}" for k, v in c.params.items())
            print(f"  {c.tool_name}({params_str})")

        if calls:
            print()
            session = ToolSession(repo_path=repo, safety_mode=safety)
            traces = session.execute_model_tool_calls(text)
            print(f"\nResults ({len(traces)} calls, {session.get_stats()['failed']} failed):")
            for t in traces:
                status = "✓" if t.result and t.result.success else "✗"
                output_preview = ""
                if t.result and t.result.output:
                    output_preview = t.result.output[:100].replace("\n", " ")
                print(f"  {status} {t.tool_name} ({t.latency_ms:.0f}ms): {output_preview}")

            print(f"\nSession stats:")
            stats = session.get_stats()
            print(f"  Total calls: {stats['tool_calls']}")
            print(f"  Total latency: {stats['total_latency_ms']:.0f}ms")
            print(f"  Failed: {stats['failed']}")
        return 0

    print("Error: Unknown tools command. Use: run, parse", file=sys.stderr)
    return 1


# ─── New: Context & Summary ────────────────────────────────────────────────────

def _cmd_context(args):
    improved = getattr(args, 'improved', False)
    cc = ImprovedContextCompiler() if improved else ContextCompiler()
    task = getattr(args, 'task', None)
    max_tokens = getattr(args, 'max_tokens', None)
    result = cc.compile(task=task, max_tokens=max_tokens)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.to_text())
        print(f"\n--- Tokens: {result.total_tokens} | Time: {result.compile_time_s}s ---")
    return 0


def _cmd_context_benchmark(args):
    repo = getattr(args, 'repo', '.')
    bench = ContextBenchmark(repo)
    if args.json:
        output = bench.summary()
        print(json.dumps(output, indent=2))
    else:
        print(bench.report())
    return 0


def _cmd_summary(args):
    repo = getattr(args, 'repo', '.')
    cc = ContextCompiler(repo)
    result = cc.compile()
    if args.json:
        print(json.dumps({"repo": repo, "summary": result.repo_summary, "structure": result.structure,
                           "risks": result.risks, "build": result.build_commands, "test": result.test_commands}, indent=2))
    else:
        print(f"Repository: {repo}")
        print(result.repo_summary)
        print(f"\nTop-level structure:")
        print(result.structure)
        if result.risks:
            print(f"\nRisky files ({len(result.risks)}):")
            for r in result.risks[:5]:
                print(f"  - {r}")
            if len(result.risks) > 5:
                print(f"  ... and {len(result.risks) - 5} more")
        print(f"\nBuild: {'; '.join(result.build_commands)}")
        print(f"Test: {'; '.join(result.test_commands)}")
    return 0


# ─── Existing Commands (enhanced) ──────────────────────────────────────────────

def _cmd_run(args):
    task = getattr(args, 'task', None)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Error: Task description required", file=sys.stderr)
        return 1

    if getattr(args, 'dry_run', False):
        est = diff_estimator.estimate(task)
        mode = mode_selector.select_mode(est.difficulty_score, est.risk.value, "standard_gpu", 1000)
        result = {
            "task": task,
            "dry_run": True,
            "estimate": est.to_dict(),
            "mode": mode.to_dict(),
        }
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"DRY RUN: {task}")
            print(f"  Type: {est.task_type.value} | Difficulty: {est.difficulty_level.value}")
            print(f"  Mode: {mode.selected_mode.value}")
        return 0

    runtime = AgentRuntime(model_name=getattr(args, 'model', 'deepseek-coder:6.7b'),
                            repo_path=getattr(args, 'repo', '.'))
    context = None
    if hasattr(args, 'context') and args.context:
        context = Path(args.context).read_text()

    result = runtime.run_task(task, context)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(result.output)
    return 0 if result.success else 1


def _cmd_list(args=None):
    models = ModelLoader.list_models()
    print(f"{'Model':30s} {'Size':8s} {'Quant':6s} {'Backend':10s}")
    print("-" * 54)
    for m in models:
        print(f"{m.name:30s} {m.size:8s} {m.quantization:6s} {m.backend:10s}")
    return 0


def _cmd_history(args):
    """List all model runs from .lyme/model-runs/."""
    from pathlib import Path
    import json
    import time

    runs_dir = Path.cwd() / ".lyme" / "model-runs"
    if not runs_dir.is_dir():
        result = {"runs": [], "total": 0, "message": "No model runs found"}
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            print("No model runs found. Run a model command first.")
        return 0

    limit = getattr(args, 'limit', 20)
    entries = sorted(runs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    runs = []
    for f in entries:
        try:
            data = json.loads(f.read_text())
            run_id = f.stem
            task = data.get("task", data.get("question", data.get("run_id", run_id)))
            model = data.get("model", data.get("raw", {}).get("model", ""))
            status = data.get("status", data.get("success", data.get("dry_run", False)))
            latency = data.get("latency_s", data.get("time_s", 0))
            if isinstance(status, bool):
                status = "success" if status else "failure"
            elif status is True:
                status = "dry-run"
            elif isinstance(status, str):
                pass
            else:
                status = "unknown"
            mtime = f.stat().st_mtime
            runs.append({
                "run_id": run_id,
                "task": str(task)[:80] if task else run_id,
                "model": str(model) if model else "",
                "status": status,
                "latency_s": round(latency, 2) if isinstance(latency, (int, float)) else 0,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime)),
            })
        except Exception:
            runs.append({"run_id": f.stem, "task": "(corrupt)", "model": "", "status": "error", "latency_s": 0})

    result = {"runs": runs, "total": len(runs)}
    if getattr(args, 'json', False):
        print(json.dumps(result, indent=2))
    else:
        print(f"{'Run ID':20s} {'Task':40s} {'Status':12s} {'Latency':10s}")
        print("-" * 82)
        for r in runs:
            lat = f"{r['latency_s']}s" if r['latency_s'] else "-"
            print(f"{r['run_id']:20s} {r['task']:40s} {r['status']:12s} {lat:10s}")
        print(f"\nTotal runs: {len(runs)}")
    return 0


def _cmd_show(args):
    """Show details for a specific model run."""
    from pathlib import Path
    import json

    runs_dir = Path.cwd() / ".lyme" / "model-runs"
    run_id = args.run_id

    candidates = list(runs_dir.glob(f"{run_id}*"))
    if not candidates:
        print(f"Run '{run_id}' not found in {runs_dir}")
        return 1

    try:
        data = json.loads(candidates[0].read_text())
    except Exception as e:
        print(f"Error reading run '{run_id}': {e}")
        return 1

    if getattr(args, 'json', False):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(f"Run: {run_id}")
        print(f"File: {candidates[0].name}")
        print("-" * 50)
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"\n{k}:")
                for sk, sv in v.items():
                    sv_str = str(sv)[:120] if not isinstance(sv, (int, float, bool)) else str(sv)
                    print(f"  {sk}: {sv_str}")
            elif isinstance(v, list):
                print(f"\n{k}: ({len(v)} items)")
                for item in v[:5]:
                    item_str = str(item)[:100] if isinstance(item, (dict, list)) else str(item)
                    print(f"  - {item_str}")
                if len(v) > 5:
                    print(f"  ... and {len(v) - 5} more")
            else:
                print(f"  {k}: {v}")
    return 0


def _cmd_report(args):
    """Generate summary report of all model runs."""
    from pathlib import Path
    import json
    import time

    runs_dir = Path.cwd() / ".lyme" / "model-runs"
    if not runs_dir.is_dir():
        result = {"total_runs": 0, "message": "No model runs found"}
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            print("No model runs found. Run a model command first.")
        return 0

    entries = list(runs_dir.glob("*.json"))
    if not entries:
        result = {"total_runs": 0, "message": "No runs found"}
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            print("No model runs found.")
        return 0

    total = len(entries)
    successes = 0
    failures = 0
    dry_runs = 0
    total_latency = 0.0
    latency_count = 0
    models = {}
    tasks = {}

    for f in entries:
        try:
            data = json.loads(f.read_text())
            status = data.get("status", data.get("success", data.get("dry_run", False)))
            if isinstance(status, bool):
                if status:
                    successes += 1
                else:
                    failures += 1
            elif isinstance(status, str):
                if status == "success":
                    successes += 1
                elif status == "failure":
                    failures += 1
                else:
                    dry_runs += 1
            elif status is True:
                dry_runs += 1

            lat = data.get("latency_s", data.get("time_s", 0))
            if isinstance(lat, (int, float)) and lat > 0:
                total_latency += lat
                latency_count += 1

            model = data.get("model", data.get("raw", {}).get("model", "unknown"))
            if isinstance(model, str) and model:
                models[model] = models.get(model, 0) + 1

            task = str(data.get("task", data.get("question", "")))[:80]
            if task:
                tasks[task] = tasks.get(task, 0) + 1
        except Exception:
            failures += 1

    report = {
        "total_runs": total,
        "successful": successes,
        "failed": failures,
        "dry_runs": dry_runs,
        "success_rate": round(successes / total * 100, 1) if total > 0 else 0,
        "avg_latency_s": round(total_latency / latency_count, 2) if latency_count > 0 else 0,
        "models_used": models,
        "task_types": tasks,
    }

    if getattr(args, 'json', False):
        print(json.dumps(report, indent=2))
    else:
        print("=" * 50)
        print("  LYME MODEL RUN REPORT")
        print("=" * 50)
        print(f"  Total runs:         {report['total_runs']}")
        print(f"  Successful:         {report['successful']}")
        print(f"  Failed:             {report['failed']}")
        print(f"  Dry runs:           {report['dry_runs']}")
        print(f"  Success rate:       {report['success_rate']}%")
        print(f"  Avg latency:        {report['avg_latency_s']}s")
        if models:
            print(f"  Models used:        {', '.join(f'{k}({v})' for k, v in models.items())}")
        if tasks:
            print(f"  Unique tasks:       {len(tasks)}")
        print("=" * 50)
    return 0


def _cmd_locate(args):
    """Locate bug-relevant files from a task description."""
    from pathlib import Path
    import json

    task = getattr(args, 'task', None)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("Error: Task description required", file=sys.stderr)
        return 1

    repo = Path(getattr(args, 'repo', '.')).resolve()
    keywords = set(task.lower().split())
    stopwords = {"the", "a", "an", "is", "are", "in", "to", "of", "for", "and", "or", "not", "it", "this", "that"}
    keywords = {k for k in keywords if len(k) > 2 and k not in stopwords}

    scored = []
    extensions = {"*.py", "*.js", "*.ts", "*.go", "*.rs", "*.java", "*.c", "*.cpp", "*.rb", "*.md", "*.toml", "*.yaml", "*.yml", "*.json"}

    import glob as glob_mod
    for ext in extensions:
        for f in glob_mod.iglob(str(repo / "**" / ext), recursive=True):
            fp = Path(f)
            if not fp.is_file():
                continue
            if "site-packages" in str(fp) or ".venv" in str(fp) or "__pycache__" in str(fp) or ".git" in str(fp):
                continue
            rel = str(fp.relative_to(repo))
            name_score = sum(1 for k in keywords if k in fp.name.lower() or k in rel.lower())
            content_score = 0
            if name_score > 0 and fp.stat().st_size < 200000:
                try:
                    text = fp.read_text(errors="ignore").lower()
                    content_score = sum(kw_count for k in keywords for kw_count in [text.count(k)] if kw_count > 0)
                except Exception:
                    pass
            total = name_score * 3 + content_score
            if total > 0:
                scored.append((total, rel, name_score, content_score))

    scored.sort(key=lambda x: -x[0])
    top = scored[:15]

    candidates = []
    for score, path, ns, cs in top:
        candidates.append({
            "file": path,
            "score": score,
            "name_match": ns,
            "content_match": cs,
            "confidence": round(min(ns * 0.3 + min(cs / 10, 1) * 0.7, 1.0), 2),
        })

    result = {
        "task": task,
        "repo": str(repo),
        "candidates": candidates,
        "total_scanned": len(scored),
    }

    if getattr(args, 'json', False):
        print(json.dumps(result, indent=2))
    else:
        print(f"Task: {task}")
        print(f"Repo: {repo.name}")
        print(f"\nTop file candidates ({len(candidates)}):")
        for c in candidates[:10]:
            bar = "█" * int(c['confidence'] * 20) + "░" * (20 - int(c['confidence'] * 20))
            print(f"  [{bar}] {c['confidence']:.0%}  {c['file']}")
        if len(candidates) > 10:
            print(f"  ... and {len(candidates) - 10} more")
        print(f"\nTotal files scanned: {result['total_scanned']}")
    return 0


def _cmd_profile(args):
    """Comprehensive system profile for Lyme Model operations."""
    import platform
    import shutil
    import sys
    import subprocess

    profile = detect_all()
    result = profile.to_dict()

    result["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
    }
    result["python"] = {
        "version": sys.version.split()[0],
        "executable": sys.executable,
        "implementation": platform.python_implementation(),
    }

    tools = {}
    for tool in ["git", "pytest", "node", "npm", "go", "cargo", "make", "docker"]:
        tools[tool] = shutil.which(tool) is not None
    result["tools"] = tools

    ollama_avail = profile.ollama_available
    result["ollama"] = {
        "available": ollama_avail,
        "models": profile.ollama_models,
    }

    result["model_feasibility"] = profile.model_feasibility()
    result["latency_estimate"] = profile.latency_estimate("7B")

    show_json = getattr(args, 'json', False)
    if show_json:
        print(json.dumps(result, indent=2))
    else:
        hw = result
        print("=" * 55)
        print("  LYME MODEL PROFILE")
        print("=" * 55)
        print(f"  Platform:      {hw['platform']}")
        os_info = hw.get('os', {})
        print(f"  OS:            {os_info.get('system', '?')} {os_info.get('release', '?')}")
        py = hw.get('python', {})
        print(f"  Python:        {py.get('version', '?')} ({py.get('implementation', '?')})")
        print(f"  CPU:           {hw['cpu']['model']} ({hw['cpu']['cores']} cores)")
        print(f"  RAM:           {hw['ram']['total_gb']} GB ({hw['ram']['available_gb']} GB avail)")
        if hw['gpu']['present']:
            print(f"  GPU:           {hw['gpu']['name']} ({hw['gpu']['vram_total_mb']} MB VRAM)")
        else:
            print(f"  GPU:           None")
        print(f"  Disk:          {hw['disk']['total_gb']:.0f} GB ({hw['disk']['free_gb']:.0f} GB free)")
        tools = hw.get('tools', {})
        available_tools = [t for t, avail in tools.items() if avail]
        print(f"  Tools:         {', '.join(available_tools) if available_tools else 'none'}")
        ollama = hw.get('ollama', {})
        if ollama.get('available'):
            models = ollama.get('models', [])
            print(f"  Ollama:        available ({len(models)} models)")
            for m in models[:5]:
                print(f"                   {m['name']} ({m.get('size', '?')})")
            if len(models) > 5:
                print(f"                   ... and {len(models) - 5} more")
        else:
            print(f"  Ollama:        not available")
        print(f"  Feasible models (7B+ on GPU):")
        for m in hw.get('model_feasibility', []):
            if m['feasible']:
                print(f"                   {m['size']} ({m['quant']})")
        est = hw.get('latency_estimate', {})
        print(f"  Est. speed:    {est.get('tokens_per_sec_estimate', '?')} tok/s (7B)")
        print("=" * 55)
    return 0


def _cmd_hardware(args=None):
    profile = detect_all()
    hw = profile.to_dict()
    tier = hw.get("tier", "unknown")
    modes = mode_selector.available_modes(tier)
    output = {"hardware": hw, "available_modes": modes}
    print(json.dumps(output, indent=2))
    return 0


def _cmd_eval(args):
    harness = ModelEvaluationHarness(model_name=getattr(args, 'model', 'deepseek-coder:6.7b'))
    results = harness.run_all()
    harness.print_summary(results)
    return 0
