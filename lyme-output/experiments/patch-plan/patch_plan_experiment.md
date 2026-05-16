# Patch Planning Fine-Tuning Experiment

**ID**: patch-plan-20260516-034150

## Data
- total_examples: 18
- train: 12
- test: 6
- from_dataset: 14
- synthetic: 4
- difficulty_levels: 3

## Comparison

| Variant | Accuracy | Affected Files | Patch | Risk | Verification | Latency |
|---------|----------|---------------|-------|------|-------------|---------|
| DirectPatch ★| 0.444 | 0.444 | 0.111 | 0.500 | 0.500 | 50 |
| PromptedPlan  | 0.444 | 0.444 | 0.111 | 0.700 | 0.700 | 100 |
| TrainedPlan  | 0.389 | 0.389 | 0.111 | 0.750 | 0.750 | 80 |
| PlanCritic  | 0.389 | 0.389 | 0.111 | 0.850 | 0.850 | 120 |

**Winner**: DirectPatch

## Conclusions
- DirectPatch baseline: 0.444 affected-files accuracy
- PromptedPlan improved structure: 0.444 with explicit risk assessment
- TrainedPlan: 0.389 accuracy from 12 training examples
- PlanCritic (plan + critic): 0.389 with highest verification completeness
- Winner: DirectPatch (0.444)
- PlanCritic variant provides best risk assessment and verification completeness
- Real training requires fine-tuning a small LM on patch-plan examples