# Week 73 — Local Coding Agent Error Taxonomy

**Theme:** Build an error taxonomy specifically for local coding models.
**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. Taxonomy (12 categories)

| # | Category | Severity | Root Cause |
|---|----------|----------|------------|
| 1 | missing_context | HIGH | Context window too small, retrieval missed key files |
| 2 | wrong_file_selected | HIGH | Similar filenames, model guessed file location |
| 3 | hallucinated_api | CRITICAL | Model generalized from training instead of reading code |
| 4 | bad_patch | HIGH | Model misunderstood change or generated malformed diff |
| 5 | incomplete_patch | MEDIUM | Model missed side effects, related files, edge cases |
| 6 | test_misunderstanding | MEDIUM | Model didn't parse test output correctly |
| 7 | command_misuse | MEDIUM | Model guessed command syntax instead of checking |
| 8 | syntax_regression | HIGH | Model generated code without checking surrounding syntax |
| 9 | architectural_misunderstanding | HIGH | Model lacked architectural overview |
| 10 | excessive_latency | LOW | Slow model, large context, many tool calls |
| 11 | context_overflow | MEDIUM | Context exceeded model's max window |
| 12 | tool_loop_failure | HIGH | Model stuck repeating same action without progress |

## 2. Examples

Each category has a concrete example showing how the failure manifests in local coding agent behavior:

- **missing_context**: Model edits file without reading it first → patch contradicts existing code
- **wrong_file_selected**: Task says "fix auth bug", model edits utils/helpers.py instead of auth/login.py
- **hallucinated_api**: Model calls paginate_results() which doesn't exist in the codebase
- **bad_patch**: Model generates indentation error, missing closing paren, broken imports
- **incomplete_patch**: Model adds validation to controller but not model/migration
- **test_misunderstanding**: Model changes test assertion instead of fixing source code
- **command_misuse**: Model runs `pytest --flags --that --dont --exist`
- **syntax_regression**: Model adds code with missing colon, mismatched quotes, undefined vars
- **architectural_misunderstanding**: Model adds caching in controller instead of service layer
- **excessive_latency**: Task takes 120s on 3B model with full repo context
- **context_overflow**: 12K tokens across 25 files pushed into 4K context window
- **tool_loop_failure**: Same file read 4x without any edits

## 3. Detector Rules (22 total)

| Rule | Category | Cost | Priority |
|------|----------|------|----------|
| no_read_before_edit | missing_context | cheap | 0 |
| output_contradicts_code | missing_context | medium | 1 |
| edit_wrong_file | wrong_file_selected | cheap | 0 |
| nonexistent_import | hallucinated_api | cheap | 0 |
| nonexistent_function_call | hallucinated_api | medium | 1 |
| patch_fails_apply | bad_patch | cheap | 0 |
| syntax_error_after_patch | syntax_regression | cheap | 1 |
| test_still_failing | incomplete_patch | medium | 0 |
| missing_side_effects | incomplete_patch | expensive | 2 |
| wrong_assertion_interpretation | test_misunderstanding | medium | 1 |
| model_modified_test_instead | test_misunderstanding | cheap | 0 |
| command_non_zero_exit | command_misuse | cheap | 0 |
| command_not_found | command_misuse | cheap | 0 |
| python_syntax_regression | syntax_regression | cheap | 0 |
| wrong_pattern_used | architectural_misunderstanding | expensive | 2 |
| change_breaks_layer | architectural_misunderstanding | expensive | 2 |
| total_time_too_high | excessive_latency | cheap | 0 |
| model_load_time_high | excessive_latency | cheap | 1 |
| context_exceeds_window | context_overflow | cheap | 0 |
| too_many_files_retrieved | context_overflow | cheap | 1 |
| same_tool_repeated | tool_loop_failure | cheap | 0 |
| no_progress_after_n_calls | tool_loop_failure | cheap | 1 |

## 4. Metrics

Tracked per run and per window:
- **failure_rate**: Total failures / total runs
- **by_category_rate**: Per-category failure frequency
- **by_severity_rate**: Breakdown by CRITICAL / HIGH / MEDIUM / LOW
- **mitigation_success_rate**: Failures that were mitigated by runtime
- **trend_direction**: improving / degrading / stable

## 5. CLI Report

The CLI report (`lyme model failures report`) produces:
1. Taxonomy overview with all 12 categories
2. Detector rules listed by priority
3. Failure analysis (counts, categories, severities)
4. Metrics (rates, trends)
5. Concrete examples per category
6. Mitigation recommendations

## 6. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/failures/__init__.py` | Module exports |
| `src/lyme_model/failures/taxonomy.py` | 12-category taxonomy + records |
| `src/lyme_model/failures/detector.py` | 22 detector rules + detection engine |
| `src/lyme_model/failures/metrics.py` | Failure metrics computation |
| `src/lyme_model/failures/report.py` | CLI report generator |

## 7. Integration with Lyme Audit

The taxonomy uses Lyme Audit traces as input:
- `trace["tool_calls"]` → tool sequence analysis
- `trace["test_results"]` → test failure detection
- `trace["output"]` → hallucination detection
- `trace["total_time_ms"]` → latency detection
- `trace["context_tokens"]` → overflow detection
- `trace["audit_id"]` → cross-reference to Audit entries

**No modifications to Lyme Audit were made.** The taxonomy reads Audit output as a consumer.

## 8. Next Week

Week 74 will use this taxonomy to redesign the Lyme Model runtime — adding guardrails, measurement hooks, and mitigations for each failure type.
