from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import re


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


@dataclass
class ContextBudget:
    included_files: List[str] = field(default_factory=list)
    included_summaries: Dict[str, str] = field(default_factory=dict)
    omitted_items: List[str] = field(default_factory=list)
    lazy_retrieval_queue: List[str] = field(default_factory=list)
    estimated_tokens: int = 0


class ContextBudgetOptimizer:
    def __init__(
        self,
        context_limit: int = 128_000,
        summary_token_budget: int = 4_000,
        file_token_budget: int = 60_000,
        lazy_threshold: int = 2_000,
    ):
        self.context_limit = context_limit
        self.summary_token_budget = summary_token_budget
        self.file_token_budget = file_token_budget
        self.lazy_threshold = lazy_threshold

    def optimize(
        self,
        task: str,
        layer1_tree: Dict[str, Any],
        layer2_apis: Dict[str, Any],
        layer3_subsystems: Dict[str, Any],
        layer4_invariants: Dict[str, Any],
    ) -> ContextBudget:
        task_keywords = self._extract_keywords(task)
        task_lower = task.lower()

        modules = layer2_apis.get("modules", [])
        subsystems = layer3_subsystems.get("subsystems", {})
        risk_zones = layer4_invariants.get("risk_zones", [])
        tree_files = self._flatten_tree(layer1_tree.get("file_tree", []))

        scored_files: List[Tuple[float, str, Dict[str, Any]]] = []
        for module in modules:
            filepath = module.get("file", "")
            score = self._score_file(
                filepath, module, task_keywords, task_lower, risk_zones, tree_files
            )
            estimated_size = self._estimate_file_size(filepath, module)
            utility = score / max(estimated_size, 1)
            scored_files.append((utility, filepath, module))

        scored_files.sort(reverse=True)

        budget = ContextBudget()
        remaining = self.context_limit

        task_tokens = estimate_tokens(task)
        remaining -= task_tokens

        summaries = self._generate_summaries(
            layer1_tree, layer2_apis, layer3_subsystems, layer4_invariants
        )
        summary_text = self._format_summaries(summaries)
        summary_tokens = estimate_tokens(summary_text)
        budget.included_summaries = summaries
        budget.estimated_tokens += min(summary_tokens, self.summary_token_budget)
        remaining -= min(summary_tokens, self.summary_token_budget)

        for utility, filepath, module in scored_files:
            if remaining <= 0:
                budget.lazy_retrieval_queue.append(filepath)
                continue

            file_size = self._estimate_file_size(filepath, module)
            file_size_tokens = estimate_tokens(str(file_size))

            if file_size_tokens > self.lazy_threshold:
                budget.lazy_retrieval_queue.append(filepath)
                continue

            if file_size_tokens > remaining:
                budget.lazy_retrieval_queue.append(filepath)
                continue

            budget.included_files.append(filepath)
            budget.estimated_tokens += file_size_tokens
            remaining -= file_size_tokens

        all_files = set(m.get("file", "") for m in modules)
        included_set = set(budget.included_files)
        budget.omitted_items = sorted(all_files - included_set)[:50]

        budget.estimated_tokens = self.context_limit - remaining
        return budget

    def _extract_keywords(self, task: str) -> Set[str]:
        words = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]*", task.lower())
        stopwords = {
            "the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
            "and", "or", "but", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "shall",
            "this", "that", "these", "those", "it", "its", "they", "them",
            "we", "you", "i", "me", "my", "our", "what", "which", "who",
            "how", "when", "where", "why", "not", "no", "nor", "if",
            "then", "else", "all", "each", "every", "some", "any", "both",
            "few", "more", "most", "other", "into", "over", "after",
            "before", "between", "under", "above", "below", "up", "down",
            "out", "off", "about", "than", "so", "as", "just", "also",
            "very", "too", "really", "please", "need", "want", "help",
        }
        return {w for w in words if w not in stopwords and len(w) > 1}

    def _score_file(
        self,
        filepath: str,
        module: Dict[str, Any],
        keywords: Set[str],
        task_lower: str,
        risk_zones: List[Dict[str, Any]],
        tree_files: Set[str],
    ) -> float:
        score = 0.0
        file_lower = filepath.lower()

        for kw in keywords:
            if kw in file_lower:
                score += 10.0
            if kw in " ".join(module.get("public_exports", [])).lower():
                score += 5.0

        for rz in risk_zones:
            if filepath in rz.get("file", ""):
                risk = rz.get("risk", "")
                score += 8.0 if risk == "high" else 3.0

        classes = module.get("classes", [])
        functions = module.get("functions", [])
        score += min(len(classes) * 2 + len(functions), 20)

        hq_indicators = ["__init__", "main", "core", "api", "router", "service", "controller"]
        for indicator in hq_indicators:
            if indicator in file_lower:
                score += 3.0

        imports = module.get("imports", [])
        if len(imports) > 0:
            score += min(len(imports) * 0.5, 5.0)

        entry_points = tree_files
        if filepath in entry_points:
            score += 15.0

        return score

    def _estimate_file_size(self, filepath: str, module: Dict[str, Any]) -> int:
        classes = module.get("classes", [])
        functions = module.get("functions", [])
        methods = sum(len(c.get("methods", [])) for c in classes)
        return (len(classes) * 30 + methods * 5 + len(functions) * 15 + 20)

    def _flatten_tree(self, tree: List[Dict[str, Any]]) -> Set[str]:
        files: Set[str] = set()
        for entry in tree:
            if entry.get("type") == "file":
                files.add(entry["name"])
            elif entry.get("children"):
                files.update(self._flatten_tree(entry["children"]))
        return files

    def _generate_summaries(
        self,
        layer1_tree: Dict[str, Any],
        layer2_apis: Dict[str, Any],
        layer3_subsystems: Dict[str, Any],
        layer4_invariants: Dict[str, Any],
    ) -> Dict[str, str]:
        return {
            "file_tree": self._summarize_tree(layer1_tree),
            "apis": self._summarize_apis(layer2_apis),
            "subsystems": self._summarize_subsystems(layer3_subsystems),
            "invariants": self._summarize_invariants(layer4_invariants),
        }

    def _summarize_tree(self, tree: Dict[str, Any]) -> str:
        return (
            f"Repo: {tree.get('repo_name', 'unknown')} | "
            f"Files: {tree.get('total_files', 0)} | "
            f"Languages: {', '.join(tree.get('languages', {}).keys())} | "
            f"Frameworks: {', '.join(tree.get('frameworks', []))} | "
            f"Entry points: {[e['path'] for e in tree.get('entry_points', [])]}"
        )

    def _summarize_apis(self, apis: Dict[str, Any]) -> str:
        modules = apis.get("modules", [])
        total_classes = sum(len(m.get("classes", [])) for m in modules)
        total_functions = sum(len(m.get("functions", [])) for m in modules)
        return (
            f"Modules: {apis.get('total_modules', 0)} | "
            f"Classes: {total_classes} | Functions: {total_functions}"
        )

    def _summarize_subsystems(self, subsystems: Dict[str, Any]) -> str:
        sub_names = list(subsystems.get("subsystems", {}).keys())
        deps = subsystems.get("subsystem_dependency_graph", {})
        cycles = subsystems.get("circular_dependencies", [])
        return (
            f"Subsystems: {', '.join(sub_names)} | "
            f"Dependency edges: {sum(len(v) for v in deps.values())} | "
            f"Cycles: {len(cycles)}"
        )

    def _summarize_invariants(self, invariants: Dict[str, Any]) -> str:
        return (
            f"Risk zones: {len(invariants.get('risk_zones', []))} | "
            f"Shared constants: {len(invariants.get('shared_constants', []))} | "
            f"Circular imports: {len(invariants.get('circular_imports', []))} | "
            f"Large files: {len(invariants.get('large_files', []))} | "
            f"Git history: {invariants.get('change_patterns', {}).get('available', False)}"
        )

    def _format_summaries(self, summaries: Dict[str, str]) -> str:
        return "\n".join(f"[{k}] {v}" for k, v in summaries.items())
