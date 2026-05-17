# Week 86 — Base Model Re-evaluation Report
> Generated: 2026-05-16T23:39:25.478449+00:00

## Summary
- Candidates evaluated: 9
- Live Ollama evals: 0
- Eval tasks: 10
- Eval categories: patch_validity, test_repair, bug_localization, tool_action, refusal

## Candidate Comparison
| Model | Class | Params | HumanEval | Patch Quality | Code Understanding | Composite |
|-------|-------|--------|-----------|---------------|-------------------|-----------|
| qwen2.5-coder:32b | 30B | 32.5B | 0.927 | 0.92 | 0.93 | 0.926 |
| qwen2.5-coder:14b | 14B | 14.8B | 0.887 | 0.88 | 0.9 | 0.889 |
| qwen2.5-coder:7b | 7B | 7.6B | 0.832 | 0.81 | 0.85 | 0.831 |
| deepseek-coder:6.7b | 7B | 6.7B | 0.737 | 0.88 | 0.8 | 0.799 |
| codellama:34b | 30B | 34B | 0.652 | 0.77 | 0.75 | 0.717 |
| codellama:13b | 14B | 13B | 0.669 | 0.75 | 0.73 | 0.712 |
| starcoder2:7b | 7B | 7.0B | 0.655 | 0.67 | 0.7 | 0.673 |
| codellama:7b | 7B | 7.0B | 0.624 | 0.71 | 0.68 | 0.667 |
| starcoder2:15b | 14B | 15B | 0 | 0 | 0 | 0.500 |

## Selections
### 7B Class
- **Primary**: qwen2.5-coder:7b (83.1% composite)
- HumanEval: 0.832
- Runners-up: deepseek-coder:6.7b, starcoder2:7b

### 14B Class
- **Primary**: qwen2.5-coder:14b (88.9% composite)
- HumanEval: 0.887
- Runners-up: codellama:13b, starcoder2:15b

### 30B Class
- **Primary**: qwen2.5-coder:32b (92.6% composite)
- HumanEval: 0.927
- Runners-up: codellama:34b

## Decision Matrix
| Criteria | 7B | 14B | 30B |
|----------|----|-----|-----|
| Base model | qwen2.5-coder:7b | qwen2.5-coder:14b | qwen2.5-coder:32b |
| Training hardware | 8GB VRAM | 12-16GB VRAM | 24GB+ VRAM |
| Inference hardware | 8GB VRAM | 12GB VRAM | 24GB VRAM |
| Target quality | Good | Better | Best |
| Quantization | Q4_K_M | Q4_K_M | Q4_K_M/Q5_K_M |

## Recommendation
- **Primary (7B)**: qwen2.5-coder:7b — fits 8GB VRAM, strongest 7B-class coder for current hardware
- **Upgrade (14B)**: qwen2.5-coder:14b — significantly stronger, requires 12GB+ VRAM
- **Stretch (30B)**: qwen2.5-coder:32b — bleeding-edge local coding, needs 24GB+ VRAM

## Hardware Fit (Current: RTX 4060 8GB VRAM)
- **Best 7B option**: qwen2.5-coder:7b at Q4_K_M (~4.5GB)
- Best 14B option needs 12GB+ VRAM
- Best 30B option needs 24GB+ VRAM
- 8GB VRAM limit means 7B-class is the practical maximum without offloading