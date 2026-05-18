"""SymbolicSearch — keyword and pattern-based code search."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from lyme.parser.symbols import SymbolIndex, SymbolKind


@dataclass
class SymbolQuery:
    text: str
    kind: Optional[SymbolKind] = None
    file_pattern: Optional[str] = None
    max_results: int = 20
    exact: bool = False


@dataclass
class SymbolMatch:
    symbol_name: str
    symbol_kind: str
    file_path: str
    line: int
    score: float
    context: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol_name": self.symbol_name,
            "symbol_kind": self.symbol_kind,
            "file_path": self.file_path,
            "line": self.line,
            "score": round(self.score, 4),
            "context": self.context[:200],
        }


class SymbolicSearch:
    def __init__(self, symbol_index: SymbolIndex):
        self.symbol_index = symbol_index

    def search(self, query: SymbolQuery) -> List[SymbolMatch]:
        results: List[SymbolMatch] = []
        query_text = query.text.lower()
        query_words = query_text.split()

        for fi in self.symbol_index.get_files():
            if query.file_pattern and query.file_pattern not in fi.file_path:
                continue

            for sym in fi.symbols:
                if query.kind and sym.kind != query.kind:
                    continue

                score = 0.0
                if query.exact:
                    if sym.name.lower() == query_text:
                        score = 1.0
                    elif sym.name.lower() == query_text.split(".")[-1]:
                        score = 0.9
                else:
                    for word in query_words:
                        if word in sym.name.lower():
                            score += 0.3
                        if sym.parent and word in sym.parent.lower():
                            score += 0.1

                    if sym.docstring:
                        for word in query_words:
                            if word in sym.docstring.lower():
                                score += 0.1
                                break

                if score > 0:
                    results.append(SymbolMatch(
                        symbol_name=sym.full_name,
                        symbol_kind=sym.kind.value,
                        file_path=fi.file_path,
                        line=sym.location.line,
                        score=score,
                        context=sym.docstring[:200] if sym.docstring else "",
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:query.max_results]

    def find_class(self, name: str) -> List[SymbolMatch]:
        return self.search(SymbolQuery(text=name, kind=SymbolKind.CLASS, exact=True))

    def find_function(self, name: str) -> List[SymbolMatch]:
        return self.search(SymbolQuery(text=name, kind=SymbolKind.FUNCTION))

    def find_by_kind(self, kind: SymbolKind) -> List[SymbolMatch]:
        results: List[SymbolMatch] = []
        for fi in self.symbol_index.get_files():
            for sym in fi.symbols:
                if sym.kind == kind:
                    results.append(SymbolMatch(
                        symbol_name=sym.full_name,
                        symbol_kind=sym.kind.value,
                        file_path=fi.file_path,
                        line=sym.location.line,
                        score=0.5,
                    ))
        return results

    def find_test_files(self) -> List[SymbolMatch]:
        return self.find_by_kind(SymbolKind.FUNCTION)
