# Lyme Model v1.3 — Teacher-Distilled Local Coding Behavior

> Generated: 2026-05-16T23:06:38.705134+00:00

## Theme
Distilled agentic behavior from stronger teacher models.

## Components
| Component | Description |
|-----------|-------------|
| Distillation Dataset | 240 examples of good search, minimal patches, cautious editing, repair after failure |
| Patch Style | 120 examples of minimal vs overbroad patches |
| Debugging Strategy | 90 examples of structured debugging |
| Teacher Matrix | 32 teacher×task comparisons |

## Gap vs Claude/OpenCode
- **+**: Structured output discipline, minimal patches, appropriate stop behavior
- **-**: Model capacity (0.5B vs 100B+ Claude), complex reasoning, long-horizon planning
- **Measured imitation**: Similar tool sequence patterns to teacher models
