"""v1.0 Readiness Audit — honest, evidence-based self-measurement."""

import os
import subprocess
import sys
import time
from pathlib import Path


class V1Audit:
    def __init__(self, repo_path: str = "."):
        self._repo_path = Path(repo_path).resolve()
        self._src = self._repo_path / "src"

    def audit(self) -> dict:
        reliability = self._score_reliability()
        usefulness = self._score_usefulness()
        onboarding = self._score_onboarding()
        retention = self._score_retention()
        performance = self._score_performance()
        trust = self._score_trust()
        differentiation = self._score_differentiation()
        economics = self._score_economics()

        scores = {
            "reliability": reliability,
            "usefulness": usefulness,
            "onboarding": onboarding,
            "retention": retention,
            "performance": performance,
            "trust": trust,
            "differentiation": differentiation,
            "economics": economics,
        }
        overall = sum(scores.values()) / len(scores)
        return {
            "overall_score": round(overall, 2),
            "scores": scores,
            "grade": self._grade(overall),
            "ready_for_v1": overall >= 0.7,
            "critical_gaps": self._find_gaps(scores),
            "roadmap": self._generate_roadmap(scores),
            "cut_list": self._cut_list(),
            "survival_strategy": self._survival_strategy(scores),
            "evidence": self._collect_evidence(),
        }

    def _count_tests(self) -> int:
        test_dir = self._repo_path / "tests"
        if not test_dir.is_dir():
            return 0
        return len(list(test_dir.rglob("test_*.py")))

    def _count_test_functions(self) -> int:
        test_dir = self._repo_path / "tests"
        if not test_dir.is_dir():
            return 0
        count = 0
        for f in test_dir.rglob("test_*.py"):
            try:
                content = f.read_text()
                count += content.count("def test_")
            except Exception:
                pass
        return count

    def _count_source_files(self) -> int:
        src = self._src / "lyme"
        if not src.is_dir():
            return 0
        return len(list(src.rglob("*.py")))

    def _count_total_commands(self) -> int:
        cli_path = self._src / "lyme" / "cli.py"
        if not cli_path.exists():
            return 0
        try:
            content = cli_path.read_text()
            count = 0
            for line in content.split("\n"):
                if 'add_parser("' in line and "subparsers" not in line:
                    count += 1
            return count
        except Exception:
            return 0

    def _measure_startup_time(self) -> float:
        try:
            start = time.time()
            result = subprocess.run(
                [sys.executable, "-m", "lyme", "--help"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo_path),
            )
            elapsed = time.time() - start
            return elapsed if result.returncode == 0 else 5.0
        except Exception:
            return 5.0

    def _check_has_doc_page(self, name: str) -> bool:
        docs_dir = self._repo_path / "docs"
        if not docs_dir.is_dir():
            return False
        for f in docs_dir.rglob("*.md"):
            if name.lower() in f.stem.lower():
                return True
        return False

    def _score_reliability(self) -> float:
        test_files = self._count_tests()
        test_funcs = self._count_test_functions()
        source_files = self._count_source_files()

        score = 0.3
        if test_files > 5:
            score += 0.1
        if test_files > 15:
            score += 0.1
        if test_funcs > 30:
            score += 0.1
        if test_funcs > 100:
            score += 0.1
        if source_files > 0:
            coverage_est = min(1.0, test_funcs / max(source_files * 2, 1))
            score += coverage_est * 0.1

        return round(min(1.0, score), 2)

    def _score_usefulness(self) -> float:
        score = 0.3
        heal_path = self._src / "lyme" / "heal.py"
        doctor_path = self._src / "lyme" / "doctor.py"
        fix_path = self._src / "lyme" / "edit.py"

        if doctor_path.exists():
            try:
                doc_lines = len(doctor_path.read_text().split("\n"))
                if doc_lines > 100:
                    score += 0.15
            except Exception:
                pass
        if heal_path.exists():
            try:
                heal_lines = len(heal_path.read_text().split("\n"))
                if heal_lines > 50:
                    score += 0.15
            except Exception:
                pass
        if fix_path.exists():
            score += 0.1

        has_demo = self._check_has_doc_page("heal") or self._check_has_doc_page("quickstart")
        if has_demo:
            score += 0.1

        return round(min(1.0, score), 2)

    def _score_onboarding(self) -> float:
        score = 0.2

        readme = self._repo_path / "README.md"
        if readme.exists():
            content = readme.read_text()
            if "install" in content.lower():
                score += 0.1
            if "example" in content.lower() or "quickstart" in content.lower():
                score += 0.1
            if "lyme heal" in content.lower():
                score += 0.1
            if len(content) > 3000:
                score += 0.1

        beginner_path = self._src / "lyme" / "simplify" / "beginner.py"
        if beginner_path.exists():
            score += 0.05

        has_init = self._count_total_commands() > 0
        if has_init:
            score += 0.05

        return round(min(1.0, score), 2)

    def _score_retention(self) -> float:
        score = 0.15

        beta_dir = self._src / "lyme" / "beta"
        if beta_dir.is_dir() and len(list(beta_dir.rglob("*.py"))) > 5:
            score += 0.1

        analytics_dir = self._src / "lyme" / "analytics"
        if analytics_dir.is_dir() and len(list(analytics_dir.rglob("*.py"))) > 5:
            score += 0.05

        return round(min(1.0, score), 2)

    def _score_performance(self) -> float:
        startup = self._measure_startup_time()
        score = 0.5
        if startup < 0.5:
            score += 0.3
        elif startup < 1.0:
            score += 0.2
        elif startup < 2.0:
            score += 0.1
        else:
            score -= 0.1

        has_cache = (self._src / "lyme" / "cache").is_dir()
        if has_cache:
            score += 0.1

        return round(max(0.0, min(1.0, score)), 2)

    def _score_trust(self) -> float:
        score = 0.2

        has_telemetry_consent = False
        telemetry_dir = self._src / "lyme" / "analytics"
        if telemetry_dir.is_dir():
            for f in telemetry_dir.rglob("*.py"):
                try:
                    if "consent" in f.read_text().lower() or "opt" in f.read_text().lower():
                        has_telemetry_consent = True
                        break
                except Exception:
                    pass
        if has_telemetry_consent:
            score += 0.15

        has_undo = False
        cli_path = self._src / "lyme" / "cli.py"
        if cli_path.exists():
            try:
                content = cli_path.read_text()
                if "def _do_undo" in content or "undo" in content:
                    has_undo = True
            except Exception:
                pass
        if has_undo:
            score += 0.15

        has_error_handling = False
        if cli_path.exists():
            try:
                content = cli_path.read_text()
                if "try:" in content and "except" in content:
                    has_error_handling = True
            except Exception:
                pass
        if has_error_handling:
            score += 0.1

        if self._check_has_doc_page("troubleshooting"):
            score += 0.1

        return round(min(1.0, score), 2)

    def _score_differentiation(self) -> float:
        score = 0.3

        heal_path = self._src / "lyme" / "heal.py"
        if heal_path.exists():
            try:
                heal_content = heal_path.read_text()
                if "class HealWorkflow" in heal_content:
                    score += 0.2
            except Exception:
                pass

        has_graph = (self._src / "lyme" / "graph").is_dir()
        if has_graph:
            score += 0.1

        has_discovery = (self._src / "lyme" / "discovery").is_dir()
        if has_discovery:
            score += 0.1

        has_ecosystem = (self._src / "lyme" / "ecosystem").is_dir()
        if has_ecosystem:
            score += 0.1

        return round(min(1.0, score), 2)

    def _score_economics(self) -> float:
        score = 0.3

        try:
            has_roi_module = bool(list(self._src.rglob("*/roi*.py"))) or \
                bool(list(self._src.rglob("*/economics*.py")))
            if has_roi_module:
                score += 0.15
        except Exception:
            pass

        if self._check_has_doc_page("benchmark") or self._check_has_doc_page("performance"):
            score += 0.1

        report_dir = self._repo_path / "lyme-output"
        if report_dir.is_dir() and len(list(report_dir.iterdir())) > 0:
            score += 0.1

        return round(min(1.0, score), 2)

    def _grade(self, score: float) -> str:
        if score >= 0.9:
            return "A"
        if score >= 0.8:
            return "B"
        if score >= 0.7:
            return "C"
        if score >= 0.6:
            return "D"
        return "F"

    def _find_gaps(self, scores: dict) -> list[dict]:
        gaps = []
        for k, v in scores.items():
            if v < 0.5:
                gaps.append({"area": k, "score": v, "severity": "critical"})
            elif v < 0.7:
                gaps.append({"area": k, "score": v, "severity": "needs_work"})
        return gaps

    def _generate_roadmap(self, scores: dict) -> list[dict]:
        sorted_items = sorted(scores.items(), key=lambda x: x[1])
        roadmap = []
        for area, score in sorted_items:
            if score < 0.7:
                roadmap.append({
                    "area": area,
                    "current_score": score,
                    "priority": "high" if score < 0.5 else "medium",
                    "effort": self._estimate_effort(area),
                    "suggestion": self._suggest_improvement(area),
                })
        return roadmap

    def _estimate_effort(self, area: str) -> str:
        efforts = {
            "reliability": "high",
            "usefulness": "high",
            "onboarding": "medium",
            "retention": "high",
            "performance": "low",
            "trust": "medium",
            "differentiation": "low",
            "economics": "low",
        }
        return efforts.get(area, "medium")

    def _suggest_improvement(self, area: str) -> str:
        suggestions = {
            "reliability": f"Write tests. Only {self._count_test_functions()} test functions across {self._count_tests()} test files. Target 100+ test functions for core commands.",
            "usefulness": "Make 'lyme heal' the one-command killer workflow: diagnose → prioritize → fix → verify → report. Currently partial implementation.",
            "onboarding": "Create first-run wizard. Add 'lyme start' that walks through heal in under 60 seconds. README needs explicit install/quickstart.",
            "retention": "No retention loop exists. Add daily value commends, weekly progress reports, and churn detection.",
            "performance": f"CLI startup is too slow. Measure with 'lyme profile run'. Add lazy imports and caching.",
            "trust": "Add telemetry consent on first run. Publish security audit. Add undo confirmation for all destructive operations.",
            "differentiation": "Mature the heal workflow. Publish comparison benchmarks against other dev tools.",
            "economics": "Publish ROI comparison data. Show time saved with 'lyme heal' vs manual debugging.",
        }
        return suggestions.get(area, "Review and improve")

    def _cut_list(self) -> list[str]:
        return [
            "Remove all demo-v0* commands (deprecated demos)",
            "Remove civ-map (never used, experimental)",
            "Remove epistemology (never used, experimental)",
            "Remove govern/constitution (never used, experimental)",
            "Remove similar/compress/fabric (never used, experimental)",
            "Remove cross-repo (never used, experimental)",
            "Remove tradeoff/decisions/roadmap (never used, experimental)",
            "Remove maintain/detect (never used, experimental)",
            "Remove learn/predict/intent (never used, experimental)",
            "Merge observe into observe-v2",
            "Merge run into bench",
            "Merge trace-std into trace",
            "Merge semantic-diff into diff",
            "Merge benchmark into bench",
            "Hide 'society' behind --experimental flag",
            "Hide 'evolution' behind --experimental flag",
            "Hide 'research' behind --experimental flag",
        ]

    def _survival_strategy(self, scores: dict) -> str:
        weak = [k for k, v in scores.items() if v < 0.6]
        strong = [k for k, v in scores.items() if v >= 0.6]
        return (
            f"Strengths: {', '.join(strong) or 'none'}. "
            f"Focus entirely on fixing: {', '.join(weak)}. "
            "Cut 50% of commands. Ship 'lyme heal' as the headline workflow. "
            "Publish credibility report and economic analysis concurrently."
        )

    def _collect_evidence(self) -> dict:
        return {
            "test_files": self._count_tests(),
            "test_functions": self._count_test_functions(),
            "source_files": self._count_source_files(),
            "total_commands_estimated": self._count_total_commands(),
            "startup_time_seconds": round(self._measure_startup_time(), 2),
        }

    def get_report_text(self) -> str:
        report = self.audit()
        evidence = report.get("evidence", {})
        lines = []
        lines.append("=" * 55)
        lines.append("  LYME v1.0 READINESS AUDIT")
        lines.append("=" * 55)
        lines.append(f"  Overall: {report['overall_score']:.2f} / 1.0  Grade: {report['grade']}")
        lines.append(f"  Ready for v1.0: {'YES' if report['ready_for_v1'] else 'NO'}")
        lines.append("")
        for k, v in report['scores'].items():
            bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
            icon = "✓" if v >= 0.7 else ("!" if v >= 0.5 else "✗")
            lines.append(f"  {icon} {k:20s} {v:.2f}  [{bar}]")
        lines.append("")
        if evidence:
            lines.append("  Evidence:")
            lines.append(f"    Test files:      {evidence.get('test_files', '?')}")
            lines.append(f"    Test functions:  {evidence.get('test_functions', '?')}")
            lines.append(f"    Source files:    {evidence.get('source_files', '?')}")
            lines.append(f"    Commands:        ~{evidence.get('total_commands_estimated', '?')}")
            lines.append(f"    Startup time:    {evidence.get('startup_time_seconds', '?')}s")
            lines.append("")
        lines.append("  Critical gaps:")
        for g in report['critical_gaps']:
            lines.append(f"    {g['severity'].upper()}: {g['area']} ({g['score']:.2f})")
        lines.append("")
        lines.append("  Priority roadmap:")
        for item in report['roadmap'][:5]:
            lines.append(f"    [{item['priority']:6s}] [{item['effort']:6s}] {item['area']:20s} → {item['suggestion'][:70]}")
        lines.append("")
        lines.append("  Cut list (reduce commands by 50%):")
        for c in report['cut_list'][:10]:
            lines.append(f"    - {c}")
        lines.append("")
        lines.append("  Survival strategy:")
        lines.append(f"    {report['survival_strategy']}")
        lines.append("=" * 55)
        return "\n".join(lines)
