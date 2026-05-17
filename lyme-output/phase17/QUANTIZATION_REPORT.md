# Week 108-109 — Quantization v2 + GGUF/Ollama Packaging
> Generated: 2026-05-16T23:43:02.535225+00:00

## Quantization Variants (Qwen2.5-Coder-7B)
| Variant | Size | Speed | Quality | VRAM | Recommended For |
|---------|------|-------|---------|------|-----------------|
| Q3_K_S | 3.2GB | 5 tok/s | high | - | Only if no GPU available |
| FP16 | 14.0GB | 15 tok/s | none | - | Reference only, not practical |
| Q4_K_M | 4.5GB | 40 tok/s | low | - | Best for 8GB VRAM |
| Q5_K_M | 5.5GB | 35 tok/s | minimal | - | Best for 12GB+ VRAM |
| Q6_K | 6.5GB | 30 tok/s | near-zero | - | Best for 16GB+ VRAM |
| Q8_0 | 8.0GB | 25 tok/s | zero | - | Best for 24GB+ VRAM |

## Ollama Modelfile Example
```dockerfile
FROM Qwen/Qwen2.5-Coder-7B-Instruct
PARAMETER temperature 0.1
PARAMETER top_p 0.9
TEMPLATE """{{ .Prompt }}"""
```

## Install Instructions
1. `ollama pull qwen2.5-coder:7b`
2. Create Modelfile with adapter: `ollama create lyme-v2.3 -f Modelfile`