from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path
from enum import Enum
import json
import uuid


class NodeType(str, Enum):
    FRAMEWORK = "framework"
    LIBRARY = "library"
    TOOL = "tool"
    LANGUAGE = "language"
    DATABASE = "database"
    PROTOCOL = "protocol"
    PLATFORM = "platform"
    PATTERN = "pattern"
    MIGRATION_PATH = "migration_path"
    SECURITY_ZONE = "security_zone"
    FREQUENT_BUG = "frequent_bug"
    ARCH_NORM = "arch_norm"
    INTEGRATION = "integration"
    BEST_PRACTICE = "best_practice"


class EdgeType(str, Enum):
    DEPENDS_ON = "depends_on"
    INTEGRATES_WITH = "integrates_with"
    REPLACES = "replaces"
    MIGRATES_TO = "migrates_to"
    COMPATIBLE_WITH = "compatible_with"
    INCOMPATIBLE_WITH = "incompatible_with"
    EXTENDS = "extends"
    USES = "uses"
    SUGGESTS = "suggests"
    FREQUENTLY_PAIRED_WITH = "frequently_paired_with"
    SECURITY_SENSITIVE = "security_sensitive"
    KNOWN_BUG = "known_bug"
    ARCH_NORM_FOR = "arch_norm_for"
    COMMON_MISTAKE = "common_mistake"


@dataclass
class EcosystemNode:
    id: str
    name: str
    node_type: NodeType
    description: str
    version: str = ""
    ecosystem: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "description": self.description,
            "version": self.version,
            "ecosystem": self.ecosystem,
            "tags": self.tags,
            "metadata": self.metadata,
            "confidence": self.confidence,
        }


@dataclass
class EcosystemEdge:
    id: str
    source_id: str
    target_id: str
    edge_type: EdgeType
    weight: float = 1.0
    description: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "description": self.description,
            "confidence": self.confidence,
        }


class EcosystemGraph:
    def __init__(self):
        self._nodes: Dict[str, EcosystemNode] = {}
        self._edges: Dict[str, EcosystemEdge] = {}
        self._adjacency: Dict[str, Dict[str, List[str]]] = {}
        self._reverse_adj: Dict[str, Dict[str, List[str]]] = {}

    def add_node(self, node: EcosystemNode):
        self._nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = {}
            self._reverse_adj[node.id] = {}

    def add_edge(self, edge: EcosystemEdge):
        self._edges[edge.id] = edge
        if edge.source_id not in self._adjacency:
            self._adjacency[edge.source_id] = {}
        if edge.target_id not in self._reverse_adj:
            self._reverse_adj[edge.target_id] = {}
        if edge.edge_type.value not in self._adjacency[edge.source_id]:
            self._adjacency[edge.source_id][edge.edge_type.value] = []
        if edge.edge_type.value not in self._reverse_adj[edge.target_id]:
            self._reverse_adj[edge.target_id][edge.edge_type.value] = []
        self._adjacency[edge.source_id][edge.edge_type.value].append(edge.target_id)
        self._reverse_adj[edge.target_id][edge.edge_type.value].append(edge.source_id)

    def get_node(self, node_id: str) -> Optional[EcosystemNode]:
        return self._nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[EcosystemEdge]:
        return self._edges.get(edge_id)

    def query(self, node_type: Optional[NodeType] = None, tag: Optional[str] = None, name_contains: Optional[str] = None) -> List[EcosystemNode]:
        results = []
        for node in self._nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if tag and tag not in node.tags:
                continue
            if name_contains and name_contains.lower() not in node.name.lower():
                continue
            results.append(node)
        return results

    def get_dependencies(self, node_id: str) -> List[EcosystemNode]:
        outgoing = set()
        adj = self._adjacency.get(node_id, {})
        for targets in adj.values():
            outgoing.update(targets)
        return [self._nodes[t] for t in outgoing if t in self._nodes]

    def get_dependents(self, node_id: str) -> List[EcosystemNode]:
        incoming = set()
        radj = self._reverse_adj.get(node_id, {})
        for sources in radj.values():
            incoming.update(sources)
        return [self._nodes[s] for s in incoming if s in self._nodes]

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> List[List[str]]:
        paths = []
        visited = set()

        def dfs(current: str, target: str, path: List[str], depth: int):
            if depth > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            if current in visited:
                return
            visited.add(current)
            adj = self._adjacency.get(current, {})
            for targets in adj.values():
                for next_id in targets:
                    if next_id not in visited:
                        path.append(next_id)
                        dfs(next_id, target, path, depth + 1)
                        path.pop()
            visited.remove(current)

        dfs(source_id, target_id, [source_id], 0)
        return paths

    def get_upgrade_path(self, library_name: str) -> List[Tuple[str, str, str]]:
        path = []
        nodes = self.query(name_contains=library_name)
        for node in nodes:
            for edge in self._edges.values():
                if edge.source_id == node.id and edge.edge_type == EdgeType.MIGRATES_TO:
                    target = self._nodes.get(edge.target_id)
                    if target:
                        path.append((node.name, target.name, edge.description))
        return path

    def get_security_zones(self) -> List[EcosystemNode]:
        return self.query(node_type=NodeType.SECURITY_ZONE)

    def get_frequent_bugs(self) -> List[EcosystemNode]:
        return self.query(node_type=NodeType.FREQUENT_BUG)

    def get_arch_norms(self) -> List[EcosystemNode]:
        return self.query(node_type=NodeType.ARCH_NORM)

    def merge(self, other: EcosystemGraph):
        for node in other._nodes.values():
            if node.id not in self._nodes:
                self.add_node(node)
        for edge in other._edges.values():
            if edge.id not in self._edges:
                self.add_edge(edge)

    def to_dict(self) -> Dict:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    @classmethod
    def from_dict(cls, d: Dict) -> EcosystemGraph:
        g = cls()
        for nd in d.get("nodes", []):
            g.add_node(EcosystemNode(
                id=nd["id"],
                name=nd["name"],
                node_type=NodeType(nd["node_type"]),
                description=nd.get("description", ""),
                version=nd.get("version", ""),
                ecosystem=nd.get("ecosystem", ""),
                tags=nd.get("tags", []),
                metadata=nd.get("metadata", {}),
                confidence=nd.get("confidence", 1.0),
            ))
        for ed in d.get("edges", []):
            g.add_edge(EcosystemEdge(
                id=ed["id"],
                source_id=ed["source_id"],
                target_id=ed["target_id"],
                edge_type=EdgeType(ed["edge_type"]),
                weight=ed.get("weight", 1.0),
                description=ed.get("description", ""),
                confidence=ed.get("confidence", 1.0),
            ))
        return g

    def save(self, path: Path):
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> EcosystemGraph:
        return cls.from_dict(json.loads(path.read_text()))

    @property
    def nodes(self) -> List[EcosystemNode]:
        return list(self._nodes.values())

    @property
    def edges(self) -> List[EcosystemEdge]:
        return list(self._edges.values())

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)
