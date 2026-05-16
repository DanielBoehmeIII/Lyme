# Week 140 — Lyme Model v0.8

**Theme**: Specialist local coding model system

## Components Built

| # | Component | Lines | Status |
|:-:|-----------|:-----:|:------:|
| 133 | Specialization Strategy | 130 | Operational |
| 134 | Specialist Interfaces | 300 | Operational |
| 135 | Planner Specialist | 220 | Operational |
| 136 | Retriever Specialist | 280 | Operational |
| 137 | Patch Generator Specialist | 250 | Operational |
| 138 | Critic Specialist | 380 | Operational |
| 139 | Verifier Specialist | 300 | Operational |
| 140 | v0.8 Release | 250 | Released |

## Hardware Matrix

| Tier | Compatible Specialists |
|------|----------------------|
| Minimal (RPi 5) | retriever, verifier |
| CPU-only (MacBook Air) | retriever, verifier, planner |
| Budget GPU (GTX 1650) | planner, retriever, patch_gen, verifier |
| Standard GPU (RTX 3070) | planner, retriever, patch_gen, critic, verifier |
| High-end (RTX 4090) | all 5 specialists |

## Ablation Study Summary

| Remove | Risk | Redundancy? |
|--------|:----:|:-----------:|
| Planner | HIGH | No — no other specialist decomposes tasks |
| Retriever | HIGH | Partial — raw context always available |
| Patch Generator | MEDIUM | Yes — direct edit possible but risky |
| Critic | MEDIUM | Partial — verifier catches some issues |
| Verifier | HIGH | No — no safety net for incorrect output |

**Conclusion**: Planner, Retriever, Verifier are critical. Patch Generator and Critic have partial redundancy.

## Failure Analysis

| Specialist | Failure Rate | Top Failure Mode |
|------------|:-----------:|------------------|
| Planner | ~5% refusals | Ambiguous task, risk threshold |
| Retriever | ~10% high missing rate | Task too vague, wrong policy |
| Patch Generator | ~10% validation failure | No verification command |
| Critic | ~15% rejection | Missing citations, empty patches |
| Verifier | ~5% failure | Syntax errors, missing files |

## Lyme Audit Status

**Untouched.** Lyme Audit measures all specialist outputs.

## Files Created
- `src/lyme_model/release_v08.py` — v0.8 release module with demo, benchmarks, hardware matrix
- `src/lyme_model/specialists/` — 7 specialist modules (strategy, interfaces, planner, retriever, patch_generator, critic, verifier)
