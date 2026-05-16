# Lyme v0.3 — Agent Instructions

## Test Commands

```bash
cd /home/dboehmeiii/Desktop/repos/Lyme
python3 -m pytest tests/ -v
```

## Key Architecture

Lyme is a research platform for coding agent evaluation with:

- **src/lyme/cross_repo/** — Cross-repository intelligence
- **src/lyme/ecosystem/** — Ecosystem knowledge graph (Python/FastAPI)
- **src/lyme/epistemology/** — Evidence theory, epistemic debugging, confidence calibration
- **src/lyme/governance/** — Autonomy policy, sensitive code detection, action review board

## CLI Commands (v0.3)

| Command | Purpose |
|---------|---------|
| `lyme cross-repo --dirs repo1 repo2` | Cross-repo pattern mining |
| `lyme ecosystem query --library fastapi` | Ecosystem knowledge query |
| `lyme epistemology assess --claim "..."` | Evidence-grounded claim assessment |
| `lyme epistemology calibrate` | Confidence calibration report |
| `lyme epistemology debug` | Epistemic debugging |
| `lyme policy check --action modify_files --context '{}'` | Autonomy policy evaluation |
| `lyme policy sensitive --path /repo` | Sensitive code detection |
| `lyme policy review --request '{}'` | Action review board |
| `lyme demo-v03` | Full v0.3 demo |

## Module Conventions

- Dataclasses with `to_dict()` for serialization
- JSON file storage under `.lyme/` and `lyme-output/`
- `__init__.py` exports only public API
- Tests in `tests/` directory with pytest
