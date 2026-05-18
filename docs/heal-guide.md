# Lyme Heal — The Killer Workflow

`lyme heal` is the flagship command. It turns repo diagnosis + repair into
a single command you can run every day.

## How It Works

```
lyme heal
  │
  ├── 1. Diagnose ── RepoDoctor scans structure, risks, suggestions
  ├── 2. Prioritize ── Issues sorted by severity (critical → low)
  ├── 3. Plan ── Each issue gets a clear fix action
  ├── 4. Fix (--fix) ── SafeEditProtocol applies patches
  ├── 5. Verify ── Checks if fixes improved the score
  └── 6. Report ── Beautiful terminal output with before/after
```

## Usage

```bash
# Quick scan (read-only)
lyme heal

# Apply fixes
lyme heal --fix

# Preview with JSON output
lyme heal --dry-run --json

# Save report
lyme heal --output heal-report.md
```

## Understanding the Report

```
==========================================================
  LYME HEAL REPORT
==========================================================
  Audit Score: 0.64 → 0.64  (Δ +0.00)
  Issues: 0 found, 0 fixed

  Recommendations:
    • Run 'lyme doctor' for a deeper diagnosis
    • Run 'lyme heal --fix' to auto-apply safe fixes
==========================================================
```

## Score Improvement

Heal reports before/after audit scores. Each successful fix improves
your v1 readiness score.

Track progress:
```bash
lyme v1-fix status    # Quick progress check
lyme v1-fix report    # Full repair report
```
