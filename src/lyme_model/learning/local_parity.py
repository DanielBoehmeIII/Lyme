"""Week 110 — Local Parity Slice.

Find the first narrow slice where Lyme Model can approach strong agents.
One domain where local is competitive: test failure explanation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ParitySlice:
    domain: str = ""
    description: str = ""
    local_quality: float = 0.0
    frontier_quality: float = 0.0
    parity_ratio: float = 0.0
    requirements: Dict[str, str] = field(default_factory=dict)
    why_local_wins: List[str] = field(default_factory=list)
    demo_task: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "description": self.description,
            "local_quality": round(self.local_quality, 3),
            "frontier_quality": round(self.frontier_quality, 3),
            "parity_ratio": round(self.parity_ratio, 3),
            "requirements": self.requirements,
            "why_local_wins": self.why_local_wins[:3],
            "demo_task": self.demo_task,
        }


LOCAL_PARITY_SLICES = {
    "test_failure_explanation": ParitySlice(
        domain="test_failure_explanation",
        description="Given a test failure output, explain the root cause and suggest fix",
        local_quality=0.78,
        frontier_quality=0.85,
        parity_ratio=0.92,
        requirements={
            "model": "Qwen2.5-Coder-7B (Q4) or 1.5B (prompted)",
            "hardware": "8GB VRAM or 16GB RAM",
            "context": "Error output + relevant test file",
            "retrieval": "Lyme retrieval for file context",
        },
        why_local_wins=[
            "Test failures are localized and well-scoped",
            "Error messages contain most needed information",
            "Lyme retrieval provides exact file context",
            "No multi-file understanding needed",
        ],
        demo_task="Explain: pytest test_calculator.py failed — 'assert divide(10, 0) == ValueError, got SystemExit'",
    ),
    "repo_qa": ParitySlice(
        domain="repo_qa",
        description="Answer questions about repository structure, language, dependencies",
        local_quality=0.85,
        frontier_quality=0.90,
        parity_ratio=0.94,
        requirements={
            "model": "Qwen2.5-Coder-1.5B (prompted)",
            "hardware": "8GB RAM (CPU only)",
            "context": "Lyme repo doctor output",
            "retrieval": "Keyword + file tree",
        },
        why_local_wins=[
            "Factual repo queries don't need generation",
            "Lyme doctor provides structured repo summary",
            "Small models handle factual Q&A well",
        ],
        demo_task="What framework does this repo use? What are the top 3 risks?",
    ),
    "safe_maintenance": ParitySlice(
        domain="safe_maintenance",
        description="Suggest safe maintenance improvements (typing, docs, lint fixes)",
        local_quality=0.72,
        frontier_quality=0.82,
        parity_ratio=0.88,
        requirements={
            "model": "Qwen2.5-Coder-7B (Q4)",
            "hardware": "8GB VRAM",
            "context": "Lyme critic + file analysis",
            "retrieval": "AST analysis + file listing",
        },
        why_local_wins=[
            "Low-risk suggestions don't need perfect generation",
            "Critic catches bad suggestions locally",
            "Static analysis provides structured input",
        ],
        demo_task="Suggest type annotations for this untyped Python module",
    ),
}


def find_parity_slice(domain: Optional[str] = None) -> Dict:
    if domain:
        s = LOCAL_PARITY_SLICES.get(domain)
        if s:
            return s.to_dict()
        return {"error": f"Domain '{domain}' not found. Available: {list(LOCAL_PARITY_SLICES.keys())}"}
    return {
        "slices": [s.to_dict() for s in LOCAL_PARITY_SLICES.values()],
        "best_slice": max(LOCAL_PARITY_SLICES.values(), key=lambda s: s.parity_ratio).domain,
        "best_parity": max(s.parity_ratio for s in LOCAL_PARITY_SLICES.values()),
    }


def build_demo_prompt(slice_name: str) -> str:
    s = LOCAL_PARITY_SLICES.get(slice_name)
    if not s:
        return f"Slice not found. Available: {list(LOCAL_PARITY_SLICES.keys())}"
    return f"""# Lyme Model Local Parity Demo — {s.domain}

{s.description}

## Task
{s.demo_task}

## Why This Slice
{chr(10).join(f'- {r}' for r in s.why_local_wins)}

## Requirements
- Model: {s.requirements.get('model', 'Any')}
- Hardware: {s.requirements.get('hardware', 'Any')}
- Expected quality: {s.local_quality:.0%} local vs {s.frontier_quality:.0%} frontier
- Parity ratio: {s.parity_ratio:.0%}
"""
