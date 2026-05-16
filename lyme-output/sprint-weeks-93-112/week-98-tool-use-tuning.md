# Week 98 — Tool-Use Fine-Tuning

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/tool_use_training.py`
**Tests:** `tests/test_week98_tool_use.py` (21 tests, all passing)

**Tool-use fine-tuning experiment** with 3 model variants for tool-use decisions:
1. **HeuristicRouter** — rule-based baseline (7 actions)
2. **PromptedPolicyVariant** — instruction-tuned model with few-shot rules
3. **TrainedPolicyVariant** — learned weights from training data

---

## 2. Action Space (7)

| Action | When to Use |
|--------|-------------|
| `search` | Need to find code by pattern |
| `read` | Need to understand file contents |
| `inspect_ast` | Need to check symbol definitions |
| `run_command` | Need to execute tests or commands |
| `generate_patch` | Ready to make the edit |
| `verify` | Patch applied, need to check correctness |
| `stop` | Task complete or stuck |

---

## 3. Experiment Results

| Variant | Accuracy | Type |
|---------|----------|------|
| HeuristicRouter | 0.429 | Rule-based |
| Prompted (Qwen2.5-Coder-1.5B-Instruct) | 0.429 | Prompted |
| TrainedPolicy | 0.429 | Trained |

**Winner**: HeuristicRouter (tie — all rule-based in simulation)

**Note:** All three converge to the same accuracy because the prompted and trained variants currently derive from the same heuristic rules. Real differentiation requires actual model inference.

### By-Action Distribution

| Action | Examples |
|--------|----------|
| search | 11 |
| generate_patch | 9 |
| read | 6 |
| stop | 6 |
| verify | 6 |
| run_command | 5 |
| inspect_ast | 2 |

---

## 4. Training Data

| Source | Count |
|--------|-------|
| Standard traces (3) | 32 event-level examples |
| Synthetic scenarios | 7 |
| Edge cases | 6 |
| **Total** | **45** |

Split: 31 train / 14 test

---

## 5. Files

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/tool_use_training.py` | Data generator, 3 policy variants, experiment runner |
| `tests/test_week98_tool_use.py` | 21 tests |
| `lyme-output/experiments/tool-use/tool_use_experiment.json` | Experiment results (JSON) |
| `lyme-output/experiments/tool-use/tool_use_experiment.md` | Experiment results (Markdown) |

---

## 6. Next Week

Week 99 — Patch Planning Fine-Tuning: train a model specifically for patch planning with repo context, risk assessment, and verification command.

---

## End of Week 98

**Tool-use tuning infrastructure built. 3 policy variants compared. 45 training examples across 7 action types. Real model inference deferred until GPU environment available.**
