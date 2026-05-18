"""Enterprise risk checklist for Lyme deployment."""


ENTERPRISE_RISK_CHECKLIST = """
# Enterprise Risk Checklist

## Data Security

- [ ] Is Lyme configured in local-only mode?
- [ ] Is telemetry disabled?
- [ ] Are `.lyme/` and `lyme-output/` in .gitignore?
- [ ] Is the audit trail enabled?
- [ ] Are compliance exports configured?

## Access Control

- [ ] Are team member permissions defined?
- [ ] Is the airgap mode enabled for sensitive environments?
- [ ] Are license gates tested for all tiers?

## Monitoring

- [ ] Is the audit log being monitored?
- [ ] Are bug reports reviewed?
- [ ] Is the churn/friction tracker active?

## Recovery

- [ ] Is git-based rollback available?
- [ ] Are diagnostic bundles being collected?
- [ ] Is there a backup of `.lyme/` data?

## Compliance

- [ ] SOC2 audit log export ready
- [ ] GDPR data deletion procedure documented
- [ ] Privacy policy reviewed and posted
- [ ] Data handling documentation published

## Deployment

- [ ] Airgapped mode tested with no network access
- [ ] All features work in offline mode
- [ ] Install script verified on target OS
- [ ] Version pinned to specific release
"""


class EnterpriseRiskChecklist:
    def print_checklist(self):
        print(ENTERPRISE_RISK_CHECKLIST.strip())

    def check_defaults(self) -> list:
        findings = []
        from pathlib import Path

        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            if ".lyme/" not in content:
                findings.append("WARNING: .lyme/ not in .gitignore — local data could be committed")
            if "lyme-output/" not in content:
                findings.append("WARNING: lyme-output/ not in .gitignore — output could be committed")
        else:
            findings.append("WARNING: No .gitignore found")

        return findings


risk = EnterpriseRiskChecklist()
