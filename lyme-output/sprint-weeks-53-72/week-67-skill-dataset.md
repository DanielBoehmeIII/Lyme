# Week 67 — Coding-Agent Skill Dataset

**Date:** Week 67 of Year Two
**Action:** Build a dataset definition for local coding-agent skills.

---

## 1. Skill Categories

| Category | Description | Example Task | Count (planned) |
|----------|-------------|-------------|:---------------:|
| locate-bug | Find and describe a bug from symptoms | "Login fails with valid credentials" | 20 |
| explain-file | Explain what a module does | "What does auth.py do?" | 15 |
| run-tests | Execute tests and interpret results | "Run tests and report failures" | 10 |
| repair-test | Fix a failing test | "test_login is failing" | 15 |
| modify-api | Add a new endpoint/function | "Add DELETE /users/{id}" | 15 |
| add-feature | Implement a small feature | "Add pagination to list_users" | 10 |
| refactor-safe | Rename/extract safely | "Rename User to Account" | 10 |
| avoid-hallucination | Answer accurately without fabricating | "What methods does CloudClient have?" | 10 |
| cite-evidence | Support claims with file references | "Why is this code vulnerable?" | 10 |

**Total: 115 examples** (covers all skill categories)

---

## 2. Example Format

```python
@dataclass
class SkillExample:
    skill: str                       # "locate-bug"
    task: str                        # Task description
    repo_context: str                # Compressed repo summary
    correct_tool_sequence: List[str] # ["grep_search(login)", "read_file(auth.py)"]
    expected_patch: str              # The correct code change
    verification: str                # How to verify the fix
    failure_traps: List[str]         # Common mistakes to avoid
    difficulty: float                # 0.0-1.0
```

### Example Entry

```json
{
  "skill": "repair-test",
  "task": "The test test_divide_by_zero fails. Fix the divide function to handle division by zero.",
  "repo_context": "L1: 2 files (calculator.py, test_calculator.py); L2: functions=divide; L4: invariant=functions should handle edge cases",
  "correct_tool_sequence": [
    "read_file(calculator.py)",
    "read_file(test_calculator.py)", 
    "think(divide function doesn't check for zero divisor)",
    "edit_file(calculator.py)"
  ],
  "expected_patch": "def divide(a, b):\n    if b == 0:\n        raise ZeroDivisionError('Cannot divide by zero')\n    return a / b",
  "verification": "python -m pytest test_calculator.py -v",
  "failure_traps": [
    "Returning None instead of raising an error",
    "Only fixing the test, not the source code",
    "Changing the function signature instead of adding a guard"
  ],
  "difficulty": 0.5
}
```

---

## 3. Generation Strategy

| Source | Method | Count | Quality |
|--------|--------|:-----:|:-------:|
| Existing benchmarks | Extract from 21 Audit benchmark scenarios | 21 | High |
| Manual creation | Write by hand from real debugging experience | 20 | Highest |
| Teacher model | Generate via strong model (Claude/Codex) | 50 | Medium-High |
| Synthetic mutation | Take working code, introduce bug, ask for fix | 24 | Medium |

**Total: ~115 examples** — enough for a meaningful evaluation suite.

---

## 4. Dataset Usage

The dataset serves two purposes:

### 1. Evaluation
Run Lyme Model against the dataset to measure skill-specific performance:
```bash
lyme model eval --dataset skills.json
```

### 2. Training (future)
If fine-tuning becomes feasible, the dataset provides labeled examples:
```python
# Each example becomes a training pair
train_prompt = f"Task: {example.task}\nContext: {example.repo_context}"
train_completion = f"Tool sequence: {example.correct_tool_sequence}\nPatch: {example.expected_patch}"
```

---

## 5. Deliverable

**Status:** Schema defined (above). Dataset creation deferred to post-v0.1.
The 21 existing Audit benchmark scenarios serve as the initial evaluation set.

**File:** `src/lyme_model/eval/suite.py` (to be implemented with skill dataset)
