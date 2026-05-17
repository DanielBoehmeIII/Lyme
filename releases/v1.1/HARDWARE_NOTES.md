# Lyme Model v1.1 — Hardware Notes

## Training Hardware
- **GPU**: NVIDIA GeForce RTX 4060 Laptop (8.3GB VRAM)
- **CPU**: 12th Gen Intel Core i7
- **RAM**: 32GB
- **Storage**: SSD

## Training Configuration
- **Base Model**: Qwen2.5-Coder-0.5B-Instruct (495M params)
- **Quantization**: 4-bit NF4 (BitsAndBytes)
- **LoRA**: r=16, alpha=32, all linear layers
- **Trainable params**: 8.8M (1.75% of total)
- **Batch Size**: 1 per GPU with 8 gradient accumulation steps
- **Max Sequence Length**: 1024 tokens
- **Peak VRAM**: ~4.5GB during training

## Inference Hardware Tiers
| Tier | Hardware | Config | Expected Performance |
|------|----------|--------|---------------------|
| Low | CPU only, 16GB RAM | 4-bit, seq=512 | ~5-10s per generation |
| Mid | 8GB VRAM GPU | 4-bit, seq=1024 | ~1-3s per generation |
| High | 24GB VRAM GPU | 8-bit, seq=2048 | ~0.5-1s per generation |

## Scaling Notes
- The 0.5B model fits easily on consumer hardware
- Moving to 1.5B or 3B models would require reduced batch size or deeper quantization
- 7B models require 24GB VRAM for training even with QLoRA
