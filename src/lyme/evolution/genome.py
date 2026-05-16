from __future__ import annotations

import ast
import math
import re
import subprocess
import time
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class GenomeSegment(str, Enum):
    ARCHITECTURE = "architecture"
    DEPENDENCY = "dependency"
    SUBSYSTEM_TOPOLOGY = "subsystem_topology"
    CONVENTIONS = "conventions"
    INVARIANT_FAMILIES = "invariant_families"
    COORDINATION = "coordination"
    RUNTIME_PATTERNS = "runtime_patterns"
    HISTORICAL_TENDENCIES = "historical_tendencies"


@dataclass
class GenomeLocus:
    segment: GenomeSegment
    name: str
    value: Any = None
    confidence: float = 1.0
    alleles: List[Any] = field(default_factory=list)
    compressed_representation: str = ""

    def to_dict(self) -> dict:
        return {
            "segment": self.segment.value,
            "name": self.name,
            "value": str(self.value)[:100] if not isinstance(self.value, (int, float, bool)) else self.value,
            "confidence": self.confidence,
            "allele_count": len(self.alleles),
            "compressed": self.compressed_representation[:50],
        }


@dataclass
class RepositoryGenome:
    repo_path: str = ""
    genome_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    created_at: float = field(default_factory=time.time)
    loci: List[GenomeLocus] = field(default_factory=list)
    genome_version: str = "1.0"

    def add_locus(self, locus: GenomeLocus):
        self.loci.append(locus)

    def get_segment(self, segment: GenomeSegment) -> List[GenomeLocus]:
        return [l for l in self.loci if l.segment == segment]

    def to_dict(self) -> dict:
        return {
            "repo_path": self.repo_path,
            "genome_id": self.genome_id,
            "created_at": self.created_at,
            "genome_version": self.genome_version,
            "locus_count": len(self.loci),
            "segments": {
                seg.value: [l.to_dict() for l in self.get_segment(seg)]
                for seg in GenomeSegment
            },
        }

    def to_compact(self) -> str:
        parts = []
        for segment in GenomeSegment:
            loci = self.get_segment(segment)
            if loci:
                seg_str = f"{segment.value}:"
                for l in loci:
                    if l.compressed_representation:
                        seg_str += l.compressed_representation
                    else:
                        seg_str += f"{l.name}={str(l.value)[:20]};"
                parts.append(seg_str)
        return "|".join(parts)


@dataclass
class GenomeComparison:
    genome_a_id: str = ""
    genome_b_id: str = ""
    overall_similarity: float = 0.0
    segment_similarities: Dict[str, float] = field(default_factory=dict)
    divergent_loci: List[Dict[str, Any]] = field(default_factory=list)
    convergent_loci: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "genome_a": self.genome_a_id,
            "genome_b": self.genome_b_id,
            "overall_similarity": self.overall_similarity,
            "segment_similarities": self.segment_similarities,
            "divergent_loci": self.divergent_loci[:10],
            "convergent_loci": self.convergent_loci[:10],
        }


class GenomeExtractor:
    def extract(self, repo_path: Path) -> RepositoryGenome:
        repo_path = Path(repo_path).resolve()
        genome = RepositoryGenome(repo_path=str(repo_path))

        self._extract_architecture(genome, repo_path)
        self._extract_dependency(genome, repo_path)
        self._extract_topology(genome, repo_path)
        self._extract_conventions(genome, repo_path)
        self._extract_invariants(genome, repo_path)
        self._extract_coordination(genome, repo_path)
        self._extract_runtime_patterns(genome, repo_path)
        self._extract_historical_tendencies(genome, repo_path)

        return genome

    def _extract_architecture(self, genome: RepositoryGenome, repo_path: Path):
        try:
            text = (repo_path / "pyproject.toml").read_text() if (repo_path / "pyproject.toml").exists() else ""
            src_dirs = []
            if "[tool" in text:
                src_dirs.append("src/" if (repo_path / "src").exists() else ".")

            for f in repo_path.rglob("__init__.py"):
                if not any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                    rel = f.relative_to(repo_path)
                    src_dirs.append(str(rel.parent) if str(rel.parent) != "." else "root")

            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.ARCHITECTURE,
                name="module_count",
                value=len(set(src_dirs)),
                compressed_representation=f"mc={len(set(src_dirs))}",
            ))

            has_src_layout = (repo_path / "src").exists()
            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.ARCHITECTURE,
                name="src_layout",
                value=has_src_layout,
                compressed_representation=f"src={int(has_src_layout)}",
            ))

            build_files = []
            for bf in ["pyproject.toml", "setup.py", "setup.cfg", "Cargo.toml",
                        "package.json", "go.mod", "CMakeLists.txt", "Makefile"]:
                if (repo_path / bf).exists():
                    build_files.append(bf)
            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.ARCHITECTURE,
                name="build_system",
                value=", ".join(build_files) if build_files else "unknown",
                compressed_representation=f"build={len(build_files)}",
            ))

        except Exception:
            pass

    def _extract_dependency(self, genome: RepositoryGenome, repo_path: Path):
        dep_graph: Dict[str, Set[str]] = {}
        for f in repo_path.rglob("*.py"):
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
                rel = str(f.relative_to(repo_path))
                dep_graph[rel] = deps
            except Exception:
                pass

        total_deps = sum(len(d) for d in dep_graph.values())
        avg_deps = total_deps / max(len(dep_graph), 1)

        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.DEPENDENCY,
            name="avg_deps_per_module",
            value=avg_deps,
            compressed_representation=f"ad={avg_deps:.2f}",
        ))

        fan_in: Counter = Counter()
        for src, deps in dep_graph.items():
            for dep in deps:
                fan_in[dep] += 1

        high_fan_in = sum(1 for v in fan_in.values() if v > 5)
        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.DEPENDENCY,
            name="high_fan_in_modules",
            value=high_fan_in,
            compressed_representation=f"hfi={high_fan_in}",
        ))

        cycles = self._detect_cycles(dep_graph)
        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.DEPENDENCY,
            name="dependency_cycles",
            value=len(cycles),
            compressed_representation=f"cyc={len(cycles)}",
        ))

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

    def _extract_topology(self, genome: RepositoryGenome, repo_path: Path):
        subsystems = set()
        file_count = 0
        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            file_count += 1
            rel = f.relative_to(repo_path)
            parts = rel.parts
            if len(parts) > 1:
                subsystems.add(parts[0])
            else:
                subsystems.add("root")

        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.SUBSYSTEM_TOPOLOGY,
            name="subsystem_count",
            value=len(subsystems),
            compressed_representation=f"sc={len(subsystems)}",
        ))
        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.SUBSYSTEM_TOPOLOGY,
            name="file_count",
            value=file_count,
            compressed_representation=f"fc={file_count}",
        ))
        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.SUBSYSTEM_TOPOLOGY,
            name="subsystem_balance",
            value=len(subsystems) / max(file_count, 1),
            compressed_representation=f"sb={len(subsystems)/max(file_count,1):.3f}",
        ))

        depth_distribution: Counter = Counter()
        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            rel = f.relative_to(repo_path)
            depth_distribution[len(rel.parts) - 1] += 1

        avg_depth = sum(
            d * c for d, c in depth_distribution.items()
        ) / max(sum(depth_distribution.values()), 1)

        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.SUBSYSTEM_TOPOLOGY,
            name="avg_nesting_depth",
            value=avg_depth,
            compressed_representation=f"nd={avg_depth:.2f}",
        ))

    def _extract_conventions(self, genome: RepositoryGenome, repo_path: Path):
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%s", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                msgs = result.stdout.splitlines()
                conventional = sum(
                    1 for m in msgs
                    if re.match(r"^(feat|fix|chore|docs|refactor|test|style|perf|ci|build)(\(.+\))?:", m)
                )
                conventional_ratio = conventional / max(len(msgs), 1)
                genome.add_locus(GenomeLocus(
                    segment=GenomeSegment.CONVENTIONS,
                    name="conventional_commits",
                    value=conventional_ratio,
                    compressed_representation=f"cc={conventional_ratio:.2f}",
                ))
        except Exception:
            pass

        if (repo_path / ".pre-commit-config.yaml").exists():
            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.CONVENTIONS,
                name="pre_commit",
                value=True,
                compressed_representation="pc=1",
            ))

        if (repo_path / ".editorconfig").exists():
            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.CONVENTIONS,
                name="editorconfig",
                value=True,
                compressed_representation="ec=1",
            ))

        if (repo_path / "ruff.toml").exists() or (repo_path / ".ruff.toml").exists():
            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.CONVENTIONS,
                name="linter",
                value="ruff",
                compressed_representation="lint=ruff",
            ))

    def _extract_invariants(self, genome: RepositoryGenome, repo_path: Path):
        try:
            test_dir = repo_path / "tests"
            if test_dir.exists():
                test_files = list(test_dir.rglob("*.py"))
                total_files = sum(
                    1 for _ in repo_path.rglob("*.py")
                    if not any(p.startswith(".") or p == "__pycache__" for p in _.parts)
                )
                test_ratio = len(test_files) / max(total_files, 1)
                genome.add_locus(GenomeLocus(
                    segment=GenomeSegment.INVARIANT_FAMILIES,
                    name="test_to_code_ratio",
                    value=test_ratio,
                    compressed_representation=f"tcr={test_ratio:.3f}",
                ))

                test_types = Counter()
                for tf in test_files:
                    text = tf.read_text(encoding="utf-8", errors="replace")
                    if "def test_" in text:
                        test_types["pytest"] += 1
                    if "unittest" in text:
                        test_types["unittest"] += 1
                    if "property" in text.lower() or "hypothesis" in text.lower():
                        test_types["property"] += 1
                genome.add_locus(GenomeLocus(
                    segment=GenomeSegment.INVARIANT_FAMILIES,
                    name="test_framework",
                    value=dict(test_types),
                    compressed_representation=f"tf={'/'.join(test_types.keys())}",
                ))
        except Exception:
            pass

    def _extract_coordination(self, genome: RepositoryGenome, repo_path: Path):
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%an", "-200"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                authors = result.stdout.splitlines()
                author_counts = Counter(authors)
                unique_authors = len(author_counts)
                genome.add_locus(GenomeLocus(
                    segment=GenomeSegment.COORDINATION,
                    name="unique_authors",
                    value=unique_authors,
                    compressed_representation=f"ua={unique_authors}",
                ))

                if unique_authors > 0:
                    top_share = author_counts.most_common(1)[0][1] / len(authors)
                    genome.add_locus(GenomeLocus(
                        segment=GenomeSegment.COORDINATION,
                        name="author_concentration",
                        value=top_share,
                        compressed_representation=f"ac={top_share:.2f}",
                    ))
        except Exception:
            pass

    def _extract_runtime_patterns(self, genome: RepositoryGenome, repo_path: Path):
        class_patterns: Counter = Counter()
        func_patterns: Counter = Counter()

        for f in repo_path.rglob("*.py"):
            if not f.is_file() or any(p.startswith(".") or p == "__pycache__" for p in f.parts):
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(text)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                        for base in bases:
                            class_patterns[base] += 1
                    elif isinstance(node, ast.FunctionDef):
                        if node.name.startswith("async "):
                            func_patterns["async"] += 1
                        if node.name.startswith("_"):
                            func_patterns["private"] += 1
                        has_decorators = len(node.decorator_list) > 0
                        if has_decorators:
                            func_patterns["decorated"] += 1
            except Exception:
                pass

        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.RUNTIME_PATTERNS,
            name="inheritance_patterns",
            value=dict(class_patterns.most_common(5)),
            compressed_representation=f"ip={sum(class_patterns.values())}",
        ))
        genome.add_locus(GenomeLocus(
            segment=GenomeSegment.RUNTIME_PATTERNS,
            name="function_patterns",
            value=dict(func_patterns),
            compressed_representation=f"fp={'/'.join(f'{k}={v}' for k,v in func_patterns.most_common(3))}",
        ))

    def _extract_historical_tendencies(self, genome: RepositoryGenome, repo_path: Path):
        try:
            result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "--format=%H|%an|%at|%s"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                return

            events = []
            for line in result.stdout.splitlines():
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    events.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "timestamp": float(parts[2]) if parts[2].isdigit() else 0,
                        "message": parts[3],
                    })

            if not events:
                return

            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.HISTORICAL_TENDENCIES,
                name="total_commits",
                value=len(events),
                compressed_representation=f"tc={len(events)}",
            ))

            if len(events) >= 2:
                span = events[-1]["timestamp"] - events[0]["timestamp"]
                days = max(span / 86400, 1)
                commit_rate = len(events) / days
                genome.add_locus(GenomeLocus(
                    segment=GenomeSegment.HISTORICAL_TENDENCIES,
                    name="commit_rate_per_day",
                    value=commit_rate,
                    compressed_representation=f"cr={commit_rate:.2f}",
                ))

            type_counts: Counter = Counter()
            for e in events:
                msg = e["message"].lower()
                if any(kw in msg for kw in ("fix", "bug", "hotfix")):
                    type_counts["fix"] += 1
                elif any(kw in msg for kw in ("feat", "feature", "add")):
                    type_counts["feature"] += 1
                elif any(kw in msg for kw in ("refactor", "restructure")):
                    type_counts["refactor"] += 1
                elif any(kw in msg for kw in ("test",)):
                    type_counts["test"] += 1
                elif any(kw in msg for kw in ("doc", "readme", "comment")):
                    type_counts["docs"] += 1
                else:
                    type_counts["other"] += 1

            genome.add_locus(GenomeLocus(
                segment=GenomeSegment.HISTORICAL_TENDENCIES,
                name="commit_type_distribution",
                value=dict(type_counts),
                compressed_representation=f"ctd={'/'.join(f'{k}={v}' for k,v in type_counts.most_common(4))}",
            ))

        except Exception:
            pass


class GenomeComparator:
    def compare(self, genome_a: RepositoryGenome, genome_b: RepositoryGenome) -> GenomeComparison:
        comparison = GenomeComparison(
            genome_a_id=genome_a.genome_id,
            genome_b_id=genome_b.genome_id,
        )

        seg_similarities = {}
        for segment in GenomeSegment:
            loci_a = genome_a.get_segment(segment)
            loci_b = genome_b.get_segment(segment)
            sim = self._segment_similarity(loci_a, loci_b)
            seg_similarities[segment.value] = sim

        comparison.segment_similarities = seg_similarities
        comparison.overall_similarity = sum(seg_similarities.values()) / max(len(seg_similarities), 1)

        for segment in GenomeSegment:
            loci_a = genome_a.get_segment(segment)
            loci_b = genome_b.get_segment(segment)
            divergent = self._find_divergent(loci_a, loci_b)
            convergent = self._find_convergent(loci_a, loci_b)
            comparison.divergent_loci.extend(divergent)
            comparison.convergent_loci.extend(convergent)

        return comparison

    def _segment_similarity(self, loci_a: List[GenomeLocus], loci_b: List[GenomeLocus]) -> float:
        if not loci_a and not loci_b:
            return 1.0
        if not loci_a or not loci_b:
            return 0.0

        names_a = {l.name: l.value for l in loci_a}
        names_b = {l.name: l.value for l in loci_b}

        common = set(names_a.keys()) & set(names_b.keys())
        if not common:
            return 0.0

        matches = 0
        for name in common:
            va = names_a[name]
            vb = names_b[name]
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                if va == 0 and vb == 0:
                    matches += 1
                elif max(abs(va), abs(vb)) > 0:
                    similarity = 1 - abs(va - vb) / max(abs(va), abs(vb), 1)
                    if similarity > 0.8:
                        matches += 1
            elif va == vb:
                matches += 1

        return matches / max(len(common), 1)

    def _find_divergent(self, loci_a: List[GenomeLocus], loci_b: List[GenomeLocus]) -> List[dict]:
        divergent = []
        names_b = {l.name: l for l in loci_b}
        for la in loci_a:
            if la.name in names_b:
                lb = names_b[la.name]
                if isinstance(la.value, (int, float)) and isinstance(lb.value, (int, float)):
                    if max(abs(la.value), abs(lb.value)) > 0:
                        diff = abs(la.value - lb.value) / max(abs(la.value), abs(lb.value), 1)
                        if diff > 0.3:
                            divergent.append({
                                "locus": la.name,
                                "segment": la.segment.value,
                                "value_a": la.value,
                                "value_b": lb.value,
                                "difference": diff,
                            })
        return divergent

    def _find_convergent(self, loci_a: List[GenomeLocus], loci_b: List[GenomeLocus]) -> List[dict]:
        convergent = []
        names_b = {l.name: l for l in loci_b}
        for la in loci_a:
            if la.name in names_b:
                lb = names_b[la.name]
                if isinstance(la.value, (int, float)) and isinstance(lb.value, (int, float)):
                    if max(abs(la.value), abs(lb.value)) > 0:
                        sim = 1 - abs(la.value - lb.value) / max(abs(la.value), abs(lb.value), 1)
                        if sim > 0.9:
                            convergent.append({
                                "locus": la.name,
                                "segment": la.segment.value,
                                "value_a": la.value,
                                "value_b": lb.value,
                                "similarity": sim,
                            })
        return convergent


class GenomePredictor:
    def __init__(self, genome: RepositoryGenome):
        self.genome = genome

    def predict_maintainability(self) -> Dict[str, Any]:
        loci = {l.name: l.value for l in self.genome.loci}
        score = 0.5

        if loci.get("subsystem_count", 0) > 3:
            score += 0.1
        if loci.get("dependency_cycles", 0) == 0:
            score += 0.15
        if loci.get("conventional_commits", 0) > 0.5:
            score += 0.1
        if loci.get("test_to_code_ratio", 0) > 0.3:
            score += 0.1
        if loci.get("author_concentration", 1) < 0.3:
            score += 0.05

        return {
            "score": min(1.0, score),
            "confidence": 0.6,
            "contributing_factors": {
                "modularization": loci.get("subsystem_count", 0) > 3,
                "acyclic_deps": loci.get("dependency_cycles", 0) == 0,
                "commit_convention": loci.get("conventional_commits", 0) > 0.5,
                "test_presence": loci.get("test_to_code_ratio", 0) > 0.3,
                "distributed_ownership": loci.get("author_concentration", 1) < 0.3,
            },
        }

    def predict_fragility(self) -> Dict[str, Any]:
        loci = {l.name: l.value for l in self.genome.loci}
        score = 0.0

        score += min(1.0, loci.get("high_fan_in_modules", 0) * 0.1)
        score += min(1.0, loci.get("dependency_cycles", 0) * 0.2)
        score += (1 - min(1.0, loci.get("test_to_code_ratio", 0)))

        author_conc = loci.get("author_concentration", 0)
        if author_conc > 0.5:
            score += 0.2

        return {
            "score": min(1.0, score),
            "confidence": 0.5,
            "risk_factors": {
                "high_fan_in": loci.get("high_fan_in_modules", 0),
                "dependency_cycles": loci.get("dependency_cycles", 0),
                "low_test_ratio": loci.get("test_to_code_ratio", 0) < 0.2,
                "bus_factor": author_conc > 0.5,
            },
        }

    def predict_scaling_behavior(self) -> Dict[str, Any]:
        loci = {l.name: l.value for l in self.genome.loci}
        score = 0.5

        if loci.get("subsystem_count", 0) > 5:
            score += 0.2
        if loci.get("dependency_cycles", 0) == 0:
            score += 0.15
        if loci.get("avg_deps_per_module", 0) < 3:
            score += 0.1
        if loci.get("build_system", "") != "unknown":
            score += 0.05

        return {
            "score": min(1.0, score),
            "confidence": 0.5,
            "scaling_capacity": "high" if score > 0.7 else "medium" if score > 0.4 else "low",
        }

    def predict_evolution_path(self) -> Dict[str, Any]:
        loci = {l.name: l.value for l in self.genome.loci}
        predictions = []

        if loci.get("dependency_cycles", 0) > 0:
            predictions.append({
                "type": "risk",
                "prediction": "Dependency cycles will cause increasing maintenance overhead",
                "timeframe": "3-6 months",
                "confidence": 0.7,
            })

        if loci.get("high_fan_in_modules", 0) > 3:
            predictions.append({
                "type": "risk",
                "prediction": "High fan-in modules will become refactoring bottlenecks",
                "timeframe": "6-12 months",
                "confidence": 0.6,
            })

        if loci.get("author_concentration", 0) > 0.5:
            predictions.append({
                "type": "risk",
                "prediction": "Bus factor of 1 poses continuity risk",
                "timeframe": "any time",
                "confidence": 0.8,
            })

        if loci.get("commit_rate_per_day", 0) > 5:
            predictions.append({
                "type": "opportunity",
                "prediction": "High commit velocity enables rapid iteration",
                "timeframe": "ongoing",
                "confidence": 0.7,
            })

        if not predictions:
            predictions.append({
                "type": "stable",
                "prediction": "No strong evolution signals detected",
                "timeframe": "6-12 months",
                "confidence": 0.5,
            })

        return {"predictions": predictions}


class GenomeClusterer:
    def cluster(self, genomes: List[RepositoryGenome], n_clusters: int = 3) -> Dict[str, Any]:
        if len(genomes) <= 1:
            return {"clusters": [{"genomes": [g.genome_id for g in genomes], "centroid": None}]}

        from collections import defaultdict

        comparator = GenomeComparator()
        similarity_matrix = {}
        for i, ga in enumerate(genomes):
            for j, gb in enumerate(genomes):
                if i < j:
                    comp = comparator.compare(ga, gb)
                    similarity_matrix[(i, j)] = comp.overall_similarity

        clusters = []
        assigned = set()
        for i in range(len(genomes)):
            if i in assigned:
                continue
            cluster = [i]
            assigned.add(i)
            for j in range(len(genomes)):
                if j not in assigned:
                    sim = similarity_matrix.get((min(i, j), max(i, j)), 0)
                    if sim > 0.7:
                        cluster.append(j)
                        assigned.add(j)
            clusters.append(cluster)

        result = []
        for cluster in clusters:
            centroid_idx = cluster[0]
            result.append({
                "size": len(cluster),
                "genomes": [genomes[idx].genome_id for idx in cluster],
                "centroid_sample": genomes[centroid_idx].to_compact()[:100],
                "internal_similarity": self._cluster_similarity(
                    [genomes[idx] for idx in cluster], similarity_matrix
                ),
            })

        return {"clusters": result, "cluster_count": len(result)}

    def _cluster_similarity(self, cluster_genomes: List[RepositoryGenome],
                             similarity_matrix: Dict[Tuple[int, int], float]) -> float:
        if len(cluster_genomes) <= 1:
            return 1.0
        sims = []
        for i in range(len(cluster_genomes)):
            for j in range(i + 1, len(cluster_genomes)):
                sims.append(similarity_matrix.get((i, j), 0))
        return sum(sims) / len(sims) if sims else 0.0
