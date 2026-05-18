"""RepoQuestions — answers to "what files matter", "what changed", "what likely breaks"."""
from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from lyme.parser.symbols import SymbolIndex, SymbolKind
from lyme.parser.imports import ImportGraph
from lyme.indexer import RepoIndexer


@dataclass
class WhatMattersResult:
    files: List[Dict[str, Any]] = field(default_factory=list)
    total_files: int = 0
    top_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files": self.files,
            "total_files": self.total_files,
            "top_reasons": self.top_reasons,
        }


@dataclass
class WhatChangedResult:
    files: List[Dict[str, Any]] = field(default_factory=list)
    added: List[str] = field(default_factory=list)
    modified: List[str] = field(default_factory=list)
    deleted: List[str] = field(default_factory=list)
    since: str = ""
    total_changes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "since": self.since,
            "total_changes": self.total_changes,
        }


@dataclass
class WhatBreaksResult:
    changed_files: List[str] = field(default_factory=list)
    potentially_broken: List[Dict[str, Any]] = field(default_factory=list)
    breakage_risk: float = 0.0
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "changed_files": self.changed_files,
            "potentially_broken": self.potentially_broken,
            "breakage_risk": round(self.breakage_risk, 4),
            "suggestions": self.suggestions,
        }


class RepoQuestions:
    def __init__(self, symbol_index: SymbolIndex, import_graph: ImportGraph,
                 repo_path: str = "."):
        self.symbol_index = symbol_index
        self.import_graph = import_graph
        self.repo_path = repo_path

    def what_matters(self, top_n: int = 20) -> WhatMattersResult:
        """Rank files by importance: complexity, dependencies, test coverage."""
        scores: List[Tuple[float, str, str, int, int]] = []
        for fi in self.symbol_index.get_files():
            score = 0.0
            reasons = []

            # Classes are important
            classes = sum(1 for s in fi.symbols if s.kind == SymbolKind.CLASS)
            if classes > 0:
                score += classes * 3.0
                reasons.append(f"{classes} classes")

            # Functions
            funcs = sum(1 for s in fi.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD))
            score += funcs * 1.5

            # Many imports = hub file
            if len(fi.imports) > 10:
                score += len(fi.imports) * 0.5
                reasons.append(f"{len(fi.imports)} imports")

            # Many downstream dependents = critical
            downstream = len(self.import_graph.downstream(fi.file_path))
            if downstream > 0:
                scorer_mult = min(3.0, 1.0 + downstream * 0.1)
                score += downstream * scorer_mult
                reasons.append(f"{downstream} downstream dependents")

            # Test files
            upstream = len(self.import_graph.upstream(fi.file_path))
            if upstream > 0:
                score += upstream * 0.5

            # Large files are complex
            if fi.lines > 200:
                score += fi.lines * 0.01

            scores.append((score, fi.file_path, "; ".join(reasons[:3]), classes, funcs))

        scores.sort(key=lambda x: x[0], reverse=True)
        result = WhatMattersResult(
            total_files=len(scores),
            top_reasons=[
                "Files with the most classes and dependencies rank highest",
                "Downstream dependents indicate critical infrastructure",
                "High import count suggests hub/module files",
            ],
        )
        for score, fp, reasons, classes, funcs in scores[:top_n]:
            result.files.append({
                "file_path": fp,
                "importance_score": round(score, 2),
                "reasons": reasons,
                "classes": classes,
                "functions": funcs,
            })
        return result

    def what_changed(self, since_ref: str = "HEAD~5", days: Optional[int] = None) -> WhatChangedResult:
        """Find files changed since a git ref or time period."""
        result = WhatChangedResult(since=since_ref)

        try:
            if days:
                import time
                since_ts = time.time() - (days * 86400)
                cmd = ["git", "log", "--after", str(int(since_ts)),
                       "--name-only", "--pretty=format:", "-100"]
            else:
                cmd = ["git", "diff", "--name-only", since_ref, "HEAD"]

            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                cwd=self.repo_path, timeout=10,
            )
            changed = set()
            for line in proc.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    changed.add(line)
            result.files = list(changed - set(result.added) - set(result.deleted))
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Classify changes
        for fp in result.files:
            full_path = Path(self.repo_path) / fp
            if not full_path.exists():
                result.deleted.append(fp)
            else:
                try:
                    proc = subprocess.run(
                        ["git", "log", "--oneline", "-1", "--", fp],
                        capture_output=True, text=True,
                        cwd=self.repo_path, timeout=5,
                    )
                    if proc.stdout.strip():
                        result.modified.append(fp)
                except Exception:
                    result.modified.append(fp)

        result.total_changes = len(result.added) + len(result.modified) + len(result.deleted)
        return result

    def what_breaks(self, changed_files: Optional[List[str]] = None) -> WhatBreaksResult:
        """Estimate what files/functionality might break given changes."""
        if changed_files is None:
            changed = self.what_changed()
            changed_files = changed.files

        result = WhatBreaksResult(changed_files=changed_files)

        affected: Dict[str, float] = {}
        for cf in changed_files:
            # Find downstream dependents
            for edge in self.import_graph.edges:
                if edge.source == cf:
                    target = edge.target or cf
                    weight = edge.weight
                    if target in affected:
                        affected[target] += weight
                    else:
                        affected[target] = weight

            # Find test files
            test_patterns = ("test_", "_test.", ".spec.", "_spec.")
            for fi in self.symbol_index.get_files():
                fname = Path(fi.file_path).name
                if any(fname.startswith(p) or fname.endswith(p.replace(".", "."))
                       for p in test_patterns):
                    # Check if test imports the changed file
                    for imp in fi.imports:
                        if cf.replace("/", ".").replace(".py", "") in imp:
                            affected[fi.file_path] = affected.get(fi.file_path, 0) + 2.0

        for fp, risk in sorted(affected.items(), key=lambda x: -x[1]):
            result.potentially_broken.append({
                "file_path": fp,
                "risk_score": round(min(risk, 10.0), 2),
            })

        if result.potentially_broken:
            result.breakage_risk = min(1.0, sum(r["risk_score"] for r in result.potentially_broken) / 20.0)
            result.suggestions.append(f"Run tests for {len(result.potentially_broken)} affected files")
            high_risk = [r for r in result.potentially_broken if r["risk_score"] > 3.0]
            if high_risk:
                result.suggestions.append(
                    f"Review {len(high_risk)} high-risk files: {', '.join(r['file_path'] for r in high_risk[:5])}"
                )

        return result
