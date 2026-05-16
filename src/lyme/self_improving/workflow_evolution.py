from __future__ import annotations

import math
import random
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class StepType(str, Enum):
    READ = "read"
    SEARCH = "search"
    EDIT = "edit"
    WRITE = "write"
    VERIFY = "verify"
    REASON = "reason"
    PLAN = "plan"
    DEBUG = "debug"
    TEST = "test"
    LINT = "lint"
    BUILD = "build"


@dataclass
class WorkflowStep:
    step_type: StepType = StepType.REASON
    target: str = ""
    context_size: int = 0
    duration_ms: float = 0.0
    success: bool = True
    output_size: int = 0
    depth: int = 0
    tool_name: str = ""
    is_verification: bool = False

    def to_dict(self) -> dict:
        return {
            "step_type": self.step_type.value,
            "target": self.target[:50],
            "context_size": self.context_size,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "depth": self.depth,
            "is_verification": self.is_verification,
        }


@dataclass
class WorkflowSequence:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    steps: List[WorkflowStep] = field(default_factory=list)
    fitness: float = 0.0
    compression_ratio: float = 1.0
    total_duration_ms: float = 0.0
    total_context_read: int = 0
    success_rate: float = 0.0
    repo_specific: bool = False
    repo_path: str = ""
    created_at: float = field(default_factory=time.time)
    parent_id: Optional[str] = None

    def add_step(self, step: WorkflowStep):
        self.steps.append(step)
        self.total_duration_ms += step.duration_ms
        self.total_context_read += step.context_size

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "step_count": len(self.steps),
            "fitness": self.fitness,
            "compression_ratio": self.compression_ratio,
            "total_duration_ms": self.total_duration_ms,
            "success_rate": self.success_rate,
            "repo_specific": self.repo_specific,
            "steps": [s.to_dict() for s in self.steps[:20]],
            "parent_id": self.parent_id,
        }


@dataclass
class WorkflowTemplate:
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    name: str = ""
    description: str = ""
    pattern: List[StepType] = field(default_factory=list)
    frequency: int = 1
    avg_fitness: float = 0.0
    avg_duration_ms: float = 0.0
    is_compressed: bool = False

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "pattern": [s.value for s in self.pattern],
            "frequency": self.frequency,
            "avg_fitness": self.avg_fitness,
            "is_compressed": self.is_compressed,
        }


@dataclass
class CompressionResult:
    original_step_count: int = 0
    compressed_step_count: int = 0
    compression_ratio: float = 1.0
    removed_redundancies: int = 0
    merged_sequences: int = 0
    reordered_steps: int = 0
    fitness_impact: float = 0.0

    def to_dict(self) -> dict:
        return {
            "original_step_count": self.original_step_count,
            "compressed_step_count": self.compressed_step_count,
            "compression_ratio": self.compression_ratio,
            "removed_redundancies": self.removed_redundancies,
            "merged_sequences": self.merged_sequences,
            "fitness_impact": self.fitness_impact,
        }


class MutationOperator:
    REMOVE_STEP = "remove_step"
    REORDER_STEPS = "reorder_steps"
    MERGE_READS = "merge_reads"
    ADD_VERIFICATION = "add_verification"
    MOVE_VERIFICATION_EARLIER = "move_verification_earlier"
    COMPRESS_CONTEXT = "compress_context"
    SPLIT_STEP = "split_step"
    PARALLELIZE = "parallelize"


@dataclass
class BenchmarkResult:
    sequence_id: str = ""
    fitness: float = 0.0
    success: bool = False
    duration_ms: float = 0.0
    context_saved: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "sequence_id": self.sequence_id,
            "fitness": self.fitness,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "context_saved": self.context_saved,
        }


class FitnessScorer:
    def score(self, sequence: WorkflowSequence, baseline_duration: float = 0.0,
              baseline_context: int = 0) -> float:
        if not sequence.steps:
            return 0.0

        duration_score = 0.0
        if baseline_duration > 0:
            duration_ratio = baseline_duration / max(sequence.total_duration_ms, 1)
            duration_score = min(1.0, duration_ratio * 0.5)

        context_score = 0.0
        if baseline_context > 0:
            context_ratio = baseline_context / max(sequence.total_context_read, 1)
            context_score = min(1.0, context_ratio * 0.5)

        verification_steps = sum(1 for s in sequence.steps if s.is_verification)
        verification_ratio = verification_steps / max(len(sequence.steps), 1)
        verification_score = min(1.0, verification_ratio * 3.0)

        success_score = sequence.success_rate
        compression_bonus = min(0.2, sequence.compression_ratio * 0.1)

        fitness = (
            duration_score * 0.25 +
            context_score * 0.25 +
            verification_score * 0.15 +
            success_score * 0.25 +
            compression_bonus * 0.1
        )

        return min(1.0, max(0.0, fitness))


class BenchmarkHarness:
    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def run(self, sequence: WorkflowSequence, test_func: Optional[Callable] = None) -> BenchmarkResult:
        success = True
        errors = []

        for step in sequence.steps:
            step_success = random.random() < 0.85
            if not step_success:
                success = False
                errors.append(f"Step {step.step_type.value} failed")

        fitness = FitnessScorer().score(sequence)
        context_saved = int(sequence.total_context_read * sequence.compression_ratio)

        result = BenchmarkResult(
            sequence_id=sequence.id,
            fitness=fitness,
            success=success,
            duration_ms=sequence.total_duration_ms,
            context_saved=context_saved,
            errors=errors,
        )
        self.results.append(result)
        return result

    def compare(self, baseline: WorkflowSequence, mutated: WorkflowSequence) -> Dict[str, Any]:
        baseline_result = self.run(baseline)
        mutated_result = self.run(mutated)

        improvement = mutated_result.fitness - baseline_result.fitness
        return {
            "improvement": improvement,
            "improvement_pct": (improvement / max(baseline_result.fitness, 0.01)) * 100,
            "baseline_fitness": baseline_result.fitness,
            "mutated_fitness": mutated_result.fitness,
            "baseline_duration": baseline_result.duration_ms,
            "mutated_duration": mutated_result.duration_ms,
        }


class WorkflowEvolutionEngine:
    def __init__(self):
        self._sequences: Dict[str, WorkflowSequence] = {}
        self._templates: Dict[str, WorkflowTemplate] = {}
        self._generation = 0
        self._fitness_history: List[float] = []
        self._fitness_scorer = FitnessScorer()
        self._harness = BenchmarkHarness()
        self._mutation_rate = 0.3

    def observe_workflow(self, steps: List[Dict[str, Any]]) -> WorkflowSequence:
        sequence = WorkflowSequence()
        for s in steps:
            step = WorkflowStep(
                step_type=StepType(s.get("type", "reason")),
                target=s.get("target", ""),
                context_size=s.get("context_size", 0),
                duration_ms=s.get("duration_ms", 0),
                success=s.get("success", True),
                depth=s.get("depth", 0),
                tool_name=s.get("tool", ""),
                is_verification=s.get("is_verification", False),
            )
            sequence.add_step(step)

        fitness = self._fitness_scorer.score(sequence)
        sequence.fitness = fitness
        self._sequences[sequence.id] = sequence
        return sequence

    def compress_workflow(self, sequence_id: str) -> Optional[CompressionResult]:
        sequence = self._sequences.get(sequence_id)
        if not sequence or len(sequence.steps) < 2:
            return None

        original_count = len(sequence.steps)
        removed = 0
        merged = 0
        reordered = 0

        compressed = []
        i = 0
        while i < len(sequence.steps):
            if i + 1 < len(sequence.steps):
                s1 = sequence.steps[i]
                s2 = sequence.steps[i + 1]

                if s1.step_type == StepType.READ and s2.step_type == StepType.READ:
                    merged_step = WorkflowStep(
                        step_type=StepType.READ,
                        target=f"{s1.target}, {s2.target}",
                        context_size=s1.context_size + s2.context_size,
                        duration_ms=s1.duration_ms + s2.duration_ms - min(s1.duration_ms, s2.duration_ms) * 0.2,
                        is_verification=False,
                    )
                    compressed.append(merged_step)
                    merged += 1
                    removed += 1
                    i += 2
                    continue

                if s1.step_type == StepType.SEARCH and s2.step_type == StepType.SEARCH:
                    merged_step = WorkflowStep(
                        step_type=StepType.SEARCH,
                        target=f"{s1.target} | {s2.target}",
                        context_size=max(s1.context_size, s2.context_size),
                        duration_ms=s1.duration_ms + s2.duration_ms * 0.5,
                        is_verification=False,
                    )
                    compressed.append(merged_step)
                    merged += 1
                    removed += 1
                    i += 2
                    continue

                if s1.step_type == StepType.VERIFY and s2.step_type == StepType.VERIFY:
                    removed += 1
                    i += 2
                    continue

            compressed.append(sequence.steps[i])
            i += 1

        reordered = self._reorder_for_efficiency(compressed)

        sequence.steps = compressed
        ratio = len(compressed) / max(original_count, 1)

        old_fitness = sequence.fitness
        sequence.fitness = self._fitness_scorer.score(sequence)
        sequence.compression_ratio = ratio

        result = CompressionResult(
            original_step_count=original_count,
            compressed_step_count=len(compressed),
            compression_ratio=ratio,
            removed_redundancies=removed,
            merged_sequences=merged,
            reordered_steps=reordered,
            fitness_impact=sequence.fitness - old_fitness,
        )

        self._detect_template(sequence)
        return result

    def _reorder_for_efficiency(self, steps: List[WorkflowStep]) -> int:
        reorders = 0
        for i in range(len(steps) - 1):
            if steps[i].step_type == StepType.WRITE and steps[i + 1].step_type == StepType.VERIFY:
                continue
            if steps[i].step_type == StepType.READ and steps[i + 1].step_type == StepType.READ:
                continue
            if steps[i].step_type == StepType.VERIFY and not steps[i + 1].is_verification:
                if steps[i + 1].step_type == StepType.EDIT:
                    steps[i], steps[i + 1] = steps[i + 1], steps[i]
                    reorders += 1
        return reorders

    def mutate(self, sequence_id: str) -> Optional[WorkflowSequence]:
        sequence = self._sequences.get(sequence_id)
        if not sequence or len(sequence.steps) < 2:
            return None

        mutated = WorkflowSequence(
            repo_path=sequence.repo_path,
            repo_specific=sequence.repo_specific,
            parent_id=sequence.id,
        )
        mutated.steps = [WorkflowStep(**s.__dict__) for s in sequence.steps]

        mutations = random.choices(
            list(MutationOperator.__dict__.values()),
            k=random.randint(1, 3),
        )
        mutations = [m for m in mutations if isinstance(m, str) and not m.startswith("_")][:3]

        for mutation in mutations:
            if mutation == MutationOperator.REMOVE_STEP and len(mutated.steps) > 3:
                remove_idx = random.randint(1, len(mutated.steps) - 2)
                if not mutated.steps[remove_idx].is_verification:
                    mutated.steps.pop(remove_idx)

            elif mutation == MutationOperator.REORDER_STEPS and len(mutated.steps) >= 3:
                i, j = random.sample(range(len(mutated.steps)), 2)
                mutated.steps[i], mutated.steps[j] = mutated.steps[j], mutated.steps[i]

            elif mutation == MutationOperator.MERGE_READS and len(mutated.steps) >= 2:
                for i in range(len(mutated.steps) - 1):
                    if (mutated.steps[i].step_type == StepType.READ and
                            mutated.steps[i + 1].step_type == StepType.READ):
                        mutated.steps[i].target += f", {mutated.steps[i + 1].target}"
                        mutated.steps[i].context_size += mutated.steps[i + 1].context_size
                        mutated.steps.pop(i + 1)
                        break

            elif mutation == MutationOperator.ADD_VERIFICATION:
                verify_step = WorkflowStep(
                    step_type=StepType.VERIFY,
                    is_verification=True,
                )
                mutated.steps.append(verify_step)

            elif mutation == MutationOperator.COMPRESS_CONTEXT:
                for s in mutated.steps:
                    if s.context_size > 1000:
                        s.context_size = int(s.context_size * 0.7)

        mutated.fitness = self._fitness_scorer.score(mutated)
        self._sequences[mutated.id] = mutated
        return mutated

    def evolve(self, sequence_id: str, generations: int = 5) -> List[WorkflowSequence]:
        self._generation = 0
        history = []

        current = self._sequences.get(sequence_id)
        if not current:
            return history

        baseline_bench = self._harness.run(current)

        for gen in range(generations):
            self._generation += 1
            offspring = self.mutate(current.id)

            if not offspring:
                continue

            offspring_bench = self._harness.run(offspring)

            if offspring_bench.fitness > baseline_bench.fitness * 0.9:
                current = offspring
                history.append(offspring)

            self._fitness_history.append(offspring.fitness)

        return history

    def learn_repo_strategies(self, repo_path: str, sequences: List[WorkflowSequence]):
        repo_sequences = [s for s in sequences if s.repo_path == repo_path]
        if not repo_sequences:
            return

        for seq in repo_sequences:
            seq.repo_specific = True

            read_ratio = sum(1 for s in seq.steps if s.step_type == StepType.READ) / max(len(seq.steps), 1)
            verify_ratio = sum(1 for s in seq.steps if s.is_verification) / max(len(seq.steps), 1)

            if read_ratio > 0.4:
                self._mutation_rate = 0.2
            if verify_ratio < 0.1:
                for seq2 in repo_sequences:
                    v_step = WorkflowStep(step_type=StepType.VERIFY, is_verification=True)
                    seq2.steps.append(v_step)

    def _detect_template(self, sequence: WorkflowSequence):
        if len(sequence.steps) < 2:
            return

        pattern = [s.step_type for s in sequence.steps[:10]]
        pattern_key = "->".join(p.value for p in pattern)

        for template in self._templates.values():
            existing_key = "->".join(p.value for p in template.pattern)
            if existing_key == pattern_key:
                template.frequency += 1
                template.avg_fitness = (template.avg_fitness * (template.frequency - 1) + sequence.fitness) / template.frequency
                return

        template = WorkflowTemplate(
            name=f"template_{len(self._templates)}",
            description=f"Pattern: {pattern_key[:100]}",
            pattern=pattern,
            frequency=1,
            avg_fitness=sequence.fitness,
        )
        self._templates[template.template_id] = template

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "generation": self._generation,
            "sequences_tracked": len(self._sequences),
            "templates_discovered": len(self._templates),
            "avg_fitness": (
                sum(s.fitness for s in self._sequences.values()) / max(len(self._sequences), 1)
            ),
            "best_fitness": max((s.fitness for s in self._sequences.values()), default=0.0),
            "fitness_history": self._fitness_history[-20:],
            "mutation_rate": self._mutation_rate,
        }
