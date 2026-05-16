from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import math
import uuid
from collections import defaultdict, Counter


class DependencyType(str, Enum):
    DIRECT = "direct"
    TRANSITIVE = "transitive"
    PEER = "peer"
    OPTIONAL = "optional"
    DEV = "dev"
    RUNTIME = "runtime"
    BUILD = "build"


class EcosystemPhase(str, Enum):
    EMBRYONIC = "embryonic"
    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    DOMINANT = "dominant"
    FRAGMENTING = "fragmenting"
    DECLINING = "declining"
    NICHE = "niche"


@dataclass
class LibraryNode:
    id: str
    name: str
    version: str
    ecosystem: str
    category: str = ""
    latest_version: str = ""
    release_count: int = 0
    release_frequency: float = 0.0
    adoption_rate: float = 0.0
    abandonment_risk: float = 0.0
    centrality: float = 0.0
    community_size: int = 0
    phase: EcosystemPhase = EcosystemPhase.EMERGING
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "ecosystem": self.ecosystem,
            "category": self.category,
            "latest_version": self.latest_version,
            "release_count": self.release_count,
            "release_frequency": self.release_frequency,
            "adoption_rate": self.adoption_rate,
            "abandonment_risk": self.abandonment_risk,
            "centrality": self.centrality,
            "phase": self.phase.value,
            "metadata": self.metadata,
        }


@dataclass
class DependencyEdge:
    id: str
    source_id: str
    target_id: str
    dep_type: DependencyType
    version_constraint: str = ""
    weight: float = 1.0
    is_optional: bool = False
    is_conflicting: bool = False
    conflict_description: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "dep_type": self.dep_type.value,
            "version_constraint": self.version_constraint,
            "weight": self.weight,
            "is_optional": self.is_optional,
            "is_conflicting": self.is_conflicting,
            "confidence": self.confidence,
        }


@dataclass
class TransitiveChain:
    chain: List[str]
    depth: int
    total_weight: float
    risk_score: float
    is_circular: bool = False
    bottlenecks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "chain": self.chain,
            "depth": self.depth,
            "total_weight": self.total_weight,
            "risk_score": self.risk_score,
            "is_circular": self.is_circular,
            "bottlenecks": self.bottlenecks,
        }


@dataclass
class EcosystemSnapshot:
    timestamp: float
    libraries: Dict[str, LibraryNode]
    edges: Dict[str, DependencyEdge]
    stability_score: float
    fragility_score: float
    diversity_score: float
    dominant_frameworks: List[str]
    emerging_trends: List[str]
    risk_hotspots: List[str]

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "libraries": {k: v.to_dict() for k, v in self.libraries.items()},
            "stability_score": self.stability_score,
            "fragility_score": self.fragility_score,
            "diversity_score": self.diversity_score,
            "dominant_frameworks": self.dominant_frameworks,
            "emerging_trends": self.emerging_trends,
            "risk_hotspots": self.risk_hotspots,
        }


class DependencyGraphEngine:
    def __init__(self):
        self._libraries: Dict[str, LibraryNode] = {}
        self._edges: Dict[str, DependencyEdge] = {}
        self._adjacency: Dict[str, Dict[str, List[str]]] = {}
        self._reverse_adj: Dict[str, Dict[str, List[str]]] = {}
        self._snapshots: List[EcosystemSnapshot] = []

    def add_library(self, lib: LibraryNode):
        self._libraries[lib.id] = lib
        if lib.id not in self._adjacency:
            self._adjacency[lib.id] = {}
            self._reverse_adj[lib.id] = {}

    def add_dependency(self, edge: DependencyEdge):
        self._edges[edge.id] = edge
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = {}
        if edge.target_id not in self._reverse_adj:
            self._reverse_adj[edge.target_id] = {}
        t = edge.dep_type.value
        if t not in self._adjacency[edge.source_id]:
            self._adjacency[edge.source_id][t] = []
        if t not in self._reverse_adj[edge.target_id]:
            self._reverse_adj[edge.target_id][t] = []
        self._adjacency[edge.source_id][t].append(edge.target_id)
        self._reverse_adj[edge.target_id][t].append(edge.source_id)

    def get_library(self, lib_id: str) -> Optional[LibraryNode]:
        return self._libraries.get(lib_id)

    def get_direct_dependencies(self, lib_id: str) -> List[LibraryNode]:
        deps = []
        adj = self._adjacency.get(lib_id, {})
        for targets in adj.values():
            for t in targets:
                if t in self._libraries:
                    deps.append(self._libraries[t])
        return deps

    def get_dependents(self, lib_id: str) -> List[LibraryNode]:
        deps = []
        radj = self._reverse_adj.get(lib_id, {})
        for sources in radj.values():
            for s in sources:
                if s in self._libraries:
                    deps.append(self._libraries[s])
        return deps

    def compute_transitive_dependencies(self, lib_id: str, max_depth: int = 10) -> List[TransitiveChain]:
        chains = []
        visited = set()

        def dfs(current: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current != lib_id and current in path[:-1]:
                chains.append(TransitiveChain(
                    chain=list(path), depth=depth,
                    total_weight=0.0, risk_score=0.5,
                    is_circular=True,
                ))
                return
            if current in visited:
                return
            visited.add(current)
            adj = self._adjacency.get(current, {})
            for targets in adj.values():
                for nxt in targets:
                    if nxt not in visited:
                        path.append(nxt)
                        dfs(nxt, path, depth + 1)
                        path.pop()
            visited.remove(current)

        dfs(lib_id, [lib_id], 0)

        result = []
        for chain in chains:
            if chain.is_circular:
                continue
            total_weight = 1.0
            bottlenecks = []
            for i in range(len(chain.chain) - 1):
                src, tgt = chain.chain[i], chain.chain[i + 1]
                for e in self._edges.values():
                    if e.source_id == src and e.target_id == tgt:
                        total_weight *= e.weight
                        break
                dep_count = len(self.get_dependents(tgt))
                if dep_count > 5:
                    bottlenecks.append(tgt)
            risk = 1.0 - (total_weight / max(1, len(chain.chain)))
            result.append(TransitiveChain(
                chain=chain.chain, depth=len(chain.chain) - 1,
                total_weight=round(total_weight, 3),
                risk_score=round(risk, 3),
                bottlenecks=bottlenecks,
            ))

        return sorted(result, key=lambda x: -x.risk_score)[:50]

    def find_circular_dependencies(self) -> List[List[str]]:
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            adj = self._adjacency.get(node, {})
            for targets in adj.values():
                for neighbor in targets:
                    if neighbor not in visited:
                        dfs(neighbor, path + [neighbor])
                    elif neighbor in rec_stack:
                        cycle_start = path.index(neighbor) if neighbor in path else 0
                        cycles.append(path[cycle_start:] + [neighbor])
            rec_stack.remove(node)

        for lib_id in self._libraries:
            if lib_id not in visited:
                dfs(lib_id, [lib_id])

        return cycles

    def compute_ecosystem_metrics(self) -> Dict:
        total = len(self._libraries)
        if total == 0:
            return {}

        edge_count = len(self._edges)
        density = (2 * edge_count) / max(1, total * (total - 1))

        in_degrees = Counter()
        out_degrees = Counter()
        for e in self._edges.values():
            in_degrees[e.target_id] += 1
            out_degrees[e.source_id] += 1

        max_centrality = max(in_degrees.values()) if in_degrees else 0
        central_nodes = [lid for lid, deg in in_degrees.items() if deg == max_centrality]

        phases = Counter(l.phase.value for l in self._libraries.values())
        diversity = len(set(l.category for l in self._libraries.values()))

        cycles = self.find_circular_dependencies()

        return {
            "total_libraries": total,
            "total_edges": edge_count,
            "density": round(density, 4),
            "avg_in_degree": round(sum(in_degrees.values()) / max(1, total), 2),
            "avg_out_degree": round(sum(out_degrees.values()) / max(1, total), 2),
            "max_centrality": max_centrality,
            "central_nodes": [self._libraries.get(n, n).name if isinstance(n, str) else n for n in central_nodes],
            "phase_distribution": dict(phases),
            "category_diversity": diversity,
            "circular_dependency_count": len(cycles),
            "circular_dependencies": [[self._libraries.get(n, n).name for n in c] for c in cycles[:5]],
        }

    def compute_centrality(self) -> Dict[str, float]:
        centrality = {}
        for lib_id in self._libraries:
            deps = len(self.get_direct_dependencies(lib_id))
            dependents = len(self.get_dependents(lib_id))
            centrality[lib_id] = deps + dependents * 2

        max_c = max(centrality.values()) if centrality else 1
        return {k: round(v / max_c, 4) for k, v in centrality.items()}

    def detect_ecosystem_fragmentation(self) -> List[Dict]:
        communities = []
        assigned = set()
        for lib_id in list(self._libraries.keys())[:100]:
            if lib_id in assigned:
                continue
            community = set()
            stack = [lib_id]
            while stack:
                cur = stack.pop()
                if cur in assigned:
                    continue
                assigned.add(cur)
                community.add(cur)
                neighbors = set()
                adj = self._adjacency.get(cur, {})
                for targets in adj.values():
                    neighbors.update(targets)
                radj = self._reverse_adj.get(cur, {})
                for sources in radj.values():
                    neighbors.update(sources)
                stack.extend(n for n in neighbors if n not in assigned)
            communities.append(list(community))

        fragments = []
        for comm in communities:
            if len(comm) < 3:
                continue
            members = [self._libraries[c] for c in comm if c in self._libraries]
            avg_centrality = sum(m.centrality for m in members) / len(members) if members else 0
            fragments.append({
                "size": len(comm),
                "members": [m.name for m in members[:10]],
                "avg_centrality": round(avg_centrality, 3),
                "is_isolated": len(comm) == 1,
            })

        return sorted(fragments, key=lambda x: -x["size"])

    def analyze_dominance(self) -> Dict[str, float]:
        dep_counts = Counter()
        for e in self._edges.values():
            dep_counts[e.target_id] += 1
        total = sum(dep_counts.values()) if dep_counts else 1
        dominance = {}
        for lib_id, count in dep_counts.most_common(20):
            lib = self._libraries.get(lib_id)
            if lib:
                dominance[lib.name] = round(count / total, 4)
        return dominance

    def compute_lock_in_risk(self) -> List[Dict]:
        risks = []
        for lib_id, lib in self._libraries.items():
            dependents = len(self.get_dependents(lib_id))
            if dependents < 3:
                continue
            alternatives = sum(1 for e in self._edges.values()
                               if e.target_id == lib_id and e.dep_type == DependencyType.OPTIONAL)
            risk = {
                "library": lib.name,
                "dependents": dependents,
                "alternatives": alternatives,
                "lock_in_score": round(dependents / max(1, dependents + alternatives), 3),
                "phase": lib.phase.value,
            }
            risks.append(risk)
        return sorted(risks, key=lambda x: -x["lock_in_score"])[:20]

    def detect_emerging_standards(self) -> List[Dict]:
        standards = []
        for lib_id, lib in self._libraries.items():
            if lib.phase in (EcosystemPhase.EMERGING, EcosystemPhase.GROWING):
                growth_rate = lib.adoption_rate
                if growth_rate > 0.3:
                    standards.append({
                        "library": lib.name,
                        "growth_rate": growth_rate,
                        "phase": lib.phase.value,
                        "centrality": lib.centrality,
                        "community_size": lib.community_size,
                    })
        return sorted(standards, key=lambda x: -x["growth_rate"])[:10]

    def detect_ecosystem_decay(self) -> List[Dict]:
        decaying = []
        for lib_id, lib in self._libraries.items():
            if lib.phase == EcosystemPhase.DECLINING:
                decaying.append({
                    "library": lib.name,
                    "abandonment_risk": lib.abandonment_risk,
                    "release_frequency": lib.release_frequency,
                    "dependents": len(self.get_dependents(lib_id)),
                    "recommended_replacement": lib.metadata.get("replacement", ""),
                })
            elif lib.abandonment_risk > 0.7:
                decaying.append({
                    "library": lib.name,
                    "abandonment_risk": lib.abandonment_risk,
                    "release_frequency": lib.release_frequency,
                    "phase": lib.phase.value,
                    "warning": "High abandonment risk detected",
                })
        return sorted(decaying, key=lambda x: -x.get("abandonment_risk", 0))[:15]

    def compute_brittle_chains(self) -> List[TransitiveChain]:
        all_chains = []
        for lib_id in list(self._libraries.keys())[:30]:
            chains = self.compute_transitive_dependencies(lib_id, max_depth=5)
            all_chains.extend(chains)
        return sorted(all_chains, key=lambda x: -x.risk_score)[:20]

    def analyze_migration_waves(self) -> List[Dict]:
        waves = []
        for e in self._edges.values():
            if e.dep_type == DependencyType.OPTIONAL and e.weight < 0.3:
                src = self._libraries.get(e.source_id)
                tgt = self._libraries.get(e.target_id)
                if src and tgt:
                    waves.append({
                        "from": src.name,
                        "to": tgt.name,
                        "confidence": e.confidence,
                        "ecosystem": src.ecosystem,
                    })
        return waves

    def take_snapshot(self, timestamp: float) -> EcosystemSnapshot:
        metrics = self.compute_ecosystem_metrics()
        decay = self.detect_ecosystem_decay()
        snapshot = EcosystemSnapshot(
            timestamp=timestamp,
            libraries=dict(self._libraries),
            edges=dict(self._edges),
            stability_score=1.0 - metrics.get("density", 0),
            fragility_score=len(decay) / max(1, len(self._libraries)),
            diversity_score=metrics.get("category_diversity", 0) / max(1, len(self._libraries)),
            dominant_frameworks=[m["library"] for m in self.analyze_dominance().items()][:5],
            emerging_trends=[s["library"] for s in self.detect_emerging_standards()],
            risk_hotspots=[d["library"] for d in decay[:5]],
        )
        self._snapshots.append(snapshot)
        return snapshot

    def temporal_comparison(self, snapshot_a: EcosystemSnapshot, snapshot_b: EcosystemSnapshot) -> Dict:
        delta = {
            "stability_change": round(snapshot_b.stability_score - snapshot_a.stability_score, 3),
            "fragility_change": round(snapshot_b.fragility_score - snapshot_a.fragility_score, 3),
            "diversity_change": round(snapshot_b.diversity_score - snapshot_a.diversity_score, 3),
            "new_dominant": list(set(snapshot_b.dominant_frameworks) - set(snapshot_a.dominant_frameworks)),
            "lost_dominant": list(set(snapshot_a.dominant_frameworks) - set(snapshot_b.dominant_frameworks)),
            "new_emerging": list(set(snapshot_b.emerging_trends) - set(snapshot_a.emerging_trends)),
            "new_risks": list(set(snapshot_b.risk_hotspots) - set(snapshot_a.risk_hotspots)),
        }
        return delta

    def propagate_vulnerability(self, source_id: str) -> List[Dict]:
        affected = []
        visited = set()
        queue = [(source_id, 0)]

        while queue:
            current, depth = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            dependents = self.get_dependents(current)
            for dep in dependents:
                affected.append({
                    "library": dep.name,
                    "depth": depth + 1,
                    "path_from_source": [source_id, dep.id],
                })
                queue.append((dep.id, depth + 1))

        return affected

    def save(self, path: str):
        data = {
            "libraries": {k: v.to_dict() for k, v in self._libraries.items()},
            "edges": {k: v.to_dict() for k, v in self._edges.items()},
            "snapshots": [s.to_dict() for s in self._snapshots],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> DependencyGraphEngine:
        with open(path) as f:
            data = json.load(f)
        engine = cls()
        for ld in data.get("libraries", {}).values():
            lib = LibraryNode(
                id=ld["id"], name=ld["name"], version=ld.get("version", ""),
                ecosystem=ld.get("ecosystem", ""),
                latest_version=ld.get("latest_version", ""),
                release_count=ld.get("release_count", 0),
                release_frequency=ld.get("release_frequency", 0.0),
                adoption_rate=ld.get("adoption_rate", 0.0),
                abandonment_risk=ld.get("abandonment_risk", 0.0),
                centrality=ld.get("centrality", 0.0),
                phase=EcosystemPhase(ld.get("phase", "emerging")),
                category=ld.get("category", ""),
                metadata=ld.get("metadata", {}),
            )
            engine.add_library(lib)
        for ed in data.get("edges", {}).values():
            edge = DependencyEdge(
                id=ed["id"], source_id=ed["source_id"], target_id=ed["target_id"],
                dep_type=DependencyType(ed.get("dep_type", "direct")),
                version_constraint=ed.get("version_constraint", ""),
                weight=ed.get("weight", 1.0),
                is_optional=ed.get("is_optional", False),
                is_conflicting=ed.get("is_conflicting", False),
                confidence=ed.get("confidence", 1.0),
            )
            engine.add_dependency(edge)
        return engine

    @property
    def libraries(self) -> List[LibraryNode]:
        return list(self._libraries.values())

    @property
    def library_count(self) -> int:
        return len(self._libraries)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def snapshots(self) -> List[EcosystemSnapshot]:
        return list(self._snapshots)
