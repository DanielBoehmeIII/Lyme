from __future__ import annotations

import math
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AutonomyLevel(str, Enum):
    FULL_AUTONOMY = "full_autonomy"
    AUTOMATIC_WITH_VERIFICATION = "automatic_with_verification"
    ASK_PERMISSION = "ask_permission"
    REQUEST_CLARIFICATION = "request_clarification"
    REQUIRE_VERIFICATION = "require_verification"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    BLOCKED = "blocked"


class RiskDomain(str, Enum):
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    DATA = "data"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    EXECUTION = "execution"
    SECURITY = "security"
    STATE = "state"


@dataclass
class TaskRisk:
    risk_score: float = 0.0
    domain: RiskDomain = RiskDomain.FILE_SYSTEM
    description: str = ""
    file_path: str = ""
    complexity: float = 0.0
    blast_radius: float = 0.0
    uncertainty: float = 0.0
    historical_failure_rate: float = 0.0
    verification_coverage: float = 0.0
    architectural_impact: float = 0.0

    def to_dict(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "domain": self.domain.value,
            "description": self.description,
            "file_path": self.file_path,
            "complexity": self.complexity,
            "blast_radius": self.blast_radius,
            "uncertainty": self.uncertainty,
            "historical_failure_rate": self.historical_failure_rate,
            "verification_coverage": self.verification_coverage,
            "architectural_impact": self.architectural_impact,
        }


@dataclass
class TrustModel:
    trust_score: float = 0.5
    task_type_scores: Dict[str, float] = field(default_factory=dict)
    subsystem_scores: Dict[str, float] = field(default_factory=dict)
    recency_weighted_accuracy: float = 0.5
    total_tasks_attempted: int = 0
    total_failures: int = 0
    recent_successes: int = 0
    recent_failures: int = 0
    calibration_bias: float = 0.0
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "trust_score": self.trust_score,
            "task_type_scores": self.task_type_scores,
            "subsystem_scores": self.subsystem_scores,
            "recency_weighted_accuracy": self.recency_weighted_accuracy,
            "total_tasks_attempted": self.total_tasks_attempted,
            "total_failures": self.total_failures,
            "recent_successes": self.recent_successes,
            "recent_failures": self.recent_failures,
            "calibration_bias": self.calibration_bias,
            "last_updated": self.last_updated,
        }


@dataclass
class EscalationLog:
    escalation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    task_description: str = ""
    autonomy_level: AutonomyLevel = AutonomyLevel.FULL_AUTONOMY
    risk_score: float = 0.0
    reason: str = ""
    resolved_by: str = ""
    resolution: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "escalation_id": self.escalation_id,
            "timestamp": self.timestamp,
            "task_description": self.task_description[:200],
            "autonomy_level": self.autonomy_level.value,
            "risk_score": self.risk_score,
            "reason": self.reason,
            "resolved_by": self.resolved_by,
            "resolution": self.resolution[:200],
            "duration_ms": self.duration_ms,
        }


class AdaptiveTrustSystem:
    def __init__(self):
        self._trust_model = TrustModel()
        self._escalation_log: List[EscalationLog] = []
        self._risk_history: List[Dict[str, Any]] = []
        self._decision_history: List[Dict[str, Any]] = []
        self._calibration_history: List[float] = []

    def estimate_task_risk(self, task_description: str, file_path: str = "",
                           task_type: str = "", subsystem: str = "",
                           complexity: float = 0.0,
                           verification_coverage: float = 0.0,
                           runtime_traces: List[Dict[str, Any]] = None) -> TaskRisk:
        risk_score = complexity * 0.3
        blast_radius = 0.5

        if file_path:
            if task_type and task_type in self._trust_model.task_type_scores:
                task_trust = self._trust_model.task_type_scores[task_type]
                risk_score += (1 - task_trust) * 0.2
            if subsystem and subsystem in self._trust_model.subsystem_scores:
                sub_trust = self._trust_model.subsystem_scores[subsystem]
                risk_score += (1 - sub_trust) * 0.15

        if "delete" in task_description.lower() or "remove" in task_description.lower():
            risk_score += 0.2
            blast_radius += 0.2
        if "config" in task_description.lower() or "credential" in task_description.lower():
            risk_score += 0.15
        if "migration" in task_description.lower() or "refactor" in task_description.lower():
            risk_score += 0.1
            blast_radius += 0.3
        if "database" in task_description.lower() or "schema" in task_description.lower():
            risk_score += 0.25
            blast_radius += 0.4

        verification_risk = (1 - verification_coverage) * 0.15
        risk_score += verification_risk

        uncertainty = self._estimate_uncertainty(task_description, file_path)
        risk_score += uncertainty * 0.2

        historical_failure_rate = 0.0
        if self._trust_model.total_tasks_attempted > 0:
            historical_failure_rate = self._trust_model.total_failures / self._trust_model.total_tasks_attempted
            risk_score += historical_failure_rate * 0.1

        risk_score = min(1.0, risk_score)
        domain = self._classify_risk_domain(task_description, file_path)

        return TaskRisk(
            risk_score=risk_score,
            domain=domain,
            description=task_description,
            file_path=file_path,
            complexity=complexity,
            blast_radius=min(1.0, blast_radius),
            uncertainty=uncertainty,
            historical_failure_rate=historical_failure_rate,
            verification_coverage=verification_coverage,
            architectural_impact=0.0,
        )

    def determine_autonomy(self, task_risk: TaskRisk) -> AutonomyLevel:
        risk = task_risk.risk_score
        trust = self._trust_model.trust_score
        combined = risk * (1 - trust)

        if combined < 0.1:
            return AutonomyLevel.FULL_AUTONOMY
        elif combined < 0.25:
            return AutonomyLevel.AUTOMATIC_WITH_VERIFICATION
        elif combined < 0.4:
            return AutonomyLevel.ASK_PERMISSION
        elif combined < 0.55:
            return AutonomyLevel.REQUEST_CLARIFICATION
        elif combined < 0.7:
            return AutonomyLevel.REQUIRE_VERIFICATION
        else:
            return AutonomyLevel.ESCALATE_TO_HUMAN

    def decide_autonomy(self, task_description: str, file_path: str = "",
                        task_type: str = "", subsystem: str = "",
                        complexity: float = 0.0,
                        verification_coverage: float = 0.0,
                        user_confidence: float = 1.0,
                        runtime_traces: List[Dict[str, Any]] = None) -> AutonomyLevel:
        task_risk = self.estimate_task_risk(
            task_description=task_description,
            file_path=file_path,
            task_type=task_type,
            subsystem=subsystem,
            complexity=complexity,
            verification_coverage=verification_coverage,
            runtime_traces=runtime_traces,
        )
        task_risk.risk_score = task_risk.risk_score * (1 + (1 - user_confidence) * 0.3)
        task_risk.risk_score = min(1.0, task_risk.risk_score)

        autonomy = self.determine_autonomy(task_risk)

        decision = {
            "timestamp": time.time(),
            "task": task_description[:100],
            "risk_score": task_risk.risk_score,
            "autonomy": autonomy.value,
            "trust_score": self._trust_model.trust_score,
        }
        self._decision_history.append(decision)

        return autonomy

    def record_outcome(self, task_description: str, autonomy_level: AutonomyLevel,
                       success: bool, user_feedback: float = 0.0,
                       task_type: str = "", subsystem: str = ""):
        self._trust_model.total_tasks_attempted += 1
        if success:
            self._trust_model.recent_successes += 1
        else:
            self._trust_model.total_failures += 1
            self._trust_model.recent_failures += 1

        if task_type:
            current = self._trust_model.task_type_scores.get(task_type, 0.5)
            delta = 0.05 if success else -0.1
            self._trust_model.task_type_scores[task_type] = max(0.0, min(1.0, current + delta))

        if subsystem:
            current = self._trust_model.subsystem_scores.get(subsystem, 0.5)
            delta = 0.05 if success else -0.1
            self._trust_model.subsystem_scores[subsystem] = max(0.0, min(1.0, current + delta))

        accuracy = self._trust_model.recent_successes / max(
            self._trust_model.recent_successes + self._trust_model.recent_failures, 1
        )
        self._trust_model.recency_weighted_accuracy = (
            self._trust_model.recency_weighted_accuracy * 0.7 + accuracy * 0.3
        )

        trust_delta = 0.03 if success else -0.08
        if user_feedback != 0:
            trust_delta += user_feedback * 0.05
        self._trust_model.trust_score = max(0.0, min(1.0, self._trust_model.trust_score + trust_delta))
        self._trust_model.last_updated = time.time()

        self._risk_history.append({
            "timestamp": time.time(),
            "success": success,
            "autonomy": autonomy_level.value,
        })

    def record_escalation(self, task_description: str, autonomy_level: AutonomyLevel,
                          risk_score: float, reason: str,
                          resolved_by: str = "", resolution: str = "",
                          duration_ms: float = 0.0) -> EscalationLog:
        log = EscalationLog(
            task_description=task_description,
            autonomy_level=autonomy_level,
            risk_score=risk_score,
            reason=reason,
            resolved_by=resolved_by,
            resolution=resolution,
            duration_ms=duration_ms,
        )
        self._escalation_log.append(log)
        return log

    def calibrate_confidence(self, predicted_confidence: float, actual_outcome: bool) -> float:
        error = predicted_confidence - (1.0 if actual_outcome else 0.0)
        self._calibration_history.append(error)
        recent_errors = self._calibration_history[-20:]
        self._trust_model.calibration_bias = sum(recent_errors) / max(len(recent_errors), 1)
        adjusted = predicted_confidence - self._trust_model.calibration_bias
        return max(0.0, min(1.0, adjusted))

    def get_trust_summary(self) -> Dict[str, Any]:
        return {
            "trust_score": self._trust_model.trust_score,
            "autonomy_distribution": self._autonomy_distribution(),
            "task_type_scores": dict(self._trust_model.task_type_scores),
            "subsystem_scores": dict(self._trust_model.subsystem_scores),
            "calibration_bias": self._trust_model.calibration_bias,
            "total_tasks": self._trust_model.total_tasks_attempted,
            "failure_rate": self._trust_model.total_failures / max(self._trust_model.total_tasks_attempted, 1),
            "recent_accuracy": self._trust_model.recency_weighted_accuracy,
            "escalation_count": len(self._escalation_log),
        }

    def _estimate_uncertainty(self, task_description: str, file_path: str) -> float:
        uncertainty = 0.0
        uncertain_terms = ["might", "maybe", "probably", "unclear", "unknown", "if possible"]
        for term in uncertain_terms:
            if term in task_description.lower():
                uncertainty += 0.1
        if not file_path:
            uncertainty += 0.15
        return min(0.5, uncertainty)

    def _classify_risk_domain(self, task_description: str, file_path: str) -> RiskDomain:
        task_lower = task_description.lower()
        file_lower = (file_path or "").lower()
        if any(t in task_lower for t in ["delete", "remove", "write", "create", "modify"]):
            return RiskDomain.FILE_SYSTEM
        if any(t in task_lower for t in ["config", "setting", "env", "credential"]):
            return RiskDomain.CONFIGURATION
        if any(t in task_lower for t in ["network", "api", "http", "request", "url"]):
            return RiskDomain.NETWORK
        if any(t in task_lower for t in ["dependency", "install", "package", "import"]):
            return RiskDomain.DEPENDENCY
        if any(t in task_lower for t in ["security", "auth", "permission", "encrypt"]):
            return RiskDomain.SECURITY
        if any(t in task_lower for t in ["state", "cache", "store", "database", "db"]):
            return RiskDomain.STATE
        if any(t in task_lower for t in ["exec", "run", "shell", "command", "process"]):
            return RiskDomain.EXECUTION
        if any(t in task_lower for t in ["data", "import", "export", "migrate"]):
            return RiskDomain.DATA
        return RiskDomain.FILE_SYSTEM

    def _autonomy_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = defaultdict(int)
        for decision in self._decision_history[-100:]:
            dist[decision.get("autonomy", "unknown")] += 1
        return dict(dist)


class ConfidenceCalibrator:
    def __init__(self, trust_system: AdaptiveTrustSystem):
        self.trust_system = trust_system
        self._calibration_data: List[Tuple[float, bool]] = []

    def calibrate(self, predicted_confidence: float, task_risk: TaskRisk) -> float:
        adjusted = self.trust_system.calibrate_confidence(predicted_confidence, True)

        risk_penalty = task_risk.risk_score * 0.15
        adjusted -= risk_penalty

        if len(self._calibration_data) > 10:
            recent = self._calibration_data[-10:]
            avg_pred = sum(p for p, _ in recent) / len(recent)
            avg_outcome = sum(1.0 for _, o in recent if o) / len(recent)
            overconfidence_penalty = max(0, avg_pred - avg_outcome) * 0.3
            adjusted -= overconfidence_penalty

        return max(0.0, min(1.0, adjusted))

    def record_calibration(self, predicted: float, actual_success: bool):
        self._calibration_data.append((predicted, actual_success))

    def calibration_report(self) -> Dict[str, Any]:
        if not self._calibration_data:
            return {"error": "No calibration data"}
        predictions = [p for p, _ in self._calibration_data]
        outcomes = [1.0 if o else 0.0 for _, o in self._calibration_data]
        mae = sum(abs(p - o) for p, o in zip(predictions, outcomes)) / len(self._calibration_data)
        bias = sum(p - o for p, o in zip(predictions, outcomes)) / len(self._calibration_data)
        return {
            "mae": mae,
            "bias": bias,
            "samples": len(self._calibration_data),
            "overconfidence": bias > 0.05,
            "underconfidence": bias < -0.05,
        }
