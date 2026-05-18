# Changelog

## v1.0.0-rc1 (2026-05-17)

### Added
- `lyme heal` — flagship workflow: diagnose + prioritize + fix + verify + report
- `lyme v1-audit` — honest self-measurement with evidence-based scoring (Grade: D)
- `lyme v1-fix` — repair engine: auto-generates tasks, before/after scoring, feature gate
- `lyme gate` — v1 reliability gate: 95% smoke pass, zero crashes, heal succeeds
- `lyme doctor --install` — install diagnostics
- `lyme beta funnel` — activation funnel tracking (install → first value → repeat)
- `lyme beta retention` — retention report with user segmentation
- Installation diagnostics and fallback modes
- Cross-platform CI workflow (Ubuntu, macOS, Windows)
- Honest limitations documentation

### Changed
- CLI help simplified to show core commands by default
- Beginner mode includes heal, v1-audit, v1-fix, gate as essential
- Install script with Python version fallback and diagnostics
- Documentation rewritten around user outcomes
- Benchmark claims now require evidence bundles

### Removed (hidden behind --experimental)
- society, evolution, research (experimental flags)
- civ-map, epistemology, govern, constitution
- similar, compress, fabric, cross-repo
- learn, predict, intent, tradeoff, decisions
- maintain, detect, roadmap

### Fixed
- CLI startup time profiled and optimized
- Error boundaries added to heal workflow
- Rollback support for fix operations
- Safer edit handling with SafeEditProtocol

### Known Issues
- Overall readiness: D (0.64/1.0) — see `lyme v1-audit`
- Windows native support needs WSL
- Auto-fix is limited to safe, low-risk edits
