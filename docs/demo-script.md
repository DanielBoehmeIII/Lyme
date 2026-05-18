# Lyme Demo Script (60 seconds)

## Setup

```bash
# Terminal with a real codebase ready
cd ~/projects/your-repo
```

## Demo Flow (60 seconds)

### :00-:10 — Install & Setup

```bash
# Already installed? Show version
lyme --version

# First time? One command
curl -fsSL https://lyme.ai/install.sh | bash
```

### :10-:25 — Repo Diagnostics

```bash
# Show repo understanding
lyme doctor

# Point out: language, framework, test count, risks detected
# "Lyme understood this repo in under a second"
```

### :25-:40 — Evidence-Grounded Q&A

```bash
# Ask about the codebase
lyme ask "What framework does this project use?"
lyme ask "Are there security-related files?"

# Point out: citations, confidence scores, evidence
# "Every answer comes with file citations"
```

### :40-:50 — Daily Developer Workflow

```bash
# Show the dashboard
lyme dashboard

# Show daily startup
lyme start

# Point out: git status, tests, model server, dogfood score
```

### :50-:60 — Dogfood & Metrics

```bash
# Run the dogfood
lyme dogfood score

# Point out: productivity ratio, daily usefulness score
# "Lyme eats its own dog food — it tests itself against real repos"
```

## Key Talking Points

1. "Lyme is the first tool that measures how coding agents *think*, not just what they *produce*"
2. "Every claim is evidence-grounded with file citations and confidence scores"
3. "Your code never leaves your machine — local-first by default"
4. "It's open source (MIT) and extensible via plugins"
5. "The dogfood system means Lyme gets better by using itself"
