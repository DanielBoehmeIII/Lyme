from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .trace_schema import (
    RuntimeEventType,
    RuntimeTrace,
    RuntimeTraceEvent,
)


class StateType(str, Enum):
    VARIABLE = "variable"
    STORE = "store"
    CACHE = "cache"
    DATABASE = "database"
    QUEUE = "queue"
    API_STATE = "api_state"
    WEBSOCKET = "websocket"
    SESSION = "session"
    FILE = "file"
    CONFIG = "config"
    DOM = "dom"
    COMPONENT = "component"
    GLOBAL = "global"
    DERIVED = "derived"


class MutationType(str, Enum):
    WRITE = "write"
    READ = "read"
    DELETE = "delete"
    UPDATE = "update"
    MERGE = "merge"
    RESET = "reset"
    OBSERVE = "observe"
    SUBSCRIBE = "subscribe"
    INVALIDATE = "invalidate"
    SYNC = "sync"


class SynchronizationType(str, Enum):
    LOCK = "lock"
    TRANSACTION = "transaction"
    BARRIER = "barrier"
    ATOMIC = "atomic"
    QUEUE = "queue"
    SIGNAL = "signal"
    SEMAPHORE = "semaphore"
    CONDITION_VARIABLE = "condition_variable"
    FUTURE = "future"
    CHANNEL = "channel"


@dataclass
class StateNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    name: str = ""
    state_type: StateType = StateType.VARIABLE
    scope: str = ""
    owner: str = ""
    owner_file: str = ""
    owner_function: str = ""
    initial_value: str = ""
    current_value: Optional[str] = None
    subsystem: str = ""
    file_path: str = ""
    line_number: int = 0
    complexity: float = 0.0
    mutation_count: int = 0
    read_count: int = 0
    dependent_count: int = 0
    uncertainty_score: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_mutated: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "state_type": self.state_type.value,
            "scope": self.scope,
            "owner": self.owner,
            "owner_file": self.owner_file,
            "owner_function": self.owner_function,
            "initial_value": self.initial_value,
            "current_value": self.current_value,
            "subsystem": self.subsystem,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "complexity": self.complexity,
            "mutation_count": self.mutation_count,
            "read_count": self.read_count,
            "dependent_count": self.dependent_count,
            "uncertainty_score": self.uncertainty_score,
            "first_seen": self.first_seen,
            "last_mutated": self.last_mutated,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> StateNode:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class MutationEdge:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_state_id: str = ""
    target_state_id: str = ""
    mutation_type: MutationType = MutationType.WRITE
    confidence: float = 1.0
    frequency: int = 1
    latency_ms: Optional[float] = None
    trigger_event_id: str = ""
    trigger_file: str = ""
    trigger_function: str = ""
    condition: str = ""
    async_propagation: bool = False
    synchronization: Optional[SynchronizationType] = None
    evidence_sources: List[str] = field(default_factory=list)
    first_observed: float = field(default_factory=time.time)
    last_observed: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source_state_id": self.source_state_id,
            "target_state_id": self.target_state_id,
            "mutation_type": self.mutation_type.value,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "latency_ms": self.latency_ms,
            "trigger_event_id": self.trigger_event_id,
            "trigger_file": self.trigger_file,
            "trigger_function": self.trigger_function,
            "condition": self.condition,
            "async_propagation": self.async_propagation,
            "synchronization": self.synchronization.value if self.synchronization else None,
            "evidence_sources": self.evidence_sources,
            "first_observed": self.first_observed,
            "last_observed": self.last_observed,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, d: dict) -> MutationEdge:
        sync_val = d.get("synchronization")
        if sync_val:
            d["synchronization"] = SynchronizationType(sync_val)
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class MutationPathway:
    nodes: List[StateNode] = field(default_factory=list)
    edges: List[MutationEdge] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    exit_points: List[str] = field(default_factory=list)
    total_latency_ms: float = 0.0
    confidence: float = 1.0
    async_branches: List[List[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "entry_points": self.entry_points,
            "exit_points": self.exit_points,
            "total_latency_ms": self.total_latency_ms,
            "confidence": self.confidence,
            "async_branches": self.async_branches,
        }


@dataclass
class SynchronizationSurface:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    states: List[str] = field(default_factory=list)
    sync_type: SynchronizationType = SynchronizationType.LOCK
    contention_score: float = 0.0
    deadlock_risk: float = 0.0
    participants: List[str] = field(default_factory=list)
    file_path: str = ""
    function: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "states": self.states,
            "sync_type": self.sync_type.value,
            "contention_score": self.contention_score,
            "deadlock_risk": self.deadlock_risk,
            "participants": self.participants,
            "file_path": self.file_path,
            "function": self.function,
            "confidence": self.confidence,
        }


@dataclass
class CacheInvalidationZone:
    cache_id: str = ""
    cache_name: str = ""
    invalidated_by: List[str] = field(default_factory=list)
    invalidation_count: int = 0
    stale_read_risk: float = 0.0
    ttl_seconds: Optional[float] = None
    strategy: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "cache_id": self.cache_id,
            "cache_name": self.cache_name,
            "invalidated_by": self.invalidated_by,
            "invalidation_count": self.invalidation_count,
            "stale_read_risk": self.stale_read_risk,
            "ttl_seconds": self.ttl_seconds,
            "strategy": self.strategy,
        }


@dataclass
class StateFlowModel:
    name: str = ""
    application: str = ""
    version: str = ""
    states: Dict[str, StateNode] = field(default_factory=dict)
    mutations: Dict[str, MutationEdge] = field(default_factory=dict)
    pathways: List[MutationPathway] = field(default_factory=list)
    sync_surfaces: List[SynchronizationSurface] = field(default_factory=list)
    cache_zones: List[CacheInvalidationZone] = field(default_factory=list)
    events_to_states: Dict[str, List[str]] = field(default_factory=dict)
    uncertainty_zones: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_state(self, state: StateNode) -> str:
        self.states[state.id] = state
        self.updated_at = time.time()
        return state.id

    def add_mutation(self, mutation: MutationEdge) -> str:
        self.mutations[mutation.id] = mutation
        if mutation.source_state_id in self.states:
            self.states[mutation.source_state_id].mutation_count += 1
        if mutation.target_state_id in self.states:
            if mutation.mutation_type in (MutationType.READ, MutationType.OBSERVE):
                self.states[mutation.target_state_id].read_count += 1
            self.states[mutation.target_state_id].dependent_count += 1
        self.updated_at = time.time()
        return mutation.id

    def find_pathways(self, from_state: str, to_state: str, max_depth: int = 10) -> List[MutationPathway]:
        pathways = []
        visited: Set[str] = set()

        def dfs(current: str, target: str, path_nodes: List[StateNode],
                path_edges: List[MutationEdge], depth: int):
            if depth > max_depth:
                return
            if current in visited:
                return
            visited.add(current)

            if current == target and path_nodes:
                pathways.append(MutationPathway(
                    nodes=list(path_nodes),
                    edges=list(path_edges),
                    entry_points=[path_nodes[0].id] if path_nodes else [],
                    exit_points=[target],
                    confidence=min((e.confidence for e in path_edges), default=1.0),
                    total_latency_ms=sum((e.latency_ms or 0) for e in path_edges),
                ))
                visited.discard(current)
                return

            for mutation in self.mutations.values():
                next_id = None
                if mutation.source_state_id == current:
                    next_id = mutation.target_state_id
                elif mutation.target_state_id == current:
                    next_id = mutation.source_state_id

                if next_id and next_id not in visited and next_id in self.states:
                    path_edges.append(mutation)
                    path_nodes.append(self.states[next_id])
                    dfs(next_id, target, path_nodes, path_edges, depth + 1)
                    path_edges.pop()
                    path_nodes.pop()

            visited.discard(current)

        start_node = self.states.get(from_state)
        if start_node:
            dfs(from_state, to_state, [start_node], [], 0)
        return sorted(pathways, key=lambda p: p.confidence, reverse=True)

    def find_async_cascades(self) -> List[MutationPathway]:
        cascades = []
        for mutation in self.mutations.values():
            if mutation.async_propagation:
                pathway = MutationPathway()
                source = self.states.get(mutation.source_state_id)
                target = self.states.get(mutation.target_state_id)
                if source:
                    pathway.nodes.append(source)
                pathway.edges.append(mutation)
                if target:
                    pathway.nodes.append(target)
                pathway.async_branches = [[mutation.target_state_id]]
                cascade_downstream = self._follow_async(mutation.target_state_id, set(), 0)
                for downstream in cascade_downstream:
                    pathway.nodes.extend(downstream.nodes)
                    pathway.edges.extend(downstream.edges)
                    pathway.async_branches.append(
                        [n.id for n in downstream.nodes if n.id != mutation.target_state_id]
                    )
                cascades.append(pathway)
        return cascades

    def _follow_async(self, state_id: str, visited: Set[str], depth: int) -> List[MutationPathway]:
        if depth > 5 or state_id in visited:
            return []
        visited.add(state_id)
        pathways = []
        for mutation in self.mutations.values():
            if mutation.source_state_id == state_id and mutation.async_propagation:
                target = self.states.get(mutation.target_state_id)
                if target:
                    pw = MutationPathway(
                        nodes=[target],
                        edges=[mutation],
                    )
                    pathways.append(pw)
                    downstream = self._follow_async(mutation.target_state_id, visited, depth + 1)
                    pathways.extend(downstream)
        return pathways

    def find_cache_invalidation_zones(self) -> List[CacheInvalidationZone]:
        zones = []
        cache_states = {
            sid: s for sid, s in self.states.items()
            if s.state_type in (StateType.CACHE, StateType.STORE)
        }
        for cid, cache in cache_states.items():
            invalidators = []
            for mutation in self.mutations.values():
                if mutation.target_state_id == cid and mutation.mutation_type == MutationType.INVALIDATE:
                    invalidators.append(mutation.source_state_id)
                if mutation.source_state_id == cid and mutation.mutation_type == MutationType.WRITE:
                    if mutation.target_state_id not in invalidators:
                        invalidators.append(mutation.target_state_id)
            stale_risk = len(invalidators) * 0.1
            if cache.complexity > 0:
                stale_risk = min(1.0, stale_risk * (1 + cache.complexity))
            zones.append(CacheInvalidationZone(
                cache_id=cid,
                cache_name=cache.name,
                invalidated_by=invalidators,
                invalidation_count=len(invalidators),
                stale_read_risk=stale_risk,
                strategy=cache.metadata.get("cache_strategy", "unknown"),
            ))
        return sorted(zones, key=lambda z: -z.stale_read_risk)

    def find_synchronization_surfaces(self) -> List[SynchronizationSurface]:
        sync_edges = [
            m for m in self.mutations.values()
            if m.synchronization is not None
        ]
        surfaces: Dict[str, SynchronizationSurface] = {}
        for edge in sync_edges:
            key = edge.synchronization.value
            if key not in surfaces:
                surfaces[key] = SynchronizationSurface(sync_type=edge.synchronization)
            surfaces[key].states.append(edge.source_state_id)
            surfaces[key].states.append(edge.target_state_id)
            surfaces[key].participants.append(edge.trigger_file)
            if edge.confidence < 0.5:
                surfaces[key].deadlock_risk += 0.1
            surfaces[key].contention_score += 1.0 / max(len(surfaces[key].states), 1)
        for surface in surfaces.values():
            surface.contention_score = min(1.0, surface.contention_score)
            surface.deadlock_risk = min(1.0, surface.deadlock_risk)
        return list(surfaces.values())

    def estimate_uncertainty(self) -> List[Dict[str, Any]]:
        zones = []
        for state in self.states.values():
            uncertainty = 0.0
            factors = []
            if state.mutation_count == 0 and state.read_count == 0:
                uncertainty += 0.5
                factors.append("no_observations")
            incoming_mutations = [
                m for m in self.mutations.values()
                if m.target_state_id == state.id
            ]
            low_conf = sum(1 for m in incoming_mutations if m.confidence < 0.5)
            uncertainty += low_conf * 0.1
            if low_conf > 0:
                factors.append(f"{low_conf}_low_confidence_mutations")
            if state.state_type == StateType.DERIVED:
                uncertainty += 0.2
                factors.append("derived_state")
            if uncertainty > 0.5:
                zones.append({
                    "state_id": state.id,
                    "state_name": state.name,
                    "uncertainty_score": min(1.0, uncertainty),
                    "factors": factors,
                })
                self.uncertainty_zones.append(state.id)
        return sorted(zones, key=lambda z: -z["uncertainty_score"])

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "application": self.application,
            "version": self.version,
            "states": {sid: s.to_dict() for sid, s in self.states.items()},
            "mutations": {mid: m.to_dict() for mid, m in self.mutations.items()},
            "pathways": [p.to_dict() for p in self.pathways],
            "sync_surfaces": [s.to_dict() for s in self.sync_surfaces],
            "cache_zones": [z.to_dict() for z in self.cache_zones],
            "events_to_states": self.events_to_states,
            "uncertainty_zones": self.uncertainty_zones,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
            "state_count": len(self.states),
            "mutation_count": len(self.mutations),
            "pathway_count": len(self.pathways),
        }

    @classmethod
    def from_dict(cls, d: dict) -> StateFlowModel:
        model = cls(
            name=d.get("name", ""),
            application=d.get("application", ""),
            version=d.get("version", ""),
            events_to_states=d.get("events_to_states", {}),
            uncertainty_zones=d.get("uncertainty_zones", []),
            created_at=d.get("created_at", time.time()),
            updated_at=d.get("updated_at", time.time()),
            metadata=d.get("metadata", {}),
        )
        for sid, sdata in d.get("states", {}).items():
            model.states[sid] = StateNode.from_dict(sdata)
        for mid, mdata in d.get("mutations", {}).items():
            model.mutations[mid] = MutationEdge.from_dict(mdata)
        for pdata in d.get("pathways", []):
            pathway = MutationPathway()
            for ndata in pdata.get("nodes", []):
                pathway.nodes.append(StateNode.from_dict(ndata))
            for edata in pdata.get("edges", []):
                pathway.edges.append(MutationEdge.from_dict(edata))
            pathway.entry_points = pdata.get("entry_points", [])
            pathway.exit_points = pdata.get("exit_points", [])
            pathway.total_latency_ms = pdata.get("total_latency_ms", 0.0)
            pathway.confidence = pdata.get("confidence", 1.0)
            pathway.async_branches = pdata.get("async_branches", [])
            model.pathways.append(pathway)
        return model


class StateFlowInferrer:
    def __init__(self):
        self._patterns = self._build_patterns()

    def _build_patterns(self) -> Dict[str, List[str]]:
        return {
            "assignment": ["=", ":=", "set", "put", "assign"],
            "state_write": [".state", ".value", "setState", "dispatch", "commit"],
            "store_write": [".set", ".update", ".patch", ".replace", ".mutate"],
            "cache_write": [".set", ".put", ".add", ".store", ".cache"],
            "db_write": ["INSERT", "UPDATE", "DELETE", "UPSERT", "MERGE"],
            "queue_write": [".push", ".send", ".publish", ".enqueue", ".emit"],
            "async": ["async", "await", "Promise", "setTimeout", "setInterval",
                      "nextTick", "then(", "catch(", "future", "defer"],
            "sync": ["lock", "mutex", "semaphore", "transaction", "atomic",
                     "synchronized", "barrier"],
        }

    def infer_from_trace(self, trace: RuntimeTrace) -> StateFlowModel:
        model = StateFlowModel(
            name=trace.name,
            application=trace.application,
        )
        event_groups: Dict[str, List[RuntimeTraceEvent]] = defaultdict(list)
        for event in trace.events:
            key = f"{event.source_file}:{event.source_function}"
            if event.source_file:
                event_groups[key].append(event)

        state_registry: Dict[str, str] = {}
        for group_key, events in event_groups.items():
            sorted_events = sorted(events, key=lambda e: e.timestamp)
            for event in sorted_events:
                state_ids = self._infer_state_nodes(event, model)
                for sid in state_ids:
                    state_registry.setdefault(sid, sid)

        for event in trace.events:
            mutations = self._infer_mutations(event, model)
            for mutation in mutations:
                model.add_mutation(mutation)

        if trace.events:
            self._infer_event_driven_cascades(model, trace)

        model.pathways = self._infer_pathways(model)
        model.sync_surfaces = model.find_synchronization_surfaces()
        model.cache_zones = model.find_cache_invalidation_zones()
        model.uncertainty_zones = [z["state_id"] for z in model.estimate_uncertainty()]

        return model

    def _infer_state_nodes(self, event: RuntimeTraceEvent, model: StateFlowModel) -> List[str]:
        state_ids = []
        metadata = event.metadata or {}
        file_path = event.source_file
        func_name = event.source_function

        if event.event_type == RuntimeEventType.STATE_MUTATION:
            state_name = metadata.get("state_name", f"state_{event.id[:8]}")
            state_type = StateType(metadata.get("state_type", StateType.VARIABLE.value))
            state = StateNode(
                name=state_name,
                state_type=state_type,
                owner=func_name,
                owner_file=file_path,
                owner_function=func_name,
                subsystem=event.subsystem,
                file_path=file_path,
                line_number=event.source_line,
                initial_value=metadata.get("initial_value", ""),
                current_value=metadata.get("new_value"),
                mutation_count=1,
                metadata={"inferred_from": event.id},
            )
            model.add_state(state)
            state_ids.append(state.id)
            model.events_to_states.setdefault(event.id, []).append(state.id)

        if event.event_type == RuntimeEventType.DB_QUERY:
            query = metadata.get("query", "")
            table = metadata.get("table", metadata.get("collection", ""))
            if table:
                state_name = f"db:{table}"
                existing = self._find_state_by_name(model, state_name)
                if not existing:
                    state = StateNode(
                        name=state_name,
                        state_type=StateType.DATABASE,
                        owner=file_path,
                        owner_file=file_path,
                        subsystem=event.subsystem,
                        file_path=file_path,
                        metadata={"table": table, "query_type": metadata.get("type", "")},
                    )
                    model.add_state(state)
                    state_ids.append(state.id)

        if event.event_type == RuntimeEventType.CACHE_OPERATION:
            cache_key = metadata.get("key", "")
            if cache_key:
                state_name = f"cache:{cache_key}"
                existing = self._find_state_by_name(model, state_name)
                if not existing:
                    state = StateNode(
                        name=state_name,
                        state_type=StateType.CACHE,
                        owner=file_path,
                        owner_file=file_path,
                        subsystem=event.subsystem,
                        file_path=file_path,
                        metadata={"cache_key": cache_key, "operation": metadata.get("operation", "")},
                    )
                    model.add_state(state)
                    state_ids.append(state.id)

        return state_ids

    def _infer_mutations(self, event: RuntimeTraceEvent, model: StateFlowModel) -> List[MutationEdge]:
        mutations = []
        metadata = event.metadata or {}
        file_path = event.source_file

        if event.event_type == RuntimeEventType.STATE_MUTATION:
            state_name = metadata.get("state_name", "")
            source_name = metadata.get("trigger_state", "")
            source_state = self._find_state_by_name(model, source_name)
            target_state = self._find_state_by_name(model, state_name)
            if source_state and target_state:
                mutations.append(MutationEdge(
                    source_state_id=source_state.id,
                    target_state_id=target_state.id,
                    mutation_type=MutationType(metadata.get("mutation_type", MutationType.WRITE.value)),
                    trigger_event_id=event.id,
                    trigger_file=file_path,
                    trigger_function=event.source_function,
                    async_propagation=metadata.get("async", False),
                    evidence_sources=[f"trace_event:{event.id}"],
                ))

        if event.event_type == RuntimeEventType.API_CALL:
            api_name = metadata.get("api", metadata.get("endpoint", ""))
            method = metadata.get("method", "GET")
            state_name = f"api:{api_name}"
            api_state = self._find_state_by_name(model, state_name)
            if not api_state:
                api_state = StateNode(
                    name=state_name,
                    state_type=StateType.API_STATE,
                    owner=file_path,
                    owner_file=file_path,
                    subsystem=event.subsystem,
                    file_path=file_path,
                )
                model.add_state(api_state)
            target_name = metadata.get("response_state", "")
            target = self._find_state_by_name(model, target_name) if target_name else None
            if target:
                mutations.append(MutationEdge(
                    source_state_id=api_state.id,
                    target_state_id=target.id,
                    mutation_type=MutationType.WRITE if method in ("POST", "PUT", "PATCH", "DELETE") else MutationType.READ,
                    trigger_event_id=event.id,
                    trigger_file=file_path,
                    trigger_function=event.source_function,
                    async_propagation=True,
                    evidence_sources=[f"api_call:{api_name}"],
                ))

        if event.event_type == RuntimeEventType.DB_QUERY:
            table = metadata.get("table", metadata.get("collection", ""))
            query_type = metadata.get("type", "SELECT").upper()
            state_name = f"db:{table}"
            db_state = self._find_state_by_name(model, state_name)
            if not db_state and table:
                db_state = StateNode(
                    name=state_name,
                    state_type=StateType.DATABASE,
                    owner=file_path,
                    owner_file=file_path,
                    subsystem=event.subsystem,
                )
                model.add_state(db_state)
            func_state = self._find_state_by_name(model, f"func:{event.source_function}") or StateNode(
                name=f"func:{event.source_function}",
                state_type=StateType.VARIABLE,
                owner=event.source_function,
                owner_file=file_path,
                file_path=file_path,
            )
            model.add_state(func_state)
            if db_state:
                mut_type = MutationType.WRITE if query_type in ("INSERT", "UPDATE", "DELETE", "UPSERT") else MutationType.READ
                mutations.append(MutationEdge(
                    source_state_id=func_state.id,
                    target_state_id=db_state.id,
                    mutation_type=mut_type,
                    trigger_event_id=event.id,
                    trigger_file=file_path,
                    trigger_function=event.source_function,
                    async_propagation=metadata.get("async", False),
                    evidence_sources=[f"db_query:{table}:{query_type}"],
                ))

        return mutations

    def _infer_event_driven_cascades(self, model: StateFlowModel, trace: RuntimeTrace):
        error_events = trace.get_error_events()
        sorted_errors = sorted(error_events, key=lambda e: e.timestamp)
        for i in range(len(sorted_errors) - 1):
            latency = (sorted_errors[i + 1].timestamp - sorted_errors[i].timestamp) * 1000
            if latency < 5000:
                source_state = self._find_or_create_state(model, sorted_errors[i])
                target_state = self._find_or_create_state(model, sorted_errors[i + 1])
                if source_state and target_state and source_state.id != target_state.id:
                    model.add_mutation(MutationEdge(
                        source_state_id=source_state.id,
                        target_state_id=target_state.id,
                        mutation_type=MutationType.OBSERVE,
                        confidence=0.4,
                        trigger_event_id=sorted_errors[i].id,
                        trigger_file=sorted_errors[i].source_file,
                        trigger_function=sorted_errors[i].source_function,
                        async_propagation=True,
                        evidence_sources=["error_cascade"],
                    ))

    def _infer_pathways(self, model: StateFlowModel) -> List[MutationPathway]:
        pathways = []
        for mutation in list(model.mutations.values())[:50]:
            source = model.states.get(mutation.source_state_id)
            target = model.states.get(mutation.target_state_id)
            if source and target:
                pathway = MutationPathway(
                    nodes=[source, target],
                    edges=[mutation],
                    entry_points=[source.id],
                    exit_points=[target.id],
                    total_latency_ms=mutation.latency_ms or 0,
                    confidence=mutation.confidence,
                )
                deeper = model.find_pathways(target.id, source.id, max_depth=3)
                if deeper:
                    pathway.nodes.extend(deeper[0].nodes[1:])
                    pathway.edges.extend(deeper[0].edges)
                pathways.append(pathway)
        return pathways[:50]

    def _find_state_by_name(self, model: StateFlowModel, name: str) -> Optional[StateNode]:
        if not name:
            return None
        for state in model.states.values():
            if state.name == name:
                return state
        return None

    def _find_or_create_state(self, model: StateFlowModel, event: RuntimeTraceEvent) -> Optional[StateNode]:
        if not event.source_file:
            state_name = f"event:{event.id[:8]}"
        else:
            state_name = f"{event.source_file}:{event.source_function or 'unknown'}"
        existing = self._find_state_by_name(model, state_name)
        if existing:
            return existing
        state = StateNode(
            name=state_name,
            state_type=StateType.VARIABLE,
            owner=event.source_function or "",
            owner_file=event.source_file or "",
            owner_function=event.source_function or "",
            subsystem=event.subsystem,
            file_path=event.source_file or "",
        )
        model.add_state(state)
        return state


class StateFlowVisualizer:
    @staticmethod
    def pathway_summary(pathway: MutationPathway) -> str:
        parts = []
        for i, node in enumerate(pathway.nodes):
            parts.append(f"{node.name}[{node.state_type.value}]")
            if i < len(pathway.edges):
                edge = pathway.edges[i]
                parts.append(f"--({edge.mutation_type.value})-->")
        return " ".join(parts)

    @staticmethod
    def model_summary(model: StateFlowModel) -> str:
        lines = []
        lines.append(f"State Flow Model: {model.name or 'unnamed'}")
        lines.append(f"  States: {len(model.states)}")
        lines.append(f"  Mutations: {len(model.mutations)}")
        lines.append(f"  Pathways: {len(model.pathways)}")
        lines.append(f"  Sync Surfaces: {len(model.sync_surfaces)}")
        lines.append(f"  Cache Zones: {len(model.cache_zones)}")
        lines.append(f"  Uncertainty Zones: {len(model.uncertainty_zones)}")

        type_counts: Dict[str, int] = defaultdict(int)
        for state in model.states.values():
            type_counts[state.state_type.value] += 1
        lines.append("  State Types: " + ", ".join(f"{k}={v}" for k, v in sorted(type_counts.items())))

        if model.sync_surfaces:
            lines.append("  Sync Surfaces:")
            for surf in model.sync_surfaces:
                lines.append(f"    - {surf.sync_type.value}: contention={surf.contention_score:.2f}, deadlock_risk={surf.deadlock_risk:.2f}")

        if model.cache_zones:
            lines.append("  Cache Zones:")
            for zone in model.cache_zones[:5]:
                lines.append(f"    - {zone.cache_name}: stale_risk={zone.stale_read_risk:.2f}, invalidations={zone.invalidation_count}")

        if model.uncertainty_zones:
            lines.append(f"  Uncertainty: {len(model.uncertainty_zones)} zones with low confidence")
        return "\n".join(lines)

    @staticmethod
    def mermaid_flow(model: StateFlowModel) -> str:
        lines = ["graph LR"]
        added_edges: Set[Tuple[str, str]] = set()
        for mutation in model.mutations.values():
            source = model.states.get(mutation.source_state_id)
            target = model.states.get(mutation.target_state_id)
            if source and target and (source.id, target.id) not in added_edges:
                sname = source.name.replace(":", "_").replace(".", "_").replace("/", "_")[:20]
                tname = target.name.replace(":", "_").replace(".", "_").replace("/", "_")[:20]
                label = mutation.mutation_type.value
                if mutation.async_propagation:
                    label += "_async"
                lines.append(f'    {sname}--"{label}"-->{tname}')
                added_edges.add((source.id, target.id))
        return "\n".join(lines)
