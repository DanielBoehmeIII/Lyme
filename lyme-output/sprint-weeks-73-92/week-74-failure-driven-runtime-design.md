# Week 74 — Failure-Driven Runtime Design

**Theme:** Use Week 73 error taxonomy to redesign Lyme Model runtime.
**Principle:** Do NOT remove existing Lyme systems. Add guardrails on top.

---

## 1. Failure-to-Mitigation Map

| Failure Type | Root Cause | Runtime Mitigation | Guardrail | Measurement |
|---|---|---|---|---|
| missing_context | No read before edit | Enforce read_file before edit_file | GuardrailMissingContext | read_edit_ratio |
| wrong_file_selected | Guessed file location | Require file path verification via glob | GuardrailWrongFile | wrong_file_edit_rate |
| hallucinated_api | Training data generalization | Inject AST symbol table; verify symbols | GuardrailSymbolCheck | hallucination_rate |
| bad_patch | Malformed diff | Run syntax check + dry-run patch | GuardrailPatchValidation | patch_failure_rate |
| incomplete_patch | Missed side effects | Run dependency impact analysis | GuardrailImpactAnalysis | incomplete_patch_rate |
| test_misunderstanding | Wrong test output parse | Parse test output structurally | GuardrailTestOutputParsing | assertion_misread_rate |
| command_misuse | Guessed command syntax | Validate command existence before run | GuardrailCommandValidation | command_failure_rate |
| syntax_regression | No syntax context | Run syntax check after every edit | GuardrailSyntaxCheck | syntax_error_rate |
| architectural_misunderstanding | No arch overview | Inject architecture summary card | GuardrailArchitecture | architectural_violation_rate |
| excessive_latency | Slow model / big context | Cache outputs; use smaller draft model | GuardrailLatency | p95_task_time_ms |
| context_overflow | Too much unprioritized context | Compress; truncate low-priority files | GuardrailContextWindow | context_utilization_pct |
| tool_loop_failure | No stopping criteria | Add loop detection; enforce max retries | GuardrailLoopDetection | loop_frequency |

## 2. Runtime Flow

```
Task Input
    │
    ▼
Pre-flight Guardrails (context_window check)
    │
    ▼
Execute (base runtime or simulation)
    │
    ▼
Failure Detection (Week 73 detector rules)
    │
    ▼
Apply Mitigations (per-failure-type mitigation)
    │
    ▼
Post-flight Guardrails (loop detection, symbol check)
    │
    ▼
Record Measurements (6 hooks)
    │
    ▼
Result + Report
```

## 3. Guardrails (12 total)

Each guardrail has: name, description, failure category, enabled flag, trigger count, last triggered timestamp.

## 4. Measurement Hooks (6 active hooks)

| Hook | Measures | Threshold | Failure Category |
|------|----------|-----------|------------------|
| read_edit_ratio | Reads per edit | >= 1.0 | missing_context |
| hallucination_rate | Hallucinated symbols/output | < 5% | hallucinated_api |
| p95_task_time | Task completion ms | < 30000 | excessive_latency |
| context_utilization | Context window % | < 90% | context_overflow |
| loop_frequency | Loop failures per run | 0 | tool_loop_failure |

## 5. Benchmark Scenarios (12 total)

One per failure type: `bench_missing_context`, `bench_wrong_file_selected`, etc.

## 6. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/runtime/failure_driven.py` | Failure-driven runtime with 12 guardrails + 6 hooks |
| `tests/test_week74_failure_driven_runtime.py` | 15 tests |

## 7. Audit Preservation

**No modifications to Lyme Audit.** The failure-driven runtime is a consumer of audit traces, using them for detection and measurement.

## 8. Next Week

Week 75 will build retrieval policy experiments comparing keyword, embedding, graph, AST, git-history, hybrid, and model-planned retrieval.
