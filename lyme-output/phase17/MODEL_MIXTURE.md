# Week 111 — Model Mixture Runtime
> Generated: 2026-05-16T23:43:02.535440+00:00

## Roles
- **Fast_planner**: Qwen/Qwen2.5-Coder-1.5B-Instruct
- **Retriever**: Qwen/Qwen2.5-Coder-7B-Instruct
- **Patch_generator**: Qwen/Qwen2.5-Coder-7B-Instruct (with SFT v2 adapter)
- **Critic**: Qwen/Qwen2.5-Coder-7B-Instruct (with critic adapter)
- **orchestrator**: decision_tree + priority queue
- **fallback**: single_model_mode

## Expected Improvements
- Quality: +5-10% over single model
- Latency: slightly worse (orchestration overhead)
- RAM/VRAM: +2-4GB (multiple models loaded)