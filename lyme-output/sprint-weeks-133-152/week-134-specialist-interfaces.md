# Week 134 — Specialist Model Interfaces

**Theme**: Every specialist has a contract. Input, output, confidence, failures, tools, verification, audit.

## Interface Summary

| Specialist | Input | Output | Confidence | Failure Labels |
|------------|-------|--------|:----------:|:--------------:|
| **Planner** | PlannerInput | PlannerOutput | 0.0-1.0 | ambiguous_input, out_of_scope, risk_too_high, insufficient_context |
| **Retriever** | RetrieverInput | RetrieverOutput | 0.0-1.0 | insufficient_context, ambiguous_input, timeout |
| **Patch Generator** | PatchGeneratorInput | PatchGeneratorOutput | 0.0-1.0 | verification_failed, hallucinated_evidence, risk_too_high, model_too_weak |
| **Critic** | CriticInput | CriticOutput | 0.0-1.0 | ambiguous_input, insufficient_context, internal_error |
| **Verifier** | VerifierInput | VerifierOutput | 0.0-1.0 | verification_failed, timeout, internal_error |
| **Summarizer** | SummarizerInput | SummarizerOutput | 0.0-1.0 | ambiguous_input, internal_error |
| **Refusal Detector** | RefusalInput | RefusalOutput | 0.0-1.0 | ambiguous_input |

## Key Design Decisions

### Confidence Levels
- **very_low** (0.0-0.2): refuse, ask for help
- **low** (0.2-0.4): require human review
- **medium** (0.4-0.7): require verification
- **high** (0.7-0.9): accept with verification
- **very_high** (0.9-1.0): accept, light verification

### Failure Labels
11 standardized failure labels across all specialists:
`ambiguous_input, insufficient_context, out_of_scope, hallucinated_evidence, missing_dependency, verification_failed, risk_too_high, model_too_weak, timeout, internal_error, conflict_detected`

### Audit Trace Format
Every specialist produces a structured `AuditTrace`:
```json
{
  "specialist": "planner",
  "trace_id": "...",
  "steps": [{"step": 1, "description": "...", "detail": {...}}],
  "decisions": [{"decision": "...", "rationale": "...", "alternatives": [...]}],
  "start_time": "2026-05-16T..."
}
```

### Standardized Output Format
Every specialist output converts via `to_dict()` and wraps via `specialist_output_to_audit()` for Lyme Audit ingestion.

## Files Created
- `src/lyme_model/specialists/interfaces.py` — All 7 specialist interfaces with dataclasses
- Updated `src/lyme_model/specialists/__init__.py` — Exports all interfaces

## Lyme Audit Status
**Untouched.** All specialist outputs flow into Lyme Audit via `specialist_output_to_audit()`.
