# Week 78 — Verifier-First Local Agent

**Theme:** Before accepting output, verify. Cheap tools before expensive model calls.
**Question:** Can verification compensate for weak local reasoning?

---

## 1. Six Verifiers (ordered by cost)

| Verifier | Cost | Checks | Stops On Failure |
|----------|------|--------|------------------|
| file_existence | cheap | Referenced files exist in repo | Yes |
| symbol_verifier | cheap | Function/class names exist in codebase | Yes |
| import_verifier | cheap | Import statements would resolve | Yes |
| test_verifier | medium | Test commands and test files exist | Yes |
| claim_verifier | medium | Claims have codebase citations | Yes |
| patch_verifier | medium | Patch format is valid, target syntax OK | Yes |

## 2. Execution Flow

```
Context Input
    │
    ▼
FileExistenceVerifier (cheap) ──fail──→ REJECT
    │pass
    ▼
SymbolVerifier (cheap) ──fail──→ REJECT
    │pass
    ▼
ImportVerifier (cheap) ──fail──→ REJECT
    │pass
    ▼
TestVerifier (medium) ──fail──→ REJECT
    │pass
    ▼
ClaimVerifier (medium) ──fail──→ REJECT
    │pass
    ▼
PatchVerifier (medium) ──fail──→ REJECT
    │pass
    ▼
ACCEPT output
```

## 3. Compensation

When verification fails, the agent attempts compensation:
- Missing file → add file existence check to pre-flight
- Missing symbol → add symbol lookup before generation
- Bad import → add import resolution check
- Invalid patch → reject with format feedback

## 4. Metrics

| Metric | Purpose |
|--------|---------|
| total_verifiers | How many checks ran |
| passed / failed | Pass/fail count |
| all_passed | Gate for output acceptance |
| total_latency_ms | Overhead of verification |
| compensation_applied | What mitigation was used |

## 5. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/verification/__init__.py` | Module exports |
| `src/lyme_model/verification/verifier.py` | 6 verifiers + VerifierFirstAgent |

## 6. Next Week

Week 79 will build the Local Self-Correction Loop — given failed tests or verification errors, the model should summarize, locate, patch, rerun, and stop after bounded attempts.
