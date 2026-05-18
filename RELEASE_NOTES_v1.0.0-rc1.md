# Lyme v1.0.0-rc1 — One-Command Repo Repair

## What's New

Lyme is now a production-grade CLI tool that diagnoses, prioritizes, fixes,
and verifies repository health in a single command.

### Flagship: `lyme heal`

```
lyme heal           # Diagnose + prioritize + plan
lyme heal --fix     # Apply safe patches + verify
```

The heal workflow:
1. Scans your repo for real issues
2. Prioritizes by severity (critical → low)
3. Generates a clear fix plan
4. Applies safe, reversible patches
5. Verifies fixes improved your score
6. Reports before/after metrics

### Honest Scoring: `lyme v1-audit`

```
lyme v1-audit       # Grade: D (0.64/1.0)
```

Lyme measures itself honestly. No fake confidence, no inflated metrics.
Everything is evidence-based and reproducible.

### Repair Engine: `lyme v1-fix`

```
lyme v1-fix diagnose   # Auto-generate repair tasks
lyme v1-fix apply      # Apply fixes
lyme v1-fix status     # Track progress
```

Groups failures by: onboarding, reliability, speed, trust, killer workflow, docs.
Blocks new feature work until score improves.

### Reliability Gate: `lyme gate`

```
lyme gate           # Pass/fail release check
```

Enforces:
- 95% CLI smoke pass rate
- Zero critical crashes in core workflows
- `lyme heal` succeeds on target repo
- Benchmark claims have evidence

## Install

```bash
pip install lyme
# or from source
pip install -e .
```

## Metrics

| Metric | Value |
|--------|-------|
| CLI commands | 70+ (15 core) |
| Smoke tests | 70 passing |
| Test files | 49 |
| Test functions | 1091 |
| Install time | < 30s |
| Heal runtime | < 10s |

## Limitations

- Auto-fix applies safe patches only (high-risk files skipped)
- Windows native requires WSL
- ML model inference needs Ollama
- Readiness: D (we're working on it)

## Project

- Source: https://github.com/anomalyco/lyme
- Issues: https://github.com/anomalyco/lyme/issues
