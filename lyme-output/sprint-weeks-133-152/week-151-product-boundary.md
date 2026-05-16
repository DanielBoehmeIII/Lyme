# Week 151 — Local Coding Agent Product Boundary

**Theme**: What Lyme Model should and should not do as a product.

## Allowed Strong Claims (Evidence-Supported)

| Claim | Evidence | Limitation |
|-------|----------|------------|
| Evidence-grounded repo Q&A | 94% parity, 25 benchmark tasks | Structural Q&A only, no design evaluation |
| Safe patch planning | Plan-then-patch prevents wrong-file edits | Plan quality depends on task clarity |
| Bounded small fixes | Max 50 lines, requires verification + rollback | Multi-file changes need human review |
| Test failure explanation | 92% accuracy | Requires test output as input |
| Semantic diff explanation | AST-based classification | Subtle semantic changes may be misclassified |

## Claims Requiring Proof (Not Yet Ready)

| Claim | Status | Gap |
|-------|--------|-----|
| Autonomous coding | Not proven | Context drift at >4 subtasks |
| Claude/Codex parity | Not proven | 7B vs 70B+, specialized not general |
| Long-horizon feature building | Not proven | Max safe: 3 files, 4 subtasks |
| Self-improvement | Not proven | No automated audit→training pipeline |
| Cross-repo generality | Not proven | Optimized for Python/TS |

## Out of Scope

- Replace human code review
- Architectural design decisions
- Security vulnerability detection
- Production-ready code without human verification
- Sensitive data handling
- Timeline estimates or project management

## Claim Policy

> Lyme Model claims must be evidence-grounded, bounded, hardware-aware, and honest. Every claim must cite the specific week, benchmark, or experiment that supports it. Claims without supporting evidence are explicitly labeled as 'requiring proof'.

## Demo Script

1. **Repo Q&A**: "What framework does this project use?"
2. **Patch Planning**: Plan a fix with affected files
3. **Specialist Pipeline**: Run orchestrator on a small fix
4. **Verification**: Cheapest verification that catches the bug
5. **Tradeoff**: Compare fast vs careful vs specialist mode
6. **Boundary**: Explicitly state what Lyme Model cannot do
