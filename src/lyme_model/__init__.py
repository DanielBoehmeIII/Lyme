"""Lyme Model — local model runtime and amplification layer.
Lyme Audit is the measurement instrument. Lyme Model is the experiment.
Audit measures Model. Model uses Audit as library.

v0.7.0 — Weeks 113-132: checkpointed long-horizon local agent with hardened narrow parity.
"""

__version__ = "0.7.0"

__all__ = [
    "failures",      # Week 73 — Error taxonomy + detection
    "runtime",       # Week 74 — Failure-driven runtime
    "retrieval",     # Week 75 — Retrieval policies
    "amplify",       # Week 76 — Context packet compiler
    "planning",      # Week 77 — Patch planner (extended Weeks 116-128: diff. estimator, mode select, fallback, long-horizon)
    "verification",  # Week 78 — Verifier-first workflow
    "correction",    # Week 79 — Self-correction loop
    "memory",        # Weeks 81-84 — Coding memory, corruption, adaptation, transfer
    "learning",      # Weeks 85-99 — Full learning pipeline
    "speed",         # Week 89 — Speed profiling and optimization
    "cache",         # Week 90 — Caching and reuse
    "slices",        # Week 113 — Hardened local parity slices
    "eval",          # Weeks 114-115 — Real-repo eval set + human baseline
    "ui",            # Week 129 — Developer UX for local agents
]

# Import key components for easy access
from .slices.repo_qa import repo_qa_slice
from .release_v06 import v06 as lyme_v06
from .release_v07 import v07 as lyme_v07
from .planning.difficulty_estimator import estimator as diff_estimator
from .planning.mode_selection import selector as mode_selector
from .planning.fallback import fallback as fallback_strategy
from .planning.confidence import calibrator as conf_calibrator
from .install import wizard as install_wizard
