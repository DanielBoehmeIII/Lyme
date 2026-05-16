# Week 51 — Product and Open-Source Strategy

## Prompt 51.1 — Decide What Lyme Actually Is

### Options Analysis

#### Option 1: Local Coding Agent

**What was built:** Lyme has a tool router, memory system, compression pipeline, governance layer, safe edit protocol, and CLI commands structured like agent interactions. But Lyme is explicitly not an agent — it has no language model integration, no agent loop, no prompt management, no conversation handling.

**Verdict:** This is what Lyme is NOT. The codebase and documentation are consistent on this point. Forcing Lyme into this identity would require building an entirely new product on top of the existing infrastructure. Recommend: **abandon this positioning entirely.**

#### Option 2: Agent Observability Platform

**What was built:** Cognitive tracing (15 thought types, decision points, confidence scoring), trace recording and replay, thought analysis (confidence volatility, exploration rates, error loops), anomaly detection, telemetry substrate with spans and events, trace viewer (timeline, thought, branch views), OATS standard for portable traces.

**What is missing:** No connection to real agents to observe. No distributed tracing across agent sessions. No real-time monitoring. No alerting. No dashboards (static HTML only).

**Verdict:** The observability infrastructure is robust but unused. This is the most defensible positioning if and only if Lyme connects to real agents. As a standalone claim, it is infrastructure without instrumentation. Recommend: **strong secondary positioning**, contingent on agent integration.

#### Option 3: Software Cognition Research System

**What was built:** Intelligence dimensions framework (10 dimensions), experiment generator, ablation study framework, scaling law experiment framework, research report generator, research corpus management, 8 benchmark scenarios, cognition benchmark spec (8 dimensions × 16 tasks), research portal (static JSON).

**What is missing:** No research executed using these facilities. All output is simulated. No papers. No datasets. No validated findings.

**Verdict:** The research scaffolding exists but produced nothing. This positioning is aspirational. It becomes legitimate only after experiments are run. Recommend: **long-term identity** after Year Two experiments.

#### Option 4: Autonomous Maintenance Tool

**What was built:** `lyme maintain` command, `lyme detect` for maintenance opportunities, `lyme roadmap` for technical roadmap generation, saf edit protocol, undo/audit system.

**What is missing:** The maintenance loop operates on heuristic detection and simulated execution. No autonomous maintenance has been performed on a real repository. Governance system is a precondition for safe autonomy but has not been tested in autonomous mode.

**Verdict:** The most practical near-term product identity. A developer tool that runs locally, diagnoses repositories, generates roadmaps, and applies safe fixes with governance oversight. This is the closest match to what actually works in the codebase. Recommend: **primary near-term identity**.

#### Option 5: Benchmark Standard

**What was built:** 8 benchmark scenarios, ScenarioRegistry, ScenarioResult (25-field structured output), cognition benchmark spec, OATS and SDS standards, benchmark leaderboard format, reproducible trace-based evaluation.

**What is missing:** No real benchmark runs. The standard has no adoption. The cognition benchmark is aspirational.

**Verdict:** The standards are well-designed but need adoption. This is a community outcome, not a product identity. Recommend: **important component of other identities**, not standalone positioning.

#### Option 6: Governance Layer

**What was built:** Change governance engine (5 decision levels), 13 default policies, repo constitution format, immutable change ledger, sensitive code detection (13 categories), 5-critic review board, verification graph (43 evidence types, 14 gap labels), verification strategy planner (fast/standard/thorough).

**What is missing:** No integration with any agent framework. No testing in production-like conditions. Review board critics are simulated.

**Verdict:** The most novel and differentiated component. No other open-source project provides governance-as-code for coding agents. This could be Lyme's wedge — the component that provides immediate value while the research platform matures. Recommend: **primary differentiator and integration hook**.

#### Option 7: All of the Above

**What was built:** Fragments of each identity.
**What is missing:** A coherent story. 30+ CLI commands, 66+ modules, and mixed messaging.

**Verdict:** Trying to be everything makes Lyme nothing. The diffuse identity confuses potential users and dilutes development effort. Recommend: **reject this option forcefully.**

---

### Final Recommendation

**Primary identity: Autonomous Maintenance Tool with Governance Layer**

- Lyme should present itself as a tool that helps developers maintain their codebases autonomously
- The governance layer is Lyme's moat — no other tool provides machine-readable safety policies for agent actions
- The observability and research layers are internal infrastructure that enables continuous improvement
- The standards are community contributions that support the ecosystem

**What to emphasize:**
- `lyme doctor` (repo diagnosis — works today)
- `lyme ask` (evidence-grounded Q&A — works today)
- `lyme fix` (safe, governed edits — works today)
- Governance policies and constitutions (differentiator — works today)
- Verification graph (novel approach to agent safety — works today)
- Safe autonomy via graduated decision levels (compelling narrative)

**What to hide/demote:**
- "Research platform" language (lacks evidence)
- Simulated benchmark results (misleading)
- Software civilization maps (overbuilt, irrelevant)
- Multi-agent society simulation (simulated, not real)
- Self-improving agents (aspirational, not functional)
- Repository genome (clever metaphor, unclear value)

**What to rename:**
- "Lyme: Research Infrastructure for Coding Agent Science" → "Lyme: Local-First Repository Maintenance and Governance"
- "Dual Architecture" → "Built-in Observability" (more accessible)
- "Compression Pipeline" → "Smart Context" (for product layer)
- "Cognitive Tracing" → "Activity Log" (for product layer)
- "Causal Graph" → "Dependency Map" (for product layer)

**What to abandon:**
- Software civilization maps
- Autonomous maintenance loop (until governance is validated)
- Self-improving agents (workflow/prompt evolution experiments)
- Ecosystem risk forecasting
- Architecture advisor

---

## Prompt 51.2 — Open-Source Launch Strategy

### Target Audience

**Primary:**
- Solo developers and small teams who want safe, local agent-assisted codebase maintenance
- Developers who are privacy-conscious about their code
- Developer tool enthusiasts who contribute to open-source infrastructure

**Secondary:**
- Research groups studying agent safety and governance
- Engineering teams evaluating agent governance policies
- Platform engineering teams building internal developer platforms

**Tertiary:**
- AI safety researchers interested in machine-readable governance
- Academic CS groups studying software engineering with AI

### Repo Structure

```
lyme/
├── README.md              # One-page: what, why, quickstart
├── MANIFESTO.md           # Vision document (toned down from current)
├── GOVERNANCE.md          # Governance framework documentation
├── CONTRIBUTING.md        # How to contribute
├── ROADMAP.md             # Public roadmap
├── LICENSE                # MIT
├── pyproject.toml         # Build config, dependencies
├── src/
│   ├── lyme/
│   │   ├── cli.py         # CLI entry (pruned to 12 core commands)
│   │   ├── doctor.py      # Repo diagnosis
│   │   ├── ask.py         # Evidence-grounded Q&A
│   │   ├── edit.py        # Safe edit protocol
│   │   ├── audit.py       # Action audit
│   │   ├── failures.py    # Failure taxonomy
│   │   ├── governance/    # Governance engine
│   │   ├── compression/   # Compression pipeline
│   │   ├── memory/        # Memory store
│   │   ├── cognition/     # Cognitive tracing
│   │   ├── graph/         # Causal graph
│   │   ├── discovery/     # Invariant discovery
│   │   ├── benchmark/     # Benchmark engine
│   │   └── standards/     # Open standards
│   └── ...
├── tests/
├── examples/
│   ├── quickstart.md      # Walkthrough
│   ├── governance-demo.md # Policy configuration demo
│   └── ci-integration.md  # CI setup guide
├── docs/
│   ├── getting-started.md
│   ├── commands.md
│   ├── governance.md
│   ├── compression.md
│   └── contributing.md
└── .lyme/                 # Example project state
```

### README Framing (One-Page)

```markdown
# Lyme

**Safe, local, governed codebase maintenance for the age of AI.**

Lyme is a developer tool that helps you maintain your codebase. It diagnoses
problems, answers questions about your code, and applies fixes — all with
an explicit governance layer that ensures safety.

## Why Lyme?

AI coding agents are powerful but reckless. They make changes you didn't
ask for, touch files they shouldn't, and leave no audit trail. Lyme inverts
this: it provides a governance layer that constrains agent actions, and a
set of practical tools that work without a model at all.

## Quickstart

```bash
pip install lyme
cd your-project
lyme doctor          # Diagnose repository health
lyme ask "What is the testing strategy?"  # Evidence-grounded Q&A
```

## Governance

Lyme's governance system lets you define machine-readable policies for
what agents can and cannot do:

```bash
lyme constitution init --name my-project
lyme govern evaluate --scope module --risk 0.7
```

See [GOVERNANCE.md](GOVERNANCE.md) for details.

## Commands

| Command | What it does |
|---------|--------------|
| `lyme doctor` | Diagnose repository health |
| `lyme ask` | Answer questions with evidence citations |
| `lyme diff` | Classify what a diff actually means |
| `lyme fix` | Apply a safe, auditable edit |
| `lyme history` | See what happened |
| `lyme audit` | Full action inspection |
| `lyme undo` | Reverse a previous action |
| `lyme memory` | Persistent project memory |
| `lyme graph` | Hidden dependencies and risk zones |
| `lyme discover` | Architecture rules and violations |
| `lyme govern` | Evaluate and enforce governance policies |
| `lyme verify` | Check verification completeness |

## License

MIT
```

### Demo Video Script (60 seconds)

```
[0:00-0:05] OPEN: Terminal window. Title card: "Lyme: Codebase Maintenance with Governance"

[0:05-0:15] "You have a codebase. You want to understand it, maintain it, 
             and fix issues — safely. Meet Lyme."

[0:15-0:25] Type: lyme doctor
             Output shows: language, framework, file count, risks, suggestions
             "One command diagnoses your entire repository. Structure, risks, 
             what to fix first — all from static analysis."

[0:25-0:35] Type: lyme ask "How is authentication handled?"
             Output shows: answer with file citations, confidence score
             "Ask questions and get answers grounded in your actual code, 
             with citations you can verify."

[0:35-0:45] Type: lyme govern evaluate --scope module --risk 0.5
             Output shows: decision level, policy match, rationale
             "Want to let an AI edit your code? Define your policies first. 
             Lyme's governance engine evaluates every proposed change 
             against your repository constitution."

[0:45-0:55] Type: lyme fix (shows safe edit preview with rollback)
             "Safe, auditable, reversible edits. Every action is traced, 
             every outcome is measured."

[0:55-1:00] CLOSE: "Lyme. Local-first codebase maintenance with governance. 
             Install it today."
             URL overlay: github.com/lyme-research/lyme
```

### Examples Directory

- `examples/quickstart.md`: Walk through `lyme doctor`, `lyme ask`, `lyme diff` on a sample repo
- `examples/governance-demo.md`: Initialize a constitution, define policies, evaluate actions
- `examples/ci-integration.md`: Run `lyme ci` in GitHub Actions
- `examples/standards-demo.md`: Generate and validate OATS traces and semantic diffs

### Documentation Path

1. **README** (one page) — Install, run, understand
2. **Getting Started Guide** — 10-minute walkthrough
3. **Commands Reference** — All CLI commands with examples
4. **Governance Guide** — Policies, constitutions, verification
5. **Compression Guide** — How codebase understanding works
6. **Contributing Guide** — How to contribute scenarios, adapters, policies

### Contribution Strategy

**Phase 1 (solo):** Core maintainer handles all merges. Focus on quality, consistency, testing.

**Phase 2 (community):** After 100+ GitHub stars and 10+ issues, add:
- CONTRIBUTING.md with clear guidelines
- Issue labels for good first issues
- PR template
- Code review checklist

**Phase 3 (governance):** After community contributors, establish:
- Maintainer team (2-3 people)
- RFC process for significant changes
- Governance policies for the Lyme repo itself

### Issue Labels

```
bug / enhancement / documentation / question
good-first-issue / help-wanted
governance / compression / memory / tracing / benchmarks
standards / integrations / ci / ide
research / experiment / paper
priority: critical / high / medium / low
needs-reproduction / needs-design / needs-discussion
```

### Roadmap (Public)

```
## v0.8 — Governance Beta
- [ ] Connects to Ollama models for real agent execution
- [ ] Governance evaluation with real agent actions
- [ ] CI integration (GitHub Action)
- [ ] 5 verified success stories

## v0.9 — Measurement Platform
- [ ] Real benchmark results (8 scenarios, 3 models)
- [ ] Community-contributed scenarios
- [ ] IDE extension (VSCode)
- [ ] Published open standards

## v1.0 — Production
- [ ] Verified governance effectiveness
- [ ] Longitudinal agent improvement data
- [ ] Enterprise governance features
- [ ] Published research paper
```

### Launch Channels

| Channel | Action | Timing |
|---|---|---|
| Hacker News | Launch post with technical deep-dive | Day 0 |
| /r/MachineLearning | Research-focused post about governance | Day 0 |
| Twitter/X | Demo video + thread | Day 0 |
| lobste.rs | Technical discussion | Day 0 |
| GitHub | Launch with good README + examples | Day 0 |
| dev.to | "How we built a governance layer for AI agents" | Day +3 |
| YouTube | Demo video (60s) + deep-dive (10min) | Day +7 |
| PyCoder's Weekly | Submission | Day +7 |
| Open-source podcasts | Pitch for interviews | Day +14 |

### Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| "Another CLI tool" dismissal | High | Differentiate via governance — the only tool with machine-readable policies |
| No real agent integration | High | Honest communication: "pre-agent" phase, governance works with any agent |
| Perceived as vaporware due to simulated data | Medium | Remove simulated results from public output. Show what actually works. |
| Too many commands | Medium | Prune to 12 core. Move advanced to `--advanced` or separate scripts. |
| Low discoverability | Medium | Clear README, demo video, examples directory |
| Governance is overkill for solo devs | Medium | Default policies are minimal. "Just works" for individuals, powerful for teams. |

---

## Prompt 51.3 — Productization Strategy

### Option 1: Local CLI

**Customer:** Solo developers, small teams, open-source maintainers.

**Value:** Free, local, privacy-preserving codebase maintenance and governance.

**Difficulty:** Low. Already built. Needs CLI pruning (30 → 12 commands) and documentation.

**Defensibility:** Low. Readily forkable. Moats are governance format adoption and community scenarios.

**Revenue Possibility:** Zero (MIT license, local-only).

**Ethical Risks:** None. Code never leaves user's machine.

**Technical Prerequisites:** None.

**Decision:** Ship as the free/open-source entry point. This is table stakes.

### Option 2: Enterprise Observability

**Customer:** Engineering teams managing multiple agent subscriptions. Platform engineering teams evaluating agent safety.

**Value:** Centralized governance policy management, cross-repository audit trails, agent behavior dashboards, compliance reporting.

**Difficulty:** High. Requires: server component, database, multi-tenant architecture, user authentication, team management, dashboard UI (not static HTML).

**Defensibility:** High. Governance data + policy library + integration depth create switching costs.

**Revenue Possibility:** Medium-High. SaaS for agent observability is an emerging category. Pricing: per-seat or per-repository.

**Ethical Risks:** Privacy. Enterprise deployment could expose sensitive code patterns in aggregated dashboards. Need clear data isolation guarantees.

**Technical Prerequisites:**
- Server component (Python/FastAPI or Rust)
- Database (PostgreSQL)
- Multi-tenant architecture with privacy isolation
- Web dashboard (React/Next.js)
- SSO/SAML integration
- Agent framework integrations (LangChain, CrewAI, Claude Code)

**Decision:** Defer to Year Two. Requires community validation first.

### Option 3: GitHub App

**Customer:** Open-source maintainers, CI-dependent teams.

**Value:** PR governance, automatic invariant checks, governance policy enforcement in CI.

**Difficulty:** Medium. Requires GitHub App webhook handling, PR comment integration, check run API.

**Defensibility:** Medium. Dependent on GitHub platform. Would need to support GitLab/Bitbucket for full defensibility.

**Revenue Possibility:** Low-Medium. Freemium with paid private repo support.

**Ethical Risks:** Code access. GitHub App has broad permissions. Need transparent data handling.

**Technical Prerequisites:**
- GitHub App endpoint
- OAuth flow
- Check run API integration
- PR comment formatting

**Decision:** Build after v0.8. Natural extension of CI integration.

### Option 4: CI Governance Layer

**Customer:** Teams that want AI-generated code to pass governance checks before merge.

**Value:** Automated policy evaluation in CI pipeline. Block PRs that violate governance policies. Generate compliance reports.

**Difficulty:** Medium. Needs: CI plugin (GitHub Action, GitLab CI template, Jenkins plugin), policy evaluation endpoint, report generation.

**Defensibility:** Medium. Policy format lock-in creates migration cost. But governance is a new category, so switching costs are unproven.

**Revenue Possibility:** Medium. Freemium for public repos, paid for private/enterprise.

**Ethical Risks:** False positives block legitimate work. Need transparent override mechanism.

**Technical Prerequisites:**
- GitHub Action (Ansible role or Docker container)
- GitLab CI template
- Policy packaging format
- Integration test suite

**Decision:** Build for v0.8. This is the most actionable productization path.

### Option 5: Research Platform

**Customer:** Academic CS groups, industry research labs, AI safety organizations.

**Value:** Reproducible benchmark execution, standardized trace formats, cross-model comparison infrastructure, research dataset management.

**Difficulty:** High. Requires: real agent integration, experiment management, dataset hosting, reproducibility guarantees.

**Defensibility:** High if standards achieve adoption. Low otherwise.

**Revenue Possibility:** Low. Research grants, not product revenue.

**Ethical Risks:** Low.

**Technical Prerequisites:**
- All of Option 1
- Dataset hosting infrastructure
- Experiment replication service
- Paper authoring templates

**Decision:** Revert to original project vision after governance product succeeds.

### Option 6: IDE Extension

**Customer:** Individual developers who want in-editor governance and diagnostics.

**Value:** Inline diagnostics from lyme doctor, governance policy feedback during editing, one-click governed fixes.

**Difficulty:** Medium. LSP-compatible protocol already defined. Needs VSCode extension packaging + JetBrains plugin.

**Defensibility:** Low. Extensions are cheap to build and easy to switch.

**Revenue Possibility:** Zero as standalone. Value is as distribution channel for enterprise observability.

**Ethical Risks:** Low.

**Technical Prerequisites:**
- LSP server implementation
- VSCode extension TypeScript
- Extension marketplace listing

**Decision:** Build as distribution channel after CLI is stable. Not a standalone product.

### Option 7: Benchmark Service

**Customer:** Model providers, agent framework developers, enterprise procurement teams evaluating agents.

**Value:** Standardized, reproducible agent evaluation across models and configurations. Published leaderboards.

**Difficulty:** Very High. Requires: managed compute for running models, benchmark scenario maintenance, anti-gaming measures, continuous integration with model providers.

**Defensibility:** High if leaderboards achieve authority. Network effects: more participants → more valuable leaderboard.

**Revenue Possibility:** Medium. Benchmark-as-a-service for model providers. Paid certifications.

**Ethical Risks:** Benchmark gaming. Model providers optimizing for the benchmark rather than real performance.

**Technical Prerequisites:**
- All of Option 5
- Managed compute infrastructure
- Anti-gaming protocols
- Leaderboard hosting
- Certification program

**Decision:** Do not pursue in Year Two. Too early, too competitive, misaligned with current strengths.

---

### Productization Decision Matrix

| Option | Difficulty | Defensibility | Revenue | Ethics | Timeline |
|---|---|---|---|---|---|
| Local CLI | Low | Low | None | Clean | Now |
| CI Governance | Medium | Medium | Medium | Clean | v0.8 |
| GitHub App | Medium | Medium | Low-Med | Needs care | v0.9 |
| IDE Extension | Medium | Low | None | Clean | v0.9 |
| Enterprise Observability | High | High | Med-High | Needs care | Year Two |
| Research Platform | High | High (conditional) | Low | Clean | Year Two+ |
| Benchmark Service | Very High | High (conditional) | Medium | Gaming risk | Do not pursue |

### Recommended Productization Path

**Phase 1 (Now): Local CLI.** Ship the free open-source tool. 12 core commands. Great documentation. Prune the rest.

**Phase 2 (v0.8): CI Governance Layer.** GitHub Action + GitLab CI template. This is the wedge — governance in the development workflow. Monetize via freemium (free for public repos, paid governance features for private repos).

**Phase 3 (v0.9): IDE Extension + GitHub App.** Distribution channels for governance. The IDE extension surfaces governance feedback in-editor. The GitHub App brings governance to PRs.

**Phase 4 (Year Two): Enterprise Observability.** The platform play. Only pursue if Phase 2+3 show traction.
