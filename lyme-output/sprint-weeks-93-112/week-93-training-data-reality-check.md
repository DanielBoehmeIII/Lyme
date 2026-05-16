# Week 93 — Training Data Reality Check

**System:** Lyme Audit measures. Lyme Model competes.

---

## Executive Summary

This week audits every Lyme Audit trace, generated artifact, and existing data source for training usefulness. The conclusion is honest: **we have ~3-5 genuinely usable traces** for supervised learning. The majority of data is skeleton/synthetic, and no current dataset is large enough for gradient-based training. This report provides the inventory, quality scores, risk analysis, and a concrete collection plan.

---

## 1. Data Source Inventory

### Source A: `.lyme/audit/` — Real Audit Traces (5 entries)

| Audit ID | Kind | Description | Timestamp | Has Tool Calls? | Has Patches? | Has Outcome? |
|----------|------|-------------|-----------|----------------|-------------|--------------|
| `98c75876-2047-4d23-b89f-64b46687f7cd` | diagnose | Ran lyme doctor | 2026-05-16 | No | No | Yes (completed) |
| `c65e5969-0640-4f05-9d7d-5b562c9d44cb` | benchmark | Ran latency baseline | 2026-05-16 | No | No | Yes (completed) |
| `63e3d91c-248c-4287-a688-97e3f6cb62ce` | benchmark | Ran latency baseline | 2026-05-16 | No | No | Yes (completed) |
| `7e842cf5-b803-4df1-a8ab-538970c7c97f` | diagnose | Ran lyme doctor | 2026-05-16 | No | No | Yes (completed) |
| `53b6f66c-8b32-4602-a152-b0b1e1de301f` | test | Verification test | 2026-05-16 | No | No | Yes (completed) |

**Verdict: 0/5 usable for training.** These are skeleton entries with no tool call traces, no patches, no observations, no intermediate state. They record *that* something happened, not *how*.

### Source B: `lyme-output/standards/traces/` — Reference Standard Traces (3 traces)

| Trace ID | Schema | Events | Outcome | Quality |
|----------|--------|--------|---------|---------|
| `oat-simple-fix-001` | Open Agent Trace v0.7.0 | 6 (model_call, file_read, file_edit, test_run, evidence_claim, verification) | All tests pass | High — full tool sequence |
| `oat-refactor-002` | Open Agent Trace v0.7.0 | 15 (model_call, 3 file_reads, 5 file_edits, test_run, failed_attempt, confidence_change, verification, human_intervention, evidence_claim) | Completed after retry | High — includes failure + recovery |
| `oat-failed-003` | Open Agent Trace v0.7.0 | 11 (model_call, 3 file_edits, 2 test_runs, 2 failed_attempts, confidence_change, human_intervention, rollback) | Abandoned | High — failure sequence with human correction |

**Verdict: 3/3 usable for training.** Each has:
- Clear task instruction (in header.tags.task or events[0].prompt_preview)
- Sequential tool calls with timestamps
- Intermediate observations (evidence_claim events)
- Patches with before/after previews
- Verification results (test_run events)
- Failure recovery (failed_attempt → retry events)
- Final outcome (completed/abandoned in summary.status)

### Source C: `lyme-output/ci/` — CI Run Traces (11 runs, 33 files)

| Pattern | Count | Data Quality |
|---------|-------|-------------|
| `ci-*-trace.json` | 11 | Skeleton — 2 events each (system + metric), no tool calls |
| `ci-*-audit.json` | 11 | Minimal — risk_score, decision, policy_decision |
| `ci-*-semantic-diff.json` | 11 | Trivial — empty arrays |

**Verdict: 0/33 usable for training.** CI traces contain no tool call sequences, no patches, no intermediate observations. They are operation metadata, not cognitive traces.

### Source D: `lyme-output/demo-v0.7/` — Demo Artifacts

| File | Content | Training Value |
|------|---------|---------------|
| `01-pr-intelligence-report.json` | GitHub PR analysis report | **Evaluation only** — static report, no agent actions |
| `02-open-agent-trace.json` | Duplicate of oat-refactor-002 | Same as Source B (already counted) |
| `03-semantic-diff.json` | Diff classification | **Patch critique** — diff with classification |
| `03-semantic-diff.md` | Same in markdown | Same |
| `07-benchmark-leaderboard.json` | Benchmark results | **Evaluation only** — scores only |
| `08-corpus-export.jsonl` | Corpus of 1 trace | Same as Source B |
| `ci-artifacts/` | CI artifacts | **Evaluation only** |
| `research-corpus/` | Research templates | **Evaluation only** |
| `research-portal/` | Portal HTML/data | **Evaluation only** |

**Verdict: 1 file usable for patch critique** (03-semantic-diff.json). The rest is evaluation-only or duplicate.

### Source E: `lyme-experiments/synthetic/` — Synthetic Test Project

A complete synthetic repo with 17 test files and 7 service modules. Contains architecture docs and test infrastructure. Could be used as a target repo for synthetic data generation.

**Verdict: Usable as a test environment** for generating training data, not training data itself.

### Source F: Generated Data (in code)

| Generator | Output Type | Count | Training Value |
|-----------|------------|-------|---------------|
| `DataGenerator.generate_synthetic()` | `ToolExample` | 50 | **Low** — 20% random labels, hand-crafted situations |
| `ToolPolicyModel.train_step()` | Weight adjustments | N/A | **Not real training** — simulated weight updates |
| `PatchCritic.evaluate()` | `CriticVerdict` | N/A | **Rule-based** — could create critique training data |

### Source G: `lyme-output/memory/` — Memory Store

| File | Content | Training Value |
|------|---------|---------------|
| `index.json` | Memory index | **Evaluation only** |
| `*.json` (UUID) | Individual memories | **Evaluation only** — structured observations |

---

## 2. Classification Summary

| Category | Count | Sources |
|----------|-------|---------|
| 1. Usable for supervised fine-tuning | 3 | Standard traces (simple-fix, refactor, failed-attempt) |
| 2. Usable for tool-policy learning | 3 | Standard traces (tool sequences explicitly recorded) |
| 3. Usable for retrieval-policy learning | 0 | No traces capture retrieval decisions |
| 4. Usable for patch critique | 4 | 3 standard traces + 1 semantic diff |
| 5. Usable only for evaluation | ~30+ | CI traces, audit skeletons, benchmark results, memory stores |
| 6. Unusable / synthetic / misleading | 50+ | `generate_synthetic()` output with random labels |

**Bottom line: We have exactly 3 high-quality traces for any form of supervised learning.**

---

## 3. Quality Score

### Per-Trace Quality Assessment

| Trace | Completeness | Correctness | Granularity | Verifiability | Overall |
|-------|-------------|-------------|-------------|---------------|---------|
| `oat-simple-fix-001` | 0.9 | 1.0 | 0.8 | 0.9 | **0.90** |
| `oat-refactor-002` | 0.95 | 1.0 | 0.9 | 1.0 | **0.96** |
| `oat-failed-003` | 0.9 | 1.0 | 0.95 | 0.9 | **0.94** |
| Semantic diff (demo) | 0.6 | 0.9 | 0.5 | 0.7 | **0.68** |
| CI traces (avg) | 0.2 | 0.8 | 0.1 | 0.3 | **0.35** |
| Audit skeletons (avg) | 0.1 | 0.9 | 0.05 | 0.3 | **0.34** |
| Synthetic gen (avg) | 0.5 | 0.5 | 0.4 | 0.3 | **0.43** |

**Overall dataset quality score: 0.38** (weighted by count, dominated by low-quality entries)

**Usable subset quality score: 0.93** (just the 3 standard traces)

---

## 4. Leakage Risks

### Risk 1: Synthetic Trace Replication
The 3 standard traces use fictional project names and file paths. However, if these patterns match real projects that agents later encounter, the model may overfit to these specific structures.

**Severity: Low** — paths like `/src/pagination.py` are generic enough.

### Risk 2: Model-Specific Traces
Standard traces attribute actions to specific models (`claude-3-opus`, `gpt-4-turbo`, `claude-3-haiku`). Training on these could leak the assumption that certain models behave in certain ways.

**Severity: Medium** — models evolve. Traces should be model-agnostic for training.

### Risk 3: Repo Identifiers
Trace headers include `repo_name` fields (e.g., `sample-project`, `legacy-ecommerce`, `broken-project`). These are fictional but the field exists for real data.

**Severity: Low (current) / High (future)** — no real repo names yet, but the field is populated.

### Risk 4: User Information
The `human_intervention` events contain `user_message` fields. In the standard traces, these contain "This looks good. Approved for merge." — benign. In real traces, these could leak sensitive information.

**Severity: Low (current) / Critical (future)** — sanitization is required before training.

### Risk 5: File Path Leakage
Trace events contain `file_path` fields with absolute paths. Current traces use `/src/...` paths which are generic.

**Severity: Low (current) / High (future)** — real traces would leak local filesystem structure.

---

## 5. Hallucination Risks

### Risk 1: Synthetic Task / Generated Patch Mismatch
The `generate_synthetic()` method creates situations and randomly assigns correctness (20% chance of wrong label). This means ~10 synthetic examples have incorrect action labels. Training on these teaches the model that wrong answers are sometimes correct.

**Severity: Medium** — affects synthetic data only, but synthetic data is 50/53 of the current total.

### Risk 2: Simulated Training Without Real Gradients
`ToolPolicyModel.train_step()` adjusts weights by multiplying by 1.01/0.99. This is NOT gradient descent. Using this as a proxy for real training creates an illusion of learning.

**Severity: High** — the simulated training is misleading and should be clearly labeled as a prototype.

### Risk 3: Patch Content Without Source Context
Standard traces include `patch_hash` and text previews but NOT the full file content before/after. A model trained only on diffs may learn to patch patterns without understanding repository context.

**Severity: Medium** — patch critique training specifically needs before/after context.

### Risk 4: No "I Don't Know" Examples
None of the current data includes refusals or uncertainty expressions. A model trained only on successful/failed attempts will always try to produce an answer, even when insufficient information exists.

**Severity: High** — missing critical safety behavior.

---

## 6. Missing Labels

| Label Type | Current Coverage | Gap |
|------------|-----------------|-----|
| Task instruction | 3/3 standard traces have it | Missing from CI, audit skeletons |
| Repo state summary | None structured | No trace has a formal repo state snapshot |
| Relevant files | 3/3 standard traces have file_read events | Not explicitly labeled as "relevant" |
| Tool calls | 3/3 standard traces | Not labeled as correct/incorrect |
| Intermediate observations | 3/3 have evidence_claim events | Not labeled as grounded/hallucinated |
| Patch plan | 0/3 | No trace has an explicit patch plan before execution |
| Patch | 3/3 have file_edit events | Not extracted as standalone training target |
| Verification result | 3/3 have test_run + verification | Not labeled as comprehensive/superficial |
| Failure recovery | 2/3 have failed_attempt + retry | Not labeled as appropriate/inappropriate |
| Final answer | 0/3 | No trace has a structured final answer |
| Difficulty rating | 3/3 in tags | Not used in training data |
| Risk score | 1/3 has risk tag | Not in training schema |

**Critical missing label: Correctness.** No trace explicitly labels which decisions were correct, which were mistakes, or which alternative actions would have been better.

---

## 7. Next Data Collection Plan

### Phase 1: Instrument for Real Collection (Immediate)

| Action | Target | Priority |
|--------|--------|----------|
| Instrument `lyme model run` to capture detailed tool traces | The 3 runtime engines | P0 |
| Add `repo_state` snapshot at trace start | Runtime trace schema | P0 |
| Add `patch_plan` field before file_edit events | Runtime trace schema | P1 |
| Capture full file content before/after edits | Runtime trace schema | P1 |
| Label tool calls as success/failure/irrelevant | Runtime trace schema | P1 |
| Add final answer field to trace summary | Runtime trace schema | P0 |

### Phase 2: Generate From Synthetic Repos (Weeks 94-96)

| Action | Target | Count |
|--------|--------|-------|
| Create tool-use examples using `lyme-experiments/synthetic/` | 7 action types | 50-100 |
| Create patch-plan examples from intentional bugs | Multi-file fixes | 20-50 |
| Create verification examples with known outcomes | Pass/fail patterns | 30-60 |
| Create refusal examples for unsupported claims | Uncertainty scenarios | 10-20 |

### Phase 3: Curate Real Runs (Weeks 97-100)

| Action | Target | Count |
|--------|--------|-------|
| Collect traces from real `lyme model` usage | All modules | 100-500 |
| Human-verify a subset for correctness | Small initial set | 20-50 |
| Create preference pairs from real runs | Better/worse outputs | 30-100 |

### Phase 4: Dataset Growth Targets

| Milestone | Examples | Use Case |
|-----------|----------|----------|
| v0.1 | 100-200 | SFT feasibility |
| v0.2 | 500-1000 | Tool policy training |
| v0.3 | 1000-5000 | Patch critic training |
| v0.4 | 5000+ | Multi-task training |

---

## 8. Recommendations

1. **Do NOT train on synthetic data** — the 20% random label noise will degrade any learned model
2. **Do NOT use simulated training as a proxy** — `ToolPolicyModel.train_step()` should be clearly labeled as a prototype only
3. **Start collecting real traces immediately** — instrument the runtime before Week 96
4. **Generate data from synthetic repos** — controlled environments produce clean labels
5. **Add explicit labels** — correctness, grounding, difficulty to every trace
6. **Sanitize everything** — build the sanitizer before any training data leaves local storage
7. **Keep the 3 standard traces as eval-only** — they are too few to train on but perfect for measuring progress

---

## End of Week 93

**3 usable traces identified. 50+ synthetic examples marked misleading. Simulated training flagged as risk. Collection plan defined. Data quality score: 0.38 overall, 0.93 for usable subset.**
