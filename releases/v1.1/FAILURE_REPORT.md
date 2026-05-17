# Lyme Model v1.1 — Failure Analysis Report

## Known Failure Modes

1. **Long-context tasks** (>1024 tokens): Model truncates context, loses information
2. **Multi-file consistency**: 0.5B model struggles to maintain consistency across 3+ files
3. **Complex SQL/general logic**: Small model limited reasoning depth
4. **Hallucinated file paths**: Model occasionally references files not in context
5. **Verbose output**: SFT model sometimes adds extra commentary instead of pure diff
6. **Diff formatting**: Minor formatting inconsistencies in edge cases

## Mitigation Strategies
- Use critic model to reject hallucinated patches
- Enforce action grammar (Week 53+) for structured output
- Distill from larger teacher models (Phase 10)
- Increase to 7B base model when hardware permits
