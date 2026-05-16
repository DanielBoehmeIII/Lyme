from __future__ import annotations

import hashlib
import json
import math
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .intelligence_dimensions import IntelligenceDimension


class BenchmarkCategory(str, Enum):
    ABSTRACTION = "abstraction"
    CAUSAL = "causal"
    INVARIANT = "invariant"
    REPAIR = "repair"
    TEMPORAL = "temporal"
    EVOLUTION = "evolution"
    COORDINATION = "coordination"
    MEMORY = "memory"
    INTENT = "intent"
    UNCERTAINTY = "uncertainty"


@dataclass
class ResearchBenchmark:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    category: BenchmarkCategory = BenchmarkCategory.ABSTRACTION
    description: str = ""
    difficulty: float = 0.5
    steps: int = 1
    hidden_coupling: bool = False
    temporal_drift: bool = False
    ambiguous_goals: bool = False
    scoring_criteria: Dict[str, float] = field(default_factory=dict)
    anti_gaming_hash: str = ""
    created_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "difficulty": self.difficulty,
            "steps": self.steps,
            "hidden_coupling": self.hidden_coupling,
            "temporal_drift": self.temporal_drift,
            "ambiguous_goals": self.ambiguous_goals,
            "scoring_criteria": self.scoring_criteria,
            "version": self.version,
        }


@dataclass
class LongitudinalEvaluation:
    benchmark_id: str = ""
    timestamps: List[float] = field(default_factory=list)
    scores: List[float] = field(default_factory=list)
    versions: List[int] = field(default_factory=list)

    def add_measurement(self, score: float, version: int):
        self.timestamps.append(time.time())
        self.scores.append(score)
        self.versions.append(version)

    def get_trend(self) -> Dict[str, Any]:
        if len(self.scores) < 2:
            return {"trend": "insufficient_data"}

        slope = (self.scores[-1] - self.scores[0]) / max(len(self.scores) - 1, 1)
        volatility = sum(
            abs(self.scores[i] - self.scores[i - 1])
            for i in range(1, len(self.scores))
        ) / max(len(self.scores) - 1, 1)

        return {
            "slope": slope,
            "volatility": volatility,
            "improving": slope > 0,
            "best_score": max(self.scores),
            "latest_score": self.scores[-1],
            "measurement_count": len(self.scores),
        }


class AntiGamingProtection:
    def __init__(self):
        self._seeds: Dict[str, int] = {}

    def generate_variant(self, benchmark_id: str, template: str) -> str:
        seed = self._seeds.get(benchmark_id, 0)
        self._seeds[benchmark_id] = seed + 1

        variant_seed = int(hashlib.sha256(
            f"{benchmark_id}_{seed}_{int(time.time() / 86400)}".encode()
        ).hexdigest()[:8], 16)

        rng = random.Random(variant_seed)

        lines = template.split("\n")
        if len(lines) > 3:
            swap_idx = rng.randint(0, len(lines) - 2)
            lines[swap_idx], lines[swap_idx + 1] = lines[swap_idx + 1], lines[swap_idx]

        vars_to_rename = ["x", "y", "z", "val", "temp", "result", "data", "item"]
        rng.shuffle(vars_to_rename)
        for i, var in enumerate(vars_to_rename):
            if i % 2 == 0 and i + 1 < len(vars_to_rename):
                lines = [l.replace(var, f"{var}_variant") for l in lines]

        return "\n".join(lines)

    def compute_checksum(self, benchmark: ResearchBenchmark) -> str:
        data = f"{benchmark.name}:{benchmark.description}:{benchmark.difficulty}:{benchmark.version}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def verify_integrity(self, benchmark: ResearchBenchmark) -> bool:
        return self.compute_checksum(benchmark) == benchmark.anti_gaming_hash


class ScoringSystem:
    def __init__(self):
        self._weights = {
            "correctness": 0.3,
            "completeness": 0.2,
            "efficiency": 0.15,
            "maintainability": 0.15,
            "adaptability": 0.1,
            "uncertainty_calibration": 0.1,
        }

    def score(self, result: Dict[str, Any], criteria: Dict[str, float]) -> Dict[str, Any]:
        dimension_scores = {}
        total_weight = 0
        weighted_sum = 0

        for criterion, weight in criteria.items():
            raw = result.get(criterion, 0)
            score = min(1.0, max(0.0, raw))
            dimension_scores[criterion] = {
                "raw": raw,
                "normalized": score,
                "weight": weight,
                "weighted": score * weight,
            }
            weighted_sum += score * weight
            total_weight += weight

        overall = weighted_sum / max(total_weight, 1)

        calibrated = self._calibrate_for_difficulty(overall, result.get("benchmark_difficulty", 0.5))

        return {
            "overall": overall,
            "calibrated": calibrated,
            "dimension_scores": dimension_scores,
            "total_weight": total_weight,
        }

    def _calibrate_for_difficulty(self, score: float, difficulty: float) -> float:
        return min(1.0, score * (1.0 + difficulty * 0.5))

    def normalize_across_agents(self, scores: List[float]) -> List[float]:
        if not scores:
            return []
        mean = sum(scores) / len(scores)
        std = math.sqrt(sum((s - mean) ** 2 for s in scores) / len(scores)) if len(scores) > 1 else 1
        return [(s - mean) / max(std, 0.001) * 10 + 50 for s in scores]


class BenchmarkGenerator:
    def __init__(self):
        self.benchmarks: List[ResearchBenchmark] = []

    def generate_abstraction_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Abstraction Formation ({difficulty:.1f})",
            category=BenchmarkCategory.ABSTRACTION,
            description="Given scattered implementations of the same logical pattern, identify the common abstraction",
            difficulty=difficulty,
            steps=max(1, int(difficulty * 5)),
            hidden_coupling=difficulty > 0.5,
            scoring_criteria={"correctness": 0.4, "completeness": 0.3, "efficiency": 0.3},
        )

    def generate_causal_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Causal Reasoning ({difficulty:.1f})",
            category=BenchmarkCategory.CAUSAL,
            description="Given a change to component X, predict downstream breakage in Y and Z",
            difficulty=difficulty,
            steps=3,
            hidden_coupling=True,
            scoring_criteria={"prediction_accuracy": 0.5, "propagation_depth": 0.3, "false_positives": 0.2},
        )

    def generate_invariant_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Invariant Preservation ({difficulty:.1f})",
            category=BenchmarkCategory.INVARIANT,
            description="Discover and maintain architectural invariants across modifications",
            difficulty=difficulty,
            steps=max(2, int(difficulty * 6)),
            hidden_coupling=True,
            scoring_criteria={"discovery_rate": 0.3, "violation_detection": 0.3, "repair_quality": 0.4},
        )

    def generate_repair_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Repair Ability ({difficulty:.1f})",
            category=BenchmarkCategory.REPAIR,
            description="Diagnose and fix subtle defects while avoiding regressions",
            difficulty=difficulty,
            steps=2,
            temporal_drift=True,
            scoring_criteria={"fix_correctness": 0.4, "minimality": 0.3, "no_regressions": 0.3},
        )

    def generate_temporal_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Temporal Reasoning ({difficulty:.1f})",
            category=BenchmarkCategory.TEMPORAL,
            description="Analyze repository history to predict next evolution steps",
            difficulty=difficulty,
            steps=3,
            temporal_drift=True,
            scoring_criteria={"prediction_accuracy": 0.4, "trend_identification": 0.3, "timing": 0.3},
        )

    def generate_coordination_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Coordination Efficiency ({difficulty:.1f})",
            category=BenchmarkCategory.COORDINATION,
            description="Coordinate with other agents to solve a task with minimal communication overhead",
            difficulty=difficulty,
            steps=max(2, int(difficulty * 8)),
            hidden_coupling=difficulty > 0.4,
            scoring_criteria={"task_completion": 0.3, "communication_efficiency": 0.3, "conflict_avoidance": 0.4},
        )

    def generate_memory_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Memory Compression ({difficulty:.1f})",
            category=BenchmarkCategory.MEMORY,
            description="Effectively compress and retrieve codebase knowledge within fixed context",
            difficulty=difficulty,
            steps=1,
            scoring_criteria={"compression_ratio": 0.2, "retrieval_precision": 0.4, "information_preservation": 0.4},
        )

    def generate_intent_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Intent Modeling ({difficulty:.1f})",
            category=BenchmarkCategory.INTENT,
            description="Infer purpose, tradeoffs, and design rationale from unfamiliar code",
            difficulty=difficulty,
            steps=2,
            ambiguous_goals=difficulty > 0.6,
            scoring_criteria={"purpose_accuracy": 0.3, "tradeoff_identification": 0.3, "rationale_reconstruction": 0.4},
        )

    def generate_uncertainty_benchmark(self, difficulty: float = 0.5) -> ResearchBenchmark:
        return ResearchBenchmark(
            name=f"Uncertainty Calibration ({difficulty:.1f})",
            category=BenchmarkCategory.UNCERTAINTY,
            description="Produce calibrated confidence estimates for code understanding tasks",
            difficulty=difficulty,
            steps=1,
            ambiguous_goals=True,
            scoring_criteria={"calibration_error": 0.5, "appropriate_deferral": 0.3, "knowledge_boundaries": 0.2},
        )

    def generate_suite(self, count: int = 10) -> List[ResearchBenchmark]:
        generators = [
            self.generate_abstraction_benchmark,
            self.generate_causal_benchmark,
            self.generate_invariant_benchmark,
            self.generate_repair_benchmark,
            self.generate_temporal_benchmark,
            self.generate_coordination_benchmark,
            self.generate_memory_benchmark,
            self.generate_intent_benchmark,
            self.generate_uncertainty_benchmark,
        ]

        suite = []
        for i in range(count):
            gen = generators[i % len(generators)]
            difficulty = 0.3 + (i / count) * 0.6
            bm = gen(difficulty)
            self.benchmarks.append(bm)
            suite.append(bm)

        return suite

    def run_evaluation(self, benchmark_id: str, agent_results: Dict[str, Any]) -> Dict[str, Any]:
        bm = next((b for b in self.benchmarks if b.id == benchmark_id), None)
        if not bm:
            return {"error": "benchmark not found"}

        scorer = ScoringSystem()
        score_result = scorer.score(agent_results, bm.scoring_criteria)

        return {
            "benchmark": bm.to_dict(),
            "scores": score_result,
            "anti_gaming": {"hash": AntiGamingProtection().compute_checksum(bm)},
        }
