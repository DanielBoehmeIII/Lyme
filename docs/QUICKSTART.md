# Quickstart — 2 Minutes

## 1. Install

```bash
pip install lyme
```

Or from source:
```bash
git clone https://github.com/anomalyco/lyme
cd lyme
pip install -e .
```

## 2. Run Your First Heal

```bash
cd your-project
lyme heal
```

This scans your repo and shows issues found. No changes made yet.

## 3. Deep Diagnosis

```bash
lyme doctor
```

Full health report with structure analysis, risk assessment, and suggestions.

## 4. Check Your v1 Readiness

```bash
lyme v1-audit
```

Honest A-F score. Most repos start at D or C. That is normal.

## 5. Apply Fixes

```bash
lyme heal --fix
```

Automatically applies safe fixes and verifies the result.

## What's Next

- `lyme v1-fix diagnose` — get a repair plan with tasks
- `lyme v1-fix status` — track repair progress
- `lyme fix --dry-run` — preview edits before applying
- `lyme start` — daily dev workflow launcher
