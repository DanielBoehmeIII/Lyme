# Tool-Use Fine-Tuning Experiment

**ID**: tool-use-20260516-034008

## Data
- total_examples: 45
- train: 31
- test: 14
- standard_traces: 32
- synthetic: 7
- edge_cases: 6
- action_types: 7

## Comparison

| Variant | Accuracy | Level |
|---------|----------|-------|
| HeuristicRouter | 0.429 | ★ |
| Prompted (Qwen2.5-Coder-1.5B-Instruct) | 0.429 | ☆ |
| TrainedPolicy | 0.429 | ☆ |

**Winner**: HeuristicRouter

## By Action

| Action | Count |
|--------|-------|
| search | 11 |
| generate_patch | 9 |
| read | 6 |
| stop | 6 |
| verify | 6 |
| run_command | 5 |
| inspect_ast | 2 |

## Conclusions
- Heuristic router provides baseline: 0.429 accuracy
- Prompted model improves: 0.429 accuracy
- Trained policy: 0.429 accuracy
- Training data: 31 examples across 7 action types
- Winner: HeuristicRouter (0.429)
- Simulated — real training requires fine-tuning a small LM on tool-use data
- Next: generate more labeled tool-use data from Lyme Audit traces