from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict, Counter
import json
import math
import uuid


class SimilarityDimension(str, Enum):
    ARCHITECTURE = "architecture"
    INVARIANTS = "invariants"
    DEPENDENCY_STRUCTURE = "dependency_structure"
    RUNTIME_BEHAVIOR = "runtime_behavior"
    WORKFLOW_PATTERNS = "workflow_patterns"
    EVOLUTION_HISTORY = "evolution_history"
    FAILURE_MOTIFS = "failure_motifs"


@dataclass
class SimilarityScore:
    dimension: SimilarityDimension
    score: float
    confidence: float
    contributing_factors: List[str]

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "score": self.score,
            "confidence": self.confidence,
            "contributing_factors": self.contributing_factors,
        }


@dataclass
class RepoProfile:
    repo_id: str
    repo_name: str
    primary_language: str
    module_names: List[str]
    file_paths: List[str]
    import_structure: Dict[str, List[str]]
    dependencies: Dict[str, str]
    architecture_patterns: List[str]
    invariants: List[str]
    workflow_files: List[str]
    test_ratio: float

    def to_dict(self) -> Dict:
        return {
            "repo_id": self.repo_id,
            "repo_name": self.repo_name,
            "primary_language": self.primary_language,
            "module_names": self.module_names[:50],
            "dependencies": self.dependencies,
            "architecture_patterns": self.architecture_patterns,
            "invariants": self.invariants[:20],
            "test_ratio": self.test_ratio,
        }


@dataclass
class RepoCluster:
    cluster_id: str
    label: str
    size: int
    members: List[str]
    common_patterns: List[str]
    avg_similarity: float
    representative_repo: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "size": self.size,
            "members": self.members,
            "common_patterns": self.common_patterns,
            "avg_similarity": self.avg_similarity,
            "representative_repo": self.representative_repo,
        }


@dataclass
class ClusterVisualization:
    clusters: List[RepoCluster]
    similarity_matrix: List[List[float]]
    repo_names: List[str]
    dimensionality: int

    def to_dict(self) -> Dict:
        return {
            "clusters": [c.to_dict() for c in self.clusters],
            "similarity_matrix": [[round(v, 3) for v in row] for row in self.similarity_matrix],
            "repo_names": self.repo_names,
            "dimensionality": self.dimensionality,
        }

    def to_html(self) -> str:
        matrix_rows = ""
        for i, row in enumerate(self.similarity_matrix):
            cells = ""
            for j, val in enumerate(row):
                color = int(val * 255)
                bg = f"rgb({255 - color}, {color}, 50)"
                cells += f"<td style='background:{bg};color:{'white' if val > 0.5 else 'black'}'>{val:.2f}</td>"
            matrix_rows += f"<tr><td style='font-weight:bold'>{self.repo_names[i][:15]}</td>{cells}</tr>"

        cluster_info = ""
        for c in self.clusters:
            members = ", ".join(m[:12] for m in c.members[:5])
            cluster_info += f"<div style='margin:8px 0;padding:8px;background:#2a2a4e;border-radius:6px'><strong>{c.label}</strong> ({c.size} repos): {members}</div>"

        return f"""<!DOCTYPE html>
<html><head><title>Repository Similarity Matrix</title>
<style>body{{background:#1a1a2e;color:#eee;font-family:sans-serif;padding:40px}} table{{border-collapse:collapse}} td{{padding:4px 8px;text-align:center;border:1px solid #444;font-size:12px}}</style></head><body>
<h2>Repository Similarity Matrix</h2>
<p>{len(self.repo_names)} repositories, {len(self.clusters)} clusters</p>
<table>
<tr><th>Repo</th>{"".join(f'<th>{n[:8]}</th>' for n in self.repo_names)}</tr>
{matrix_rows}
</table>
<h3>Clusters</h3>
{cluster_info}
</body></html>"""


class RepositorySimilarityEngine:
    def __init__(self):
        self._profiles: Dict[str, RepoProfile] = {}
        self._similarity_cache: Dict[Tuple[str, str], float] = {}

    def add_profile(self, profile: RepoProfile):
        self._profiles[profile.repo_id] = profile

    def compute_similarity(self, repo_a_id: str, repo_b_id: str) -> List[SimilarityScore]:
        a = self._profiles.get(repo_a_id)
        b = self._profiles.get(repo_b_id)
        if not a or not b:
            return []

        cache_key = tuple(sorted([repo_a_id, repo_b_id]))
        if cache_key in self._similarity_cache:
            pass

        scores = [
            self._compare_architecture(a, b),
            self._compare_invariants(a, b),
            self._compare_dependency_structure(a, b),
            self._compare_workflows(a, b),
            self._compare_evolution(a, b),
        ]

        return scores

    def _compare_architecture(self, a: RepoProfile, b: RepoProfile) -> SimilarityScore:
        a_patterns = set(a.architecture_patterns)
        b_patterns = set(b.architecture_patterns)

        if not a_patterns and not b_patterns:
            return SimilarityScore(SimilarityDimension.ARCHITECTURE, 0.5, 0.3, ["No architecture data"])

        intersection = a_patterns & b_patterns
        union = a_patterns | b_patterns

        jaccard = len(intersection) / max(1, len(union)) if union else 0

        lang_similarity = 1.0 if a.primary_language == b.primary_language else 0.3

        score = jaccard * 0.7 + lang_similarity * 0.3

        return SimilarityScore(
            dimension=SimilarityDimension.ARCHITECTURE,
            score=round(score, 3),
            confidence=0.6 if union else 0.3,
            contributing_factors=[
                f"Shared patterns: {', '.join(list(intersection)[:3])}" if intersection else "No shared patterns",
                f"{'Same' if a.primary_language == b.primary_language else 'Different'} language",
            ],
        )

    def _compare_invariants(self, a: RepoProfile, b: RepoProfile) -> SimilarityScore:
        a_inv = set(a.invariants)
        b_inv = set(b.invariants)

        if not a_inv and not b_inv:
            return SimilarityScore(SimilarityDimension.INVARIANTS, 0.5, 0.2, ["No invariant data"])

        intersection = a_inv & b_inv
        union = a_inv | b_inv
        jaccard = len(intersection) / max(1, len(union)) if union else 0

        return SimilarityScore(
            dimension=SimilarityDimension.INVARIANTS,
            score=round(jaccard, 3),
            confidence=0.5,
            contributing_factors=[
                f"Shared invariants: {len(intersection)}",
                f"Unique to {a.repo_name}: {len(a_inv - b_inv)}",
            ],
        )

    def _compare_dependency_structure(self, a: RepoProfile, b: RepoProfile) -> SimilarityScore:
        a_deps = set(a.dependencies.keys())
        b_deps = set(b.dependencies.keys())

        if not a_deps and not b_deps:
            return SimilarityScore(SimilarityDimension.DEPENDENCY_STRUCTURE, 0.5, 0.3, ["No dependency data"])

        intersection = a_deps & b_deps
        union = a_deps | b_deps
        jaccard = len(intersection) / max(1, len(union)) if union else 0

        a_modules = set(a.module_names)
        b_modules = set(b.module_names)
        module_overlap = len(a_modules & b_modules) / max(1, len(a_modules | b_modules)) if (a_modules or b_modules) else 0

        score = jaccard * 0.6 + module_overlap * 0.4

        return SimilarityScore(
            dimension=SimilarityDimension.DEPENDENCY_STRUCTURE,
            score=round(score, 3),
            confidence=0.6,
            contributing_factors=[
                f"Shared deps: {len(intersection)}",
                f"Module overlap: {module_overlap:.0%}",
            ],
        )

    def _compare_workflows(self, a: RepoProfile, b: RepoProfile) -> SimilarityScore:
        a_wf = set(a.workflow_files)
        b_wf = set(b.workflow_files)

        if not a_wf and not b_wf:
            return SimilarityScore(SimilarityDimension.WORKFLOW_PATTERNS, 0.5, 0.2, ["No workflow data"])

        intersection = a_wf & b_wf
        union = a_wf | b_wf
        jaccard = len(intersection) / max(1, len(union)) if union else 0

        test_similarity = 1.0 - abs(a.test_ratio - b.test_ratio)

        score = jaccard * 0.5 + test_similarity * 0.5

        return SimilarityScore(
            dimension=SimilarityDimension.WORKFLOW_PATTERNS,
            score=round(score, 3),
            confidence=0.4,
            contributing_factors=[
                f"Workflow overlap: {len(intersection)} files",
                f"Test ratio: {a.test_ratio:.0%} vs {b.test_ratio:.0%}",
            ],
        )

    def _compare_evolution(self, a: RepoProfile, b: RepoProfile) -> SimilarityScore:
        return SimilarityScore(
            dimension=SimilarityDimension.EVOLUTION_HISTORY,
            score=0.5, confidence=0.3,
            contributing_factors=["Evolution history comparison requires git data"],
        )

    def overall_similarity(self, repo_a_id: str, repo_b_id: str) -> float:
        scores = self.compute_similarity(repo_a_id, repo_b_id)
        if not scores:
            return 0
        weighted = sum(s.score * s.confidence for s in scores)
        total_weight = sum(s.confidence for s in scores)
        return weighted / max(1, total_weight)

    def find_similar_repos(self, repo_id: str, top_n: int = 5) -> List[Dict]:
        results = []
        for other_id in self._profiles:
            if other_id == repo_id:
                continue
            similarity = self.overall_similarity(repo_id, other_id)
            profile = self._profiles.get(other_id)
            if profile:
                results.append({
                    "repo_id": other_id,
                    "repo_name": profile.repo_name,
                    "similarity": round(similarity, 3),
                })

        return sorted(results, key=lambda x: -x["similarity"])[:top_n]

    def cluster_repos(self, n_clusters: int = 3) -> List[RepoCluster]:
        repo_ids = list(self._profiles.keys())
        if len(repo_ids) < 2:
            return []

        n = len(repo_ids)
        sim_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if i == j:
                    sim_matrix[i][j] = 1.0
                else:
                    cache_key = tuple(sorted([repo_ids[i], repo_ids[j]]))
                    if cache_key not in self._similarity_cache:
                        self._similarity_cache[cache_key] = self.overall_similarity(repo_ids[i], repo_ids[j])
                    sim_matrix[i][j] = self._similarity_cache[cache_key]

        clusters = []
        assigned = set()
        actual_clusters = min(n_clusters, n)

        for ci in range(actual_clusters):
            if len(assigned) >= n:
                break

            best_seed = None
            best_avg_sim = -1
            for i in range(n):
                if i in assigned:
                    continue
                avg_sim = sum(sim_matrix[i][j] for j in range(n) if j != i) / max(1, n - 1)
                if avg_sim > best_avg_sim:
                    best_avg_sim = avg_sim
                    best_seed = i

            if best_seed is None:
                break

            cluster_members = [best_seed]
            assigned.add(best_seed)

            for j in range(n):
                if j not in assigned and sim_matrix[best_seed][j] > 0.4:
                    cluster_members.append(j)
                    assigned.add(j)

            member_names = [self._profiles[repo_ids[m]].repo_name for m in cluster_members]
            avg_sim = sum(sim_matrix[cluster_members[0]][m] for m in cluster_members[1:]) / max(1, len(cluster_members) - 1) if len(cluster_members) > 1 else 0

            common_patterns = self._find_common_patterns([repo_ids[m] for m in cluster_members])

            cluster = RepoCluster(
                cluster_id=f"cluster_{ci}",
                label=f"Cluster {ci}: {member_names[0][:20] if member_names else 'unknown'}",
                size=len(cluster_members),
                members=member_names,
                common_patterns=common_patterns,
                avg_similarity=round(avg_sim, 3),
                representative_repo=member_names[0] if member_names else None,
            )
            clusters.append(cluster)

        unassigned = [i for i in range(n) if i not in assigned]
        for i in unassigned:
            cluster = RepoCluster(
                cluster_id=f"cluster_outlier_{i}",
                label=f"Outlier: {self._profiles[repo_ids[i]].repo_name[:20]}",
                size=1,
                members=[self._profiles[repo_ids[i]].repo_name],
                common_patterns=[],
                avg_similarity=0,
                representative_repo=self._profiles[repo_ids[i]].repo_name,
            )
            clusters.append(cluster)

        return clusters

    def _find_common_patterns(self, repo_ids: List[str]) -> List[str]:
        all_patterns = Counter()
        for rid in repo_ids:
            profile = self._profiles.get(rid)
            if profile:
                for p in profile.architecture_patterns:
                    all_patterns[p] += 1
        return [p for p, count in all_patterns.most_common(5) if count > 1]

    def cluster_visualization(self, n_clusters: int = 3) -> ClusterVisualization:
        clusters = self.cluster_repos(n_clusters)
        names = [p.repo_name for p in self._profiles.values()]
        n = len(names)
        matrix = [[0.0] * n for _ in range(n)]
        ids = list(self._profiles.keys())
        for i in range(n):
            for j in range(n):
                matrix[i][j] = self.overall_similarity(ids[i], ids[j]) if i != j else 1.0

        return ClusterVisualization(
            clusters=clusters,
            similarity_matrix=matrix,
            repo_names=names,
            dimensionality=min(4, len(names)),
        )

    def save(self, path: str):
        data = {
            "profiles": {k: v.to_dict() for k, v in self._profiles.items()},
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> RepositorySimilarityEngine:
        with open(path) as f:
            data = json.load(f)
        engine = cls()
        for pid, pd in data.get("profiles", {}).items():
            engine._profiles[pid] = RepoProfile(
                repo_id=pid, repo_name=pd.get("repo_name", pid),
                primary_language=pd.get("primary_language", "unknown"),
                module_names=pd.get("module_names", []),
                file_paths=[], import_structure={},
                dependencies=pd.get("dependencies", {}),
                architecture_patterns=pd.get("architecture_patterns", []),
                invariants=pd.get("invariants", []),
                workflow_files=[], test_ratio=pd.get("test_ratio", 0),
            )
        return engine
