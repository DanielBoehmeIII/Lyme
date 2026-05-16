# Lyme v0.1 Release Plan

**Goal**: A credible first release that proves Lyme is both useful and
scientifically different.

**Not perfection.** A research preview that works, demonstrates the dual
architecture, and invites contribution.

---

## Minimum Features (Must Ship)

### Product Layer
| Feature | Status | Notes |
|---------|--------|-------|
| `lyme doctor` | ✅ | Repo diagnosis with structure, risks, hotspots |
| `lyme ask` | ✅ | Evidence-grounded Q&A with citations, confidence |
| `lyme diff` | 🔧 Already in codebase | Integrate with CLI |
| `lyme trace` | ✅ | Trace viewer with timeline |
| `lyme history` | ✅ | Action audit trail |
| `lyme undo` | ✅ | Git-based action reversal |
| `lyme audit` | ✅ | Full audit reports |
| `lyme bench` | 🔧 Already in codebase | Model comparison |
| `lyme memory` | 🔧 Already in codebase | Memory inspection |
| `lyme fix` (plan only) | ✅ | Safe edit protocol (planning phase) |

### Research Layer
| Feature | Status | Notes |
|---------|--------|-------|
| Cognitive tracing | 🔧 Already in codebase | Decision trees, thought steps |
| Causal graphs | 🔧 Already in codebase | Risk analysis, hidden dependencies |
| Invariant discovery | 🔧 Already in codebase | Architecture rules, violations |
| Temporal modeling | 🔧 Already in codebase | Evolution analysis |
| Scaling laws | 🔧 Already in codebase | Model scaling experiments |
| Agent coordination | 🔧 Already in codebase | Debate, specialization, topology |
| Hallucination detection | 🔧 Already in codebase | Claim verification |
| Context degradation | 🔧 Already in codebase | Stress experiments |

### Shared Infrastructure
| Feature | Status | Notes |
|---------|--------|-------|
| Dual architecture registry | ✅ | Product/research module definitions |
| Telemetry substrate | ✅ | Consent-based telemetry routing |
| Experiment API | ✅ | Hook-based experiment registration |
| Plugin system | ✅ | File-based plugin discovery |
| Privacy boundary | ✅ | Classification, sanitization, audit |
| Storage strategy | ✅ | Versioned, portable, human-inspectable |
| Versioned project schema | ✅ | LymeProject with 12 data collections |
| Failure taxonomy | ✅ | 14 failure categories with retry strategies |

---

## Broken Features to Hide (Known Issues)

These features exist in the codebase but are NOT ready for v0.1:

| Feature | Issue | Plan |
|---------|-------|------|
| `lyme fix` (execution) | Safe edit protocol plans work; actual file editing needs interactive approval | Hide from default help; document as experimental |
| Multi-agent `society` commands | Debate and specialization use random simulation, not real agents | Document as simulation |
| `lyme research scaling --auto` | Uses regression-based simulated data, not real model runs | Document as methodology preview |
| Web UI (`lyme ui dashboard`) | Basic HTML generation, no interactive backend | Document as preview |
| `lyme stress` with real agents | Runs against real repos but agent execution is mocked | Document as infrastructure preview |

**Decision**: Ship these as "research preview" features with clear labeling.
Hide from `--help` unless `--experimental` flag is passed.

---

## Demo Path

The demo should take < 5 minutes and show both product and research value:

```
# 1. Install
pip install lyme

# 2. Diagnose
lyme doctor
# → Shows: language, framework, risks, hotspots, invariants

# 3. Ask
lyme ask "What language is this? What are the risky files?"
# → Shows: evidence citations, confidence scores, what was checked

# 4. Causal graph
lyme graph infer .
# → Shows: hidden dependencies, risk amplification zones

# 5. Invariants
lyme discover invariants .
# → Shows: architecture rules, naming conventions, structure constraints

# 6. History
lyme history
# → Shows: all actions recorded with audit trail
```

### Target Repository Criteria

**Ideal for demo:**
- Python or TypeScript project (best analysis)
- 50-500 source files
- Has tests
- Has git history (50+ commits)
- Has multiple modules/packages
- Open source

**Acceptable for demo:**
- Any language with parsable files
- At least 10 source files
- Has a build file

### Failure Fallback Plan

| Scenario | Fallback |
|----------|----------|
| No git history | Show structure analysis only; note git-dependent features disabled |
| No build file | Show language detection by file extension; skip build commands |
| No tests | Show "no tests found" with suggestion to add test framework |
| Single file repo | Show limited analysis; suggest trying on larger repo |
| Binary-only repo | Suggest source-based repo |
| Permission errors | Show error with fix instructions |

---

## Installation Path

### Primary: pip install
```bash
pip install lyme
```

### Development: from source
```bash
git clone https://github.com/lyme-research/lyme
cd lyme
pip install -e ".[dev]"
```

### Dependencies
- **Required**: Python 3.10+, pyyaml
- **Optional**: git, pytest, ollama, llama.cpp

### Platform Support
| Platform | Status |
|----------|--------|
| Linux (x86_64) | ✅ Primary target |
| macOS (arm64) | ✅ Tested |
| macOS (x86_64) | ⚠ Likely works, not extensively tested |
| Windows (WSL2) | ⚠ Should work, not tested |
| Windows (native) | ❌ Not supported (CLI uses Unix paths) |

---

## Documentation Needed

| Document | Status | Priority |
|----------|--------|----------|
| README.md | ✅ Complete | Critical |
| MANIFESTO.md | ✅ Complete | Critical |
| Installation guide | ✅ In README | High |
| Quickstart | ✅ In README | High |
| CLI reference | 🔧 In cli.py help strings | High |
| Architecture overview | ✅ In architecture module | Medium |
| Privacy model | ✅ In README + boundary.py | Medium |
| Research agenda | ✅ In MANIFESTO + research module | Medium |
| Contribution guide | ✅ In README | Medium |
| API documentation | 🔧 Docstrings in code | Low |
| Tutorial: first analysis | ❌ Not written | Low |

---

## Test Coverage Needed

| Module | Minimum Coverage | Current | Notes |
|--------|-----------------|---------|-------|
| architecture/ | 80% | ❌ Not tested | New files, need tests |
| doctor.py | 80% | ❌ Not tested | New file |
| ask.py | 80% | ❌ Not tested | New file |
| edit.py | 70% | ❌ Not tested | New file |
| failures.py | 80% | ❌ Not tested | New file |
| audit.py | 70% | ❌ Not tested | New file |
| demo.py | 50% | ❌ Not tested | Mostly text/output |
| positioning.py | manual | ❌ | Text only |
| Existing modules* | 60% | ✅ | Built with tests |

*benchmark, cognition, compression, discovery, evolution, experiments,
graph, intent, learning, memory, models, prediction, replay, research,
society, stress, telemetry, tools

---

## Known Limitations (v0.1)

### Analysis Limitations
- **Language support**: Full AST analysis for Python only. Other languages
  use file-extension-based heuristics.
- **Git analysis**: Requires git to be installed. No support for other VCS.
- **Test detection**: Heuristic filename matching. Does not run tests.
- **Large repos**: Repos with >5000 files may have slow analysis.
- **Circular dependency detection**: Simple DFS-based; may miss complex cycles.

### Research Limitations
- **Scaling laws**: v0.1 uses simulated data for scaling law experiments.
  Real model execution requires local model setup.
- **Agent coordination**: Uses simulated agents, not real model calls.
- **Context degradation**: Stress experiments generate synthetic repos;
  results are illustrative, not validated against real agents.
- **Hallucination detection**: Regex-based claim extraction; limited to
  Python code patterns.

### Product Limitations
- **lyme fix**: Planning phase only. No automatic file editing.
- **lyme society**: Simulation only. No real multi-agent execution.
- **Web UI**: Single-file HTML generation. Not a real web application.
- **CLI**: No interactive mode. No tab completion (beyond shell defaults).

---

## Supported Models

### Local Models (via Ollama)
| Model | Size | Evaluated |
|-------|------|-----------|
| CodeLlama 7B | 7B | ✅ |
| CodeLlama 13B | 13B | ⚠ Partial |
| CodeLlama 34B | 34B | ⚠ Partial |
| Qwen 2.5 Coder 7B | 7B | ✅ |
| DeepSeek Coder 6.7B | 6.7B | ⚠ Partial |
| Mistral 7B | 7B | ⚠ Partial |
| Llama 3 8B | 8B | ⚠ Partial |
| Llama 3 70B | 70B | ❌ Not tested (too large for most local setups) |

### API Models
| Model | Backend | Evaluated |
|-------|---------|-----------|
| Claude 3.5 Sonnet | claude-code | ✅ |
| Claude 3 Opus | claude-code | ✅ |
| GPT-4o | OpenAI API | ⚠ Partial |
| GPT-4o-mini | OpenAI API | ⚠ Partial |
| OpenCode | opencode | ✅ |

### Model Adapter Configuration
```yaml
# ~/.lyme/config.yaml
agents:
  - name: codellama-7b
    command: "ollama run codellama:7b"
    agent_type: ollama
    timeout_s: 300
    max_tokens: 8192

  - name: claude-sonnet
    command: "claude"
    agent_type: claude-code
    timeout_s: 300
    max_tokens: 128000
```

---

## Supported Languages

| Language | AST Analysis | Import Detection | Test Detection | Doc Detection |
|----------|-------------|-----------------|----------------|---------------|
| Python | ✅ Full | ✅ | ✅ | ✅ |
| TypeScript | ⚠ Extension | ⚠ Regex | ✅ | ✅ |
| JavaScript | ⚠ Extension | ⚠ Regex | ✅ | ✅ |
| Go | ⚠ Extension | ⚠ Regex | ✅ | ✅ |
| Rust | ⚠ Extension | ⚠ Regex | ✅ | ✅ |
| Java | ⚠ Extension | ⚠ Regex | ✅ | ✅ |
| Ruby | ⚠ Extension | ⚠ Regex | ⚠ | ✅ |
| C/C++ | ⚠ Extension | ❌ | ⚠ | ✅ |
| Other | ❌ | ❌ | ⚠ | ✅ |

**Legend**: ✅ Full, ⚠ Basic/heuristic, ❌ Not supported

---

## Target Users

### Primary (v0.1)
1. **AI/ML researchers** studying coding agent behavior
2. **Developer tool engineers** building agent infrastructure
3. **Open source maintainers** wanting to benchmark agents on their repos
4. **Technical leads** evaluating coding agents for team adoption

### Secondary (v0.2+)
5. **Individual developers** wanting to understand their codebase
6. **DevOps teams** setting up agent observability
7. **Security researchers** studying agent safety
8. **Academic CS labs** researching software engineering AI

### NOT Target (v0.1)
- Non-technical users
- Teams wanting a production coding agent replacement
- Enterprise compliance departments (v0.2+ target)

---

## Launch Checklist

### Pre-Launch (2 weeks before)

- [ ] Run `lyme doctor` on 10+ open-source repos of varying sizes
- [ ] Run `lyme ask` on 20+ questions from real developer workflows
- [ ] Verify all CLI commands work without errors
- [ ] Test on macOS (arm64) and Linux (x86_64)
- [ ] Fix any crash-level bugs
- [ ] Add docstrings to all new modules
- [ ] Run linter on all new code

### Launch Week

- [ ] Publish to PyPI (`pip install lyme`)
- [ ] Publish README and MANIFESTO
- [ ] Create GitHub repository with issues enabled
- [ ] Add CI (GitHub Actions) for tests
- [ ] Publish example output (screenshots of `lyme doctor`, `lyme ask`)
- [ ] Write launch blog post / announcement
- [ ] Set up project communication channel

### Post-Launch (1 month)

- [ ] Triage all initial issues
- [ ] Publish first contribution guide examples
- [ ] Write tutorial: "Analyzing Your First Repo with Lyme"
- [ ] Collect traces from early users (with consent)
- [ ] Publish first research findings
- [ ] Plan v0.2 priorities based on feedback

---

## Success Criteria

The v0.1 release is successful if:

1. **Users can install and run `lyme doctor`** on any Python/TypeScript repo
   and get a useful diagnosis
2. **Users can run `lyme ask`** and get evidence-grounded answers with
   citations and confidence scores
3. **Researchers can see the dual architecture** — product output AND
   research telemetry from every command
4. **No crash-level bugs** on supported platforms
5. **At least 100 GitHub stars** and 3+ community contributions in first month
6. **At least 10 published traces** from early users

---

## v0.1 Release Checklist (Day-Of)

```
[ ] Version bumped to 0.1.0 in pyproject.toml
[ ] CHANGELOG.md created with v0.1 entries
[ ] README.md reviewed for accuracy
[ ] MANIFESTO.md reviewed
[ ] RELEASE_PLAN.md reviewed
[ ] All new modules import cleanly
[ ] `lyme doctor` works on self
[ ] `lyme ask` works on self
[ ] `lyme --version` prints 0.1.0
[ ] `pip install .` succeeds
[ ] `pip install -e ".[dev]"` succeeds
[ ] git tag v0.1.0 created
[ ] PyPI package published
[ ] GitHub release created
```

---

## Appendix: Feature Gates

Features hidden behind `--experimental` flag (not shown in default help):

```
lyme society          # Simulated multi-agent, not ready
lyme stress           # Synthetic repos, illustrative results
lyme research scaling  # Simulated scaling laws
lyme ui               # Basic HTML, no interactive backend
lyme fix              # Planning only, no automatic execution
```

These features are functional but clearly labeled as research previews.
They demonstrate the architecture without making promises about production use.
