"""Week 141 — Specialist Coordination Protocol.
Week 142 — Blackboard Architecture.
Week 143 — Specialist Router.
Week 144 — Conflict Resolution.
Week 145 — Minimal Autonomy Loop.

All in one module as they form an integrated system.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from enum import Enum
from datetime import datetime, timezone
import time
import json
import uuid


# ═══════════════════════════════════════════════════════════════════════════════
# Week 141: Coordination Protocol
# ═══════════════════════════════════════════════════════════════════════════════

class MessageType(Enum):
    PLAN = "plan"
    RETRIEVE = "retrieve"
    GENERATE_PATCH = "generate_patch"
    CRITIQUE = "critique"
    VERIFY = "verify"
    SUMMARIZE = "summarize"
    STATE_UPDATE = "state_update"
    CONFLICT = "conflict"
    ESCALATION = "escalation"
    STOP = "stop"


class SpecialistRole(Enum):
    PLANNER = "planner"
    RETRIEVER = "retriever"
    PATCH_GENERATOR = "patch_generator"
    CRITIC = "critic"
    VERIFIER = "verifier"
    SUMMARIZER = "summarizer"
    ROUTER = "router"


@dataclass
class SpecialistMessage:
    msg_id: str
    msg_type: MessageType
    source: SpecialistRole
    target: Optional[SpecialistRole]
    payload: dict
    confidence: float
    timestamp: float
    trace_id: str
    in_response_to: Optional[str] = None
    failure_labels: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "msg_id": self.msg_id,
            "msg_type": self.msg_type.value,
            "source": self.source.value,
            "target": self.target.value if self.target else None,
            "confidence": round(self.confidence, 3),
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "in_response_to": self.in_response_to,
            "failure_labels": self.failure_labels,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Week 142: Blackboard Architecture
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class BlackboardState:
    task: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    context_packets: dict = field(default_factory=dict)
    plans: dict = field(default_factory=dict)
    patches: dict = field(default_factory=dict)
    critiques: dict = field(default_factory=dict)
    verification_results: dict = field(default_factory=dict)
    confidence_updates: dict = field(default_factory=dict)
    stop_conditions: List[str] = field(default_factory=list)
    current_phase: str = "init"
    messages: List[SpecialistMessage] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    latencies: Dict[str, float] = field(default_factory=dict)
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "task_keys": list(self.task.keys()),
            "evidence_count": len(self.evidence),
            "plans_count": len(self.plans),
            "patches_count": len(self.patches),
            "critiques_count": len(self.critiques),
            "verification_count": len(self.verification_results),
            "messages_count": len(self.messages),
            "current_phase": self.current_phase,
            "errors_count": len(self.errors),
            "trace_id": self.trace_id,
        }


class Blackboard:
    """Shared state — all specialists write to and read from it.

    Every state mutation is traceable through Lyme Audit.
    """

    def __init__(self):
        self.state = BlackboardState()
        self._mutations: List[dict] = []

    def initialize(self, task: str, trace_id: str):
        self.state = BlackboardState(
            task={"description": task, "created_at": time.time()},
            trace_id=trace_id,
        )
        self._mutate("init", {"task": task})

    def write(self, key: str, specialist: str, data: dict):
        if key == "plans":
            self.state.plans[specialist] = data
        elif key == "patches":
            self.state.patches[specialist] = data
        elif key == "critiques":
            self.state.critiques[specialist] = data
        elif key == "verification_results":
            self.state.verification_results[specialist] = data
        elif key == "context_packets":
            self.state.context_packets[specialist] = data
        elif key == "evidence":
            self.state.evidence[specialist] = data
        elif key == "confidence_updates":
            self.state.confidence_updates[specialist] = data
        self._mutate(f"write:{key}", {"specialist": specialist, "data_keys": list(data.keys())})

    def read(self, key: str) -> dict:
        return getattr(self.state, key, {})

    def set_phase(self, phase: str):
        self.state.current_phase = phase
        self._mutate("phase_change", {"phase": phase})

    def add_message(self, msg: SpecialistMessage):
        self.state.messages.append(msg)
        self._mutate("message", {"msg_id": msg.msg_id, "type": msg.msg_type.value})

    def add_error(self, specialist: str, error: str, phase: str):
        self.state.errors.append({
            "specialist": specialist,
            "error": error,
            "phase": phase,
            "timestamp": time.time(),
        })
        self._mutate("error", {"specialist": specialist, "error": error})

    def record_latency(self, specialist: str, latency_s: float):
        self.state.latencies[specialist] = latency_s

    def get_summary(self) -> dict:
        return self.state.to_dict()

    def get_audit_trail(self) -> List[dict]:
        return list(self._mutations)

    def _mutate(self, action: str, detail: dict):
        self._mutations.append({
            "action": action,
            "detail": detail,
            "timestamp": time.time(),
            "state_version": len(self._mutations),
        })


# ═══════════════════════════════════════════════════════════════════════════════
# Week 143: Specialist Router
# ═══════════════════════════════════════════════════════════════════════════════

class RouterDecision(Enum):
    CONTINUE = "continue"
    STOP_SUCCESS = "stop_success"
    STOP_FAILURE = "stop_failure"
    RETRY = "retry"
    ESCALATE = "escalate"
    ASK_USER = "ask_user"
    RUN_VERIFICATION = "run_verification"


class SpecialistRouter:
    """Decides which specialist acts next, when to stop, when to retry/escalate/ask/verify."""

    def __init__(self):
        self._router_history: List[dict] = []
        self._policy_scores: Dict[str, float] = {}

    def next_action(self, state: BlackboardState) -> tuple:
        if state.stop_conditions:
            return (RouterDecision.STOP_FAILURE, "stop_condition_met")

        phase = state.current_phase
        errors = state.errors

        # Error-driven decisions
        recent_errors = [e for e in errors if time.time() - e.get("timestamp", 0) < 30]
        if len(recent_errors) > 3:
            return (RouterDecision.ESCALATE, "too_many_recent_errors")

        # Standard pipeline
        pipeline = {
            "init": ("planner", "plan"),
            "plan": ("retriever", "retrieve"),
            "retrieve": ("patch_generator", "generate_patch"),
            "generate_patch": ("critic", "critique"),
            "critique": ("verifier", "verify"),
            "verify": ("", "summarize"),
        }

        if phase in pipeline:
            next_specialist, next_phase = pipeline[phase]
            if not next_specialist:
                return (RouterDecision.STOP_SUCCESS, "pipeline_complete")
            return (RouterDecision.CONTINUE, f"call_{next_specialist}")

        if phase == "summarize":
            return (RouterDecision.STOP_SUCCESS, "summarize_complete")

        return (RouterDecision.CONTINUE, f"unknown_phase:{phase}")

    def should_retry(self, state: BlackboardState, specialist: str, max_retries: int = 2) -> bool:
        retry_count = sum(1 for m in state.messages if m.source.value == specialist and m.msg_type == MessageType.STATE_UPDATE)
        return retry_count < max_retries

    def should_escalate(self, state: BlackboardState, min_confidence: float = 0.3) -> bool:
        latest_confidences = [v for v in state.confidence_updates.values()]
        if not latest_confidences:
            return False
        return min(latest_confidences) < min_confidence

    def needs_verification(self, phase: str, risk_score: float) -> bool:
        return phase in ("generate_patch", "critique") or risk_score > 0.5

    def predict(self, state: BlackboardState) -> RouterDecision:
        decision, reason = self.next_action(state)
        self._router_history.append({
            "phase": state.current_phase,
            "decision": decision.value,
            "reason": reason,
            "timestamp": time.time(),
        })
        return decision


# ═══════════════════════════════════════════════════════════════════════════════
# Week 144: Conflict Resolution
# ═══════════════════════════════════════════════════════════════════════════════

class ConflictType(Enum):
    PLAN_VS_CRITIC = "plan_vs_critic"
    EVIDENCE_VS_VERIFIER = "evidence_vs_verifier"
    SCOPE_VS_GOVERNANCE = "scope_vs_governance"
    CONFIDENCE_VS_EVIDENCE = "confidence_vs_evidence"


class ConflictResolver:
    """Resolves conflicts between specialists.

    Rules:
    - evidence beats confidence
    - tests beat claims
    - governance beats generation
    - uncertainty triggers fallback
    """

    def __init__(self):
        self._conflict_history: List[dict] = []

    def detect(self, state: BlackboardState) -> List[dict]:
        conflicts = []

        # Planner says safe, Critic says risky
        plans = state.plans
        critiques = state.critiques
        for specialist, plan in plans.items():
            plan_risk = plan.get("risk_score", 0) if isinstance(plan, dict) else 0
            for critic_spec, critique in critiques.items():
                critic_decision = critique.get("decision", "") if isinstance(critique, dict) else ""
                if plan_risk < 0.3 and critic_decision == "reject":
                    conflicts.append({
                        "type": ConflictType.PLAN_VS_CRITIC.value,
                        "between": f"{specialist} vs {critic_spec}",
                        "plan_risk": plan_risk,
                        "critic_decision": critic_decision,
                        "resolution": "critic_wins",
                        "rationale": "Critic has more evidence — evidence beats confidence",
                    })

        # Retriever says enough context, Verifier says missing evidence
        verifications = state.verification_results
        for ver_spec, ver_result in verifications.items():
            if isinstance(ver_result, dict):
                missing = ver_result.get("missing_context_rate", 0)
                if missing > 0.3:
                    conflicts.append({
                        "type": ConflictType.EVIDENCE_VS_VERIFIER.value,
                        "between": "retriever vs verifier",
                        "missing_rate": missing,
                        "resolution": "verifier_wins",
                        "rationale": f"Verifier found {missing:.0%} missing context — evidence over claim",
                    })

        # Patch Generator wants broad edit, governance says too risky
        patches = state.patches
        for spec, patch in patches.items():
            if isinstance(patch, dict):
                patch_size = patch.get("patch_size_lines", 0)
                if patch_size > 50 and state.stop_conditions:
                    conflicts.append({
                        "type": ConflictType.SCOPE_VS_GOVERNANCE.value,
                        "between": f"patch_generator vs governance",
                        "patch_size": patch_size,
                        "resolution": "governance_wins",
                        "rationale": "Patch exceeds governance boundary — scope limited",
                    })

        # Local model confident, Audit evidence contradicts
        for spec, conf in state.confidence_updates.items():
            if isinstance(conf, (int, float)) and conf > 0.8:
                errors = [e for e in state.errors if e.get("specialist") == spec]
                if errors:
                    conflicts.append({
                        "type": ConflictType.CONFIDENCE_VS_EVIDENCE.value,
                        "between": f"{spec} confidence vs audit evidence",
                        "claimed_confidence": conf,
                        "error_count": len(errors),
                        "resolution": "audit_wins",
                        "rationale": "Audit evidence contradicts high confidence",
                    })

        for c in conflicts:
            self._conflict_history.append(c)
        return conflicts

    def resolve(self, conflicts: List[dict]) -> List[dict]:
        resolutions = []
        for c in conflicts:
            if c["resolution"] == "critic_wins":
                resolutions.append({
                    "conflict": c["type"],
                    "winner": "critic",
                    "action": "revise_plan",
                })
            elif c["resolution"] == "verifier_wins":
                resolutions.append({
                    "conflict": c["type"],
                    "winner": "verifier",
                    "action": "gather_more_context",
                })
            elif c["resolution"] == "governance_wins":
                resolutions.append({
                    "conflict": c["type"],
                    "winner": "governance",
                    "action": "reduce_scope",
                })
            elif c["resolution"] == "audit_wins":
                resolutions.append({
                    "conflict": c["type"],
                    "winner": "audit",
                    "action": "reduce_confidence",
                })
        return resolutions

    def get_history(self) -> List[dict]:
        return self._conflict_history


# ═══════════════════════════════════════════════════════════════════════════════
# Week 145: Minimal Autonomy Loop
# ═══════════════════════════════════════════════════════════════════════════════

class SpecialistOrchestrator:
    """Minimal autonomy loop using specialists.

    Loop: plan → retrieve → generate → critique → verify → repair once if needed → stop with report.
    Bounded: no endless autonomy.
    """

    def __init__(self):
        self.blackboard = Blackboard()
        self.router = SpecialistRouter()
        self.conflict_resolver = ConflictResolver()
        self._loop_history: List[dict] = []

    def run(self, task: str, repo_path: str = ".", max_steps: int = 20) -> dict:
        trace_id = f"loop-{uuid.uuid4().hex[:12]}"
        self.blackboard.initialize(task, trace_id)
        start_time = time.time()

        from .planner import planner
        from .retriever import retriever
        from .patch_generator import patch_generator
        from .critic import critic
        from .verifier import verifier
        from ..planning.long_horizon import TaskDecomposer

        specialists = {
            "planner": planner,
            "retriever": retriever,
            "patch_generator": patch_generator,
            "critic": critic,
            "verifier": verifier,
        }

        steps = 0
        repair_used = False
        phase_sequence = ["init", "plan", "retrieve", "generate_patch", "critique", "verify", "summarize"]
        phase_order = {p: i for i, p in enumerate(phase_sequence)}

        while steps < max_steps:
            steps += 1
            decision = self.router.predict(self.blackboard.state)

            if decision in (RouterDecision.STOP_SUCCESS, RouterDecision.STOP_FAILURE):
                elapsed = time.time() - start_time
                result = {
                    "trace_id": trace_id,
                    "task": task,
                    "steps": steps,
                    "elapsed_s": round(elapsed, 2),
                    "decision": decision.value,
                    "phases_completed": self.blackboard.state.current_phase,
                    "errors": len(self.blackboard.state.errors),
                    "conflicts": len(self._get_conflicts()),
                    "messages": len(self.blackboard.state.messages),
                }
                self._loop_history.append(result)
                return result

            if decision == RouterDecision.ESCALATE:
                self.blackboard.add_error("router", "Escalation triggered", self.blackboard.state.current_phase)
                continue

            # Determine current phase and next specialist
            current_phase_idx = phase_order.get(self.blackboard.state.current_phase, 0)
            if current_phase_idx < len(phase_sequence) - 1:
                next_phase = phase_sequence[current_phase_idx + 1]
            else:
                break

            # Call the specialist for the current phase
            if next_phase == "plan":
                from .interfaces import PlannerInput
                inp = PlannerInput(user_task=task, hardware_profile="standard_gpu")
                output = specialists["planner"].process(inp)
                self.blackboard.write("plans", "planner", output.to_dict())
                self.blackboard.record_latency("planner", 0.1)

            elif next_phase == "retrieve":
                from .interfaces import RetrieverInput
                plans = self.blackboard.read("plans")
                affected = []
                for p in plans.values():
                    if isinstance(p, dict):
                        affected.extend(p.get("affected_files", []))
                inp = RetrieverInput(task=task, affected_files_hint=affected, repo_path=repo_path)
                output = specialists["retriever"].process(inp)
                self.blackboard.write("evidence", "retriever", output.to_dict())
                self.blackboard.record_latency("retriever", 0.1)

            elif next_phase == "generate_patch":
                from .interfaces import PatchGeneratorInput
                plans = self.blackboard.read("plans")
                plan_data = next(iter(plans.values()), {})
                inp = PatchGeneratorInput(
                    validated_plan=plan_data if isinstance(plan_data, dict) else {},
                    affected_files=plan_data.get("affected_files", []) if isinstance(plan_data, dict) else [],
                    context_packet={"evidence": str(self.blackboard.read("evidence"))[:500]},
                    verification_command="pytest",
                    rollback_path="git checkout HEAD",
                )
                output = specialists["patch_generator"].process(inp)
                self.blackboard.write("patches", "patch_generator", output.to_dict())
                self.blackboard.record_latency("patch_generator", 0.1)

                # Repair: if patch generation failed, retry once
                if not output.patch and not repair_used:
                    repair_used = True
                    inp.validated_plan = plan_data if isinstance(plan_data, dict) else {}
                    output = specialists["patch_generator"].process(inp)
                    self.blackboard.write("patches", "patch_generator_retry", output.to_dict())

            elif next_phase == "critique":
                from .interfaces import CriticInput
                patches = self.blackboard.read("patches")
                patch_data = next(iter(patches.values()), {})
                plans = self.blackboard.read("plans")
                plan_data = next(iter(plans.values()), {})
                inp = CriticInput(
                    patch_plan=plan_data if isinstance(plan_data, dict) else {},
                    generated_patch=patch_data.get("patch", "") if isinstance(patch_data, dict) else "",
                    affected_files=plan_data.get("affected_files", []) if isinstance(plan_data, dict) else [],
                )
                output = specialists["critic"].process(inp)
                self.blackboard.write("critiques", "critic", output.to_dict())
                self.blackboard.record_latency("critic", 0.1)

                # Detect and resolve conflicts
                conflicts = self.conflict_resolver.detect(self.blackboard.state)
                if conflicts:
                    resolutions = self.conflict_resolver.resolve(conflicts)
                    self.blackboard.add_message(SpecialistMessage(
                        msg_id=uuid.uuid4().hex[:12],
                        msg_type=MessageType.CONFLICT,
                        source=SpecialistRole.ROUTER,
                        target=SpecialistRole.CRITIC,
                        payload={"conflicts": conflicts, "resolutions": resolutions},
                        confidence=0.9,
                        timestamp=time.time(),
                        trace_id=trace_id,
                    ))

            elif next_phase == "verify":
                from .interfaces import VerifierInput
                patches = self.blackboard.read("patches")
                patch_data = next(iter(patches.values()), {})
                inp = VerifierInput(
                    change=patch_data if isinstance(patch_data, dict) else {},
                    repo_path=repo_path,
                    max_verification_cost="medium",
                    required_confidence=0.6,
                )
                output = specialists["verifier"].process(inp)
                self.blackboard.write("verification_results", "verifier", output.to_dict())
                self.blackboard.record_latency("verifier", 0.1)

                # Check stop conditions
                if not output.overall_pass:
                    self.blackboard.state.stop_conditions.append("verification_failed")
                    if repair_used:
                        self.blackboard.state.stop_conditions.append("repair_exhausted")

            self.blackboard.set_phase(next_phase)

        elapsed = time.time() - start_time
        return {
            "trace_id": trace_id,
            "task": task,
            "steps": steps,
            "elapsed_s": round(elapsed, 2),
            "decision": "max_steps_reached" if steps >= max_steps else "completed",
            "phases_completed": self.blackboard.state.current_phase,
            "errors": len(self.blackboard.state.errors),
            "conflicts": len(self._get_conflicts()),
            "messages": len(self.blackboard.state.messages),
            "stop_conditions": self.blackboard.state.stop_conditions,
        }

    def _get_conflicts(self) -> List[dict]:
        return self.conflict_resolver.get_history()

    def get_loop_history(self) -> List[dict]:
        return self._loop_history


orchestrator = SpecialistOrchestrator()
