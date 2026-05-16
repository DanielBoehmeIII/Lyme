from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .intent_model import IntentModel, IntentUncertainty, SubsystemIntent


class IntentEvolutionTracker:
    def __init__(self):
        self._snapshots: List[Dict[str, Any]] = []

    def snapshot(self, model: IntentModel) -> Dict[str, Any]:
        snap = {
            "timestamp": time.time(),
            "subsystem_count": len(model.intents),
            "philosophy": model.overall_philosophy.value,
            "direction": model.evolution_direction.value,
            "subsystems": {
                si.subsystem: {
                    "purpose": si.purpose[:50] if si.purpose else "",
                    "confidence": si.confidence,
                    "uncertainty": si.uncertainty.overall,
                    "tradeoff_count": len(si.tradeoffs),
                    "constraint_count": len(si.constraints),
                    "evidence_count": len(si.evidence),
                }
                for si in model.intents
            },
            "avg_confidence": (
                sum(si.confidence for si in model.intents) / max(len(model.intents), 1)
            ),
        }
        self._snapshots.append(snap)
        return snap

    def get_trend(self, metric: str = "avg_confidence") -> List[float]:
        return [s.get(metric, 0) for s in self._snapshots]

    def compare_snapshots(self, idx_a: int, idx_b: int) -> Dict[str, Any]:
        if idx_a >= len(self._snapshots) or idx_b >= len(self._snapshots):
            return {"error": "snapshot index out of range"}

        a = self._snapshots[idx_a]
        b = self._snapshots[idx_b]

        changes = {}
        for sub in set(list(a.get("subsystems", {}).keys()) + list(b.get("subsystems", {}).keys())):
            sub_a = a.get("subsystems", {}).get(sub, {})
            sub_b = b.get("subsystems", {}).get(sub, {})
            confidence_change = sub_b.get("confidence", 0) - sub_a.get("confidence", 0)
            if abs(confidence_change) > 0.05:
                changes[sub] = {
                    "confidence_change": confidence_change,
                    "evidence_change": sub_b.get("evidence_count", 0) - sub_a.get("evidence_count", 0),
                    "constraints_change": sub_b.get("constraint_count", 0) - sub_a.get("constraint_count", 0),
                }

        return {
            "snapshot_a_time": a.get("timestamp"),
            "snapshot_b_time": b.get("timestamp"),
            "philosophy_a": a.get("philosophy"),
            "philosophy_b": b.get("philosophy"),
            "direction_a": a.get("direction"),
            "direction_b": b.get("direction"),
            "avg_confidence_a": a.get("avg_confidence"),
            "avg_confidence_b": b.get("avg_confidence"),
            "subsystem_confidence_changes": changes,
        }


class UncertaintyEstimator:
    def estimate(self, model: IntentModel) -> IntentUncertainty:
        if not model.intents:
            return IntentUncertainty(
                overall=1.0,
                evidence_gap=1.0,
                contradiction_level=0.0,
                staleness=0.0,
                missing_domains=["no subsystems found"],
            )

        avg_uncertainty = sum(si.uncertainty.overall for si in model.intents) / len(model.intents)
        min_evidence = min(len(si.evidence) for si in model.intents)
        max_evidence = max(len(si.evidence) for si in model.intents)

        evidence_gap = 1.0 - (min_evidence / max(max_evidence, 1))

        contradictions = self._detect_contradictions(model)
        contradiction_level = len(contradictions) / max(len(model.intents), 1)

        age = time.time() - model.created_at
        staleness = min(1.0, age / (86400 * 30))

        missing = self._find_missing_domains(model)

        overall = (
            avg_uncertainty * 0.4 +
            evidence_gap * 0.3 +
            contradiction_level * 0.2 +
            staleness * 0.1
        )

        return IntentUncertainty(
            overall=min(1.0, overall),
            evidence_gap=evidence_gap,
            contradiction_level=contradiction_level,
            staleness=staleness,
            missing_domains=missing,
        )

    def _detect_contradictions(self, model: IntentModel) -> List[str]:
        contradictions = []
        philosophies = {}
        for si in model.intents:
            for tradeoff in si.tradeoffs:
                if hasattr(tradeoff, 'chosen_path') and tradeoff.chosen_path:
                    philosophies[si.subsystem] = tradeoff.chosen_path

        philosophy_values = list(philosophies.values())
        for i in range(len(philosophy_values)):
            for j in range(i + 1, len(philosophy_values)):
                if philosophy_values[i] != philosophy_values[j]:
                    contradictions.append(
                        f"Different architectural directions: {list(philosophies.keys())[i]} vs {list(philosophies.keys())[j]}"
                    )
        return contradictions

    def _find_missing_domains(self, model: IntentModel) -> List[str]:
        standard_domains = {"controllers", "services", "models", "config", "utils"}
        present_domains = {si.subsystem for si in model.intents}
        missing = list(standard_domains - present_domains)
        return missing if missing else []
