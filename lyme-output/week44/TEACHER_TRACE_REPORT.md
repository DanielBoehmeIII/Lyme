# Week 44 — Teacher Trace Collection Report
> Generated: 2026-05-16T21:29:38.690230+00:00

## Summary
- Total teacher traces: 36
- Teacher models: 3
- Task types: 6

## Per-Model Breakdown
| Model | Traces |
|-------|--------|
| qwen2.5-coder:14b | 12 |
| qwen2.5-coder:7b | 12 |
| deepseek-coder:6.7b | 12 |

## Per-Type Breakdown
| Task Type | Traces |
|-----------|--------|
| bug_localization | 9 |
| patch_planning | 6 |
| repo_qa | 6 |
| test_repair | 6 |
| tool_use | 3 |
| unified_diff | 6 |

## Splits
- train: 25
- val: 5
- test: 6

## Trace Fields
- id: unique trace identifier
- modality: task type classification
- teacher_model: source model name
- instruction: task description
- tool_outputs: simulated tool call sequence
- target_output: raw model response
- metadata.plan: extracted plan (if applicable)
- metadata.patch: extracted patch (if applicable)