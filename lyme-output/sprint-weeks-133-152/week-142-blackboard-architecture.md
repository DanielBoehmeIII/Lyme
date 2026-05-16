# Week 142 — Blackboard Architecture

**Theme**: All specialists write to/read from shared state. Lyme Audit traces every mutation.

## Blackboard State Schema

```
BlackboardState:
  ├── task: dict          (original task, metadata)
  ├── evidence: dict      (search results, file contents, git history)
  ├── context_packets: dict (prepared context for specialists)
  ├── plans: dict         (planner outputs)
  ├── patches: dict       (patch generator outputs)
  ├── critiques: dict     (critic outputs)
  ├── verification_results: dict (verifier outputs)
  ├── confidence_updates: dict (latest confidence per specialist)
  ├── stop_conditions: List[str]
  ├── current_phase: str
  ├── messages: List[SpecialistMessage]
  ├── errors: List[dict]
  ├── latencies: Dict[str, float]
  └── trace_id: str
```

## Audit Trail

Every state mutation is recorded:
```json
{
  "action": "write:plans",
  "detail": {"specialist": "planner", "data_keys": ["task_decomposition", "risk_score"]},
  "timestamp": 1234567890.0,
  "state_version": 5
}
```

## Design Rules
1. Specialists write results, not instructions
2. Router reads state to decide next action
3. No direct specialist-to-specialist communication (always through Blackboard)
4. Every mutation is traceable
