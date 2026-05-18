"""TestSelector — impact-aware test selection using dependency analysis."""
from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


@dataclass
class ImpactAnalysis:
    changed_files: List[str] = field(default_factory=list)
    affected_tests: List[str] = field(default_factory=list)
    unaffected_tests: int = 0
    reduction_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changed_files": self.changed_files,
            "affected_tests": len(self.affected_tests),
            "unaffected_tests": self.unaffected_tests,
            "reduction_pct": round(self.reduction_pct, 2),
            "test_files": self.affected_tests[:20],
        }


@dataclass
class TestSelection:
    all_tests: List[str] = field(default_factory=list)
    selected: List[str] = field(default_factory=list)
    impact: ImpactAnalysis = field(default_factory=ImpactAnalysis)
    strategy: str = "all"  # all, impact, random, failed_first

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": len(self.all_tests),
            "selected": len(self.selected),
            "strategy": self.strategy,
            "impact": self.impact.to_dict(),
        }


class TestSelector:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self._import_map: Dict[str, Set[str]] = {}

    def discover_all(self) -> List[str]:
        tests = []
        for pattern in ["test_*.py", "*_test.py", "test_*.rs", "*_test.rs", "*.spec.js", "*.spec.ts", "*.test.js", "*.test.ts"]:
            for f in self.repo_path.rglob(pattern):
                tests.append(str(f.relative_to(self.repo_path)))
        return sorted(tests)

    def select_by_impact(self, changed_files: List[str]) -> TestSelection:
        all_tests = self.discover_all()
        impact = ImpactAnalysis(changed_files=changed_files)

        for changed in changed_files:
            changed_name = Path(changed).stem
            for test_file in all_tests:
                test_path = Path(self.repo_path / test_file)
                if test_path.exists():
                    try:
                        content = test_path.read_text(errors="replace")
                        if changed_name in content or changed.replace("/", ".") in content:
                            if test_file not in impact.affected_tests:
                                impact.affected_tests.append(test_file)
                    except Exception:
                        continue

        impact.unaffected_tests = len(all_tests) - len(impact.affected_tests)
        impact.reduction_pct = (impact.unaffected_tests / max(len(all_tests), 1)) * 100

        selection = TestSelection(
            all_tests=all_tests,
            selected=impact.affected_tests or all_tests[:10],
            impact=impact,
            strategy="impact",
        )
        return selection

    def select_failed_first(self, failed_tests: List[str]) -> TestSelection:
        all_tests = self.discover_all()
        selected = failed_tests + [t for t in all_tests if t not in failed_tests]
        return TestSelection(
            all_tests=all_tests,
            selected=selected,
            strategy="failed_first",
        )
