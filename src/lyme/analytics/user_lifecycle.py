import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class UserState(str, Enum):
    ANONYMOUS = "anonymous"
    INSTALLED = "installed"
    ONBOARDING = "onboarding"
    ACTIVATED = "activated"
    ENGAGED = "engaged"
    CHURNED = "churned"
    RESURRECTED = "resurrected"


class OnboardingPhase(str, Enum):
    INSTALL = "install"
    FIRST_COMMAND = "first_command"
    REPO_INIT = "repo_init"
    FIRST_DOCTOR = "first_doctor"
    FIRST_DASHBOARD = "first_dashboard"
    FIRST_FIX = "first_fix"
    FIRST_BENCH = "first_bench"
    COMPLETED = "completed"


class UserPersona(str, Enum):
    INDIE_DEV = "indie_dev"
    AGENCY = "agency"
    OSS_MAINTAINER = "oss_maintainer"
    STARTUP_ENGINEER = "startup_engineer"
    ENTERPRISE_TEAM = "enterprise_team"
    RESEARCHER = "researcher"
    HOBBYIST = "hobbyist"
    UNKNOWN = "unknown"


@dataclass
class ActivationMetric:
    name: str
    achieved: bool = False
    achieved_at: Optional[float] = None
    attempts: int = 0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "achieved": self.achieved,
            "achieved_at": self.achieved_at,
            "attempts": self.attempts,
        }


@dataclass
class RetentionMetric:
    day: int
    active: bool = False
    commands_run: int = 0
    workflows_completed: int = 0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "active": self.active,
            "commands_run": self.commands_run,
            "workflows_completed": self.workflows_completed,
            "errors": self.errors,
        }


@dataclass
class UserProfile:
    user_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: UserState = UserState.ANONYMOUS
    persona: UserPersona = UserPersona.UNKNOWN
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    session_count: int = 0
    total_commands: int = 0
    completed_workflows: int = 0
    abandoned_workflows: int = 0
    errors_count: int = 0
    onboarding_phase: Optional[OnboardingPhase] = None
    activation_metrics: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "state": self.state.value,
            "persona": self.persona.value,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "session_count": self.session_count,
            "total_commands": self.total_commands,
            "completed_workflows": self.completed_workflows,
            "abandoned_workflows": self.abandoned_workflows,
            "errors_count": self.errors_count,
            "onboarding_phase": self.onboarding_phase.value if self.onboarding_phase else None,
            "activation_metrics": {k: v.to_dict() for k, v in self.activation_metrics.items()},
            "tags": self.tags,
            "properties": self.properties,
        }


class UserLifecycleTracker:
    def __init__(self, storage_dir: str = ".lyme/analytics/users"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._profiles: dict[str, UserProfile] = {}
        self._load_all()

    def _profile_path(self, user_id: str) -> Path:
        return self._storage_dir / f"{user_id}.json"

    def _load_all(self):
        for path in self._storage_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                profile = self._from_dict(data)
                self._profiles[profile.user_id] = profile
            except Exception:
                pass

    def _from_dict(self, data: dict) -> UserProfile:
        profile = UserProfile(
            user_id=data.get("user_id", uuid.uuid4().hex[:12]),
            state=UserState(data.get("state", "anonymous")),
            persona=UserPersona(data.get("persona", "unknown")),
            first_seen=data.get("first_seen", time.time()),
            last_seen=data.get("last_seen", time.time()),
            session_count=data.get("session_count", 0),
            total_commands=data.get("total_commands", 0),
            completed_workflows=data.get("completed_workflows", 0),
            abandoned_workflows=data.get("abandoned_workflows", 0),
            errors_count=data.get("errors_count", 0),
            tags=data.get("tags", []),
            properties=data.get("properties", {}),
        )
        phase = data.get("onboarding_phase")
        if phase:
            profile.onboarding_phase = OnboardingPhase(phase)
        metrics_data = data.get("activation_metrics", {})
        for k, v in metrics_data.items():
            profile.activation_metrics[k] = ActivationMetric(
                name=v.get("name", k),
                achieved=v.get("achieved", False),
                achieved_at=v.get("achieved_at"),
                attempts=v.get("attempts", 0),
            )
        return profile

    def get_or_create(self, user_id: str = "") -> UserProfile:
        if not user_id:
            user_id = uuid.uuid4().hex[:12]
        if user_id not in self._profiles:
            self._profiles[user_id] = UserProfile(user_id=user_id)
        return self._profiles[user_id]

    def _save(self, profile: UserProfile):
        path = self._profile_path(profile.user_id)
        path.write_text(json.dumps(profile.to_dict(), indent=2))

    def record_session(self, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.session_count += 1
        profile.last_seen = time.time()
        if profile.state == UserState.ANONYMOUS:
            profile.state = UserState.INSTALLED
        self._save(profile)

    def record_command(self, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.total_commands += 1
        profile.last_seen = time.time()
        if profile.state == UserState.INSTALLED:
            profile.state = UserState.ONBOARDING
        if profile.state == UserState.CHURNED:
            profile.state = UserState.RESURRECTED
        self._check_activation_metrics(profile)
        self._save(profile)

    def record_workflow_completed(self, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.completed_workflows += 1
        profile.last_seen = time.time()
        if profile.state == UserState.ONBOARDING:
            profile.state = UserState.ACTIVATED
        self._save(profile)

    def record_workflow_abandoned(self, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.abandoned_workflows += 1
        profile.last_seen = time.time()
        self._save(profile)

    def record_error(self, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.errors_count += 1
        self._save(profile)

    def set_onboarding_phase(self, phase: OnboardingPhase, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.onboarding_phase = phase
        if phase == OnboardingPhase.COMPLETED:
            profile.state = UserState.ACTIVATED
        self._save(profile)

    def set_persona(self, persona: UserPersona, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.persona = persona
        self._save(profile)

    def set_user_property(self, key: str, value, user_id: str = ""):
        profile = self.get_or_create(user_id)
        profile.properties[key] = value
        self._save(profile)

    def _check_activation_metrics(self, profile: UserProfile):
        if "first_command" not in profile.activation_metrics:
            profile.activation_metrics["first_command"] = ActivationMetric(
                name="first_command", achieved=True, achieved_at=time.time()
            )
        if profile.total_commands >= 5 and "five_commands" not in profile.activation_metrics:
            profile.activation_metrics["five_commands"] = ActivationMetric(
                name="five_commands", achieved=True, achieved_at=time.time()
            )
        if profile.completed_workflows >= 1 and "first_workflow" not in profile.activation_metrics:
            profile.activation_metrics["first_workflow"] = ActivationMetric(
                name="first_workflow", achieved=True, achieved_at=time.time()
            )

    def get_activation_progress(self, user_id: str = "") -> dict:
        profile = self.get_or_create(user_id)
        metrics = profile.activation_metrics
        achieved = sum(1 for m in metrics.values() if m.achieved)
        total = max(len(metrics), 1)
        first_value_time = None
        for m in metrics.values():
            if m.name == "first_command" and m.achieved_at:
                first_value_time = m.achieved_at - profile.first_seen
                break
        return {
            "user_id": profile.user_id,
            "state": profile.state.value,
            "metrics_achieved": achieved,
            "metrics_total": total,
            "completion_pct": round(achieved / total * 100, 1),
            "time_to_first_value_s": round(first_value_time, 1) if first_value_time else None,
            "session_count": profile.session_count,
            "total_commands": profile.total_commands,
            "completed_workflows": profile.completed_workflows,
            "abandoned_workflows": profile.abandoned_workflows,
            "errors_count": profile.errors_count,
        }

    def get_retention(self, user_id: str = "", days: int = 30) -> list[RetentionMetric]:
        profile = self.get_or_create(user_id)
        metrics = []
        for d in range(days):
            metrics.append(RetentionMetric(day=d + 1, active=d == 0))
        return metrics

    def get_lifecycle_summary(self) -> dict:
        if not self._profiles:
            return {"total_users": 0}
        states = {}
        personas = {}
        for p in self._profiles.values():
            states[p.state.value] = states.get(p.state.value, 0) + 1
            personas[p.persona.value] = personas.get(p.persona.value, 0) + 1
        total = len(self._profiles)
        activated = sum(1 for p in self._profiles.values()
                        if p.state in (UserState.ACTIVATED, UserState.ENGAGED))
        return {
            "total_users": total,
            "activated_users": activated,
            "activation_rate": round(activated / total * 100, 1) if total else 0,
            "states": states,
            "personas": personas,
            "total_commands": sum(p.total_commands for p in self._profiles.values()),
            "total_workflows": sum(p.completed_workflows for p in self._profiles.values()),
            "total_abandoned": sum(p.abandoned_workflows for p in self._profiles.values()),
            "total_errors": sum(p.errors_count for p in self._profiles.values()),
        }

    def get_workflow_segmentation(self) -> dict:
        if not self._profiles:
            return {}
        heavy = sum(1 for p in self._profiles.values() if p.total_commands >= 20)
        medium = sum(1 for p in self._profiles.values() if 5 <= p.total_commands < 20)
        light = sum(1 for p in self._profiles.values() if 1 <= p.total_commands < 5)
        inactive = sum(1 for p in self._profiles.values() if p.total_commands == 0)
        return {
            "heavy_users": heavy,
            "medium_users": medium,
            "light_users": light,
            "inactive_users": inactive,
        }


lifecycle_tracker = UserLifecycleTracker()
