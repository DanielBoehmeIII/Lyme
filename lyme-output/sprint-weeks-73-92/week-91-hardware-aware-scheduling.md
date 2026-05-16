# Week 91 — Hardware-Aware Scheduling

**System:** Lyme Audit measures. Lyme Model competes.

---

## 1. What Was Built

**Module:** `src/lyme_model/hardware/scheduler.py`

**8 scheduling decisions per task:**

| Decision | Options | Determined By |
|----------|---------|--------------|
| Model selection | 7 models in catalog | VRAM budget + task difficulty |
| Quantization | Q4, Q8 | VRAM available |
| Compute backend | GPU, CPU, hybrid | GPU presence + VRAM |
| Context size | 2K-16K tokens | VRAM after model load |
| Parallel tools | True/False | GPU backend + task difficulty |
| Fallback mode | True/False | Hardware constraints |
| Unload timeout | 120s / 300s | VRAM pressure |
| Confidence | 0.0-1.0 | Hardware reliability |

## 2. Model Catalog (7 entries)

| Model | Params | Q4 VRAM | Quality | Speed (tok/s) |
|-------|--------|---------|---------|---------------|
| qwen2.5-coder:1.5b | 1.5B | 1.2GB | 0.50 | 40 |
| qwen2.5-coder:3b | 3B | 2.2GB | 0.65 | 25 |
| qwen2.5-coder:7b | 7B | 4.5GB | 0.80 | 15 |
| deepseek-coder:6.7b | 6.7B | 4.2GB | 0.82 | 14 |
| codegemma:7b | 7B | 4.5GB | 0.78 | 16 |
| codellama:7b | 7B | 4.5GB | 0.75 | 15 |
| llama3:8b | 8B | 5.0GB | 0.76 | 14 |

## 3. Task Difficulty Levels

| Level | Min Quality | Example Tasks |
|-------|-------------|--------------|
| EASY | 0.4 | Lint fix, import sort |
| MEDIUM | 0.6 | Single-file edit, test addition |
| HARD | 0.75 | Multi-file edit, refactor |
| COMPLEX | 0.85 | Architecture change, cross-cutting |

## 4. Files

| File | Purpose |
|------|---------|
| `src/lyme_model/hardware/scheduler.py` | HardwareScheduler, SchedulingDecision, HardwareState, TaskRequirements, MODEL_CATALOG |
| `src/lyme_model/hardware/__init__.py` | Updated exports |
| `tests/test_week91_scheduler.py` | 28 tests |

## 5. Tests

**Tests:** `tests/test_week91_scheduler.py`
**Coverage:** 28 tests — SchedulingDecision, HardwareState, model selection, quantization, unload logic, CPU/GPU backends, all difficulty levels, VRAM budgeting
**All passing.**

## 6. Next Week

Week 92 — Second 20-Week Report: comprehensive report of weeks 73-92 with results, architecture changes, and next roadmap.
