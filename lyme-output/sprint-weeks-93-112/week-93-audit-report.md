# Training Data Audit Report

**Total sources assessed**: 32
**Overall quality score**: 0.45
**Usable subset quality**: 0.95

## Classification Summary

| Category | Count |
|----------|-------|
| Supervised Fine-Tuning | 4 |
| Tool-Policy Learning | 0 |
| Retrieval-Policy Learning | 0 |
| Patch Critique | 2 |
| Evaluation Only | 24 |
| Unusable / Synthetic / Misleading | 2 |

## By Source Type

- ci_trace: 12
- memory_entry: 5
- demo_artifact: 4
- standard_trace: 3
- generated_data: 3
- audit_benchmark: 2
- audit_diagnose: 2
- audit_test: 1

## Assessments

### ✗ 53b6f66c-8b32-4602-a152-b0b1e1de301f
- **Type**: audit_test
- **Category**: Evaluation Only
- **Quality**: 0.34
- **Issues**: Skeleton entry — no tool call traces, No intermediate observations

### ✗ 63e3d91c-248c-4287-a688-97e3f6cb62ce
- **Type**: audit_benchmark
- **Category**: Evaluation Only
- **Quality**: 0.34
- **Issues**: Skeleton entry — no tool call traces, No intermediate observations

### ✗ 7e842cf5-b803-4df1-a8ab-538970c7c97f
- **Type**: audit_diagnose
- **Category**: Evaluation Only
- **Quality**: 0.34
- **Issues**: Skeleton entry — no tool call traces, No intermediate observations

### ✗ 98c75876-2047-4d23-b89f-64b46687f7cd
- **Type**: audit_diagnose
- **Category**: Evaluation Only
- **Quality**: 0.34
- **Issues**: Skeleton entry — no tool call traces, No intermediate observations

### ✗ c65e5969-0640-4f05-9d7d-5b562c9d44cb
- **Type**: audit_benchmark
- **Category**: Evaluation Only
- **Quality**: 0.34
- **Issues**: Skeleton entry — no tool call traces, No intermediate observations

### ✓ oat-refactor-002
- **Type**: standard_trace
- **Category**: Supervised Fine-Tuning
- **Quality**: 0.96
- **Issues**: Failure-attempt trace — good for recovery training

### ✓ oat-failed-003
- **Type**: standard_trace
- **Category**: Supervised Fine-Tuning
- **Quality**: 0.94
- **Issues**: Failure-attempt trace — good for recovery training

### ✓ oat-simple-fix-001
- **Type**: standard_trace
- **Category**: Supervised Fine-Tuning
- **Quality**: 0.96
- **Issues**: None

### ✗ ci-1778906846-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778906853-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778906863-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778907093-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778911152-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778915590-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778915685-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778915708-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778915778-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778915896-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778916047-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ ci-1778916135-1-trace
- **Type**: ci_trace
- **Category**: Evaluation Only
- **Quality**: 0.35
- **Issues**: Skeleton CI trace — no tool calls, Only system + metric events

### ✗ 01-pr-intelligence-report.json
- **Type**: demo_artifact
- **Category**: Evaluation Only
- **Quality**: 0.30
- **Issues**: Demo artifact — may not reflect real usage

### ✓ 02-open-agent-trace.json
- **Type**: demo_artifact
- **Category**: Supervised Fine-Tuning
- **Quality**: 0.96
- **Issues**: Demo artifact — may not reflect real usage

### △ 03-semantic-diff.json
- **Type**: demo_artifact
- **Category**: Patch Critique
- **Quality**: 0.68
- **Issues**: Demo artifact — may not reflect real usage

### ✗ 07-benchmark-leaderboard.json
- **Type**: demo_artifact
- **Category**: Evaluation Only
- **Quality**: 0.30
- **Issues**: Demo artifact — may not reflect real usage

### ✗ synthetic_data_generate_synthetic
- **Type**: generated_data
- **Category**: Unusable / Synthetic / Misleading
- **Quality**: 0.43
- **Issues**: 20% random labels, Hand-crafted situations, not from real traces, No patch content, no verification

### ✗ simulated_training_toolpolicymodel.train_step
- **Type**: generated_data
- **Category**: Unusable / Synthetic / Misleading
- **Quality**: 0.30
- **Issues**: Not gradient-based — weight multiplication by 1.01/0.99, Creates illusion of learning, No validation against held-out data

### △ rule-based_critic_patchcritic.evaluate
- **Type**: generated_data
- **Category**: Patch Critique
- **Quality**: 0.70
- **Issues**: Rule-based, not learned, Can generate critique training pairs

### ✗ 1ed67c2a937545a1.json
- **Type**: memory_entry
- **Category**: Evaluation Only
- **Quality**: 0.40
- **Issues**: Memory entry — structured observation, not agent trace, No tool call sequence, no patch

### ✗ 262ec3818c134738.json
- **Type**: memory_entry
- **Category**: Evaluation Only
- **Quality**: 0.40
- **Issues**: Memory entry — structured observation, not agent trace, No tool call sequence, no patch

### ✗ d51e1a1b0179443f.json
- **Type**: memory_entry
- **Category**: Evaluation Only
- **Quality**: 0.40
- **Issues**: Memory entry — structured observation, not agent trace, No tool call sequence, no patch

### ✗ d63296fccf514401.json
- **Type**: memory_entry
- **Category**: Evaluation Only
- **Quality**: 0.40
- **Issues**: Memory entry — structured observation, not agent trace, No tool call sequence, no patch

### ✗ e86440e8b4d04642.json
- **Type**: memory_entry
- **Category**: Evaluation Only
- **Quality**: 0.40
- **Issues**: Memory entry — structured observation, not agent trace, No tool call sequence, no patch

## Leakage Risks
- Synthetic repo paths may not generalize to real codebases
- Model attribution in traces (claude-3-opus, gpt-4-turbo) may leak model-specific patterns
- Repo names in trace headers identify fictional projects but field exists for real data
- human_intervention events contain user_message — benign now, critical in real data
- file_path fields use generic paths now but would leak structure in real traces

## Hallucination Risks
- Synthetic data has 20% random label noise — degrades any learned model
- Simulated training (weight multiply) creates illusion of learning without gradients
- No 'I don't know' examples — model always tries to answer
- Patch content without full before/after context misses structural understanding

## Missing Labels
- patch_plan — no trace records the plan before execution
- repo_state — no pre-task snapshot of repository structure
- final_answer — no structured final output
- correctness_label — no explicit correct/incorrect per decision
- alternative_actions — no counterfactual options recorded
- grounding_score — no measure of evidence grounding per claim
- difficulty_rating — exists in some traces but not in training schema

## Recommendations
- Do NOT train on synthetic data — 20% random label noise will degrade any learned model
- Do NOT use simulated training as proxy — label as prototype only
- Instrument runtime immediately to collect real traces before Week 96
- Generate controlled data from synthetic repos — lyme-experiments/synthetic/ is ready
- Add explicit correctness, grounding, and difficulty labels to every trace
- Build sanitizer before any training data leaves local storage
- Keep the 3 standard traces as eval-only — too few to train on, perfect for measurement