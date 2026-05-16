# Week 96 — Lyme Model Dataset v0.1

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/dataset_v01.py`
**Tests:** `tests/test_week96_dataset_v01.py` (24 tests, all passing)

**Generated dataset:** `lyme-output/datasets/v01/`

---

## 2. Dataset Statistics

| Metric | Value |
|--------|-------|
| Total examples | 35 |
| Train | 27 |
| Validation | 3 |
| Test | 5 |
| Sources | 32 synthetic + 3 Lyme Audit traces |
| Sanitization | Applied |

### By Task Type

| Task Type | Count |
|-----------|-------|
| qa | 8 |
| explain_failure | 5 |
| locate_bug | 4 |
| plan_patch | 4 |
| apply_patch | 4 |
| refuse | 4 |
| verify_patch | 3 |
| recover | 3 |

### By Difficulty

| Difficulty | Count |
|-----------|-------|
| medium | 20 |
| easy | 12 |
| hard | 3 |

---

## 3. Exported Files

```
lyme-output/datasets/v01/
├── dataset_card.json      # Machine-readable dataset card
├── dataset_card.md        # Human-readable dataset card
├── lyme_dataset_v01.json  # Full dataset (all examples + modality views)
├── train/
│   ├── examples.jsonl      # 27 training examples
│   ├── sft.jsonl           # SFT format views
│   ├── tool_use.jsonl      # Tool-use imitation views
│   ├── patch_critic.jsonl  # Patch critic training views
│   ├── retrieval.jsonl     # Retrieval ranking views
│   └── verifier.jsonl      # Verifier training views
├── validation/
│   ├── examples.jsonl      # 3 validation examples
│   ├── sft.jsonl
│   └── verifier.jsonl
└── test/
    ├── examples.jsonl      # 5 test examples
    ├── sft.jsonl
    └── patch_critic.jsonl
```

---

## 4. Data Sources

| Source | Method | Count |
|--------|--------|-------|
| Synthetic repos | Generated from 5 templates (calc-app, todo-api, data-pipeline, cli-tool, blog-engine) | 32 |
| Lyme Audit traces | Converted from `lyme-output/standards/traces/` (simple-fix, refactor, failed-attempt) | 3 |

---

## 5. Known Limitations

1. **Small dataset size** — 35 examples is not sufficient for full model training
2. **Synthetic repos only** — all examples use 5 fictional template repos
3. **Single-file patches** — no multi-file change examples
4. **No real user data** — all examples curated or generated
5. **Limited refusal scenarios** — only 4 unsupported claim patterns
6. **Hand-crafted traces** — only 3 reference traces from standards directory
7. **Heuristic difficulty labels** — not validated against model performance
8. **Repo-isolated** — no cross-repo transfer examples

---

## 6. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/dataset_v01.py` | Dataset generator, exporter, card |
| `tests/test_week96_dataset_v01.py` | 24 tests |
| `lyme-output/datasets/v01/` | Exported dataset (11 files) |

---

## 7. Next Week

Week 97 — SFT Feasibility Run: fine-tune smallest practical coding model with LoRA/QLoRA on a narrow skill.

---

## End of Week 96

**Lyme Model Dataset v0.1 generated: 35 examples, 8 task types, 3 splits, sanitized, exported with dataset card.**
