# Lyme Model Dataset v2 — Blueprint

> Phase 13, Week 81
> Target: Build a serious local coding model dataset

## 1. Modality Expansion (v1 → v2)

v1 had 8 formal modalities + 3 metadata-only categories.
v2 promotes all 11 to first-class modalities:

| # | Modality | v1 Status | v2 Target | Description |
|---|----------|-----------|-----------|-------------|
| 1 | `repo_qa` | existing | 10,000 | Evidence-grounded repo Q&A with citations |
| 2 | `bug_localization` | existing | 5,000 | Find bug location from symptoms |
| 3 | `test_repair` | existing | 8,000 | Fix failing tests |
| 4 | `unified_diff` | existing | 12,000 | Minimal valid unified diff generation |
| 5 | `multi_file_edit` | meta-tag → modality | 4,000 | Multi-file coordinated edits |
| 6 | `tool_use` | existing | 4,000 | Agentic tool sequences |
| 7 | `debugging_trace` | **new** | 3,000 | Full debugging trace with decisions |
| 8 | `patch_critique` | extends verification | 3,000 | Evaluate patch quality |
| 9 | `self_repair` | meta-tag → modality | 3,000 | Fix own patch after failure |
| 10 | `refusal` | existing | 2,000 | Refuse/ask when appropriate |
| 11 | `long_horizon_planning` | meta-tag → modality | 3,000 | Multi-step task planning/execution |
| | **Total** | | **~57,000** | |

## 2. Schema Changes

### 2.1 New Modalities

Add to `VALID_MODALITIES`:
- `debugging_trace`
- `patch_critique`
- `self_repair`
- `multi_file_edit`
- `long_horizon_planning`

### 2.2 New Fields in `LymeExample`

```python
# Optional: for tasks requiring a patch
patch_before: str = ""   # original file content / state
patch_after: str = ""    # expected patched content
patch_diff: str = ""     # unified diff string (canonical format)

# Optional: chain of thought / reasoning trace
reasoning_trace: str = ""

# Optional: candidate patches for ranking (critique modality)
candidate_patches: List[PatchCandidate] = field(default_factory=list)

# Optional: tool call limit / step budget
max_steps: int = 0

# Language tag for language coverage tracking
language: str = ""
```

### 2.3 New Sub-Object

```python
@dataclass
class PatchCandidate:
    patch_id: str
    patch_diff: str
    score: float = 0.0
    issues: List[str] = field(default_factory=list)
    explanation: str = ""
```

### 2.4 New Valid Source

Add `"mined"` to `VALID_SOURCES` for repo-mined examples.

## 3. Target Example Counts by Source

| Source | Count | Method |
|--------|-------|--------|
| v1 pre-existing (carried forward) | 16,328 | Filter, rebalance, re-validate |
| Public repo mining (Week 82) | 15,000 | Commit mining + filtering |
| Synthetic failure factory v2 (Week 83) | 10,000 | Programmatic bug injection |
| Teacher traces (Week 84) | 5,000 | Trace collection from strong models |
| Manually curated | 1,000 | Expert-written examples |
| Previously generated / augmented | ~10,000 | Expand existing pipelines |
| **Total** | **~57,000** | |

## 4. Quality Filters

### 4.1 Mandatory Filters (applied to all examples)

1. **Instruction clarity**: Must contain a complete, parseable task
   - Minimum 10 characters, maximum 2000 characters
   - Must not be a duplicate (exact match with existing)
2. **Target output quality**: Must contain a correct, verifiable answer
   - Minimum 5 characters
   - Must be self-consistent with instruction
   - For patches: must be a syntactically valid unified diff
3. **Context sufficiency**: At least one `retrieved_file` for repo-dependent modalities
4. **No secrets**: Filter out any example containing real credentials, keys, tokens via pattern match
5. **Size limits**:
   - Max 20 retrieved files per example
   - Max 30 tool calls per example
   - Max 8,192 characters in any single field (to fit context window)
6. **Language tag**: Must be set to a recognized language

### 4.2 Task-Specific Filters

| Modality | Specific Filter |
|----------|----------------|
| `unified_diff` | Must parse as valid unified diff; file paths must match context; patch must apply cleanly |
| `test_repair` | Test must fail before patch and pass after; test framework must be identified |
| `bug_localization` | Bug file must be in retrieved_files; bug location must be specific (file:line or function) |
| `multi_file_edit` | Must touch 2-5 files; changes must be internally consistent |
| `tool_use` | Tool sequence must be executable; tools must exist in action grammar |
| `debugging_trace` | Must contain at least 3 steps; must end with a conclusion or patch |
| `patch_critique` | Must include at least 2 candidate patches; score must be justified |
| `self_repair` | Must include original failed attempt; repair must fix the failure |
| `refusal` | Instruction must be ambiguous, dangerous, or impossible; refusal must be appropriate |
| `long_horizon_planning` | Must have 3+ steps; each step must have a verification check |

### 4.3 Removal Rules

Reject any example where:
- `target_output` contains `"[TODO]"`, `"[FIXME]"`, `"TODO:"`, `"FIXME:"`
- Instruction is fewer than 10 characters
- Target output is fewer than 5 characters
- Content contains placeholder text like "Lorem ipsum" or "example.com"
- Any file path contains `/node_modules/`, `/vendor/`, `/venv/`, `/__pycache__/`
- More than 500 lines added or removed in a diff
- Source is `synthetic` and no quality score > 0.7

## 5. Train/Val/Test Split Plan

### 5.1 Strategy

- **Stratified sampling**: Split per-modality, then per-source, then per-language
- **Ratio**: 80% train, 10% validation, 10% test
- **Held-out sets**:
  - `eval_real_repo`: Real repo examples excluded from training (for real-world eval)
  - `held_out_languages`: Russian, Ukrainian, Arabic, Hindi, Chinese comments/docs (train on English only if testing cross-lingual)
  - `hard_only`: All "expert" difficulty examples reserved for final eval

### 5.2 Splits

| Split | Count | Purpose |
|-------|-------|---------|
| **sft** | ~40,000 | Main supervised fine-tuning |
| **tool_policy** | ~5,000 | Tool-use behavior training |
| **critic** | ~4,000 | Critic/verification model training |
| **eval_real_repo** | ~3,000 | Held-out real-world evaluation |
| **held_out_hard** | ~2,000 | Expert difficulty only, never seen in training |
| **distillation_targets** | ~3,000 | Teacher outputs for behavioral distillation |

### 5.3 No Leakage Rules

1. **No repo overlap**: If a repo contributes to train, no examples from same repo go to eval held-out
2. **No problem overlap**: If a bug class appears in train, val/test use different code examples
3. **No source overlap**: Real repo mined examples from repo X cannot appear in both sft and held_out_real_repo
4. **ID-based dedup**: All examples get v2 IDs prefixed with `v2-` + modality + UUID; v1 IDs are remapped
5. **Hash-based near-dedup**: MinHash LSH on instruction text to find near-duplicates; keep only one per cluster

## 6. Language Coverage Plan

### 6.1 Primary Languages (≥5,000 examples each)

| Language | Target Count | Coverage Priority |
|----------|-------------|-------------------|
| Python | 20,000 | Comprehensive (all modalities) |
| JavaScript/TypeScript | 10,000 | Full coverage |
| Go | 5,000 | Full coverage |
| Rust | 5,000 | Full coverage |

### 6.2 Secondary Languages (1,000–5,000 examples each)

| Language | Target Count | Coverage Priority |
|----------|-------------|-------------------|
| Java | 3,000 | Core modalities |
| C/C++ | 2,000 | Bug localization, unified diff |
| Ruby | 1,500 | Core modalities |
| Shell/Bash | 1,500 | Tool use, unified diff |

### 6.3 Tertiary Languages (500–1,000 examples each)

| Language | Target Count | Coverage Priority |
|----------|-------------|-------------------|
| C# | 1,000 | unified_diff, tool_use |
| PHP | 500 | unified_diff |
| Swift | 500 | unified_diff |
| Kotlin | 500 | unified_diff |
| R | 500 | repo_qa, bug_localization |

### 6.4 Language Tagging

Every example MUST have a `language` field in metadata. Multi-language repos tag the primary language of the edit.

## 7. Difficulty Distribution Target

| Difficulty | Target % | Count |
|------------|----------|-------|
| Trivial | 10% | ~5,700 |
| Easy | 25% | ~14,250 |
| Medium | 35% | ~19,950 |
| Hard | 20% | ~11,400 |
| Expert | 10% | ~5,700 |

## 8. Dataset Delivery Format

### 8.1 Directory Structure

```
datasets/v2/
  DATASET_CARD.md
  dataset_stats.json
  sft/
    train/  (combined.jsonl + per-modality .jsonl)
    val/    (combined.jsonl + per-modality .jsonl)
    test/   (combined.jsonl + per-modality .jsonl)
  tool_policy/
    train/  (combined.jsonl + tool_use.jsonl)
    val/    (combined.jsonl + tool_use.jsonl)
    test/   (combined.jsonl + tool_use.jsonl)
  critic/
    train/  (combined.jsonl + patch_critique.jsonl + verification.jsonl)
    val/    (combined.jsonl + patch_critique.jsonl + verification.jsonl)
    test/   (combined.jsonl + patch_critique.jsonl + verification.jsonl)
  eval_real_repo/
    train/  (...)
    val/    (...)
    test/   (...)
  held_out_hard/
    test/   (combined.jsonl)
  distillation_targets/
    train/  (combined.jsonl)
    val/    (combined.jsonl)
    test/   (combined.jsonl)
  tools/
    assemble_v2.py
    validate_v2.py
    compute_stats.py
    leak_check.py
    quality_filter.py
```

### 8.2 Build Pipeline

1. `assemble_v2.py` — Merges sources, filters, splits, deduplicates
2. `validate_v2.py` — Schema validation (extends `validate_jsonl`)
3. `compute_stats.py` — Statistics generation (extends `compute_statistics`)
4. `leak_check.py` — Cross-split and cross-source leakage detection
5. `quality_filter.py` — Post-generation quality scoring and filtering

## 9. Benchmark Delta Target

Compare Lyme Model trained on v1 vs v2:

| Metric | v1 Baseline | v2 Target | Delta |
|--------|------------|-----------|-------|
| Patch validity | 67% | 80% | +13% |
| Test repair pass@1 | 50% | 70% | +20% |
| Bug localization top-3 | 60% | 80% | +20% |
| Multi-file edit success | 40% | 65% | +25% |
| Tool action parse rate | 75% | 90% | +15% |
| Refusal accuracy | 80% | 92% | +12% |

## 10. Failure Analysis (v1 Dataset)

| Failure Mode | Root Cause | v2 Fix |
|-------------|------------|--------|
| Patch invalid diffs | Not enough real diff examples; minimal diffs with extra context | More mined real diffs; strict parser feedback |
| Test repair overfits to synthetic tests | Synthetic tests are too simple | Real repo test failure pairs |
| Bug localization too vague | Examples say "somewhere in this file" | Force specific file:line or function identification |
| Tool-use sequences too short | Traces are 2-3 calls, unrealistic | Teacher traces with 5-15 step sequences |
| Multi-file edits have internal inconsistency | Generated independently | Coordinated generation with cross-file consistency checks |
| Refusal examples are too few | Only 122 examples | Expand to 2,000 with nuanced categories |
| Long-horizon planning is too simple | Only 3-step plans | Upgrade to 5-12 step plans with verification |

## 11. Next Steps

- Week 82: Build public repo mining pipeline (target: 15,000 mined examples)
- Week 83: Build synthetic failure factory v2 (target: 10,000 synthetic bugs)
- Week 84: Build teacher trace factory (target: 5,000 traces)
- Week 85: Assemble Dataset v2 (target: ~57,000 examples across 11 modalities)
