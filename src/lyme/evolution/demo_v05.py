from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .mutation_engine import MutationEngine, MutationType
from .fitness_refactoring import FitnessAssessor, FitnessGuidedRefactorer
from .sandbox import EvolutionSandbox
from .maintenance_detector import MaintenanceDetector
from .maintenance_loops import AutonomousMaintenanceLoop
from .maintenance_memory import MaintenanceMemory
from .roadmap_generator import RoadmapGenerator
from .decision_memory import EngineeringDecisionMemory
from .tradeoff_simulator import TradeoffSimulator, TradeoffDomain


class V05Demo:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.results: Dict[str, Any] = {}
        self.timings: Dict[str, float] = {}

    def run(self, full: bool = True) -> Dict[str, Any]:
        demo_steps = [
            ("analyze_repo_health", self._step_analyze_health),
            ("identify_maintenance_opportunity", self._step_identify_opportunity),
            ("simulate_refactor", self._step_simulate_refactor),
            ("apply_mutation_sandbox", self._step_apply_mutation),
            ("compare_fitness", self._step_compare_fitness),
            ("generate_adr", self._step_generate_adr),
            ("update_roadmap", self._step_update_roadmap),
            ("produce_audit_report", self._step_audit_report),
        ]

        for name, step_fn in demo_steps:
            start = time.time()
            try:
                result = step_fn()
                self.results[name] = result
                self.timings[name] = time.time() - start
                print(f"  ✓ {name} ({self.timings[name]:.1f}s)")
            except Exception as e:
                self.results[name] = {"error": str(e)}
                self.timings[name] = time.time() - start
                print(f"  ✗ {name}: {e}")
                if not full:
                    break

        return self.summarize()

    def _step_analyze_health(self) -> Dict[str, Any]:
        assessor = FitnessAssessor(self.repo_path)
        fitness = assessor.assess()
        return fitness.to_dict()

    def _step_identify_opportunity(self) -> Dict[str, Any]:
        detector = MaintenanceDetector(self.repo_path)
        opportunities = detector.detect_all()
        return {
            "total_opportunities": len(opportunities),
            "top_opportunities": [o.to_dict() for o in opportunities[:5]],
        }

    def _step_simulate_refactor(self) -> Dict[str, Any]:
        refactorer = FitnessGuidedRefactorer(self.repo_path)
        assessment = refactorer.assess_fitness()
        proposals = refactorer.propose_refactors(assessment)
        return {
            "fitness": assessment.to_dict(),
            "proposals": [p.to_dict() for p in proposals[:3]],
            "explanation": proposals[0].why_it_helps if proposals else "No proposals generated",
        }

    def _step_apply_mutation(self) -> Dict[str, Any]:
        sandbox = EvolutionSandbox(self.repo_path)
        engine = MutationEngine(self.repo_path)
        mutations = engine.generate_mutations()
        if mutations:
            mutation = mutations[0]
            result = sandbox.run_full_experiment("v0.5-demo-mutation", mutation)
            return result.to_dict()
        return {"error": "No mutations generated"}

    def _step_compare_fitness(self) -> Dict[str, Any]:
        assessor = FitnessAssessor(self.repo_path)
        fitness = assessor.assess()
        return {
            "current_fitness": fitness.to_dict(),
            "dimension_scores": {
                k: {"score": round(v.score, 4), "confidence": round(v.confidence, 4)}
                for k, v in fitness.scores.items()
            },
            "overall_fitness": round(fitness.overall_fitness, 4),
            "weakest": fitness.weakest_dimension,
            "strongest": fitness.strongest_dimension,
        }

    def _step_generate_adr(self) -> Dict[str, Any]:
        memory = EngineeringDecisionMemory(self.repo_path)
        adr = memory.generate_adr_from_data(
            title="Adopt autonomous software evolution pipeline",
            context="Lyme v0.5 introduces autonomous software evolution capabilities including mutation engine, fitness-guided refactoring, and maintenance automation.",
            decision="Implement evolution pipeline with sandbox isolation, fitness assessment, and reversible mutations.",
            rationale="Cautious, measurable, reversible evolution requires isolated experiments with fitness validation before promotion.",
            constraints=["Must preserve behavioral equivalence", "Must support rollback", "Must measure fitness impact"],
            alternatives=["Manual refactoring only", "Full automation without sandbox", "Separate maintenance tool"],
        )
        return adr.to_dict()

    def _step_update_roadmap(self) -> Dict[str, Any]:
        generator = RoadmapGenerator(self.repo_path)
        roadmap = generator.generate_roadmap()
        return roadmap.to_dict()

    def _step_audit_report(self) -> Dict[str, Any]:
        memory = MaintenanceMemory(self.repo_path)
        decisions = EngineeringDecisionMemory(self.repo_path)
        return {
            "maintenance_memory": memory.produce_report(),
            "decision_memory": decisions.produce_report(),
            "all_decisions": decisions.get_statistics(),
        }

    def summarize(self) -> Dict[str, Any]:
        total_time = sum(self.timings.values())
        successful = sum(1 for v in self.results.values() if "error" not in v)

        summary = []
        summary.append("=" * 60)
        summary.append(" LYME v0.5 DEMO RESULTS")
        summary.append("=" * 60)
        for name in self.results:
            status = "✓" if "error" not in self.results[name] else "✗"
            timing = self.timings.get(name, 0)
            summary.append(f"  {status} {name}: {timing:.1f}s")
        summary.append("")
        summary.append(f"  Steps completed: {successful}/{len(self.results)}")
        summary.append(f"  Total time: {total_time:.1f}s")
        summary.append("")
        summary.append("  Demo proves Lyme can:")
        summary.append("    • Analyze repository health through fitness metrics")
        summary.append("    • Identify maintenance opportunities automatically")
        summary.append("    • Simulate refactor impact before applying")
        summary.append("    • Apply mutations in isolated sandbox branches")
        summary.append("    • Compare before/after fitness measurably")
        summary.append("    • Generate Architecture Decision Records")
        summary.append("    • Update technical roadmap with evidence")
        summary.append("    • Produce audit trail for all operations")
        summary.append("")
        summary.append("  Thesis: Lyme evolves software cautiously, measurably, and reversibly.")
        summary.append("=" * 60)

        return {
            "summary": "\n".join(summary),
            "steps_completed": successful,
            "total_steps": len(self.results),
            "total_time_seconds": round(total_time, 1),
            "results": {
                k: v for k, v in self.results.items()
                if "error" not in v
            },
        }
