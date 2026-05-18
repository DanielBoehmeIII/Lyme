"""Symbols — data models for parsed code symbols and indexes."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class SymbolKind(Enum):
    MODULE = "module"
    CLASS = "class"
    METHOD = "method"
    FUNCTION = "function"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    DECORATOR = "decorator"
    PROPERTY = "property"
    PARAMETER = "parameter"
    TYPE_ALIAS = "type_alias"
    INTERFACE = "interface"
    ENUM_MEMBER = "enum_member"


@dataclass
class SymbolLocation:
    file_path: str
    line: int
    column: int = 0
    end_line: int = 0
    end_column: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "end_line": self.end_line,
            "end_column": self.end_column,
        }


@dataclass
class Symbol:
    name: str
    kind: SymbolKind
    location: SymbolLocation
    parent: Optional[str] = None
    docstring: str = ""
    decorators: List[str] = field(default_factory=list)
    params: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    is_async: bool = False
    is_public: bool = True
    is_test: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def full_name(self) -> str:
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "full_name": self.full_name,
            "kind": self.kind.value,
            "location": self.location.to_dict(),
            "parent": self.parent,
            "docstring": self.docstring[:200] if self.docstring else "",
            "decorators": self.decorators,
            "params": self.params,
            "returns": self.returns,
            "is_async": self.is_async,
            "is_public": self.is_public,
            "is_test": self.is_test,
        }


@dataclass
class FileIndex:
    file_path: str
    language: str = "unknown"
    symbols: List[Symbol] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    test_files: List[str] = field(default_factory=list)
    change_frequency: int = 0
    complexity: float = 0.0
    lines: int = 0
    last_modified: float = 0.0
    hash: str = ""

    @property
    def symbol_count(self) -> int:
        return len(self.symbols)

    @property
    def class_count(self) -> int:
        return sum(1 for s in self.symbols if s.kind == SymbolKind.CLASS)

    @property
    def function_count(self) -> int:
        return sum(1 for s in self.symbols if s.kind == SymbolKind.FUNCTION)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": self.imports[:20],
            "exports": self.exports,
            "test_files": self.test_files,
            "change_frequency": self.change_frequency,
            "complexity": self.complexity,
            "lines": self.lines,
            "hash": self.hash[:16],
        }


class SymbolIndex:
    def __init__(self):
        self._files: Dict[str, FileIndex] = {}
        self._symbol_map: Dict[str, List[Symbol]] = {}
        self._name_index: Dict[str, List[Symbol]] = {}

    def add_file(self, index: FileIndex) -> None:
        self._files[index.file_path] = index
        for sym in index.symbols:
            key = sym.full_name
            if key not in self._symbol_map:
                self._symbol_map[key] = []
            self._symbol_map[key].append(sym)

            name_key = sym.name
            if name_key not in self._name_index:
                self._name_index[name_key] = []
            self._name_index[name_key].append(sym)

    def get_file(self, file_path: str) -> Optional[FileIndex]:
        return self._files.get(file_path)

    def get_files(self) -> List[FileIndex]:
        return list(self._files.values())

    def get_symbol(self, full_name: str) -> List[Symbol]:
        return self._symbol_map.get(full_name, [])

    def find_symbol(self, name: str, kind: Optional[SymbolKind] = None) -> List[Symbol]:
        results = self._name_index.get(name, [])
        if kind:
            results = [s for s in results if s.kind == kind]
        return results

    def find_by_kind(self, kind: SymbolKind) -> List[Symbol]:
        return [s for s in self._all_symbols() if s.kind == kind]

    def find_in_file(self, file_path: str) -> List[Symbol]:
        fi = self._files.get(file_path)
        return fi.symbols if fi else []

    def find_by_pattern(self, pattern: str) -> List[Symbol]:
        pattern_lower = pattern.lower()
        results = []
        for sym in self._all_symbols():
            if pattern_lower in sym.name.lower() or pattern_lower in (sym.docstring or "").lower():
                results.append(sym)
        return results

    def file_count(self) -> int:
        return len(self._files)

    def symbol_count(self) -> int:
        return len(self._symbol_map)

    def remove_file(self, file_path: str) -> None:
        fi = self._files.pop(file_path, None)
        if fi:
            for sym in fi.symbols:
                key = sym.full_name
                if key in self._symbol_map:
                    self._symbol_map[key] = [s for s in self._symbol_map[key] if s.location.file_path != file_path]
                    if not self._symbol_map[key]:
                        del self._symbol_map[key]
                name_key = sym.name
                if name_key in self._name_index:
                    self._name_index[name_key] = [s for s in self._name_index[name_key] if s.location.file_path != file_path]
                    if not self._name_index[name_key]:
                        del self._name_index[name_key]

    def clear(self) -> None:
        self._files.clear()
        self._symbol_map.clear()
        self._name_index.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files": {fp: fi.to_dict() for fp, fi in self._files.items()},
            "symbol_count": self.symbol_count(),
        }

    def _all_symbols(self) -> List[Symbol]:
        symbols = []
        for fi in self._files.values():
            symbols.extend(fi.symbols)
        return symbols
