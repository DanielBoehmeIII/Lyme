# Week 65 — Distillation From Strong Models

**Date:** Week 65 of Year Two
**Action:** Design a distillation pipeline that uses strong models to generate training data for local Lyme Model.

---

## 1. Concept

Use a strong model (Claude, GPT-4, or Codex) to generate high-quality task examples,
then train the local Lyme Model on those examples.

```
Strong Model (Teacher)
  |-- task + repo context
  |-- generates: reasoning + tool sequence + patch
  |-- validates: passes tests
  v
Distillation Dataset
  |-- [task, context, tool_sequence, patch, verification]
  v
Lyme Model (Student)
  |-- trained on distilled examples
  |-- evaluated on held-out tasks
```

---

## 2. Dataset Schema

```python
@dataclass
class DistillationExample:
    # Task
    task: str                          # "Fix divide by zero in calculator.py"
    task_type: str                     # "bugfix", "feature", "refactor", "qa"
    repo_context: str                  # Compressed repo summary (L1-L4)
    
    # Solution
    tool_sequence: List[Dict]          # [{"tool": "read_file", "params": {...}}, ...]
    reasoning: str                     # Step-by-step reasoning
    patch: str                         # Final code change
    
    # Verification
    verification_command: str          # "python -m pytest tests/"
    verification_result: bool          # True = passed
    test_output: str                   # Test output
    
    # Metadata
    teacher_model: str                 # "claude-sonnet-4"
    difficulty: float                  # 0.0-1.0
    timestamp: str
```

---

## 3. Quality Filters

| Filter | Criteria | Expected Pass Rate |
|--------|----------|:------------------:|
| Syntax check | Patch compiles | 90% |
| Test pass | All tests pass after patch | 70% |
| No hallucination | No fabricated functions | 85% |
| Minimal change | <30% of file changed | 80% |
| Human review | (optional) Expert review | Variable |

**Expected yield:** ~40% of generated examples pass all quality filters.

---

## 4. Generation Pipeline

```python
class DistillationPipeline:
    def __init__(self, teacher_model: str = "claude-sonnet-4"):
        self.teacher = teacher_model
        self.dataset = []
    
    def generate_example(self, task: dict, repo: str) -> DistillationExample:
        # Step 1: Build compressed context
        context = compress_repo(repo)
        
        # Step 2: Ask teacher to solve the task
        teacher_response = query_teacher(task, context)
        tool_sequence = parse_tools(teacher_response)
        patch = extract_patch(teacher_response)
        
        # Step 3: Verify the patch
        passed, output = run_verification(patch, repo)
        
        # Step 4: Apply quality filters
        if not passed:
            return None  # Discard
        
        # Step 5: Format as training example
        return DistillationExample(
            task=task,
            task_type=task["type"],
            repo_context=context,
            tool_sequence=tool_sequence,
            reasoning=extract_reasoning(teacher_response),
            patch=patch,
            verification_command=task.get("verification", ""),
            verification_result=passed,
            test_output=output,
            teacher_model=self.teacher,
        )
    
    def build_dataset(self, tasks: List[dict], repo: str) -> List[DistillationExample]:
        for task in tasks:
            example = self.generate_example(task, repo)
            if example:
                self.dataset.append(example)
        return self.dataset
```

---

## 5. Dataset Sizing

| Dataset Size | Expected Quality Gain | Collection Time | Notes |
|:-----------:|:--------------------:|:---------------:|-------|
| 50 examples | +5% | 1 day | Minimum viable |
| 200 examples | +10% | 3 days | Practical first target |
| 1000 examples | +15-20% | 2 weeks | Research-grade |
| 5000 examples | +20-30% | 2 months | Production-grade |

**Target for first experiment: 200 examples** (3 days of generation + verification).

---

## 6. Privacy and Safety

| Concern | Mitigation |
|---------|------------|
| Private code in training data | Use redacted/placeholder repos for generation |
| Teacher API costs | ~$10-20 for 200 examples (Claude API) |
| Dataset leakage | Never train on production code |
| Model theft | Distillation produces smaller, less capable model |

---

## 7. Recommendation

**Build the distillation dataset in parallel with runtime development.**

The pipeline design is straightforward but generating 200 high-quality examples
requires API credits and manual verification. Start with:

1. **5 manual examples** to validate the schema and pipeline
2. **50 synthetic examples** from benchmark scenarios (no API cost)
3. **200 examples** from teacher model (requires API credits)

**Defer actual distillation training** until the dataset reaches 200+ examples
and a training pipeline exists (Week 66+).

---

## 8. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/distill/` | Module stub created but not yet implemented |
