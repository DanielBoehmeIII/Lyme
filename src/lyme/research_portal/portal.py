import json
import time
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from pathlib import Path


@dataclass
class LeaderboardEntry:
    rank: int = 0
    agent_name: str = ""
    model: str = ""
    overall_score: float = 0.0
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    tasks_completed: int = 0
    total_tasks: int = 0
    benchmark_version: str = "0.7.0"
    submitted_at: float = field(default_factory=time.time)
    trace_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class BenchmarkLeaderboard:
    name: str = "Lyme Software Cognition Benchmark"
    version: str = "0.7.0"
    entries: List[LeaderboardEntry] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

    def add_entry(self, entry: LeaderboardEntry):
        self.entries.append(entry)
        self.entries.sort(key=lambda e: -e.overall_score)
        for i, e in enumerate(self.entries, 1):
            e.rank = i
        self.last_updated = time.time()

    def top_n(self, n: int = 10) -> List[LeaderboardEntry]:
        return self.entries[:n]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "entries": [e.to_dict() for e in self.entries],
            "last_updated": self.last_updated,
        }


@dataclass
class FailureTaxonomy:
    categories: Dict[str, List[str]] = field(default_factory=lambda: {
        "reasoning": [
            "wrong_root_cause", "incomplete_causal_chain",
            "hallucinated_evidence", "logical_error",
        ],
        "execution": [
            "tool_misuse", "syntax_error", "import_error",
            "test_failure", "build_failure",
        ],
        "safety": [
            "unsafe_operation", "bypassed_review",
            "data_loss_risk", "security_regression",
        ],
        "verification": [
            "insufficient_coverage", "false_positive",
            "false_negative", "skipped_verification",
        ],
        "memory": [
            "failed_transfer", "stale_knowledge",
            "context_confusion", "missed_pattern",
        ],
    })
    severity_map: Dict[str, str] = field(default_factory=lambda: {
        "wrong_root_cause": "critical",
        "unsafe_operation": "critical",
        "hallucinated_evidence": "high",
        "insufficient_coverage": "medium",
        "tool_misuse": "medium",
        "missed_pattern": "low",
    })
    recovery_strategies: Dict[str, str] = field(default_factory=lambda: {
        "wrong_root_cause": "retry_with_additional_evidence",
        "unsafe_operation": "require_human_approval",
        "insufficient_coverage": "run_expanded_test_suite",
        "tool_misuse": "retry_with_correct_tool_params",
        "hallucinated_evidence": "verify_claims_against_codebase",
    })

    def classify(self, failure_type: str) -> Optional[str]:
        for category, types in self.categories.items():
            if failure_type in types:
                return category
        return None

    def severity(self, failure_type: str) -> str:
        return self.severity_map.get(failure_type, "medium")

    def to_dict(self) -> dict:
        return {
            "categories": self.categories,
            "severity_map": self.severity_map,
            "recovery_strategies": self.recovery_strategies,
        }


@dataclass
class ResearchReport:
    report_id: str = ""
    title: str = ""
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    methodology: str = ""
    results: dict = field(default_factory=dict)
    conclusions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    related_entries: List[str] = field(default_factory=list)
    published_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown(self) -> str:
        lines = [
            f"# {self.title}",
            f"",
            f"**Authors**: {', '.join(self.authors)}",
            f"**Report ID**: {self.report_id}",
            f"",
            f"## Abstract",
            f"{self.abstract}",
            f"",
            f"## Methodology",
            f"{self.methodology}",
            f"",
            f"## Results",
        ]
        for k, v in self.results.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")
        lines.append("## Conclusions")
        for c in self.conclusions:
            lines.append(f"- {c}")
        if self.open_questions:
            lines.append("")
            lines.append("## Open Questions")
            for q in self.open_questions:
                lines.append(f"- {q}")
        return "\n".join(lines)


@dataclass
class AblationResult:
    component: str = ""
    full_system_score: float = 0.0
    ablated_score: float = 0.0
    impact: float = 0.0
    description: str = ""
    tasks_affected: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ModelComparison:
    models: List[str] = field(default_factory=list)
    dimension: str = ""
    scores: Dict[str, float] = field(default_factory=dict)
    winner: str = ""
    margin: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OpenQuestion:
    question: str = ""
    category: str = ""
    importance: str = "medium"
    status: str = "open"
    related_dimensions: List[str] = field(default_factory=list)
    proposed_experiments: List[str] = field(default_factory=list)
    raised_by: str = ""
    raised_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PortalConfig:
    output_dir: str = "lyme-output/research-portal"
    title: str = "Lyme Research Portal"
    description: str = "Scientific research infrastructure for coding agent cognition"
    maintainers: List[str] = field(default_factory=lambda: ["Lyme Project"])


class ResearchPortal:
    def __init__(self, config: Optional[PortalConfig] = None):
        self.config = config or PortalConfig()
        self.leaderboard = BenchmarkLeaderboard()
        self.failure_taxonomy = FailureTaxonomy()
        self.reports: List[ResearchReport] = []
        self.ablations: List[AblationResult] = []
        self.comparisons: List[ModelComparison] = []
        self.open_questions: List[OpenQuestion] = []
        self._output = Path(self.config.output_dir)

    def add_report(self, report: ResearchReport):
        self.reports.append(report)
        self._save("reports", report.report_id, report.to_dict())

    def add_ablation(self, result: AblationResult):
        self.ablations.append(result)
        self._save("ablations", result.component, result.to_dict())

    def add_comparison(self, comparison: ModelComparison):
        self.comparisons.append(comparison)
        self._save("comparisons", f"{comparison.dimension}-{len(self.comparisons)}", comparison.to_dict())

    def add_question(self, question: OpenQuestion):
        self.open_questions.append(question)
        self._save("questions", question.question[:30], question.to_dict())

    def _save(self, subdir: str, name: str, data: dict):
        path = self._output / subdir
        path.mkdir(parents=True, exist_ok=True)
        fname = name.replace(" ", "_").replace("/", "_")[:60]
        with open(path / f"{fname}.json", "w") as f:
            json.dump(data, f, indent=2, default=str)

    def generate_index_html(self) -> str:
        lb = self.leaderboard.top_n(10)
        lb_rows = "\n".join(
            f"<tr><td>{e.rank}</td><td>{e.agent_name}</td>"
            f"<td>{e.model}</td><td>{e.overall_score:.3f}</td>"
            f"<td>{e.tasks_completed}/{e.total_tasks}</td></tr>"
            for e in lb
        )

        reports_section = "\n".join(
            f"<li><a href='reports/{r.report_id}.json'>{r.title}</a>"
            f" ({', '.join(r.authors)})</li>"
            for r in self.reports[-5:]
        )

        questions_section = "\n".join(
            f"<li><strong>[{q.category}]</strong> {q.question} "
            f"(<em>{q.status}</em>)</li>"
            for q in self.open_questions[-5:]
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8">
<title>{self.config.title}</title>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:960px;
margin:40px auto;padding:0 20px;line-height:1.6;color:#1a1a2e;background:#f8f9fa}}
h1,h2,h3{{color:#16213e}}table{{border-collapse:collapse;width:100%;margin:16px 0}}
th,td{{border:1px solid #e2e8f0;padding:8px 12px;text-align:left}}
th{{background:#e2e8f0}}.badge{{display:inline-block;padding:2px 8px;
border-radius:12px;font-size:12px;font-weight:600}}
.badge-open{{background:#fefcbf;color:#975a16}}
.badge-exploring{{background:#bee3f8;color:#2a4365}}
.section{{margin:32px 0;padding:16px;background:white;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1)}}
</style></head>
<body>
<h1>{self.config.title}</h1>
<p>{self.config.description}</p>
<p>Maintainers: {', '.join(self.config.maintainers)}</p>

<div class="section">
<h2>Leaderboard (Top {len(lb)})</h2>
<table><tr><th>#</th><th>Agent</th><th>Model</th><th>Score</th><th>Tasks</th></tr>
{lb_rows}</table>
</div>

<div class="section">
<h2>Failure Taxonomy</h2>
<p>Categories: {', '.join(self.failure_taxonomy.categories.keys())}</p>
<p>Total failure types: {sum(len(v) for v in self.failure_taxonomy.categories.values())}</p>
</div>

<div class="section">
<h2>Research Reports ({len(self.reports)})</h2>
<ul>{reports_section}</ul>
</div>

<div class="section">
<h2>Ablation Studies ({len(self.ablations)})</h2>
<ul>{"".join(f'<li>{a.component}: {a.impact:+.1%}</li>' for a in self.ablations[-5:])}</ul>
</div>

<div class="section">
<h2>Open Questions ({len(self.open_questions)})</h2>
<ul>{questions_section}</ul>
</div>

<div class="section">
<h2>Model Comparisons ({len(self.comparisons)})</h2>
<ul>{"".join(f'<li>{c.dimension}: {", ".join(c.models)} — winner: {c.winner}</li>'
           for c in self.comparisons[-5:])}</ul>
</div>

<p><em>Generated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</em></p>
</body></html>"""

    def save_portal(self):
        self._output.mkdir(parents=True, exist_ok=True)
        html = self.generate_index_html()
        with open(self._output / "index.html", "w") as f:
            f.write(html)
        with open(self._output / "leaderboard.json", "w") as f:
            json.dump(self.leaderboard.to_dict(), f, indent=2, default=str)
        print(f"Research portal saved to {self._output / 'index.html'}")
