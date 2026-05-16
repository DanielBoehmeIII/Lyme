from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from .schema import (
    OpenAgentTrace, TraceEvent, EventType,
    ModelCallEvent, ToolCallEvent, FileReadEvent,
    FileEditEvent, TestRunEvent, FailedAttemptEvent,
    EvidenceClaimEvent, VerificationStepEvent,
    HumanInterventionEvent, ConfidenceChangeEvent, RollbackEvent,
    SCHEMA_URN, SCHEMA_VERSION,
)


@dataclass
class ValidationError:
    field: str = ""
    message: str = ""
    severity: str = "error"
    event_id: Optional[str] = None
    event_index: Optional[int] = None


@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    trace_id: str = ""
    event_count: int = 0

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)

    def summary(self) -> str:
        status = "VALID" if self.valid else "INVALID"
        parts = [
            f"Trace {self.trace_id}: {status}",
            f"  Events: {self.event_count}",
            f"  Errors: {len(self.errors)}",
            f"  Warnings: {len(self.warnings)}",
        ]
        if self.errors:
            parts.append("  Errors:")
            for e in self.errors:
                loc = f"event[{e.event_index}]." if e.event_index is not None else ""
                parts.append(f"    - {loc}{e.field}: {e.message}")
        if self.warnings:
            parts.append("  Warnings:")
            for w in self.warnings:
                loc = f"event[{w.event_index}]." if w.event_index is not None else ""
                parts.append(f"    - {loc}{w.field}: {w.message}")
        return "\n".join(parts)


_EVENT_TYPES = {e.value for e in EventType}
_REQUIRED_MODEL_FIELDS = ["model", "total_tokens"]
_REQUIRED_EVENT_FIELDS = ["id", "type", "timestamp"]


class OpenTraceValidator:
    def __init__(self, strict: bool = True):
        self.strict = strict

    def validate(self, trace: OpenAgentTrace) -> ValidationResult:
        result = ValidationResult(trace_id=trace.header.trace_id)

        schema_urn = trace.header.schema_urn
        if schema_urn != SCHEMA_URN:
            result.warnings.append(ValidationError(
                field="header.schema_urn",
                message=f"Expected {SCHEMA_URN}, got {schema_urn}",
                severity="warning",
            ))

        if not trace.header.trace_id:
            result.errors.append(ValidationError(
                field="header.trace_id",
                message="Trace ID is required",
            ))

        if not trace.header.agent.name:
            result.warnings.append(ValidationError(
                field="header.agent.name",
                message="Agent name is empty",
                severity="warning",
            ))

        result.event_count = len(trace.events)
        seen_ids = set()
        sequences = set()

        for i, event in enumerate(trace.events):
            evt_id = event.get("id", "")
            if not evt_id:
                result.errors.append(ValidationError(
                    field="id", message="Event ID is required",
                    event_index=i,
                ))
            elif evt_id in seen_ids:
                result.errors.append(ValidationError(
                    field="id", message=f"Duplicate event ID: {evt_id}",
                    event_index=i,
                ))
            seen_ids.add(evt_id)

            evt_type = event.get("type", "")
            if not evt_type:
                result.errors.append(ValidationError(
                    field="type", message="Event type is required",
                    event_index=i,
                ))
            elif evt_type not in _EVENT_TYPES:
                result.warnings.append(ValidationError(
                    field="type", message=f"Unknown event type: {evt_type}",
                    severity="warning", event_index=i,
                ))

            if event.get("timestamp", 0) <= 0:
                result.errors.append(ValidationError(
                    field="timestamp", message="Invalid timestamp",
                    event_index=i,
                ))

            seq = event.get("sequence", -1)
            if seq in sequences:
                result.warnings.append(ValidationError(
                    field="sequence", message=f"Duplicate sequence: {seq}",
                    severity="warning", event_index=i,
                ))
            sequences.add(seq)

            self._validate_event_type(event, i, result)

        if result.errors and self.strict:
            result.valid = False
        elif not result.errors:
            result.valid = True
        else:
            result.valid = len([e for e in result.errors if e.severity == "error"]) == 0

        return result

    def _validate_event_type(self, event: dict, index: int, result: ValidationResult):
        evt_type = event.get("type", "")
        if evt_type == EventType.MODEL_CALL:
            for f in _REQUIRED_MODEL_FIELDS:
                if not event.get(f):
                    result.warnings.append(ValidationError(
                        field=f, message=f"Model call missing field: {f}",
                        severity="warning", event_index=index,
                    ))
        elif evt_type == EventType.FILE_EDIT:
            if not event.get("file_path"):
                result.errors.append(ValidationError(
                    field="file_path", message="File edit missing file_path",
                    event_index=index,
                ))
        elif evt_type == EventType.TEST_RUN:
            if not event.get("command"):
                result.warnings.append(ValidationError(
                    field="command", message="Test run missing command",
                    severity="warning", event_index=index,
                ))
        elif evt_type == EventType.FAILED_ATTEMPT:
            if not event.get("failure_reason"):
                result.warnings.append(ValidationError(
                    field="failure_reason", message="Failed attempt missing reason",
                    severity="warning", event_index=index,
                ))
        elif evt_type == EventType.HUMAN_INTERVENTION:
            if not event.get("intervention_type"):
                result.warnings.append(ValidationError(
                    field="intervention_type",
                    message="Human intervention missing type",
                    severity="warning", event_index=index,
                ))


class TraceValidationSuite:
    def __init__(self):
        self.validator = OpenTraceValidator()

    def validate_file(self, path: str) -> ValidationResult:
        import json
        with open(path) as f:
            data = json.load(f)
        trace = OpenAgentTrace.from_dict(data)
        return self.validator.validate(trace)

    def validate_all(self, paths: List[str]) -> List[ValidationResult]:
        return [self.validate_file(p) for p in paths]
