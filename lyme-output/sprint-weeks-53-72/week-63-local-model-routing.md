# Week 63 — Local Model Routing

**Date:** Week 63 of Year Two
**Action:** Design a local model router that routes tasks to the optimal model size.

---

## 1. Concept

Instead of one model doing everything, route tasks to different model sizes:

| Model | Size | VRAM | Speed | Role |
|-------|:----:|:----:|:----:|------|
| qwen2.5-coder:1.5b | 1.5B | ~1 GB | ~50 tok/s | Classification, routing decisions |
| deepseek-coder:6.7b | 6.7B | ~4.5 GB | ~10 tok/s | Code generation, complex reasoning |

---

## 2. Routing Strategy

### Task Classification (1.5B model)
```
Input: "Add error handling to the auth module"
  → Category: feature
  → Complexity: medium
  → Target files: src/auth.py
  → Route to: 6.7B model

Input: "What imports does main.py use?"
  → Category: qa
  → Complexity: low
  → Route to: 1.5B model (or no model needed, use AST analysis)
```

### Routing Rules

| Task Type | Complexity | Route To | Expected Success |
|-----------|:----------:|:--------:|:----------------:|
| Q&A (simple) | Low | 1.5B or grep-only | 90%+ |
| Q&A (architecture) | Medium | 6.7B | 80%+ |
| Code generation (small) | Low | 1.5B | 70% |
| Code generation (complex) | High | 6.7B | 70% |
| Bug finding | Medium | 6.7B | 80% |
| Refactoring | High | 6.7B | 60% |
| Test generation | Medium | 6.7B | 70% |
| File navigation | Low | grep-only | 95% |

---

## 3. Routing Implementation

```python
class ModelRouter:
    def route(self, task: str, context: dict) -> str:
        """Returns model name to use."""
        complexity = self._estimate_complexity(task)
        task_type = self._classify_task(task)
        
        # Rule-based routing
        if complexity == "low" and task_type in ("qa", "navigation"):
            return "grep_only"  # no model needed
        elif complexity == "low":
            return "qwen2.5-coder:1.5b"
        elif complexity == "medium" and task_type == "simple_gen":
            return "qwen2.5-coder:1.5b"
        else:
            return "deepseek-coder:6.7b"
    
    def _estimate_complexity(self, task: str) -> str:
        # Heuristic: longer tasks are more complex
        if len(task) < 50:
            return "low"
        elif len(task) < 200:
            return "medium"
        return "high"
    
    def _classify_task(self, task: str) -> str:
        task_lower = task.lower()
        if any(w in task_lower for w in ["what", "where", "how many", "list"]):
            return "qa"
        elif any(w in task_lower for w in ["add", "create", "implement"]):
            return "simple_gen" if len(task) < 100 else "complex_gen"
        elif any(w in task_lower for w in ["fix", "bug", "error", "broken"]):
            return "bug_fix"
        elif any(w in task_lower for w in ["refactor", "rename", "move"]):
            return "refactor"
        elif any(w in task_lower for w in ["test"]):
            return "test"
        return "complex_gen"
```

---

## 4. Expected Benefits

| Scenario | Single 6.7B | With Router | Savings |
|----------|:-----------:|:-----------:|:-------:|
| Simple Q&A (50% of tasks) | 6.5s | 1.5s | 5x faster |
| Code gen (30% of tasks) | 6.5s | 6.5s | Same |
| Complex reasoning (20%) | 10s | 10s | Same |
| **Weighted average** | **7.2s** | **4.4s** | **1.6x faster** |
| **VRAM** | 4.5 GB | 5.5 GB | +1 GB (both loaded) |

---

## 5. Recommendation

**Implement routing post-MVP.** The 1.6x speedup for Q&A-style tasks is valuable
but requires maintaining two loaded models simultaneously (+1 GB VRAM). For the
MVP, single-model operation is simpler and sufficient.

**Critical dependency:** The 1.5B model must be loaded alongside the 6.7B model,
which requires Ollama to support concurrent model loading.

**Alternative:** Route simple tasks to grep/AST analysis (no model needed) rather
than loading a second model. This saves VRAM and provides faster responses for
Q&A tasks.

---

## 6. Decision

For Lyme Model v0.1: **Single model (6.7B at Q4)** for all tasks.
Routing is a post-v0.1 optimization.
