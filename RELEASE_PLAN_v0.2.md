# Lyme v0.2 Release Plan

**Goal**: A serious research prototype that normal technical users can actually run.
Lyme transitions from a project to a platform for autonomous software science.

---

## v0.2 Feature Overview

| Feature | User Value | Research Value | Maturity | Limitations | Demo Path |
|---------|-----------|---------------|----------|-------------|-----------|
| **Repo Self-Description** (`lyme self`) | Living README for repo understanding | Self-modeling repository theory | Alpha | Confidence depends on git history; limited to source analysis | `lyme self` → markdown report |
| **Machine-Readable Architecture** (`lyme archfile`) | Package.json for architecture | Architecture evolution tracking | Alpha | Subsystem inference is heuristic; manual tuning improves accuracy | `lyme archfile generate && lyme archfile view` |
| **Architecture-Aware Planning** (`lyme plan`) | Smarter agent task decomposition | Planning benchmark for agent comparison | Alpha | Requires archfile; without it falls back to baseline planner | `lyme plan "add feature"` → structured plan |
| **Experiment Generator** (`lyme research experiment`) | Auto-generate experiment designs | Standardized experiment methodology | Beta | Templates cover 5 domains; custom questions use default template | `lyme research experiment "Does memory improve?"` |
| **Automated Ablation** (`lyme research ablation`) | Understand which components matter | Component importance ranking | Alpha | Uses simulated metrics unless task_runner provided; results are estimates | `lyme research ablation` → ranking report |
| **Research Report Generator** (`lyme research report`) | Auto-generated research papers | Honest, hype-free reporting | Alpha | Statistical analysis uses approximations; real data improves quality | `lyme research report --title "..."` |
| **Skill Library** (`lyme skill list/search/extract`) | Reusable automation patterns | Skill acquisition theory | Alpha | Skills are manually extracted; automated extraction needs real runs | `lyme skill list` |
| **Cross-Repo Skill Transfer** (`lyme skill transfer`) | Apply lessons across projects | Transfer learning for agents | Pre-alpha | Risk estimation is heuristic; real validation needed | `lyme skill transfer ../other-repo` |
| **Skill Critic** (`lyme skill critique`) | Safety check before applying skills | Applicability theory | Alpha | Assumption extraction is template-based; real reasoning would improve | `lyme skill critique <id>` |

---

## New CLI Commands (v0.2)

```
lyme self                     Repository self-description
  --repo PATH                 Path to repository
  --update                    Force regeneration
  --format {markdown,json}    Output format

lyme archfile generate        Generate machine-readable architecture file
lyme archfile validate        Validate architecture file
lyme archfile violations      Detect architecture violations
lyme archfile view            View architecture as markdown
lyme archfile mermaid         Render as Mermaid diagram

lyme plan TASK                Architecture-aware planning
  --baseline                  Use baseline planner for comparison

lyme skill list               List all skills in library
lyme skill search QUERY       Search skills
lyme skill extract RUN_ID     Extract skill from run
lyme skill transfer REPO      Transfer skills to another repo
lyme skill critique SKILL_ID  Critique a skill for applicability

lyme research experiment Q    Generate experiment plan from question
lyme research ablation        Run automated ablation study
lyme research report          Generate research report

New modules:
  lyme/self_modeling/         Repository self-description system
  lyme/archfile/              Machine-readable architecture file system
  lyme/planning/              Architecture-aware agent planning
  lyme/skills/                Skill library, transfer, and critic
  lyme/research/              Enhanced: experiment generator, ablation, report
```

## v0.2 Architecture Changes

```
┌─────────────────────────────────────────────────────────────────┐
│                      LYME v0.2 ARCHITECTURE                      │
├──────────────────────┬──────────────────────────────────────────┤
│    PRODUCT LAYER     │           RESEARCH LAYER                  │
│                      │                                            │
│  lyme self           │  Self-modeling repository theory           │
│  lyme archfile       │  Architecture evolution tracking           │
│  lyme plan           │  Planning benchmark                        │
│  lyme skill          │  Skill acquisition / transfer / critique   │
│  (existing commands) │  (existing research modules)               │
├──────────────────────┴──────────────────────────────────────────┤
│                      SHARED SUBSTRATE                             │
│  SelfDescription schema         ArchitectureFile schema          │
│  Skill library (JSON)           Planner framework                │
│  Evidence links                 Confidence scoring               │
└─────────────────────────────────────────────────────────────────┘
```

## Known Limitations (v0.2)

### Self-Modeling
- Identity detection relies on pyproject.toml / package.json; may miss other project types
- Invariant discovery requires InvariantInferenceEngine (may not import)
- Drift detection is time-based, not content-based

### Architecture File
- Subsystem discovery only looks at `src/` directory structure
- Dependency inference from imports is heuristic
- No automatic enforcement of boundary rules (detection only)

### Planning
- Keyword-based subsystem matching is simplistic
- Context selection assumes source files in `src/`
- Requires archfile for full benefit

### Experiment Generator
- Templates cover only 5 research domains
- Generated plans need human review before execution

### Ablation
- Metrics are simulated unless task_runner is provided
- Effect size computation assumes normal distributions

### Skills
- Library is ephemeral (JSON file storage)
- Automated skill extraction needs real agent runs
- Transfer risk estimation is heuristic

### Cross-Repo Transfer
- Only tested on Python repositories
- Adaptation is minimal (path rewriting)
- No learning from transfer failures yet

## Launch Checklist

### Documentation
- [x] README.md updated with v0.2 commands
- [x] RELEASE_PLAN.md created for v0.2
- [x] CLI help strings for all new commands

### CLI Polish
- [x] All new commands have help text
- [x] Consistent argument naming (--repo, --output, --format)
- [x] Error messages for missing files/directories
- [x] Graceful fallbacks when modules unavailable

### Testing
- [ ] All new modules import cleanly
- [ ] `lyme self` generates valid output
- [ ] `lyme archfile generate` produces valid JSON
- [ ] `lyme plan` creates structured plan
- [ ] `lyme skill list` shows skills
- [ ] `lyme research experiment` generates plan

### Reliability
- [x] All commands handle missing git history
- [x] All commands handle non-existent files
- [x] All commands handle import errors gracefully
- [x] Default parameters prevent crashes

## Success Criteria

1. A user can run `lyme self` on any repo and get a useful self-description
2. A user can run `lyme archfile generate && lyme archfile view` and see architecture
3. A user can run `lyme plan "fix bug"` and get an architecture-aware plan
4. A user can run `lyme skill list` and see the skill library
5. A user can run `lyme research experiment "question"` and get an experiment plan
6. All commands have clear help text and error messages
7. No unhandled exceptions on supported platforms

## Version

**v0.2.0** — Research Platform
- Schema version: 0.1.0 (backward compatible)
- Storage format: JSON (unchanged)
- Python: 3.10+
