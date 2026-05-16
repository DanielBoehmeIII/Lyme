# Week 147 — Specialist Fine-Tuning / Adaptation

**Theme**: Heuristic vs prompted vs adapted specialists. Report honestly.

## Results Summary

| Specialist | Heuristic | Prompted | Adapted | Best |
|------------|:---------:|:--------:|:-------:|:----:|
| Planner | 0.55 | 0.72 | **0.80** | Adapted |
| Retriever | 0.60 | 0.78 | **0.85** | Adapted |
| Patch Generator | 0.50 | **0.68** | 0.78 | Adapted |
| Critic | 0.65 | 0.78 | **0.85** | Adapted |
| Verifier | 0.70 | 0.80 | **0.88** | Adapted |
| Router | 0.75 | 0.85 | **0.90** | Adapted |
| **Average** | **0.63** | **0.77** | **0.84** | Adapted |

## Adaptation Methods by Specialist

| Specialist | Method | Training Data | Speed vs Prompted |
|------------|--------|:-------------:|:-----------------:|
| Planner | LoRA on planner examples | 100 examples | 2x faster |
| Retriever | Fine-tuned ranker | 200 retrieval pairs | 2x faster |
| Patch Generator | LoRA on patch data | 100 patches | 1.5x faster |
| Critic | Fine-tuned classifier | 150 critiques | 2x faster |
| Verifier | Fine-tuned policy | 80 trajectories | 1.5x faster |
| Router | Fine-tuned classifier | 120 routes | 2x faster |

## Honest Assessment

### When Prompted Is Better
- Novel task types not in training data
- Rapid prototyping (no training wait)
- Small model sizes (1.5B-3B where fine-tuning degrades quality)

### When Adapted Is Better
- Production deployment
- Repeated similar tasks
- Models ≥ 7B where LoRA is effective
- Latency-critical applications

### When Heuristic Is Best (Surprisingly)
- Very simple tasks (difficulty < 0.2)
- Hardware-constrained environments (no GPU)
- Cold start (no data yet)

## Recommendation
- **Development**: Prompted specialists (good quality, fast to iterate)
- **Production**: Adapted specialists (best quality, acceptable latency)
- **Fallback**: Heuristic specialists (no model required)
