"""RepoMap — generates structured maps of repository contents."""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from lyme.parser.symbols import SymbolIndex, SymbolKind, Symbol
from lyme.parser.imports import ImportGraph


@dataclass
class RepoMapConfig:
    max_files: int = 100
    show_symbols: bool = True
    show_imports: bool = True
    show_tests: bool = True
    group_by_directory: bool = True
    include_details: bool = False


@dataclass
class RepoMapEntry:
    file_path: str
    language: str = ""
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    symbol_count: int = 0
    lines: int = 0
    complexity: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "classes": self.classes,
            "functions": self.functions,
            "imports": self.imports[:10],
            "exports": self.exports,
            "test_files": self.test_files,
            "symbol_count": self.symbol_count,
            "lines": self.lines,
            "complexity": round(self.complexity, 4),
        }


class RepoMap:
    def __init__(self, symbol_index: SymbolIndex, config: RepoMapConfig = None):
        self.symbol_index = symbol_index
        self.config = config or RepoMapConfig()

    def generate(self) -> Dict[str, Any]:
        """Generate the structured repo map."""
        entries: Dict[str, RepoMapEntry] = {}
        for fi in self.symbol_index.get_files():
            entry = RepoMapEntry(
                file_path=fi.file_path,
                language=fi.language,
                symbol_count=fi.symbol_count,
                lines=fi.lines,
                complexity=fi.complexity,
            )
            for sym in fi.symbols:
                if sym.kind == SymbolKind.CLASS:
                    entry.classes.append(sym.name)
                elif sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                    entry.functions.append(sym.name)
                elif sym.kind == SymbolKind.IMPORT:
                    entry.imports.append(sym.full_name)
            entry.exports = fi.exports
            entry.test_files = fi.test_files
            entries[fi.file_path] = entry

        sorted_files = sorted(entries.keys(), key=lambda f: (
            -entries[f].complexity,
            -entries[f].lines,
        ))

        if self.config.max_files and len(sorted_files) > self.config.max_files:
            sorted_files = sorted_files[:self.config.max_files]

        map_dict: Dict[str, Any] = {
            "generated_at": __import__("time").time(),
            "total_files": len(entries),
            "displayed_files": len(sorted_files),
            "files": {},
        }

        if self.config.group_by_directory:
            groups: Dict[str, List[str]] = {}
            for fp in sorted_files:
                parts = Path(fp).parts
                group = parts[0] if len(parts) > 1 else "root"
                if group not in groups:
                    groups[group] = []
                groups[group].append(fp)
            map_dict["groups"] = {}
            for group, fps in sorted(groups.items()):
                map_dict["groups"][group] = {
                    "file_count": len(fps),
                    "files": {fp: entries[fp].to_dict() for fp in sorted(fps)},
                }
        else:
            map_dict["files"] = {fp: entries[fp].to_dict() for fp in sorted_files}

        return map_dict

    def markdown(self, include_tree: bool = True) -> str:
        """Generate a markdown repo map."""
        lines = ["# Repository Map", ""]
        if include_tree:
            lines.append("## File Tree")
            lines.append("```")
            dirs: Set[str] = set()
            for fi in self.symbol_index.get_files():
                parts = Path(fi.file_path).parts
                for i in range(1, len(parts)):
                    parent = "/".join(parts[:i])
                    if parent not in dirs:
                        indent = "  " * (i - 1)
                        lines.append(f"{indent}{parts[i-1]}/")
                        dirs.add(parent)
                indent = "  " * (len(parts) - 1)
                lines.append(f"{indent}{parts[-1]}")
            lines.append("```")
            lines.append("")

        entries = []
        for fi in self.symbol_index.get_files():
            entry = RepoMapEntry(
                file_path=fi.file_path,
                language=fi.language,
                symbol_count=fi.symbol_count,
                lines=fi.lines,
                complexity=fi.complexity,
            )
            for sym in fi.symbols:
                if sym.kind == SymbolKind.CLASS:
                    entry.classes.append(sym.name)
                elif sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                    entry.functions.append(sym.name)
            entries.append(entry)

        entries.sort(key=lambda e: (-e.complexity, -e.lines))
        if self.config.max_files:
            entries = entries[:self.config.max_files]

        lines.append("## Files")
        lines.append(f"| File | Lang | Symbols | Lines | Complexity |")
        lines.append(f"|------|------|---------|-------|------------|")
        for e in entries:
            comp = f"{e.complexity:.2f}" if e.complexity > 0 else "-"
            lines.append(f"| {e.file_path} | {e.language} | {e.symbol_count} | {e.lines} | {comp} |")

        if self.config.show_symbols:
            lines.append("")
            lines.append("## Key Symbols")
            for fi in self.symbol_index.get_files():
                classes = [s for s in fi.symbols if s.kind == SymbolKind.CLASS]
                funcs = [s for s in fi.symbols if s.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD)]
                if classes or funcs:
                    lines.append(f"")
                    lines.append(f"### {fi.file_path}")
                    for cls in classes:
                        lines.append(f"- **class** `{cls.name}`")
                    for fn in funcs:
                        lines.append(f"- `{fn.name}()`")

        return "\n".join(lines)

    def important_files(self, top_n: int = 20) -> List[Dict[str, Any]]:
        """Rank files by importance based on complexity, symbol count, and imports."""
        scores: List[tuple[float, str, RepoMapEntry]] = []
        for fi in self.symbol_index.get_files():
            score = 0.0
            score += fi.class_count * 2.0
            score += fi.function_count * 1.0
            score += len(fi.imports) * 0.3
            score += fi.complexity * 5.0
            score += fi.change_frequency * 2.0
            entry = RepoMapEntry(
                file_path=fi.file_path,
                language=fi.language,
                symbol_count=fi.symbol_count,
                lines=fi.lines,
                complexity=fi.complexity,
            )
            for sym in fi.symbols:
                if sym.kind == SymbolKind.CLASS:
                    entry.classes.append(sym.name)
                elif sym.kind in (SymbolKind.FUNCTION, SymbolKind.METHOD):
                    entry.functions.append(sym.name)
            scores.append((score, fi.file_path, entry))

        scores.sort(key=lambda x: x[0], reverse=True)
        return [
            {"score": round(s, 2), "file_path": fp, **e.to_dict()}
            for s, fp, e in scores[:top_n]
        ]
