# Lyme Model v1.2 — Agentic Local Coding Model

> Generated: 2026-05-16T23:05:31.983007+00:00

## Theme
Agentic local coding model — structured action grammar with tool-use behavior.

## Components
| Component | Week | Description |
|-----------|------|-------------|
| SFT v1 | 46 | Supervised fine-tuning on coding tasks |
| Tool-Use Spec | 47 | Structured tool actions |
| Diff Discipline | 48 | Strict unified diff generation |
| Test Repair | 49 | Failing test fix specialization |
| Multi-File Edit | 50 | Bounded cross-file editing |
| Critic v1 | 51 | Patch scoring and verification |
| Action Grammar | 53 | Parseable SEARCH/READ/PATCH/STOP |
| ReAct Traces | 54 | Observe-Decide-Act loops |
| Tool Feedback | 55 | Recovery from failed actions |
| Stop Conditions | 56 | Appropriate stop behavior |
| Plan-Patch Align | 57 | Plan matches final patch |
| Agent Runtime v2 | 58 | Parse model output, execute tools |

## Training Data
- **Dataset v1**: 16,328 examples across 10 modalities
- **Specialized datasets**: Tool-use (240), Diff (270), Test Repair (300), Multi-file (180), Critic (350)
- **Agentic datasets**: Action grammar (120), ReAct (60), Feedback (120), Stop (150), Plan-Patch (90)

## Architecture
- **Base Model**: Qwen/Qwen2.5-Coder-0.5B-Instruct
- **Fine-tuning**: QLoRA (4-bit NF4, LoRA r=16)
- **Inference**: <1s per action on RTX 4060, ~3s on CPU

## Gap vs Claude/OpenCode
- **Strengths**: Structured output, minimal patches, appropriate stopping
- **Weaknesses**: Limited reasoning (0.5B), multi-file consistency, complex planning
- **Bottleneck**: Model capacity; next step is distillation from larger models
