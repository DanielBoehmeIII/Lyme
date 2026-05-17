# Lyme Model v2.5 — Local Monster Beta
> Generated: 2026-05-16T23:43:02.535730+00:00

## Claim
A local coding model adaptation system designed to compete with 
Claude/OpenCode on narrow, measurable coding-agent tasks while 
running on consumer hardware.

## Deliverables
- **Primary adapter** (SFT v2): Qwen2.5-Coder-7B + QLoRA
- **Specialization adapters**: Diff Discipline, Test Repair, Bug Loc, Multi-File
- **Quantized variants**: Q3_K_S through Q8_0
- **Ollama/GGUF setup**: Modelfile + install instructions
- **Action grammar**: SEARCH/READ/RUN/PATCH/VERIFY/STOP/ASK_USER
- **Agent loop runtime**: Action parsing + tool execution + observation
- **Self-repair**: Failed patch → re-analysis → corrected patch
- **Best-of-N critic**: N=5 candidate patches → ranked → best applied
- **Distilled behavior**: Search rhythm, minimal patches, verification discipline
- **Refusal/uncertainty**: 7 nuanced refusal categories

## Narrow Competitive Slices
1. **Primary slice**: small_failing_test_repair
2. **Secondary slice**: test_failure_localization

## Benchmark Snapshot
| Metric | v1 | v2.5 Target |
|--------|------|-------------|
| Patch validity | 67% | 80% |
| Test repair pass@1 | 50% | 70% |
| Bug localization top-3 | 60% | 80% |
| Action parse rate | 75% | 90% |
| Refusal accuracy | 80% | 92% |
| Self-repair success | - | 70% |

## Hardware Guide
- 8GB VRAM: Q4_K_M variant, fast+careful modes
- 12GB VRAM: Q5_K_M variant, all modes
- 24GB+ VRAM: Q8_0 variant, full pipeline including best-of-N

## Next Bottlenecks
1. Model capacity ceiling at 7B
2. No RLHF/DPO (SFT only)
3. Dataset size (~3K curated vs proprietary scale)
4. No real-time tool execution integration
5. Speculative decoding not production-tested
6. Long-horizon (>5 step) tasks still unreliable