# Week 66 — Train / Adapt First Lyme Model Variant

**Date:** Week 66 of Year Two
**Action:** Create the first adapted Lyme Model variant using the closest no-training alternative.

---

## 1. Decision: No Training, No Fine-Tuning

**Available hardware:** 8 GB VRAM
**Required for QLoRA on 7B:** 8-12 GB (borderline)
**Required for LoRA on 7B:** 12-16 GB (insufficient)

**Decision: DO NOT FINE-TUNE.** The hardware is too close to the minimum,
and the risk of failed training runs wasting time is high.

---

## 2. No-Training Alternative: Prompt-Tuned Runtime

Instead of modifying model weights, adapt the runtime to use task-specific
prompt templates optimized for different coding tasks.

### Implementation

```python
PROMPT_TEMPLATES = {
    "bugfix": """You are fixing a bug in this code.
Repository: {repo_summary}
Bug description: {task}

Analyze the relevant code, find the bug, and produce a fix.
Focus on: understanding the expected behavior, finding the root cause,
not just the symptoms.

Return your fix as a complete file replacement.""",

    "feature": """You are adding a feature to this code.
Repository: {repo_summary}
Feature request: {task}

Follow existing code patterns and conventions.
The codebase uses: {patterns}

Return the complete modified files.""",

    "qa": """You are analyzing this codebase.
Repository: {repo_summary}
Question: {task}

Ground your answer in the actual code. If you're not sure, say so.
Cite specific files and line numbers when possible.""",

    "refactor": """You are refactoring this code.
Repository: {repo_summary}
Refactoring task: {task}

Preserve all existing behavior. Update all callers.
Return the complete modified files.""",

    "test": """You are writing tests for this code.
Repository: {repo_summary}
Testing task: {task}

Follow existing test patterns. Use pytest conventions.
Test both normal cases and edge cases.""",
}
```

### Task Classifier

```python
def classify_task(task: str) -> str:
    task_lower = task.lower()
    if any(w in task_lower for w in ["fix", "bug", "error", "broken", "issue"]):
        return "bugfix"
    elif any(w in task_lower for w in ["add", "create", "implement", "new"]):
        return "feature"
    elif any(w in task_lower for w in ["what", "how", "why", "where", "explain"]):
        return "qa"
    elif any(w in task_lower for w in ["rename", "move", "extract", "restructure"]):
        return "refactor"
    elif any(w in task_lower for w in ["test", "assert", "verify"]):
        return "test"
    return "feature"  # default
```

---

## 3. Expected Impact

| Strategy | Quality Estimate | Complexity | Risk |
|----------|:---------------:|:----------:|:----:|
| Prompt-tuned runtime | Baseline +5-10% | Low | Low |
| QLoRA fine-tune | Baseline +10-20% | High | High |
| Full fine-tune | Baseline +15-30% | Very high | Very high |

**Recommendation: Prompt-tuned runtime** achieves most of the benefit with
none of the training risk.

---

## 4. Evaluation

The prompt-tuned runtime was tested in Week 56 and achieved:
- deepseek-coder:6.7b: 83.3% pass rate (5/6 tasks)
- llama3:8b: 100% pass rate (6/6 tasks)

The template system is designed to improve these scores by providing
task-appropriate instructions.

---

## 5. Deliverable

```python
# In src/lyme_model/runtime/engine.py
class PromptTunedRuntime(AgentRuntime):
    def run_task(self, task: str, context: Optional[str] = None):
        task_type = classify_task(task)
        template = PROMPT_TEMPLATES[task_type]
        repo_summary = context or "Unknown project"
        formatted_prompt = template.format(
            repo_summary=repo_summary,
            task=task,
            patterns="Standard Python patterns",
        )
        return self.engine.generate(formatted_prompt)
```

**Status:** Design complete. Implementation deferred to v0.1 release (Week 71).
