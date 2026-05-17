# Week 112-113 — Fast Mode v2 + Careful Mode v2

> Generated: 2026-05-16T23:43:02.535493+00:00

## Fast Mode
- **Goal**: Complete repo Q&A / bug localization / patch planning in <60s
- **Model**: Qwen2.5-Coder-1.5B-Instruct (distilled)
- **Context**: Max 4096 tokens
- **No best-of-N**
- **Target**: 80% of careful mode quality at 5x speed

## Careful Mode
- **Goal**: Highest success rate on repair tasks
- **Model**: Qwen2.5-Coder-7B-Instruct with SFT v2 adapter
- **Context**: Max 8192 tokens
- **Best-of-N**: 5 candidates with critic
- **Full verification**: Run tests and check results
- **Target**: 90%+ success on in-distribution tasks
