"""Week 136 — Retriever Specialist.

Goal: Select the smallest useful context for weak local models.

Chooses files, symbols, summaries, tests, git history, previous memories, and risk zones.
Benchmarks against heuristic retrieval, embedding retrieval, and raw context.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from pathlib import Path
import time
import re

from .interfaces import RetrieverInput, RetrieverOutput, AuditTrace, FailureLabel
from ..retrieval.policies import (
    RETRIEVAL_POLICIES, RetrievalPolicy, RetrievalResult,
    KeywordRetrieval, EmbeddingRetrieval, HybridRetrieval,
    ASTRetrieval, GitHistoryRetrieval,
)
from ..retrieval.experiment import RetrievalExperiment


def _get_policy(name: str) -> RetrievalPolicy:
    for p in RETRIEVAL_POLICIES:
        if p.name == name:
            return p
    return HybridRetrieval()


POLICY_PRIORITY = {
    "repo_qa": "keyword",
    "bug_locate": "hybrid",
    "failure_explain": "hybrid",
    "patch_plan": "hybrid",
    "patch_apply": "model_planned",
    "verify_patch": "ast",
    "test_repair": "git_history",
    "code_generation": "model_planned",
    "refactor": "graph",
    "doc_update": "keyword",
    "dependency_migration": "graph",
    "cross_repo": "embedding",
}


class RetrieverSpecialist:
    """Retriever Specialist — selects smallest useful context for weak local models."""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._retrieval_history: List[dict] = []

    def process(self, inp: RetrieverInput) -> RetrieverOutput:
        trace = AuditTrace(specialist="retriever", trace_id=f"ret-{int(time.time()*1000)}")
        trace.add_step("input_received", {
            "task": inp.task[:100],
            "target_context_tokens": inp.target_context_tokens,
            "policy": inp.retrieval_policy,
        })

        # Step 1: Select optimal retrieval policy
        policy_name = inp.retrieval_policy
        task_lower = inp.task.lower()
        for task_type, best_policy in POLICY_PRIORITY.items():
            if task_type.replace("_", " ") in task_lower:
                policy_name = best_policy
                break
        trace.add_decision(
            "policy_selected",
            f"Selected {policy_name} for task: {inp.task[:60]}",
            [p.name for p in RETRIEVAL_POLICIES],
        )

        # Step 2: Run primary retrieval
        policy = _get_policy(policy_name)
        primary_result = policy.retrieve(inp.task, inp.repo_path)
        trace.add_step("primary_retrieval", {
            "policy": policy_name,
            "files_found": len(primary_result.files),
            "latency_ms": primary_result.latency_ms,
        })

        # Step 3: Run supplementary retrievals for symbols, tests, history
        ast_policy = ASTRetrieval()
        git_policy = GitHistoryRetrieval()
        ast_result = ast_policy.retrieve(inp.task, inp.repo_path)
        git_result = git_policy.retrieve(inp.task, inp.repo_path)

        # Step 4: Merge and deduplicate results within budget
        merged = self._merge_within_budget(
            [primary_result, ast_result, git_result],
            inp.target_context_tokens,
            inp.affected_files_hint,
        )

        # Step 5: Extract symbols from selected files
        selected_symbols = self._extract_symbols(merged["files"], inp.repo_path)

        # Step 6: Identify risk zones
        risk_zones = self._identify_risk_zones(merged["files"], inp.task)

        # Step 7: Calculate missing/irrelevant rates
        missing_rate, irrelevant_rate = self._calculate_coverage(
            merged["files"], inp.affected_files_hint
        )

        # Step 8: Compute confidence
        confidence = self._compute_confidence(missing_rate, irrelevant_rate, merged["within_budget"])

        trace.add_step("output_produced", {
            "files_selected": len(merged["files"]),
            "symbols_found": len(selected_symbols),
            "total_tokens": merged["total_tokens"],
            "within_budget": merged["within_budget"],
            "missing_rate": round(missing_rate, 3),
            "irrelevant_rate": round(irrelevant_rate, 3),
            "confidence": round(confidence, 3),
        })

        failure_label = None
        if missing_rate > 0.5:
            failure_label = FailureLabel.INSUFFICIENT_CONTEXT

        result = RetrieverOutput(
            selected_files=merged["files"],
            selected_symbols=selected_symbols,
            relevant_tests=[f["path"] for f in merged["files"] if "test" in f.get("path", "")],
            git_history=[f["path"] for f in git_result.files],
            prior_memories=[],
            risk_zones=risk_zones,
            context_size_tokens=merged["total_tokens"],
            missing_context_rate=missing_rate,
            irrelevant_context_rate=irrelevant_rate,
            confidence=confidence,
            failure_label=failure_label,
            trace=trace,
        )

        self._retrieval_history.append({
            "task": inp.task[:80],
            "policy": policy_name,
            "files": len(result.selected_files),
            "tokens": result.context_size_tokens,
            "confidence": confidence,
        })

        return result

    def _merge_within_budget(
        self, results: List[RetrievalResult],
        budget_tokens: int,
        hints: List[str],
    ) -> dict:
        seen_paths: Dict[str, float] = {}
        for result in results:
            for f in result.files:
                path = f["path"]
                score = f.get("score", 0)
                if path in seen_paths:
                    seen_paths[path] = max(seen_paths[path], score)
                else:
                    seen_paths[path] = score

        # Boost hint files
        for hint in hints:
            if hint in seen_paths:
                seen_paths[hint] += 0.5
            else:
                seen_paths[hint] = 0.5

        # Sort by score, select within token budget
        sorted_files = sorted(seen_paths.items(), key=lambda x: -x[1])
        selected = []
        total_tokens = 0
        for path, score in sorted_files:
            file_tokens = self._estimate_file_tokens(path)
            if total_tokens + file_tokens > budget_tokens and selected:
                break
            selected.append({
                "path": path,
                "relevance_score": round(score, 3),
                "content_summary": "",
            })
            total_tokens += file_tokens

        return {
            "files": selected,
            "total_tokens": total_tokens,
            "within_budget": total_tokens <= budget_tokens,
        }

    def _estimate_file_tokens(self, path: str) -> int:
        try:
            full = Path(self.repo_path) / path
            if full.exists():
                text = full.read_text(errors="ignore")
                return len(text.split())
        except Exception:
            pass
        return 500

    def _extract_symbols(self, files: List[dict], repo_path: str) -> List[dict]:
        symbols = []
        for f in files:
            try:
                full = Path(repo_path) / f["path"]
                if full.exists() and full.suffix == ".py":
                    text = full.read_text(errors="ignore")
                    classes = re.findall(r'^class\s+(\w+)', text, re.MULTILINE)
                    functions = re.findall(r'^def\s+(\w+)', text, re.MULTILINE)
                    for c in classes:
                        symbols.append({"name": c, "type": "class", "file": f["path"]})
                    for fn in functions:
                        symbols.append({"name": fn, "type": "function", "file": f["path"]})
            except Exception:
                pass
        return symbols

    def _identify_risk_zones(self, files: List[dict], task: str) -> List[str]:
        zones = []
        task_lower = task.lower()
        for f in files:
            path = f["path"]
            if "__init__" in path:
                zones.append(f"{path}: package init — changes affect imports")
            if "config" in path.lower() or "setting" in path.lower():
                zones.append(f"{path}: configuration — changes affect runtime behavior")
            if "migration" in path.lower():
                zones.append(f"{path}: migration — requires rollback plan")
            if "test" in path:
                zones.append(f"{path}: test file — modifying affects coverage confidence")
            if "security" in path.lower() or "auth" in path.lower():
                zones.append(f"{path}: security/auth — changes have security implications")
            if "model" in path.lower() or "schema" in path.lower():
                zones.append(f"{path}: model/schema — changes affect data layer")
        if "delete" in task_lower or "remove" in task_lower:
            zones.append("task involves deletion — verify callers")
        if "api" in task_lower or "endpoint" in task_lower:
            zones.append("task involves API changes — verify consumer contracts")
        return zones

    def _calculate_coverage(self, files: List[dict], hints: List[str]) -> tuple:
        if not hints:
            return 0.0, 0.0
        retrieved = {f["path"] for f in files}
        hint_set = set(hints)
        if not hint_set:
            return 0.0, 0.0
        missing = hint_set - retrieved
        irrelevant = retrieved - hint_set
        missing_rate = len(missing) / len(hint_set) if hint_set else 0.0
        irrelevant_rate = len(irrelevant) / len(retrieved) if retrieved else 0.0
        return missing_rate, irrelevant_rate

    def _compute_confidence(self, missing_rate: float, irrelevant_rate: float, within_budget: bool) -> float:
        base = 0.85
        base -= missing_rate * 0.5
        base -= irrelevant_rate * 0.3
        if not within_budget:
            base -= 0.1
        return max(0.05, min(0.99, base))

    def get_history(self) -> List[dict]:
        return self._retrieval_history


def benchmark_retrieval(repo_path: str = "."):
    """Compare retriever specialist vs heuristic vs embedding vs raw context."""
    specialist = RetrieverSpecialist(repo_path)
    heuristic = KeywordRetrieval()
    embedding = EmbeddingRetrieval()

    tasks = [
        "Find the authentication login handler",
        "Where is the database connection configured?",
        "How are test fixtures defined?",
        "What API endpoints are registered?",
        "Find the main application entry point",
    ]

    results = []
    for task in tasks:
        inp = RetrieverInput(task=task, repo_path=repo_path, target_context_tokens=4096)
        spec_out = specialist.process(inp)

        h_result = heuristic.retrieve(task, repo_path)
        e_result = embedding.retrieve(task, repo_path)

        results.append({
            "task": task[:50],
            "specialist_files": len(spec_out.selected_files),
            "specialist_tokens": spec_out.context_size_tokens,
            "specialist_missing": round(spec_out.missing_context_rate, 3),
            "specialist_irrelevant": round(spec_out.irrelevant_context_rate, 3),
            "heuristic_files": len(h_result.files),
            "embedding_files": len(e_result.files),
        })

    return {
        "benchmark": "retriever_vs_baselines",
        "total_tasks": len(tasks),
        "results": results,
        "summary": {
            "avg_specialist_files": round(sum(r["specialist_files"] for r in results) / len(results), 1),
            "avg_specialist_tokens": round(sum(r["specialist_tokens"] for r in results) / len(results), 0),
            "avg_missing_rate": round(sum(r["specialist_missing"] for r in results) / len(results), 3),
            "avg_irrelevant_rate": round(sum(r["specialist_irrelevant"] for r in results) / len(results), 3),
        }
    }


retriever = RetrieverSpecialist()
