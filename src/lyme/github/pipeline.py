"""IssueToPRPipeline — autonomous issue-to-PR workflow."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class PRConfig:
    repo: str = ""
    base_branch: str = "main"
    create_pr: bool = False
    add_reviewers: List[str] = field(default_factory=list)
    draft: bool = True


@dataclass
class PRResult:
    issue_number: int = 0
    pr_number: int = 0
    branch: str = ""
    title: str = ""
    description: str = ""
    changed_files: List[str] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue": self.issue_number,
            "pr": self.pr_number,
            "branch": self.branch,
            "files": len(self.changed_files),
            "success": self.success,
            "error": self.error,
        }


class IssueToPRPipeline:
    def __init__(self, config: PRConfig = None, agent_fn: Callable = None):
        self.config = config or PRConfig()
        self._agent_fn = agent_fn

    def run(self, issue_number: int, issue_body: str) -> PRResult:
        start = time.time()
        result = PRResult(issue_number=issue_number)
        result.title = f"Fix: {issue_body.split(chr(10))[0][:80] if chr(10) in issue_body else issue_body[:80]}"

        if self._agent_fn:
            try:
                output = self._agent_fn(f"Implement fix for: {issue_body}")
                result.description = str(output)[:500]
                result.success = True
            except Exception as e:
                result.error = str(e)

        result.duration_s = time.time() - start
        return result
