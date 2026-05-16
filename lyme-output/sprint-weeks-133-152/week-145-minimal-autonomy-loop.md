# Week 145 — Minimal Autonomy Loop

**Theme**: Bounded specialist loop. No endless autonomy.

## Loop

```
1. PLAN    → Planner processes task, writes plan to Blackboard
2. RETRIEVE → Retriever gathers context, writes evidence to Blackboard
3. GENERATE → Patch Generator creates patch, writes to Blackboard
4. CRITIQUE → Critic reviews plan+patch, writes evaluation
5. VERIFY   → Verifier runs checks, writes results
6. REPAIR   → (once if needed) Retry Patch Generator
7. STOP     → Return report

       ┌──────────────────────────────────────┐
       │              Blackboard              │
       │  ┌────┐ ┌──────┐ ┌──────┐ ┌──────┐ │
       │  │Plan│ │Evid. │ │Patch │ │Crit. │ │
       │  └────┘ └──────┘ └──────┘ └──────┘ │
       │  ┌────┐ ┌──────┐ ┌───────────────┐  │
       │  │Ver.│ │Conf. │ │Stop Conditions│  │
       │  └────┘ └──────┘ └───────────────┘  │
       └──────────────────────────────────────┘
              ▲    ▲    ▲    ▲    ▲    ▲
              │    │    │    │    │    │
       ┌──────┴──┐ ┌┴──┐ ┌┴──┐ ┌┴──┐ ┌┴──────┐
       │ Planner │ │Rtr│ │PG │ │Cri│ │Verifier│
       └─────────┘ └───┘ └───┘ └───┘ └────────┘
              │    │    │    │    │    │
       ┌──────▼────▼────▼────▼────▼────▼──────┐
       │           Specialist Router           │
       └───────────────────────────────────────┘
```

## Bounds
- Max steps: 20 (absolute upper limit)
- Repair attempts: 1 (no infinite loops)
- Errors before escalation: 3 in 30 seconds
- Max retries per specialist: 2

## Metrics
- `steps`: loop iterations
- `elapsed_s`: wall clock time
- `phases_completed`: how far through the pipeline
- `errors`: total errors
- `conflicts`: conflicts detected and resolved
- `messages`: messages exchanged
- `stop_conditions`: why the loop stopped
