import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class EventCategory(str, Enum):
    COMMAND = "command"
    ONBOARDING = "onboarding"
    ACTIVATION = "activation"
    RETENTION = "retention"
    ERROR = "error"
    CRASH = "crash"
    WORKFLOW = "workflow"
    SUPPORT = "support"
    FEEDBACK = "feedback"
    SYSTEM = "system"


class AnalyticsEventType(str, Enum):
    COMMAND_INVOKED = "command.invoked"
    COMMAND_COMPLETED = "command.completed"
    COMMAND_FAILED = "command.failed"
    COMMAND_ABANDONED = "command.abandoned"
    ONBOARDING_STARTED = "onboarding.started"
    ONBOARDING_STEP = "onboarding.step"
    ONBOARDING_COMPLETED = "onboarding.completed"
    ONBOARDING_ABANDONED = "onboarding.abandoned"
    ACTIVATION_FIRST_VALUE = "activation.first_value"
    ACTIVATION_MILESTONE = "activation.milestone"
    SESSION_STARTED = "session.started"
    SESSION_ENDED = "session.ended"
    DAILY_ACTIVE = "daily.active"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_ABANDONED = "workflow.abandoned"
    ERROR_OCCURRED = "error.occurred"
    CRASH_OCCURRED = "crash.occurred"
    CRASH_REPORTED = "crash.reported"
    SUPPORT_TICKET = "support.ticket"
    FEEDBACK_SUBMITTED = "feedback.submitted"
    TELEMETRY_OPT_IN = "telemetry.opt_in"
    TELEMETRY_OPT_OUT = "telemetry.opt_out"
    PERSONA_DETECTED = "persona.detected"
    USER_PROPERTY = "user.property"


@dataclass
class AnalyticsEvent:
    event_type: AnalyticsEventType
    category: EventCategory
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    user_id: str = ""
    session_id: str = ""
    properties: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "category": self.category.value,
            "timestamp": self.timestamp,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "properties": self.properties,
            "tags": self.tags,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata,
        }
