# Lyme — One-Command Repo Repair

**Your repository has problems. Lyme finds them, prioritizes them, and fixes them.**

```bash
pip install lyme
cd your-project
lyme heal        # Diagnose + prioritize + fix + verify
lyme doctor      # Deep repo health check
lyme v1-audit    # Honest readiness score
```

---

## What Does Lyme Do?

Lyme is a CLI tool that scans your repository, finds real issues, and either
fixes them automatically or tells you exactly what to do.

**It answers three questions:**
- What is wrong with my repo?
- What should I fix first?
- Did the fix actually work?

---

## Why Should I Care?

Most repos accumulate silent rot:
- Dead code, missing tests, skewed dependencies
- Architectural drift nobody tracks
- Config that works by accident

Lyme catches this before it bites you. One command, under 10 seconds.

---

## Install

```bash
# Install directly
pip install lyme

# Or from source
git clone https://github.com/anomalyco/lyme
cd lyme && pip install -e .

# Verify
lyme doctor --install
```

**Requirements:** Python 3.10+ | git (recommended)

---

## First Command

```bash
cd your-project
lyme heal
```

This runs the full workflow:
1. **Diagnose** — scan for issues (missing tests, high-risk files, config drift)
2. **Prioritize** — order by real impact, not guesswork
3. **Plan** — show exactly what needs to happen
4. **Fix** — `lyme heal --fix` applies safe patches
5. **Verify** — confirms fixes improved the score

---

## What Does Success Look Like?

**Before:**
```
lyme v1-audit
  Overall: 0.64  Grade: D
  ! reliability  ████████████████░░░░
  ✗ retention    ██████░░░░░░░░░░░░░░
```

**After running recommended fixes:**
```
lyme v1-fix report
  Score: D → C  (+0.11)
  Tasks: 5/8 completed
  ✓ reliability improved
```

Lyme is honest about what it can and cannot do. It starts with a D grade
and works up from there — no fake confidence, no empty promises.

---

## Key Commands

| Command | What it does |
|---------|-------------|
| `lyme heal` | Full diagnose → prioritize → fix → verify |
| `lyme doctor` | Detailed repo health diagnosis |
| `lyme v1-audit` | Honest readiness score (A-F) |
| `lyme v1-fix` | Track and apply repairs |
| `lyme fix --dry-run` | Safe edit preview |
| `lyme start` | Daily dev workflow |

---

## Documentation

- [Quickstart](docs/QUICKSTART.md) — get started in 2 minutes
- [Heal Guide](docs/heal-guide.md) — deep dive on the killer workflow
- [Troubleshooting](docs/TROUBLESHOOTING.md) — common issues
- [Limitations](docs/LIMITATIONS.md) — honest about what we don't do

---

## Project Status

**v0.9.0** — Beta. Core workflow works. Some experimental commands exist.

Lyme measures itself: `lyme v1-audit` reports an honest readiness score.
Currently scoring **D (0.64/1.0)**. Target: B+ for v1.0.
