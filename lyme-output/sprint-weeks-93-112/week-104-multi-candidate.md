# Week 104 — Multi-Candidate Local Decoding

**Module:** `learning/multi_candidate.py`
**N=3 candidates** per task, ranked by score + risk
**Benchmark:** 5 tasks, avg best-of-N improvement over first candidate
**Best-of-N gains estimated:** n=2: +15%, n=3: +25%, n=5: +35% (diminishing returns)
**Selection:** critic score (primary) + risk score (tiebreaker) + static checks
**Tests:** 10 tests

Cost: Nx generation latency + 1x ranking. Quality gain depends on task difficulty.
