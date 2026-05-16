"""Week 93 — Training Data Reality Check.

Audits all Lyme Audit traces and generated artifacts for training usefulness.
Classifies data into 6 categories and produces inventory, quality scores, risks.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import os


class DataCategory:
    SFT = "usable_for_supervised_fine_tuning"
    TOOL_POLICY = "usable_for_tool_policy_learning"
    RETRIEVAL_POLICY = "usable_for_retrieval_policy_learning"
    PATCH_CRITIQUE = "usable_for_patch_critique"
    EVAL_ONLY = "usable_only_for_evaluation"
    UNUSABLE = "unusable_synthetic_misleading"


CATEGORY_LABELS = {
    DataCategory.SFT: "Supervised Fine-Tuning",
    DataCategory.TOOL_POLICY: "Tool-Policy Learning",
    DataCategory.RETRIEVAL_POLICY: "Retrieval-Policy Learning",
    DataCategory.PATCH_CRITIQUE: "Patch Critique",
    DataCategory.EVAL_ONLY: "Evaluation Only",
    DataCategory.UNUSABLE: "Unusable / Synthetic / Misleading",
}


@dataclass
class DataSourceAssessment:
    source_id: str = ""
    source_type: str = ""
    path: str = ""
    category: str = DataCategory.UNUSABLE
    completeness: float = 0.0
    correctness: float = 0.0
    has_task: bool = False
    has_tool_calls: bool = False
    has_patches: bool = False
    has_verification: bool = False
    has_outcome: bool = False
    quality_score: float = 0.0
    issues: List[str] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    missing_labels: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "path": self.path,
            "category": self.category,
            "category_label": CATEGORY_LABELS.get(self.category, "Unknown"),
            "completeness": round(self.completeness, 2),
            "correctness": round(self.correctness, 2),
            "has_task": self.has_task,
            "has_tool_calls": self.has_tool_calls,
            "has_patches": self.has_patches,
            "has_verification": self.has_verification,
            "has_outcome": self.has_outcome,
            "quality_score": round(self.quality_score, 2),
            "issues": self.issues[:5],
            "risks": self.risks[:5],
            "missing_labels": self.missing_labels[:5],
        }


@dataclass
class TrainingDataAuditReport:
    total_sources: int = 0
    by_category: Dict[str, int] = field(default_factory=dict)
    by_source_type: Dict[str, int] = field(default_factory=dict)
    assessments: List[DataSourceAssessment] = field(default_factory=list)
    overall_quality: float = 0.0
    usable_quality: float = 0.0
    leakage_risks: List[str] = field(default_factory=list)
    hallucination_risks: List[str] = field(default_factory=list)
    missing_labels_global: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "total_sources": self.total_sources,
            "by_category": dict(sorted(self.by_category.items())),
            "by_source_type": dict(sorted(self.by_source_type.items())),
            "overall_quality": round(self.overall_quality, 2),
            "usable_quality": round(self.usable_quality, 2),
            "assessments": [a.to_dict() for a in self.assessments],
            "leakage_risks": self.leakage_risks,
            "hallucination_risks": self.hallucination_risks,
            "missing_labels_global": self.missing_labels_global,
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        lines = ["# Training Data Audit Report", ""]
        lines.append(f"**Total sources assessed**: {self.total_sources}")
        lines.append(f"**Overall quality score**: {self.overall_quality:.2f}")
        lines.append(f"**Usable subset quality**: {self.usable_quality:.2f}")
        lines.append("")
        lines.append("## Classification Summary")
        lines.append("")
        lines.append("| Category | Count |")
        lines.append("|----------|-------|")
        for cat, label in CATEGORY_LABELS.items():
            count = self.by_category.get(cat, 0)
            lines.append(f"| {label} | {count} |")
        lines.append("")
        lines.append("## By Source Type")
        lines.append("")
        for st, count in sorted(self.by_source_type.items(), key=lambda x: -x[1]):
            lines.append(f"- {st}: {count}")
        lines.append("")
        lines.append("## Assessments")
        lines.append("")
        for a in self.assessments:
            status = "✓" if a.quality_score >= 0.8 else "△" if a.quality_score >= 0.5 else "✗"
            lines.append(f"### {status} {a.source_id}")
            lines.append(f"- **Type**: {a.source_type}")
            lines.append(f"- **Category**: {CATEGORY_LABELS.get(a.category, 'Unknown')}")
            lines.append(f"- **Quality**: {a.quality_score:.2f}")
            lines.append(f"- **Issues**: {', '.join(a.issues[:3]) if a.issues else 'None'}")
            lines.append("")
        if self.leakage_risks:
            lines.append("## Leakage Risks")
            for r in self.leakage_risks:
                lines.append(f"- {r}")
            lines.append("")
        if self.hallucination_risks:
            lines.append("## Hallucination Risks")
            for r in self.hallucination_risks:
                lines.append(f"- {r}")
            lines.append("")
        if self.missing_labels_global:
            lines.append("## Missing Labels")
            for l in self.missing_labels_global:
                lines.append(f"- {l}")
            lines.append("")
        if self.recommendations:
            lines.append("## Recommendations")
            for r in self.recommendations:
                lines.append(f"- {r}")
        return "\n".join(lines)


class TrainingDataAuditor:
    """Audits data sources for training usefulness."""

    def __init__(self, lyme_root: str = "."):
        self.lyme_root = Path(lyme_root).resolve()
        self.assessments: List[DataSourceAssessment] = []

    def audit_all(self) -> TrainingDataAuditReport:
        self.assessments = []
        self._audit_audit_traces()
        self._audit_standard_traces()
        self._audit_ci_traces()
        self._audit_demo_artifacts()
        self._audit_generated_data()
        self._audit_memory_store()
        return self._build_report()

    def _audit_audit_traces(self):
        audit_dir = self.lyme_root / ".lyme" / "audit"
        if not audit_dir.exists():
            return
        for f in sorted(audit_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, Exception):
                continue
            kind = data.get("kind", "unknown")
            has_patches = bool(data.get("patch_ids", []))
            has_files = bool(data.get("files_affected", []))
            has_outcome = data.get("status") in ("completed", "failed", "abandoned")

            category = DataCategory.EVAL_ONLY
            issues = ["Skeleton entry — no tool call traces", "No intermediate observations"]
            quality = 0.34
            if kind == "edit" and has_patches:
                category = DataCategory.SFT
                issues = []
                quality = 0.7

            missing = []
            if not data.get("trace_id"):
                missing.append("trace_id")
            if not data.get("metadata"):
                missing.append("metadata (task, observations, decisions)")

            self.assessments.append(DataSourceAssessment(
                source_id=data.get("audit_id", f.name),
                source_type=f"audit_{kind}",
                path=str(f),
                category=category,
                completeness=0.1,
                correctness=0.9,
                has_tool_calls=has_files,
                has_patches=has_patches,
                has_outcome=has_outcome,
                quality_score=quality,
                issues=issues,
                risks=["No task instruction captured", "No intermediate state recorded"],
                missing_labels=missing,
            ))

    def _audit_standard_traces(self):
        traces_dir = self.lyme_root / "lyme-output" / "standards" / "traces"
        if not traces_dir.exists():
            return
        for f in sorted(traces_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, Exception):
                continue

            events = data.get("events", [])
            header = data.get("header", {})
            tags = header.get("tags", {})
            summary = data.get("summary", {})

            event_types = [e.get("type", "") for e in events]
            has_task = bool(tags.get("task", "") or
                          any(e.get("prompt_preview", "") for e in events if e.get("type") == "model_call"))
            has_tool_calls = any(t in event_types for t in
                              ["file_read", "file_edit", "test_run", "rollback"])
            has_patches = any(e.get("type") == "file_edit" for e in events)
            has_verification = any(e.get("type") in ("test_run", "verification_step") for e in events)
            has_outcome = summary.get("status") in ("completed", "abandoned", "failed")

            has_failure = any(e.get("type") == "failed_attempt" for e in events)
            has_evidence = any(e.get("type") == "evidence_claim" for e in events)

            category = DataCategory.SFT
            quality = 0.90
            issues = []

            if has_failure:
                quality = 0.94
                category = DataCategory.SFT
                issues = ["Failure-attempt trace — good for recovery training"]
            if has_evidence:
                quality = 0.96

            if not has_tool_calls:
                category = DataCategory.EVAL_ONLY
                quality = 0.3

            missing = []
            if not any(e.get("type") == "patch_plan" for e in events):
                missing.append("patch_plan (no explicit plan before execution)")
            if not any(e.get("type") == "repo_state" for e in events):
                missing.append("repo_state (no pre-task repo snapshot)")
            if not any(e.get("type") == "final_answer" for e in events):
                missing.append("final_answer (no structured final output)")

            self.assessments.append(DataSourceAssessment(
                source_id=header.get("trace_id", f.name),
                source_type="standard_trace",
                path=str(f),
                category=category,
                completeness=0.85,
                correctness=1.0,
                has_task=has_task,
                has_tool_calls=has_tool_calls,
                has_patches=has_patches,
                has_verification=has_verification,
                has_outcome=has_outcome,
                quality_score=quality,
                issues=issues,
                risks=["Synthetic/fictional repo paths", "Single model attribution may leak"],
                missing_labels=missing,
            ))

    def _audit_ci_traces(self):
        ci_dir = self.lyme_root / "lyme-output" / "ci"
        if not ci_dir.exists():
            return
        for f in sorted(ci_dir.glob("*-trace.json")):
            try:
                data = json.loads(f.read_text())
            except (json.JSONDecodeError, Exception):
                continue

            events = data.get("content", {}).get("events", [])
            event_types = [e.get("type", "") for e in events]

            has_tool_calls = False
            has_patches = False
            has_verification = any(e.get("type") == "metric" for e in events)
            has_outcome = data.get("content", {}).get("summary", {}).get("status") == "completed"

            self.assessments.append(DataSourceAssessment(
                source_id=data.get("id", f.name),
                source_type="ci_trace",
                path=str(f),
                category=DataCategory.EVAL_ONLY,
                completeness=0.2,
                correctness=0.8,
                has_task=False,
                has_tool_calls=has_tool_calls,
                has_patches=has_patches,
                has_verification=has_verification,
                has_outcome=has_outcome,
                quality_score=0.35,
                issues=["Skeleton CI trace — no tool calls", "Only system + metric events"],
                risks=["CI metadata may contain repo identifiers"],
                missing_labels=["task", "tool_calls", "patches", "observations"],
            ))

    def _audit_demo_artifacts(self):
        demo_dir = self.lyme_root / "lyme-output" / "demo-v0.7"
        if not demo_dir.exists():
            return
        for f in sorted(demo_dir.glob("*.json")):
            name = f.name
            source_type = "demo_artifact"
            category = DataCategory.EVAL_ONLY
            quality = 0.3

            if "semantic-diff" in name:
                category = DataCategory.PATCH_CRITIQUE
                quality = 0.68
            elif "open-agent-trace" in name:
                category = DataCategory.SFT
                quality = 0.96
            elif "corpus-export" in name:
                category = DataCategory.EVAL_ONLY
                quality = 0.3

            self.assessments.append(DataSourceAssessment(
                source_id=name,
                source_type=source_type,
                path=str(f),
                category=category,
                quality_score=quality,
                completeness=0.5,
                correctness=0.9,
                has_task="trace" in name,
                has_tool_calls="trace" in name,
                has_patches="trace" in name or "diff" in name,
                has_verification=False,
                has_outcome=False,
                issues=["Demo artifact — may not reflect real usage"],
                risks=["Demo data may contain fictional decision patterns"],
                missing_labels=[],
            ))

    def _audit_generated_data(self):
        gen_sources = [
            ("Synthetic Data (generate_synthetic)", DataCategory.UNUSABLE, 0.43,
             ["20% random labels", "Hand-crafted situations, not from real traces",
              "No patch content, no verification", "Random correctness assignment"]),
            ("Simulated Training (ToolPolicyModel.train_step)", DataCategory.UNUSABLE, 0.3,
             ["Not gradient-based — weight multiplication by 1.01/0.99",
              "Creates illusion of learning", "No validation against held-out data"]),
            ("Rule-based Critic (PatchCritic.evaluate)", DataCategory.PATCH_CRITIQUE, 0.7,
             ["Rule-based, not learned", "Can generate critique training pairs"]),
        ]

        for name, cat, quality, issues in gen_sources:
            self.assessments.append(DataSourceAssessment(
                source_id=name.lower().replace(" ", "_").replace("(", "").replace(")", ""),
                source_type="generated_data",
                path="src/lyme_model/learning/",
                category=cat,
                quality_score=quality,
                completeness=0.4,
                correctness=0.5,
                has_task=True,
                has_tool_calls=("tool" in name.lower()),
                has_patches=("critic" in name.lower()),
                has_verification=False,
                has_outcome=False,
                issues=issues,
                risks=["Synthetic labels are incorrect 20% of the time",
                       "Simulated training has no real gradient signal"],
                missing_labels=["correctness_ground_truth", "source_trace_id"],
            ))

    def _audit_memory_store(self):
        memory_dir = self.lyme_root / "lyme-output" / "memory"
        if not memory_dir.exists():
            return
        for f in sorted(memory_dir.glob("*.json")):
            if f.name == "index.json":
                continue
            self.assessments.append(DataSourceAssessment(
                source_id=f.name,
                source_type="memory_entry",
                path=str(f),
                category=DataCategory.EVAL_ONLY,
                quality_score=0.4,
                completeness=0.3,
                correctness=0.7,
                has_task=False,
                has_tool_calls=False,
                has_patches=False,
                has_verification=False,
                has_outcome=False,
                issues=["Memory entry — structured observation, not agent trace",
                        "No tool call sequence, no patch"],
                risks=["Memory may contain stale or contradicted information"],
                missing_labels=["task", "tool_calls", "verification_result"],
            ))

    def _build_report(self) -> TrainingDataAuditReport:
        by_category: Dict[str, int] = {}
        by_source_type: Dict[str, int] = {}
        total_quality = 0.0
        usable_qualities = []

        for a in self.assessments:
            by_category[a.category] = by_category.get(a.category, 0) + 1
            by_source_type[a.source_type] = by_source_type.get(a.source_type, 0) + 1
            total_quality += a.quality_score
            if a.quality_score >= 0.8:
                usable_qualities.append(a.quality_score)

        overall = total_quality / len(self.assessments) if self.assessments else 0.0
        usable = sum(usable_qualities) / len(usable_qualities) if usable_qualities else 0.0

        return TrainingDataAuditReport(
            total_sources=len(self.assessments),
            by_category=by_category,
            by_source_type=by_source_type,
            assessments=self.assessments,
            overall_quality=overall,
            usable_quality=usable,
            leakage_risks=[
                "Synthetic repo paths may not generalize to real codebases",
                "Model attribution in traces (claude-3-opus, gpt-4-turbo) may leak model-specific patterns",
                "Repo names in trace headers identify fictional projects but field exists for real data",
                "human_intervention events contain user_message — benign now, critical in real data",
                "file_path fields use generic paths now but would leak structure in real traces",
            ],
            hallucination_risks=[
                "Synthetic data has 20% random label noise — degrades any learned model",
                "Simulated training (weight multiply) creates illusion of learning without gradients",
                "No 'I don't know' examples — model always tries to answer",
                "Patch content without full before/after context misses structural understanding",
            ],
            missing_labels_global=[
                "patch_plan — no trace records the plan before execution",
                "repo_state — no pre-task snapshot of repository structure",
                "final_answer — no structured final output",
                "correctness_label — no explicit correct/incorrect per decision",
                "alternative_actions — no counterfactual options recorded",
                "grounding_score — no measure of evidence grounding per claim",
                "difficulty_rating — exists in some traces but not in training schema",
            ],
            recommendations=[
                "Do NOT train on synthetic data — 20% random label noise will degrade any learned model",
                "Do NOT use simulated training as proxy — label as prototype only",
                "Instrument runtime immediately to collect real traces before Week 96",
                "Generate controlled data from synthetic repos — lyme-experiments/synthetic/ is ready",
                "Add explicit correctness, grounding, and difficulty labels to every trace",
                "Build sanitizer before any training data leaves local storage",
                "Keep the 3 standard traces as eval-only — too few to train on, perfect for measurement",
            ],
        )


def run_audit(lyme_root: str = ".") -> TrainingDataAuditReport:
    auditor = TrainingDataAuditor(lyme_root)
    return auditor.audit_all()


def save_report(report: TrainingDataAuditReport, output_path: str):
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    report_dict = report.to_dict()
    path.write_text(json.dumps(report_dict, indent=2))

    md_path = path.with_suffix(".md")
    md_path.write_text(report.to_markdown())

    return str(path), str(md_path)
