# Lyme v0.7 — Standardization, Integration, and Public Research Infrastructure

**Theme**: Making agent behavior portable, inspectable, and comparable across systems.

---

## Overview

v0.7 transforms Lyme from a research project into shared infrastructure for the field.
It defines open standards for agent traces, semantic diffs, and cognition benchmarks;
integrates with GitHub, CI/CD, and IDEs; and establishes public research infrastructure
for the coding agent community.

---

## 48.1 — Open Agent Trace Standard (OATS)

- **User value**: Inspect any coding agent's behavior in a portable format. Compare agents side-by-side. Replay failures across systems.
- **Ecosystem value**: Interoperability between agents, benchmarks, and observability tools. All major agent frameworks can export/import OATS.
- **Research value**: Large-scale trace analysis, failure pattern mining, cross-agent comparison studies.
- **Maturity**: Stable schema v0.7.0. Validation suite. Example traces. Converter from Lyme traces.
- **Demo path**: `lyme trace export --format oat` → `oat-validator validate` → `oat-compare trace-a.json trace-b.json`

## 48.2 — Semantic Diff Standard (SDS)

- **User value**: Understand not just what changed but why and how risky. Machine-readable semantic analysis of every PR.
- **Ecosystem value**: Standard format for CI systems, code review tools, and governance policies to evaluate changes.
- **Research value**: Study how agents change code. Correlate diff characteristics with bug rates. Train models on semantic diffs.
- **Maturity**: Stable schema v0.7.0. Markdown/HTML/JSON renderers. CLI export.
- **Demo path**: `lyme diff --semantic` → `sd-renderer --format html` → view risk assessment

## 48.3 — Software Cognition Benchmark Spec

- **User value**: Know which agent is best for which cognitive task. Compare across 8 dimensions of software cognition.
- **Ecosystem value**: Standard benchmark for the coding agent field. All major models publish scores.
- **Research value**: Measure cognitive capabilities beyond code generation. Track progress over time.
- **Maturity**: Spec v0.7.0 with 16 tasks across 8 dimensions. Scoring rubric. Anti-gaming rules. Baseline expectations.
- **Demo path**: `lyme benchmark run --spec cognition-benchmark-spec.json` → `lyme benchmark leaderboard`

## 48.4 — GitHub PR Intelligence

- **User value**: Automated PR analysis that understands semantic impact, invariant violations, architectural drift, and risk zones.
- **Ecosystem value**: Standard PR analysis that any CI system or review tool can use.
- **Research value**: Large-scale PR analysis — study how agents and humans write PRs differently.
- **Maturity**: Stable analyzer with GitHub API client. Mock mode for testing. Markdown report export.
- **Demo path**: `lyme pr analyze <repo> <pr-number>` → view report → `lyme pr comment <repo> <pr-number>`

## 48.5 — CI/CD Integration

- **User value**: Every PR or commit gets cognition-aware governance. Block risky changes before they land.
- **Ecosystem value**: Reference CI integration that any platform can adopt. Standard CI artifact format.
- **Research value**: Study real governance decisions. Correlate policy strictness with defect rates.
- **Maturity**: 3 modes (advisory, blocking, research_telemetry). Governance policy engine. Artifact export.
- **Demo path**: `lyme ci run --mode blocking` → publishes audit artifact → CI fails if risk > threshold

## 48.6 — IDE Bridge

- **User value**: Evidence-grounded answers, semantic diff previews, architecture warnings, confidence indicators — in your editor.
- **Ecosystem value**: Thin protocol that any editor can implement (LSP-compatible). Reference implementation.
- **Research value**: Study developer-agent interaction patterns. Measure trust calibration.
- **Maturity**: Bridge protocol defined. 7 insight types. LSP-compatible output. No editor-specific code.
- **Demo path**: `lyme bridge query "What does this function do?"` → `lyme bridge preview-diff` → LSP response

## 48.7 — Public Research Corpus

- **User value**: Anonymized, citable research data. Contribute traces while protecting secrets.
- **Ecosystem value**: The corpus grows as the community uses Lyme. Common resource for the field.
- **Research value**: Large-N studies of agent behavior. Reproducible research. Meta-analysis across studies.
- **Maturity**: Privacy redaction pipeline. Citation format (BibTeX). Opt-in enforcement. JSONL export.
- **Demo path**: `lyme corpus add --trace trace.json` → `lyme corpus export --format citations`

## 48.8 — Research Portal

- **User value**: See how your agent ranks. Read research reports. Understand failure patterns.
- **Ecosystem value**: Central hub for the coding agent research community.
- **Research value**: Publication venue for empirical studies. Leaderboard drives improvement.
- **Maturity**: Leaderboard with 8-dimension scoring. Failure taxonomy. Research reports. Ablation results. Open questions.
- **Demo path**: `lyme portal generate` → open `index.html` → browse leaderboard and reports

## 48.9 — Contribution Protocol

- **User value**: Clear path to contribute benchmarks, adapters, policies, visualizations.
- **Ecosystem value**: The project grows through community contributions. Every contribution has quality guarantees.
- **Research value**: Community contributions increase coverage. Diverse benchmarks reduce overfitting.
- **Maturity**: 11 contribution types. Requirements checklists. Review workflow. Guides and templates.
- **Demo path**: `lyme contrib new --type benchmark_task` → `lyme contrib submit` → `lyme contrib review`

---

## Maturity Summary

| Component | Schema | Validator | Tests | Docs | CLI | Demo |
|-----------|--------|-----------|-------|------|-----|------|
| Agent Trace Standard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Semantic Diff Standard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Cognition Benchmark Spec | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| GitHub PR Intelligence | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| CI/CD Integration | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| IDE Bridge | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Research Corpus | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Research Portal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Contribution Protocol | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

---

## Dependencies

- Python 3.10+
- `pyyaml` (existing dependency)
- No new external dependencies for core standards
- GitHub integration requires `GITHUB_TOKEN` environment variable (optional)
- All components work fully in mock/offline mode

## Upgrade Path from v0.6

Existing users:
- `lyme trace` → enhanced to export OATS format
- `lyme diff` → enhanced to export semantic diff format
- `lyme benchmark` → enhanced to use cognition benchmark spec
- All new features are additive — no breaking changes to existing data formats

New users get the complete v0.7 experience.
