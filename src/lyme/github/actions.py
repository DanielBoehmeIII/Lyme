"""RepoActions — automated repository maintenance actions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ActionConfig:
    auto_label: bool = True
    auto_assign: bool = True
    stale_days: int = 60
    close_stale: bool = False


class RepoActions:
    def __init__(self, config: ActionConfig = None):
        self.config = config or ActionConfig()

    def label_issue(self, issue: Dict[str, Any]) -> List[str]:
        labels = []
        title = (issue.get("title", "") + " " + issue.get("body", "")).lower()
        if "bug" in title:
            labels.append("bug")
        if "feature" in title:
            labels.append("enhancement")
        if "test" in title:
            labels.append("tests")
        if "doc" in title:
            labels.append("documentation")
        if "security" in title:
            labels.append("security")
        return labels

    def check_stale(self, issue: Dict[str, Any]) -> bool:
        import time
        updated = issue.get("updated_at", 0)
        if isinstance(updated, str):
            return False
        age_days = (time.time() - updated) / 86400
        return age_days > self.config.stale_days

    def suggest_reviewers(self, files: List[str], author_map: Dict[str, List[str]]) -> List[str]:
        reviewers = set()
        for fp in files:
            for author, owned_files in author_map.items():
                if any(owned in fp for owned in owned_files):
                    reviewers.add(author)
        return list(reviewers)[:3]
