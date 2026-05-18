"""HybridSearch — fused vector + symbolic search for code retrieval."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from lyme.parser.symbols import SymbolIndex, SymbolKind


@dataclass
class SearchConfig:
    symbol_weight: float = 0.3
    vector_weight: float = 0.7
    max_results: int = 20
    min_score: float = 0.1
    include_content: bool = True
    kind_filter: Optional[SymbolKind] = None


@dataclass
class SearchResult:
    file_path: str
    score: float
    symbol_name: str = ""
    symbol_kind: str = ""
    line: int = 0
    snippet: str = ""
    matched_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "score": round(self.score, 4),
            "symbol_name": self.symbol_name,
            "symbol_kind": self.symbol_kind,
            "line": self.line,
            "snippet": self.snippet[:200] if self.snippet else "",
            "matched_by": self.matched_by,
        }


class HybridSearch:
    def __init__(self, symbol_index: SymbolIndex, config: SearchConfig = None):
        self.symbol_index = symbol_index
        self.config = config or SearchConfig()
        self._vector_search: Optional[VectorSearchProxy] = None

    def set_vector_search(self, vs: VectorSearchProxy) -> None:
        self._vector_search = vs

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        config = SearchConfig(**(self.config.__dict__))
        config.max_results = top_k

        symbolic_results = self._symbolic_search(query)
        vector_results = self._vector_retrieve(query) if self._vector_search else []

        fused = self._fuse(symbolic_results, vector_results, config)
        return fused[:top_k]

    def _symbolic_search(self, query: str) -> List[SearchResult]:
        """Search symbol index by name/pattern match."""
        results: List[SearchResult] = []
        words = query.lower().split()

        for fi in self.symbol_index.get_files():
            file_score = 0.0
            matched_symbols = []

            for sym in fi.symbols:
                sym_score = 0.0
                match_reasons = []

                for word in words:
                    if word in sym.name.lower():
                        sym_score += 0.4
                        match_reasons.append(f"name:{sym.name}")

                if sym.docstring:
                    for word in words:
                        if word in sym.docstring.lower():
                            sym_score += 0.15
                            match_reasons.append(f"docstring")
                            break

                if self.config.kind_filter and sym.kind == self.config.kind_filter:
                    sym_score += 0.2
                    match_reasons.append(f"kind:{sym.kind.value}")

                if sym_score > 0:
                    file_score += sym_score
                    matched_symbols.append((sym, match_reasons, sym_score))

            if file_score > 0 and matched_symbols:
                best = max(matched_symbols, key=lambda x: x[2])
                sym, reasons, _ = best
                results.append(SearchResult(
                    file_path=fi.file_path,
                    score=file_score,
                    symbol_name=sym.name,
                    symbol_kind=sym.kind.value,
                    line=sym.location.line,
                    matched_by=reasons,
                ))

        results.sort(key=lambda r: r.score, reverse=True)

        # File-level fallback: if no symbols matched, match file path
        if not results:
            for fi in self.symbol_index.get_files():
                file_score = sum(0.1 for word in words if word in fi.file_path.lower())
                if file_score > 0:
                    results.append(SearchResult(
                        file_path=fi.file_path,
                        score=file_score,
                        matched_by=["file_path"],
                    ))

        return results

    def _vector_retrieve(self, query: str) -> List[SearchResult]:
        if not self._vector_search:
            return []
        return self._vector_search.search(query, self.config.max_results)

    def _fuse(self, symbolic: List[SearchResult],
              vector: List[SearchResult],
              config: SearchConfig) -> List[SearchResult]:
        merged: Dict[str, SearchResult] = {}

        for r in symbolic:
            r.score *= config.symbol_weight
            merged[r.file_path] = r

        for r in vector:
            if r.file_path in merged:
                merged[r.file_path].score += r.score * config.vector_weight
                merged[r.file_path].matched_by.extend(r.matched_by)
            else:
                r.score *= config.vector_weight
                merged[r.file_path] = r

        results = [r for r in merged.values() if r.score >= config.min_score]
        results.sort(key=lambda r: r.score, reverse=True)
        return results


class VectorSearchProxy:
    def search(self, query: str, top_k: int) -> List[SearchResult]:
        return []
