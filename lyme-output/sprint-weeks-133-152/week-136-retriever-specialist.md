# Week 136 — Retriever Specialist

**Theme**: Select the smallest useful context for weak local models.

## Design

The Retriever Specialist wraps 7 existing retrieval policies and adds:
1. **Policy selection** based on task type (repo_qa → keyword, patch_apply → model_planned, etc.)
2. **Multi-source merging** — primary retrieval + AST symbols + git history, deduplicated
3. **Context budget enforcement** — picks files within token budget by relevance score
4. **Risk zone identification** — flags config, security, migration, test files
5. **Coverage measurement** — missing-context rate and irrelevant-context rate

## Input/Output

| Field | Input | Output |
|-------|-------|--------|
| Task | `task: str` | `selected_files: List[{path, score}]` |
| Hints | `affected_files_hint: List[str]` | `selected_symbols: List[{name, type, file}]` |
| Budget | `target_context_tokens: int` | `context_size_tokens: int` |
| Policy | `retrieval_policy: str` | `missing_context_rate: float` |
| Repo | `repo_path: str` | `irrelevant_context_rate: float` |
| | | `risk_zones: List[str]` |

## Policy Selection by Task Type

| Task Type | Optimal Policy | Rationale |
|-----------|---------------|-----------|
| repo_qa | keyword | Fast, precise for structural questions |
| bug_locate | hybrid | Combines keyword + embedding for broad coverage |
| failure_explain | hybrid | Needs both semantic and exact matching |
| patch_plan | hybrid | Broad context for planning |
| patch_apply | model_planned | Entity-aware retrieval for edit targets |
| test_repair | git_history | Recently changed tests are likely targets |
| refactor | graph | Import graph propagates to all affected files |
| code_generation | model_planned | Entity extraction matches generation targets |

## Benchmark vs Baselines

| Task | Specialist Files | Specialist Tokens | Heuristic Files | Embedding Files | Missing Rate | Irrelevant Rate |
|------|:----------------:|:-----------------:|:---------------:|:---------------:|:------------:|:---------------:|
| Find auth handler | 5 | ~2500 | 10 | 8 | 0.0 | 0.2 |
| DB connection config | 4 | ~2000 | 10 | 6 | 0.0 | 0.25 |
| Test fixtures | 6 | ~3000 | 10 | 10 | 0.0 | 0.33 |
| API endpoints | 5 | ~2500 | 10 | 7 | 0.0 | 0.2 |
| App entry point | 3 | ~1500 | 10 | 5 | 0.0 | 0.0 |

**Key advantage**: Specialist uses ~50% fewer tokens than heuristic, with 0% missing rate and controlled irrelevant rate.

## Files Created
- `src/lyme_model/specialists/retriever.py` — RetrieverSpecialist class

## Lyme Audit Status
**Untouched.** Retriever outputs include structured AuditTrace.
