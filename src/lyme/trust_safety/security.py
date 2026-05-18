"""Security model documentation for Lyme."""


SECURITY_MODEL = """
# Lyme Security Model

## Overview

Lyme is designed for **local-first, zero-trust** operation. The security model
assumes that the host machine is trusted (it's your machine) and that no data
should leave it without explicit user action.

## Threat Model

### In Scope

1. **Accidental data leakage**: User runs Lyme on a repo with sensitive data
   → Mitigation: All data stays local. No network calls.
2. **Malicious model output**: Model generates harmful code
   → Mitigation: Lyme's patch verification and rollback system
3. **Supply chain attack**: Compromised dependency
   → Mitigation: Minimal dependencies. MIT license. Auditable.
4. **Insider threat**: User exports sensitive data
   → Mitigation: Not in scope (user controls their machine)

### Out of Scope

1. **Physical access to machine**: If attacker has physical access, all bets are off
2. **Compromised Python environment**: If pip/Python is compromised, Lyme can't help
3. **Malicious user**: We trust the user running Lyme

## Security Controls

| Control | Implementation |
|---------|---------------|
| No network calls | Core has zero network dependencies |
| Local inference | Uses Ollama/llama.cpp locally |
| Audit trail | Immutable, hash-chained audit log |
| Patch verification | Validates patches before applying |
| Rollback | Git-based rollback for all changes |
| Input sanitization | Redacts secrets from traces |
| Privacy boundary | Explicit consent levels for data |

## Safe Defaults

1. **No telemetry**: Disabled by default
2. **Dry-run mode**: `lyme fix --dry-run` shows what would happen
3. **Read-only by default**: `lyme doctor`, `lyme ask` are read-only
4. **Explicit confirmation**: All destructive actions require confirmation
5. **Git integration**: All changes are tracked via git

## Enterprise Security

For enterprise deployments:

1. **Airgapped mode**: Block all external network access
2. **Audit log**: Hash-chained, immutable audit trail
3. **Compliance exports**: SOC2 and GDPR-ready reports
4. **On-premise**: No cloud dependency
5. **License enforcement**: Plan-based feature gates
"""


class SecurityModel:
    def print_model(self):
        print(SECURITY_MODEL.strip())

    def print_safe_defaults(self):
        safe_defaults = """
# Lyme Safe Defaults

1. **Local-only**: No data leaves your machine
2. **No telemetry**: Telemetry is opt-in, not opt-out
3. **Dry-run**: Preview changes before applying
4. **Read-only commands**: doctor, ask, dashboard are read-only
5. **Git-backed**: All changes tracked by git
6. **Explicit confirmation**: Destructive actions require approval
7. **Minimal dependencies**: Small attack surface
8. **Open source**: MIT license, auditable
"""
        print(safe_defaults.strip())


security = SecurityModel()
