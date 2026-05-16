"""Week 101 — Preference Data for Coding Agents.

Creates paired preference data for Lyme Model training:
- better vs worse patch plans
- safer vs riskier patches
- grounded vs hallucinated answers
- minimal vs overbroad edits
- verified vs unverified solutions
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime, timezone
import json
import uuid
import random


@dataclass
class PreferencePair:
    """A paired preference data point."""
    pair_id: str = ""
    preference_type: str = ""  # plan_quality, patch_safety, grounding, edit_size, verification
    task: str = ""
    chosen: str = ""
    rejected: str = ""
    chosen_patch: str = ""
    rejected_patch: str = ""
    preference_reason: str = ""
    label_source: str = ""  # test, static_check, human_review, audit_graph, critic
    source_trace_id: str = ""
    difficulty: str = "medium"

    def to_dict(self) -> dict:
        return {
            "pair_id": self.pair_id,
            "preference_type": self.preference_type,
            "task": self.task[:200],
            "chosen": self.chosen[:500],
            "rejected": self.rejected[:500],
            "chosen_patch": self.chosen_patch[:500],
            "rejected_patch": self.rejected_patch[:500],
            "preference_reason": self.preference_reason[:200],
            "label_source": self.label_source,
            "source_trace_id": self.source_trace_id,
            "difficulty": self.difficulty,
        }


@dataclass
class PreferenceDataset:
    version: str = "0.1"
    pairs: List[PreferencePair] = field(default_factory=list)
    by_type: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    by_difficulty: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "total": len(self.pairs),
            "by_type": self.by_type,
            "by_source": self.by_source,
            "by_difficulty": self.by_difficulty,
        }

    def compute_stats(self):
        self.by_type = {}
        self.by_source = {}
        self.by_difficulty = {}
        for p in self.pairs:
            self.by_type[p.preference_type] = self.by_type.get(p.preference_type, 0) + 1
            self.by_source[p.label_source] = self.by_source.get(p.label_source, 0) + 1
            self.by_difficulty[p.difficulty] = self.by_difficulty.get(p.difficulty, 0) + 1


class PreferenceDataGenerator:
    """Generates preference pairs from Lyme Audit traces and synthetic data."""

    def __init__(self):
        self.pairs: List[PreferencePair] = []

    def generate_all(self) -> PreferenceDataset:
        self.pairs = []
        self._generate_from_traces()
        self._generate_plan_quality()
        self._generate_patch_safety()
        self._generate_grounding()
        self._generate_edit_size()
        self._generate_verification()

        ds = PreferenceDataset(pairs=self.pairs)
        ds.compute_stats()
        return ds

    def _generate_from_traces(self):
        traces_dir = Path("lyme-output/standards/traces")
        if not traces_dir.exists():
            return
        for f in sorted(traces_dir.glob("*.json")):
            try:
                trace = json.loads(f.read_text())
                header = trace.get("header", {})
                tags = header.get("tags", {})
                events = trace.get("events", [])
                task = tags.get("task", "")
                status = trace.get("summary", {}).get("status", "")

                # Good completion vs bad completion preference
                good = f"Completed: {task}"
                bad = f"Failed: {task} (status: {status})"

                self.pairs.append(PreferencePair(
                    pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                    preference_type="verification",
                    task=task,
                    chosen=good,
                    rejected=bad,
                    preference_reason=f"Trace completed successfully vs {status}",
                    label_source="audit_graph",
                    source_trace_id=header.get("trace_id", ""),
                ))

                # Extract individual decisions for grounding preference
                for ev in events:
                    if ev.get("type") == "evidence_claim":
                        grounded = ev.get("claim", "")
                        self.pairs.append(PreferencePair(
                            pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                            preference_type="grounding",
                            task=task,
                            chosen=grounded,
                            rejected=f"Unsupported claim about {task}",
                            preference_reason="Evidence-claimed vs hallucinated",
                            label_source="audit_graph",
                        ))

            except (json.JSONDecodeError, Exception):
                continue

    def _generate_plan_quality(self):
        plans = [
            ("Fix division by zero", "Add zero check before division with ValueError",
             "Wrap in try/except", "Includes explicit validation"),
            ("Fix null dropping", "Add warning log before dropna()",
             "Remove dropna() call entirely", "Preserves behavior while adding visibility"),
            ("Fix ID mismatch", "Accept both old and new ID params with deprecation",
             "Force all clients to use new ID only", "Backward compatible migration"),
        ]
        for task, good, bad, reason in plans:
            self.pairs.append(PreferencePair(
                pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                preference_type="plan_quality",
                task=task, chosen=good, rejected=bad,
                preference_reason=reason, label_source="human_review",
            ))

    def _generate_patch_safety(self):
        patches = [
            ("Remove input validation", "Add allowlist-based validation",
             "Delete all validation code", "Safety: validation protects against injection"),
            ("Add admin backdoor", "Implement proper audit logging",
             "Add unlogged admin access", "Security: all admin access must be logged"),
            ("Fix database connection", "Add retry with exponential backoff",
             "Increase timeout to 60s", "Reliability: retry is better than timeout"),
        ]
        for task, safe, risky, reason in patches:
            self.pairs.append(PreferencePair(
                pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                preference_type="patch_safety",
                task=task, chosen=safe, rejected=risky,
                preference_reason=reason, label_source="critic",
            ))

    def _generate_grounding(self):
        examples = [
            ("Fix the pagination bug", "The off-by-one is in the end index calculation",
             "The bug is probably in the imports", "Based on code evidence vs speculation"),
            ("Add rate limiting", "Rate limiting belongs in middleware per framework docs",
             "Rate limiting should go in the database layer", "Grounded in framework conventions"),
        ]
        for task, good, bad, reason in examples:
            self.pairs.append(PreferencePair(
                pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                preference_type="grounding",
                task=task, chosen=good, rejected=bad,
                preference_reason=reason, label_source="human_review",
            ))

    def _generate_edit_size(self):
        edits = [
            ("Fix off-by-one", "Change single line: end = min(start + per_page, len(items))",
             "Rewrite entire pagination function (50 lines)", "Minimal change, same behavior"),
            ("Add input validation", "Add 3-line Pydantic validator",
             "Add 100-line validation module with custom exceptions", "Minimal change addresses root cause"),
        ]
        for task, minimal, overbroad, reason in edits:
            self.pairs.append(PreferencePair(
                pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                preference_type="edit_size",
                task=task, chosen=minimal, rejected=overbroad,
                preference_reason=reason, label_source="critic",
            ))

    def _generate_verification(self):
        examples = [
            ("Fix division by zero", "pytest tests/test_calculator.py -v (5 tests pass)",
             "Manual testing only", "Automated verification is reproducible"),
            ("Fix todo-api endpoint", "pytest tests/test_api.py -v (12 tests pass, coverage 88%)",
             "Just check the endpoint works manually", "Quantified verification prevents regression"),
        ]
        for task, verified, unverified, reason in examples:
            self.pairs.append(PreferencePair(
                pair_id=f"pref-{uuid.uuid4().hex[:12]}",
                preference_type="verification",
                task=task, chosen=verified, rejected=unverified,
                preference_reason=reason, label_source="audit_graph",
            ))

    def save(self, output_dir: str) -> str:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        ds = PreferenceDataset(pairs=self.pairs)
        ds.compute_stats()
        out_file = out_dir / "preference_data.json"
        out_file.write_text(json.dumps({
            "dataset": ds.to_dict(),
            "pairs": [p.to_dict() for p in self.pairs],
        }, indent=2))
        return str(out_file)
