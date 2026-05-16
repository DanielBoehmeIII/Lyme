# Week 62 — Speculative Decoding / Draft Model Research

**Date:** Week 62 of Year Two
**Action:** Research speculative decoding feasibility for Lyme Model on consumer hardware.

---

## 1. Concept

Speculative decoding uses a small, fast **draft model** to generate K candidate tokens,
then a larger **target model** verifies them in parallel. If accepted, throughput increases.
If rejected, the target model regains control.

**For Lyme Model:**
- Draft: 0.5-1.5B model (Q4) → expected 40-60 tok/s
- Target: 6.7-8B model (Q4) → expected 10-15 tok/s
- Ideal speedup: 1.5x-2.5x on code tokens

---

## 2. Hardware Feasibility

### Can we run two models simultaneously on 8GB VRAM?

| Models | Total VRAM | Feasible? |
|--------|:----------:|:---------:|
| 7B Q4 (4.5 GB) + 1.5B Q4 (1.0 GB) | 5.5 GB | ✅ Yes |
| 7B Q4 (4.5 GB) + 3B Q4 (2.0 GB) | 6.5 GB | ✅ Yes |
| 7B Q5 (5.5 GB) + 1.5B Q4 (1.0 GB) | 6.5 GB | ✅ Yes |
| 8B Q4 (5.0 GB) + 1.5B Q4 (1.0 GB) | 6.0 GB | ✅ Yes |
| 7B Q6 (6.8 GB) + 1.5B Q4 (1.0 GB) | 7.8 GB | ⚠️ Tight |

**Conclusion:** Dual-model inference is feasible on 8GB VRAM for a 7B + 1.5B pair at Q4.

---

## 3. Code-Specific Optimization

Code tokens are more predictable than natural language, making speculative
decoding more effective:

| Token Type | Acceptance Rate | Why |
|-----------|:--------------:|-----|
| Keywords (def, return, if) | ~95% | Nearly deterministic |
| Braces, parens, semicolons | ~99% | Syntactically forced |
| Variable names | ~60% | Depends on context |
| Strings/comments | ~40% | Free-form text |
| Indentation | ~99% | Structurally determined |

**Expected acceptance rate for code: ~75-85%** (vs ~60-70% for natural language).

---

## 4. Implementation Strategy

### Phase 1: Draft-Target Pairing
```
Draft model: qwen2.5-coder:1.5b (Q4, ~1 GB, ~50 tok/s)
Target model: deepseek-coder:6.7b (Q4, ~4.5 GB, ~10 tok/s)

Draft generates: K=5 tokens
Target verifies: all 5 in parallel
If accepted: skip to token 6
If rejected: use target's token, reduce K

Expected throughput: 10 tok/s → ~18 tok/s (1.8x)
```

### Phase 2: Dynamic K Selection
```
K starts at 5
On each full acceptance: K += 1 (up to max 10)
On each rejection: K = max(1, K - 2)
Code tokens: higher starting K (7)
Comment tokens: lower starting K (3)
```

### Phase 3: Ollama Integration
Ollama does not natively support speculative decoding.
Implementation would require:
- Direct llama.cpp integration (speculative flag)
- Or custom orchestration running two Ollama instances
- Or switching to a Python inference library (llama-cpp-python)

---

## 5. Estimated Impact

| Metric | Single Model (7B Q4) | Speculative Decode | Improvement |
|--------|:-------------------:|:------------------:|:----------:|
| Tokens/sec | 10-13 | 18-25 | 1.6-2.0x |
| Latency per task | 6.5s | ~4s | 1.6x faster |
| VRAM usage | 4.5 GB | 5.5 GB | +1 GB |
| Quality | Baseline | Slightly lower (draft errors) | <5% loss |
| Complexity | Low | High | New failure mode |

---

## 6. Recommendation

**Implement speculative decoding post-MVP.** The 1.6-2.0x throughput improvement
is valuable but not critical for the MVP. It adds significant complexity (dual
model management, acceptance logic, fallback) that should not distract from
getting the basic agent loop working.

**Prerequisite:** Direct llama.cpp integration (not Ollama subprocess).

**Timeline:** Target Week 62 of Year Two (if Year Two extends to 72+ weeks)
or as a post-v0.1 enhancement.

---

## 7. Reference

Design document in `docs/LYME_MODEL_DESIGN.md` Section 5.3 (decode/ module
with SpeculativeDecode class, dynamic K, code-specific acceleration).
