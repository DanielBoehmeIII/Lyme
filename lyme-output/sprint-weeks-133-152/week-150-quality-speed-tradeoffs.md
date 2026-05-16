# Week 150 — Quality-Speed Tradeoff Curves

**Theme**: User-facing mode recommendations.

## Tradeoff Matrix

| Mode | Success | Latency | HW | Hallucination | Verification | Best For |
|------|:-------:|:-------:|----|:-------------:|:------------:|----------|
| fastest_local | 55% | 2s | CPU | 30% | 0.2 | Trivial Q&A, exploration |
| balanced_local | 70% | 5s | Budget GPU | 18% | 0.5 | Daily dev, medium tasks |
| careful_local | 78% | 10s | Std GPU | 12% | 0.7 | Bug fixes, test repair |
| **specialist_local** | **84%** | **15s** | **Std GPU** | **8%** | **0.85** | **★ BEST VALUE** |
| specialist_critic | 88% | 20s | Std GPU | 5% | 0.90 | High-risk changes |
| fallback_stronger | 92% | 30s | High-end | 3% | 0.95 | Complex refactoring |

## Quality-Speed Curve

```
Success % (higher is better)
  95% ┤                                          ● fallback_stronger (30s)
  90% ┤                                ● specialist_critic (20s)
  85% ┤                     ● specialist_local (15s)  ★ BEST VALUE
  80% ┤           ● careful_local (10s)
  75% ┤
  70% ┤     ● balanced_local (5s)
  65% ┤
  60% ┤
  55% ┤ ● fastest_local (2s)
  50% └──────────────────────────────────────────────
       0s    10s    20s    30s    40s
                  Latency (seconds)
```

## User-Facing Recommendations

| Your Goal | Recommended Mode | Why |
|-----------|:----------------:|-----|
| "I need a quick answer" | fastest_local | 2s, good enough for structural Q&A |
| "I'm doing daily development" | balanced_local | 5s, 70% success, runs on budget GPU |
| "I need to fix a bug" | careful_local | 10s, self-verification catches errors |
| "I need high confidence changes" | **specialist_local** | **15s, 84% success — best value** |
| "This is critical infrastructure" | specialist_critic | 20s, critic catches remaining issues |
| "Local model can't handle this" | fallback_stronger | 30s, but requires high-end hardware |
