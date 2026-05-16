from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclass
class ArchitectureDecisionRecord:
    adr_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = ""
    status: DecisionStatus = DecisionStatus.PROPOSED
    context: str = ""
    decision: str = ""
    rationale: str = ""
    constraints: List[str] = field(default_factory=list)
    alternatives_considered: List[str] = field(default_factory=list)
    alternatives_rejected: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    outcome: str = ""
    aged_well: Optional[bool] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# ADR-{self.adr_id[:8]}: {self.title}")
        lines.append("")
        lines.append(f"**Status:** {self.status.value}")
        lines.append(f"**Created:** {datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()}")
        if self.updated_at != self.created_at:
            lines.append(f"**Updated:** {datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()}")
        lines.append("")
        lines.append("## Context")
        lines.append("")
        lines.append(self.context)
        lines.append("")
        lines.append("## Decision")
        lines.append("")
        lines.append(self.decision)
        lines.append("")
        lines.append("## Rationale")
        lines.append("")
        lines.append(self.rationale)
        lines.append("")
        if self.constraints:
            lines.append("## Constraints")
            for c in self.constraints:
                lines.append(f"- {c}")
            lines.append("")
        if self.alternatives_considered:
            lines.append("## Alternatives Considered")
            for a in self.alternatives_considered:
                lines.append(f"- {a}")
            lines.append("")
        if self.alternatives_rejected:
            lines.append("## Alternatives Rejected")
            for a in self.alternatives_rejected:
                lines.append(f"- {a}")
            lines.append("")
        if self.consequences:
            lines.append("## Consequences")
            for c in self.consequences:
                lines.append(f"- {c}")
            lines.append("")
        if self.outcome:
            lines.append("## Outcome")
            lines.append("")
            lines.append(self.outcome)
            lines.append("")
        if self.aged_well is not None:
            lines.append(f"**Aged well:** {'Yes' if self.aged_well else 'No'}")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "adr_id": self.adr_id,
            "title": self.title,
            "status": self.status.value,
            "context": self.context[:200],
            "decision": self.decision[:200],
            "rationale": self.rationale[:200],
            "constraints": self.constraints,
            "alternatives_considered": self.alternatives_considered[:5],
            "alternatives_rejected": self.alternatives_rejected[:5],
            "consequences": self.consequences,
            "outcome": self.outcome[:200] if self.outcome else "",
            "aged_well": self.aged_well,
            "created_at": self.created_at,
            "tags": self.tags,
        }


class EngineeringDecisionMemory:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self._memory_dir = self.repo_path / ".lyme" / "decisions"
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        self.records: Dict[str, ArchitectureDecisionRecord] = {}
        self._load()

    def record_decision(self, title: str, context: str, decision: str, rationale: str, constraints: Optional[List[str]] = None, alternatives: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> ArchitectureDecisionRecord:
        adr = ArchitectureDecisionRecord(
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            constraints=constraints or [],
            alternatives_considered=alternatives or [],
            status=DecisionStatus.ACCEPTED,
            tags=tags or [],
        )
        self.records[adr.adr_id] = adr
        self._persist(adr)
        return adr

    def update_outcome(self, adr_id: str, outcome: str, aged_well: bool):
        adr = self.records.get(adr_id)
        if adr:
            adr.outcome = outcome
            adr.aged_well = aged_well
            adr.updated_at = time.time()
            self._persist(adr)

    def get_decision(self, adr_id: str) -> Optional[ArchitectureDecisionRecord]:
        return self.records.get(adr_id)

    def query_decisions(self, tag: Optional[str] = None, status: Optional[DecisionStatus] = None, limit: int = 20) -> List[ArchitectureDecisionRecord]:
        results = list(self.records.values())
        if tag:
            results = [r for r in results if tag in r.tags]
        if status:
            results = [r for r in results if r.status == status]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    def generate_adr_from_data(self, title: str, context: str, decision: str, rationale: str, constraints: List[str], alternatives: List[str]) -> ArchitectureDecisionRecord:
        adr = ArchitectureDecisionRecord(
            title=title,
            context=context,
            decision=decision,
            rationale=rationale,
            constraints=constraints,
            alternatives_considered=alternatives,
        )
        self.records[adr.adr_id] = adr
        self._persist(adr)
        return adr

    def get_statistics(self) -> Dict[str, Any]:
        total = len(self.records)
        by_status = {}
        for r in self.records.values():
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        aged_well_count = sum(1 for r in self.records.values() if r.aged_well is True)
        aged_poorly = sum(1 for r in self.records.values() if r.aged_well is False)

        return {
            "total_adrs": total,
            "by_status": by_status,
            "aged_well": aged_well_count,
            "aged_poorly": aged_poorly,
            "awaiting_outcome": total - aged_well_count - aged_poorly,
        }

    def produce_report(self) -> str:
        lines = []
        lines.append("=" * 60)
        lines.append(" ENGINEERING DECISION MEMORY REPORT")
        lines.append("=" * 60)
        stats = self.get_statistics()
        lines.append(f"  Total ADRs: {stats['total_adrs']}")
        lines.append(f"  Aged well: {stats['aged_well']}")
        lines.append(f"  Aged poorly: {stats['aged_poorly']}")
        lines.append("")
        for r in sorted(self.records.values(), key=lambda r: r.created_at, reverse=True)[:10]:
            age = "✓" if r.aged_well is True else ("✗" if r.aged_well is False else "?")
            lines.append(f"  [{r.status.value[0].upper()}] [{age}] {r.title[:70]}")
            lines.append(f"       {r.decision[:80]}")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _persist(self, adr: ArchitectureDecisionRecord):
        path = self._memory_dir / f"{adr.adr_id}.json"
        path.write_text(json.dumps(adr.to_dict(), indent=2, default=str))
        index = {"adr_ids": list(self.records.keys())}
        (self._memory_dir / "index.json").write_text(json.dumps(index, indent=2))

    def _load(self):
        index_path = self._memory_dir / "index.json"
        if index_path.exists():
            try:
                index = json.loads(index_path.read_text())
                for adr_id in index.get("adr_ids", []):
                    path = self._memory_dir / f"{adr_id}.json"
                    if path.exists():
                        data = json.loads(path.read_text())
                        adr = ArchitectureDecisionRecord(
                            adr_id=data["adr_id"],
                            title=data["title"],
                            status=DecisionStatus(data["status"]),
                            context=data.get("context", ""),
                            decision=data.get("decision", ""),
                            rationale=data.get("rationale", ""),
                            constraints=data.get("constraints", []),
                            alternatives_considered=data.get("alternatives_considered", []),
                            consequences=data.get("consequences", []),
                            outcome=data.get("outcome", ""),
                            aged_well=data.get("aged_well"),
                            created_at=data.get("created_at", 0),
                            tags=data.get("tags", []),
                        )
                        self.records[adr_id] = adr
            except Exception:
                pass
