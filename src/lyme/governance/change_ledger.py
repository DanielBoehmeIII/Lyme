from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import time
import uuid


class LedgerEntryType(str, Enum):
    CODE_CHANGE = "code_change"
    VERIFICATION = "verification"
    GOVERNANCE = "governance"
    APPROVAL = "approval"
    ROLLBACK = "rollback"
    BENCHMARK = "benchmark"
    MEMORY_LEARNED = "memory_learned"
    ERROR = "error"
    USER_INTERVENTION = "user_intervention"


class EntryOutcome(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class LedgerEntry:
    id: str
    timestamp: float
    entry_type: LedgerEntryType
    description: str
    agent: str
    intent: str
    risk_score: float
    verification_result: str
    outcome: EntryOutcome
    evidence: List[str] = field(default_factory=list)
    human_approvals: List[str] = field(default_factory=list)
    rollback_path: str = ""
    learned_memory: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    parent_id: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "entry_type": self.entry_type.value,
            "description": self.description,
            "agent": self.agent,
            "intent": self.intent,
            "risk_score": self.risk_score,
            "verification_result": self.verification_result,
            "outcome": self.outcome.value,
            "evidence": self.evidence,
            "human_approvals": self.human_approvals,
            "rollback_path": self.rollback_path,
            "learned_memory": self.learned_memory,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
        }

    def to_markdown(self) -> str:
        icons = {
            EntryOutcome.SUCCESS: "✅", EntryOutcome.FAILURE: "❌",
            EntryOutcome.BLOCKED: "🚫", EntryOutcome.ROLLED_BACK: "↩️",
            EntryOutcome.PARTIAL: "⚠️", EntryOutcome.PENDING: "⏳",
            LedgerEntryType.CODE_CHANGE: "📝", LedgerEntryType.VERIFICATION: "🔍",
            LedgerEntryType.GOVERNANCE: "⚖️", LedgerEntryType.APPROVAL: "👤",
            LedgerEntryType.ROLLBACK: "↩️", LedgerEntryType.BENCHMARK: "📊",
            LedgerEntryType.MEMORY_LEARNED: "🧠", LedgerEntryType.ERROR: "💥",
            LedgerEntryType.USER_INTERVENTION: "✋",
        }
        lines = []
        t_icon = icons.get(self.entry_type, "•")
        o_icon = icons.get(self.outcome, "•")
        lines.append(f"### {t_icon} {self.description}")
        lines.append(f"")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| ID | `{self.id}` |")
        lines.append(f"| Type | {self.entry_type.value} |")
        lines.append(f"| Outcome | {o_icon} {self.outcome.value} |")
        lines.append(f"| Agent | {self.agent} |")
        lines.append(f"| Intent | {self.intent} |")
        lines.append(f"| Risk Score | {self.risk_score:.2f} |")
        lines.append(f"| Verification | {self.verification_result} |")
        lines.append(f"| Rollback Path | {self.rollback_path or 'N/A'} |")
        lines.append(f"| Timestamp | {time.ctime(self.timestamp)} |")
        if self.parent_id:
            lines.append(f"| Parent | `{self.parent_id}` |")
        if self.evidence:
            lines.append(f"| Evidence | {', '.join(self.evidence[:3])} |")
        if self.human_approvals:
            lines.append(f"| Approvals | {', '.join(self.human_approvals)} |")
        return "\n".join(lines)


@dataclass
class LedgerSummary:
    total_entries: int
    by_type: Dict[str, int]
    by_outcome: Dict[str, int]
    total_risk: float
    avg_risk: float
    success_rate: float
    rollback_count: int
    intervention_count: int
    memory_count: int
    time_span_hours: float

    def to_dict(self) -> Dict:
        return {
            "total_entries": self.total_entries,
            "by_type": self.by_type,
            "by_outcome": self.by_outcome,
            "total_risk": round(self.total_risk, 2),
            "avg_risk": round(self.avg_risk, 3),
            "success_rate": round(self.success_rate, 3),
            "rollback_count": self.rollback_count,
            "intervention_count": self.intervention_count,
            "memory_count": self.memory_count,
            "time_span_hours": round(self.time_span_hours, 1),
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"## Autonomous Change Ledger Summary")
        lines.append(f"")
        lines.append(f"| Metric | Value |")
        lines.append(f"|--------|-------|")
        lines.append(f"| Total Entries | {self.total_entries} |")
        lines.append(f"| Time Span | {self.time_span_hours:.1f}h |")
        lines.append(f"| Success Rate | {self.success_rate:.0%} |")
        lines.append(f"| Rollbacks | {self.rollback_count} |")
        lines.append(f"| Interventions | {self.intervention_count} |")
        lines.append(f"| Avg Risk | {self.avg_risk:.3f} |")
        lines.append(f"| Memory Entries | {self.memory_count} |")
        lines.append(f"")
        lines.append(f"### By Type")
        for t, c in sorted(self.by_type.items(), key=lambda x: -x[1]):
            bar = "█" * max(1, c * 20 // max(self.total_entries, 1))
            lines.append(f"- {t}: {c} {bar}")
        lines.append(f"")
        lines.append(f"### By Outcome")
        for o, c in sorted(self.by_outcome.items(), key=lambda x: -x[1]):
            pct = c / max(self.total_entries, 1) * 100
            lines.append(f"- {o}: {c} ({pct:.0f}%)")
        return "\n".join(lines)


class AutonomousChangeLedger:
    def __init__(self, storage_path: Optional[Path] = None):
        self._entries: List[LedgerEntry] = []
        self._storage_path = storage_path
        self._load()

    def record(self, entry: LedgerEntry) -> str:
        self._entries.append(entry)
        self._save()
        return entry.id

    def record_change(
        self,
        description: str,
        agent: str,
        intent: str,
        risk_score: float,
        verification_result: str,
        outcome: EntryOutcome,
        evidence: Optional[List[str]] = None,
        approvals: Optional[List[str]] = None,
        rollback_path: str = "",
        learned_memory: Optional[Dict] = None,
        metadata: Optional[Dict] = None,
        parent_id: Optional[str] = None,
    ) -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.CODE_CHANGE,
            description=description,
            agent=agent,
            intent=intent,
            risk_score=risk_score,
            verification_result=verification_result,
            outcome=outcome,
            evidence=evidence or [],
            human_approvals=approvals or [],
            rollback_path=rollback_path,
            learned_memory=learned_memory or {},
            metadata=metadata or {},
            parent_id=parent_id,
        )
        return self.record(entry)

    def record_verification(self, description: str, agent: str, result: str, evidence: List[str]) -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.VERIFICATION,
            description=description,
            agent=agent,
            intent="verify_change",
            risk_score=0.1,
            verification_result=result,
            outcome=EntryOutcome.SUCCESS if "pass" in result.lower() else EntryOutcome.FAILURE,
            evidence=evidence,
        )
        return self.record(entry)

    def record_governance(self, description: str, decision: str, risk_score: float) -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.GOVERNANCE,
            description=description,
            agent="governance_engine",
            intent="governance_check",
            risk_score=risk_score,
            verification_result=decision,
            outcome=EntryOutcome.SUCCESS,
        )
        return self.record(entry)

    def record_approval(self, description: str, approver: str, approved: bool, reason: str = "") -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.APPROVAL,
            description=description,
            agent=approver,
            intent="approve_change",
            risk_score=0.0,
            verification_result=reason or "approved" if approved else "rejected",
            outcome=EntryOutcome.SUCCESS if approved else EntryOutcome.FAILURE,
            human_approvals=[f"{approver}: {'approved' if approved else 'rejected'}"],
        )
        return self.record(entry)

    def record_rollback(self, description: str, agent: str, success: bool, path: str = "") -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.ROLLBACK,
            description=description,
            agent=agent,
            intent="rollback_change",
            risk_score=0.0,
            verification_result="Rollback executed",
            outcome=EntryOutcome.ROLLED_BACK if success else EntryOutcome.FAILURE,
            rollback_path=path,
        )
        return self.record(entry)

    def record_memory(self, description: str, memory_data: Dict) -> str:
        entry = LedgerEntry(
            id=str(uuid.uuid4())[:8],
            timestamp=time.time(),
            entry_type=LedgerEntryType.MEMORY_LEARNED,
            description=description,
            agent="lyme",
            intent="learn_from_experience",
            risk_score=0.0,
            verification_result="memory_stored",
            outcome=EntryOutcome.SUCCESS,
            learned_memory=memory_data,
        )
        return self.record(entry)

    def get_entries(self, entry_type: Optional[LedgerEntryType] = None,
                    limit: int = 100) -> List[LedgerEntry]:
        entries = self._entries
        if entry_type:
            entries = [e for e in entries if e.entry_type == entry_type]
        return sorted(entries, key=lambda e: -e.timestamp)[:limit]

    def get_entry(self, entry_id: str) -> Optional[LedgerEntry]:
        for e in self._entries:
            if e.id == entry_id:
                return e
        return None

    def get_summary(self) -> LedgerSummary:
        total = len(self._entries)
        if total == 0:
            return LedgerSummary(
                total_entries=0, by_type={}, by_outcome={},
                total_risk=0, avg_risk=0, success_rate=0,
                rollback_count=0, intervention_count=0,
                memory_count=0, time_span_hours=0,
            )

        by_type: Dict[str, int] = {}
        by_outcome: Dict[str, int] = {}
        total_risk = 0.0
        rollbacks = 0
        interventions = 0
        memories = 0

        for e in self._entries:
            by_type[e.entry_type.value] = by_type.get(e.entry_type.value, 0) + 1
            by_outcome[e.outcome.value] = by_outcome.get(e.outcome.value, 0) + 1
            total_risk += e.risk_score
            if e.outcome == EntryOutcome.ROLLED_BACK:
                rollbacks += 1
            if e.entry_type == LedgerEntryType.USER_INTERVENTION:
                interventions += 1
            if e.entry_type == LedgerEntryType.MEMORY_LEARNED:
                memories += 1

        times = [e.timestamp for e in self._entries]
        span = (max(times) - min(times)) / 3600.0 if times else 0

        successes = by_outcome.get(EntryOutcome.SUCCESS.value, 0)

        return LedgerSummary(
            total_entries=total,
            by_type=by_type,
            by_outcome=by_outcome,
            total_risk=total_risk,
            avg_risk=total_risk / total,
            success_rate=successes / total,
            rollback_count=rollbacks,
            intervention_count=interventions,
            memory_count=memories,
            time_span_hours=span,
        )

    def get_rollback_path(self, entry_id: str) -> str:
        entry = self.get_entry(entry_id)
        if entry:
            return entry.rollback_path
        return ""

    def get_learned_memories(self) -> List[Dict]:
        return [
            e.learned_memory for e in self._entries
            if e.entry_type == LedgerEntryType.MEMORY_LEARNED and e.learned_memory
        ]

    def _save(self) -> None:
        if not self._storage_path:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries]
        self._storage_path.write_text(json.dumps(data, indent=2))

    def _load(self) -> None:
        if not self._storage_path or not self._storage_path.exists():
            return
        try:
            data = json.loads(self._storage_path.read_text())
            for d in data:
                self._entries.append(LedgerEntry(
                    id=d["id"], timestamp=d["timestamp"],
                    entry_type=LedgerEntryType(d["entry_type"]),
                    description=d["description"], agent=d["agent"],
                    intent=d["intent"], risk_score=d["risk_score"],
                    verification_result=d["verification_result"],
                    outcome=EntryOutcome(d["outcome"]),
                    evidence=d.get("evidence", []),
                    human_approvals=d.get("human_approvals", []),
                    rollback_path=d.get("rollback_path", ""),
                    learned_memory=d.get("learned_memory", {}),
                    metadata=d.get("metadata", {}),
                    parent_id=d.get("parent_id"),
                ))
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Could not load ledger: {e}")

    def to_dict(self) -> Dict:
        return {
            "entries": [e.to_dict() for e in self._entries],
            "summary": self.get_summary().to_dict(),
        }
