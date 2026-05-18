"""Privacy policy and data handling documentation for Lyme."""


PRIVACY_POLICY = """
# Lyme Privacy Policy

**Last updated: 2026-05-17**

## Our Commitment

Lyme is built on a simple principle: **your code belongs to you**.

Lyme is designed to be local-first. All analysis, tracing, and measurement
happens on your machine. Your code, file paths, and repository data never
leave your machine unless you explicitly choose to share them.

## What We Collect

### By Default (Nothing)

Lyme collects nothing by default. There is no telemetry, no analytics, no
phone-home mechanism in the open-source core.

### Optional Telemetry

If you enable telemetry (via `lyme beta telemetry`), data is stored locally
in `.lyme/telemetry/`. This data never leaves your machine unless you
explicitly export and share it.

### Bug Reports

When you run `lyme beta bug`, a bug report is generated locally. It includes:
- System information (OS, Python version, GPU if available)
- Git branch and recent commit hashes
- Lyme version
- The bug description you provide

You control whether to share this report.

## What We NEVER Collect

- API keys, tokens, or credentials
- File contents (unless explicitly analyzed for a command)
- Git commit messages or author names (anonymized by default in research data)
- Personally identifiable information
- Network requests to third-party services (unless explicitly triggered)

## Data Storage

All Lyme data is stored in:
- `.lyme/` — telemetry, model runs, audit trails, beta data
- `lyme-output/` — benchmark reports, evidence bundles, dogfood results

These directories are local to your repository. Delete them at any time.

## Third-Party Services

Lyme does not connect to any third-party service by default.

Optional integrations (GitHub, remote model APIs) require explicit
configuration and are clearly documented.

## Your Rights

- You can view all data Lyme has stored: `ls .lyme/`
- You can delete all data: `rm -rf .lyme/`
- You can export data: `lyme beta diagnostic`
- You can opt out of all telemetry: Lyme is opt-in by default

## Changes

This policy may be updated as Lyme adds features. Check back periodically.

## Contact

For privacy concerns, open an issue at:
https://github.com/lyme-research/lyme/issues
"""

DATA_HANDLING_DOC = """
# Data Handling Documentation

## Local-Only Guarantee

Lyme guarantees local-only operation by default:

1. **No phone-home**: The open-source core contains zero network calls
2. **No analytics SDK**: No Google Analytics, Sentry, or similar
3. **No user tracking**: No user IDs, device fingerprints, or sessions
4. **No third-party APIs**: All model inference is local (Ollama, llama.cpp)

## Data Flow

```
Your Repository  →  Lyme Analysis  →  Local Storage (.lyme/)
                                        ↓
                              (optional) Export / Share
                                        ↓
                              Your explicit choice
```

## Data Categories

| Data Type | Storage Location | Retention | Sharing |
|-----------|-----------------|-----------|---------|
| Repo analysis | `.lyme/model-runs/` | Until deleted | Never by default |
| Telemetry | `.lyme/telemetry/` | Until deleted | Never by default |
| Bug reports | `.lyme/beta/bug-reports/` | Until deleted | You choose |
| Benchmark reports | `lyme-output/` | Until deleted | You choose |
| Diagnostic bundles | `.lyme/diagnostics/` | Until deleted | You choose |

## Data Deletion

To delete all Lyme data:
```bash
rm -rf .lyme/ lyme-output/
```

## Export

To export Lyme data:
```bash
lyme beta diagnostic
```
"""


class PrivacyPolicy:
    def print_policy(self):
        print(PRIVACY_POLICY.strip())

    def print_data_handling(self):
        print(DATA_HANDLING_DOC.strip())


privacy = PrivacyPolicy()
