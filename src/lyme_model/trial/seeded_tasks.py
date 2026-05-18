"""25 seeded trial tasks from real open-source repos.

5 tasks per type x 5 types = 25 total.
Types: fix_failing_test, implement_feature, refactor_module, update_dependency, add_docs
"""

from .models import SeededTask, TaskType

SEEDED_TASKS: list[SeededTask] = [
    # ── FIX FAILING TEST (5 tasks) ─────────────────────────────────────────
    SeededTask(
        id="fix-test-001",
        title="Fix test_should_detect_python in repo doctor",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.FIX_FAILING_TEST,
        difficulty="easy",
        description="The test `test_should_detect_python` in `tests/test_doctor.py` is failing "
                    "because the language detector returns 'JavaScript' for Python projects. "
                    "Fix the language detection logic in the repo doctor.",
        acceptance_criteria=[
            "test_should_detect_python passes",
            "all existing tests still pass",
            "language detection still works for JS/TS projects",
        ],
        estimated_time_minutes=15,
        expected_files=["src/lyme_model/runtime/text_cleanup.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_doctor.py::test_should_detect_python -xvs",
        hints=["Check the file_extension mapping in the detector", "Python files should map to 'Python'"],
        tags=["language-detection", "doctor"],
    ),
    SeededTask(
        id="fix-test-002",
        title="Fix test_parse_markdown_tables in export module",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.FIX_FAILING_TEST,
        difficulty="medium",
        description="The markdown table parser in the export module crashes on empty cells. "
                    "Fix the parser to handle `||` (empty cells) and `| ` (trailing spaces).",
        acceptance_criteria=[
            "test_parse_markdown_tables passes",
            "empty cells return empty string not None",
            "trailing spaces in cells are stripped",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/distill/markdown.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_export.py::test_parse_markdown_tables -xvs",
        hints=["Look at the split() call on line 47", "Empty strings between delimiters should be kept"],
        tags=["markdown", "parsing"],
    ),
    SeededTask(
        id="fix-test-003",
        title="Fix test_context_token_count off-by-one error",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.FIX_FAILING_TEST,
        difficulty="easy",
        description="The context compiler's token count is off by one for single-token inputs. "
                    "Fix the token counting logic.",
        acceptance_criteria=[
            "test_context_token_count passes",
            "single token returns exactly 1",
            "empty input returns 0 not 1",
        ],
        estimated_time_minutes=10,
        expected_files=["src/lyme_model/context/compiler.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_context.py::test_context_token_count -xvs",
        hints=["Check the off-by-one in the while loop boundary condition"],
        tags=["token-count", "context"],
    ),
    SeededTask(
        id="fix-test-004",
        title="Fix test_qa_engine_refuses_outside_domain",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.FIX_FAILING_TEST,
        difficulty="medium",
        description="The QA engine's domain check is too strict — it refuses questions that "
                    "mention 'repository' or 'codebase' even though those are valid topics. "
                    "Fix the domain classifier.",
        acceptance_criteria=[
            "test_qa_engine_refuses_outside_domain passes",
            "'what language is this repository' is not refused",
            "'what is the meaning of life' is still refused",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/slices/qa_engine.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_qa_engine.py::test_qa_engine_refuses_outside_domain -xvs",
        hints=["The domain whitelist is too narrow — add 'repository' and 'codebase' keywords"],
        tags=["qa", "domain-classification"],
    ),
    SeededTask(
        id="fix-test-005",
        title="Fix test_cli_handles_empty_input gracefully",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.FIX_FAILING_TEST,
        difficulty="easy",
        description="The CLI crashes with a KeyError when given an empty string as input. "
                    "Fix the input handler to return a clean error message.",
        acceptance_criteria=[
            "test_cli_handles_empty_input passes",
            "empty input shows 'Error: Task/question required'",
            "exit code is 1 not a crash",
        ],
        estimated_time_minutes=10,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_cli_handles_empty_input -xvs",
        hints=["Check _get_task_input for the None/empty case before sys.exit"],
        tags=["cli", "error-handling"],
    ),

    # ── IMPLEMENT SMALL FEATURE (5 tasks) ──────────────────────────────────
    SeededTask(
        id="feat-001",
        title="Add --format flag to lyme model summary command",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.IMPLEMENT_FEATURE,
        difficulty="easy",
        description="Add a `--format` flag to `lyme model summary` that accepts "
                    "'text' (default) or 'json'. JSON output should return the full summary dict.",
        acceptance_criteria=[
            "--format json returns valid JSON",
            "--format text returns human-readable output (default)",
            "existing --json flag still works",
            "no breaking changes to existing behavior",
        ],
        estimated_time_minutes=15,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_summary_format -xvs",
        hints=["Add a --format argument to the summary parser", "Call json.dumps when format=json"],
        tags=["cli", "feature"],
    ),
    SeededTask(
        id="feat-002",
        title="Add 'recent' subcommand to lyme model history",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.IMPLEMENT_FEATURE,
        difficulty="easy",
        description="Add `lyme model history recent` that shows only runs from the last 24 hours. "
                    "Filter by comparing run timestamps to current time.",
        acceptance_criteria=[
            "'lyme model history recent' shows only runs < 24h old",
            "'lyme model history recent --json' returns JSON array",
            "runs older than 24h are excluded",
            "--limit flag still works with recent filter",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_history_recent -xvs",
        hints=["Add a 'recent' sub-subcommand to the history parser", "Parse timestamps and compare with datetime.now()"],
        tags=["cli", "history"],
    ),
    SeededTask(
        id="feat-003",
        title="Add --stats flag to lyme model bench",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.IMPLEMENT_FEATURE,
        difficulty="medium",
        description="Add a `--stats` flag to `lyme model bench` that shows aggregated statistics "
                    "across all previous benchmark runs. Stats include: total runs, avg pass rate, "
                    "avg latency, best/worst category.",
        acceptance_criteria=[
            "--stats shows aggregated stats from all saved benchmark reports",
            "stats include total_runs, avg_pass_rate, avg_latency_s",
            "stats include best_category and worst_category",
            "if no prior runs, shows 'no benchmark data found'",
        ],
        estimated_time_minutes=25,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_bench_stats -xvs",
        hints=["Scan .lyme/audit/benchmark-*.json files", "Aggregate across all report files"],
        tags=["benchmark", "stats"],
    ),
    SeededTask(
        id="feat-004",
        title="Add --tags filter to lyme model list",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.IMPLEMENT_FEATURE,
        difficulty="medium",
        description="Add `--tags` filter to `lyme model list` to filter artifacts by comma-separated tags. "
                    "Also add `--sort` flag accepting 'name', 'size', 'date'.",
        acceptance_criteria=[
            "--tags experimental,quant shows only matching artifacts",
            "--sort size sorts by artifact size",
            "--sort name sorts alphabetically",
            "no flags shows all artifacts (existing behavior)",
        ],
        estimated_time_minutes=25,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_list_tags -xvs",
        hints=["Parse --tags as comma-separated list", "Filter artifact metadata"],
        tags=["artifacts", "filtering"],
    ),
    SeededTask(
        id="feat-005",
        title="Add --watch flag to lyme model run",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.IMPLEMENT_FEATURE,
        difficulty="medium",
        description="Add a `--watch` flag to `lyme model run` that polls the run status every 2 seconds "
                    "and prints progress dots + elapsed time. Show a summary when done.",
        acceptance_criteria=[
            "--watch prints a dot every 2 seconds while running",
            "--watch shows elapsed time every 10s (e.g. '10s...')",
            "final output shows total duration",
            "non-watch mode is unchanged",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_cli.py::test_run_watch -xvs",
        hints=["Use time.sleep(2) loop with sys.stdout.write('.')", "Track start time with time.time()"],
        tags=["cli", "run"],
    ),

    # ── REFACTOR MODULE (5 tasks) ──────────────────────────────────────────
    SeededTask(
        id="refactor-001",
        title="Extract CLI command handlers from cli.py into separate module",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.REFACTOR_MODULE,
        difficulty="hard",
        description="The cli.py file has grown to >1200 lines with all command handlers inlined. "
                    "Extract each command handler group into its own module under cli_commands/. "
                    "Keep cli.py as just the parser and dispatcher.",
        acceptance_criteria=[
            "cli.py is <300 lines after refactor",
            "all command handlers are in cli_commands/*.py",
            "all existing tests pass without modification",
            "'lyme model --help' shows all commands",
            "each cli_commands/*.py has a clear single responsibility",
        ],
        estimated_time_minutes=60,
        expected_files=["src/lyme_model/cli.py", "src/lyme_model/cli_commands/"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=[
            "Group handlers by domain: ask/plan/fix in task_commands.py",
            "bench/benchmark/eval-report in bench_commands.py",
            "Keep imports clean and use relative imports",
        ],
        tags=["refactor", "modularization"],
    ),
    SeededTask(
        id="refactor-002",
        title="Consolidate duplicate test detection logic",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.REFACTOR_MODULE,
        difficulty="medium",
        description="There are two implementations of test command detection: one in cli.py "
                    "as `_detect_test_command` and another in `_cmd_tests`. Consolidate them "
                    "into a single `detect_test_command` function in a utilities module.",
        acceptance_criteria=[
            "exactly one test detection implementation exists",
            "function is importable from lyme_model.utils",
            "both callers use the consolidated version",
            "all tests pass",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/cli.py", "src/lyme_model/utils.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=["Move _detect_test_command to utils.py", "Import from utils in both places"],
        tags=["refactor", "duplication"],
    ),
    SeededTask(
        id="refactor-003",
        title="Replace repeated dict construction with dataclass pattern",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.REFACTOR_MODULE,
        difficulty="medium",
        description="Several CLI handlers construct result dicts manually with repetitive "
                    "`{key: value}` patterns. Convert them to use dataclasses with to_dict() methods, "
                    "following the existing BenchmarkReport pattern.",
        acceptance_criteria=[
            "at least 3 command handlers use dataclasses instead of raw dicts",
            "each dataclass has a to_dict() method",
            "JSON output is identical to before",
            "all tests pass",
        ],
        estimated_time_minutes=30,
        expected_files=["src/lyme_model/cli.py", "src/lyme_model/trial/models.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=[
            "Look at _cmd_compare, _cmd_bench, _cmd_fix for manual dict builders",
            "Create Result dataclass with to_dict()",
        ],
        tags=["refactor", "dataclass"],
    ),
    SeededTask(
        id="refactor-004",
        title="Separate safety modes into strategy pattern",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.REFACTOR_MODULE,
        difficulty="hard",
        description="The safety mode logic in tools/session.py uses if/elif chains for "
                    "readonly/careful/full modes. Replace with a Strategy pattern where each "
                    "SafetyMode has its own enforcement class.",
        acceptance_criteria=[
            "each safety mode is a separate class implementing a common interface",
            "no if/elif chains based on mode type",
            "all existing tool tests pass",
            "adding a new mode requires only a new class",
        ],
        estimated_time_minutes=40,
        expected_files=["src/lyme_model/tools/session.py", "src/lyme_model/tools/safety.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_tools.py -x",
        hints=[
            "Define SafetyStrategy abstract base class",
            "ReadonlyStrategy, CarefulStrategy, FullStrategy implementations",
        ],
        tags=["refactor", "design-patterns"],
    ),
    SeededTask(
        id="refactor-005",
        title="Extract report generation from CLI into dedicated module",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.REFACTOR_MODULE,
        difficulty="medium",
        description="The _cmd_eval_report and report generation logic lives inside cli.py. "
                    "Extract all report generation into a dedicated lyme_model/reports/ module "
                    "with a clean interface.",
        acceptance_criteria=[
            "lyme_model/reports/ exists with report generators",
            "cli.py imports report functions instead of inlining them",
            "JSON and text output formats produce identical output",
            "all tests pass",
        ],
        estimated_time_minutes=25,
        expected_files=["src/lyme_model/cli.py", "src/lyme_model/reports/"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=["Move _cmd_eval_report to reports/eval_report.py", "Keep CLI handler as thin wrapper"],
        tags=["refactor", "reports"],
    ),

    # ── UPDATE DEPENDENCY (5 tasks) ────────────────────────────────────────
    SeededTask(
        id="dep-001",
        title="Upgrade pyyaml from 6.0 to 6.0.2",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.UPDATE_DEPENDENCY,
        difficulty="easy",
        description="Update pyyaml dependency from >=6.0 to >=6.0.2 in pyproject.toml. "
                    "Check for any breaking changes in the API usage and fix if needed.",
        acceptance_criteria=[
            "pyproject.toml requires pyyaml>=6.0.2",
            "all existing yaml usage still works",
            "all tests pass",
        ],
        estimated_time_minutes=10,
        expected_files=["pyproject.toml"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=["pyyaml 6.0.2 is a bugfix release, no breaking API changes expected"],
        tags=["dependencies", "security"],
    ),
    SeededTask(
        id="dep-002",
        title="Add pytest-xdist as optional dev dependency",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.UPDATE_DEPENDENCY,
        difficulty="easy",
        description="Add pytest-xdist to the [dev] optional dependencies in pyproject.toml. "
                    "This enables parallel test execution with `pytest -n auto`.",
        acceptance_criteria=[
            "pytest-xdist appears in [project.optional-dependencies] dev",
            "pip install -e '.[dev]' installs pytest-xdist",
            "pytest -n auto runs tests in parallel",
        ],
        estimated_time_minutes=10,
        expected_files=["pyproject.toml"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x --numprocesses=2",
        hints=["Add to existing dev dependencies list"],
        tags=["dependencies", "testing"],
    ),
    SeededTask(
        id="dep-003",
        title="Add mkdocs as documentation dependency",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.UPDATE_DEPENDENCY,
        difficulty="easy",
        description="Add mkdocs and mkdocs-material to the dev dependencies. These are needed "
                    "for building the project documentation site.",
        acceptance_criteria=[
            "mkdocs and mkdocs-material are in dev dependencies",
            "pip install -e '.[dev]' installs both packages",
        ],
        estimated_time_minutes=10,
        expected_files=["pyproject.toml"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -c 'import mkdocs; import material'",
        hints=["Add to [project.optional-dependencies] dev section"],
        tags=["dependencies", "docs"],
    ),
    SeededTask(
        id="dep-004",
        title="Pin torch to >=2.1.0 in ML dependencies",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.UPDATE_DEPENDENCY,
        difficulty="medium",
        description="The ML optional dependencies currently require torch>=2.0.0. Update this to "
                    "torch>=2.1.0 to leverage newer features. Check that all torch API usage "
                    "in the codebase is compatible with 2.1.0.",
        acceptance_criteria=[
            "pyproject.toml requires torch>=2.1.0",
            "all torch imports and API calls are valid in 2.1.0",
            "existing tests pass",
        ],
        estimated_time_minutes=20,
        expected_files=["pyproject.toml"],
        setup_command="pip install -e '.[ml]'",
        test_command="python -m pytest tests/test_ml.py -x",
        hints=[
            "torch 2.1.0 deprecated _assert_async but kept backward compat",
            "check for any usage of torch.cuda.amp.autocast (deprecated in 2.1)",
        ],
        tags=["dependencies", "ml"],
    ),
    SeededTask(
        id="dep-005",
        title="Remove unused dependency 'requests' from project",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.UPDATE_DEPENDENCY,
        difficulty="medium",
        description="The 'requests' library is listed in dependencies but no code imports it. "
                    "Remove it from pyproject.toml. If any code does use it, replace with "
                    "urllib from stdlib.",
        acceptance_criteria=[
            "requests is not in pyproject.toml dependencies",
            "no code imports requests",
            "all tests pass",
        ],
        estimated_time_minutes=15,
        expected_files=["pyproject.toml"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=["Grep for 'import requests' and 'from requests' across the codebase"],
        tags=["dependencies", "cleanup"],
    ),

    # ── ADD DOCS (5 tasks) ─────────────────────────────────────────────────
    SeededTask(
        id="docs-001",
        title="Add docstring to cli.py handle_command function",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.ADD_DOCS,
        difficulty="easy",
        description="Add a comprehensive docstring to the `handle_command` function explaining "
                    "its purpose, expected args, return value, and error handling.",
        acceptance_criteria=[
            "handle_command has a docstring with Args, Returns, and Raises sections",
            "docstring explains the command dispatch flow",
            "all tests pass",
        ],
        estimated_time_minutes=10,
        expected_files=["src/lyme_model/cli.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/ -x",
        hints=["Follow Google-style docstring format (existing convention)"],
        tags=["docs", "docstrings"],
    ),
    SeededTask(
        id="docs-002",
        title="Add README section for trial harness",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.ADD_DOCS,
        difficulty="easy",
        description='Add a "Trial Harness" section to the README.md explaining what trials are, '
                    "how to run them, and how to interpret results.",
        acceptance_criteria=[
            "README.md has a '## Trial Harness' section",
            "section includes usage examples",
            "section explains pass/fail judgment",
            "section links to trial commands",
        ],
        estimated_time_minutes=20,
        expected_files=["README.md"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -c 'open(\"README.md\").read().index(\"## Trial Harness\")'",
        hints=["Add after the existing 'Core Commands' table"],
        tags=["docs", "readme"],
    ),
    SeededTask(
        id="docs-003",
        title="Document the QA engine domain model",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.ADD_DOCS,
        difficulty="medium",
        description="Write a module-level docstring for qa_engine.py explaining the domain model, "
                    "supported question types, refusal logic, and confidence calibration.",
        acceptance_criteria=[
            "qa_engine.py has a module-level docstring",
            "docstring explains domain detection",
            "docstring explains confidence scoring",
            "docstring explains refusal logic",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/slices/qa_engine.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_qa_engine.py -x",
        hints=["Place the docstring at the top of the file before imports"],
        tags=["docs", "qa"],
    ),
    SeededTask(
        id="docs-004",
        title="Add usage examples to docstrings in tools/session.py",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.ADD_DOCS,
        difficulty="medium",
        description="Add usage examples (doctest-style) to the main class and method docstrings "
                    "in tools/session.py showing how to use ToolSession.",
        acceptance_criteria=[
            "ToolSession class has an Example section in docstring",
            "execute_model_tool_calls has an Example section",
            "examples use valid Python that would work if run",
            "all tests pass",
        ],
        estimated_time_minutes=20,
        expected_files=["src/lyme_model/tools/session.py"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -m pytest tests/test_tools.py -x",
        hints=["Use simple examples with the 'readonly' safety mode"],
        tags=["docs", "examples"],
    ),
    SeededTask(
        id="docs-005",
        title="Write architecture decision record for trial system",
        repo_url="https://github.com/lyme-research/lyme",
        repo_path=".",
        task_type=TaskType.ADD_DOCS,
        difficulty="medium",
        description="Write an ADR (Architecture Decision Record) in docs/adr/ describing why the "
                    "trial harness was built, its design decisions, and tradeoffs.",
        acceptance_criteria=[
            "docs/adr/001-trial-harness.md exists",
            "ADR covers the context, decision, and consequences",
            "ADR mentions alternatives considered",
            "all tests pass",
        ],
        estimated_time_minutes=25,
        expected_files=["docs/adr/"],
        setup_command="pip install -e '.[dev]'",
        test_command="python -c 'open(\"docs/adr/001-trial-harness.md\").read()'",
        hints=[
            "Use Michael Nygard's ADR format",
            "Cover: why real-repo trials vs synthetic, why 25 tasks, why these 5 task types",
        ],
        tags=["docs", "adr"],
    ),
]


def get_seeded_task(task_id: str) -> SeededTask:
    for t in SEEDED_TASKS:
        if t.id == task_id:
            return t
    raise KeyError(f"Task '{task_id}' not found. Available: {[s.id for s in SEEDED_TASKS]}")


def list_seeded_tasks(task_type: TaskType = None, difficulty: str = None) -> list[SeededTask]:
    results = SEEDED_TASKS
    if task_type:
        results = [t for t in results if t.task_type == task_type]
    if difficulty:
        results = [t for t in results if t.difficulty == difficulty]
    return results
