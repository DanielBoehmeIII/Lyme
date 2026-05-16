# Dataset Card: Lyme Model Dataset v0.1

**Version**: 0.1
**Created**: 2026-05-16T07:35:33.469432+00:00
**Description**: First local coding dataset for Lyme Model training
**License**: Research Use Only
**Format Version**: 0.1

## Dataset Statistics

- Total examples: 35
- Train: 27
- Validation: 3
- Test: 5

### By Task Type
- qa: 8
- explain_failure: 5
- locate_bug: 4
- plan_patch: 4
- apply_patch: 4
- refuse: 4
- verify_patch: 3
- recover: 3

### By Difficulty
- medium: 20
- easy: 12
- hard: 3

### By Source
- synthetic: 32
- lyme_audit: 3

## Known Limitations
- Small dataset size — not sufficient for full model training
- Synthetic examples use fictional repos — may not generalize to real codebases
- No multi-file change examples — all patches touch single files
- No real-world user data — all examples are curated or generated
- Refusal examples are limited — 4 unsupported claim scenarios
- Lyme Audit traces are hand-crafted — only 3 reference traces available
- Difficulty labels are heuristic — not validated against model performance
- No cross-repo transfer examples — each example is repo-isolated

## Data Collection

- **Synthetic repos**: Generated from templates with intentional bugs
- **Lyme Audit traces**: Converted from real agent runs
- **Manual curation**: Verified correct/incorrect labels

## Sanitization

All examples pass through the Lyme Sanitizer which redacts:
- API keys, secrets, tokens
- Email addresses, usernames in paths
- Private repo identifiers
- Credential URLs