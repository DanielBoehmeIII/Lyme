"""CompressionIntegration — wires compression pipeline into agent context assembly."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .codebase_compressor import CodebaseCompressor
from .context_budget import ContextBudgetOptimizer


@dataclass
class ContextPacket:
    task: str
    files: List[Dict[str, Any]] = field(default_factory=list)
    symbols: List[Dict[str, Any]] = field(default_factory=list)
    summary: str = ""
    token_estimate: int = 0
    budget_used: int = 0
    budget_total: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task[:80],
            "files": len(self.files),
            "symbols": len(self.symbols),
            "summary": self.summary[:200],
            "token_estimate": self.token_estimate,
            "budget_used": self.budget_used,
            "budget_total": self.budget_total,
        }


class CompressionIntegration:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self._compressor: Optional[CodebaseCompressor] = None
        self._optimizer = ContextBudgetOptimizer()

    def build_context(self, task: str, token_budget: int = 8000) -> ContextPacket:
        if not self._compressor:
            self._compressor = CodebaseCompressor(str(self.repo_path))
            self._compressor.compress()

        packet = ContextPacket(task=task, budget_total=token_budget)

        # Get rehydration packet
        rehydrated = self._compressor.get_rehydration_packet(task)
        if isinstance(rehydrated, dict):
            packet.files = rehydrated.get("files", rehydrated.get("primary_files", []))
            packet.symbols = rehydrated.get("symbols", [])
            packet.summary = rehydrated.get("summary", "")

        # Optimize to token budget
        if packet.files:
            optimized = self._optimizer.optimize({
                "files": packet.files,
                "symbols": packet.symbols,
            })
            if isinstance(optimized, dict):
                packet.budget_used = optimized.get("token_estimate", 0) or len(str(optimized)) // 4
        else:
            packet.budget_used = len(str(packet.files)) // 4

        packet.token_estimate = max(packet.budget_used, len(task) // 4)
        return packet

    def summarize_repo(self) -> str:
        if not self._compressor:
            self._compressor = CodebaseCompressor(str(self.repo_path))
            self._compressor.compress()
        return self._compressor.get_summary() or ""
