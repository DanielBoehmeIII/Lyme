from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime


AVAILABLE_TOOLS = [
    "grep_search",
    "ast_parse",
    "dep_graph",
    "vector_search",
    "test_runner",
    "shell_command",
    "package_manager",
    "static_analyzer",
    "formatter",
    "type_checker",
]

TOOL_CAPABILITIES: Dict[str, List[str]] = {
    "grep_search": ["find_definition", "find_references", "search_pattern"],
    "ast_parse": ["find_definition", "parse_structure", "extract_symbols"],
    "dep_graph": ["understand_architecture", "trace_dependencies", "analyze_imports"],
    "vector_search": ["semantic_search", "find_similar_code", "concept_lookup"],
    "test_runner": ["fix_bug", "run_tests", "verify_behavior"],
    "shell_command": ["execute_build", "run_script", "dev_ops"],
    "package_manager": ["install_dependency", "update_package", "check_version"],
    "static_analyzer": ["lint", "find_bugs", "code_quality"],
    "formatter": ["format_code", "style_check"],
    "type_checker": ["type_check", "verify_types"],
}

TOOL_COST_WEIGHTS: Dict[str, float] = {
    "grep_search": 0.1,
    "ast_parse": 0.3,
    "dep_graph": 0.4,
    "vector_search": 0.5,
    "test_runner": 0.6,
    "shell_command": 0.2,
    "package_manager": 0.1,
    "static_analyzer": 0.4,
    "formatter": 0.1,
    "type_checker": 0.3,
}

TOOL_RELIABILITY: Dict[str, float] = {
    "grep_search": 0.95,
    "ast_parse": 0.9,
    "dep_graph": 0.85,
    "vector_search": 0.7,
    "test_runner": 0.9,
    "shell_command": 0.8,
    "package_manager": 0.95,
    "static_analyzer": 0.85,
    "formatter": 0.98,
    "type_checker": 0.9,
}

HEURISTIC_RULES: Dict[str, List[str]] = {
    "find_definition": ["grep_search", "ast_parse"],
    "understand_architecture": ["dep_graph"],
    "fix_bug": ["test_runner", "grep_search"],
    "find_references": ["grep_search", "ast_parse"],
    "semantic_search": ["vector_search", "grep_search"],
    "format_code": ["formatter"],
    "type_check": ["type_checker"],
    "install_dependency": ["package_manager"],
    "run_tests": ["test_runner"],
    "lint_code": ["static_analyzer"],
}


@dataclass
class RouterDecision:
    chosen_tool: str
    alternatives: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.0
    estimated_cost: float = 0.0
    estimated_reliability: float = 0.0
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "chosen_tool": self.chosen_tool,
            "alternatives": self.alternatives,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "estimated_cost": self.estimated_cost,
            "estimated_reliability": self.estimated_reliability,
            "timestamp": self.timestamp,
        }

    def explain(self) -> str:
        lines = [
            f"Decision: use {self.chosen_tool}",
            f"Confidence: {self.confidence:.0%}",
            f"Rationale: {self.rationale}",
        ]
        if self.alternatives:
            alts = ", ".join(self.alternatives)
            lines.append(f"Alternatives considered: {alts}")
        lines.append(f"Estimated cost: {self.estimated_cost:.2f}")
        lines.append(f"Estimated reliability: {self.estimated_reliability:.0%}")
        return "\n".join(lines)


class ToolRouter:
    def __init__(self):
        self.decision_log: List[RouterDecision] = []

    def decide(self, task: str, context: Optional[Dict] = None) -> RouterDecision:
        task_lower = task.lower()
        candidates = self._score_all_tools(task_lower)
        candidates.sort(key=lambda x: x[1], reverse=True)
        chosen = candidates[0][0] if candidates else "grep_search"
        score = candidates[0][1] if candidates else 0.0
        alternatives = [t for t, s in candidates[1:4] if s > 0]
        rationale = self._generate_rationale(task_lower, chosen, alternatives)

        decision = RouterDecision(
            chosen_tool=chosen,
            alternatives=alternatives,
            rationale=rationale,
            confidence=min(1.0, score / 10.0),
            estimated_cost=TOOL_COST_WEIGHTS.get(chosen, 0.5),
            estimated_reliability=TOOL_RELIABILITY.get(chosen, 0.8),
            timestamp=datetime.utcnow().isoformat(),
        )
        self.decision_log.append(decision)
        return decision

    def _score_all_tools(self, task: str) -> List[tuple]:
        scores: List[tuple] = []
        for tool in AVAILABLE_TOOLS:
            s = self._score_tool(tool, task)
            scores.append((tool, s))
        return scores

    def _score_tool(self, tool: str, task: str) -> float:
        score = 0.0
        task_words = set(task.split())
        for intent, preferred_tools in HEURISTIC_RULES.items():
            intent_words = set(intent.split("_"))
            if intent_words & task_words:
                if tool in preferred_tools:
                    score += 5.0
                elif preferred_tools:
                    score += 0.5
        for capability in TOOL_CAPABILITIES.get(tool, []):
            cap_words = set(capability.split("_"))
            if cap_words & task_words:
                score += 3.0
        if "find" in task_words and tool in ("grep_search", "ast_parse"):
            score += 2.0
        if "search" in task_words and tool in ("grep_search", "vector_search"):
            score += 2.0
        if "test" in task_words and tool == "test_runner":
            score += 3.0
        if "format" in task_words and tool == "formatter":
            score += 3.0
        if "install" in task_words and tool == "package_manager":
            score += 3.0
        return score

    def _generate_rationale(self, task: str, chosen: str, alternatives: List[str]) -> str:
        for intent, tools in HEURISTIC_RULES.items():
            intent_words = set(intent.split("_"))
            if intent_words & set(task.split()):
                if chosen in tools:
                    return f"Task requires '{intent.replace('_', ' ')}'; {chosen} is the recommended tool"
        caps = TOOL_CAPABILITIES.get(chosen, [])
        if caps:
            return f"{chosen} supports: {', '.join(caps)}"
        return f"{chosen} is the highest-scored tool for this task"

    def get_log(self) -> List[RouterDecision]:
        return list(self.decision_log)

    def clear_log(self):
        self.decision_log.clear()

    def explain_last(self) -> str:
        if not self.decision_log:
            return "No decisions logged yet"
        return self.decision_log[-1].explain()

    def summarize_log(self) -> Dict[str, int]:
        summary: Dict[str, int] = {}
        for decision in self.decision_log:
            summary[decision.chosen_tool] = summary.get(decision.chosen_tool, 0) + 1
        return summary
