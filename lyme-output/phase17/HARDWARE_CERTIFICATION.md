# Week 114 — Hardware Tier Certification
> Generated: 2026-05-16T23:43:02.535529+00:00

## Certified Tiers
| Tier | RAM | VRAM | Variant | Mode | Max Task | Latency |
|------|-----|------|---------|------|----------|---------|
| 12gb_vram | 32GB | 12GB | q5_k_m | fast + careful | multi-file edits (2-5 files) | good (35 tok/s) |
| 24gb_vram | 64GB | 24GB | q8_0 | fast + careful + best-of-N | any | fast (25-40 tok/s) |
| 48gb_vram | 128GB | 48GB | fp16 | all modes | any, including 30B model | fast (15-50 tok/s) |
| 8gb_vram | 16GB | 8GB | q4_k_m | fast + careful | multi-file edits (2-3 files) | good (40 tok/s) |
| cpu_only | 16GB | 0GB | q3_k_s | fast | single-file bug fix | slow (5 tok/s) |

## Known Failure Points
- **12gb_vram**: 30B model cannot fit at Q4
- **24gb_vram**: none
- **48gb_vram**: none
- **8gb_vram**: 30B model cannot fit, large context >8K
- **cpu_only**: multi-file edits, long context tasks