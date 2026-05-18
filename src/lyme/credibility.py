"""Benchmark credibility: reproducibility, transparency, and trust."""


class CredibilityReport:
    def __init__(self):
        self._scores = {}

    def assess(self) -> dict:
        self._scores = {
            "reproducibility": self._score_reproducibility(),
            "transparency": self._score_transparency(),
            "human_review": self._score_human_review(),
            "randomization": self._score_randomization(),
            "full_disclosure": self._score_full_disclosure(),
        }
        return self._compute_report()

    def _score_reproducibility(self) -> float:
        score = 0.0
        replay_dir = __import__('pathlib').Path(".lyme") / "benchmarks"
        if replay_dir.is_dir():
            trace_files = list(replay_dir.rglob("*.json"))
            score = min(1.0, len(trace_files) / 10.0)
            if trace_files:
                score = max(score, 0.3)
        return round(score, 2)

    def _score_transparency(self) -> float:
        score = 0.0
        score += 0.2  # CLI always records commands
        score += 0.2  # Telemetry consent system exists
        score += 0.1  # Crash reporting exists
        return round(min(score, 1.0), 2)

    def _score_human_review(self) -> float:
        return 0.0

    def _score_randomization(self) -> float:
        return 0.0

    def _score_full_disclosure(self) -> float:
        score = 0.0
        score += 0.2
        return round(score, 2)

    def _compute_report(self) -> dict:
        overall = sum(self._scores.values()) / max(len(self._scores), 1)
        weaknesses = []
        for k, v in self._scores.items():
            if v < 0.5:
                weaknesses.append({
                    "area": k,
                    "score": v,
                    "gap": f"Score {v}/1.0 — needs improvement",
                    "action": self._recommend_action(k),
                })
        return {
            "overall_credibility": round(overall, 2),
            "scores": self._scores,
            "grade": self._grade(overall),
            "weaknesses": weaknesses,
            "strengths": [
                k for k, v in self._scores.items() if v >= 0.7
            ],
        }

    def _grade(self, score: float) -> str:
        if score >= 0.9:
            return "A"
        if score >= 0.8:
            return "B"
        if score >= 0.6:
            return "C"
        if score >= 0.4:
            return "D"
        return "F"

    def _recommend_action(self, area: str) -> str:
        actions = {
            "reproducibility": "Publish full trace artifacts alongside every benchmark result",
            "transparency": "Record and expose all evaluation parameters",
            "human_review": "Implement human verification layer for benchmark results",
            "randomization": "Add random task ordering and hidden test sets",
            "full_disclosure": "Publish failure cases alongside successes",
        }
        return actions.get(area, "Review and improve methodology")

    def get_report_text(self) -> str:
        report = self.assess()
        lines = []
        lines.append("=" * 55)
        lines.append("  LYME BENCHMARK CREDIBILITY REPORT")
        lines.append("=" * 55)
        lines.append(f"  Overall: {report['overall_credibility']:.2f} / 1.0  Grade: {report['grade']}")
        lines.append("")
        for k, v in report['scores'].items():
            bar = "█" * int(v * 20) + "░" * (20 - int(v * 20))
            lines.append(f"  {k:20s} {v:.2f}  [{bar}]")
        lines.append("")
        if report['weaknesses']:
            lines.append("  Weaknesses:")
            for w in report['weaknesses']:
                lines.append(f"    ✗ {w['area']}: {w['action']}")
        if report['strengths']:
            lines.append("  Strengths:")
            for s in report['strengths']:
                lines.append(f"    ✓ {s}")
        lines.append("=" * 55)
        return "\n".join(lines)
