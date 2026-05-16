# Week 94 — Lyme Model Data Format

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/data_format.py`
**Tests:** `tests/test_week94_data_format.py` (33 tests, all passing)

**Canonical Lyme Model training format** with:
- Core data types for all training modalities
- Modality-specific views with conversion functions
- Full trace → example conversion pipeline
- Dataset container with train/val/test split
- JSON and JSONL serialization

**Every example is traceable back to a Lyme Audit run** via `source_trace_id` and `source_audit_id` fields.

---

## 2. Core Data Types

| Type | Fields | Purpose |
|------|--------|---------|
| `RepoState` | repo_name, language, framework, file_count, total_lines, test_count, git_head | Snapshot of repository at task start |
| `RelevantFile` | file_path, file_role, lines, content_preview, dependency_of | File-level context |
| `ToolCall` | sequence, tool_name, input_args, output_summary, observation, latency_ms, success | Every tool invocation |
| `PatchPlan` | plan, affected_files, intended_change, risk_assessment, verification_command, rollback_plan, confidence | Plan before execution |
| `Patch` | file_path, old_content, new_content, diff, lines_added, lines_removed, hash | Actual edit |
| `VerificationResult` | verification_type, command, passed, tests_passed/failed, errors, findings, coverage | Outcome check |
| `FailureRecovery` | attempt_number, max_attempts, failure_reason, failure_category, strategy_change, confidence_before/after | Retry behavior |

---

## 3. Modality Formats

### SFT (Supervised Fine-Tuning)
```
Input:  instruction + input_context (repo, files, error)
Output: correct_answer or patch diff
```
Conversion: `SFTExample.from_lyme_example()`

### Tool-Use Imitation
```
Input:  scenario + files_read + task_remaining + test_failed + has_patch + loop_count
Output: correct_action + correct_args
```
Conversion: `ToolUseExample.from_lyme_example()`

### Patch Critic Training
```
Input:  task + patch_diff + target_file + repo_language + known_symbols + arch_rules
Output: label_safe + label_issues
```
Conversion: `PatchCriticExample.from_lyme_example()`

### Retrieval Ranking
```
Input:  query
Output: relevant_docs + irrelevant_docs
```
Conversion: `RetrievalRankingExample.from_lyme_example()`

### Verifier Training
```
Input:  task + proposed_solution + patch_diff + verification_result
Output: label_correct + label_issues
```
Conversion: `VerifierExample.from_lyme_example()`

### Preference Data
```
Input:  task
Output: chosen_output + rejected_output + chosen_patch + rejected_patch + preference_reason
```

---

## 4. Trace → Example Pipeline

`LymeDataFormat.from_trace()` converts an Open Agent Trace (dict) into a `LymeTrainingExample`:

| Trace Event | Mapped To |
|-------------|-----------|
| `header.tags.task` | `task_instruction` |
| `header.system.repo_name` | `repo_state.repo_name` |
| `file_read` events | `relevant_files[]` |
| `file_edit` events | `patches[]` |
| `model_call`, `file_read`, `file_edit`, `test_run` | `tool_calls[]` |
| `test_run` | `verification` |
| `verification_step` | `verification` |
| `failed_attempt` | `failure_recoveries[]` |
| `confidence_change` | `failure_recoveries[].confidence_before/after` |
| `evidence_claim` | `intermediate_observations[]` |
| `summary.status` | `is_correct`, `quality_score` |

---

## 5. Dataset Container

`LymeDataset` holds:
- `examples` — list of `LymeTrainingExample`
- Modalit-specific views (sft, tool_use, patch_critic, retrieval, verifier, preference)
- `train_ids`, `val_ids`, `test_ids` — random split at construction
- `by_task_type`, `by_difficulty` — distribution statistics
- `to_markdown()` — human-readable report

**Serialization:** `LymeDataFormat.to_json()` for full dataset, `LymeDataFormat.to_jsonl()` for individual lists.

---

## 6. Task Type Taxonomy

| Task Type | Description |
|-----------|-------------|
| `qa` | Repo Q&A — answer questions about code |
| `locate_bug` | Find where a bug is in the code |
| `explain_failure` | Explain why a test or build failed |
| `plan_patch` | Design a fix without applying it |
| `apply_patch` | Generate and apply a code change |
| `verify_patch` | Check if a patch is correct |
| `recover` | Recover from a failed test or build |
| `refuse` | Refuse an unsupported or unsafe request |

---

## 7. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/data_format.py` | Core data types, modality views, dataset container, trace converter |
| `tests/test_week94_data_format.py` | 33 tests covering all types, views, conversion, serialization |

---

## 8. Next Week

Week 95 — Build Data Sanitization for Training: remove secrets, API keys, private paths, usernames; preserve technical structure.

---

## End of Week 94

**Canonical Lyme Model data format defined. 33 tests passing. 6 modality formats supported. Trace → example pipeline functional.**
