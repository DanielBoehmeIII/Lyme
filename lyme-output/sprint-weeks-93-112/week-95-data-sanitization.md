# Week 95 — Data Sanitization for Training

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/learning/sanitizer.py`
**Tests:** `tests/test_week95_sanitizer.py` (32 tests, all passing)

**Training-data sanitization pipeline** that removes or redacts sensitive information while preserving technical structure, tool sequences, patch logic, verification outcomes, and failure labels.

---

## 2. Redaction Patterns

| Pattern | What It Catches | Examples |
|---------|----------------|----------|
| `api_key` | API keys, secrets, tokens, passwords | `sk-proj-...`, `ghp_...`, `AKIA...`, JWT tokens |
| `email` | Email addresses | `user@example.com` |
| `username_path` | Home directory paths | `/home/alice/`, `/Users/bob/`, `C:\Users\carol\` |
| `credential_url` | URLs with embedded credentials | `https://user:pass@host.com` |
| `ip_address` | IP addresses | `192.168.1.1` |
| `private_repo` | Private repo identifiers | Git SSH URLs, "private" keywords |
| `private_path` | Sensitive config paths | `/.ssh/`, `/.aws/`, `/credentials` |
| `private_key` | Private key material | `-----BEGIN RSA PRIVATE KEY-----` |

**False positive protection:**
- Builtin Python keywords excluded from redaction
- Short tokens (< 16 chars for API keys) not flagged
- Email pattern requires full domain format

---

## 3. Pipeline Components

| Component | Purpose |
|-----------|---------|
| `TrainingDataSanitizer` | Recursive dict sanitizer with field-level tracking |
| `PathSanitizer` | Path-specific sanitization with optional mapping |
| `sanitize_example_file()` | File-level sanitization (JSON + JSONL) |
| `write_redaction_log()` | Human-readable redaction report |
| `write_safety_checklist()` | Machine-readable safety checklist |

### What It Preserves
- Technical structure (dict hierarchy, list order)
- Tool sequences (search → read → edit → verify)
- Patch logic (diffs, line counts, file paths with redacted user parts)
- Verification outcomes (pass/fail, test counts, error messages)
- Failure labels (category, attempt number, strategy change)

### What It Removes/Redacts
- API keys, secrets, tokens → `[REDACTED]`
- Email addresses → `[REDACTED]`
- Usernames in paths → `[REDACTED_USER]`
- Private repo identifiers → redacted or rejected
- Private key material → example rejected

---

## 4. Safety Checklist

Generated per-run:
```
[✓] No API keys in training data       (or ✓ if redacted)
[✓] No email addresses                 (or ✓ if redacted)
[✓] No username paths                  (or ✓ if redacted)
[✓] No credential URLs                 (or ✓ if redacted)
[✓] No private repo identifiers        (or ✓ if redacted)
[✓] No private key material
[✓] Technical structure preserved
[✓] All redactions logged
```

---

## 5. Rejected-Example Log

Examples containing unrecoverable content (e.g., embedded private keys) are rejected with a logged reason. The log includes:
- Example identifier
- Rejection reason
- Pattern that triggered rejection

---

## 6. Files Created

| File | Purpose |
|------|---------|
| `src/lyme_model/learning/sanitizer.py` | Full sanitization pipeline |
| `tests/test_week95_sanitizer.py` | 32 tests |

---

## 7. Next Week

Week 96 — Generate the First Local Coding Dataset v0.1: synthetic repos, public toy repos, Lyme Audit traces, manually verified examples.

---

## End of Week 95

**Sanitization pipeline built. 32 tests passing. 8 redaction patterns. Safety checklist generated per run. Rejected-example log maintained. Technical structure preserved.**
