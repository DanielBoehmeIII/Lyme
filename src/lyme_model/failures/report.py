"""Week 73 — CLI report generator for local coding agent failures.

Outputs formatted reports showing failure taxonomy, detected failures,
metrics, and mitigation recommendations.
"""

from __future__ import annotations
from typing import List, Optional
from datetime import datetime, timezone
from pathlib import Path
import json

from .taxonomy import (
    LocalCodingFailureCategory,
    LOCAL_CODING_TAXONOMY,
    LocalCodingFailureRecord,
    LocalCodingFailureAnalysis,
)
from .detector import DETECTOR_RULES
from .metrics import FailureMetrics


def generate_cli_report(
    analysis: Optional[LocalCodingFailureAnalysis] = None,
    metrics: Optional[FailureMetrics] = None,
    output_path: Optional[str] = None,
) -> str:
    """Generate a formatted CLI report for local coding agent failures."""
    lines = []
    lines.append("=" * 72)
    lines.append("  LYME MODEL — LOCAL CODING AGENT ERROR TAXONOMY REPORT")
    lines.append("=" * 72)
    lines.append(f"  Generated: {datetime.now(timezone.utc).isoformat()[:19]}")
    lines.append(f"  System: Lyme Audit (measure) + Lyme Model (compete)")
    lines.append("")

    # Section 1: Taxonomy overview
    lines.append("-" * 72)
    lines.append("  1. FAILURE TAXONOMY (12 categories)")
    lines.append("-" * 72)
    for cat in LocalCodingFailureCategory:
        info = LOCAL_CODING_TAXONOMY.get(cat, {})
        sev = info.get("severity", "?").upper()
        lines.append(f"  [{sev:8s}] {cat.value:35s} {info.get('description', '')[:60]}")
    lines.append("")

    # Section 2: Detector rules
    lines.append("-" * 72)
    lines.append("  2. DETECTOR RULES ({0} total)".format(len(DETECTOR_RULES)))
    lines.append("-" * 72)
    for rule in sorted(DETECTOR_RULES, key=lambda r: r.priority):
        lines.append(f"  [{rule.cost:8s}] {rule.name:40s} -> {rule.category.value}")
    lines.append("")

    # Section 3: Analysis results
    if analysis:
        lines.append("-" * 72)
        lines.append("  3. FAILURE ANALYSIS")
        lines.append("-" * 72)
        lines.append(f"  Total failures: {analysis.total_count}")
        lines.append(f"  Mitigation rate: {analysis.mitigation_rate:.0%}")
        lines.append(f"  Summary: {analysis.summary}")
        lines.append("")
        if analysis.by_category:
            lines.append("  By Category:")
            for cat, count in sorted(analysis.by_category.items(), key=lambda x: -x[1]):
                lines.append(f"    {cat:40s} {count}")
        lines.append("")
        if analysis.by_severity:
            lines.append("  By Severity:")
            for sev, count in sorted(analysis.by_severity.items(), key=lambda x: -x[1]):
                lines.append(f"    {sev:40s} {count}")
        lines.append("")
        for f in analysis.failures:
            lines.append(f"  {f.cli_line()}")
            if f.mitigated_by:
                lines.append(f"    -> Mitigated: {f.mitigated_by}")
        lines.append("")

    # Section 4: Metrics
    if metrics:
        lines.append("-" * 72)
        lines.append("  4. FAILURE METRICS")
        lines.append("-" * 72)
        lines.append(f"  Window: {metrics.window_label}")
        lines.append(f"  Total runs: {metrics.total_runs}")
        lines.append(f"  Total failures: {metrics.total_failures}")
        lines.append(f"  Failure rate: {metrics.failure_rate:.1%}")
        lines.append(f"  Mitigation success: {metrics.mitigation_success_rate:.1%}")
        lines.append(f"  Trend: {metrics.trend_direction}")
        lines.append("")

    # Section 5: Examples
    lines.append("-" * 72)
    lines.append("  5. FAILURE EXAMPLES (one per category)")
    lines.append("-" * 72)
    examples = {
        "missing_context": (
            'Task: "Add error handling to the login function."\n'
            '  Model output: "Here is the updated login() function."\n'
            '  Problem: Model never read login.py, assumed wrong file.\n'
            '  Signal: audit trace shows no read_file before edit_file.'
        ),
        "wrong_file_selected": (
            'Task: "Fix the bug in user auth."\n'
            '  Model edited: src/utils/helpers.py (contained similar function name)\n'
            '  Should have edited: src/auth/login.py\n'
            '  Signal: edit targets file not mentioned in task.'
        ),
        "hallucinated_api": (
            'Task: "Add pagination to the API."\n'
            '  Model output: Called paginate_results() which does not exist in codebase.\n'
            '  Signal: import error on generated code.'
        ),
        "bad_patch": (
            'Task: "Fix the off-by-one error."\n'
            '  Model patch: Indentation error, missing closing paren, imports broken.\n'
            '  Signal: patch fails syntax check or does not apply.'
        ),
        "incomplete_patch": (
            'Task: "Add validation to create_user."\n'
            '  Model patch: Added validation but did not update the model or migration.\n'
            '  Signal: tests still failing after patch.'
        ),
        "test_misunderstanding": (
            'Task: "Fix the failing test."\n'
            '  Model patch: Changed test assertion instead of fixing source code.\n'
            '  Signal: model edited test file without editing source.'
        ),
        "command_misuse": (
            'Task: "Run the tests."\n'
            '  Model ran: pytest --flags --that --dont --exist\n'
            '  Signal: non-zero exit code, command not found.'
        ),
        "syntax_regression": (
            'Task: "Add a new endpoint."\n'
            '  Model patch: Missing colon, mismatched quotes, undefined variables.\n'
            '  Signal: python SyntaxError after patch.apply().'
        ),
        "architectural_misunderstanding": (
            'Task: "Add caching to the service layer."\n'
            '  Model patch: Added caching directly in the controller instead of the service.\n'
            '  Signal: change violates layer boundaries.'
        ),
        "excessive_latency": (
            'Task: "Refactor the database layer."\n'
            '  Model took 120s on a 3B model with full repo context.\n'
            '  Signal: total_time > 30s threshold.'
        ),
        "context_overflow": (
            'Task: "Fix all bugs in the project."\n'
            '  Context: 12,000 tokens across 25 files (model max: 4096).\n'
            '  Signal: model output ignores instructions from later context.'
        ),
        "tool_loop_failure": (
            'Trace: read_file -> read_file -> read_file -> read_file (same file 4x)\n'
            '  No edit_file or progress after 6 tool calls.\n'
            '  Signal: same tool called >3x without changes.'
        ),
    }
    for cat in LocalCodingFailureCategory:
        ex = examples.get(cat.value, "No example available.")
        lines.append(f"  [{cat.value}]")
        for ex_line in ex.split("\n"):
            lines.append(f"    {ex_line}")
        lines.append("")

    # Section 6: Recommendations
    lines.append("-" * 72)
    lines.append("  6. MITIGATION RECOMMENDATIONS")
    lines.append("-" * 72)
    mitigations = {
        "missing_context": "Add retrieval policy before every generation.",
        "wrong_file_selected": "Verify file path matches task intent before edit.",
        "hallucinated_api": "Force AST inspection step before referencing symbols.",
        "bad_patch": "Add syntax check and patch dry-run before apply.",
        "incomplete_patch": "Require dependency impact analysis before patching.",
        "test_misunderstanding": "Parse test output structurally; highlight assertions.",
        "command_misuse": "Cache successful commands; validate before running.",
        "syntax_regression": "Run linter after every edit; provide AST context.",
        "architectural_misunderstanding": "Provide architecture summary card before tasks.",
        "excessive_latency": "Cache aggressively; use smaller draft model.",
        "context_overflow": "Prioritize and compress context packets.",
        "tool_loop_failure": "Add loop detection; enforce max retry limits.",
    }
    for rule_name, mitigation in sorted(mitigations.items()):
        lines.append(f"  {rule_name:35s} {mitigation}")
    lines.append("")
    lines.append("=" * 72)
    lines.append("  REPORT END")
    lines.append("=" * 72)

    report = "\n".join(lines)

    if output_path:
        Path(output_path).write_text(report)
        print(f"Report written to {output_path}")

    return report


def detect_and_report(trace: dict, output_path: Optional[str] = None) -> str:
    """Convenience: run detection and generate report for a single trace."""
    from .detector import LocalCodingFailureDetector

    detector = LocalCodingFailureDetector()
    failures = detector.detect(trace)
    analysis = detector.analyze(failures)

    total_runs = trace.get("total_runs", 1)
    from .metrics import compute_failure_metrics
    metrics = compute_failure_metrics(failures, total_runs=total_runs)

    return generate_cli_report(
        analysis=analysis,
        metrics=metrics,
        output_path=output_path,
    )
