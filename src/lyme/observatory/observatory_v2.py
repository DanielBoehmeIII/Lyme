from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from collections import defaultdict
import json
import math
import time


class DataPipelineStage(str, Enum):
    INGESTION = "ingestion"
    VALIDATION = "validation"
    TRANSFORMATION = "transformation"
    ENRICHMENT = "enrichment"
    STORAGE = "storage"
    ANALYSIS = "analysis"


@dataclass
class TelemetrySource:
    source_type: str
    source_id: str
    last_ingested: float
    records_ingested: int
    schema_version: str
    pipeline_stage: DataPipelineStage

    def to_dict(self) -> Dict:
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "last_ingested": self.last_ingested,
            "records_ingested": self.records_ingested,
            "schema_version": self.schema_version,
            "pipeline_stage": self.pipeline_stage.value,
        }


@dataclass
class IntegratedObservation:
    timestamp: float
    repo_evolution: Dict
    runtime_trace: Optional[Dict]
    ecosystem_intelligence: Dict
    architecture_fitness: Dict
    invariant_systems: Dict
    coordination_telemetry: Optional[Dict]
    skill_transfer: Optional[Dict]
    confidence_calibration: Dict
    risk_forecast: Dict

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "repo_evolution": self.repo_evolution,
            "ecosystem_intelligence": self.ecosystem_intelligence,
            "architecture_fitness": self.architecture_fitness,
            "invariant_systems": self.invariant_systems,
            "confidence_calibration": self.confidence_calibration,
            "risk_forecast": self.risk_forecast,
        }


@dataclass
class ObservatoryV2Config:
    name: str = "lyme-observatory-v2"
    pipeline_batch_size: int = 100
    storage_backend: str = "json"
    enable_repo_evolution: bool = True
    enable_runtime_traces: bool = True
    enable_ecosystem_intel: bool = True
    enable_architecture_fitness: bool = True
    enable_invariant_systems: bool = True
    enable_coordination: bool = True
    enable_skill_transfer: bool = True
    enable_confidence: bool = True
    enable_risk_forecasting: bool = True
    snapshot_interval: int = 3600
    max_snapshots: int = 1000


class ObservatoryV2:
    def __init__(self, config: Optional[ObservatoryV2Config] = None):
        self.config = config or ObservatoryV2Config()
        self._observations: List[IntegratedObservation] = []
        self._sources: Dict[str, TelemetrySource] = {}
        self._pipeline_status: Dict[DataPipelineStage, int] = defaultdict(int)

    def record_observation(self, observation: IntegratedObservation):
        self._observations.append(observation)
        if len(self._observations) > self.config.max_snapshots:
            self._observations = self._observations[-self.config.max_snapshots:]

    def register_source(self, source: TelemetrySource):
        self._sources[source.source_id] = source

    def latest_observation(self) -> Optional[IntegratedObservation]:
        return self._observations[-1] if self._observations else None

    def compute_integrated_health(self) -> Dict:
        if not self._observations:
            return {"health_score": 0.5, "status": "no_data"}

        recent = self._observations[-min(5, len(self._observations)):]

        evolution_scores = []
        architecture_scores = []
        confidence_scores = []
        risk_scores = []

        for obs in recent:
            if "stability_score" in obs.repo_evolution:
                evolution_scores.append(obs.repo_evolution["stability_score"])
            if "overall_score" in obs.architecture_fitness:
                architecture_scores.append(obs.architecture_fitness["overall_score"])
            if "average_confidence" in obs.confidence_calibration:
                confidence_scores.append(obs.confidence_calibration["average_confidence"])
            if "health_score" in obs.risk_forecast:
                risk_scores.append(obs.risk_forecast["health_score"])

        avg_evolution = sum(evolution_scores) / len(evolution_scores) if evolution_scores else 0.5
        avg_architecture = sum(architecture_scores) / len(architecture_scores) if architecture_scores else 0.5
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5
        avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0.5

        composite = (avg_evolution * 0.25 + avg_architecture * 0.25 +
                     avg_confidence * 0.25 + avg_risk * 0.25)

        signals = []
        if avg_evolution < 0.4:
            signals.append("repo_evolution_declining")
        if avg_architecture < 0.4:
            signals.append("architecture_fitness_low")
        if avg_confidence < 0.4:
            signals.append("confidence_calibration_degraded")

        return {
            "health_score": round(composite, 3),
            "trend": "improving" if composite > 0.6 else "stable" if composite > 0.4 else "declining",
            "signals": signals,
            "dimension_scores": {
                "repo_evolution": round(avg_evolution, 3),
                "architecture_fitness": round(avg_architecture, 3),
                "confidence_calibration": round(avg_confidence, 3),
                "risk_health": round(avg_risk, 3),
            },
            "total_observations": len(self._observations),
        }

    def data_pipeline_report(self) -> Dict:
        return {
            "pipeline_stages": {k.value: v for k, v in self._pipeline_status.items()},
            "total_sources": len(self._sources),
            "sources": [s.to_dict() for s in self._sources.values()],
            "total_observations": len(self._observations),
            "config": {
                "enable_repo_evolution": self.config.enable_repo_evolution,
                "enable_runtime_traces": self.config.enable_runtime_traces,
                "enable_ecosystem_intel": self.config.enable_ecosystem_intel,
                "enable_architecture_fitness": self.config.enable_architecture_fitness,
                "snapshot_interval": self.config.snapshot_interval,
            },
        }

    def replay_observations(self, start_idx: int = 0, end_idx: Optional[int] = None) -> List[IntegratedObservation]:
        end = end_idx or len(self._observations)
        return self._observations[start_idx:end]

    def build_timeline(self, dimension: str = "health") -> List[Dict]:
        timeline = []
        for i, obs in enumerate(self._observations):
            entry = {"index": i, "timestamp": obs.timestamp}
            if dimension == "health":
                entry["value"] = obs.repo_evolution.get("stability_score", 0.5)
            elif dimension == "architecture":
                entry["value"] = obs.architecture_fitness.get("overall_score", 0.5)
            elif dimension == "confidence":
                entry["value"] = obs.confidence_calibration.get("average_confidence", 0.5)
            timeline.append(entry)
        return timeline

    def compute_migration_risks(self) -> List[Dict]:
        risks = []
        for obs in self._observations[-10:]:
            if "migration_risks" in obs.risk_forecast:
                risks.extend(obs.risk_forecast["migration_risks"])
        return risks

    def compute_skill_transfer_effectiveness(self) -> Dict:
        transfers = [obs.skill_transfer for obs in self._observations if obs.skill_transfer]
        if not transfers:
            return {"effectiveness": 0, "total_transfers": 0}

        avg_effectiveness = sum(t.get("transfer_score", 0) for t in transfers) / len(transfers)
        return {
            "effectiveness": round(avg_effectiveness, 3),
            "total_transfers": len(transfers),
            "trend": "improving" if avg_effectiveness > 0.6 else "stable" if avg_effectiveness > 0.4 else "declining",
        }

    def storage_report(self) -> Dict:
        return {
            "total_observations": len(self._observations),
            "estimated_size_bytes": len(json.dumps([o.to_dict() for o in self._observations[-10:]])),
            "storage_backend": self.config.storage_backend,
            "retention_policy": f"max_{self.config.max_snapshots}_snapshots",
        }

    def save(self, path: str):
        data = {
            "config": {k: v for k, v in self.config.__dict__.items() if not k.startswith("_")},
            "observations": [o.to_dict() for o in self._observations],
            "sources": {k: v.to_dict() for k, v in self._sources.items()},
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: str) -> ObservatoryV2:
        with open(path) as f:
            data = json.load(f)
        config_data = data.get("config", {})
        config = ObservatoryV2Config(**{k: v for k, v in config_data.items() if k in ObservatoryV2Config.__dataclass_fields__})
        obs = cls(config)
        for od in data.get("observations", []):
            observation = IntegratedObservation(
                timestamp=od["timestamp"],
                repo_evolution=od.get("repo_evolution", {}),
                runtime_trace=od.get("runtime_trace"),
                ecosystem_intelligence=od.get("ecosystem_intelligence", {}),
                architecture_fitness=od.get("architecture_fitness", {}),
                invariant_systems=od.get("invariant_systems", {}),
                coordination_telemetry=od.get("coordination_telemetry"),
                skill_transfer=od.get("skill_transfer"),
                confidence_calibration=od.get("confidence_calibration", {}),
                risk_forecast=od.get("risk_forecast", {}),
            )
            obs._observations.append(observation)
        for sid, sd in data.get("sources", {}).items():
            obs._sources[sid] = TelemetrySource(**sd)
        return obs
