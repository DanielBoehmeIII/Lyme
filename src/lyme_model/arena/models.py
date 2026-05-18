"""Data models for the competitive benchmark arena."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, List


class ToolName(Enum):
    LYME = "lyme"
    CLAUDE_CODE = "claude_code"
    CODEX = "codex"
    OPENCODE = "opencode"
    AIDER = "aider"
    CURSOR = "cursor"


class ScoringDimension(Enum):
    CORRECTNESS = "correctness"
    TEST_PASS_RATE = "test_pass_rate"
    TIME = "time"
    COST = "cost"
    FILES_TOUCHED = "files_touched"
    ROLLBACK_COUNT = "rollback_count"
    HUMAN_INTERVENTION = "human_intervention"


@dataclass
class ArenaConfig:
    task_ids: list[str]
    tools: list[ToolName]
    repo_path: str
    timeout_s: int = 600
    max_retries: int = 2
    cost_per_token: Dict[str, float] = field(default_factory=lambda: {
        "lyme": 0.0,
        "claude_code": 0.00003,
        "codex": 0.00002,
        "opencode": 0.0,
        "aider": 0.0,
        "cursor": 0.00003,
    })

    def to_dict(self) -> dict:
        return {
            "task_ids": self.task_ids,
            "tools": [t.value for t in self.tools],
            "repo_path": self.repo_path,
            "timeout_s": self.timeout_s,
            "max_retries": self.max_retries,
        }


@dataclass
class ToolResult:
    tool: ToolName
    task_id: str
    task_title: str
    success: bool
    duration_s: float
    correctness: float
    test_pass_rate: float
    files_touched: int
    rollback_count: int
    human_intervention: bool
    token_count: int = 0
    cost: float = 0.0
    error: Optional[str] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool.value,
            "task_id": self.task_id,
            "task_title": self.task_title,
            "success": self.success,
            "duration_s": self.duration_s,
            "correctness": self.correctness,
            "test_pass_rate": self.test_pass_rate,
            "files_touched": self.files_touched,
            "rollback_count": self.rollback_count,
            "human_intervention": self.human_intervention,
            "token_count": self.token_count,
            "cost": self.cost,
            "error": self.error,
        }


@dataclass
class ArenaRun:
    run_id: str
    config: ArenaConfig
    started_at: str
    completed_at: Optional[str] = None
    results: Dict[str, List[ToolResult]] = field(default_factory=dict)
    scores: Dict[str, dict] = field(default_factory=dict)
    summary: dict = field(default_factory=dict)

    def add_result(self, result: ToolResult) -> None:
        tool_key = result.tool.value
        if tool_key not in self.results:
            self.results[tool_key] = []
        self.results[tool_key].append(result)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "config": self.config.to_dict() if hasattr(self.config, 'to_dict') else self.config,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "results": {k: [r.to_dict() for r in v] for k, v in self.results.items()},
            "scores": self.scores,
            "summary": self.summary,
        }
