# Lyme Model v2.1 — Tool-Using Local Monster
> Generated: 2026-05-16T23:41:49.055485+00:00

## Components
- Action Grammar v2: strict parseable action sequences
- Tool-Use Imitation v2: learned tool selection and ordering
- Tool Feedback Recovery: recovery from bad tool outputs
- Agent Loop v3: action parsing + tool execution + observation
- Best-of-N + Critic: candidate patch ranking
- Self-Repair v2: correct own patches after test failure
- Micro Long-Horizon Tasks: small multi-step project changes

## Benchmark Deltas
- Action parse rate: target 90%+
- Tool efficiency: 30% fewer tool calls per task
- Self-repair success: 70%+ second-attempt pass rate
- Long-horizon task completion: 60%+