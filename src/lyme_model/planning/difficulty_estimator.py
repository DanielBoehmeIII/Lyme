"""Week 116 — Task Difficulty Estimator.

Estimate task difficulty before running Lyme Model:
- task type
- expected files involved
- risk
- ambiguity
- model difficulty
- tool requirements
- likely success probability
- whether local model is enough

Uses Lyme Audit outcomes to calibrate.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
from enum import Enum
import json
import math


class TaskType(Enum):
    REPO_QA = "repo_qa"
    BUG_LOCATE = "bug_locate"
    FAILURE_EXPLAIN = "failure_explain"
    PATCH_PLAN = "patch_plan"
    PATCH_APPLY = "patch_apply"
    VERIFY_PATCH = "verify_patch"
    TEST_REPAIR = "test_repair"
    CODE_GENERATION = "code_generation"
    REFACTOR = "refactor"
    DOC_UPDATE = "doc_update"
    DEPENDENCY_MIGRATION = "dependency_migration"
    CROSS_REPO = "cross_repo"
    UNKNOWN = "unknown"


class DifficultyLevel(Enum):
    TRIVIAL = "trivial"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    VERY_HARD = "very_hard"
    IMPOSSIBLE = "impossible"


class RiskLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendedMode(Enum):
    LOCAL_FAST = "local_fast"
    LOCAL_CAREFUL = "local_careful"
    LOCAL_MULTI_CANDIDATE = "local_multi_candidate"
    LOCAL_WITH_CRITIC = "local_with_critic"
    LOCAL_WITH_HUMAN_CHECKPOINT = "local_with_human_checkpoint"
    FALLBACK_STRONGER = "fallback_stronger"
    AUDIT_ONLY = "audit_only"
    REFUSE = "refuse"


@dataclass
class DifficultyEstimate:
    task_type: TaskType
    difficulty_score: float
    difficulty_level: DifficultyLevel
    risk: RiskLevel
    ambiguity: float
    expected_files: int
    model_difficulty: float
    tool_requirements: List[str]
    success_probability: float
    local_model_sufficient: bool
    recommended_mode: RecommendedMode
    expected_latency_s: float
    confidence: float
    reasoning: List[str]

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type.value,
            "difficulty_score": round(self.difficulty_score, 3),
            "difficulty_level": self.difficulty_level.value,
            "risk": self.risk.value,
            "ambiguity": round(self.ambiguity, 3),
            "expected_files": self.expected_files,
            "model_difficulty": round(self.model_difficulty, 3),
            "tool_requirements": self.tool_requirements,
            "success_probability": round(self.success_probability, 3),
            "local_model_sufficient": self.local_model_sufficient,
            "recommended_mode": self.recommended_mode.value,
            "expected_latency_s": round(self.expected_latency_s, 1),
            "confidence": round(self.confidence, 3),
            "reasoning": self.reasoning[:5],
        }


# Task type base difficulty (0=trivial, 1=impossible)
TASK_TYPE_DIFFICULTY = {
    TaskType.REPO_QA: 0.15,
    TaskType.BUG_LOCATE: 0.35,
    TaskType.FAILURE_EXPLAIN: 0.40,
    TaskType.PATCH_PLAN: 0.50,
    TaskType.PATCH_APPLY: 0.55,
    TaskType.VERIFY_PATCH: 0.30,
    TaskType.TEST_REPAIR: 0.50,
    TaskType.CODE_GENERATION: 0.65,
    TaskType.REFACTOR: 0.60,
    TaskType.DOC_UPDATE: 0.25,
    TaskType.DEPENDENCY_MIGRATION: 0.70,
    TaskType.CROSS_REPO: 0.80,
    TaskType.UNKNOWN: 0.50,
}

# Modifiers for task characteristics
TASK_MODIFIERS = {
    "single_file": -0.10,
    "multi_file": 0.15,
    "well_documented": -0.10,
    "undocumented": 0.20,
    "has_tests": -0.10,
    "no_tests": 0.15,
    "familiar_framework": -0.05,
    "unfamiliar_framework": 0.15,
    "explicit_error_message": -0.15,
    "vague_description": 0.20,
    "single_step": -0.10,
    "multi_step": 0.20,
    "generative": 0.15,
    "analytical": -0.10,
    "high_risk_change": 0.25,
    "low_risk_change": -0.10,
    "requires_test_update": 0.15,
    "no_test_update": -0.05,
}


class DifficultyEstimator:
    """Estimate task difficulty for Lyme Model."""

    def __init__(self, calibration_data: Optional[Dict[str, float]] = None):
        self.calibration_data = calibration_data or {}
        self._audit_calibration: Dict[str, float] = {}

    def classify_task(self, task_description: str) -> TaskType:
        desc = task_description.lower()
        type_map: List[Tuple[List[str], TaskType]] = [
            (["what", "language", "framework", "dependency", "how many", "does this"],
             TaskType.REPO_QA),
            (["find bug", "locate", "where is", "what is wrong", "why does"],
             TaskType.BUG_LOCATE),
            (["explain", "why did", "why is", "failure", "fail"],
             TaskType.FAILURE_EXPLAIN),
            (["plan", "how to fix", "what to change"],
             TaskType.PATCH_PLAN),
            (["fix", "apply", "implement", "add", "change", "write"],
             TaskType.PATCH_APPLY),
            (["verify", "check", "test", "validate"],
             TaskType.VERIFY_PATCH),
            (["repair test", "fix test", "test fail"],
             TaskType.TEST_REPAIR),
            (["generate", "write code", "create", "implement feature"],
             TaskType.CODE_GENERATION),
            (["refactor", "rename", "restructure", "clean up"],
             TaskType.REFACTOR),
            (["document", "update doc", "readme", "docstring"],
             TaskType.DOC_UPDATE),
            (["migrate", "upgrade dependency", "bump", "update package"],
             TaskType.DEPENDENCY_MIGRATION),
            (["cross", "multiple repo", "across repo"],
             TaskType.CROSS_REPO),
        ]
        for keywords, task_type in type_map:
            if any(k in desc for k in keywords):
                return task_type
        return TaskType.UNKNOWN

    def estimate_ambiguity(self, task: str) -> float:
        """Estimate ambiguity (0=precise, 1=very ambiguous)."""
        desc = task.lower()
        ambiguity = 0.0
        ambiguous_terms = [
            "maybe", "possibly", "might", "could", "some", "thing",
            "whatever", "etc", "stuff", "better", "improve",
            "optimize", "clean", "nice", "good",
        ]
        vague_length = sum(1 for t in ambiguous_terms if t in desc)
        ambiguity += vague_length * 0.1

        if len(desc.split()) < 5:
            ambiguity += 0.2
        if "?" in task and len(task.split()) < 10:
            ambiguity += 0.1
        if desc.count(" ") < 3:
            ambiguity += 0.3
        return min(1.0, ambiguity)

    def estimate_files_involved(self, task: str, repo_size_hint: Optional[int] = None) -> int:
        desc = task.lower()
        if any(w in desc for w in ["refactor", "migrate", "restructure", "cross"]):
            return max(5, (repo_size_hint or 20) // 100)
        if any(w in desc for w in ["fix", "repair", "locate", "explain"]):
            return 2
        if any(w in desc for w in ["what", "how many", "does this"]):
            return 1
        return 3

    def estimate_risk(self, task: str, task_type: TaskType) -> RiskLevel:
        desc = task.lower()
        high_risk_keywords = [
            "delete", "remove", "migrate", "change api", "breaking",
            "security", "critical", "production",
        ]
        if any(k in desc for k in high_risk_keywords):
            return RiskLevel.HIGH
        if task_type in (TaskType.PATCH_APPLY, TaskType.DEPENDENCY_MIGRATION, TaskType.REFACTOR):
            return RiskLevel.MEDIUM
        if task_type in (TaskType.REPO_QA, TaskType.VERIFY_PATCH, TaskType.DOC_UPDATE):
            return RiskLevel.LOW
        return RiskLevel.NONE

    def estimate_model_difficulty(self, task: str, task_type: TaskType) -> float:
        base = TASK_TYPE_DIFFICULTY.get(task_type, 0.5)
        desc = task.lower()
        modifiers = 0.0
        if any(w in desc for w in ["multi", "multiple", "all", "every"]):
            modifiers += 0.1
        if len(desc.split()) > 30:
            modifiers += 0.1
        if any(w in desc for w in ["complicated", "complex", "hard", "difficult"]):
            modifiers += 0.15
        return min(1.0, base + modifiers)

    def estimate_success_probability(self, task_type: TaskType, difficulty: float, ambiguity: float, risk: RiskLevel) -> float:
        base_rates = {
            TaskType.REPO_QA: 0.94,
            TaskType.BUG_LOCATE: 0.75,
            TaskType.FAILURE_EXPLAIN: 0.80,
            TaskType.PATCH_PLAN: 0.70,
            TaskType.PATCH_APPLY: 0.60,
            TaskType.VERIFY_PATCH: 0.85,
            TaskType.TEST_REPAIR: 0.65,
            TaskType.CODE_GENERATION: 0.50,
            TaskType.REFACTOR: 0.55,
            TaskType.DOC_UPDATE: 0.85,
            TaskType.DEPENDENCY_MIGRATION: 0.40,
            TaskType.CROSS_REPO: 0.30,
            TaskType.UNKNOWN: 0.50,
        }
        base = base_rates.get(task_type, 0.5)
        penalty = difficulty * 0.3 + ambiguity * 0.2
        if risk in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            penalty += 0.15
        return max(0.05, min(0.99, base - penalty))

    def recommend_mode(self, task_type: TaskType, difficulty: float, risk: RiskLevel, local_sufficient: bool) -> RecommendedMode:
        if not local_sufficient:
            return RecommendedMode.FALLBACK_STRONGER
        if risk in (RiskLevel.CRITICAL, RiskLevel.HIGH) and difficulty > 0.6:
            return RecommendedMode.LOCAL_WITH_HUMAN_CHECKPOINT
        if difficulty > 0.7:
            if risk == RiskLevel.MEDIUM:
                return RecommendedMode.LOCAL_WITH_CRITIC
            return RecommendedMode.LOCAL_MULTI_CANDIDATE
        if difficulty > 0.5:
            return RecommendedMode.LOCAL_CAREFUL
        if difficulty > 0.3:
            return RecommendedMode.LOCAL_FAST
        if task_type == TaskType.REPO_QA:
            return RecommendedMode.LOCAL_FAST
        return RecommendedMode.AUDIT_ONLY

    def estimate_latency(self, task_type: TaskType, mode: RecommendedMode, files_involved: int) -> float:
        base = {
            TaskType.REPO_QA: 2.0,
            TaskType.BUG_LOCATE: 10.0,
            TaskType.FAILURE_EXPLAIN: 8.0,
            TaskType.PATCH_PLAN: 15.0,
            TaskType.PATCH_APPLY: 20.0,
            TaskType.VERIFY_PATCH: 5.0,
            TaskType.TEST_REPAIR: 25.0,
            TaskType.CODE_GENERATION: 15.0,
            TaskType.REFACTOR: 30.0,
            TaskType.DOC_UPDATE: 5.0,
            TaskType.DEPENDENCY_MIGRATION: 40.0,
            TaskType.CROSS_REPO: 60.0,
            TaskType.UNKNOWN: 10.0,
        }
        base_time = base.get(task_type, 10.0)
        mode_mult = {
            RecommendedMode.LOCAL_FAST: 0.8,
            RecommendedMode.LOCAL_CAREFUL: 1.5,
            RecommendedMode.LOCAL_MULTI_CANDIDATE: 3.0,
            RecommendedMode.LOCAL_WITH_CRITIC: 2.0,
            RecommendedMode.LOCAL_WITH_HUMAN_CHECKPOINT: 2.5,
            RecommendedMode.FALLBACK_STRONGER: 1.2,
            RecommendedMode.AUDIT_ONLY: 0.5,
            RecommendedMode.REFUSE: 0.1,
        }
        return base_time * mode_mult.get(mode, 1.0) * (1 + 0.1 * max(0, files_involved - 1))

    def estimate(self, task_description: str, repo_size_hint: Optional[int] = None,
                 hardware_tier: str = "cpu_8gb") -> DifficultyEstimate:
        task_type = self.classify_task(task_description)
        ambiguity = self.estimate_ambiguity(task_description)
        expected_files = self.estimate_files_involved(task_description, repo_size_hint)
        risk = self.estimate_risk(task_description, task_type)
        model_difficulty = self.estimate_model_difficulty(task_description, task_type)

        difficulty_score = min(1.0, (
            TASK_TYPE_DIFFICULTY.get(task_type, 0.5) * 0.4 +
            ambiguity * 0.2 +
            model_difficulty * 0.2 +
            ({"none": 0.0, "low": 0.1, "medium": 0.3, "high": 0.5, "critical": 0.7}.get(risk.value, 0.0)) * 0.2
        ))

        difficulty_level = self._score_to_level(difficulty_score)
        local_sufficient = difficulty_score <= 0.6 and risk not in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        success_probability = self.estimate_success_probability(task_type, difficulty_score, ambiguity, risk)
        recommended_mode = self.recommend_mode(task_type, difficulty_score, risk, local_sufficient)
        expected_latency = self.estimate_latency(task_type, recommended_mode, expected_files)
        estimator_confidence = self._estimate_confidence(task_type, difficulty_score, ambiguity)

        tool_reqs = self._get_tool_requirements(task_type)

        reasoning = self._build_reasoning(task_type, difficulty_score, risk, local_sufficient, recommended_mode)

        return DifficultyEstimate(
            task_type=task_type,
            difficulty_score=difficulty_score,
            difficulty_level=difficulty_level,
            risk=risk,
            ambiguity=ambiguity,
            expected_files=expected_files,
            model_difficulty=model_difficulty,
            tool_requirements=tool_reqs,
            success_probability=success_probability,
            local_model_sufficient=local_sufficient,
            recommended_mode=recommended_mode,
            expected_latency_s=expected_latency,
            confidence=estimator_confidence,
            reasoning=reasoning,
        )

    def _score_to_level(self, score: float) -> DifficultyLevel:
        if score < 0.1: return DifficultyLevel.TRIVIAL
        if score < 0.3: return DifficultyLevel.EASY
        if score < 0.5: return DifficultyLevel.MEDIUM
        if score < 0.7: return DifficultyLevel.HARD
        if score < 0.9: return DifficultyLevel.VERY_HARD
        return DifficultyLevel.IMPOSSIBLE

    def _estimate_confidence(self, task_type: TaskType, difficulty: float, ambiguity: float) -> float:
        base = 0.9 if task_type == TaskType.REPO_QA else 0.7
        penalty = difficulty * 0.3 + ambiguity * 0.2
        return max(0.3, min(0.98, base - penalty))

    def _get_tool_requirements(self, task_type: TaskType) -> List[str]:
        reqs = {
            TaskType.REPO_QA: ["file_indexer"],
            TaskType.BUG_LOCATE: ["file_indexer", "ast_parser", "grep"],
            TaskType.FAILURE_EXPLAIN: ["test_runner", "file_indexer"],
            TaskType.PATCH_PLAN: ["file_indexer", "ast_parser", "grep", "diff_checker"],
            TaskType.PATCH_APPLY: ["file_indexer", "ast_parser", "grep", "diff_checker", "test_runner"],
            TaskType.VERIFY_PATCH: ["test_runner", "diff_checker"],
            TaskType.TEST_REPAIR: ["test_runner", "file_indexer", "ast_parser"],
            TaskType.CODE_GENERATION: ["file_indexer", "model_inference"],
            TaskType.REFACTOR: ["file_indexer", "ast_parser", "grep", "test_runner"],
            TaskType.DOC_UPDATE: ["file_indexer", "grep"],
            TaskType.DEPENDENCY_MIGRATION: ["file_indexer", "grep", "test_runner", "dep_resolver"],
            TaskType.CROSS_REPO: ["file_indexer", "grep", "multi_repo"],
        }
        return reqs.get(task_type, ["file_indexer"])

    def _build_reasoning(self, task_type: TaskType, difficulty: float, risk: RiskLevel,
                         local_sufficient: bool, mode: RecommendedMode) -> List[str]:
        reasons = [f"Task classified as: {task_type.value}"]
        reasons.append(f"Base difficulty: {TASK_TYPE_DIFFICULTY.get(task_type, 0.5):.2f}")
        reasons.append(f"Risk level: {risk.value}")
        if local_sufficient:
            reasons.append("Local model should be sufficient")
        else:
            reasons.append("Local model may be insufficient — consider fallback")
        reasons.append(f"Recommended mode: {mode.value}")
        return reasons


estimator = DifficultyEstimator()
