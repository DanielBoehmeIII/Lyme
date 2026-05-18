# 5-Minute Quickstart

This guide gets Lyme running on any repository in under 5 minutes.

## Step 1: Install

```bash
pip install lyme
```

Or use the one-liner:

```bash
curl -fsSL https://lyme.ai/install.sh | bash
```

Verify it works:

```bash
lyme --version
```

## Step 2: Diagnose a Repository

```bash
cd /path/to/your/project
lyme doctor
```

This analyzes the repository structure, language, framework, tests, and risks.

## Step 3: Ask Questions

```bash
lyme ask "What language and framework does this project use?"
lyme ask "Are there tests? How do I run them?"
lyme ask "What are the main architectural components?"
```

Lyme answers with evidence — including file citations and confidence scores.

## Step 4: Use the Daily Tools

```bash
# Terminal dashboard — everything at a glance
lyme dashboard

# Daily startup ritual
lyme start

# Explain recent changes
lyme diff-explain

# Review your branch for PR readiness
lyme branch-review
```

## Step 5: Run Dogfood Testing

```bash
# See how Lyme performs on your repos
lyme dogfood run

# Check the daily usefulness score
lyme dogfood score
```

## What's Next?

- Read [Why Lyme?](why-lyme.md) to understand the philosophy
- See the [Comparison](../comparison/overview.md) page
- Run `lyme help` to see all commands
