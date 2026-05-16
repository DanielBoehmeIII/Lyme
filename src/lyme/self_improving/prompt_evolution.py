from __future__ import annotations

import math
import random
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PromptSegment(str, Enum):
    ROLE = "role"
    TASK = "task"
    CONTEXT = "context"
    INSTRUCTION = "instruction"
    CONSTRAINT = "constraint"
    OUTPUT_FORMAT = "output_format"
    REASONING = "reasoning"
    VERIFICATION = "verification"
    EXAMPLE = "example"


@dataclass
class PromptVariant:
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    segments: Dict[PromptSegment, str] = field(default_factory=dict)
    parent_id: Optional[str] = None
    generation: int = 0
    fitness: float = 0.0
    stability: float = 0.0
    interpretability: float = 1.0
    safety_score: float = 1.0
    mutation_history: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def full_text(self) -> str:
        parts = []
        for segment in PromptSegment:
            if segment in self.segments:
                parts.append(self.segments[segment])
        return "\n\n".join(parts)

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "segments": {k.value: v[:100] for k, v in self.segments.items()},
            "generation": self.generation,
            "fitness": self.fitness,
            "stability": self.stability,
            "interpretability": self.interpretability,
            "safety_score": self.safety_score,
            "mutation_history": self.mutation_history[-5:],
        }


@dataclass
class PromptGenome:
    genome_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    variants: List[PromptVariant] = field(default_factory=list)
    best_fitness: float = 0.0
    best_variant_id: Optional[str] = None
    generation: int = 0
    diversity: float = 0.0
    convergence_score: float = 0.0

    def add_variant(self, variant: PromptVariant):
        self.variants.append(variant)
        if variant.fitness > self.best_fitness:
            self.best_fitness = variant.fitness
            self.best_variant_id = variant.variant_id
        self._update_diversity()

    def _update_diversity(self):
        if len(self.variants) < 2:
            self.diversity = 1.0
            return

        fitnesses = [v.fitness for v in self.variants[-20:]]
        if len(fitnesses) >= 2:
            mean_f = sum(fitnesses) / len(fitnesses)
            variance = sum((f - mean_f) ** 2 for f in fitnesses) / len(fitnesses)
            self.diversity = min(1.0, math.sqrt(variance) * 5)

    def to_dict(self) -> dict:
        return {
            "genome_id": self.genome_id,
            "variant_count": len(self.variants),
            "best_fitness": self.best_fitness,
            "generation": self.generation,
            "diversity": self.diversity,
            "convergence_score": self.convergence_score,
            "best_variant": next(
                (v.to_dict() for v in self.variants if v.variant_id == self.best_variant_id),
                None,
            ),
        }


class PromptMutation:
    SUBSTITUTE_SEGMENT = "substitute_segment"
    REORDER_SEGMENTS = "reorder_segments"
    SPLIT_SEGMENT = "split_segment"
    MERGE_SEGMENTS = "merge_segments"
    ADD_CONSTRAINT = "add_constraint"
    REMOVE_CONSTRAINT = "remove_constraint"
    TONE_SHIFT = "tone_shift"
    SHORTEN = "shorten"
    LENGTHEN = "lengthen"
    ADD_EXAMPLE = "add_example"


class SafetyConstraint:
    def __init__(self):
        self._forbidden_patterns = [
            "ignore previous instructions",
            "bypass safety",
            "do anything",
            "no restrictions",
            "override",
        ]
        self._required_patterns = [
            "verify",
            "check",
            "ensure",
        ]
        self._max_length = 4000
        self._min_length = 50

    def check(self, variant: PromptVariant) -> Tuple[bool, List[str]]:
        violations = []
        full_text = variant.full_text().lower()

        for pattern in self._forbidden_patterns:
            if pattern in full_text:
                violations.append(f"Forbidden pattern: '{pattern}'")

        if len(full_text) > self._max_length:
            violations.append(f"Prompt too long: {len(full_text)} > {self._max_length}")

        if len(full_text) < self._min_length:
            violations.append(f"Prompt too short: {len(full_text)} < {self._min_length}")

        for segment in variant.segments:
            if len(variant.segments[segment]) > 500:
                violations.append(f"Segment {segment.value} too long")

        return len(violations) == 0, violations


class ConvergenceAnalyzer:
    def analyze(self, genome: PromptGenome) -> Dict[str, Any]:
        if len(genome.variants) < 5:
            return {"status": "insufficient_data", "converged": False}

        recent = genome.variants[-10:]
        fitnesses = [v.fitness for v in recent]
        mean_f = sum(fitnesses) / len(fitnesses)
        variance = sum((f - mean_f) ** 2 for f in fitnesses) / len(fitnesses)
        std = math.sqrt(variance)

        plateau = std < 0.05 and len(fitnesses) >= 5

        segments = Counter()
        for v in recent:
            for seg in v.segments:
                segments[seg.value] += 1

        stable_segments = {seg: count for seg, count in segments.items()
                           if count >= len(recent) * 0.8}

        return {
            "converged": plateau,
            "fitness_std": std,
            "fitness_plateau": plateau,
            "stable_segments": stable_segments,
            "diversity": genome.diversity,
            "recommendation": "converged" if plateau else "continue_evolution",
        }


class PromptEvaluator:
    def evaluate(self, variant: PromptVariant) -> float:
        score = 0.5

        segments_present = len(variant.segments)
        if segments_present >= 4:
            score += 0.1
        if PromptSegment.ROLE in variant.segments:
            score += 0.1
        if PromptSegment.VERIFICATION in variant.segments:
            score += 0.1
        if PromptSegment.CONSTRAINT in variant.segments:
            score += 0.1

        full_text = variant.full_text()
        words = full_text.split()
        if 50 <= len(words) <= 200:
            score += 0.1

        specific_terms = ["specifically", "exactly", "precisely",
                           "step", "first", "then", "finally"]
        if any(term in full_text.lower() for term in specific_terms):
            score += 0.1

        question_ratio = full_text.count("?") / max(len(words), 1)
        if 0.001 < question_ratio < 0.02:
            score += 0.05

        reasoning_depth = PromptSegment.REASONING in variant.segments
        if reasoning_depth:
            reasoning_text = variant.segments[PromptSegment.REASONING]
            if len(reasoning_text.split()) > 30:
                score += 0.05

        return min(1.0, score)


class PromptEvolutionEngine:
    def __init__(self):
        self.genome = PromptGenome()
        self.evaluator = PromptEvaluator()
        self.safety = SafetyConstraint()
        self.convergence = ConvergenceAnalyzer()
        self._mutation_rate = 0.4

        self._segment_variants = {
            PromptSegment.ROLE: [
                "You are an expert software engineer.",
                "You are a senior developer focused on code quality.",
                "You are a principal architect reviewing a codebase.",
                "You are a skilled programmer with deep systems knowledge.",
                "You are a technical lead responsible for this repository.",
            ],
            PromptSegment.REASONING: [
                "Think step by step about the problem before coding.",
                "Analyze the requirements carefully and consider edge cases.",
                "Consider multiple approaches and select the most appropriate one.",
                "Break down the problem into smaller sub-problems and solve each.",
                "Use first-principles reasoning to understand the core issue.",
            ],
            PromptSegment.VERIFICATION: [
                "Verify your solution by checking against all requirements.",
                "Double-check your work for correctness and completeness.",
                "Review the code for potential bugs and edge cases.",
                "Ensure the solution is robust and handles error conditions.",
                "Validate the implementation meets the specified criteria.",
            ],
            PromptSegment.CONSTRAINT: [
                "Do not introduce unnecessary dependencies.",
                "Follow existing code patterns and conventions.",
                "Maintain backward compatibility where possible.",
                "Keep changes minimal and focused on the task.",
                "Preserve existing functionality when making changes.",
            ],
        }

    def seed(self):
        base = PromptVariant(generation=0)
        base.segments = {
            PromptSegment.ROLE: "You are an expert software engineer.",
            PromptSegment.TASK: "Complete the following task accurately and efficiently.",
            PromptSegment.REASONING: "Think step by step about the problem.",
            PromptSegment.VERIFICATION: "Verify your solution before finalizing.",
            PromptSegment.CONSTRAINT: "Follow existing code conventions.",
        }
        base.fitness = self.evaluator.evaluate(base)
        self.genome.add_variant(base)

    def mutate(self, variant_id: str) -> Optional[PromptVariant]:
        parent = next(
            (v for v in self.genome.variants if v.variant_id == variant_id),
            None,
        )
        if not parent:
            return None

        child = PromptVariant(
            parent_id=parent.variant_id,
            generation=parent.generation + 1,
            segments=dict(parent.segments),
            mutation_history=list(parent.mutation_history),
        )

        mutations = random.choices(
            [
                PromptMutation.SUBSTITUTE_SEGMENT,
                PromptMutation.REORDER_SEGMENTS,
                PromptMutation.SPLIT_SEGMENT,
                PromptMutation.ADD_CONSTRAINT,
                PromptMutation.REMOVE_CONSTRAINT,
                PromptMutation.TONE_SHIFT,
                PromptMutation.SHORTEN,
                PromptMutation.LENGTHEN,
            ],
            k=random.randint(1, 3),
        )

        for mutation in set(mutations):
            if mutation == PromptMutation.SUBSTITUTE_SEGMENT:
                seg = random.choice(list(PromptSegment))
                if seg in self._segment_variants:
                    old = child.segments.get(seg, "")
                    child.segments[seg] = random.choice(self._segment_variants[seg])
                    child.mutation_history.append(f"substituted {seg.value}")

            elif mutation == PromptMutation.REORDER_SEGMENTS:
                segs = list(child.segments.keys())
                if len(segs) >= 3:
                    i, j = random.sample(range(len(segs)), 2)
                    segs[i], segs[j] = segs[j], segs[i]
                    child.segments = {s: child.segments[s] for s in segs}
                    child.mutation_history.append("reordered segments")

            elif mutation == PromptMutation.ADD_CONSTRAINT:
                if PromptSegment.CONSTRAINT in self._segment_variants:
                    constraint = random.choice(self._segment_variants[PromptSegment.CONSTRAINT])
                    current = child.segments.get(PromptSegment.CONSTRAINT, "")
                    if current:
                        child.segments[PromptSegment.CONSTRAINT] = current + " " + constraint
                    else:
                        child.segments[PromptSegment.CONSTRAINT] = constraint
                    child.mutation_history.append("added constraint")

            elif mutation == PromptMutation.REMOVE_CONSTRAINT:
                if PromptSegment.CONSTRAINT in child.segments:
                    del child.segments[PromptSegment.CONSTRAINT]
                    child.mutation_history.append("removed constraint")

            elif mutation == PromptMutation.TONE_SHIFT:
                for seg in list(child.segments.keys()):
                    text = child.segments[seg]
                    if "must" in text:
                        text = text.replace("must", "should")
                    elif "should" in text:
                        text = text.replace("should", "must")
                    child.segments[seg] = text
                child.mutation_history.append("tone shift")

            elif mutation == PromptMutation.SHORTEN:
                for seg in list(child.segments.keys()):
                    words = child.segments[seg].split()
                    if len(words) > 10:
                        child.segments[seg] = " ".join(words[:len(words) // 2])
                child.mutation_history.append("shortened")

            elif mutation == PromptMutation.LENGTHEN:
                for seg in list(child.segments.keys()):
                    words = child.segments[seg].split()
                    if len(words) < 20:
                        child.segments[seg] += " Take your time to ensure correctness."
                child.mutation_history.append("lengthened")

        child.fitness = self.evaluator.evaluate(child)

        safe, violations = self.safety.check(child)
        if not safe:
            child.safety_score = max(0.0, child.safety_score - len(violations) * 0.2)
            if child.safety_score < 0.3:
                return None

        if child.fitness > parent.fitness * 0.8:
            self.genome.add_variant(child)

        return child

    def evolve(self, generations: int = 10) -> PromptGenome:
        if not self.genome.variants:
            self.seed()

        for gen in range(generations):
            self.genome.generation += 1

            if self.genome.best_variant_id:
                for _ in range(3):
                    self.mutate(self.genome.best_variant_id)

            for variant in random.sample(
                self.genome.variants[-10:],
                min(3, len(self.genome.variants)),
            ):
                self.mutate(variant.variant_id)

        convergence = self.convergence.analyze(self.genome)
        self.genome.convergence_score = convergence.get("fitness_std", 1.0)

        return self.genome

    def evaluate_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        variant = next(
            (v for v in self.genome.variants if v.variant_id == variant_id),
            None,
        )
        if not variant:
            return None

        return {
            "variant_id": variant.variant_id,
            "full_text": variant.full_text(),
            "fitness": variant.fitness,
            "stability": variant.stability,
            "safety": variant.safety_score,
            "segments": {k.value: v[:150] for k, v in variant.segments.items()},
        }

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "variants": len(self.genome.variants),
            "generation": self.genome.generation,
            "best_fitness": self.genome.best_fitness,
            "diversity": self.genome.diversity,
            "convergence": self.genome.convergence_score,
        }
