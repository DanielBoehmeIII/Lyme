from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .context_budget import ContextBudgetOptimizer


# Rough token estimation (4 chars ≈ 1 token for code)
def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class RehydrationLayer:
    def __init__(self, default_context_limit: int = 128_000):
        self.default_context_limit = default_context_limit

    def rehydrate(
        self,
        task: str,
        layer1_tree: Dict[str, Any],
        layer2_apis: Dict[str, Any],
        layer3_subsystems: Dict[str, Any],
        layer4_invariants: Dict[str, Any],
        repo_path: Optional[Path] = None,
        context_limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        limit = context_limit or self.default_context_limit
        optimizer = ContextBudgetOptimizer(context_limit=limit)

        budget = optimizer.optimize(
            task=task,
            layer1_tree=layer1_tree,
            layer2_apis=layer2_apis,
            layer3_subsystems=layer3_subsystems,
            layer4_invariants=layer4_invariants,
        )

        included_content: Dict[str, str] = {}
        if repo_path:
            for filepath in budget.included_files:
                full_path = Path(repo_path) / filepath
                if full_path.is_file():
                    try:
                        content = full_path.read_text(encoding="utf-8", errors="replace")
                        included_content[filepath] = content
                    except Exception:
                        included_content[filepath] = "  # Error reading file"

        packet = {
            "task": task,
            "summary": {
                "repo_name": layer1_tree.get("repo_name", ""),
                "languages": layer1_tree.get("languages", {}),
                "frameworks": layer1_tree.get("frameworks", []),
                "entry_points": layer1_tree.get("entry_points", []),
                "total_files": layer1_tree.get("total_files", 0),
                "total_modules": layer2_apis.get("total_modules", 0),
                "subsystems": list(layer3_subsystems.get("subsystems", {}).keys()),
                "risk_zones_count": len(layer4_invariants.get("risk_zones", [])),
            },
            "included_files": budget.included_files,
            "included_file_contents": included_content,
            "included_summaries": budget.included_summaries,
            "omitted_items": budget.omitted_items,
            "lazy_retrieval_queue": budget.lazy_retrieval_queue,
            "estimated_tokens": budget.estimated_tokens,
            "context_limit": limit,
            "usage_percent": round(
                (budget.estimated_tokens / max(limit, 1)) * 100, 1
            ),
        }

        return packet

    def extract(self, repo_path: Path, **kwargs) -> Dict[str, Any]:
        return {"rehydration_layer": True, "requires_task": True}
