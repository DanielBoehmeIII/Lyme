from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CausalRelationType(str, Enum):
    IMPORT = "import"
    CO_CHANGE = "co_change"
    DATA_FLOW = "data_flow"
    API_CALL = "api_call"
    SHARED_STATE = "shared_state"
    EVENT_PROPAGATION = "event_propagation"
    CONTRACT_DEPENDENCY = "contract_dependency"
    TEST_COUPLING = "test_coupling"
    TEMPORAL_ORDERING = "temporal_ordering"
    INHERITANCE = "inheritance"
    CONFIG_DEPENDENCY = "config_dependency"
    RUNTIME_DEPENDENCY = "runtime_dependency"
    FAILURE_AMPLIFICATION = "failure_amplification"
    SYNCHRONIZATION = "synchronization"
    ARCHITECTURAL_PRESSURE = "architectural_pressure"
    STATE_MUTATION = "state_mutation"
    SEMANTIC_SIMILARITY = "semantic_similarity"


class NodeType(str, Enum):
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SUBSYSTEM = "subsystem"
    API = "api"
    DATABASE = "database"
    CONFIG = "config"
    TEST = "test"
    INTERFACE = "interface"
    DEPENDENCY = "dependency"  # external package


@dataclass
class CausalNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    node_type: NodeType = NodeType.FILE
    file_path: str = ""
    subsystem: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    risk_score: float = 0.0
    change_frequency: float = 0.0
    complexity: float = 0.0
    failure_history: List[Dict[str, Any]] = field(default_factory=list)
    import_count: int = 0
    dependents_count: int = 0
    first_seen: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "file_path": self.file_path,
            "subsystem": self.subsystem,
            "metadata": self.metadata,
            "risk_score": self.risk_score,
            "change_frequency": self.change_frequency,
            "complexity": self.complexity,
            "failure_history": self.failure_history,
            "import_count": self.import_count,
            "dependents_count": self.dependents_count,
            "first_seen": self.first_seen,
            "last_modified": self.last_modified,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CausalNode:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CausalEdge:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_id: str = ""
    target_id: str = ""
    relation_type: CausalRelationType = CausalRelationType.IMPORT
    weight: float = 1.0
    confidence: float = 1.0
    evidence_sources: List[str] = field(default_factory=list)
    temporal_ordering: str = ""  # "source_before_target", "concurrent", "target_before_source"
    latency_ms: Optional[float] = None
    frequency: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    first_observed: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation_type": self.relation_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "evidence_sources": self.evidence_sources,
            "temporal_ordering": self.temporal_ordering,
            "latency_ms": self.latency_ms,
            "frequency": self.frequency,
            "metadata": self.metadata,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CausalEdge:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class InfluencePath:
    nodes: List[CausalNode] = field(default_factory=list)
    edges: List[CausalEdge] = field(default_factory=list)
    total_confidence: float = 0.0
    propagation_delay_ms: float = 0.0
    risk_score: float = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "total_confidence": self.total_confidence,
            "propagation_delay_ms": self.propagation_delay_ms,
            "risk_score": self.risk_score,
            "description": self.description,
        }


class CausalGraph:
    def __init__(self, name: str = "", repo_path: str = ""):
        self.name = name
        self.repo_path = repo_path
        self._nodes: Dict[str, CausalNode] = {}
        self._edges: Dict[str, CausalEdge] = {}
        self._adjacency: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._reverse_adjacency: Dict[str, Dict[str, List[str]]] = defaultdict(lambda: defaultdict(list))
        self._type_index: Dict[CausalRelationType, List[str]] = defaultdict(list)
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.metadata: Dict[str, Any] = field(default_factory=dict)

    def add_node(self, node: CausalNode) -> str:
        self._nodes[node.id] = node
        return node.id

    def add_edge(self, edge: CausalEdge) -> str:
        self._edges[edge.id] = edge
        self._adjacency[edge.source_id][edge.relation_type.value].append(edge.id)
        self._reverse_adjacency[edge.target_id][edge.relation_type.value].append(edge.id)
        self._type_index[edge.relation_type].append(edge.id)

        source = self._nodes.get(edge.source_id)
        target = self._nodes.get(edge.target_id)
        if source:
            source.dependents_count = len(self._reverse_adjacency.get(source.id, {}))
        if target:
            target.dependents_count = len(self._reverse_adjacency.get(target.id, {}))

        self.updated_at = time.time()
        return edge.id

    def get_node(self, node_id: str) -> Optional[CausalNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[CausalEdge]:
        return self._edges.get(edge_id)

    def find_node_by_name(self, name: str) -> Optional[CausalNode]:
        for node in self._nodes.values():
            if node.name == name or node.file_path == name:
                return node
        return None

    def get_outgoing_edges(self, node_id: str, relation_type: Optional[str] = None) -> List[CausalEdge]:
        if relation_type:
            edge_ids = self._adjacency[node_id].get(relation_type, [])
        else:
            edge_ids = []
            for edges in self._adjacency[node_id].values():
                edge_ids.extend(edges)
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_incoming_edges(self, node_id: str, relation_type: Optional[str] = None) -> List[CausalEdge]:
        if relation_type:
            edge_ids = self._reverse_adjacency[node_id].get(relation_type, [])
        else:
            edge_ids = []
            for edges in self._reverse_adjacency[node_id].values():
                edge_ids.extend(edges)
        return [self._edges[eid] for eid in edge_ids if eid in self._edges]

    def get_downstream(self, node_id: str, max_depth: int = 5) -> List[InfluencePath]:
        paths: List[InfluencePath] = []
        visited: Set[str] = set()

        def dfs(current_id: str, path_nodes: List[CausalNode], path_edges: List[CausalEdge], depth: int):
            if depth > max_depth:
                return
            if current_id in visited:
                return
            visited.add(current_id)

            current_node = self._nodes.get(current_id)
            if current_node and depth > 0:
                path_nodes.append(current_node)

            outgoing = self.get_outgoing_edges(current_id)
            if not outgoing and path_nodes:
                ip = InfluencePath(
                    nodes=[self._nodes[node_id]] + path_nodes if node_id != current_id else path_nodes,
                    edges=list(path_edges),
                    total_confidence=min(e.confidence for e in path_edges) if path_edges else 1.0,
                    propagation_delay_ms=sum((e.latency_ms or 0) for e in path_edges),
                    risk_score=sum(n.risk_score for n in path_nodes) / max(len(path_nodes), 1),
                )
                paths.append(ip)

            for edge in outgoing:
                target = self._nodes.get(edge.target_id)
                if target and target.id not in visited:
                    path_edges.append(edge)
                    path_nodes.append(target)
                    dfs(edge.target_id, path_nodes, path_edges, depth + 1)
                    path_edges.pop()
                    path_nodes.pop()

            visited.discard(current_id)

        dfs(node_id, [], [], 0)
        return sorted(paths, key=lambda p: p.risk_score, reverse=True)[:20]

    def get_upstream(self, node_id: str, max_depth: int = 5) -> List[InfluencePath]:
        paths: List[InfluencePath] = []
        visited: Set[str] = set()

        def dfs(current_id: str, path_nodes: List[CausalNode], path_edges: List[CausalEdge], depth: int):
            if depth > max_depth:
                return
            if current_id in visited:
                return
            visited.add(current_id)

            incoming = self.get_incoming_edges(current_id)
            if not incoming and path_nodes:
                ip = InfluencePath(
                    nodes=path_nodes + [self._nodes[node_id]],
                    edges=list(path_edges),
                    total_confidence=min(e.confidence for e in path_edges) if path_edges else 1.0,
                )
                paths.append(ip)

            for edge in incoming:
                source = self._nodes.get(edge.source_id)
                if source and source.id not in visited:
                    path_edges.append(edge)
                    path_nodes.append(source)
                    dfs(edge.source_id, path_nodes, path_edges, depth + 1)
                    path_edges.pop()
                    path_nodes.pop()

            visited.discard(current_id)

        dfs(node_id, [], [], 0)
        return sorted(paths, key=lambda p: len(p.nodes), reverse=True)[:20]

    def find_amplification_zones(self, min_risk: float = 0.5) -> List[Dict[str, Any]]:
        zones = []
        for node in self._nodes.values():
            if node.risk_score >= min_risk:
                downstream = self.get_downstream(node.id, max_depth=3)
                downstream_risk = sum(p.risk_score for p in downstream) / max(len(downstream), 1)
                amplification = downstream_risk - node.risk_score
                if amplification > 0.1:
                    zones.append({
                        "node": node.to_dict(),
                        "downstream_count": len(downstream),
                        "amplification_score": amplification,
                        "downstream_risk": downstream_risk,
                    })
        return sorted(zones, key=lambda z: -z["amplification_score"])[:20]

    def find_architectural_pressure_points(self) -> List[Dict[str, Any]]:
        points = []
        for node in self._nodes.values():
            outgoing = self.get_outgoing_edges(node.id)
            incoming = self.get_incoming_edges(node.id)
            pressure = (len(incoming) * 2 + len(outgoing)) * node.risk_score
            if pressure > 1.0:
                points.append({
                    "node": node.to_dict(),
                    "incoming_count": len(incoming),
                    "outgoing_count": len(outgoing),
                    "pressure_score": pressure,
                })
        return sorted(points, key=lambda p: -p["pressure_score"])[:20]

    def find_synchronization_surfaces(self) -> List[Dict[str, Any]]:
        surfaces = []
        edge_types_under_edges = defaultdict(list)
        for edge in self._edges.values():
            key = frozenset({edge.source_id, edge.target_id})
            edge_types_under_edges[key].append(edge)

        for node_pair, edges in edge_types_under_edges.items():
            if len(edges) >= 3:
                types = [e.relation_type.value for e in edges]
                avg_confidence = sum(e.confidence for e in edges) / len(edges)
                surfaces.append({
                    "node_a": self._nodes.get(edges[0].source_id).to_dict() if self._nodes.get(edges[0].source_id) else {},
                    "node_b": self._nodes.get(edges[0].target_id).to_dict() if self._nodes.get(edges[0].target_id) else {},
                    "relation_types": types,
                    "edge_count": len(edges),
                    "avg_confidence": avg_confidence,
                })
        return sorted(surfaces, key=lambda s: -s["edge_count"])[:20]

    def find_hidden_dependencies(self, min_confidence: float = 0.3) -> List[Dict[str, Any]]:
        hiddens = []
        for edge in self._edges.values():
            if edge.relation_type not in (CausalRelationType.IMPORT, CausalRelationType.API_CALL):
                source = self._nodes.get(edge.source_id)
                target = self._nodes.get(edge.target_id)
                if source and target and edge.confidence >= min_confidence:
                    hiddens.append({
                        "source": source.name,
                        "source_path": source.file_path,
                        "target": target.name,
                        "target_path": target.file_path,
                        "relation_type": edge.relation_type.value,
                        "confidence": edge.confidence,
                        "evidence": edge.evidence_sources,
                    })
        return sorted(hiddens, key=lambda h: -h["confidence"])

    def estimate_breakage_risk(self, node_id: str) -> Dict[str, Any]:
        node = self._nodes.get(node_id)
        if not node:
            return {"error": "node not found"}

        downstream = self.get_downstream(node_id, max_depth=3)
        upstream = self.get_upstream(node_id, max_depth=2)

        affected_nodes = set()
        for path in downstream:
            for n in path.nodes:
                if n.id != node_id:
                    affected_nodes.add(n.id)

        total_risk = node.risk_score
        propagation_risk = sum(p.risk_score for p in downstream) / max(len(downstream), 1) if downstream else 0
        hidden_deps = self.find_hidden_dependencies()
        relevant_hidden = [
            h for h in hidden_deps
            if h["source_path"] == node.file_path or h["target_path"] == node.file_path
        ]

        return {
            "node": node.to_dict(),
            "direct_downstream_count": len(downstream),
            "total_affected_count": len(affected_nodes),
            "node_risk": node.risk_score,
            "propagation_risk": propagation_risk,
            "combined_risk": (total_risk + propagation_risk) / 2,
            "hidden_dependencies_found": len(relevant_hidden),
            "amplification_zones": self.find_amplification_zones(min_risk=0.4),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "repo_path": self.repo_path,
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "nodes_by_type": {
                t.value: sum(1 for n in self._nodes.values() if n.node_type == t)
                for t in NodeType
            },
            "edges_by_type": {
                t.value: len(ids) for t, ids in self._type_index.items()
            },
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    def merge(self, other: CausalGraph) -> CausalGraph:
        merged = CausalGraph(name=f"{self.name}+{other.name}", repo_path=self.repo_path or other.repo_path)
        for node in self._nodes.values():
            merged.add_node(node)
        for node in other._nodes.values():
            existing = merged.find_node_by_name(node.name)
            if not existing:
                merged.add_node(node)
        for edge in self._edges.values():
            merged.add_edge(edge)
        for edge in other._edges.values():
            existing = merged.get_edge(edge.id)
            if existing:
                existing.weight = max(existing.weight, edge.weight)
                existing.confidence = max(existing.confidence, edge.confidence)
                existing.evidence_sources = list(set(existing.evidence_sources + edge.evidence_sources))
            else:
                merged.add_edge(edge)
        return merged
