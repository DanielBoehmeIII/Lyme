from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import json
import uuid
import math


@dataclass
class SimilarityMatrix:
    repo_ids: List[str]
    matrix: List[List[float]]
    labels: Optional[List[str]] = None

    def to_dict(self) -> Dict:
        return {
            "repo_ids": self.repo_ids,
            "matrix": self.matrix,
            "labels": self.labels,
        }


@dataclass
class ClusterResult:
    cluster_id: str
    repo_ids: List[str]
    centroid: Dict
    intra_cluster_similarity: float
    inter_cluster_distance: float
    label: str = ""
    size: int = 0

    def to_dict(self) -> Dict:
        return {
            "cluster_id": self.cluster_id,
            "repo_ids": self.repo_ids,
            "centroid": self.centroid,
            "intra_cluster_similarity": self.intra_cluster_similarity,
            "inter_cluster_distance": self.inter_cluster_distance,
            "label": self.label,
            "size": self.size,
        }


class PatternClusterer:
    def __init__(self, n_clusters: int = 5, min_cluster_size: int = 2):
        self.n_clusters = n_clusters
        self.min_cluster_size = min_cluster_size
        self._clusters: List[ClusterResult] = []

    def cluster_fingerprints(self, fingerprints: List) -> List[ClusterResult]:
        vectors = self._fingerprints_to_vectors(fingerprints)
        similarity = self._compute_similarity_matrix(vectors)
        clusters = self._hierarchical_cluster(similarity, fingerprints)
        self._clusters = clusters
        return clusters

    def cluster_patterns(self, patterns: List) -> List[ClusterResult]:
        vectors = self._patterns_to_vectors(patterns)
        similarity = self._compute_similarity_matrix(vectors)
        clusters = self._hierarchical_cluster(similarity, patterns)
        self._clusters = clusters
        return clusters

    def _fingerprints_to_vectors(self, fingerprints: List) -> List[Tuple[str, Dict]]:
        vectors = []
        for fp in fingerprints:
            vec = {}
            deps = fp.dependency_signature
            for d in deps:
                vec[f"dep_{d.category}"] = vec.get(f"dep_{d.category}", 0) + d.prevalence

            struct = fp.structural_signature
            vec["depth"] = struct.depth / 10.0
            vec["breadth"] = struct.breadth / 20.0

            conv = fp.convention_signature
            for k, v in conv.items():
                vec[f"conv_{k}"] = v

            vec["sec_ratio"] = fp.security_sensitive_ratio
            vec["test_ratio"] = min(fp.test_to_code_ratio, 2.0) / 2.0

            errors = fp.components.get("error_handling", {})
            for k, v in errors.items():
                vec[f"err_{k}"] = min(v * 100, 1.0)

            complexity = fp.complexity_profile
            vec["avg_func_len"] = min(complexity.avg_function_length / 100.0, 1.0)

            vectors.append((fp.repo_id, vec))
        return vectors

    def _patterns_to_vectors(self, patterns: List) -> List[Tuple[str, Dict]]:
        vectors = []
        for p in patterns:
            vec: Dict[str, float] = {
                "occurrences": p.occurrences / 100.0,
                "transfer_rate": p.transfer_success_rate,
            }
            vec[f"cat_{p.category.value}"] = 1.0
            for tag in p.tags[:5]:
                vec[f"tag_{tag}"] = 1.0
            vectors.append((p.id, vec))
        return vectors

    def _cosine_similarity(self, a: Dict, b: Dict) -> float:
        all_keys = set(a.keys()) | set(b.keys())
        dot_product = 0.0
        norm_a = 0.0
        norm_b = 0.0
        for k in all_keys:
            va = a.get(k, 0.0)
            vb = b.get(k, 0.0)
            dot_product += va * vb
            norm_a += va * va
            norm_b += vb * vb
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (math.sqrt(norm_a) * math.sqrt(norm_b))

    def _euclidean_distance(self, a: Dict, b: Dict) -> float:
        all_keys = set(a.keys()) | set(b.keys())
        squared_diff = 0.0
        for k in all_keys:
            diff = a.get(k, 0.0) - b.get(k, 0.0)
            squared_diff += diff * diff
        return math.sqrt(squared_diff)

    def _compute_similarity_matrix(self, vectors: List[Tuple[str, Dict]]) -> SimilarityMatrix:
        repo_ids = [v[0] for v in vectors]
        vecs = [v[1] for v in vectors]
        n = len(vecs)
        matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                matrix[i][j] = self._cosine_similarity(vecs[i], vecs[j])
        return SimilarityMatrix(repo_ids=repo_ids, matrix=matrix)

    def _hierarchical_cluster(self, similarity: SimilarityMatrix, items: List) -> List[ClusterResult]:
        n = len(similarity.repo_ids)
        if n == 0:
            return []

        clusters = {i: [i] for i in range(n)}
        merge_history = []

        while len(clusters) > 1:
            best_i, best_j, best_sim = -1, -1, -1.0
            ids = list(clusters.keys())
            for idx_i in range(len(ids)):
                for idx_j in range(idx_i + 1, len(ids)):
                    sim = self._average_linkage(clusters[ids[idx_i]], clusters[ids[idx_j]], similarity)
                    if sim > best_sim:
                        best_sim = sim
                        best_i, best_j = ids[idx_i], ids[idx_j]

            if best_sim < 0.1:
                break

            new_key = max(clusters.keys()) + 1
            clusters[new_key] = clusters[best_i] + clusters[best_j]
            del clusters[best_i]
            del clusters[best_j]
            merge_history.append((best_i, best_j, new_key, best_sim))

        results = []
        for cid, member_indices in clusters.items():
            if len(member_indices) < self.min_cluster_size:
                for mi in member_indices:
                    repo_id = similarity.repo_ids[mi]
                    results.append(ClusterResult(
                        cluster_id=f"singleton_{uuid.uuid4().hex[:8]}",
                        repo_ids=[repo_id],
                        centroid={},
                        intra_cluster_similarity=1.0,
                        inter_cluster_distance=0.0,
                        label="Unclustered",
                        size=1,
                    ))
                continue

            member_ids = [similarity.repo_ids[i] for i in member_indices]
            member_vecs = [self._items_to_centroid(items[i]) for i in member_indices]
            centroid = self._compute_centroid(member_vecs)

            intra_sim = 0.0
            pairs = 0
            for i in range(len(member_indices)):
                for j in range(i + 1, len(member_indices)):
                    v1 = self._items_to_centroid(items[member_indices[i]])
                    v2 = self._items_to_centroid(items[member_indices[j]])
                    intra_sim += self._cosine_similarity(v1, v2)
                    pairs += 1
            intra_sim = intra_sim / pairs if pairs > 0 else 1.0

            if isinstance(items[0], tuple):
                item_id = items[member_indices[0]][0]
            else:
                item_id = getattr(items[member_indices[0]], 'id', str(member_indices[0]))

            results.append(ClusterResult(
                cluster_id=f"cluster_{uuid.uuid4().hex[:8]}",
                repo_ids=member_ids,
                centroid=centroid,
                intra_cluster_similarity=round(intra_sim, 3),
                inter_cluster_distance=round(1.0 - intra_sim, 3),
                label=f"Cluster {cid}",
                size=len(member_ids),
            ))

        results.sort(key=lambda r: -r.size)
        return results

    def _items_to_centroid(self, item) -> Dict:
        if isinstance(item, tuple):
            return item[1]
        if hasattr(item, 'signature'):
            return item.signature
        return {}

    def _compute_centroid(self, vecs: List[Dict]) -> Dict:
        if not vecs:
            return {}
        all_keys = set()
        for v in vecs:
            all_keys.update(v.keys())
        centroid = {}
        for k in all_keys:
            centroid[k] = sum(v.get(k, 0.0) for v in vecs) / len(vecs)
        return centroid

    def _average_linkage(self, indices_a: List[int], indices_b: List[int], sim: SimilarityMatrix) -> float:
        total = 0.0
        count = 0
        for i in indices_a:
            for j in indices_b:
                total += sim.matrix[i][j]
                count += 1
        return total / count if count > 0 else 0.0

    def label_clusters(self, fingerprints: List[ClusterResult]):
        archetype_map = {
            "web_app": ["fastapi", "flask", "django", "express", "routes", "controller"],
            "library": ["setup.py", "pyproject.toml", "__init__.py", "package.json"],
            "cli_tool": ["cli", "argparse", "click", "typer", "commander"],
            "data_science": ["numpy", "pandas", "jupyter", "notebook", "data"],
            "infrastructure": ["docker", "deploy", "kubernetes", "ci", "cd"],
            "mobile": ["swift", "kotlin", "android", "ios", "react-native"],
            "monorepo": ["packages/", "apps/", "libs/", "modules/"],
        }

        for cluster in self._clusters:
            max_score = 0
            best_label = "unknown"
            for archetype, keywords in archetype_map.items():
                score = 0
                for kw in keywords:
                    for rid in cluster.repo_ids:
                        if kw in rid.lower():
                            score += 1
                if score > max_score:
                    max_score = score
                    best_label = archetype
            cluster.label = best_label

        return self._clusters

    @property
    def clusters(self) -> List[ClusterResult]:
        return self._clusters

    def save(self, path: Path):
        data = [c.to_dict() for c in self._clusters]
        path.write_text(json.dumps(data, indent=2))

    def load(self, path: Path) -> List[ClusterResult]:
        data = json.loads(path.read_text())
        self._clusters = [ClusterResult(**d) for d in data]
        return self._clusters
