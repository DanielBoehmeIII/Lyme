from __future__ import annotations

import ast
import json
import math
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .mutation_engine import Mutation, MutationEngine, MutationPatch, MutationType


class FitnessDimension(str, Enum):
    MAINTAINABILITY = "maintainability"
    TESTABILITY = "testability"
    REPAIRABILITY = "repairability"
    COUPLING = "coupling"
    COMPLEXITY = "complexity"
    RUNTIME_STABILITY = "runtime_stability"
    DEVELOPER_COGNITION = "developer_cognition"


@dataclass
class FitnessScore:
    dimension: FitnessDimension
    score: float
    confidence: float
    explanation: str
    contributing_factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension.value,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "explanation": self.explanation,
            "contributing_factors": self.contributing_factors,
        }


@dataclass
class FitnessAssessment:
    repo_path: str
    scores: Dict[str, FitnessScore] = field(default_factory=dict)
    overall_fitness: float = 0.0
    weakest_dimension: Optional[str] = None
    strongest_dimension: Optional[str] = None
    assessed_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repo_path": self.repo_path,
            "overall_fitness": round(self.overall_fitness, 4),
            "weakest_dimension": self.weakest_dimension,
            "strongest_dimension": self.strongest_dimension,
            "scores": {k: v.to_dict() for k, v in self.scores.items()},
            "assessed_at": self.assessed_at,
        }


@dataclass
class RefactorProposal:
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    title: str = ""
    description: str = ""
    target_dimension: FitnessDimension = FitnessDimension.MAINTAINABILITY
    why_it_helps: str = ""
    estimated_confidence: float = 0.0
    mutation: Optional[Mutation] = None
    expected_improvement: Dict[str, float] = field(default_factory=dict)
    before_fitness: Optional[Dict[str, FitnessScore]] = None
    after_fitness: Optional[Dict[str, FitnessScore]] = None
    verification_result: Dict[str, Any] = field(default_factory=dict)
    applied: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "title": self.title,
            "description": self.description,
            "target_dimension": self.target_dimension.value,
            "why_it_helps": self.why_it_helps,
            "estimated_confidence": round(self.estimated_confidence, 4),
            "expected_improvement": self.expected_improvement,
            "applied": self.applied,
            "verified": self.verification_result.get("passed", False) if self.verification_result else False,
        }


class FitnessAssessor:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()

    def assess(self) -> FitnessAssessment:
        assessment = FitnessAssessment(repo_path=str(self.repo_path))

        scores = {}
        for dimension in FitnessDimension:
            score = self._assess_dimension(dimension)
            scores[dimension.value] = score
        assessment.scores = scores

        values = [(k, v.score * v.confidence) for k, v in scores.items()]
        assessment.overall_fitness = sum(v for _, v in values) / max(len(values), 1)

        if scores:
            assessment.weakest_dimension = min(scores, key=lambda k: scores[k].score)
            assessment.strongest_dimension = max(scores, key=lambda k: scores[k].score)

        return assessment

    def _assess_dimension(self, dimension: FitnessDimension) -> FitnessScore:
        assessors = {
            FitnessDimension.MAINTAINABILITY: self._assess_maintainability,
            FitnessDimension.TESTABILITY: self._assess_testability,
            FitnessDimension.REPAIRABILITY: self._assess_repairability,
            FitnessDimension.COUPLING: self._assess_coupling,
            FitnessDimension.COMPLEXITY: self._assess_complexity,
            FitnessDimension.RUNTIME_STABILITY: self._assess_runtime_stability,
            FitnessDimension.DEVELOPER_COGNITION: self._assess_developer_cognition,
        }
        assessor = assessors.get(dimension, self._assess_maintainability)
        return assessor()

    def _assess_maintainability(self) -> FitnessScore:
        factors = {}
        total_files = 0
        total_classes = 0
        total_funcs = 0
        total_lines = 0

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            total_files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                total_lines += len(lines)
                tree = ast.parse(text)
                total_classes += sum(1 for _ in ast.walk(tree) if isinstance(_, ast.ClassDef))
                total_funcs += sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.FunctionDef, ast.AsyncFunctionDef)))
            except Exception:
                pass

        avg_file_lines = total_lines / max(total_files, 1)
        avg_class_per_file = total_classes / max(total_files, 1)

        factors["avg_file_lines"] = avg_file_lines
        factors["avg_classes_per_file"] = avg_class_per_file

        score = 0.7
        if avg_file_lines > 300:
            score -= 0.2
        elif avg_file_lines > 150:
            score -= 0.1
        if avg_class_per_file > 3:
            score -= 0.15
        if total_files > 50:
            score += 0.1

        score = max(0.0, min(1.0, score))
        return FitnessScore(
            dimension=FitnessDimension.MAINTAINABILITY,
            score=score,
            confidence=0.7,
            explanation=f"{total_files} files, avg {avg_file_lines:.0f} lines/file, {total_classes} classes",
            contributing_factors=factors,
        )

    def _assess_testability(self) -> FitnessScore:
        factors = {}
        test_files = 0
        test_funcs = 0
        source_funcs = 0

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                is_test = "test" in f.name or "tests" in f.parts
                funcs = sum(1 for _ in ast.walk(tree) if isinstance(_, (ast.FunctionDef, ast.AsyncFunctionDef)))
                if is_test:
                    test_files += 1
                    test_funcs += sum(1 for _ in ast.walk(tree) if isinstance(_, ast.FunctionDef) and _.name.startswith("test_"))
                else:
                    source_funcs += funcs
            except Exception:
                pass

        factors["test_files"] = test_files
        factors["test_funcs"] = test_funcs
        factors["source_funcs"] = source_funcs

        if source_funcs == 0:
            return FitnessScore(
                dimension=FitnessDimension.TESTABILITY,
                score=0.3,
                confidence=0.3,
                explanation="No source functions detected to assess testability",
                contributing_factors=factors,
            )

        test_ratio = test_funcs / max(source_funcs, 1)
        score = min(1.0, test_ratio * 2)
        confidence = min(0.8, 0.3 + test_ratio * 0.5)

        return FitnessScore(
            dimension=FitnessDimension.TESTABILITY,
            score=score,
            confidence=confidence,
            explanation=f"{test_funcs} tests for {source_funcs} functions ({test_ratio:.0%})",
            contributing_factors=factors,
        )

    def _assess_repairability(self) -> FitnessScore:
        factors = {}
        fix_commits = 0
        total_commits = 0
        has_ci = False

        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--format=%s", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                msgs = result.stdout.splitlines()
                total_commits = len(msgs)
                fix_commits = sum(1 for m in msgs if any(kw in m.lower() for kw in ("fix", "bug", "hotfix", "patch")))
        except Exception:
            pass

        has_ci = (self.repo_path / ".github" / "workflows").exists()
        factors["fix_ratio"] = fix_commits / max(total_commits, 1)
        factors["has_ci"] = 1.0 if has_ci else 0.0

        score = 0.5
        if has_ci:
            score += 0.2
        if total_commits > 50:
            score += 0.1
        if fix_commits / max(total_commits, 1) < 0.2:
            score += 0.1

        return FitnessScore(
            dimension=FitnessDimension.REPAIRABILITY,
            score=min(1.0, score),
            confidence=0.5,
            explanation=f"{fix_commits} fix commits out of {total_commits}, CI={'yes' if has_ci else 'no'}",
            contributing_factors=factors,
        )

    def _assess_coupling(self) -> FitnessScore:
        dep_graph: Dict[str, Set[str]] = {}
        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                deps = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            deps.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            deps.add(node.module.split(".")[0])
                rel = str(f.relative_to(self.repo_path))
                dep_graph[rel] = deps
            except Exception:
                pass

        if not dep_graph:
            return FitnessScore(
                dimension=FitnessDimension.COUPLING,
                score=0.7,
                confidence=0.3,
                explanation="No Python files to assess coupling",
            )

        avg_deps = sum(len(d) for d in dep_graph.values()) / len(dep_graph)
        fan_in: Counter = Counter()
        for src, deps in dep_graph.items():
            for dep in deps:
                fan_in[dep] += 1
        high_fan_in = sum(1 for v in fan_in.values() if v > 5)
        cycles = self._detect_cycles(dep_graph)
        factors = {
            "avg_deps_per_file": avg_deps,
            "high_fan_in_modules": high_fan_in,
            "dependency_cycles": len(cycles),
        }

        score = 0.7
        if avg_deps > 8:
            score -= 0.2
        elif avg_deps > 5:
            score -= 0.1
        if high_fan_in > 3:
            score -= 0.15
        if cycles:
            score -= 0.1 * min(1.0, len(cycles) / 3)
        score = max(0.0, min(1.0, score))

        return FitnessScore(
            dimension=FitnessDimension.COUPLING,
            score=score,
            confidence=0.65,
            explanation=f"Avg {avg_deps:.1f} deps/file, {high_fan_in} high fan-in, {len(cycles)} cycles",
            contributing_factors=factors,
        )

    def _detect_cycles(self, graph: Dict[str, Set[str]]) -> List[Set[str]]:
        cycles = []
        visited: Set[str] = set()
        path: List[str] = []

        def dfs(node: str):
            if node in path:
                cycle_start = path.index(node)
                cycle = set(path[cycle_start:])
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            for neighbor in graph.get(node, set()):
                if neighbor in graph:
                    dfs(neighbor)
            path.pop()

        for node in graph:
            dfs(node)
        return cycles

    def _assess_complexity(self) -> FitnessScore:
        factors = {}
        total_complexity = 0
        total_files = 0
        max_nesting_total = 0

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            total_files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                lines = text.splitlines()
                file_complexity = len(lines) * 0.3
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        file_complexity += len(node.body) * 0.5
                    if isinstance(node, ast.If):
                        file_complexity += 1
                total_complexity += file_complexity
                max_nesting_total += self._max_nesting(tree)
            except Exception:
                pass

        avg_complexity = total_complexity / max(total_files, 1)
        avg_nesting = max_nesting_total / max(total_files, 1)
        factors["avg_complexity"] = avg_complexity
        factors["avg_nesting"] = avg_nesting

        score = 0.7
        if avg_complexity > 50:
            score -= 0.2
        elif avg_complexity > 25:
            score -= 0.1
        if avg_nesting > 3:
            score -= 0.1

        return FitnessScore(
            dimension=FitnessDimension.COMPLEXITY,
            score=max(0.0, min(1.0, score)),
            confidence=0.6,
            explanation=f"Avg complexity {avg_complexity:.1f}, avg nesting {avg_nesting:.1f}",
            contributing_factors=factors,
        )

    def _max_nesting(self, node, current_depth=0) -> int:
        max_depth = current_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)):
                depth = self._max_nesting(child, current_depth + 1)
                max_depth = max(max_depth, depth)
            else:
                depth = self._max_nesting(child, current_depth)
                max_depth = max(max_depth, depth)
        return max_depth

    def _assess_runtime_stability(self) -> FitnessScore:
        factors = {}
        has_git = False
        recent_churn = 0

        try:
            import subprocess
            result = subprocess.run(
                ["git", "-C", str(self.repo_path), "log", "--format=%at", "-100"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                has_git = True
                timestamps = [float(t) for t in result.stdout.splitlines() if t]
                if len(timestamps) >= 2:
                    now = max(timestamps)
                    month_ago = now - 86400 * 30
                    recent = [t for t in timestamps if t > month_ago]
                    recent_churn = len(recent)

            factors["has_git"] = 1.0 if has_git else 0.0
            factors["recent_monthly_commits"] = recent_churn

            score = 0.6
            if has_git:
                score += 0.1
            if 5 <= recent_churn <= 40:
                score += 0.1
            elif recent_churn > 80:
                score -= 0.1

            return FitnessScore(
                dimension=FitnessDimension.RUNTIME_STABILITY,
                score=min(1.0, score),
                confidence=0.5,
                explanation=f"{recent_churn} commits in last 30 days" if has_git else "No git history",
                contributing_factors=factors,
            )
        except Exception:
            return FitnessScore(
                dimension=FitnessDimension.RUNTIME_STABILITY,
                score=0.4,
                confidence=0.3,
                explanation="Could not assess git history",
                contributing_factors=factors,
            )

    def _assess_developer_cognition(self) -> FitnessScore:
        factors = {}
        total_lines = 0
        total_comments = 0
        total_funcs = 0
        total_nesting = 0
        total_files = 0

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            total_files += 1
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                lines = text.splitlines()
                total_lines += len(lines)
                total_comments += sum(1 for l in lines if l.strip().startswith("#"))
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        total_funcs += 1
                total_nesting += self._max_nesting(tree)
            except Exception:
                pass

        comment_ratio = total_comments / max(total_lines, 1)
        avg_func_len = total_lines / max(total_funcs, 1)
        avg_nesting = total_nesting / max(total_files, 1)
        factors["comment_ratio"] = comment_ratio
        factors["avg_func_len"] = avg_func_len
        factors["avg_nesting"] = avg_nesting

        score = 0.6
        if comment_ratio > 0.05:
            score += 0.1
        if comment_ratio > 0.15:
            score += 0.1
        if avg_func_len < 30:
            score += 0.1
        elif avg_func_len > 60:
            score -= 0.1
        if avg_nesting > 4:
            score -= 0.1

        return FitnessScore(
            dimension=FitnessDimension.DEVELOPER_COGNITION,
            score=max(0.0, min(1.0, score)),
            confidence=0.55,
            explanation=f"Comment ratio {comment_ratio:.1%}, avg func {avg_func_len:.0f} lines, avg nesting {avg_nesting:.1f}",
            contributing_factors=factors,
        )


class FitnessGuidedRefactorer:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.assessor = FitnessAssessor(repo_path)
        self.mutation_engine = MutationEngine(repo_path)
        self.proposals: List[RefactorProposal] = []

    def assess_fitness(self) -> FitnessAssessment:
        return self.assessor.assess()

    def propose_refactors(self, assessment: FitnessAssessment) -> List[RefactorProposal]:
        proposals = []

        dim_score_map = {v.value: v for v in FitnessDimension}
        for dim_name, score in assessment.scores.items():
            dimension = dim_score_map.get(dim_name)
            if not dimension or score.score >= 0.7:
                continue

            proposals.extend(self._generate_proposals_for_dimension(dimension, score, assessment))

        proposals.sort(key=lambda p: p.estimated_confidence, reverse=True)
        self.proposals = proposals
        return proposals

    def _generate_proposals_for_dimension(self, dimension: FitnessDimension, score: FitnessScore, assessment: FitnessAssessment) -> List[RefactorProposal]:
        proposals = []

        if dimension == FitnessDimension.MAINTAINABILITY:
            mutations = self.mutation_engine.generate_mutations()
            for mut in mutations[:2]:
                why = (
                    f"Improving {mut.mutation_type.value} in {', '.join(mut.target_files)} "
                    f"addresses maintainability gaps. The module has structural issues "
                    f"that increase cognitive overhead during maintenance."
                )
                expected_improvement = {
                    "maintainability": mut.predicted_benefit.maintainability_delta,
                    "complexity": mut.predicted_benefit.complexity_delta,
                }
                proposal = RefactorProposal(
                    title=f"Improve maintainability via {mut.mutation_type.value.replace('_', ' ')}",
                    description=mut.description,
                    target_dimension=dimension,
                    why_it_helps=why,
                    estimated_confidence=0.6,
                    mutation=mut,
                    expected_improvement=expected_improvement,
                    before_fitness=assessment.scores,
                )
                proposals.append(proposal)

        elif dimension == FitnessDimension.TESTABILITY:
            test_mutations = [m for m in self.mutation_engine.generate_mutations() if m.mutation_type == MutationType.IMPROVE_TEST_SURFACE]
            for mut in test_mutations[:2]:
                proposal = RefactorProposal(
                    title=f"Improve testability: {', '.join(mut.target_files)}",
                    description=mut.description,
                    target_dimension=dimension,
                    why_it_helps=(f"Testing is weakest dimension ({score.score:.2f}). "
                                  f"Adding coverage for uncovered functions provides safety net and documents expected behavior."),
                    estimated_confidence=0.8,
                    mutation=mut,
                    expected_improvement={"testability": 0.2},
                    before_fitness=assessment.scores,
                )
                proposals.append(proposal)

        elif dimension == FitnessDimension.COUPLING:
            mutations = self.mutation_engine.generate_mutations()
            dep_mutations = [m for m in mutations if m.mutation_type in (MutationType.CHANGE_DEPENDENCY_DIRECTION, MutationType.REFACTOR_BOUNDARY)]
            for mut in dep_mutations[:2]:
                proposal = RefactorProposal(
                    title=f"Reduce coupling via {mut.mutation_type.value.replace('_', ' ')}",
                    description=mut.description,
                    target_dimension=dimension,
                    why_it_helps=(f"Coupling score is {score.score:.2f}. "
                                  f"Reducing dependency entanglement improves modularity and limits change propagation."),
                    estimated_confidence=0.55,
                    mutation=mut,
                    expected_improvement={"coupling": -0.2},
                    before_fitness=assessment.scores,
                )
                proposals.append(proposal)

        else:
            mutations = self.mutation_engine.generate_mutations()
            for mut in mutations[:1]:
                proposal = RefactorProposal(
                    title=f"Address {dimension.value} via {mut.mutation_type.value.replace('_', ' ')}",
                    description=mut.description,
                    target_dimension=dimension,
                    why_it_helps=(f"Current {dimension.value} score is {score.score:.2f}. "
                                  f"Targeted mutation addresses underlying structural issues."),
                    estimated_confidence=0.5,
                    mutation=mut,
                    expected_improvement={dimension.value: 0.15},
                    before_fitness=assessment.scores,
                )
                proposals.append(proposal)

        return proposals

    def explain_proposal(self, proposal: RefactorProposal) -> str:
        lines = []
        lines.append("═" * 60)
        lines.append(f" REFACTOR PROPOSAL: {proposal.title}")
        lines.append("═" * 60)
        lines.append(f"  Target dimension: {proposal.target_dimension.value}")
        lines.append(f"  Confidence: {proposal.estimated_confidence:.0%}")
        lines.append("")
        lines.append("  Why this helps:")
        lines.append(f"    {proposal.why_it_helps}")
        lines.append("")
        if proposal.mutation:
            lines.append("  Mutation strategy:")
            lines.append(f"    {proposal.mutation.strategy}")
            lines.append("")
            lines.append("  Expected improvement:")
            for k, v in proposal.expected_improvement.items():
                sign = "+" if v >= 0 else ""
                lines.append(f"    {k}: {sign}{v:.3f}")
            lines.append("")
            lines.append("  Predicted benefit:")
            b = proposal.mutation.predicted_benefit
            lines.append(f"    Overall: {b.overall_score():.3f}")
            lines.append(f"    {b.explanation}")
            lines.append("")
            lines.append("  Predicted risk:")
            r = proposal.mutation.predicted_risk
            lines.append(f"    Overall: {r.overall_risk():.3f}")
            lines.append(f"    {r.explanation}")
        lines.append("═" * 60)
        return "\n".join(lines)

    def apply_proposal(self, proposal: RefactorProposal) -> bool:
        if not proposal.mutation:
            return False

        patches = self.mutation_engine.produce_patches(proposal.mutation)
        if not patches:
            return False

        for patch in patches:
            full_path = self.repo_path / patch.file_path
            full_path.write_text(patch.patched_content, encoding="utf-8")

        proposal.applied = True
        return True

    def verify_proposal(self, proposal: RefactorProposal) -> Dict[str, Any]:
        if not proposal.mutation:
            return {"passed": False, "error": "No mutation"}

        benchmark = self.mutation_engine.benchmark_mutation(proposal.mutation)
        after_assessment = self.assessor.assess()

        proposal.after_fitness = after_assessment.scores

        test_passed = benchmark.test_results_after.get("returncode", -1) in (0, None, -1)

        before_overall = proposal.before_fitness.get(proposal.target_dimension.value, FitnessScore(proposal.target_dimension, 0, 0, "")).score if proposal.before_fitness else 0
        after_score = after_assessment.scores.get(proposal.target_dimension.value)
        after_val = after_score.score if after_score else 0
        improvement = after_val - before_overall

        result = {
            "passed": test_passed,
            "fitness_before": round(before_overall, 4),
            "fitness_after": round(after_val, 4),
            "improvement": round(improvement, 4),
            "dimension": proposal.target_dimension.value,
            "benchmark_duration_ms": round(benchmark.duration_ms, 2),
            "test_status": "passed" if test_passed else "failed",
        }
        proposal.verification_result = result
        return result

    def compare_before_after(self, assessment_before: FitnessAssessment, assessment_after: FitnessAssessment) -> Dict[str, Any]:
        comparison = {}
        all_dims = set(assessment_before.scores.keys()) | set(assessment_after.scores.keys())
        for dim in all_dims:
            before = assessment_before.scores.get(dim)
            after = assessment_after.scores.get(dim)
            b_val = before.score if before else 0
            a_val = after.score if after else 0
            comparison[dim] = {
                "before": round(b_val, 4),
                "after": round(a_val, 4),
                "delta": round(a_val - b_val, 4),
                "improved": a_val > b_val,
            }

        comparison["overall_before"] = round(assessment_before.overall_fitness, 4)
        comparison["overall_after"] = round(assessment_after.overall_fitness, 4)
        comparison["overall_delta"] = round(assessment_after.overall_fitness - assessment_before.overall_fitness, 4)

        return comparison
