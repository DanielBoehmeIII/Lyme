"""Week 75 — Retrieval Policy Learning.

7 retrieval strategies for small local coding models.
Each policy implements: retrieve(query, repo_path) -> RetrievalResult.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Callable
from pathlib import Path
import re
import time
import json


@dataclass
class RetrievalResult:
    files: List[Dict[str, str]]
    context_size_tokens: int
    latency_ms: float
    policy_name: str
    total_candidates: int = 0
    irrelevant_count: int = 0
    missing_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "files": self.files,
            "context_size_tokens": self.context_size_tokens,
            "latency_ms": self.latency_ms,
            "policy_name": self.policy_name,
            "total_candidates": self.total_candidates,
            "irrelevant_count": self.irrelevant_count,
            "missing_evidence": self.missing_evidence,
        }


class RetrievalPolicy:
    name: str = "base"
    description: str = "Base retrieval policy"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        raise NotImplementedError

    def estimate_tokens(self, text: str) -> int:
        return len(text.split())


class KeywordRetrieval(RetrievalPolicy):
    name = "keyword"
    description = "Keyword-based file retrieval using grep"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        keywords = set(re.findall(r'\w{3,}', query.lower()))
        results = []
        total_candidates = 0

        for f in repo.rglob("*"):
            if f.is_file() and f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
                ".c", ".cpp", ".h", ".hpp", ".rb", ".php", ".swift", ".kt",
                ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".cfg",
            }:
                try:
                    text = f.read_text(errors="ignore")
                    total_candidates += 1
                    text_lower = text.lower()
                    matches = sum(1 for kw in keywords if kw in text_lower)
                    if matches > 0:
                        results.append({
                            "path": str(f.relative_to(repo)),
                            "score": matches / len(keywords),
                            "method": "keyword",
                        })
                except Exception:
                    pass

        results.sort(key=lambda x: -x["score"])
        top = results[:10]
        context = sum(len(r["path"]) for r in top)
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=top,
            context_size_tokens=self.estimate_tokens(str(top)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class EmbeddingRetrieval(RetrievalPolicy):
    name = "embedding"
    description = "Embedding-based semantic file retrieval (TF-IDF fallback)"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        query_tokens = set(re.findall(r'\w{4,}', query.lower()))
        results = []
        total_candidates = 0

        for f in repo.rglob("*"):
            if f.is_file() and f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
                ".c", ".cpp", ".h", ".hpp", ".md", ".txt", ".yaml", ".json",
            }:
                try:
                    text = f.read_text(errors="ignore")
                    total_candidates += 1
                    text_tokens = set(re.findall(r'\w{4,}', text.lower()))
                    if not query_tokens or not text_tokens:
                        continue
                    overlap = len(query_tokens & text_tokens)
                    jaccard = overlap / len(query_tokens | text_tokens)
                    if jaccard > 0.05:
                        results.append({
                            "path": str(f.relative_to(repo)),
                            "score": jaccard,
                            "method": "embedding_tfidf",
                        })
                except Exception:
                    pass

        results.sort(key=lambda x: -x["score"])
        top = results[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=top,
            context_size_tokens=self.estimate_tokens(str(top)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class GraphRetrieval(RetrievalPolicy):
    name = "graph"
    description = "Import graph-based file retrieval"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        query_lower = query.lower()
        import_graph: Dict[str, Set[str]] = {}
        file_scores: Dict[str, float] = {}
        total_candidates = 0

        for f in repo.rglob("*.py"):
            if f.is_file():
                try:
                    text = f.read_text(errors="ignore")
                    total_candidates += 1
                    rel = str(f.relative_to(repo))
                    imports = set(re.findall(r'^(?:from|import)\s+([\w.]+)', text, re.MULTILINE))
                    import_graph[rel] = imports
                    text_lower = text.lower()
                    score = sum(1 for kw in query_lower.split() if kw in text_lower)
                    if score > 0:
                        file_scores[rel] = score
                except Exception:
                    pass

        # Propagate scores through import graph
        for _ in range(2):
            for file_ref, imports in import_graph.items():
                for imp in imports:
                    imp_file = imp.replace(".", "/") + ".py"
                    if imp_file in file_scores and file_ref in file_scores:
                        file_scores[file_ref] += file_scores[imp_file] * 0.3

        results = sorted(
            [{"path": p, "score": s, "method": "graph"} for p, s in file_scores.items()],
            key=lambda x: -x["score"],
        )[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=results,
            context_size_tokens=self.estimate_tokens(str(results)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class ASTRetrieval(RetrievalPolicy):
    name = "ast"
    description = "AST-based retrieval using function/class definitions"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        query_lower = query.lower()
        query_tokens = set(re.findall(r'\w{3,}', query_lower))
        results = []
        total_candidates = 0

        for f in repo.rglob("*.py"):
            if f.is_file():
                try:
                    text = f.read_text(errors="ignore")
                    total_candidates += 1
                    rel = str(f.relative_to(repo))
                    classes = re.findall(r'^class\s+(\w+)', text, re.MULTILINE)
                    functions = re.findall(r'^def\s+(\w+)', text, re.MULTILINE)
                    symbols = classes + functions
                    symbol_matches = sum(
                        1 for s in symbols if any(t in s.lower() for t in query_tokens)
                    )
                    if symbol_matches > 0:
                        results.append({
                            "path": rel,
                            "score": symbol_matches / max(len(query_tokens), 1),
                            "method": "ast",
                            "symbols": symbols[:10],
                        })
                except Exception:
                    pass

        results.sort(key=lambda x: -x["score"])
        top = results[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=top,
            context_size_tokens=self.estimate_tokens(str(top)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class GitHistoryRetrieval(RetrievalPolicy):
    name = "git_history"
    description = "Git history-based retrieval (recently modified files)"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        results = []
        total_candidates = 0

        try:
            import subprocess
            # Get recently modified files
            proc = subprocess.run(
                ["git", "log", "--name-only", "--pretty=format:", "-n", "30"],
                capture_output=True, text=True, cwd=repo, timeout=10,
            )
            recent_files = set()
            for line in proc.stdout.strip().split("\n"):
                line = line.strip()
                if line and line not in recent_files:
                    recent_files.add(line)
                    total_candidates += 1

            query_lower = query.lower()
            query_tokens = set(re.findall(r'\w{3,}', query_lower))

            for rf in recent_files:
                full_path = repo / rf
                if full_path.exists():
                    try:
                        text = full_path.read_text(errors="ignore")
                        text_lower = text.lower()
                        matches = sum(1 for kw in query_tokens if kw in text_lower)
                        if matches > 0:
                            results.append({
                                "path": rf,
                                "score": matches / len(query_tokens),
                                "method": "git_history",
                            })
                    except Exception:
                        pass
        except Exception:
            pass

        results.sort(key=lambda x: -x["score"])
        top = results[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=top,
            context_size_tokens=self.estimate_tokens(str(top)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class HybridRetrieval(RetrievalPolicy):
    name = "hybrid"
    description = "Hybrid retrieval combining keyword + embedding + AST"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        kw = KeywordRetrieval()
        emb = EmbeddingRetrieval()
        ast = ASTRetrieval()

        kw_result = kw.retrieve(query, repo_path)
        emb_result = emb.retrieve(query, repo_path)
        ast_result = ast.retrieve(query, repo_path)

        # Merge and deduplicate with score weighting
        file_scores: Dict[str, float] = {}
        for r in kw_result.files:
            file_scores[r["path"]] = file_scores.get(r["path"], 0) + r["score"] * 1.0
        for r in emb_result.files:
            file_scores[r["path"]] = file_scores.get(r["path"], 0) + r["score"] * 1.5
        for r in ast_result.files:
            file_scores[r["path"]] = file_scores.get(r["path"], 0) + r["score"] * 1.2

        total_candidates = (
            kw_result.total_candidates
            + emb_result.total_candidates
            + ast_result.total_candidates
        )

        results = sorted(
            [{"path": p, "score": s, "method": "hybrid"} for p, s in file_scores.items()],
            key=lambda x: -x["score"],
        )[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=results,
            context_size_tokens=self.estimate_tokens(str(results)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


class ModelPlannedRetrieval(RetrievalPolicy):
    name = "model_planned"
    description = "Model-planned retrieval using task decomposition"

    def retrieve(self, query: str, repo_path: str) -> RetrievalResult:
        start = time.time()
        repo = Path(repo_path)
        query_lower = query.lower()

        # Plan: extract key entities from query
        entities = re.findall(r'(\w+(?:\s+\w+)?)\s+(?:function|class|file|method|api|test|bug|fix|feature)',
                              query_lower)
        entities = [e.strip() for e in entities if e.strip()]
        if not entities:
            entities = [w for w in re.findall(r'\w{4,}', query_lower)][:3]

        # For each entity, search with strategy determined by entity type
        results: Dict[str, float] = {}
        total_candidates = 0

        for f in repo.rglob("*"):
            if f.is_file() and f.suffix in {
                ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java",
                ".c", ".cpp", ".h", ".hpp", ".md", ".yaml", ".json",
            }:
                try:
                    text = f.read_text(errors="ignore")
                    total_candidates += 1
                    text_lower = text.lower()
                    rel = str(f.relative_to(repo))

                    score = 0.0
                    for entity in entities:
                        if entity in text_lower:
                            score += 1.0
                        elif any(e in rel.lower() for e in entities):
                            score += 0.5

                    # Bonus for matching file type
                    if "test" in query_lower and "test" in rel:
                        score += 0.3
                    if "config" in query_lower and ("config" in rel or "setting" in rel):
                        score += 0.3

                    if score > 0:
                        results[rel] = max(results.get(rel, 0), score)
                except Exception:
                    pass

        ranked = sorted(
            [{"path": p, "score": s, "method": "model_planned"} for p, s in results.items()],
            key=lambda x: -x["score"],
        )[:10]
        elapsed = int((time.time() - start) * 1000)

        return RetrievalResult(
            files=ranked,
            context_size_tokens=self.estimate_tokens(str(ranked)),
            latency_ms=elapsed,
            policy_name=self.name,
            total_candidates=total_candidates,
        )


RETRIEVAL_POLICIES: List[RetrievalPolicy] = [
    KeywordRetrieval(),
    EmbeddingRetrieval(),
    GraphRetrieval(),
    ASTRetrieval(),
    GitHistoryRetrieval(),
    HybridRetrieval(),
    ModelPlannedRetrieval(),
]
