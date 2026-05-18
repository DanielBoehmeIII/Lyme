# Lyme v0.9.0 — Launch Candidate

**Release date: 2026-05-17**

## Theme: Product Truth & Distribution

This release transforms Lyme from an impressive architecture into a usable,
sellable, and repeatably valuable tool. It's the first launch candidate.

## New Features

### 🐕 Dogfood Testing (`lyme dogfood`)
- Run Lyme against its own repos (Lyme, NoDiff, Leveli, Abel, cShot)
- Automatic failure reports and improvement plans
- "Would I use this daily?" scoring
- Before/after productivity metrics

### 📊 Metrics Audit (`lyme metrics-audit`)
- Metric provenance tracking
- Fake/simulated metric detection
- Benchmark credibility scoring
- Evidence bundle collection
- Public-safe benchmark reports

### 🚀 Daily Developer Workflow
- `lyme start` — daily startup ritual
- `lyme dashboard` — compact terminal dashboard
- `lyme inbox` — task inbox
- `lyme diff-explain` — explain recent changes
- `lyme branch-review` — PR readiness check
- `lyme continue` — resume previous task
- `lyme fix-latest` — diagnose test failures
- `lyme watch` — scan repo for changes

### 📦 Distribution Surface
- One-command install (`pip install lyme` or `curl ... | bash`)
- 5-minute quickstart guide
- Docs site skeleton
- Demo script
- "Why Lyme?" positioning page
- Comparison page (vs Claude Code, Aider, OpenCode)

### 👥 Beta Program (`lyme beta`)
- Onboarding for first 10 users
- Feedback capture with ratings
- Local-only telemetry
- Bug report generator
- Diagnostic bundle export
- Weekly value report
- Churn/friction tracker

### 💰 Pricing & Licensing (`lyme pricing`)
- Free Local Core (MIT open source)
- Pro Individual ($29/mo)
- Team Plan ($99/mo)
- Enterprise Airgapped ($499/mo)
- License gates for feature access
- Commercial feature boundary documentation

### 🔒 Trust & Safety (`lyme trust`)
- Privacy policy
- Data handling documentation
- Security model
- Local-only guarantee
- Safe defaults
- Enterprise risk checklist
- Audit log export

## Dogfood Results

| Repo | Files | Tests | Language | Failures | Productivity Ratio |
|------|-------|-------|----------|----------|-------------------|
| Lyme | 715 | 71 | Python | 2 | 506x |
| NoDiff | 1465 | 99 | Python | 2 | 1096x |
| Leveli | 1 | 32 | Python | 1 | 44x |
| Abel | 4 | 6 | Python | 2 | 234x |
| cShot | 45 | 2 | Python | 1 | 89x |

**Daily Usefulness Score: 77% — "Daily driver ready"**

## Known Limitations

1. **No human verification yet** — credibility score at 35%
2. **Limited to Python repos** — JS/TS support is partial
3. **GPU-dependent scenarios not tested** — requires NVIDIA GPU
4. **No real model inference in dogfood** — uses static analysis only
5. **Beta is manual** — no self-service signup yet
6. **No payment processing** — pricing is documented but not enforceable
7. **No CI/CD integration** — must be run manually
8. **Limited to single machine** — no distributed operation

## Next Steps

- Get first 10 beta users
- Improve credibility to >70% by adding real execution metrics
- Add payment processing for Pro and Team plans
- Automate beta signup
- Publish benchmark report

## Install

```bash
pip install lyme
```

Or from source:

```bash
git clone https://github.com/lyme-research/lyme
cd lyme
pip install -e ".[dev]"
```
