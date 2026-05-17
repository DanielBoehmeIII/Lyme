# Lyme Model v2.0 — Hardware Requirements

## Minimum (7B, Q4_K_M)
- **GPU**: 8GB VRAM (RTX 4060, RTX 3060, etc.)
- **RAM**: 16GB system RAM
- **Storage**: 500MB (adapter) + 4.5GB (base model)
- **Speed**: ~40-50 tok/s on RTX 4060

## Recommended (7B, Q5_K_M)
- **GPU**: 12GB VRAM (RTX 4070, RTX 3080, etc.)
- **RAM**: 32GB system RAM
- **Speed**: ~35-45 tok/s

## Notes
- QLoRA adapters are ~155MB each
- Base model (Qwen2.5-Coder-7B) requires ~4.5GB at Q4_K_M
- Full pipeline (SFT + all specializations) requires ~8 hours on RTX 4060
- Inference with a single adapter requires < 6GB VRAM total
