"""VectorSearch — embedding-based semantic search for code."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .search import SearchResult


class EmbeddingProvider:
    def embed(self, texts: List[str]) -> List[List[float]]:
        raise NotImplementedError

    @property
    def dimension(self) -> int:
        return 0


class VectorIndex:
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def add(self, key: str, vector: List[float], metadata: Dict[str, Any] = None) -> None:
        self._vectors[key] = vector
        if metadata:
            self._metadata[key] = metadata

    def remove(self, key: str) -> None:
        self._vectors.pop(key, None)
        self._metadata.pop(key, None)

    def search(self, query_vector: List[float], top_k: int = 20) -> List[Tuple[str, float]]:
        scores = []
        for key, vec in self._vectors.items():
            score = self._cosine_similarity(query_vector, vec)
            scores.append((key, score))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @property
    def size(self) -> int:
        return len(self._vectors)

    def clear(self) -> None:
        self._vectors.clear()
        self._metadata.clear()


class VectorSearch:
    def __init__(self, provider: EmbeddingProvider, index: VectorIndex = None):
        self.provider = provider
        self.index = index or VectorIndex(provider.dimension)

    def search(self, query: str, top_k: int = 20) -> List[SearchResult]:
        query_vec = self.provider.embed([query])[0]
        results = self.index.search(query_vec, top_k)
        search_results = []
        for key, score in results:
            meta = self.index._metadata.get(key, {})
            search_results.append(SearchResult(
                file_path=key,
                score=score,
                symbol_name=meta.get("symbol_name", ""),
                symbol_kind=meta.get("symbol_kind", ""),
                line=meta.get("line", 0),
                snippet=meta.get("snippet", ""),
                matched_by=["vector"],
            ))
        return search_results

    def index_file(self, file_path: str, text: str, metadata: Dict[str, Any] = None) -> None:
        vec = self.provider.embed([text])[0]
        self.index.add(file_path, vec, metadata)

    def index_symbols(self, file_path: str, symbols: List[Any], get_text: Callable) -> None:
        texts = []
        for sym in symbols:
            sym_text = get_text(sym)
            if sym_text:
                texts.append(sym_text)

        if not texts:
            return

        vectors = self.provider.embed(texts)
        for sym, vec in zip(symbols, vectors):
            metadata = {
                "symbol_name": getattr(sym, "full_name", getattr(sym, "name", "")),
                "symbol_kind": getattr(sym, "kind", ""),
                "line": getattr(getattr(sym, "location", None), "line", 0),
            }
            key = f"{file_path}::{getattr(sym, 'name', 'unknown')}"
            self.index.add(key, vec, metadata)
