from __future__ import annotations

from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from .causal_graph import CausalGraph, CausalNode, CausalEdge, CausalRelationType, InfluencePath


class FailurePropagator:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def simulate_failure(self, source_node_id: str, confidence_threshold: float = 0.3) -> Dict[str, Any]:
        affected: Dict[str, List[Dict[str, Any]]] = {}
        visited: Set[str] = set()
        queue: deque = deque()
        queue.append((source_node_id, 0, 1.0, []))

        source_node = self.graph.get_node(source_node_id)
        if not source_node:
            return {"error": "source node not found", "affected": {}}

        while queue:
            node_id, depth, propagation_confidence, path = queue.popleft()
            if node_id in visited or depth > 10:
                continue
            visited.add(node_id)

            node = self.graph.get_node(node_id)
            if not node:
                continue

            if node_id != source_node_id:
                if node_id not in affected:
                    affected[node_id] = []
                affected[node_id].append({
                    "depth": depth,
                    "propagation_confidence": propagation_confidence,
                    "path": [n_id for n_id in path],
                })

            outgoing = self.graph.get_outgoing_edges(node_id)
            for edge in outgoing:
                if edge.confidence < confidence_threshold:
                    continue

                decayed_confidence = propagation_confidence * edge.confidence * edge.weight
                if decayed_confidence < 0.05:
                    continue

                target = self.graph.get_node(edge.target_id)
                if target and target.id not in visited:
                    new_path = path + [node_id]
                    queue.append((edge.target_id, depth + 1, decayed_confidence, new_path))

        return {
            "source_node": source_node.to_dict(),
            "total_affected": len(affected),
            "affected_details": affected,
            "propagation_summary": self._summarize_propagation(affected),
        }

    def _summarize_propagation(self, affected: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        if not affected:
            return {"max_depth": 0, "avg_confidence": 0, "nodes_by_depth": {}}

        depths = [info[0]["depth"] for info in affected.values()]
        confidences = [info[0]["propagation_confidence"] for info in affected.values()]

        nodes_by_depth: Dict[int, int] = defaultdict(int)
        for d in depths:
            nodes_by_depth[d] += 1

        return {
            "max_depth": max(depths),
            "avg_depth": sum(depths) / len(depths),
            "avg_confidence": sum(confidences) / len(confidences),
            "nodes_by_depth": dict(sorted(nodes_by_depth.items())),
        }

    def cascade_analysis(self, source_node_id: str) -> Dict[str, Any]:
        result = self.simulate_failure(source_node_id)
        if "error" in result:
            return result

        affected_ids = list(result["affected_details"].keys())
        cascade_chains: List[Dict[str, Any]] = []

        for affected_id in affected_ids:
            chain = self._trace_cascade_chain(source_node_id, affected_id)
            if chain:
                cascade_chains.append(chain)

        amplification = self._compute_amplification(source_node_id, affected_ids)

        return {
            **result,
            "cascade_chains": sorted(cascade_chains, key=lambda c: -c["total_risk"])[:10],
            "amplification_factor": amplification,
        }

    def _trace_cascade_chain(self, source_id: str, target_id: str) -> Optional[Dict[str, Any]]:
        visited: Set[str] = set()
        queue: deque = deque()
        queue.append((source_id, [source_id], 1.0, []))

        while queue:
            current, path, confidence, edges_traversed = queue.popleft()
            if current in visited and len(path) > 20:
                continue
            visited.add(current)

            if current == target_id:
                path_risk = sum(
                    (self.graph.get_node(n_id).risk_score if self.graph.get_node(n_id) else 0)
                    for n_id in path
                ) / max(len(path), 1)
                return {
                    "source": source_id,
                    "target": target_id,
                    "path_length": len(path),
                    "path": path,
                    "path_confidence": confidence,
                    "total_risk": path_risk,
                    "edges": edges_traversed,
                }

            outgoing = self.graph.get_outgoing_edges(current)
            for edge in outgoing:
                target = self.graph.get_node(edge.target_id)
                if target and target.id not in visited:
                    new_confidence = confidence * edge.confidence * edge.weight
                    queue.append((edge.target_id, path + [target.id], new_confidence, edges_traversed + [edge.to_dict()]))

        return None

    def _compute_amplification(self, source_id: str, affected_ids: List[str]) -> float:
        source = self.graph.get_node(source_id)
        if not source or not affected_ids:
            return 0.0

        affected_risks = [
            self.graph.get_node(a_id).risk_score
            for a_id in affected_ids
            if self.graph.get_node(a_id)
        ]
        if not affected_risks:
            return 0.0

        avg_downstream_risk = sum(affected_risks) / len(affected_risks)
        if source.risk_score == 0:
            return avg_downstream_risk
        return avg_downstream_risk / source.risk_score


class ImpactEstimator:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def estimate_change_impact(self, changed_files: List[str]) -> Dict[str, Any]:
        changed_nodes = []
        for fp in changed_files:
            node = self.graph.find_node_by_name(fp)
            if node:
                changed_nodes.append(node)

        if not changed_nodes:
            return {"error": "no matching files found in graph"}

        all_affected: Set[str] = set()
        propagator = FailurePropagator(self.graph)

        chain_results = []
        for node in changed_nodes:
            result = propagator.cascade_analysis(node.id)
            if "error" not in result:
                all_affected.update(result.get("affected_details", {}).keys())
                chain_results.append({
                    "source": node.name,
                    "affected_count": result.get("total_affected", 0),
                    "amplification": result.get("amplification_factor", 0),
                })

        breakage_estimates = []
        for node_id in all_affected:
            node = self.graph.get_node(node_id)
            if node:
                incoming = self.graph.get_incoming_edges(node_id)
                exposed_contracts = sum(
                    1 for e in incoming
                    if e.relation_type in (CausalRelationType.API_CALL, CausalRelationType.CONTRACT_DEPENDENCY)
                )
                breakage_estimates.append({
                    "file": node.name,
                    "file_path": node.file_path,
                    "risk_score": node.risk_score,
                    "exposed_contracts": exposed_contracts,
                    "change_frequency": node.change_frequency,
                    "subsystem": node.subsystem,
                })

        return {
            "changed_files": changed_files,
            "total_downstream_files": len(all_affected),
            "breakage_estimates": sorted(breakage_estimates, key=lambda b: -b["risk_score"])[:30],
            "propagation_chains": chain_results,
            "summary": self._generate_summary(changed_nodes, all_affected),
        }

    def _generate_summary(self, changed_nodes: List[CausalNode], affected_ids: Set[str]) -> str:
        if not affected_ids:
            return "No downstream impact detected."
        subsystems = set()
        for nid in affected_ids:
            node = self.graph.get_node(nid)
            if node:
                subsystems.add(node.subsystem)
        names = [n.name for n in changed_nodes]
        return (
            f"Changing {len(changed_nodes)} file(s) ({', '.join(names[:3])}) "
            f"potentially affects {len(affected_ids)} other files across "
            f"{len(subsystems)} subsystem(s): {', '.join(sorted(subsystems)[:5])}"
        )


class DownstreamAnalyzer:
    def __init__(self, graph: CausalGraph):
        self.graph = graph

    def find_downstream_breakage(self, node_id: str) -> List[Dict[str, Any]]:
        propagator = FailurePropagator(self.graph)
        result = propagator.simulate_failure(node_id)
        if "error" in result:
            return []

        breakage_list = []
        for affected_id, info_list in result.get("affected_details", {}).items():
            node = self.graph.get_node(affected_id)
            if node:
                breakage_list.append({
                    "file": node.name,
                    "file_path": node.file_path,
                    "subsystem": node.subsystem,
                    "risk_score": node.risk_score,
                    "depth": info_list[0]["depth"],
                    "propagation_confidence": info_list[0]["propagation_confidence"],
                    "evidence_count": len(info_list),
                })
        return sorted(breakage_list, key=lambda b: (-b["risk_score"], b["depth"]))

    def find_hidden_upstream(self, node_id: str, min_confidence: float = 0.2) -> List[Dict[str, Any]]:
        hiddens = []
        incoming = self.graph.get_incoming_edges(node_id)
        for edge in incoming:
            if edge.relation_type != CausalRelationType.IMPORT and edge.confidence >= min_confidence:
                source = self.graph.get_node(edge.source_id)
                if source:
                    hiddens.append({
                        "hidden_dependency": source.name,
                        "file_path": source.file_path,
                        "relation_type": edge.relation_type.value,
                        "confidence": edge.confidence,
                        "evidence": edge.evidence_sources,
                    })
        return sorted(hiddens, key=lambda h: -h["confidence"])

    def subsystem_exposure(self, subsystem: str) -> Dict[str, Any]:
        nodes = [
            n for n in self.graph._nodes.values()
            if n.subsystem == subsystem
        ]
        if not nodes:
            return {"error": f"subsystem '{subsystem}' not found"}

        all_incoming: List[str] = []
        all_outgoing: List[str] = []
        total_risk = 0.0

        for node in nodes:
            for edge in self.graph.get_incoming_edges(node.id):
                all_incoming.append(edge.source_id)
            for edge in self.graph.get_outgoing_edges(node.id):
                all_outgoing.append(edge.target_id)
            total_risk += node.risk_score

        external_dependents = set(
            sid for sid in all_incoming
            if (self.graph.get_node(sid) and self.graph.get_node(sid).subsystem != subsystem)
        )
        external_dependencies = set(
            tid for tid in all_outgoing
            if (self.graph.get_node(tid) and self.graph.get_node(tid).subsystem != subsystem)
        )

        return {
            "subsystem": subsystem,
            "node_count": len(nodes),
            "external_dependents_count": len(external_dependents),
            "external_dependencies_count": len(external_dependencies),
            "avg_risk": total_risk / max(len(nodes), 1),
            "total_risk": total_risk,
        }
