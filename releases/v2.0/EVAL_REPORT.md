# Lyme Model v2.0 — Eval Report
> Generated: 2026-05-16T23:41:05.966392+00:00

## Summary
| Metric | v1 Baseline | v2 Target | Delta |
|--------|------------|-----------|-------|
| bug_localization_top3 | 60% | 80% | +20% |
| multi_file_edit_success | 40% | 65% | +25% |
| patch_validity | 67% | 80% | +13% |
| refusal_accuracy | 80% | 92% | +12% |
| test_repair_pass@1 | 50% | 70% | +20% |
| tool_action_parse | 75% | 90% | +15% |

## Dataset Growth
- v1: 16328 examples
- v2: 3325 examples

## Training Pipeline
1. Dataset v2 Assembly (Week 85)
2. Base Model Selection: Qwen2.5-Coder-7B (Week 86)
3. SFT v2 (Week 87)
4. Diff Discipline v2 (Week 88)
5. Test Repair v2 (Week 89)
6. Bug Localization v2 (Week 90)
7. Multi-File Edit v2 (Week 91)