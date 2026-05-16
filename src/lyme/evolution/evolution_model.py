from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class TemporalEventType(str, Enum):
    COMMIT = "commit"
    REFACTOR = "refactor"
    MIGRATION = "migration"
    BUG_FIX = "bug_fix"
    FEATURE_ADD = "feature_add"
    DEPRECATION = "deprecation"
    ARCHITECTURE_CHANGE = "architecture_change"
    DEPENDENCY_CHANGE = "dependency_change"
    BREAKING_CHANGE = "breaking_change"
    PERFORMANCE_REGESSION = "performance_regression"


class StabilityClass(str, Enum):
    STABLE = "stable"
    GROWING = "growing"
    CHAOTIC = "chaotic"
    DECAYING = "decaying"
    EMERGING = "emerging"
    UNKNOWN = "unknown"


@dataclass
class TemporalEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    event_type: TemporalEventType = TemporalEventType.COMMIT
    timestamp: float = 0.0
    commit_hash: str = ""
    author: str = ""
    message: str = ""
    files_changed: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    subsystems: List[str] = field(default_factory=list)
    complexity_delta: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "commit_hash": self.commit_hash[:12],
            "author": self.author,
            "message": self.message[:100],
            "files_changed": self.files_changed,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "subsystems": self.subsystems,
            "complexity_delta": self.complexity_delta,
        }


@dataclass
class EvolutionMetrics:
    timestamp: float = 0.0
    total_files: int = 0
    total_lines: int = 0
    total_commits: int = 0
    total_authors: int = 0
    avg_file_complexity: float = 0.0
    dependency_count: int = 0
    circular_dependency_count: int = 0
    test_coverage_estimate: float = 0.0
    technical_debt_estimate: float = 0.0
    subsystem_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_files": self.total_files,
            "total_lines": self.total_lines,
            "total_commits": self.total_commits,
            "total_authors": self.total_authors,
            "avg_file_complexity": self.avg_file_complexity,
            "dependency_count": self.dependency_count,
            "circular_dependency_count": self.circular_dependency_count,
            "test_coverage_estimate": self.test_coverage_estimate,
            "technical_debt_estimate": self.technical_debt_estimate,
            "subsystem_count": self.subsystem_count,
        }


@dataclass
class EvolutionSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    period_start: float = 0.0
    period_end: float = 0.0
    metrics: EvolutionMetrics = field(default_factory=EvolutionMetrics)
    events: List[TemporalEvent] = field(default_factory=list)
    stability: StabilityClass = StabilityClass.UNKNOWN
    growth_rate: float = 0.0
    churn_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "metrics": self.metrics.to_dict(),
            "events_count": len(self.events),
            "stability": self.stability.value,
            "growth_rate": self.growth_rate,
            "churn_rate": self.churn_rate,
        }


@dataclass
class EvolutionTrend:
    metric: str = ""
    values: List[float] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)
    slope: float = 0.0
    volatility: float = 0.0
    acceleration: float = 0.0
    is_alarming: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric,
            "value_count": len(self.values),
            "slope": self.slope,
            "volatility": self.volatility,
            "acceleration": self.acceleration,
            "is_alarming": self.is_alarming,
        }


@dataclass
class EvolutionTimeline:
    snapshots: List[EvolutionSnapshot] = field(default_factory=list)
    trends: Dict[str, EvolutionTrend] = field(default_factory=dict)

    def add_snapshot(self, snapshot: EvolutionSnapshot):
        self.snapshots.append(snapshot)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_count": len(self.snapshots),
            "snapshots": [s.to_dict() for s in self.snapshots],
            "trends": {k: v.to_dict() for k, v in self.trends.items()},
        }


class EvolutionModel:
    def __init__(self, repo_path: str = ""):
        self.repo_path = repo_path
        self.timeline = EvolutionTimeline()
        self.events: List[TemporalEvent] = []
        self.subsystem_history: Dict[str, List[EvolutionMetrics]] = defaultdict(list)
        self.created_at: float = time.time()

    def add_event(self, event: TemporalEvent):
        self.events.append(event)

    def get_subsystem_timeline(self, subsystem: str) -> List[EvolutionMetrics]:
        return self.subsystem_history.get(subsystem, [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "total_events": len(self.events),
            "timeline": self.timeline.to_dict(),
            "subsystem_count": len(self.subsystem_history),
        }
