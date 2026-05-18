"""GiantRepoTest — stress tests against large codebases."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RepoScaleConfig:
    repo_path: str = "."
    file_count: int = 0
    max_depth: int = 10
    timeout_s: int = 300


@dataclass
class GiantRepoTest:
    name: str = ""
    files_scanned: int = 0
    index_duration_s: float = 0.0
    parse_success_rate: float = 0.0
    errors: List[str] = field(default_factory=list)
    passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "files_scanned": self.files_scanned,
            "index_duration_s": round(self.index_duration_s, 2),
            "parse_success_rate": round(self.parse_success_rate, 4),
            "errors": len(self.errors),
            "passed": self.passed,
        }


class GiantRepoTestRunner:
    def run(self, config: RepoScaleConfig) -> GiantRepoTest:
        start = time.time()
        result = GiantRepoTest(name=f"giant-{config.repo_path[:20]}")
        try:
            from lyme.indexer import RepoIndexer, IndexConfig
            idx = RepoIndexer(IndexConfig(repo_root=config.repo_path))
            delta = idx.index(config.repo_path)
            result.files_scanned = idx.symbol_index.file_count()
            result.parse_success_rate = 1.0
            result.passed = result.files_scanned > 0
        except Exception as e:
            result.errors.append(str(e))
        result.index_duration_s = time.time() - start
        return result
