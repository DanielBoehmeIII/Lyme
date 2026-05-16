# Week 57 — Raw 7B vs Lyme-Enhanced 7B

**Date:** Week 57 of Year Two
**Action:** First core Lyme Model experiment — does Lyme compression improve local model quality?

---

## 1. Experimental Design

### Conditions
| Condition | Context Provided | Tokens |
|-----------|-----------------|--------|
| **Raw** | Full file contents (5 files, ~317 tokens) | 317 |
| **Enhanced** | Lyme compression output (L1-L4 pipeline) | 200 |

### Test Repo
A 5-file Python project with:
- `main.py` (FastAPI app with CRUD endpoints)
- `auth.py` (password hashing, login, auth decorator)
- `storage.py` (JSON file persistence)
- `models.py` (User dataclass)
- `test_api.py` (pytest test cases)

### Tasks (4 categories)
1. **Architecture understanding** — Describe modules and relationships
2. **Bug finding** — Find security issues in auth module
3. **Extension planning** — Explain how to add a delete endpoint
4. **Test generation** — Write tests for login function

### Models
- deepseek-coder:6.7b (Ollama, code-specialized)
- llama3:8b (Ollama, general purpose)

### Evaluation
Keyword-based scoring on expected answer elements.

---

## 2. Results

### Per-Task Comparison

| Task | deepseek-coder RAW | deepseek-coder COMP | delta | llama3 RAW | llama3 COMP | delta |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| Architecture | 100% | 80% | -20% | 100% | 80% | -20% |
| Bug finding | 62% | 38% | -25% | 38% | 38% | 0% |
| Extension | 75% | 88% | **+12%** | 75% | 62% | -12% |
| Test generation | 67% | 100% | **+33%** | 89% | 89% | 0% |

### Averages

| Model | RAW avg | COMP avg | Delta |
|-------|:------:|:--------:|:-----:|
| **deepseek-coder:6.7b** | **76.0%** | **76.2%** | **+0.2%** |
| **llama3:8b** | **75.3%** | **67.2%** | **-8.1%** |

---

## 3. Key Findings

### Finding 1: No clear win for compression on small repos
On this 5-file 317-token test repo, Lyme compression showed no net benefit:
- deepseek-coder: essentially identical (±0.2%)
- llama3: compression actually reduced quality (-8.1%)

**Why:** The raw context already fits easily in a 4K-8K context window. Compression adds
overhead (structured JSON-like output) without removing enough tokens to matter.

### Finding 2: Compression helped deepseek-coder on code generation tasks
deepseek-coder improved on:
- **Extension planning:** +12% (compressed context highlighted the module structure)
- **Test generation:** +33% (compressed context focused on the relevant API surface)

This suggests that code-specialized models benefit more from structured,
diagrammatic context.

### Finding 3: Compression hurt architecture and bug-finding tasks
Both models scored worse on architecture understanding (-20%) and bug finding (-25%)
with compressed context. The compression loses detail (exact code, parameter names,
specific imports) that is essential for these tasks.

### Finding 4: The compression output format matters
The current compression pipeline outputs structured JSON/dict data, not natural language.
This format is optimized for machine consumption, not for feeding to LLMs. A future
optimization would convert compression output into natural language summaries.

---

## 4. Limitations

| Limitation | Impact |
|-----------|--------|
| Test repo too small (5 files) | Compression benefits appear only when raw context exceeds context window |
| Compression format not LLM-optimized | JSON output is not the ideal representation for model input |
| Single-turn prompting | Multi-turn agent behavior may benefit differently |
| Small task set (4 tasks) | Results may not generalize |

---

## 5. What We Learned

### What works
- Compression reduces context tokens by ~37% on small repos
- On specific tasks (code generation, planning), compression helps code-specialized models
- The pipeline outputs structured, analyzable representations

### What doesn't
- Compression hurts on comprehension tasks (architecture, bug finding)
- The net effect on small repos is zero to negative
- JSON-style output is suboptimal for model consumption

### What to try next (Weeks 58+)
1. **Test on a larger repo** (>100 files) where raw context exceeds context limits
2. **Convert compression output to natural language** (summaries, not JSON)
3. **Task-specific compression** — compress only the relevant subsystem, not the whole repo
4. **Multi-turn testing** — see if compression helps in agent loops where context budget is tight

---

## 6. Raw Data

Saved to `lyme-output/sprint-weeks-53-72/compression-experiment-results.json`

---

## 7. Decision Gate G2 Assessment

**Gate G2: Does Lyme compression improve raw model performance?**

Current answer: **INCONCLUSIVE** — not yet proven, not yet disproven.

The test was too small to show compression's benefits. Compression is designed for
large repos where raw context exceeds the context window. On tiny repos where everything
fits, compression is unnecessary overhead. A proper test requires a repo where
compression provides meaningful context reduction (>1000 tokens → <500 tokens).
