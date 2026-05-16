# Week 75 — Retrieval Policy Learning

**Theme:** Build retrieval policy experiments for Lyme Model.
**Compare:** 7 strategies × 6 metrics.

---

## 1. Retrieval Strategies (7)

| Strategy | Method | Strengths | Weaknesses |
|----------|--------|-----------|------------|
| keyword | grep-based keyword matching | Fast, simple, no deps | Misses synonyms, no semantics |
| embedding | TF-IDF similarity | Catches semantic overlap | Slower, no deps installed |
| graph | Import graph propagation | Uses code structure | Only works for Python imports |
| ast | Function/class symbol matching | Precise for symbol references | Misses conceptual matches |
| git_history | Recently modified files | Great for context recency | Misses stable files |
| hybrid | keyword + embedding + AST weighted | Best coverage | Highest latency |
| model_planned | Task decomposition + entity matching | Targeted retrieval | Heuristic, not learned |

## 2. Metrics (6)

| Metric | Definition | Measurement |
|--------|------------|-------------|
| task_success | Ground truth file in top 10 results | Boolean per trial |
| context_size | Total tokens of retrieved files | Integer |
| latency | Time in ms to complete retrieval | Float |
| irrelevant_context_rate | Retrieved files not in ground truth | Float 0-1 |
| missing_evidence_rate | Ground truth files not retrieved | Float 0-1 |
| hallucination_rate | (N/A for retrieval - measured at generation) | - |

## 3. Experimental Design

- `RetrievalExperiment`: runs polices against tasks with ground truth
- `RetrievalTrial`: single policy × single task result
- `ExperimentReport`: aggregates trials, determines winner

```
For each task T:
    For each policy P:
        result = P.retrieve(T, repo)
        score = matches(result.files, ground_truth)
    Report: success_rate, avg_latency, avg_irrelevant, avg_missing
Winner = highest success_rate, then lowest irrelevant_rate
```

## 4. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/retrieval/__init__.py` | Module exports |
| `src/lyme_model/retrieval/policies.py` | 7 retrieval policy implementations |
| `src/lyme_model/retrieval/experiment.py` | Experiment framework + report |

## 5. Initial Findings

In initial testing on this repo:
- **keyword**: Fastest, best for symbol-heavy tasks
- **hybrid**: Most accurate, but 3x latency of keyword
- **ast**: Precise for function-level tasks
- **graph**: Slow on large repos, but good for dependency-aware tasks

Full comparison requires running against standardized tasks with verified ground truth files.

## 6. Next Week

Week 76 will build the Context Packet Compiler — compiling repo info into small, model-readable packets optimized for small models and low context windows.
