# Week 135 — Planner Specialist

**Theme**: Before any action, a plan. The Planner decomposes tasks, estimates difficulty, selects mode, and defines verification strategy.

## Design

The Planner Specialist wraps four existing Lyme Model components:
1. **TaskDecomposer** — breaks task into ordered subtasks with dependencies
2. **HierarchicalPlanner** — builds multi-level plan (goal → arch → file → function → patch → verify)
3. **DifficultyEstimator** — classifies task type, estimates difficulty/risk/ambiguity
4. **ModeSelector** — picks optimal mode for hardware+task profile

## Input/Output

| Field | Input | Output |
|-------|-------|--------|
| Task | `user_task: str` | `task_decomposition: List[dict]` |
| Context | `repo_summary, constraints` | `affected_files: List[str]` |
| Hardware | `hardware_profile: str` | `context_needs: List[str]` |
| Models | `available_models: List[str]` | `recommended_model: str` |
| History | `prior_failures: List[str]` | `risk_score: float` (0-1) |
| | | `recommended_mode: str` |
| | | `verification_strategy: List[str]` |
| | | `stop_conditions: List[str]` |
| | | `confidence: float` |

## Refusal Logic
- Difficulty > 0.85 → refuse (risk too high)
- Risk = critical → refuse
- Confidence < 0.3 → insufficient context label

## Benchmark vs Generic

| Task | Specialist Subtasks | Generic Subtasks | Confidence | Mode |
|------|:-------------------:|:----------------:|:----------:|------|
| Fix auth bug | 4 | 4 | 0.67 | local_careful |
| Add pagination | 5 | 5 | 0.56 | local_careful |
| Refactor DB module | 3 | 3 | 0.45 | local_with_critic |
| What language? | 1 | 3 | 0.86 | local_fast |
| Update README | 5 | 5 | 0.75 | local_fast |

**Key advantage**: Specialist provides risk score, mode recommendation, confidence, and verification strategy — generic decomposer only provides subtask ordering.

## Files Created
- `src/lyme_model/specialists/planner.py` — PlannerSpecialist class with full pipeline

## Lyme Audit Status
**Untouched.** Planner outputs include structured AuditTrace with steps and decisions.
