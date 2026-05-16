from __future__ import annotations

import difflib
import json
import random
import shutil
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .mutation_engine import Mutation, MutationEngine, MutationPatch, MutationStatus
from .fitness_refactoring import FitnessAssessor, FitnessAssessment, FitnessGuidedRefactorer, RefactorProposal


class ExperimentStatus(str, Enum):
    CREATED = "created"
    MUTATION_APPLIED = "mutation_applied"
    TESTS_RUN = "tests_run"
    BENCHMARKED = "benchmarked"
    COMPARED = "compared"
    PROMOTED = "promoted"
    DISCARDED = "discarded"
    FAILED = "failed"


@dataclass
class SandboxExperiment:
    experiment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    branch_name: str = ""
    base_branch: str = ""
    status: ExperimentStatus = ExperimentStatus.CREATED
    mutation: Optional[Mutation] = None
    fitness_before: Optional[FitnessAssessment] = None
    fitness_after: Optional[FitnessAssessment] = None
    test_results: Dict[str, Any] = field(default_factory=dict)
    benchmark_results: Dict[str, Any] = field(default_factory=dict)
    comparison: Dict[str, Any] = field(default_factory=dict)
    trace_log: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    promoted_at: Optional[float] = None
    error_message: str = ""
    patches_applied: List[str] = field(default_factory=list)

    def log(self, message: str):
        ts = datetime.now(timezone.utc).isoformat()
        self.trace_log.append(f"[{ts}] {message}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "name": self.name,
            "branch_name": self.branch_name,
            "base_branch": self.base_branch,
            "status": self.status.value,
            "mutation_id": self.mutation.mutation_id if self.mutation else None,
            "fitness_before": self.fitness_before.to_dict() if self.fitness_before else None,
            "fitness_after": self.fitness_after.to_dict() if self.fitness_after else None,
            "test_results": self.test_results,
            "comparison": self.comparison,
            "promoted": self.promoted_at is not None,
            "error": self.error_message if self.error_message else None,
            "patches": len(self.patches_applied),
            "trace_count": len(self.trace_log),
            "created_at": self.created_at,
        }


class EvolutionSandbox:
    def __init__(self, repo_path: Path, sandbox_dir: Optional[Path] = None):
        self.repo_path = Path(repo_path).resolve()
        self.sandbox_dir = sandbox_dir or (self.repo_path / ".lyme" / "sandbox")
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.experiments: Dict[str, SandboxExperiment] = {}
        self._load()

    def create_experiment(self, name: str, base_branch: Optional[str] = None) -> SandboxExperiment:
        if base_branch is None:
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    capture_output=True, text=True, cwd=self.repo_path, timeout=10,
                )
                base_branch = result.stdout.strip()
            except Exception:
                base_branch = "main"

        branch_name = f"lyme-experiment/{name.replace(' ', '-').lower()}-{uuid.uuid4().hex[:8]}"

        experiment = SandboxExperiment(
            name=name,
            branch_name=branch_name,
            base_branch=base_branch,
        )
        experiment.log(f"Created experiment '{name}' on branch {branch_name} (base: {base_branch})")
        self.experiments[experiment.experiment_id] = experiment
        return experiment

    def create_isolated_branch(self, experiment: SandboxExperiment) -> bool:
        try:
            subprocess.run(
                ["git", "stash", "--include-untracked"],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            subprocess.run(
                ["git", "checkout", "-b", experiment.branch_name, experiment.base_branch],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            experiment.log(f"Created isolated branch {experiment.branch_name} from {experiment.base_branch}")
            return True
        except Exception as e:
            experiment.error_message = f"Failed to create branch: {e}"
            experiment.status = ExperimentStatus.FAILED
            experiment.log(f"ERROR: {experiment.error_message}")
            return False

    def apply_mutation(self, experiment: SandboxExperiment, mutation: Mutation) -> bool:
        experiment.mutation = mutation
        engine = MutationEngine(self.repo_path)

        patches = engine.produce_patches(mutation)
        if not patches:
            experiment.log("No patches produced by mutation")
            experiment.status = ExperimentStatus.FAILED
            return False

        for patch in patches:
            full_path = self.repo_path / patch.file_path
            full_path.write_text(patch.patched_content, encoding="utf-8")
            experiment.patches_applied.append(patch.file_path)

        mutation.status = MutationStatus.APPLIED
        experiment.status = ExperimentStatus.MUTATION_APPLIED
        experiment.log(f"Applied {len(patches)} patches to {len(experiment.patches_applied)} files")
        return True

    def record_fitness_before(self, experiment: SandboxExperiment) -> FitnessAssessment:
        assessor = FitnessAssessor(self.repo_path)
        assessment = assessor.assess()
        experiment.fitness_before = assessment
        experiment.log(f"Recorded fitness before: overall={assessment.overall_fitness:.4f}")
        return assessment

    def record_fitness_after(self, experiment: SandboxExperiment) -> FitnessAssessment:
        assessor = FitnessAssessor(self.repo_path)
        assessment = assessor.assess()
        experiment.fitness_after = assessment
        experiment.log(f"Recorded fitness after: overall={assessment.overall_fitness:.4f}")
        return assessment

    def run_tests(self, experiment: SandboxExperiment, timeout_sec: int = 120) -> Dict[str, Any]:
        results = {
            "passed": False,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "errors": [],
            "duration_ms": 0,
        }

        try:
            start = time.time()
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "-x"],
                capture_output=True, text=True, timeout=timeout_sec,
                cwd=self.repo_path,
            )
            results["duration_ms"] = (time.time() - start) * 1000
            results["passed"] = result.returncode == 0
            results["stdout"] = result.stdout[-1000:]
            results["stderr"] = result.stderr[-1000:]

            if result.returncode != 0:
                for line in result.stdout.splitlines():
                    if "FAILED" in line:
                        results["errors"].append(line.strip())
                for line in result.stderr.splitlines():
                    if "Error" in line or "error" in line:
                        results["errors"].append(line.strip())
        except subprocess.TimeoutExpired:
            results["errors"].append("Tests timed out")
        except Exception as e:
            results["errors"].append(str(e))

        experiment.test_results = results
        experiment.status = ExperimentStatus.TESTS_RUN
        experiment.log(f"Tests: {'passed' if results['passed'] else 'failed'} ({results['duration_ms']:.0f}ms)")
        return results

    def compare_outcomes(self, experiment: SandboxExperiment) -> Dict[str, Any]:
        if not experiment.fitness_before or not experiment.fitness_after:
            comparison = {"error": "Missing before/after fitness assessments"}
            experiment.comparison = comparison
            return comparison

        comparison = {
            "overall_before": round(experiment.fitness_before.overall_fitness, 4),
            "overall_after": round(experiment.fitness_after.overall_fitness, 4),
            "overall_delta": round(experiment.fitness_after.overall_fitness - experiment.fitness_before.overall_fitness, 4),
            "dimensions": {},
        }

        all_dims = set(experiment.fitness_before.scores.keys()) | set(experiment.fitness_after.scores.keys())
        for dim in sorted(all_dims):
            before = experiment.fitness_before.scores.get(dim)
            after = experiment.fitness_after.scores.get(dim)
            b_val = before.score if before else 0
            a_val = after.score if after else 0
            comparison["dimensions"][dim] = {
                "before": round(b_val, 4),
                "after": round(a_val, 4),
                "delta": round(a_val - b_val, 4),
            }

        experiment.comparison = comparison
        experiment.status = ExperimentStatus.COMPARED
        experiment.log(f"Comparison: overall delta = {comparison['overall_delta']:.4f}")
        return comparison

    def discard_failure(self, experiment: SandboxExperiment) -> bool:
        try:
            subprocess.run(
                ["git", "checkout", experiment.base_branch],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            subprocess.run(
                ["git", "branch", "-D", experiment.branch_name],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            experiment.status = ExperimentStatus.DISCARDED
            experiment.log(f"Discarded experiment, deleted branch {experiment.branch_name}")
            return True
        except Exception as e:
            experiment.log(f"Failed to discard: {e}")
            return False

    def promote_success(self, experiment: SandboxExperiment) -> bool:
        try:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            commit_msg = f"lyme: promote experiment '{experiment.name}'"
            if experiment.mutation:
                commit_msg += f" [{experiment.mutation.mutation_type.value}]"
            subprocess.run(
                ["git", "commit", "-m", commit_msg],
                capture_output=True, cwd=self.repo_path, timeout=10,
            )
            experiment.status = ExperimentStatus.PROMOTED
            experiment.promoted_at = time.time()
            experiment.log(f"Promoted experiment: committed as '{commit_msg}'")
            self._preserve_traces(experiment)
            return True
        except Exception as e:
            experiment.log(f"Failed to promote: {e}")
            return False

    def _preserve_traces(self, experiment: SandboxExperiment):
        trace_dir = self.sandbox_dir / "traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        path = trace_dir / f"{experiment.experiment_id}.json"
        path.write_text(json.dumps(experiment.to_dict(), indent=2, default=str))

    def get_experiment(self, experiment_id: str) -> Optional[SandboxExperiment]:
        return self.experiments.get(experiment_id)

    def list_experiments(self, status: Optional[ExperimentStatus] = None) -> List[SandboxExperiment]:
        if status:
            return [e for e in self.experiments.values() if e.status == status]
        return list(self.experiments.values())

    def discard_failures_safely(self) -> int:
        count = 0
        for exp in list(self.experiments.values()):
            if exp.status in (ExperimentStatus.FAILED, ExperimentStatus.DISCARDED):
                continue
            if exp.status in (ExperimentStatus.CREATED, ExperimentStatus.MUTATION_APPLIED):
                continue
            if exp.comparison.get("overall_delta", 0) < -0.05:
                if self.discard_failure(exp):
                    count += 1
        return count

    def _load(self):
        trace_dir = self.sandbox_dir / "traces"
        if trace_dir.exists():
            for f in trace_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text())
                    exp = SandboxExperiment(
                        experiment_id=data["experiment_id"],
                        name=data["name"],
                        branch_name=data["branch_name"],
                        base_branch=data["base_branch"],
                        status=ExperimentStatus(data["status"]),
                        created_at=data.get("created_at", 0),
                    )
                    self.experiments[exp.experiment_id] = exp
                except Exception:
                    pass

    def run_full_experiment(self, name: str, mutation: Mutation) -> SandboxExperiment:
        experiment = self.create_experiment(name)
        experiment.log("Starting full experiment pipeline")

        experiment.log("Recording fitness before...")
        self.record_fitness_before(experiment)

        experiment.log("Creating isolated branch...")
        if not self.create_isolated_branch(experiment):
            return experiment

        experiment.log("Applying mutation...")
        if not self.apply_mutation(experiment, mutation):
            return experiment

        experiment.log("Recording fitness after...")
        self.record_fitness_after(experiment)

        experiment.log("Running tests...")
        self.run_tests(experiment)

        experiment.log("Comparing outcomes...")
        self.compare_outcomes(experiment)

        if experiment.test_results.get("passed") and experiment.comparison.get("overall_delta", -1) >= 0:
            experiment.log("Experiment successful — promoting")
            self.promote_success(experiment)
        else:
            experiment.log("Experiment failed or regressed — discarding")
            self.discard_failure(experiment)

        self._preserve_traces(experiment)
        self._persist()
        return experiment

    def _persist(self):
        index = {"experiment_ids": list(self.experiments.keys())}
        (self.sandbox_dir / "index.json").write_text(json.dumps(index, indent=2))
