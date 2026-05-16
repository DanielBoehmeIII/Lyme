"""Lyme First Demo — Show both Product and Research sides.

Usage:
    python -m lyme demo [--repo <path>] [--all]
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import time
import sys
import json


DEMO_SCRIPT = """
╔══════════════════════════════════════════════════════════════╗
║           Lyme — Local-first Coding Agent Research           ║
║     Not another coding agent. The observatory for them.      ║
╚══════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PHASE 1: PRODUCT — What Lyme Does For You
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 1. lyme doctor — Diagnose your repository
    → Language, framework, build commands, test coverage
    → Risky files, architectural hotspots, stale areas
    → Suggested improvements

 2. lyme ask — Evidence-grounded Q&A
    → Every claim has file/function/git citations
    → Confidence scores and uncertainty markers
    → Refuses unsupported claims

 3. lyme diff — Semantic diff classification
    → Understand what changed, not just what's different
    → Categorizes diffs as structural/behavioral/dependency/cosmetic

 4. lyme trace — Execution trace viewer
    → See exactly what the agent did, step by step
    → Decision trees, tool calls, confidence scores

 5. lyme memory — Persistent agent memory
    → Agents learn across sessions
    → Memory distillation and pruning

 6. lyme fix — Safe, auditable code fixes
    → Explain before editing
    → Reversible patches with rollback

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PHASE 2: RESEARCH — What Lyme Discovers About Agents
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 7. Cognitive traces — See how agents think
    → Decision points, alternatives, branch exploration
    → Hallucination detection in real-time

 8. Causal graphs — Model cause-effect in your code
    → Find hidden dependencies and risk amplification zones
    → Predict breakage before it happens

 9. Invariant discovery — Learn your architecture's rules
    → Automatically infer naming, structure, and dependency invariants
    → Detect violations before they cause bugs

10. Scaling laws — Measure how agents scale
    → Performance vs model size, context budget, compression ratio
    → Find emergence thresholds and diminishing returns

11. Agent coordination — Study multi-agent systems
    → Debate quality, specialization emergence
    → Coordination overhead measurement

12. Context degradation — The collapse you can't see
    → Measure how accuracy decays with context size
    → Find your repository's collapse point

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 WHY LYME IS DIFFERENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 Every product action generates research data.
 Every research insight improves product behavior.

 Not another chat UI.
 Not another API wrapper.
 Not another benchmark toy.

 Local-first. Observable. Measurable.
"""


@dataclass
class DemoStep:
    name: str
    product_face: str
    research_face: str
    command: str
    expected_output_preview: str
    failure_fallback: str
    duration_seconds: float = 30.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "product_face": self.product_face,
            "research_face": self.research_face,
            "command": self.command,
            "expected_output_preview": self.expected_output_preview,
            "failure_fallback": self.failure_fallback,
        }


TARGET_REPO_CRITERIA = {
    "ideal": [
        "Python or TypeScript project (best analysis support)",
        "500-5000 files (not trivial, not overwhelming)",
        "Has tests (pytest, jest, or similar)",
        "Has git history (at least 50 commits)",
        "Has multiple modules/packages (non-trivial architecture)",
        "Has some documentation (README, docstrings)",
        "Open source (can be demoed publicly)",
    ],
    "acceptable": [
        "Any language with AST-parsable files",
        "At least 10 files in src/ or lib/",
        "Has a build file (pyproject.toml, package.json, etc.)",
    ],
    "not_suitable": [
        "Single-file scripts",
        "Binary-only projects (no source code)",
        "Empty repositories",
        "Proprietary code you can't show",
    ],
}


DEMO_STEPS = [
    DemoStep(
        name="Repo Doctor",
        product_face="See a complete health diagnosis of your repository",
        research_face="Graph quality metrics, invariant hypotheses, failure zones",
        command="lyme doctor",
        expected_output_preview="Language, framework, build commands, risky files, hotspots, suggestions",
        failure_fallback="Run on Lyme's own repo — always available",
    ),
    DemoStep(
        name="Ask With Evidence",
        product_face="Ask questions and get citations for every claim",
        research_face="Confidence calibration, refusal accuracy, evidence quality",
        command='lyme ask "What language is this? Are there tests?"',
        expected_output_preview="Evidence answer with file citations, confidence scores, contradiction warnings",
        failure_fallback="Show the markdown answer output file",
    ),
    DemoStep(
        name="Semantic Diff",
        product_face="Understand diffs by semantic category",
        research_face="Diff classification accuracy, taxonomy validation",
        command="lyme diff <file>",
        expected_output_preview="Diffs classified as structural/behavioral/dependency/cosmetic",
        failure_fallback="Use stored example diff from lyme-output",
    ),
    DemoStep(
        name="Causal Graph",
        product_face="See hidden dependencies and risk zones",
        research_face="Causal structure validation, risk prediction accuracy",
        command="lyme graph infer .",
        expected_output_preview="Causal graph with risk scores, amplification zones",
        failure_fallback="Show pre-generated HTML visualization",
    ),
    DemoStep(
        name="Invariant Discovery",
        product_face="Auto-discover your architecture's rules",
        research_face="Invariant completeness, false positive rate",
        command="lyme discover invariants .",
        expected_output_preview="Named invariants with severity, confidence, and evidence",
        failure_fallback="Show pre-computed invariant set",
    ),
    DemoStep(
        name="Trace Viewer",
        product_face="Step through an agent's execution",
        research_face="Decision quality vs outcome correlation",
        command="lyme ui thought <run-id>",
        expected_output_preview="Decision tree with confidence scores and branch exploration",
        failure_fallback="Open pre-generated HTML thought viewer",
    ),
    DemoStep(
        name="Scaling Laws",
        product_face="Compare models on your repository tasks",
        research_face="Emergence thresholds, diminishing returns, optimal budget",
        command="lyme research scaling --auto",
        expected_output_preview="Scaling coefficients, emergence thresholds, recommendations",
        failure_fallback="Show pre-computed scaling law report",
    ),
]


class DemoRunner:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.results: List[dict] = []

    def show_banner(self):
        print(DEMO_SCRIPT)

    def check_repo_suitability(self) -> dict:
        result = {"suitable": True, "warnings": [], "reasons": []}

        if not self.repo_path.is_dir():
            result["suitable"] = False
            result["reasons"].append("Path is not a directory")
            return result

        files = list(self.repo_path.rglob("*"))
        source_files = [f for f in files if f.is_file() and f.suffix.lower() in
                       (".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java")]

        if len(source_files) < 10:
            result["warnings"].append("Fewer than 10 source files — results may be limited")

        if not (self.repo_path / ".git").is_dir():
            result["warnings"].append("No git history — temporal analysis disabled")

        result["source_file_count"] = len(source_files)
        result["total_file_count"] = len([f for f in files if f.is_file()])

        return result

    def run_step(self, step: DemoStep, index: int) -> dict:
        result = {
            "step": step.name,
            "index": index,
            "status": "running",
            "product_output": "",
            "research_output": "",
        }
        print(f"\n{'='*60}")
        print(f"  Step {index+1}/{len(DEMO_STEPS)}: {step.name}")
        print(f"{'='*60}")
        print(f"  Product: {step.product_face}")
        print(f"  Research: {step.research_face}")
        print(f"  Command: {step.command}")
        print()
        return result

    def generate_demo_report(self) -> str:
        lines = []
        lines.append("# Lyme Demo Report")
        lines.append("")
        lines.append(f"**Repository**: {self.repo_path}")
        lines.append(f"**Steps completed**: {len(self.results)}/{len(DEMO_STEPS)}")
        lines.append("")

        suitability = self.check_repo_suitability()
        lines.append("## Repository Suitability")
        lines.append(f"- Suitable: {suitability['suitable']}")
        lines.append(f"- Source files: {suitability.get('source_file_count', 0)}")
        lines.append(f"- Total files: {suitability.get('total_file_count', 0)}")
        for w in suitability.get('warnings', []):
            lines.append(f"- ⚠ {w}")
        lines.append("")

        lines.append("## Demo Flow")
        for i, step in enumerate(DEMO_STEPS):
            lines.append(f"### {i+1}. {step.name}")
            lines.append(f"**Command**: `{step.command}`")
            lines.append(f"**Product**: {step.product_face}")
            lines.append(f"**Research**: {step.research_face}")
            lines.append(f"**Fallback**: {step.failure_fallback}")
            lines.append("")

        lines.append("## Why Lyme Is Not Just Another Coding Agent")
        lines.append("")
        lines.append("1. **Every product action generates research data**")
        lines.append("   - `lyme doctor` collects graph quality metrics and invariant hypotheses")
        lines.append("   - `lyme ask` measures confidence calibration and evidence quality")
        lines.append("   - `lyme fix` records safe edit protocol effectiveness")
        lines.append("")
        lines.append("2. **Every research insight improves product behavior**")
        lines.append("   - Hallucination detection improves answer reliability")
        lines.append("   - Causal graphs enable risk-aware editing")
        lines.append("   - Invariant discovery creates architectural guardrails")
        lines.append("   - Scaling laws optimize model selection and context budgets")
        lines.append("")
        lines.append("3. **Local-first, privacy-preserving**")
        lines.append("   - All data stays on your machine")
        lines.append("   - Explicit privacy boundaries between product and research layers")
        lines.append("   - Sanitized research data when crossing the boundary")
        lines.append("")
        lines.append("4. **Measurable, not vibes-based**")
        lines.append("   - Confidence scores for every claim")
        lines.append("   - Uncertainty estimates for every diagnosis")
        lines.append("   - Evidence trails for every answer")
        lines.append("   - Failure taxonomy for every error")
        lines.append("")

        return "\n".join(lines)

    def run(self, all_steps: bool = False):
        self.show_banner()

        print("\n" + "="*60)
        print("  REPOSITORY CHECK")
        print("="*60)
        suitability = self.check_repo_suitability()
        print(f"  Path: {self.repo_path}")
        print(f"  Source files: {suitability.get('source_file_count', 0)}")
        print(f"  Total files: {suitability.get('total_file_count', 0)}")
        for w in suitability.get('warnings', []):
            print(f"  ⚠ {w}")
        print()

        steps = DEMO_STEPS if all_steps else DEMO_STEPS[:4]

        for i, step in enumerate(steps):
            result = self.run_step(step, i)
            time.sleep(0.5)
            print(f"  Expected output:")
            print(f"  {step.expected_output_preview}")
            print()
            print(f"  Fallback if fails: {step.failure_fallback}")
            print()
            result["status"] = "ready"
            self.results.append(result)

        report = self.generate_demo_report()
        print("\n" + "="*60)
        print("  DEMO COMPLETE")
        print("="*60)
        print(f"  Steps shown: {len(self.results)}")
        print(f"  Report generated")
        print()

        return report


def run_demo(repo_path: Optional[str] = None, all_steps: bool = False):
    path = Path(repo_path).resolve() if repo_path else Path.cwd()
    runner = DemoRunner(path)
    report = runner.run(all_steps=all_steps)

    report_path = Path("lyme-demo-report.md")
    report_path.write_text(report)
    print(f"Demo report written to {report_path}")
    return report
