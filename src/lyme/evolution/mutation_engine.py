from __future__ import annotations

import ast
import difflib
import json
import math
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class MutationType(str, Enum):
    REFACTOR_BOUNDARY = "refactor_boundary"
    SPLIT_MODULE = "split_module"
    MERGE_ABSTRACTIONS = "merge_abstractions"
    SIMPLIFY_API = "simplify_api"
    CHANGE_DEPENDENCY_DIRECTION = "change_dependency_direction"
    REORGANIZE_STATE = "reorganize_state"
    IMPROVE_TEST_SURFACE = "improve_test_surface"
    EXTRACT_INTERFACE = "extract_interface"
    INLINE_DELEGATE = "inline_delegate"
    MOVE_METHOD = "move_method"


class MutationStatus(str, Enum):
    PROPOSED = "proposed"
    SIMULATED = "simulated"
    APPLIED = "applied"
    VERIFIED = "verified"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PROMOTED = "promoted"


@dataclass
class MutationBenefit:
    maintainability_delta: float = 0.0
    testability_delta: float = 0.0
    coupling_delta: float = 0.0
    complexity_delta: float = 0.0
    cognitive_load_delta: float = 0.0
    explanation: str = ""

    def overall_score(self) -> float:
        return (
            self.maintainability_delta
            + self.testability_delta
            - self.coupling_delta
            - self.complexity_delta
            - self.cognitive_load_delta
        ) / 5.0


@dataclass
class MutationRisk:
    breakage_probability: float = 0.0
    test_failure_probability: float = 0.0
    behavioral_change_risk: float = 0.0
    estimated_blast_radius: int = 0
    explanation: str = ""

    def overall_risk(self) -> float:
        return (
            self.breakage_probability
            + self.test_failure_probability
            + self.behavioral_change_risk
            + min(1.0, self.estimated_blast_radius / 20)
        ) / 4.0


@dataclass
class MutationPatch:
    file_path: str
    original_content: str
    patched_content: str
    patch_diff: str = ""
    reverse_diff: str = ""

    def __post_init__(self):
        if not self.patch_diff:
            self.patch_diff = self._compute_diff(self.original_content, self.patched_content)
        if not self.reverse_diff:
            self.reverse_diff = self._compute_diff(self.patched_content, self.original_content)

    @staticmethod
    def _compute_diff(old: str, new: str) -> str:
        return "".join(difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
        ))


@dataclass
class MutationBenchmark:
    before_fitness: Dict[str, float] = field(default_factory=dict)
    after_fitness: Dict[str, float] = field(default_factory=dict)
    test_results_before: Dict[str, Any] = field(default_factory=dict)
    test_results_after: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    memory_delta_kb: float = 0.0


@dataclass
class Mutation:
    mutation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    mutation_type: MutationType = MutationType.REFACTOR_BOUNDARY
    target_files: List[str] = field(default_factory=list)
    description: str = ""
    strategy: str = ""
    predicted_benefit: MutationBenefit = field(default_factory=MutationBenefit)
    predicted_risk: MutationRisk = field(default_factory=MutationRisk)
    simulated_impact: Dict[str, float] = field(default_factory=dict)
    patches: List[MutationPatch] = field(default_factory=list)
    benchmark: Optional[MutationBenchmark] = None
    status: MutationStatus = MutationStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    outcome_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mutation_id": self.mutation_id,
            "mutation_type": self.mutation_type.value,
            "target_files": self.target_files,
            "description": self.description,
            "strategy": self.strategy,
            "predicted_benefit": {
                "overall_score": self.predicted_benefit.overall_score(),
                "explanation": self.predicted_benefit.explanation,
            },
            "predicted_risk": {
                "overall_risk": self.predicted_risk.overall_risk(),
                "explanation": self.predicted_risk.explanation,
            },
            "status": self.status.value,
            "created_at": self.created_at,
            "patch_count": len(self.patches),
            "benchmarked": self.benchmark is not None,
            "outcome_summary": self.outcome_summary,
        }


class MutationEngine:
    def __init__(self, repo_path: Path):
        self.repo_path = Path(repo_path).resolve()
        self.mutations: List[Mutation] = []
        self._history_path = self.repo_path / ".lyme" / "mutations"
        self._history_path.mkdir(parents=True, exist_ok=True)

    def generate_mutations(self, target_subsystems: Optional[List[str]] = None) -> List[Mutation]:
        candidates = self._find_mutation_candidates(target_subsystems)
        mutations = []

        for candidate in candidates:
            mutation_type = candidate["type"]
            target_files = candidate["files"]

            benefit = self._predict_benefit(mutation_type, target_files)
            risk = self._predict_risk(mutation_type, target_files)
            strategy = self._build_strategy(mutation_type, target_files)

            mutation = Mutation(
                mutation_type=mutation_type,
                target_files=target_files,
                description=candidate["description"],
                strategy=strategy,
                predicted_benefit=benefit,
                predicted_risk=risk,
            )
            mutations.append(mutation)

        self.mutations.extend(mutations)
        self._persist()
        return mutations

    def _find_mutation_candidates(self, target_subsystems: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        candidates = []

        for f in self.repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = str(f.relative_to(self.repo_path))
            text = f.read_text(encoding="utf-8", errors="replace")

            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            lines = text.splitlines()
            class_count = len(classes)
            func_count = len(funcs)

            if class_count >= 4:
                candidates.append({
                    "type": MutationType.SPLIT_MODULE,
                    "files": [rel],
                    "description": f"Split {rel}: {class_count} classes in one module",
                })

            if class_count >= 2 and func_count >= 5:
                redundant = self._find_redundant_abstractions(text, rel)
                if redundant:
                    candidates.append({
                        "type": MutationType.MERGE_ABSTRACTIONS,
                        "files": [rel],
                        "description": f"Merge redundant abstractions in {rel}: {redundant}",
                    })

            if len(lines) > 200:
                candidates.append({
                    "type": MutationType.REFACTOR_BOUNDARY,
                    "files": [rel],
                    "description": f"Refactor boundary in {rel}: {len(lines)} lines",
                })

            api_funcs = [
                n for n in funcs
                if n.name.startswith(("get_", "set_", "create_", "update_", "delete_"))
            ]
            if len(api_funcs) >= 5:
                candidates.append({
                    "type": MutationType.SIMPLIFY_API,
                    "files": [rel],
                    "description": f"Simplify API in {rel}: {len(api_funcs)} accessor methods",
                })

            deps = self._extract_dependencies(text)
            internal_deps = [d for d in deps if self._is_internal_module(d)]
            if len(internal_deps) >= 4:
                candidates.append({
                    "type": MutationType.CHANGE_DEPENDENCY_DIRECTION,
                    "files": [rel],
                    "description": f"Flip dependency in {rel}: depends on {len(internal_deps)} internal modules",
                })

            state_holders = self._find_state_holders(tree, rel)
            if state_holders:
                candidates.append({
                    "type": MutationType.REORGANIZE_STATE,
                    "files": [rel],
                    "description": f"Reorganize state in {rel}: {len(state_holders)} state holders",
                })

            test_file = self._find_corresponding_test(rel)
            if test_file:
                test_text = test_file.read_text(encoding="utf-8", errors="replace")
                source_funcs = len(funcs)
                test_funcs = test_text.count("def test_")
                if source_funcs > 0 and test_funcs < source_funcs * 0.5:
                    candidates.append({
                        "type": MutationType.IMPROVE_TEST_SURFACE,
                        "files": [rel, str(test_file.relative_to(self.repo_path))],
                        "description": f"Improve test surface for {rel}: {test_funcs} tests for {source_funcs} functions",
                    })

        return candidates

    def _extract_dependencies(self, text: str) -> Set[str]:
        deps = set()
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        deps.add(node.module.split(".")[0])
        except SyntaxError:
            pass
        return deps

    def _is_internal_module(self, dep: str) -> bool:
        return (self.repo_path / dep).exists() or (self.repo_path / dep.replace(".", "/")).exists()

    def _find_redundant_abstractions(self, text: str, rel: str) -> str:
        try:
            tree = ast.parse(text)
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            if len(classes) < 2:
                return ""
            pairs = []
            for i, ca in enumerate(classes):
                for j, cb in enumerate(classes):
                    if i >= j:
                        continue
                    a_methods = {n.name for n in ca.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) if not n.name.startswith("_")}
                    b_methods = {n.name for n in cb.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) if not n.name.startswith("_")}
                    overlap = a_methods & b_methods
                    if len(overlap) >= max(len(a_methods), len(b_methods)) * 0.5:
                        pairs.append(f"{ca.name}~{cb.name}")
            return ", ".join(pairs) if pairs else ""
        except SyntaxError:
            return ""

    def _find_state_holders(self, tree: ast.AST, rel: str) -> List[str]:
        holders = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                instance_vars = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                        for stmt in ast.walk(item):
                            if isinstance(stmt, ast.Attribute) and isinstance(stmt.ctx, ast.Store):
                                if isinstance(stmt.value, ast.Name) and stmt.value.id == "self":
                                    instance_vars.append(stmt.attr)
                if len(instance_vars) >= 5:
                    holders.append(f"{node.name}({len(instance_vars)} vars)")
        return holders

    def _find_corresponding_test(self, source_rel: str) -> Optional[Path]:
        src = Path(source_rel)
        parts = src.parts
        test_path = self.repo_path / "tests" / f"test_{src.name}"
        if test_path.exists():
            return test_path
        for subdir in ["tests", "test"]:
            candidate = self.repo_path / subdir / src.relative_to(*src.parts[:1]) if len(parts) > 1 else self.repo_path / subdir / src.name
            if candidate.exists():
                return candidate
        src_stem = src.stem
        for tf in (self.repo_path / "tests").rglob(f"*{src_stem}*"):
            return tf
        return None

    def _predict_benefit(self, mutation_type: MutationType, target_files: List[str]) -> MutationBenefit:
        benefit = MutationBenefit()

        if mutation_type == MutationType.SPLIT_MODULE:
            benefit.maintainability_delta = 0.25
            benefit.complexity_delta = -0.2
            benefit.cognitive_load_delta = -0.15
            benefit.explanation = "Splitting reduces per-file cognitive load and improves maintainability through smaller, focused modules"
        elif mutation_type == MutationType.MERGE_ABSTRACTIONS:
            benefit.coupling_delta = -0.15
            benefit.complexity_delta = -0.1
            benefit.explanation = "Merging redundant abstractions reduces coupling and eliminates duplicate indirection"
        elif mutation_type == MutationType.SIMPLIFY_API:
            benefit.cognitive_load_delta = -0.2
            benefit.maintainability_delta = 0.15
            benefit.explanation = "Fewer surface functions reduces API surface area and cognitive overhead"
        elif mutation_type == MutationType.CHANGE_DEPENDENCY_DIRECTION:
            benefit.coupling_delta = -0.25
            benefit.maintainability_delta = 0.2
            benefit.explanation = "Flipping dependency direction reduces coupling and improves modularity through dependency inversion"
        elif mutation_type == MutationType.REORGANIZE_STATE:
            benefit.testability_delta = 0.2
            benefit.cognitive_load_delta = -0.15
            benefit.explanation = "Centralizing state management improves testability and reduces implicit state scattering"
        elif mutation_type == MutationType.IMPROVE_TEST_SURFACE:
            benefit.testability_delta = 0.3
            benefit.maintainability_delta = 0.1
            benefit.explanation = "Better test coverage provides safety net for future refactoring and documents expected behavior"
        elif mutation_type == MutationType.REFACTOR_BOUNDARY:
            benefit.maintainability_delta = 0.15
            benefit.complexity_delta = -0.1
            benefit.explanation = "Cleaner module boundaries improve separation of concerns and reduce cross-cutting changes"

        return benefit

    def _predict_risk(self, mutation_type: MutationType, target_files: List[str]) -> MutationRisk:
        risk = MutationRisk()

        if mutation_type == MutationType.SPLIT_MODULE:
            risk.breakage_probability = 0.35
            risk.estimated_blast_radius = len(target_files) + 2
            risk.explanation = "Splitting modules may break import chains; requires updating all references"
        elif mutation_type == MutationType.MERGE_ABSTRACTIONS:
            risk.behavioral_change_risk = 0.25
            risk.estimated_blast_radius = len(target_files) + 1
            risk.explanation = "Merging abstractions may lose behavioral nuance; verify equivalence"
        elif mutation_type == MutationType.SIMPLIFY_API:
            risk.breakage_probability = 0.2
            risk.estimated_blast_radius = len(target_files)
            risk.explanation = "API simplification may break callers; check all call sites"
        elif mutation_type == MutationType.CHANGE_DEPENDENCY_DIRECTION:
            risk.breakage_probability = 0.4
            risk.test_failure_probability = 0.3
            risk.estimated_blast_radius = len(target_files) + 3
            risk.explanation = "Dependency direction changes affect module initialization order; may have cascade effects"
        elif mutation_type == MutationType.REORGANIZE_STATE:
            risk.behavioral_change_risk = 0.3
            risk.estimated_blast_radius = len(target_files) + 2
            risk.explanation = "State reorganization may alter runtime behavior; needs behavioral equivalence check"
        elif mutation_type == MutationType.IMPROVE_TEST_SURFACE:
            risk.breakage_probability = 0.05
            risk.estimated_blast_radius = 0
            risk.explanation = "Adding tests has minimal risk to production code"
        elif mutation_type == MutationType.REFACTOR_BOUNDARY:
            risk.breakage_probability = 0.2
            risk.estimated_blast_radius = len(target_files) + 1
            risk.explanation = "Boundary changes may require updating related module imports and references"

        return risk

    def _build_strategy(self, mutation_type: MutationType, target_files: List[str]) -> str:
        strategies = {
            MutationType.SPLIT_MODULE: f"Extract cohesive subsets of {', '.join(target_files)} into focused modules based on dependency clustering. Create new files, update imports, verify all references.",
            MutationType.MERGE_ABSTRACTIONS: f"Identify classes with overlapping method signatures in {', '.join(target_files)}. Consolidate into unified abstraction with parameterized behavior.",
            MutationType.SIMPLIFY_API: f"Review public API surface of {', '.join(target_files)}. Consolidate getter/setter pairs. Remove unused parameters. Add convenience methods.",
            MutationType.CHANGE_DEPENDENCY_DIRECTION: f"Apply dependency inversion to {', '.join(target_files)}. Extract interfaces, invert import direction, inject dependencies.",
            MutationType.REORGANIZE_STATE: f"Extract state management from {', '.join(target_files)} into dedicated state objects. Centralize mutation logic, add state change listeners.",
            MutationType.IMPROVE_TEST_SURFACE: f"Add parameterized tests for uncovered functions in {', '.join(target_files)}. Add edge case tests. Generate test scaffolding.",
            MutationType.REFACTOR_BOUNDARY: f"Reorganize module boundaries in {', '.join(target_files)}. Move related functions together, split unrelated concerns, update cross-references.",
        }
        return strategies.get(mutation_type, "Apply mutation with minimal behavioral change.")

    def simulate_impact(self, mutation: Mutation) -> Dict[str, float]:
        import random
        rng = random.Random(mutation.mutation_id)
        benefit = mutation.predicted_benefit.overall_score()
        risk = mutation.predicted_risk.overall_risk()
        noise = rng.gauss(0, 0.1)
        net_impact = benefit * 0.7 - risk * 0.3 + noise

        impact = {
            "net_impact": round(net_impact, 4),
            "confidence": round(max(0.1, min(0.9, abs(net_impact) * 0.5 + 0.3)), 4),
            "benefit_contribution": round(benefit * 0.7, 4),
            "risk_penalty": round(risk * 0.3, 4),
            "noise_factor": round(noise, 4),
        }
        mutation.simulated_impact = impact
        mutation.status = MutationStatus.SIMULATED
        self._persist()
        return impact

    def produce_patches(self, mutation: Mutation) -> List[MutationPatch]:
        patches = []
        for file_path in mutation.target_files:
            full_path = self.repo_path / file_path
            if not full_path.exists():
                continue
            try:
                original = full_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                original = ""

            patched = self._apply_mutation_strategy(mutation.mutation_type, original, file_path)

            if patched != original:
                patch = MutationPatch(
                    file_path=file_path,
                    original_content=original,
                    patched_content=patched,
                )
                patches.append(patch)

        mutation.patches = patches
        mutation.status = MutationStatus.APPLIED
        self._persist()
        return patches

    def _apply_mutation_strategy(self, mutation_type: MutationType, content: str, file_path: str) -> str:
        if mutation_type == MutationType.SIMPLIFY_API:
            return self._simplify_api(content)
        if mutation_type == MutationType.IMPROVE_TEST_SURFACE:
            return self._add_test_scaffolding(content, file_path)
        return content

    def _simplify_api(self, content: str) -> str:
        try:
            tree = ast.parse(content)
            simplified = content
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not node.decorator_list and node.name.startswith(("get_", "set_")):
                        old = ast.get_source_segment(content, node) or ""
                        if "return" in old and len(node.body) <= 2:
                            comment = f"\n# TODO: Consider replacing {node.name} with @property\n"
                            if comment not in simplified:
                                simplified = simplified.replace(old, comment + old)
            return simplified
        except SyntaxError:
            return content

    def _add_test_scaffolding(self, content: str, file_path: str) -> str:
        try:
            tree = ast.parse(content)
            existing_tests = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith("_") and n.name not in existing_tests and not n.name.startswith("test_")]
            if not funcs:
                return content
            new_content = content.rstrip() + "\n\n"
            for func in funcs[:5]:
                params = [a.arg for a in func.args.args if a.arg != "self"]
                default_val = ", ".join(params) if params else ""
                new_content += f"def test_{func.name}():\n"
                new_content += f'    """Test {func.name} behavior."""\n'
                new_content += f"    # TODO: implement\n"
                if default_val:
                    new_content += f"    result = {func.name}({default_val})\n"
                else:
                    new_content += f"    result = {func.name}()\n"
                new_content += f"    assert result is not None\n\n"
            return new_content
        except SyntaxError:
            return content

    def benchmark_mutation(self, mutation: Mutation) -> MutationBenchmark:
        benchmark = MutationBenchmark()
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "--json-report"],
                capture_output=True, text=True, timeout=120,
                cwd=self.repo_path,
            )
            benchmark.test_results_before = {
                "returncode": result.returncode,
                "stdout": result.stdout[-500:],
                "stderr": result.stderr[-500:],
            }
        except Exception:
            benchmark.test_results_before = {"error": "Could not run tests"}

        before_size = 0
        for f in self.repo_path.rglob("*.py"):
            if f.is_file():
                before_size += f.stat().st_size
        benchmark.before_fitness["total_size_bytes"] = before_size

        start = time.time()
        for patch in mutation.patches:
            full_path = self.repo_path / patch.file_path
            full_path.write_text(patch.patched_content, encoding="utf-8")

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=short", "--json-report"],
                capture_output=True, text=True, timeout=120,
                cwd=self.repo_path,
            )
            benchmark.test_results_after = {
                "returncode": result.returncode,
                "stdout": result.stdout[-500:],
                "stderr": result.stderr[-500:],
            }
        except Exception:
            benchmark.test_results_after = {"error": "Could not run tests"}
        benchmark.duration_ms = (time.time() - start) * 1000

        after_size = 0
        for f in self.repo_path.rglob("*.py"):
            if f.is_file():
                after_size += f.stat().st_size
        benchmark.after_fitness["total_size_bytes"] = after_size
        benchmark.memory_delta_kb = (after_size - before_size) / 1024

        for patch in mutation.patches:
            full_path = self.repo_path / patch.file_path
            full_path.write_text(patch.original_content, encoding="utf-8")

        mutation.benchmark = benchmark
        mutation.status = MutationStatus.VERIFIED
        self._persist()
        return benchmark

    def record_outcome(self, mutation: Mutation, promoted: bool = False):
        if promoted:
            mutation.status = MutationStatus.PROMOTED
        else:
            mutation.status = MutationStatus.ROLLED_BACK

        mutation.outcome_summary = (
            f"{'Promoted' if promoted else 'Rolled back'} mutation {mutation.mutation_type.value} "
            f"on {len(mutation.target_files)} files. "
            f"Predicted benefit: {mutation.predicted_benefit.overall_score():.3f}, "
            f"Risk: {mutation.predicted_risk.overall_risk():.3f}"
        )
        self._persist()

    def get_mutation_history(self) -> List[Mutation]:
        self._load()
        return list(self.mutations)

    def get_mutation(self, mutation_id: str) -> Optional[Mutation]:
        self._load()
        for m in self.mutations:
            if m.mutation_id == mutation_id:
                return m
        return None

    def _persist(self):
        data = [m.to_dict() for m in self.mutations]
        path = self._history_path / "mutations.json"
        path.write_text(json.dumps(data, indent=2, default=str))

    def _load(self):
        path = self._history_path / "mutations.json"
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self.mutations = []
                for d in data:
                    m = Mutation(
                        mutation_id=d["mutation_id"],
                        mutation_type=MutationType(d["mutation_type"]),
                        target_files=d["target_files"],
                        description=d["description"],
                        strategy=d["strategy"],
                        status=MutationStatus(d["status"]),
                        created_at=d["created_at"],
                    )
                    self.mutations.append(m)
            except Exception:
                pass
