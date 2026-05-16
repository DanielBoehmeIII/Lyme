from __future__ import annotations

import itertools
import math
import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ArchitectureDimension(str, Enum):
    MEMORY_STRUCTURE = "memory_structure"
    RETRIEVAL_STRATEGY = "retrieval_strategy"
    PLANNING_DEPTH = "planning_depth"
    TOOL_ROUTING = "tool_routing"
    DEBATE_STRUCTURE = "debate_structure"
    VERIFICATION_TIMING = "verification_timing"
    COORDINATION_TOPOLOGY = "coordination_topology"
    COMPRESSION_LAYERS = "compression_layers"


@dataclass
class ArchitectureVariant:
    variant_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    dimensions: Dict[ArchitectureDimension, str] = field(default_factory=dict)
    fitness: float = 0.0
    complexity_score: float = 0.0
    memory_usage: float = 0.0
    latency_ms: float = 0.0
    parent_id: Optional[str] = None
    generation: int = 0
    evaluated: bool = False
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "dimensions": {k.value: v for k, v in self.dimensions.items()},
            "fitness": self.fitness,
            "complexity": self.complexity_score,
            "memory_usage": self.memory_usage,
            "latency_ms": self.latency_ms,
            "generation": self.generation,
            "evaluated": self.evaluated,
        }


@dataclass
class ArchitectureBenchmark:
    variant_id: str = ""
    task_completion: float = 0.0
    code_accuracy: float = 0.0
    hallucination_rate: float = 0.0
    context_efficiency: float = 0.0
    edit_success: float = 0.0
    coordination_overhead: float = 0.0
    total_duration_ms: float = 0.0
    composite_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "variant_id": self.variant_id,
            "task_completion": self.task_completion,
            "code_accuracy": self.code_accuracy,
            "hallucination_rate": self.hallucination_rate,
            "context_efficiency": self.context_efficiency,
            "edit_success": self.edit_success,
            "composite_score": self.composite_score,
        }


@dataclass
class SearchResult:
    best_variant: Optional[ArchitectureVariant] = None
    best_benchmark: Optional[ArchitectureBenchmark] = None
    all_variants: List[ArchitectureVariant] = field(default_factory=list)
    all_benchmarks: List[ArchitectureBenchmark] = field(default_factory=list)
    search_space_size: int = 0
    explored_count: int = 0
    top_k: List[Dict[str, Any]] = field(default_factory=list)
    dimension_importance: Dict[str, float] = field(default_factory=dict)
    convergence_history: List[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "search_space_size": self.search_space_size,
            "explored_count": self.explored_count,
            "best_fitness": self.best_benchmark.composite_score if self.best_benchmark else 0,
            "top_variants": self.top_k[:5],
            "dimension_importance": self.dimension_importance,
            "convergence": self.convergence_history[-20:],
        }


class CognitiveArchitectureSearch:
    def __init__(self):
        self._dimension_values: Dict[ArchitectureDimension, List[str]] = {
            ArchitectureDimension.MEMORY_STRUCTURE: [
                "short_term_only",
                "episodic_semantic",
                "hierarchical",
                "distributed",
                "compressed_history",
            ],
            ArchitectureDimension.RETRIEVAL_STRATEGY: [
                "exact_match",
                "semantic_search",
                "hybrid_retrieval",
                "context_window",
                "recency_weighted",
            ],
            ArchitectureDimension.PLANNING_DEPTH: [
                "reactive",
                "single_step",
                "multi_step_3",
                "multi_step_5",
                "tree_search",
            ],
            ArchitectureDimension.TOOL_ROUTING: [
                "direct_call",
                "orchestrated",
                "debate_based",
                "specialist_routing",
                "market_auction",
            ],
            ArchitectureDimension.DEBATE_STRUCTURE: [
                "single_agent",
                "pair_debate",
                "multi_critic",
                "adversarial",
                "consensus_committee",
            ],
            ArchitectureDimension.VERIFICATION_TIMING: [
                "no_verification",
                "post_hoc",
                "interleaved",
                "continuous",
                "adaptive",
            ],
            ArchitectureDimension.COORDINATION_TOPOLOGY: [
                "none",
                "star",
                "mesh",
                "hierarchical",
                "fully_connected",
            ],
            ArchitectureDimension.COMPRESSION_LAYERS: [
                "none",
                "summary_only",
                "selective",
                "automatic",
                "learned",
            ],
        }

        self._variants: Dict[str, ArchitectureVariant] = {}
        self._benchmarks: Dict[str, ArchitectureBenchmark] = {}
        self._generation = 0
        self._best_fitness = 0.0
        self._convergence_history: List[float] = []

    @property
    def search_space_size(self) -> int:
        total = 1
        for values in self._dimension_values.values():
            total *= len(values)
        return total

    def _random_variant(self) -> ArchitectureVariant:
        variant = ArchitectureVariant()
        for dim, values in self._dimension_values.items():
            variant.dimensions[dim] = random.choice(values)
        return variant

    def _mutate(self, variant: ArchitectureVariant) -> ArchitectureVariant:
        child = ArchitectureVariant(
            dimensions=dict(variant.dimensions),
            parent_id=variant.variant_id,
            generation=variant.generation + 1,
        )

        dims = list(child.dimensions.keys())
        num_mutations = random.randint(1, max(1, len(dims) // 3))

        for dim in random.sample(dims, min(num_mutations, len(dims))):
            current = child.dimensions[dim]
            alternatives = [v for v in self._dimension_values[dim] if v != current]
            if alternatives:
                child.dimensions[dim] = random.choice(alternatives)

        return child

    def _crossover(self, a: ArchitectureVariant, b: ArchitectureVariant) -> ArchitectureVariant:
        child = ArchitectureVariant()
        for dim in ArchitectureDimension:
            if dim in a.dimensions and dim in b.dimensions:
                child.dimensions[dim] = random.choice([a.dimensions[dim], b.dimensions[dim]])
            elif dim in a.dimensions:
                child.dimensions[dim] = a.dimensions[dim]
            elif dim in b.dimensions:
                child.dimensions[dim] = b.dimensions[dim]
        return child

    def _simulate_benchmark(self, variant: ArchitectureVariant) -> ArchitectureBenchmark:
        base_completion = 0.7
        base_accuracy = 0.75
        base_hallucination = 0.1

        mem = variant.dimensions.get(ArchitectureDimension.MEMORY_STRUCTURE, "")
        ret = variant.dimensions.get(ArchitectureDimension.RETRIEVAL_STRATEGY, "")
        plan = variant.dimensions.get(ArchitectureDimension.PLANNING_DEPTH, "")
        tool = variant.dimensions.get(ArchitectureDimension.TOOL_ROUTING, "")
        debate = variant.dimensions.get(ArchitectureDimension.DEBATE_STRUCTURE, "")
        verify = variant.dimensions.get(ArchitectureDimension.VERIFICATION_TIMING, "")
        coord = variant.dimensions.get(ArchitectureDimension.COORDINATION_TOPOLOGY, "")
        comp = variant.dimensions.get(ArchitectureDimension.COMPRESSION_LAYERS, "")

        completion = base_completion
        accuracy = base_accuracy
        hallucination = base_hallucination
        context_eff = 0.5
        edit_success = 0.7
        coord_overhead = 0.5

        if plan in ("multi_step_5", "tree_search"):
            completion += 0.1
            accuracy += 0.08
        if plan == "reactive":
            completion -= 0.1

        if ret == "semantic_search":
            accuracy += 0.05
        elif ret == "hybrid_retrieval":
            accuracy += 0.08
            completion += 0.05

        if verify == "continuous":
            accuracy += 0.1
            hallucination -= 0.04
        elif verify == "adaptive":
            accuracy += 0.06
            context_eff += 0.1

        if tool == "market_auction":
            coord_overhead += 0.3
            completion += 0.05
        elif tool == "specialist_routing":
            accuracy += 0.05
            coord_overhead += 0.1

        if debate == "multi_critic":
            accuracy += 0.07
            completion -= 0.05
        elif debate == "consensus_committee":
            accuracy += 0.1
            completion -= 0.1

        if comp in ("automatic", "learned"):
            context_eff += 0.15
            accuracy -= 0.02

        if coord == "fully_connected":
            coord_overhead += 0.4
        elif coord == "mesh":
            coord_overhead += 0.2
            accuracy += 0.03

        if mem == "hierarchical":
            context_eff += 0.1
        elif mem == "compressed_history":
            context_eff += 0.15
            accuracy -= 0.03

        completion = max(0, min(1, completion + random.uniform(-0.05, 0.05)))
        accuracy = max(0, min(1, accuracy + random.uniform(-0.05, 0.05)))
        hallucination = max(0, min(1, hallucination + random.uniform(-0.02, 0.02)))
        context_eff = max(0, min(1, context_eff + random.uniform(-0.05, 0.05)))
        edit_success = max(0, min(1, edit_success + random.uniform(-0.05, 0.05)))
        coord_overhead = max(0, min(1, coord_overhead + random.uniform(-0.05, 0.05)))

        composite = (
            completion * 0.20 +
            accuracy * 0.25 +
            (1 - hallucination) * 0.15 +
            context_eff * 0.15 +
            edit_success * 0.15 +
            (1 - coord_overhead) * 0.10
        )

        return ArchitectureBenchmark(
            variant_id=variant.variant_id,
            task_completion=completion,
            code_accuracy=accuracy,
            hallucination_rate=hallucination,
            context_efficiency=context_eff,
            edit_success=edit_success,
            coordination_overhead=coord_overhead,
            composite_score=composite,
        )

    def random_search(self, num_samples: int = 20) -> SearchResult:
        result = SearchResult(search_space_size=self.search_space_size)

        for _ in range(num_samples):
            variant = self._random_variant()
            benchmark = self._simulate_benchmark(variant)
            variant.fitness = benchmark.composite_score
            variant.evaluated = True

            self._variants[variant.variant_id] = variant
            self._benchmarks[variant.variant_id] = benchmark
            result.all_variants.append(variant)
            result.all_benchmarks.append(benchmark)

        result.explored_count = len(result.all_variants)
        result.best_variant = max(result.all_variants, key=lambda v: v.fitness)
        result.best_benchmark = self._benchmarks.get(result.best_variant.variant_id)

        scored = sorted(
            [(v, b.composite_score) for v, b in zip(result.all_variants, result.all_benchmarks)],
            key=lambda x: -x[1],
        )
        result.top_k = [
            {**v.to_dict(), "composite_score": s}
            for v, s in scored[:5]
        ]

        result.dimension_importance = self._compute_dimension_importance(result.all_variants, result.all_benchmarks)
        return result

    def evolutionary_search(self, population_size: int = 10, generations: int = 5) -> SearchResult:
        result = SearchResult(search_space_size=self.search_space_size)
        population: List[ArchitectureVariant] = []

        for _ in range(population_size):
            variant = self._random_variant()
            benchmark = self._simulate_benchmark(variant)
            variant.fitness = benchmark.composite_score
            variant.evaluated = True
            self._variants[variant.variant_id] = variant
            self._benchmarks[variant.variant_id] = benchmark
            population.append(variant)
            result.all_variants.append(variant)
            result.all_benchmarks.append(benchmark)

        for gen in range(generations):
            self._generation += 1
            population.sort(key=lambda v: -v.fitness)
            parents = population[:population_size // 2]

            offspring = []
            while len(offspring) + len(parents) < population_size:
                if random.random() < 0.7:
                    a, b = random.sample(parents, 2)
                    child = self._crossover(a, b)
                else:
                    child = self._mutate(random.choice(parents))

                child.generation = gen + 1
                benchmark = self._simulate_benchmark(child)
                child.fitness = benchmark.composite_score
                child.evaluated = True

                self._variants[child.variant_id] = child
                self._benchmarks[child.variant_id] = benchmark
                offspring.append(child)
                result.all_variants.append(child)
                result.all_benchmarks.append(benchmark)

            population = parents + offspring
            best_in_gen = max(population, key=lambda v: v.fitness).fitness
            self._convergence_history.append(best_in_gen)

        result.explored_count = len(result.all_variants)
        result.best_variant = max(result.all_variants, key=lambda v: v.fitness)
        result.best_benchmark = self._benchmarks.get(result.best_variant.variant_id)
        result.convergence_history = self._convergence_history

        scored = sorted(
            [(v, b.composite_score) for v, b in zip(result.all_variants, result.all_benchmarks)],
            key=lambda x: -x[1],
        )
        result.top_k = [
            {**v.to_dict(), "composite_score": s}
            for v, s in scored[:5]
        ]

        result.dimension_importance = self._compute_dimension_importance(result.all_variants, result.all_benchmarks)
        return result

    def _compute_dimension_importance(self, variants: List[ArchitectureVariant],
                                       benchmarks: List[ArchitectureBenchmark]) -> Dict[str, float]:
        if not variants:
            return {}

        importance: Dict[str, float] = {}
        for dim in ArchitectureDimension:
            scores_by_value: Dict[str, List[float]] = defaultdict(list)
            for v, b in zip(variants, benchmarks):
                if dim in v.dimensions:
                    scores_by_value[v.dimensions[dim]].append(b.composite_score)

            if len(scores_by_value) >= 2:
                means = [sum(scores) / len(scores) for scores in scores_by_value.values()]
                grand_mean = sum(means) / len(means)
                variance = sum((m - grand_mean) ** 2 for m in means) / len(means)
                importance[dim.value] = min(1.0, math.sqrt(variance) * 3)
            else:
                importance[dim.value] = 0.0

        return importance

    def search(self, method: str = "evolutionary", num_samples: int = 20,
               population_size: int = 10, generations: int = 5) -> SearchResult:
        if method == "random":
            return self.random_search(num_samples=num_samples)
        elif method == "evolutionary":
            return self.evolutionary_search(
                population_size=population_size, generations=generations
            )
        elif method == "exhaustive":
            return self._exhaustive_search()
        else:
            return self.evolutionary_search(population_size=population_size, generations=generations)

    def _exhaustive_search(self) -> SearchResult:
        result = SearchResult(search_space_size=self.search_space_size)

        dim_list = list(ArchitectureDimension)
        value_lists = [self._dimension_values[d] for d in dim_list]

        count = 0
        max_exhaustive = 200
        for combo in itertools.product(*value_lists):
            if count >= max_exhaustive:
                break
            variant = ArchitectureVariant()
            for i, dim in enumerate(dim_list):
                variant.dimensions[dim] = combo[i]

            benchmark = self._simulate_benchmark(variant)
            variant.fitness = benchmark.composite_score
            variant.evaluated = True

            self._variants[variant.variant_id] = variant
            self._benchmarks[variant.variant_id] = benchmark
            result.all_variants.append(variant)
            result.all_benchmarks.append(benchmark)
            count += 1

        result.explored_count = count
        result.best_variant = max(result.all_variants, key=lambda v: v.fitness)
        result.best_benchmark = self._benchmarks.get(result.best_variant.variant_id)

        scored = sorted(
            [(v, b.composite_score) for v, b in zip(result.all_variants, result.all_benchmarks)],
            key=lambda x: -x[1],
        )
        result.top_k = [
            {**v.to_dict(), "composite_score": s}
            for v, s in scored[:5]
        ]

        result.dimension_importance = self._compute_dimension_importance(result.all_variants, result.all_benchmarks)
        return result

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "search_space_size": self.search_space_size,
            "variants_explored": len(self._variants),
            "best_fitness": max((b.composite_score for b in self._benchmarks.values()), default=0.0),
            "generations": self._generation,
            "dimensions": {
                dim.value: len(values)
                for dim, values in self._dimension_values.items()
            },
        }
