# Lyme v0.3 Release Plan

## Core Theme
**Cross-Repository Intelligence + Epistemic Reliability + Safe Autonomy**

Lyme v0.3 is not just a smarter coding agent. It is an agent that:
- Knows what it knows (epistemic reliability)
- Learns across repositories (cross-repo intelligence)
- Governs itself (safe autonomy)

---

## Feature Breakdown

### 1. Cross-Repo Pattern Mining
- **User Value**: Discover patterns, anti-patterns, and conventions across any set of repositories
- **Research Value**: Enables transfer learning studies and ecosystem-level analysis
- **Implementation Maturity**: Core engine complete with fingerprinting, extraction, clustering, scoring
- **Demo Path**: `lyme cross-repo mine --dirs repo_a repo_b repo_c`
- **Known Limitations**: Requires multiple repositories for meaningful patterns; simulated scoring for zero-evidence patterns

### 2. Ecosystem Knowledge Graph
- **User Value**: Understand how frameworks, libraries, and tools relate; get migration paths and compatibility warnings
- **Research Value**: Models ecosystem-level dependencies and security zones
- **Implementation Maturity**: Python/FastAPI ecosystem deeply modeled; graph queryable
- **Demo Path**: `lyme ecosystem query --library fastapi --find risks`
- **Known Limitations**: Currently covers Python/FastAPI only; manually curated knowledge base

### 3. Transfer Benchmarks
- **User Value**: Measure whether skills actually transfer between projects
- **Research Value**: Quantifies overgeneralization and false transfer rates
- **Implementation Maturity**: Benchmark suite with 8 test cases, calibration metrics
- **Demo Path**: `lyme benchmark transfer --suite default`

### 4. Evidence Theory
- **User Value**: Every claim Lyme makes is accompanied by evidence sources, confidence scores, and uncertainty
- **Research Value**: Formal epistemology applied to code agents; testable claim assessment
- **Implementation Maturity**: Claim/evidence engine with aggregation, contradiction detection, hallucination risk
- **Demo Path**: `lyme epistemology assess --claim "this is a Python project"`

### 5. Epistemic Debugging
- **User Value**: When Lyme is wrong, it tells you WHY its knowledge process failed
- **Research Value**: Debug the agent's cognition, not just its outputs
- **Implementation Maturity**: Failure recording, pattern detection, debug report generation
- **Demo Path**: `lyme epistemology debug --trace <trace-id>`

### 6. Confidence Calibration
- **User Value**: Lyme's confidence scores are calibrated against actual accuracy
- **Research Value**: Overconfidence detection, calibration curves, domain-specific calibration
- **Implementation Maturity**: Calibration engine with ECE/MCE metrics, trend tracking
- **Demo Path**: `lyme epistemology calibrate`

### 7. Autonomy Policy Engine
- **User Value**: Control what Lyme can do automatically based on risk, confidence, and context
- **Research Value**: Structured autonomy governance for agent systems
- **Implementation Maturity**: 12 policy rules, risk computation, explainability, override mechanism
- **Demo Path**: `lyme policy check --action modify_files --context '{"test_coverage": 0.4, "edit_size": 30}'`

### 8. Sensitive Code Detection
- **User Value**: Lyme identifies and handles authentication, payments, secrets, crypto, deployment code with care
- **Research Value**: Sensitive zone classification for reduced autonomy zones
- **Implementation Maturity**: 13 pattern categories, detection engine, risk scoring
- **Demo Path**: `lyme policy sensitive --path /path/to/repo`

### 9. Action Review Board
- **User Value**: Before risky edits, Lyme reviews its own plan through computational critics
- **Research Value**: Internal governance mechanism for autonomous systems
- **Implementation Maturity**: 5-critic board (proposer, security, architecture, test, rollback)
- **Demo Path**: `lyme policy review --request '{"title": "Update auth module"}'`

---

## Demo Path (End-to-End)

```
lyme cross-repo mine --dirs ./repos/*                # 1. Analyze repos
lyme ecosystem query --library fastapi --find risks   # 2. Check ecosystem knowledge
lyme benchmark transfer --suite default              # 3. Measure transfer quality
lyme epistemology assess --claim "..."               # 4. Verify evidence
lyme epistemology calibrate                          # 5. Calibrate confidence
lyme policy sensitive --path ./target-repo           # 6. Detect sensitive code
lyme policy check --action modify_files ...          # 7. Route through policy
lyme policy review --request '{"title": "..."}'      # 8. Review board
```

---

## Release Criteria

### Must Have
- [x] All modules install without errors
- [x] CLI commands register and respond
- [x] Reproducible demo flow
- [x] Privacy warnings on cross-repo features
- [ ] Safe defaults for autonomy levels
- [ ] Readable report output (markdown)
- [ ] Confidence explanations in all assessments

### Should Have
- [x] Regression tests for core modules
- [x] Clean install via pip
- [ ] Stable CLI with consistent argument patterns
- [ ] Failure honesty (claims degraded gracefully)

### Known Fragilities (Hidden from public docs)
- Cross-repo clustering uses hierarchical average-linkage; may not scale to 1000+ repos
- Ecosystem knowledge graph is manually curated for Python/FastAPI only
- Evidence theory scores are computed analytically, not learned from data
- Action Review Board critics are rule-based, not learned

---

## v0.3 Release Notes

### What's New
- Cross-repository intelligence: pattern mining, ecosystem graph, transfer benchmarks
- Epistemic reliability: evidence theory, epistemic debugging, confidence calibration
- Safe autonomy: autonomy policy, sensitive code detection, action review board
- 9 new modules, 15+ new CLI commands

### Breaking Changes
- `lyme skill transfer` command signature updated
- Policy configuration format changed
- Telemetry event types extended

### Known Issues
- See Known Fragilities above
