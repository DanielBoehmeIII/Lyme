# Limitations — Honest Assessment

Lyme measures itself. Here is what we know we do not do well yet.

## Current Grade: D (0.64/1.0)

This is measured by `lyme v1-audit` — fully automated and honest.

## What Lyme Does NOT Do

| Area | Status | Why |
|------|--------|-----|
| **Auto-fix complex bugs** | Partial | Safe edits applied, but deep logic bugs need human review |
| **Semantic code understanding** | Basic | Knows structure, not meaning |
| **Multi-repo analysis** | Experimental | Cross-repo features exist but unproven |
| **IDE integration** | Stub | IDE bridge exists but not production-ready |
| **CI/CD integration** | Stub | CI commands exist but not integrated |
| **Windows native** | Weak | WSL works, native Windows untested |
| **ML model inference** | Experimental | Local model support needs Ollama |
| **Real-time monitoring** | Not built | Observatory is research-grade, not product-grade |

## When NOT to Use Lyme

- You need guaranteed-zero-risk code changes (Lyme edits are safe but not perfect)
- You are working on a repo with 0 tests (heal verification needs tests to confirm fixes)
- You need production support with SLAs (this is open-source beta)

## What We Are Fixing Next

1. **Reliability** — more tests, fewer crashes (target: 95% smoke pass rate)
2. **Onboarding** — first-run wizard, guided workflows
3. **Heal workflow** — mature fix → verify → rollback loop
4. **Documentation** — more examples, better troubleshooting

## Transparency

Lyme never sends your code to external servers. All analysis is local.
Telemetry is opt-in and product-only by default.
