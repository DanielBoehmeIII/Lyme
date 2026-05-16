from .schema import (
    OpenAgentTrace,
    TraceHeader,
    TraceEvent,
    ModelCallEvent,
    ToolCallEvent,
    FileReadEvent,
    FileEditEvent,
    TestRunEvent,
    FailedAttemptEvent,
    EvidenceClaimEvent,
    VerificationStepEvent,
    HumanInterventionEvent,
    ConfidenceChangeEvent,
    RollbackEvent,
    EventType,
    RollbackStrategy,
    VerificationResult,
    ConfidenceLevel,
    AgentIdentity,
    SystemMetadata,
)
from .validator import OpenTraceValidator, ValidationResult, ValidationError
from .converter import LymeTraceConverter
from .comparison import TraceComparisonReport, TraceComparer

SCHEMA_VERSION = "0.7.0"
SCHEMA_NAME = "open-agent-trace-standard"
SCHEMA_URN = "urn:lyme:standard:open-agent-trace:v1"

__all__ = [
    "OpenAgentTrace", "TraceHeader", "TraceEvent",
    "ModelCallEvent", "ToolCallEvent", "FileReadEvent",
    "FileEditEvent", "TestRunEvent", "FailedAttemptEvent",
    "EvidenceClaimEvent", "VerificationStepEvent",
    "HumanInterventionEvent", "ConfidenceChangeEvent", "RollbackEvent",
    "EventType", "RollbackStrategy", "VerificationResult", "ConfidenceLevel",
    "AgentIdentity", "SystemMetadata",
    "OpenTraceValidator", "ValidationResult", "ValidationError",
    "LymeTraceConverter",
    "TraceComparisonReport", "TraceComparer",
    "SCHEMA_VERSION", "SCHEMA_NAME", "SCHEMA_URN",
]
