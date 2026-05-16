"""Lyme Model Specialists — Coordinated specialist architecture for local coding agents."""
from .strategy import SPECIALIZATION_STRATEGY, SPECIALIZATIONS, TOP_3_SPECIALIZATIONS
from .interfaces import (
    ALL_SPECIALIST_INTERFACES,
    PlannerInput, PlannerOutput,
    RetrieverInput, RetrieverOutput,
    PatchGeneratorInput, PatchGeneratorOutput,
    CriticInput, CriticOutput,
    VerifierInput, VerifierOutput,
    SummarizerInput, SummarizerOutput,
    RefusalInput, RefusalOutput,
    AuditTrace, ConfidenceLevel, FailureLabel,
    specialist_output_to_audit,
)
from .planner import PlannerSpecialist, planner, benchmark_against_generic
from .retriever import RetrieverSpecialist, retriever, benchmark_retrieval
from .patch_generator import PatchGeneratorSpecialist, patch_generator, benchmark_patch_strategies
from .critic import CriticSpecialist, critic
from .verifier import VerifierSpecialist, verifier, benchmark_verification_quality_vs_cost
from .coordinator import (
    Blackboard, BlackboardState,
    SpecialistRouter, RouterDecision,
    ConflictResolver, ConflictType,
    SpecialistOrchestrator, orchestrator,
    SpecialistMessage, MessageType, SpecialistRole,
)
from .training_data import TrainingDataGenerator, TrainingExample, generator
from .adaptation import SpecialistAdaptationExperiment, experiment
from .optimization import LatencyOptimizer, latency_optimizer, get_tradeoff_curves

__all__ = [
    "SPECIALIZATION_STRATEGY", "SPECIALIZATIONS", "TOP_3_SPECIALIZATIONS",
    "ALL_SPECIALIST_INTERFACES",
    "PlannerInput", "PlannerOutput",
    "RetrieverInput", "RetrieverOutput",
    "PatchGeneratorInput", "PatchGeneratorOutput",
    "CriticInput", "CriticOutput",
    "VerifierInput", "VerifierOutput",
    "SummarizerInput", "SummarizerOutput",
    "RefusalInput", "RefusalOutput",
    "AuditTrace", "ConfidenceLevel", "FailureLabel",
    "specialist_output_to_audit",
    "PlannerSpecialist", "planner",
    "RetrieverSpecialist", "retriever",
    "PatchGeneratorSpecialist", "patch_generator",
    "CriticSpecialist", "critic",
    "VerifierSpecialist", "verifier",
    "Blackboard", "BlackboardState",
    "SpecialistRouter", "RouterDecision",
    "ConflictResolver", "ConflictType",
    "SpecialistOrchestrator", "orchestrator",
    "SpecialistMessage", "MessageType", "SpecialistRole",
    "TrainingDataGenerator", "TrainingExample", "generator",
    "SpecialistAdaptationExperiment", "experiment",
    "LatencyOptimizer", "latency_optimizer", "get_tradeoff_curves",
]
