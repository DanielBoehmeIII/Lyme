# Week 56 — Local Model Capability Benchmark

**Date:** Week 56 of Year Two
**Action:** Establish raw local-model baselines on coding-agent tasks.

---

## 1. Methodology

### Models Tested

| Model | Size | Parameters | Quantization |
|-------|------|------------|-------------|
| deepseek-coder:6.7b | 3.8 GB | 6.7B | Q4 (Ollama default) |
| llama3:8b | 4.7 GB | 8.0B | Q4 (Ollama default) |
| gpt-oss:20b | 13 GB | 20B | Q4 (Ollama default) |

### Tasks (6 categories)

| Task | Category | Description |
|------|----------|-------------|
| repo-qa | Repo Understanding | Answer questions about project structure |
| bug-finding | Bug Detection | Find bugs in a code snippet (div by zero, SQL injection, file handle leak) |
| small-edit | Code Generation | Add a goodbye function to an existing module |
| test-repair | Testing | Fix broken test assertions |
| hallucination-resistance | Hallucination | Use only existing API methods, don't fabricate |
| multi-file-reasoning | Reasoning | Identify security issues across 3 related files |

### Constraints
- **No tool access.** Raw model prompting only (this is the baseline).
- **No Lyme compression.** Models receive the full prompt with file contents.
- **Single-turn.** Each task is one prompt, one response.
- **60s timeout per task.**

---

## 2. Results

### Cross-Model Comparison

| Model | Pass Rate | Avg Time | Avg Tokens | Notes |
|-------|-----------|----------|------------|-------|
| **llama3:8b** | **100.0%** | 7.1s | 168 | Perfect score on all 6 tasks |
| **deepseek-coder:6.7b** | **83.3%** | **5.4s** | 162 | Fastest model, failed hallucination test |
| **gpt-oss:20b** | 50.0% | 36.1s | 48 | Too slow, 3 tasks timed out at 60s |

### Per-Task Breakdown

| Task | deepseek-coder:6.7b | llama3:8b | gpt-oss:20b |
|------|:---:|:---:|:---:|
| repo-qa | PASS (2.5s) | PASS (9.6s) | PASS (15.5s) |
| bug-finding | PASS (9.5s) | PASS (7.7s) | FAIL (timeout) |
| small-edit | PASS (1.2s) | PASS (0.9s) | PASS (6.9s) |
| test-repair | PASS (3.8s) | PASS (4.4s) | PASS (14.3s) |
| hallucination-resistance | **FAIL** (5.5s) | PASS (6.0s) | FAIL (timeout) |
| multi-file-reasoning | PASS (10.1s) | PASS (13.7s) | FAIL (timeout) |

### Latency Profile

| Model | Fastest Task | Slowest Task | Avg Response |
|-------|:-----------:|:-----------:|:----------:|
| deepseek-coder:6.7b | 1.2s (small-edit) | 10.1s (reasoning) | 5.4s |
| llama3:8b | 0.9s (small-edit) | 13.7s (reasoning) | 7.1s |
| gpt-oss:20b | 6.9s (small-edit) | 60s (timeout) | 36.1s |

---

## 3. Key Findings

### Finding 1: 7-8B local models are viable for basic coding tasks
Both deepseek-coder:6.7b and llama3:8b completed 5/6 and 6/6 tasks respectively.
Raw local models can:
- Answer repo Q&A correctly
- Find bugs in code (division by zero, SQL injection, file handles)
- Generate small code additions
- Repair broken tests
- Reason across multiple files

### Finding 2: Hallucination is real and model-dependent
deepseek-coder:6.7b fabricated API methods (`list_all_buckets`, `bucket_exists`)
instead of using only the available `list_buckets` and `get_object`.
llama3:8b correctly refused to fabricate. This suggests hallucination
resistance varies significantly by model and training approach.

### Finding 3: 20B models are not practical on 8GB VRAM
gpt-oss:20b timed out on 3 of 6 tasks. It runs entirely on CPU (doesn't fit in 8GB VRAM).
Average latency of 36.1s makes it unusable for interactive use.

### Finding 4: Code-specialized models are faster but less careful
deepseek-coder:6.7b is 1.3x faster than llama3:8b but failed the hallucination test.
The code-specialized training may optimize for speed over caution.

### Finding 5: Multi-file reasoning is the most expensive task
Both models took the longest on multi-file reasoning (10.1s and 13.7s).
Complex reasoning across files requires more generation tokens and attention.

---

## 4. Raw Baseline Summary

| Dimension | Best Model | Baseline Score |
|-----------|-----------|----------------|
| Task completion | llama3:8b | 100% (6/6) |
| Speed | deepseek-coder:6.7b | 5.4s avg |
| Hallucination resistance | llama3:8b | 100% (1/1) |
| Bug detection | deepseek-coder:6.7b | PASS |
| Code generation | deepseek-coder:6.7b | 1.2s |
| Multi-file reasoning | deepseek-coder:6.7b | 10.1s |

### What We Know Now (Baseline)
- Local 7-8B models can complete basic coding tasks
- Average response time is 5-7 seconds per turn
- Hallucination is a real problem (at least for some models)
- Multi-file reasoning costs 2x the latency of simple tasks
- 20B models are not viable on 8GB consumer VRAM

### What We Don't Know Yet (For Future Weeks)
- Does Lyme compression improve these scores? (Week 57-58)
- Does tool access amplify weak models? (Week 59)
- Does quantization affect quality? (Week 61)
- Does speculative decoding help throughput? (Week 62)
- Can fine-tuning fix hallucination? (Week 64-66)

---

## 5. Data

Raw results saved to `lyme-output/sprint-weeks-53-72/capability-benchmark-results.json`

This baseline is used for comparison in:
- **Week 57:** Lyme-enhanced vs raw model comparison
- **Week 58:** Compression experiment
- **Week 68:** Frontier comparison
