# Week 59 — Tool Use as Model Amplification

**Date:** Week 59 of Year Two
**Action:** Design and benchmark tool-use strategy for Lyme Model.

---

## 1. Tool Architecture

### Tool Registry (`src/lyme_model/tools/registry.py`)

10 tools organized by category, two optimization levels:

| Category | Tool | Model 7B | Model 3B |
|----------|------|:--------:|:--------:|
| READ | `read_file` | ✅ | ✅ |
| READ | `list_directory` | ✅ | ❌ |
| SEARCH | `grep_search` | ✅ | ✅ |
| EDIT | `edit_file` | ✅ | ✅ |
| TEST | `run_test` | ✅ | ✅ |
| ANALYSIS | `inspect_ast` | ✅ | ❌ |
| ANALYSIS | `git_log` | ✅ | ❌ |
| VERIFY | `verify_change` | ✅ | ❌ |
| META | `think` | ✅ | ✅ |
| META | `ask_for_help` | ✅ | ✅ |

### Core Components

| Module | File | Purpose |
|--------|------|---------|
| Registry | `registry.py` | Tool definitions, success tracking, prompt generation |
| Dispatch | `dispatch.py` | Tool execution handlers, result processing |
| Fallback | `fallback.py` | Error recovery, fallback chains |
| Optimizer | `dispatch.py` | `ToolUseOptimizer` — task-specific tool subset selection |

---

## 2. Experimental Results

### Conditions Tested
1. **Model-only reasoning** — full codebase in prompt, no tool descriptions
2. **Naive tool access** — all 10 tool descriptions in prompt
3. **Lyme-controlled tool access** — minimal tool set (3-4 tools) in prompt

### Results

| Task | Model Only | Naive Tools | Lyme Tools |
|------|:----------:|:-----------:|:----------:|
| Find bug (security issues) | **33.3%** | 0.0% | 0.0% |
| Trace flow (call chains) | **100.0%** | 25.0% | 50.0% |
| DB schema analysis | **71.4%** | 28.6% | 28.6% |
| **Average** | **68.2%** | **17.9%** | **26.2%** |

### Critical Finding

**Model-only performed best on every single task.**

Adding tool descriptions to the prompt HURT performance:
- Naive tools: -50.3 pp vs model-only
- Lyme tools: -42.0 pp vs model-only

---

## 3. Why Tools Hurt Single-Turn Performance

### Reason 1: Context budget theft
Tool descriptions consume tokens (200-400 tok for all tools) that could contain
code or instructions. For a 7B model with limited reasoning, every token matters.

### Reason 2: No actual tool execution
The model cannot actually call tools in a single-turn prompt. Tool descriptions
are just text that the model must process but cannot act on. This is pure overhead.

### Reason 3: Role confusion
Tool descriptions suggest an interactive workflow ("you can use tools to...")
but the model is in a single-turn answer mode. The mismatch degrades quality.

### Reason 4: Small models are easily distracted
deepseek-coder:6.7b's attention is scattered by tool descriptions. It spends
cognitive budget parsing tool schemas instead of analyzing code.

---

## 4. What This Means for Lyme Model

### Tools Only Help in Multi-Turn Loops

The tool system is **necessary infrastructure** but provides **no benefit in
single-turn prompting**. It only helps when:

1. The model can **actually call** tools and get results back
2. Tool calls happen **over multiple turns** (agent loop)
3. The task requires **information that isn't in the prompt** (external files, test results)

### Revised Strategy

| Phase | Tool Strategy | When |
|-------|--------------|------|
| **Single-turn baseline** | No tools in prompt | Weeks 56-58 benchmarks |
| **Tool-aware prompting** | Tool descriptions only for multi-turn tasks | Week 60+ agent loop |
| **Active tool controller** | Model actually calls tools and gets results | Week 60+ (MVP) |

### Recommendation
- Do NOT include tool descriptions in single-turn evaluation prompts
- Build the tool controller for the agent loop (Week 60)
- Test again when the agent loop can actually execute tool calls

---

## 5. Infrastructure Built

| File | Purpose |
|------|---------|
| `src/lyme_model/tools/__init__.py` | Public API |
| `src/lyme_model/tools/registry.py` | ToolDef, ToolCategory, ToolRegistry (10 tools, 2 levels) |
| `src/lyme_model/tools/dispatch.py` | ToolDispatcher, ToolUseOptimizer |
| `src/lyme_model/tools/fallback.py` | ToolFallback (error recovery) |

---

## 6. Decision Gate

**Question:** Can tools compensate for weaker reasoning in local models?

**Answer:** Not in single-turn mode. Tools only help in multi-turn agent loops
where the model can actually execute them and incorporate results.

**Next step:** Integrate tools into the agent runtime (Week 60), then re-test.
