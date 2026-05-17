# Lyme Model v2.3 — Local Inference Monster
> Generated: 2026-05-16T23:43:02.535633+00:00

## Included
- Quantized variants: Q3_K_S through Q8_0
- GGUF/Ollama Modelfile
- Speculative decoding prototype (0.5B + 7B)
- Model mixture runtime (4 roles)
- Fast mode (1.5B, <60s) + Careful mode (7B, best-of-N)
- Hardware certification: 5 tiers (CPU-only to 48GB VRAM)

## Hardware Requirements
- **Minimum**: CPU-only, 16GB RAM, Q3_K_S
- **Recommended**: 8GB VRAM, Q4_K_M, fast+careful modes
- **Optimal**: 24GB+ VRAM, Q8_0, all modes