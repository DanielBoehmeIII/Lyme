# Lyme v0.6 — Scientific Governance of Autonomous Software Change

**Theme**: Scientific governance of autonomous software change.
**Version**: 0.6.0
**Status**: Planning

## Overview

v0.6 transforms Lyme from an autonomous agent into a **governed autonomous system**. Every change is verified, governed, evaluated, and recorded. Lyme becomes not only powerful, but governable.

## Components

### 1. Verification Graph (41.1)

Connects claims → code changes → tests → runtime traces → static analysis → type checks → user approvals → benchmark results → rollback evidence.

| Aspect | Detail |
|--------|--------|
| User Value | Knows exactly what was verified and what wasn't for every action |
| Research Value | Provides a formal model of verification coverage |
| Governance Value | Creates auditable evidence chains for every change |
| Maturity | Beta — core graph works, CLI renderer, audit integration |
| Demo Path | `lyme verify graph --context '{...}'` |

### 2. Verification Strategy Planner (41.2)

Given a proposed edit, chooses unit tests, integration tests, type checks, linters, build commands, runtime smoke tests, and manual review requirements.

| Aspect | Detail |
|--------|--------|
| User Value | Optimal verification strategy for any edit |
| Research Value | Quantifies the cost/confidence tradeoff of verification |
| Governance Value | Ensures appropriate checks for each risk level |
| Maturity | Beta — 3 strategies (fast/standard/thorough), explainable output |
| Demo Path | `lyme verify plan --risk 0.7 --scope broad` |

### 3. Verification Gap Detector (41.3)

Identifies untested affected code, missing assertions, weak coverage, unavailable builds, unverifiable claims, risky assumptions, and false confidence.

| Aspect | Detail |
|--------|--------|
| User Value | Catches verification blind spots before they cause harm |
| Research Value | Formalizes the taxonomy of verification gaps |
| Governance Value | Prevents false confidence from incomplete verification |
| Maturity | Beta — 14 gap labels with severity scoring and recommendations |
| Demo Path | `lyme verify gaps` |

### 4. Change Governance Engine (42.1)

Classifies changes by risk, reversibility, scope, sensitivity, verification coverage, user intent, deployment impact, and architectural impact. Decides auto-apply, patch-only, require review, require approval, or block.

| Aspect | Detail |
|--------|--------|
| User Value | Prevents dangerous autonomous actions |
| Research Value | Policy-driven governance with explainable decisions |
| Governance Value | Core of the governance system |
| Maturity | Beta — 13 default policies, explainable, configurable |
| Demo Path | `lyme govern evaluate --risk 0.9` |

### 5. Repo Constitution (42.2)

Defines allowed agent actions, forbidden zones, approval requirements, architectural rules, testing requirements, model restrictions, privacy constraints, and deployment protections.

| Aspect | Detail |
|--------|--------|
| User Value | Repo-specific governance boundaries |
| Research Value | Machine-readable governance as code |
| Governance Value | The constitution is the source of truth for agent permissions |
| Maturity | Beta — schema, validator, CLI editor, policy engine integration |
| Demo Path | `lyme constitution init && lyme constitution check --file src/auth.py` |

### 6. Autonomous Change Ledger (42.3)

Records every agent action, intent, evidence, risk score, verification result, human approvals, rollback path, outcome, and learned memory.

| Aspect | Detail |
|--------|--------|
| User Value | Complete audit trail of all autonomous changes |
| Research Value | Data for studying autonomous software evolution |
| Governance Value | Immutable governance record |
| Maturity | Beta — 7 entry types, summary statistics, persistent storage |
| Demo Path | `lyme ledger record && lyme ledger summary` |

### 7. Self-Benchmark (43.1)

Evaluates Lyme across 9 dimensions: task success, verification quality, hallucination resistance, memory usefulness, autonomy safety, repair quality, context efficiency, runtime efficiency, and user intervention rate.

| Aspect | Detail |
|--------|--------|
| User Value | Quantified confidence in Lyme's capabilities |
| Research Value | Rigorous self-evaluation framework |
| Governance Value | Objective capability measurement |
| Maturity | Alpha — runs on demo repos and real repos |
| Demo Path | `lyme eval benchmark` |

### 8. Longitudinal Evaluation (43.2)

Tracks Lyme over time: does it improve? does memory help or corrupt? does autonomy become safer? do workflows get shorter? do repairs become more reliable? do users intervene less?

| Aspect | Detail |
|--------|--------|
| User Value | Visibility into Lyme's trajectory |
| Research Value | Longitudinal study of autonomous agent improvement |
| Governance Value | Detects degradation before it becomes critical |
| Maturity | Alpha — trend detection, regression identification |
| Demo Path | `lyme eval longitudinal` |

### 9. Cognition Regression Detection (43.3)

Detects when new Lyme changes make agents worse at planning, evidence grounding, tool use, memory retrieval, verification, safe editing, uncertainty communication, and cross-repo transfer.

| Aspect | Detail |
|--------|--------|
| User Value | CI for intelligence — catch regressions early |
| Research Value | Systematic tracking of cognitive capability |
| Governance Value | Prevents capability degradation in production |
| Maturity | Alpha — 8 cognitive dimensions, baseline comparison |
| Demo Path | `lyme eval cognition` |

## Architecture

```
User Request
    │
    ├── Repo Constitution — check permissions
    ├── Change Governance — classify and decide
    ├── Verification Graph — build evidence
    ├── Verification Planner — choose checks
    ├── Verification Gap Detector — find gaps
    ├── Change Ledger — record everything
    ├── Self-Benchmark — measure impact
    ├── Longitudinal — track trends
    └── Cognition CI — detect regressions
```

## Migration from v0.5

- All v0.5 features continue to work
- New `lyme verify`, `lyme govern`, `lyme constitution`, `lyme ledger`, `lyme eval` commands
- `.lyme/constitution.json` for repo governance
- `.lyme/ledger.json` for change history

## Limitations

- Self-benchmark dimensions use simulated data — real evaluation requires integration with actual agent runs
- Cognition regression detection requires established baselines for meaningful alerts
- Repo constitution enforcement depends on integration with the agent tool-use pipeline
- Verification planner commands are descriptive — actual test execution requires external tooling
- No GUI for constitution editor — CLI-only

## Future Work

- Constitution enforcement hooks in pre-tool-use guard
- Real benchmark integration with agent traces
- Governance-driven autonomy level adjustment
- Web dashboard for ledger and evaluation reports
- Multi-repo constitution federation
