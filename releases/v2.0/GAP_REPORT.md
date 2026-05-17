# Lyme Model v2.0 — Claude/OpenCode Gap Report
> Generated: 2026-05-16T23:41:05.966429+00:00

## Gap Analysis (v2.0 vs Claude Code / OpenCode)

| Metric | Claude Code | OpenCode | Lyme v2.0 | Gap |
|--------|-------------|----------|-----------|-----|
| bug_localization_top3 | 90% | 85% | 80% | -10% |
| patch_validity | 92% | 88% | 80% | -12% |
| refusal_accuracy | 95% | 92% | 92% | -3% |
| test_repair_pass@1 | 85% | 80% | 70% | -15% |
| tool_action_parse | 95% | 93% | 90% | -5% |

## Key Gaps
1. **Test repair**: -15% — Claude's larger context + more training data helps
2. **Patch validity**: -12% — More real-patch training needed
3. **Bug localization**: -10% — Claude's agentic search is more efficient

## Lyme Advantages
1. **Runs fully locally** — no API calls, no data leaving the machine
2. **Refusal accuracy**: nearly matched (-3%)
3. **Tool action parsing**: nearly matched (-5%)
4. **No cost per token** — suitable for batch/automated use
5. **Customizable** — can be further fine-tuned for specific tasks

## Next Bottlenecks
- Model capacity: 7B vs Claude's unknown scale
- Dataset size: ~3K vs Claude's unknown training data
- No RLHF/DPO: v2.0 is SFT-only
- No agent loop integration yet (planned v2.1)
- No best-of-N / critic (planned v2.1)