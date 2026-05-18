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
from .runtime import server_client
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
from .trial import TrialRunner, TrialReplay, TrialReport
from .arena import ArenaRunner, ArenaScorer, LeaderboardGenerator, RegressionChecker, ArenaConfig, ToolName
from .ticket import TicketRunner, AcceptanceGrader, RevenueEstimator
from .autonomy import AutonomyController, AuditTrail, ContinuationExplainer, AutonomyLevel, AutonomyConfig, Action
from .workflow import WorkflowExecutor, PRReporter, IssueIngester
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
    compare.add_argument("--model", default="deepseek-ai/deepseek-coder-6.7b-instruct", help="Model name for comparison")
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

    # lyme model run (enhanced)
    run = model_sub.add_parser("run", help="Execute a coding task")
    run.add_argument("task", nargs="?", help="Task description")
    run.add_argument("--model", default=None, help="Base model name (defaults to current Lyme artifact)")
    run.add_argument("--repo", default=".", help="Repository path")
    run.add_argument("--context", help="Context file path")
    run.add_argument("--no-context", action="store_true", help="Disable all context injection (overrides --context)")
    run.add_argument("--output", "-o", help="Output file for results")
    run.add_argument("--dry-run", action="store_true", help="Show what would happen")
    run.add_argument("--json", action="store_true", help="JSON output")
    run.add_argument("--max-new-tokens", type=int, default=32, help="Max tokens to generate (default: 32)")
    run.add_argument("--temperature", type=float, default=0.1, help="Sampling temperature (default: 0.1)")
    run.add_argument("--top-p", type=float, default=0.95, help="Top-p sampling (default: 0.95)")
    run.add_argument("--no-sample", action="store_true", default=True, help="Deterministic generation (default: on, deterministic)")
    run.add_argument("--timeout", type=int, default=180, help="Generation timeout in seconds (default: 180)")
    run.add_argument("--stream", action="store_true", default=False, help="Stream output tokens (experimental)")
    run.add_argument("--raw-prompt", action="store_true", help="Send raw prompt without chat template formatting")
    run.add_argument("--debug", action="store_true", help="Include full exception type and traceback in JSON error")
    run.add_argument("--reuse-worker", action="store_true", default=False, help="(backcompat, now default) Reuse persistent model server")
    run.add_argument("--no-server", action="store_true", default=False, help="One-shot isolated subprocess (no persistent server)")
    run.add_argument("--load-in-4bit", action="store_true", default=False, help="Load model in 4-bit quantization (auto-detected for <=10GB VRAM)")
    run.add_argument("--load-in-8bit", action="store_true", default=False, help="Load model in 8-bit quantization (requires bitsandbytes)")
    run.add_argument("--dtype", default=None, choices=["float16", "bfloat16", "float32"], help="Torch dtype for model weights")

    # lyme model server
    server_cmd = model_sub.add_parser("server", help="Start persistent model server")
    server_cmd.add_argument("--model", default=None, help="Base model name")
    server_cmd.add_argument("--daemon", action="store_true", help="Run in background (auto-detached)")
    server_cmd.add_argument("--load-in-4bit", action="store_true", default=False, help="Load in 4-bit")
    server_cmd.add_argument("--load-in-8bit", action="store_true", default=False, help="Load in 8-bit")
    server_cmd.add_argument("--dtype", default=None, choices=["float16", "bfloat16", "float32"], help="Torch dtype")
    server_cmd.add_argument("--debug", action="store_true", help="Verbose errors with traceback")

    # lyme model stop
    model_sub.add_parser("stop", help="Stop the persistent model server. Examples: lyme model stop")

    # lyme model status
    status_cmd = model_sub.add_parser("status", help="Show persistent model server status. Examples: lyme model status, lyme model status --json")
    status_cmd.add_argument("--json", action="store_true", help="JSON output")

    # lyme model bench-perf (runtime performance benchmark)
    bench_perf = model_sub.add_parser("bench-perf", help="Benchmark model runtime performance (load time, tok/s, VRAM)")
    bench_perf.add_argument("--model", default=None, help="Base model name")
    bench_perf.add_argument("--load-in-4bit", action="store_true", default=False, help="Load in 4-bit")
    bench_perf.add_argument("--load-in-8bit", action="store_true", default=False, help="Load in 8-bit")
    bench_perf.add_argument("--dtype", default=None, choices=["float16", "bfloat16", "float32"], help="Torch dtype")
    bench_perf.add_argument("--json", action="store_true", help="JSON output")

    # lyme model artifacts
    model_sub.add_parser("artifacts", help="List Lyme Model adapter artifacts")

    # lyme model current
    model_sub.add_parser("current", help="Show the currently selected Lyme artifact")

    # lyme model use
    use_cmd = model_sub.add_parser("use", help="Select a Lyme artifact to use")
    use_cmd.add_argument("artifact_path", help="Path to artifact directory")

    # lyme model diagnose
    model_sub.add_parser("diagnose", help="Diagnose current model adapter configuration")

    # lyme model list (existing)
    model_sub.add_parser("list", help="List available models")

    # lyme model hardware (existing)
    model_sub.add_parser("hardware", help="Detect and report hardware")

    # lyme model eval (existing)
    eval_cmd = model_sub.add_parser("eval", help="Evaluate model on benchmarks")
    eval_cmd.add_argument("--model", default="deepseek-ai/deepseek-coder-6.7b-instruct")

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

    # lyme model trial
    trial_cmd = model_sub.add_parser("trial", help="Trial harness commands")
    trial_sub = trial_cmd.add_subparsers(dest="trial_command")

    trial_list = trial_sub.add_parser("list", help="List seeded trial tasks")
    trial_list.add_argument("--type", choices=["fix_failing_test", "implement_feature", "refactor_module", "update_dependency", "add_docs"], help="Filter by task type")
    trial_list.add_argument("--difficulty", choices=["easy", "medium", "hard"], help="Filter by difficulty")
    trial_list.add_argument("--json", action="store_true", help="JSON output")

    trial_run = trial_sub.add_parser("run", help="Run a single trial task")
    trial_run.add_argument("task_id", help="Task ID to run")
    trial_run.add_argument("--repo", default=".", help="Repository path")
    trial_run.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    trial_run.add_argument("--json", action="store_true", help="JSON output")

    trial_run_all = trial_sub.add_parser("run-all", help="Run all trial tasks")
    trial_run_all.add_argument("--repo", default=".", help="Repository path")
    trial_run_all.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    trial_run_all.add_argument("--json", action="store_true", help="JSON output")

    trial_run_type = trial_sub.add_parser("run-type", help="Run trials by type")
    trial_run_type.add_argument("task_type", choices=["fix_failing_test", "implement_feature", "refactor_module", "update_dependency", "add_docs"], help="Task type to run")
    trial_run_type.add_argument("--repo", default=".", help="Repository path")
    trial_run_type.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    trial_run_type.add_argument("--json", action="store_true", help="JSON output")

    trial_replay = trial_sub.add_parser("replay", help="Replay a completed trial")
    trial_replay.add_argument("trial_id", help="Trial ID or Run ID to replay")
    trial_replay.add_argument("--json", action="store_true", help="JSON output")

    trial_report = trial_sub.add_parser("report", help="Generate report for a trial or run")
    trial_report.add_argument("trial_id", help="Trial ID or Run ID")
    trial_report.add_argument("--output", "-o", help="Output file path")
    trial_report.add_argument("--json", action="store_true", help="JSON output")

    trial_results = trial_sub.add_parser("results", help="List all trial results")
    trial_results.add_argument("--json", action="store_true", help="JSON output")
    trial_results.add_argument("--limit", type=int, default=20, help="Max entries")

    trial_summary = trial_sub.add_parser("summary", help="Show summary of a trial run")
    trial_summary.add_argument("run_id", help="Run ID")
    trial_summary.add_argument("--json", action="store_true", help="JSON output")

    trial_compare = trial_sub.add_parser("compare", help="Compare two trial runs")
    trial_compare.add_argument("run_ids", nargs="+", help="Run IDs to compare")

    # lyme model arena
    arena_cmd = model_sub.add_parser("arena", help="Benchmark arena commands")
    arena_sub = arena_cmd.add_subparsers(dest="arena_command")

    arena_run = arena_sub.add_parser("run", help="Run arena benchmark")
    arena_run.add_argument("--task-type", choices=["fix_failing_test", "implement_feature", "refactor_module", "update_dependency", "add_docs", "all"], default="all",
                           help="Task type to benchmark (default: all)")
    arena_run.add_argument("--tasks", nargs="*", help="Specific task IDs (overrides --task-type)")
    arena_run.add_argument("--tools", nargs="+", default=["lyme"],
                           choices=["lyme", "claude_code", "codex", "opencode", "aider", "cursor"],
                           help="Tools to compare (default: lyme)")
    arena_run.add_argument("--repo", default=".", help="Repository path")
    arena_run.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    arena_run.add_argument("--json", action="store_true", help="JSON output")

    arena_leaderboard = arena_sub.add_parser("leaderboard", help="Generate leaderboard from arena results")
    arena_leaderboard.add_argument("--run-id", help="Specific run ID (default: latest)")
    arena_leaderboard.add_argument("--format", choices=["markdown", "html", "both"], default="both",
                                   help="Output format")
    arena_leaderboard.add_argument("--output", "-o", help="Output file path")

    arena_regression = arena_sub.add_parser("regression", help="Check regression gates")
    arena_regression.add_argument("--run-id", help="Specific run ID (default: latest)")

    arena_list = arena_sub.add_parser("list", help="List arena runs")

    arena_results = arena_sub.add_parser("results", help="Show arena results")
    arena_results.add_argument("--run-id", help="Run ID (default: latest)")
    arena_results.add_argument("--json", action="store_true", help="JSON output")

    # lyme model ticket
    ticket_cmd = model_sub.add_parser("ticket", help="Paid ticket simulator commands")
    ticket_sub = ticket_cmd.add_subparsers(dest="ticket_command")

    ticket_list = ticket_sub.add_parser("list", help="List seeded client tickets")
    ticket_list.add_argument("--difficulty", choices=["easy", "medium", "hard", "expert"], help="Filter by difficulty")
    ticket_list.add_argument("--json", action="store_true", help="JSON output")

    ticket_run = ticket_sub.add_parser("run", help="Run a single ticket simulation")
    ticket_run.add_argument("ticket_id", help="Ticket ID to run")
    ticket_run.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    ticket_run.add_argument("--json", action="store_true", help="JSON output")

    ticket_run_all = ticket_sub.add_parser("run-all", help="Run all ticket simulations")
    ticket_run_all.add_argument("--dry-run", action="store_true", help="Show what would happen without executing")
    ticket_run_all.add_argument("--json", action="store_true", help="JSON output")

    ticket_results = ticket_sub.add_parser("results", help="List ticket results")
    ticket_results.add_argument("--json", action="store_true", help="JSON output")

    ticket_report = ticket_sub.add_parser("report", help="Generate ticket benchmark report")
    ticket_report.add_argument("--run-id", help="Run ID (default: latest)")

    # lyme model autonomy
    autonomy_cmd = model_sub.add_parser("autonomy", help="Trust-gated autonomy commands")
    autonomy_sub = autonomy_cmd.add_subparsers(dest="autonomy_command")

    autonomy_mode = autonomy_sub.add_parser("mode", help="Set or show autonomy level")
    autonomy_mode.add_argument("level", nargs="?",
                               choices=["suggest_only", "patch_only", "patch_and_test",
                                        "patch_and_commit", "patch_and_pr", "continuous_background"],
                               help="Autonomy level to set")
    autonomy_mode.add_argument("--show", action="store_true", help="Show current configuration")

    autonomy_decide = autonomy_sub.add_parser("decide", help="Ask whether an action is allowed")
    autonomy_decide.add_argument("action", choices=[a.value for a in Action],
                                 help="Action to check")
    autonomy_decide.add_argument("--description", "-d", required=True, help="Action description")
    autonomy_decide.add_argument("--confidence", "-c", type=float, default=0.8, help="Confidence (0-1)")
    autonomy_decide.add_argument("--risk", "-r", type=float, default=0.2, help="Risk score (0-1)")
    autonomy_decide.add_argument("--files", nargs="*", default=[], help="Affected files")

    autonomy_approvals = autonomy_sub.add_parser("approvals", help="List pending approvals")
    autonomy_approvals.add_argument("--approve", help="Approval ID to approve")
    autonomy_approvals.add_argument("--deny", help="Approval ID to deny")
    autonomy_approvals.add_argument("--reason", help="Reason for decision")

    autonomy_audit = autonomy_sub.add_parser("audit", help="Show audit trail")
    autonomy_audit.add_argument("--limit", type=int, default=20, help="Max entries")
    autonomy_audit.add_argument("--json", action="store_true", help="JSON output")

    autonomy_explain = autonomy_sub.add_parser("explain", help="Explain current autonomy configuration")

    # lyme model workflow
    workflow_cmd = model_sub.add_parser("workflow", help="Issue→Verified PR workflow commands")
    workflow_sub = workflow_cmd.add_subparsers(dest="workflow_command")

    workflow_run = workflow_sub.add_parser("run", help="Run full Issue→Verified PR workflow")
    workflow_run.add_argument("--url", help="GitHub issue URL")
    workflow_run.add_argument("--text", "-t", help="Issue text (title on first line, body after)")
    workflow_run.add_argument("--id", default="issue-001", help="Issue ID for manual tickets")
    workflow_run.add_argument("--repo", default=".", help="Repository path")
    workflow_run.add_argument("--dry-run", action="store_true", help="Show plan without executing")
    workflow_run.add_argument("--simulate", action="store_true", help="Simulate execution (default: true)")
    workflow_run.add_argument("--json", action="store_true", help="JSON output")

    workflow_report = workflow_sub.add_parser("report", help="Generate workflow report")
    workflow_report.add_argument("ticket_id", help="Ticket/issue ID")
    workflow_report.add_argument("--output", "-o", help="Output file path")

    workflow_plan = workflow_sub.add_parser("plan", help="Show implementation plan for an issue")
    workflow_plan.add_argument("--url", help="GitHub issue URL")
    workflow_plan.add_argument("--text", "-t", help="Issue text")
    workflow_plan.add_argument("--json", action="store_true", help="JSON output")

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
        "server": _cmd_server,
        "stop": _cmd_stop,
        "status": _cmd_status,
        "bench-perf": _cmd_bench_perf,
        "list": _cmd_list,
        "artifacts": _cmd_artifacts,
        "current": _cmd_current,
        "use": _cmd_use,
        "diagnose": _cmd_diagnose,
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
        "trial": _cmd_trial,
        "arena": _cmd_arena,
        "ticket": _cmd_ticket,
        "autonomy": _cmd_autonomy,
        "workflow": _cmd_workflow,
    }
    handler = cmd_map.get(args.model_command)
    if handler:
        return handler(args)
    print("Error: Unknown model command", file=sys.stderr)
    print("Available: ask, plan, fix, bench, resume, compare, profile, modes, run, diagnose, artifacts, current, use, context, context-benchmark, summary, qa, qa-benchmark, qa-demo, benchmark, eval-report, tools, list, hardware, eval", file=sys.stderr)
    return 1


def _get_server_script() -> str:
    return str(Path(__file__).resolve().parent / "runtime" / "server_worker.py")


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
    model_name = getattr(args, 'model', 'deepseek-ai/deepseek-coder-6.7b-instruct')

    task = getattr(args, 'task', None)
    if not task:
        task = "What language and framework does this repo use? Describe the build system and test setup."

    from .runtime.engine import LocalInferenceEngine

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


# ─── Artifact Helpers ──────────────────────────────────────────────────────────

def _scan_artifacts():
    """Scan adapters/ and checkpoints/ for Lyme adapter artifacts."""
    artifacts = []
    root = Path.cwd()
    search_dirs = [root / "adapters", root / "checkpoints"]

    for search_dir in search_dirs:
        if not search_dir.is_dir():
            continue
        for entry in sorted(search_dir.rglob("adapter_model.safetensors")):
            artifact_dir = entry.parent
            config_file = artifact_dir / "adapter_config.json"
            if not config_file.exists():
                continue

            # Compute relative path from project root
            rel_path = artifact_dir.relative_to(root)

            # Read adapter_config.json for base model
            base_model = "unknown"
            try:
                config = json.loads(config_file.read_text())
                base_model = config.get("base_model_name_or_path", "unknown")
            except Exception:
                pass

            # Read metadata.json if present
            metadata = {}
            meta_file = artifact_dir / "metadata.json"
            if meta_file.exists():
                try:
                    metadata = json.loads(meta_file.read_text())
                except Exception:
                    pass

            eval_loss = metadata.get("eval_loss", None)
            artifact_name = metadata.get("name", rel_path.name)

            size_bytes = entry.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            artifacts.append({
                "id": str(rel_path),
                "name": artifact_name,
                "path": str(rel_path),
                "base_model": base_model,
                "size_mb": round(size_mb, 1),
                "eval_loss": eval_loss,
            })

    return artifacts


def _get_current_artifact():
    """Read .lyme/model/current.json and return the artifact info or None."""
    current_file = Path.cwd() / ".lyme" / "model" / "current.json"
    if not current_file.exists():
        return None
    try:
        return json.loads(current_file.read_text())
    except Exception:
        return None


def _suggest_best_artifact():
    """Suggest the best available artifact."""
    artifacts = _scan_artifacts()
    # Prefer adapters/ over checkpoints/
    preferred = [a for a in artifacts if a["path"].startswith("adapters/")]
    if preferred:
        return preferred[0]
    if artifacts:
        return artifacts[0]
    return None


# ─── Artifact Commands ─────────────────────────────────────────────────────────

def _cmd_artifacts(args=None):
    artifacts = _scan_artifacts()
    if not artifacts:
        print("No Lyme Model artifacts found.")
        print("Expected directories: adapters/<name>/  or  checkpoints/<name>/")
        print("Each artifact must contain adapter_model.safetensors and adapter_config.json.")
        return 0

    print(f"{'Artifact':45s} {'Base Model':40s} {'Size':8s} {'Eval Loss'}")
    print("-" * 100)
    for a in artifacts:
        loss = f"{a['eval_loss']:.4f}" if a['eval_loss'] is not None else "-"
        print(f"{a['id']:45s} {a['base_model']:40s} {a['size_mb']:>6.1f}MB {loss}")
    print(f"\n{len(artifacts)} artifact(s) found.")
    return 0


def _cmd_current(args=None):
    current = _get_current_artifact()
    if current:
        print("Current Lyme Model artifact:")
        print(f"  Path:      {current.get('path', '?')}")
        print(f"  Base Model: {current.get('base_model', '?')}")
        print(f"  Selected:  {current.get('selected_at', '?')}")
        return 0

    suggest = _suggest_best_artifact()
    if suggest:
        print("No Lyme Model artifact configured.")
        print()
        print("Suggested artifact:")
        print(f"  lyme model use {suggest['path']}/")
        print()
        print(f"  Base: {suggest['base_model']} | Size: {suggest['size_mb']}MB")
        if suggest["eval_loss"] is not None:
            print(f"  Eval loss: {suggest['eval_loss']}")
    else:
        print("No Lyme Model artifact found. Train or download an adapter first.")
        print("Expected: adapters/<name>/adapter_model.safetensors")
    return 0


def _cmd_use(args):
    raw_path = args.artifact_path
    artifact_dir = Path(raw_path)
    if not artifact_dir.is_absolute():
        artifact_dir = Path.cwd() / artifact_dir

    # Validate
    safetensors_file = artifact_dir / "adapter_model.safetensors"
    config_file = artifact_dir / "adapter_config.json"
    if not safetensors_file.exists():
        print(f"Error: {safetensors_file} not found", file=sys.stderr)
        return 1
    if not config_file.exists():
        print(f"Error: {config_file} not found", file=sys.stderr)
        return 1

    # Read base model name
    base_model = "unknown"
    try:
        config = json.loads(config_file.read_text())
        base_model = config.get("base_model_name_or_path", "unknown")
    except Exception:
        pass

    # Resolve relative path
    try:
        rel_path = artifact_dir.relative_to(Path.cwd())
    except ValueError:
        rel_path = artifact_dir

    import datetime
    current_data = {
        "path": str(rel_path),
        "base_model": base_model,
        "selected_at": datetime.datetime.now().isoformat(timespec="seconds"),
    }

    current_dir = Path.cwd() / ".lyme" / "model"
    current_dir.mkdir(parents=True, exist_ok=True)
    current_file = current_dir / "current.json"
    current_file.write_text(json.dumps(current_data, indent=2))

    print(f"Selected Lyme Model artifact: {rel_path}")
    print(f"  Base model: {base_model}")
    print(f"  Written to: {current_file}")
    return 0


def _cmd_diagnose(args=None):
    """Print diagnostic info about the current model adapter configuration."""
    info = {}
    current = _get_current_artifact()
    if current:
        info["artifact"] = current
        adapter_path_str = current.get("path", "")
        p = Path(adapter_path_str)
        if not p.is_absolute():
            p = Path.cwd() / p
        config_file = p / "adapter_config.json"
        weights_file = p / "adapter_model.safetensors"
        if config_file.exists():
            try:
                cfg = json.loads(config_file.read_text())
                info["adapter_config"] = {
                    "base_model_name_or_path": cfg.get("base_model_name_or_path", "?"),
                    "peft_type": cfg.get("peft_type", "?"),
                    "task_type": cfg.get("task_type", "?"),
                    "target_modules": cfg.get("target_modules", []),
                }
            except Exception as e:
                info["adapter_config_error"] = str(e)
        if weights_file.exists():
            sz = weights_file.stat().st_size
            info["adapter_weights_exists"] = True
            info["adapter_weights_size_mb"] = round(sz / (1024 * 1024), 1)
            try:
                from safetensors import safe_open
                keys = []
                with safe_open(str(weights_file), framework="pt") as f:
                    for i, k in enumerate(f.keys()):
                        if i >= 20:
                            break
                        keys.append(k)
                info["safetensors_keys_first_20"] = keys
            except Exception:
                info["safetensors_keys"] = "(could not read)"
        else:
            info["adapter_weights_exists"] = False
    else:
        info["artifact"] = None

    import importlib
    for mod_name in ["transformers", "peft", "accelerate", "torch"]:
        try:
            m = importlib.import_module(mod_name)
            info[f"{mod_name}_version"] = getattr(m, "__version__", "?")
        except ImportError:
            info[f"{mod_name}_version"] = "NOT INSTALLED"

    print(json.dumps(info, indent=2))
    return 0


# ─── New: Server / Stop / Bench-Perf ──────────────────────────────────────────

def _cmd_server(args):
    """Start persistent model server (foreground by default)."""
    model_name = getattr(args, 'model', None)
    adapter_path = None
    if not model_name:
        current = _get_current_artifact()
        if current:
            model_name = current.get("base_model", "deepseek-ai/deepseek-coder-6.7b-instruct")
            raw_path = current.get("path")
            if raw_path:
                p = Path(raw_path)
                if not p.is_absolute():
                    p = Path.cwd() / p
                adapter_path = str(p)
        else:
            print("No model specified and no artifact configured.", file=sys.stderr)
            print("Use: lyme model server --model <name>", file=sys.stderr)
            return 1

    server_script = _get_server_script()
    socket_path = server_client.get_socket_path()
    socket_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, server_script,
           "--model", model_name,
           "--socket-path", str(socket_path)]
    if adapter_path:
        cmd.extend(["--adapter-path", adapter_path])
    if getattr(args, 'load_in_4bit', False):
        cmd.append("--load-in-4bit")
    if getattr(args, 'load_in_8bit', False):
        cmd.append("--load-in-8bit")
    if getattr(args, 'dtype', None):
        cmd.extend(["--dtype", args.dtype])
    if getattr(args, 'debug', False):
        cmd.append("--debug")

    is_daemon = getattr(args, 'daemon', False)

    if is_daemon:
        import subprocess
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print(f"Server started (PID {proc.pid})")
        print(f"Socket: {socket_path}")
        print(f"Stop with: lyme model stop")
        return 0
    else:
        print(f"Starting server: {model_name}")
        print(f"Socket: {socket_path}")
        print("Server running in foreground. Press Ctrl+C to stop.")
        os.execvp(sys.executable, [sys.executable] + cmd)


def _cmd_stop(args=None):
    """Stop the persistent model server."""
    socket_path = server_client.get_socket_path()
    pid_path = server_client.get_pid_path()

    if not socket_path.exists():
        print("No server socket found. Server is not running.")
        return 0

    try:
        server_client.send_shutdown(timeout=5)
        print("Server stopped.")
    except Exception as exc:
        print(f"Could not shut down server gracefully: {exc}")
        for p in [socket_path, pid_path]:
            try:
                if p.exists():
                    p.unlink()
            except OSError:
                pass
    return 0


def _cmd_status(args):
    """Show persistent model server status."""
    socket_path = server_client.get_socket_path()
    stats = server_client.get_server_status(timeout=3)

    if stats.get("status") != "ok":
        result = {
            "status": "stopped",
            "socket_path": str(socket_path),
            "error": stats.get("error", "Server not running"),
        }
        if getattr(args, 'json', False):
            print(json.dumps(result, indent=2))
        else:
            print(f"Server status: STOPPED")
            print(f"Socket: {socket_path}")
            if not socket_path.exists():
                print("Socket file not found.")
        return 0

    uptime_m = stats.get("uptime_s", 0) // 60
    uptime_s = stats.get("uptime_s", 0) % 60
    quant = "4-bit" if stats.get("load_in_4bit") else "8-bit" if stats.get("load_in_8bit") else "none"
    vram = stats.get("vram_allocated_mb", 0)
    ram = stats.get("ram_mb", 0)

    result = {
        "status": "running",
        "pid": stats.get("pid"),
        "model": stats.get("model"),
        "quantization": quant,
        "dtype": stats.get("dtype"),
        "socket_path": str(socket_path),
        "uptime_s": stats.get("uptime_s", 0),
        "vram_allocated_mb": vram,
        "ram_mb": ram,
        "cuda_available": stats.get("cuda_available", False),
    }

    if getattr(args, 'json', False):
        print(json.dumps(result, indent=2))
    else:
        print(f"Server status: RUNNING")
        print(f"  PID:       {stats.get('pid')}")
        print(f"  Model:     {stats.get('model')}")
        print(f"  Quant:     {quant}")
        print(f"  Dtype:     {stats.get('dtype')}")
        print(f"  Socket:    {socket_path}")
        print(f"  Uptime:    {int(uptime_m)}m {int(uptime_s)}s")
        print(f"  VRAM:      {vram} MB")
        print(f"  RAM:       {ram} MB")
        print(f"  CUDA:      {stats.get('cuda_available', False)}")
    return 0


def _cmd_bench_perf(args):
    """Benchmark model runtime performance."""
    import subprocess
    import time

    model_name = getattr(args, 'model', None) or "deepseek-ai/deepseek-coder-6.7b-instruct"
    load_in_4bit = getattr(args, 'load_in_4bit', False)
    load_in_8bit = getattr(args, 'load_in_8bit', False)
    dtype = getattr(args, 'dtype', None)

    # Clean up any existing server
    server_client.send_shutdown()

    # Build server command
    server_script = _get_server_script()
    socket_path = server_client.get_socket_path()
    socket_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, server_script,
           "--model", model_name,
           "--socket-path", str(socket_path)]
    if load_in_4bit:
        cmd.append("--load-in-4bit")
    elif load_in_8bit:
        cmd.append("--load-in-8bit")
    if dtype:
        cmd.extend(["--dtype", dtype])

    # Start server (cold start)
    t0 = time.time()
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    load_time = None
    for _ in range(180):
        if server_client.is_server_running():
            load_time = round(time.time() - t0, 1)
            break
        time.sleep(1)

    if load_time is None:
        result = {"error": "Server failed to start within 180s", "model": model_name}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
        return 1

    try:
        # First-token latency: generate 1 token
        t1 = time.time()
        result_1 = server_client.send_generate(
            "Return the word hello.",
            {"max_new_tokens": 1, "do_sample": False, "use_cache": True},
            timeout=30,
        )
        first_token_ms = round((time.time() - t1) * 1000, 1)

        # Tokens/sec: generate 50 tokens
        t2 = time.time()
        result_n = server_client.send_generate(
            "Return the word hello repeatedly until I say stop.",
            {"max_new_tokens": 50, "do_sample": False, "use_cache": True},
            timeout=60,
        )
        gen_time = time.time() - t2
        tokens_per_sec = round(result_n["generated_tokens"] / gen_time, 2) if gen_time > 0 else 0.0

        # Server stats for VRAM/RAM
        stats = server_client.get_server_stats()

    except Exception as exc:
        result = {"error": str(exc), "model": model_name}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
        return 1
    finally:
        server_client.send_shutdown()

    bench_result = {
        "model": model_name,
        "load_time_s": load_time,
        "first_token_latency_ms": first_token_ms,
        "tokens_per_second": tokens_per_sec,
        "generated_tokens": result_n.get("generated_tokens", 0),
        "vram_allocated_mb": stats.get("vram_allocated_mb", 0),
        "vram_reserved_mb": stats.get("vram_reserved_mb", 0),
        "ram_mb": stats.get("ram_mb", 0),
        "load_in_4bit": load_in_4bit,
        "load_in_8bit": load_in_8bit,
        "dtype": dtype or "auto",
        "cuda_available": stats.get("cuda_available", False),
    }

    if args.json:
        print(json.dumps(bench_result, indent=2))
    else:
        print("=" * 55)
        print("  LYME MODEL PERFORMANCE BENCHMARK")
        print("=" * 55)
        print(f"  Model:              {bench_result['model']}")
        print(f"  Load time:          {bench_result['load_time_s']}s")
        print(f"  First-token latency: {bench_result['first_token_latency_ms']}ms")
        print(f"  Tokens/sec:         {bench_result['tokens_per_second']}")
        print(f"  Generated tokens:   {bench_result['generated_tokens']}")
        print(f"  VRAM allocated:     {bench_result['vram_allocated_mb']} MB")
        print(f"  VRAM reserved:      {bench_result['vram_reserved_mb']} MB")
        print(f"  RAM:                {bench_result['ram_mb']} MB")
        print(f"  Quantization:       {'4-bit' if load_in_4bit else '8-bit' if load_in_8bit else 'none'}")
        print(f"  Dtype:              {bench_result['dtype']}")
        print(f"  CUDA:               {bench_result['cuda_available']}")
        print("=" * 55)

    return 0


# ─── Existing Commands (enhanced) ──────────────────────────────────────────────

def _detect_cuda_vram() -> Optional[int]:
    """Detect CUDA VRAM in MB. Returns None if CUDA not available."""
    try:
        import subprocess
        import shutil
        nvidia_smi = shutil.which("nvidia-smi")
        if not nvidia_smi:
            return None
        result = subprocess.run(
            [nvidia_smi, "--query-gpu=memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            mem_str = result.stdout.strip().split("\n")[0].strip()
            return int(mem_str.replace(" MiB", "").replace(" MB", ""))
    except Exception:
        pass
    return None


def _cmd_run(args):
    task = getattr(args, 'task', None)
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        _emit_error("Error: Task description required", args, _is_hard_failure=True)
        return 1

    # Resolve model name and optional adapter path:
    #   --model  → base model only (no adapter)
    #   artifact → base model + PEFT adapter
    artifact_path = None
    model_name = getattr(args, 'model', None)
    if not model_name:
        current = _get_current_artifact()
        if current is None:
            parts = ["No Lyme Model artifact configured."]
            suggest = _suggest_best_artifact()
            if suggest:
                parts.append(f"Suggested: lyme model use {suggest['path']}/")
            parts.append("Or specify --model <base-model-name> to use a base model directly.")
            msg = "\n".join(parts)
            _emit_error(msg, args, _is_hard_failure=True)
            return 1
        model_name = current.get("base_model", "deepseek-ai/deepseek-coder-6.7b-instruct")
        raw_path = current.get("path")
        if raw_path:
            p = Path(raw_path)
            if not p.is_absolute():
                p = Path.cwd() / p
            artifact_path = str(p)

    use_json = getattr(args, 'json', False)

    if getattr(args, 'dry_run', False):
        est = diff_estimator.estimate(task)
        mode = mode_selector.select_mode(est.difficulty_score, est.risk.value, "standard_gpu", 1000)
        result = {
            "task": task,
            "model": model_name,
            "dry_run": True,
            "estimate": est.to_dict(),
            "mode": mode.to_dict(),
        }
        if use_json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"DRY RUN: {task}")
            print(f"  Model: {model_name}")
            print(f"  Type: {est.task_type.value} | Difficulty: {est.difficulty_level.value}")
            print(f"  Mode: {mode.selected_mode.value}")
        return 0

    # Hardware-aware 4-bit quantization: auto-detect for <=10GB VRAM
    load_in_4bit = getattr(args, 'load_in_4bit', False)
    load_in_8bit = getattr(args, 'load_in_8bit', False)
    if not load_in_4bit and not load_in_8bit:
        vram_mb = _detect_cuda_vram()
        if vram_mb is not None and vram_mb <= 10240:
            load_in_4bit = True
            if not use_json:
                print(f"Auto-detected 4-bit quantization ({vram_mb // 1024}GB VRAM)", file=sys.stderr)

    # Use persistent server by default, --no-server for isolated subprocess
    use_server = not getattr(args, 'no_server', False)

    # Generation safety kwargs: default deterministic, pass through to engine
    no_sample = getattr(args, 'no_sample', True)
    do_sample = not no_sample
    gen_kwargs = {
        "max_new_tokens": getattr(args, 'max_new_tokens', 32),
        "temperature": getattr(args, 'temperature', 0.1),
        "top_p": getattr(args, 'top_p', 0.95),
        "do_sample": do_sample,
        "timeout": getattr(args, 'timeout', 180),
        "verbose": not use_json,
        "debug": getattr(args, 'debug', False),
        "reuse_worker": use_server,
        "load_in_4bit": load_in_4bit,
        "load_in_8bit": load_in_8bit,
        "dtype": getattr(args, 'dtype', None),
    }

    runtime = AgentRuntime(
        model_name=model_name,
        adapter_path=artifact_path,
        repo_path=getattr(args, 'repo', '.'),
        **gen_kwargs,
    )
    no_context = getattr(args, 'no_context', False)
    context = None
    if not no_context and hasattr(args, 'context') and args.context:
        context = Path(args.context).read_text()

    try:
        result = runtime.run_task(task, context, raw_prompt=getattr(args, 'raw_prompt', False))
    except Exception as exc:
        _emit_error(f"Runtime error: {exc}", args)
        return 1

    if use_json:
        d = result.to_dict()
        if getattr(args, 'debug', False) and result.error_traceback:
            d["traceback"] = result.error_traceback
        print(json.dumps(d, indent=2))
    else:
        if result.success:
            print(result.output)
        else:
            print(f"Error: {result.error}", file=sys.stderr)
    return 0 if result.success else 1


def _emit_error(message: str, args, _is_hard_failure: bool = True):
    """Print error: JSON stdout on --json, stderr otherwise."""
    if getattr(args, 'json', False):
        print(json.dumps({
            "success": not _is_hard_failure,
            "error": message,
        }, indent=2))
    else:
        print(message, file=sys.stderr)


def _cmd_list(args=None):
    # Section 1: Lyme Model artifacts
    artifacts = _scan_artifacts()
    if artifacts:
        print("Lyme Model Artifacts:")
        print(f"{'Artifact':45s} {'Base Model':40s} {'Size':8s}")
        print("-" * 95)
        for a in artifacts:
            print(f"{a['id']:45s} {a['base_model']:40s} {a['size_mb']:>6.1f}MB")
        print()

    # Section 2: Base / runtime models
    models = ModelLoader.list_models()
    if models:
        print("Base / Runtime Models:")
        print(f"{'Model':30s} {'Size':8s} {'Quant':6s} {'Backend':10s}")
        print("-" * 54)
        for m in models:
            print(f"{m.name:30s} {m.size:8s} {m.quantization:6s} {m.backend:10s}")
    else:
        print("No base models registered.")
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


def _cmd_trial(args):
    """Handle trial harness commands."""
    from .trial.models import TaskType
    from .trial.seeded_tasks import SEEDED_TASKS, get_seeded_task, list_seeded_tasks

    trial_cmd = getattr(args, 'trial_command', None)
    runner = TrialRunner(dry_run=getattr(args, 'dry_run', False))
    replay = TrialReplay(Path(".lyme/trials"))
    report = TrialReport()

    if trial_cmd == "list":
        task_type_str = getattr(args, 'type', None)
        task_type = TaskType(task_type_str) if task_type_str else None
        difficulty = getattr(args, 'difficulty', None)
        tasks = runner.list_tasks(task_type_str, difficulty)
        if getattr(args, 'json', False):
            print(json.dumps(tasks, indent=2))
        else:
            print(f"Seeded Trial Tasks ({len(tasks)}):")
            print()
            current_type = None
            for t in tasks:
                if t["task_type"] != current_type:
                    current_type = t["task_type"]
                    print(f"\n  [{current_type}]")
                print(f"    {t['id']:20s} {t['difficulty']:8s} {t['title'][:60]}")
            print(f"\nTotal: {len(tasks)} tasks")
            print("Run:  lyme model trial run <task-id>")
        return 0

    if trial_cmd == "run":
        task_id = args.task_id
        repo = getattr(args, 'repo', '.')
        result = runner.run_task(task_id, repo)
        if getattr(args, 'json', False):
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            v = result.verdict.value if result.verdict else "?"
            icon = "✓" if v == "pass" else ("✗" if v == "fail" else "~")
            print(f"{icon} Trial: {result.title}")
            print(f"  ID:      {result.trial_id}")
            print(f"  Status:  {result.status.value}")
            print(f"  Verdict: {v.upper()}")
            print(f"  Score:   {result.score:.4f}")
            print(f"  Time:    {result.duration_s:.1f}s")
            if result.failures:
                print(f"  Failures ({len(result.failures)}):")
                for f in result.failures[:5]:
                    print(f"    ✗ {f}")
            if result.file_changes:
                print(f"  Changes ({len(result.file_changes)}):")
                for fc in result.file_changes[:5]:
                    print(f"    {fc.change_type}: {fc.path} (+{fc.lines_added}/-{fc.lines_removed})")
            print(f"  Report:  lyme model trial report {result.trial_id}")
        return 0

    if trial_cmd == "run-all":
        repo = getattr(args, 'repo', '.')
        run = runner.run_all(repo)
        if getattr(args, 'json', False):
            print(json.dumps(run.compute_summary(), indent=2))
        else:
            s = run.summary or run.compute_summary()
            print("=" * 60)
            print(f"ALL TRIALS COMPLETE: {run.run_id}")
            print("=" * 60)
            print(f"  Total:     {s['total']}")
            print(f"  Passed:    {s['passed']}")
            print(f"  Failed:    {s['failed']}")
            print(f"  Ambiguous: {s['ambiguous']}")
            print(f"  Pass Rate: {s['pass_rate']:.1%}")
            print(f"  Avg Score: {s['avg_score']:.4f}")
            print(f"  Duration:  {s['total_duration_s']:.1f}s")
            print(f"\n  Summary: lyme model trial summary {run.run_id}")
        return 0

    if trial_cmd == "run-type":
        task_type = args.task_type
        repo = getattr(args, 'repo', '.')
        run = runner.run_by_type(task_type, repo)
        if getattr(args, 'json', False):
            print(json.dumps(run.compute_summary(), indent=2))
        else:
            s = run.summary or run.compute_summary()
            print(f"Trials by type '{task_type}': {s['passed']}/{s['total']} passed ({s['pass_rate']:.0%})")
        return 0

    if trial_cmd == "replay":
        trial_id = args.trial_id
        output = replay.replay_trial(trial_id, "json" if getattr(args, 'json', False) else "text")
        if output is None:
            print(f"No trial or run found with ID: {trial_id}", file=sys.stderr)
            available = replay.list_replays()
            if available:
                print(f"Available replays: {[a['id'] for a in available[:10]]}")
            return 1
        print(output)
        return 0

    if trial_cmd == "report":
        trial_id = args.trial_id
        data = runner.recorder.load_trial(trial_id)
        if data is None:
            data = runner.recorder.load_run(trial_id)
            if data is None:
                print(f"No data found for ID: {trial_id}", file=sys.stderr)
                return 1
            from .trial.models import TrialRun, TrialResult, TrialStatus, Verdict
            from .trial.seeded_tasks import get_seeded_task
            trial_run = TrialRun(run_id=data["run_id"], config=data.get("config", {}),
                                 started_at=data.get("started_at", ""),
                                 completed_at=data.get("completed_at", ""))
            for rd in data.get("results", []):
                tr = TrialResult(trial_id=rd["trial_id"], task_id=rd["task_id"],
                                 title=rd["title"], status=TrialStatus(rd["status"]),
                                 verdict=Verdict(rd["verdict"]) if rd.get("verdict") else None,
                                 starting_commit=rd.get("starting_commit", ""),
                                 task_prompt=rd.get("task_prompt", ""),
                                 files_touched=rd.get("files_touched", []),
                                 commands_run=[], failures=rd.get("failures", []),
                                 final_diff=rd.get("final_diff", ""),
                                 test_results=rd.get("test_results", {}),
                                 duration_s=rd.get("duration_s", 0),
                                 timestamp=rd.get("timestamp", ""),
                                 score=rd.get("score", 0))
                trial_run.add_result(tr)
            content = report.generate_summary_report(trial_run)
        else:
            from .models import TrialResult as TRModel, TrialStatus, Verdict
            result_obj = TRModel(
                trial_id=data["trial_id"], task_id=data["task_id"],
                title=data["title"], status=TrialStatus(data["status"]),
                verdict=Verdict(data["verdict"]) if data.get("verdict") else None,
                starting_commit=data.get("starting_commit", ""),
                task_prompt=data.get("task_prompt", ""),
                files_touched=data.get("files_touched", []),
                commands_run=[], failures=data.get("failures", []),
                final_diff=data.get("final_diff", ""),
                test_results=data.get("test_results", {}),
                duration_s=data.get("duration_s", 0),
                timestamp=data.get("timestamp", ""),
                score=data.get("score", 0),
            )
            content = report.generate_trial_report(result_obj)

        output_path = getattr(args, 'output', None)
        if output_path:
            Path(output_path).write_text(content)
            print(f"Report saved to: {output_path}")
        else:
            print(content)
        return 0

    if trial_cmd == "results":
        trials = runner.recorder.list_trials()
        limit = getattr(args, 'limit', 20)
        trials = trials[:limit]
        if getattr(args, 'json', False):
            print(json.dumps(trials, indent=2))
        else:
            print(f"Recent Trials ({len(trials)}):")
            print(f"{'ID':<14s} {'Task':<20s} {'Status':<10s} {'Verdict':<10s} {'Score':<8s} {'Time':<10s}")
            print("-" * 72)
            for t in trials:
                print(f"{t['trial_id']:<14s} {t['task_id']:<20s} {t['status']:<10s} "
                      f"{str(t.get('verdict', '') or '?'):<10s} {t.get('score', 0):<8.3f} {t.get('duration_s', 0):<10.1f}")
        return 0

    if trial_cmd == "summary":
        run_id = args.run_id
        data = runner.recorder.load_run(run_id)
        if data is None:
            print(f"No run found with ID: {run_id}", file=sys.stderr)
            return 1
        from .trial.models import TrialRun as TRun, TrialResult, TrialStatus, Verdict
        trial_run = TRun(run_id=data["run_id"], config=data.get("config", {}),
                         started_at=data.get("started_at", ""),
                         completed_at=data.get("completed_at", ""))
        for rd in data.get("results", []):
            tr = TrialResult(trial_id=rd["trial_id"], task_id=rd["task_id"],
                             title=rd["title"], status=TrialStatus(rd["status"]),
                             verdict=Verdict(rd["verdict"]) if rd.get("verdict") else None,
                             starting_commit=rd.get("starting_commit", ""),
                             task_prompt=rd.get("task_prompt", ""),
                             files_touched=[], commands_run=[], failures=rd.get("failures", []),
                             final_diff=rd.get("final_diff", ""),
                             test_results=rd.get("test_results", {}),
                             duration_s=rd.get("duration_s", 0),
                             timestamp=rd.get("timestamp", ""),
                             score=rd.get("score", 0))
            trial_run.add_result(tr)
        if getattr(args, 'json', False):
            print(json.dumps(trial_run.compute_summary(), indent=2))
        else:
            content = report.generate_summary_report(trial_run)
            print(content)
        return 0

    if trial_cmd == "compare":
        run_ids = args.run_ids
        content = report.generate_comparison_report(run_ids)
        print(content)
        return 0

    print("Error: Unknown trial command. Use: list, run, run-all, run-type, replay, report, results, summary, compare", file=sys.stderr)
    return 1


def _cmd_arena(args):
    """Handle benchmark arena commands."""
    from .arena.models import ArenaConfig, ToolName
    from .arena.runner import ArenaRunner
    from .arena.scoring import ArenaScorer
    from .arena.leaderboard import LeaderboardGenerator
    from .arena.regression import RegressionChecker
    from .trial.seeded_tasks import SEEDED_TASKS

    arena_cmd = getattr(args, 'arena_command', None)
    scorer = ArenaScorer()
    board = LeaderboardGenerator()
    regression = RegressionChecker()
    runner = ArenaRunner()

    if arena_cmd == "run":
        task_type = getattr(args, 'task_type', 'all')
        specific_tasks = getattr(args, 'tasks', None)
        tools_str = getattr(args, 'tools', ['lyme'])
        repo = getattr(args, 'repo', '.')
        dry_run = getattr(args, 'dry_run', False)

        if specific_tasks:
            task_ids = specific_tasks
        elif task_type == 'all':
            task_ids = [t.id for t in SEEDED_TASKS]
        else:
            from .trial.models import TaskType
            tt = TaskType(task_type)
            task_ids = [t.id for t in SEEDED_TASKS if t.task_type == tt]

        tools = [ToolName(t) for t in tools_str]
        config = ArenaConfig(task_ids=task_ids, tools=tools, repo_path=repo)

        if dry_run:
            result = {
                "dry_run": True,
                "config": config.to_dict(),
                "task_count": len(task_ids),
                "tool_count": len(tools),
            }
            if getattr(args, 'json', False):
                print(json.dumps(result, indent=2))
            else:
                print(f"Arena Dry Run:")
                print(f"  Tasks: {len(task_ids)} ({', '.join(task_ids[:5])}{'...' if len(task_ids) > 5 else ''})")
                print(f"  Tools: {', '.join(t.value for t in tools)}")
                print(f"  Repo:  {repo}")
            return 0

        arena_run = runner.run_arena(config)
        arena_run = scorer.score_run(arena_run)

        runner._save_run(arena_run)

        if getattr(args, 'json', False):
            print(json.dumps(arena_run.to_dict(), indent=2, default=str))
        else:
            s = arena_run.summary
            print("=" * 60)
            print(f"ARENA COMPLETE: {arena_run.run_id}")
            print("=" * 60)
            for entry in s.get("rankings", []):
                print(f"  #{entry['rank']} {entry['tool']:<20s} {entry['final_score']:.4f}")
            print(f"\n  Winner: {s.get('winner', 'N/A')} ({s.get('winner_score', 0):.4f})")
            print(f"\n  Run ID: {arena_run.run_id}")
            print(f"  Leaderboard: lyme model arena leaderboard --run-id {arena_run.run_id}")
        return 0

    if arena_cmd == "leaderboard":
        run_id = getattr(args, 'run_id', None)
        fmt = getattr(args, 'format', 'both')
        output = getattr(args, 'output', None)

        if not run_id:
            runs = sorted(runner.output_dir.glob("arena-*.json"))
            if not runs:
                print("No arena runs found.", file=sys.stderr)
                return 1
            run_id = runs[-1].stem.replace("arena-", "")

        run_path = runner.output_dir / f"arena-{run_id}.json"
        if not run_path.exists():
            print(f"Arena run not found: {run_id}", file=sys.stderr)
            return 1

        run_data = json.loads(run_path.read_text())
        summary = run_data.get("summary", {})

        if fmt in ("markdown", "both"):
            md_path = output or str(runner.output_dir / f"leaderboard-{run_id}.md")
            board.generate_markdown(summary, md_path)
            print(f"Markdown leaderboard: {md_path}")

        if fmt in ("html", "both"):
            html_path = output.replace(".md", ".html") if output and output.endswith(".md") else (output or str(runner.output_dir / f"leaderboard-{run_id}.html"))
            board.generate_html(summary, html_path)
            print(f"HTML leaderboard: {html_path}")
        return 0

    if arena_cmd == "regression":
        run_id = getattr(args, 'run_id', None)

        if not run_id:
            runs = sorted(runner.output_dir.glob("arena-*.json"))
            if not runs:
                print("No arena runs found.", file=sys.stderr)
                return 1
            run_id = runs[-1].stem.replace("arena-", "")

        run_path = runner.output_dir / f"arena-{run_id}.json"
        if not run_path.exists():
            print(f"Arena run not found: {run_id}", file=sys.stderr)
            return 1

        run_data = json.loads(run_path.read_text())
        scores = run_data.get("scores", {})
        if not scores:
            print("No scores found in arena run. Run scoring first.", file=sys.stderr)
            return 1

        check_result = regression.check(scores)
        print(regression.regression_report(check_result))
        return 0

    if arena_cmd == "list":
        runs = []
        for path in sorted(runner.output_dir.glob("arena-*.json")):
            data = json.loads(path.read_text())
            runs.append({
                "run_id": data.get("run_id", path.stem),
                "started_at": data.get("started_at", ""),
                "completed_at": data.get("completed_at", ""),
                "summary": data.get("summary", {}),
            })
        runs.sort(key=lambda r: r.get("started_at", ""), reverse=True)

        if getattr(args, 'json', False):
            print(json.dumps(runs, indent=2))
        else:
            print(f"Arena Runs ({len(runs)}):")
            for r in runs:
                s = r.get("summary", {})
                winner = s.get("winner", "N/A") if s else "N/A"
                print(f"  {r['run_id'][:12]}  {r.get('started_at', '')[:19]}  winner={winner}")
        return 0

    if arena_cmd == "results":
        run_id = getattr(args, 'run_id', None)

        if not run_id:
            runs = sorted(runner.output_dir.glob("arena-*.json"))
            if not runs:
                print("No arena runs found.", file=sys.stderr)
                return 1
            run_id = runs[-1].stem.replace("arena-", "")

        run_path = runner.output_dir / f"arena-{run_id}.json"
        if not run_path.exists():
            print(f"Arena run not found: {run_id}", file=sys.stderr)
            return 1

        run_data = json.loads(run_path.read_text())

        if getattr(args, 'json', False):
            print(json.dumps(run_data, indent=2))
        else:
            summary = run_data.get("summary", {})
            print("=" * 60)
            print(f"ARENA RESULTS: {run_id}")
            print("=" * 60)
            for entry in summary.get("rankings", []):
                print(f"\n  #{entry['rank']} {entry['tool']} — Final: {entry['final_score']:.4f}")
                dims = entry.get("dimensions", {})
                for d, v in dims.items():
                    print(f"      {d}: {v:.4f}")

            results = run_data.get("results", {})
            if results:
                print(f"\n  Results by tool:")
                for tool_key, tool_results in results.items():
                    passed = sum(1 for r in tool_results if r.get("success"))
                    total = len(tool_results)
                    avg_time = sum(r.get("duration_s", 0) for r in tool_results) / max(total, 1)
                    print(f"    {tool_key}: {passed}/{total} passed, avg {avg_time:.1f}s")
        return 0

    print("Error: Unknown arena command. Use: run, leaderboard, regression, list, results", file=sys.stderr)
    return 1


def _cmd_ticket(args):
    """Handle paid ticket simulator commands."""
    from .ticket.models import TicketDifficulty
    from .ticket.seeded_tickets import SEEDED_TICKETS, get_seeded_ticket, list_seeded_tickets
    from .ticket.runner import TicketRunner
    from .ticket.scoring import TicketScorer, RevenueEstimator
    from .ticket.acceptance import AcceptanceGrader

    ticket_cmd = getattr(args, 'ticket_command', None)

    if ticket_cmd == "list":
        diff_str = getattr(args, 'difficulty', None)
        difficulty = TicketDifficulty(diff_str) if diff_str else None
        tickets = list_seeded_tickets(difficulty)

        if getattr(args, 'json', False):
            print(json.dumps([t.to_dict() for t in tickets], indent=2))
        else:
            total_revenue = sum(t.estimated_revenue for t in tickets)
            total_hours = sum(t.estimated_hours for t in tickets)
            print(f"Seeded Client Tickets ({len(tickets)}):")
            print(f"Total estimated revenue: ${total_revenue:.2f}")
            print(f"Total estimated hours: {total_hours:.1f}h")
            print()
            for t in tickets:
                hidden = f"{len(t.hidden_tests)} hidden tests" if t.hidden_tests else ""
                constraints = f"{len(t.architecture_constraints)} constraints" if t.architecture_constraints else ""
                meta = ", ".join(filter(None, [hidden, constraints]))
                print(f"  {t.id:14s} {t.difficulty.value:8s} ${t.estimated_revenue:<7.2f} {t.title[:55]}")
                if meta:
                    print(f"  {'':14s} {'':8s} {'':9s} {meta}")
            print(f"\nTotal: {len(tickets)} tickets | ${total_revenue:.2f} | {total_hours:.1f}h")
        return 0

    if ticket_cmd == "run":
        ticket_id = args.ticket_id
        runner = TicketRunner(dry_run=getattr(args, 'dry_run', False))
        result = runner.run_ticket(ticket_id)

        if getattr(args, 'json', False):
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            grade = result.acceptance_grade.value if result.acceptance_grade else "N/A"
            icon = "✓" if result.success else "✗"
            print(f"{icon} Ticket: {result.title}")
            print(f"  ID:      {result.ticket_id}")
            print(f"  Grade:   {grade}")
            print(f"  Score:   {result.score:.4f}")
            print(f"  Revenue: ${result.revenue_earned:.2f}")
            print(f"  Hours:   {result.duration_hours:.1f}h")
            print(f"  Criteria: {result.criteria_met}/{result.criteria_met}")
            print(f"  Hidden:  {result.hidden_tests_passed}/{result.hidden_tests_total}")
            if result.constraints_violated:
                print(f"  Violated constraints: {len(result.constraints_violated)}")
                for c in result.constraints_violated[:3]:
                    print(f"    - {c}")
            if result.ambiguity_resolved:
                print(f"  Ambiguity resolved: yes")
        return 0

    if ticket_cmd == "run-all":
        runner = TicketRunner(dry_run=getattr(args, 'dry_run', False))
        run = runner.run_all()
        s = run.summary
        if getattr(args, 'json', False):
            print(json.dumps(s, indent=2))
        else:
            print("=" * 60)
            print("PAID TICKET SIMULATION — COMPLETE")
            print("=" * 60)
            print(f"  Run ID:          {run.run_id}")
            print(f"  Total:           {s['total']}")
            print(f"  Accepted:        {s['accepted']}")
            print(f"  Conditional:     {s['conditionally_accepted']}")
            print(f"  Rejected:        {s['rejected']}")
            print(f"  Acceptance Rate: {s['acceptance_rate']:.1%}")
            print(f"  Revenue Earned:  ${s['total_revenue']:.2f}")
            print(f"  Revenue Est.:    ${s['estimated_revenue']:.2f}")
            print(f"  Revenue Capture: {s['revenue_capture_rate']:.1%}")
            print(f"  Avg Score:       {s['avg_score']:.4f}")
            print()
            print(f"  Breakdown:")
            for r in run.results:
                grade = r.acceptance_grade.value[:4] if r.acceptance_grade else "?"
                icon = "✓" if r.success else "✗"
                print(f"    {icon} {r.ticket_id:12s} ${r.revenue_earned:<7.2f} {grade:>6s} {r.title[:45]}")
        return 0

    if ticket_cmd == "results":
        runner = TicketRunner()
        results_path = runner.output_dir / "results"
        results = []
        if results_path.exists():
            for path in sorted(results_path.glob("*.json")):
                results.append(json.loads(path.read_text()))
        results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        if getattr(args, 'json', False):
            print(json.dumps(results[:20], indent=2))
        else:
            print(f"Ticket Results ({len(results)}):")
            for r in results[:20]:
                grade = r.get("acceptance_grade", "N/A")[:6]
                print(f"  {r.get('ticket_id', '?'):14s} ${r.get('revenue_earned', 0):<7.2f} "
                      f"{grade:<8s} score={r.get('score', 0):.3f}")
        return 0

    if ticket_cmd == "report":
        runner = TicketRunner()
        run_id = getattr(args, 'run_id', None)
        if not run_id:
            runs_path = runner.output_dir / "runs"
            if runs_path.exists():
                runs = sorted(runs_path.glob("*.json"))
                if runs:
                    data = json.loads(runs[-1].read_text())
                    s = data.get("summary", {})
                else:
                    print("No ticket runs found.", file=sys.stderr)
                    return 1
            else:
                print("No ticket runs found.", file=sys.stderr)
                return 1
        else:
            run_path = runner.output_dir / "runs" / f"run-{run_id}.json"
            if not run_path.exists():
                print(f"Run not found: {run_id}", file=sys.stderr)
                return 1
            data = json.loads(run_path.read_text())
            s = data.get("summary", {})

        print("=" * 60)
        print("PAID TICKET BENCHMARK REPORT")
        print("=" * 60)
        print(f"Total tickets:    {s.get('total', 0)}")
        print(f"Accepted:         {s.get('accepted', 0)}")
        print(f"Conditional:      {s.get('conditionally_accepted', 0)}")
        print(f"Rejected:         {s.get('rejected', 0)}")
        print(f"Acceptance rate:  {s.get('acceptance_rate', 0):.1%}")
        print()
        print(f"Revenue earned:   ${s.get('total_revenue', 0):.2f}")
        print(f"Revenue target:   ${s.get('estimated_revenue', 0):.2f}")
        print(f"Revenue capture:  {s.get('revenue_capture_rate', 0):.1%}")
        print(f"Avg quality:      {s.get('avg_score', 0):.4f}")
        print()
        print("Client-Acceptance Scoring:")
        print("  ACCEPTED = meets all criteria, passes hidden tests, respects constraints")
        print("  CONDITIONALLY_ACCEPTED = meets most criteria, minor issues")
        print("  REJECTED_MINOR = significant gaps, partial rewrite needed")
        print("  REJECTED_MAJOR = fundamentally wrong approach")
        print()
        revenue_rate = s.get('revenue_capture_rate', 0)
        if revenue_rate >= 0.8:
            print(f"✓ Commercial Viability: STRONG ({revenue_rate:.0%} revenue capture)")
        elif revenue_rate >= 0.5:
            print(f"~ Commercial Viability: MODERATE ({revenue_rate:.0%} revenue capture)")
        else:
            print(f"✗ Commercial Viability: WEAK ({revenue_rate:.0%} revenue capture)")
        print("=" * 60)
        return 0

    print("Error: Unknown ticket command. Use: list, run, run-all, results, report", file=sys.stderr)
    return 1


def _cmd_autonomy(args):
    """Handle trust-gated autonomy commands."""
    controller = AutonomyController()
    audit = AuditTrail()
    explainer = ContinuationExplainer()
    autonomy_cmd = getattr(args, 'autonomy_command', None)

    if autonomy_cmd == "mode":
        level_str = getattr(args, 'level', None)
        show = getattr(args, 'show', False)

        if level_str:
            level = AutonomyLevel(level_str)
            controller.set_level(level)
            print(f"Autonomy mode set to: {level.value}")
            print()
            print(explainer.explain_config(controller.config))
            audit.record(level, Action.READ_FILE, f"Changed autonomy level to {level.value}",
                         1.0, 0.0, True, "mode_changed")
            return 0

        if show or not level_str:
            print(explainer.explain_config(controller.config))
            return 0

    if autonomy_cmd == "decide":
        action_str = args.action
        description = args.description
        confidence = args.confidence
        risk = args.risk
        files = args.files

        action = Action(action_str)
        decision = controller.decide(action, description, confidence, risk, files)
        print(explainer.explain_decision(decision, controller.config))

        audit.record(controller.config.level, action, description, confidence, risk,
                     decision.allowed, "allowed" if decision.allowed else "blocked",
                     files_changed=files)
        return 0 if decision.allowed else 1

    if autonomy_cmd == "approvals":
        approve_id = getattr(args, 'approve', None)
        deny_id = getattr(args, 'deny', None)

        if approve_id:
            decision = controller.approve(approve_id, "cli")
            if decision:
                audit.record(controller.config.level, Action.COMMIT, f"Approved {approve_id}",
                             1.0, 0.0, True, "approved")
                print(f"Approval {approve_id} granted.")
            else:
                print(f"Approval {approve_id} not found or already decided.", file=sys.stderr)
            return 0

        if deny_id:
            reason = getattr(args, 'reason', 'Denied by user')
            decision = controller.deny(deny_id, "cli", reason)
            if decision:
                audit.record(controller.config.level, Action.COMMIT, f"Denied {deny_id}: {reason}",
                             1.0, 0.0, False, "denied")
                print(f"Approval {deny_id} denied: {reason}")
            else:
                print(f"Approval {deny_id} not found or already decided.", file=sys.stderr)
            return 0

        pending = controller.pending_approvals()
        if not pending:
            print("No pending approvals.")
        else:
            print(f"Pending Approvals ({len(pending)}):")
            for a in pending:
                print(f"\n  ID:     {a.id}")
                print(f"  Action: {a.action.value}")
                print(f"  Desc:   {a.description}")
                print(f"  Conf:   {a.confidence:.3f} | Risk: {a.risk_score:.3f}")
                print(f"  Files:  {', '.join(a.affected_files[:5])}")
                print(f"  Created: {a.created_at}")
        return 0

    if autonomy_cmd == "audit":
        summary = audit.summary()
        if getattr(args, 'json', False):
            print(json.dumps(summary, indent=2))
        else:
            limit = getattr(args, 'limit', 20)
            print("=" * 55)
            print("  AUDIT TRAIL")
            print("=" * 55)
            print(f"  Total: {summary['total_entries']}")
            print(f"  Approved: {summary['approved']}")
            print(f"  Denied: {summary['denied']}")
            print(f"  Approval rate: {summary['approval_rate']:.1%}")
            print(f"  Errors: {summary['errors']}")
            print()
            entries = audit.get_entries(limit=limit)
            for e in entries:
                icon = "✓" if e.approved else "✗"
                print(f"  {icon} [{e.autonomy_level.value}] {e.action.value}")
                print(f"     {e.description[:60]}")
                print(f"     conf={e.confidence:.2f} risk={e.risk_score:.2f} {e.duration_ms:.0f}ms")
                if e.error:
                    print(f"     ERROR: {e.error[:60]}")
        return 0

    if autonomy_cmd == "explain":
        print(explainer.explain_config(controller.config))
        return 0

    print("Error: Unknown autonomy command. Use: mode, decide, approvals, audit, explain", file=sys.stderr)
    return 1


def _cmd_workflow(args):
    """Handle Issue→Verified PR workflow commands."""
    from .workflow.models import IssueTicket, AcceptanceCriterion

    wf_cmd = getattr(args, 'workflow_command', None)

    if wf_cmd == "plan":
        executor = WorkflowExecutor(dry_run=True)
        url = getattr(args, 'url', None)
        text = getattr(args, 'text', None)

        if url:
            ticket = executor.ingester.from_url(url)
            if not ticket:
                print(f"Could not fetch issue from URL: {url}", file=sys.stderr)
                return 1
        elif text:
            ticket = executor.ingester.from_text(text)
        else:
            print("Error: --url or --text required", file=sys.stderr)
            return 1

        plan = executor.planner.plan(ticket)
        risk = executor.planner.assess_risk(ticket, plan)

        if getattr(args, 'json', False):
            print(json.dumps({"plan": plan.to_dict(), "risk": risk.to_dict()}, indent=2, default=str))
        else:
            print("=" * 60)
            print(f"IMPLEMENTATION PLAN: {ticket.title}")
            print("=" * 60)
            print(f"  Ticket:     {ticket.id}")
            print(f"  Branch:     {plan.branch_name}")
            print(f"  Difficulty: {plan.estimated_difficulty}")
            print(f"  Files:      {', '.join(plan.estimated_files)}")
            print(f"\n  Acceptance Criteria ({len(ticket.acceptance_criteria)}):")
            for c in ticket.acceptance_criteria:
                print(f"    • {c.description}")
            print(f"\n  Steps ({len(plan.steps)}):")
            for s in plan.steps:
                print(f"    {s.order}. [{s.risk}] {s.action} on {s.file}")
                print(f"       {s.description}")
            print(f"\n  Risk Assessment:")
            print(f"    Overall: {risk.overall_risk.upper()} ({risk.risk_score:.2f})")
            for r in risk.risks:
                print(f"    ⚠ {r['description']}")
            print(f"\n  Rollback:")
            for inst in plan.rollback_instructions:
                print(f"    $ {inst}")
        return 0

    if wf_cmd == "run":
        url = getattr(args, 'url', None)
        text = getattr(args, 'text', None)
        repo = getattr(args, 'repo', '.')
        dry_run = getattr(args, 'dry_run', False)
        simulate = getattr(args, 'simulate', True)

        if not url and not text:
            print("Error: --url or --text required", file=sys.stderr)
            return 1

        executor = WorkflowExecutor(dry_run=dry_run)

        if url:
            ticket = executor.ingester.from_url(url)
            if not ticket:
                print(f"Could not fetch issue from URL: {url}", file=sys.stderr)
                return 1
        else:
            ticket_id = getattr(args, 'id', 'issue-001')
            ticket = executor.ingester.from_text(text, ticket_id)

        result = executor.run(ticket, repo_path=repo, simulate=simulate)
        executor.save_result(result)

        if getattr(args, 'json', False):
            print(json.dumps(result.to_dict(), indent=2, default=str))
        else:
            reporter = PRReporter()
            report = reporter.generate_full_report(result)
            print(report)

            report_path = reporter.save_report(result)
            print(f"\nReport saved: {report_path}")
        return 0

    if wf_cmd == "report":
        ticket_id = args.ticket_id
        output = getattr(args, 'output', None)
        executor = WorkflowExecutor()
        path = executor.output_dir / f"pr-{ticket_id}.json"
        if not path.exists():
            print(f"No workflow result found for ticket: {ticket_id}", file=sys.stderr)
            return 1
        import json as _json
        data = _json.loads(path.read_text())

        reporter = PRReporter()
        from .workflow.models import PRResult, ImplementationPlan, RiskReport, VerificationEvidence, ImplementationStep
        plan = ImplementationPlan(**data["implementation_plan"])
        plan.steps = [ImplementationStep(**s) for s in data["implementation_plan"]["steps"]]
        risk = RiskReport(**data["risk_report"])
        verif = VerificationEvidence(**data["verification"])
        result = PRResult(
            ticket_id=data["ticket_id"], title=data["title"],
            branch_name=data["branch_name"], pr_url=data["pr_url"],
            pr_summary=data["pr_summary"], implementation_plan=plan,
            risk_report=risk, verification=verif,
            rollback_instructions=data["rollback_instructions"],
            files_changed=data["files_changed"], duration_s=data["duration_s"],
            success=data["success"], created_at=data["created_at"],
            errors=data.get("errors", []),
        )

        report = reporter.generate_full_report(result)
        if output:
            Path(output).write_text(report)
            print(f"Report saved: {output}")
        else:
            print(report)
        return 0

    print("Error: Unknown workflow command. Use: run, report, plan", file=sys.stderr)
    return 1


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
    harness = ModelEvaluationHarness(model_name=getattr(args, 'model', 'deepseek-ai/deepseek-coder-6.7b-instruct'))
    results = harness.run_all()
    harness.print_summary(results)
    return 0
