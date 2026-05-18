"""Passive intelligence — background repo analysis and proactive warnings."""
from .drift import ArchitectureDriftDetector
from .flaky import FlakyTestDetector
from .suspicious import SuspiciousCommitDetector
from .debt import TechnicalDebtAnalyzer
from .engine import IntelligenceEngine

__all__ = [
    "ArchitectureDriftDetector",
    "FlakyTestDetector",
    "SuspiciousCommitDetector",
    "TechnicalDebtAnalyzer",
    "IntelligenceEngine",
]
