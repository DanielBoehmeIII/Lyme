"""Product/Research Boundary: what each feature shows, collects, and enables.

For every feature, defines:
1. what the user sees (product face)
2. what telemetry is collected (research substrate)
3. what experiments it enables (research agenda)
4. how it improves future agent behavior (feedback loop)
5. what stays hidden/internal (private research data)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class FeatureBoundary:
    name: str
    product_face: str
    telemetry_collected: List[str]
    experiments_enabled: List[str]
    agent_improvement: List[str]
    hidden_internals: List[str]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "product_face": self.product_face,
            "telemetry_collected": self.telemetry_collected,
            "experiments_enabled": self.experiments_enabled,
            "agent_improvement": self.agent_improvement,
            "hidden_internals": self.hidden_internals,
        }


PRODUCT_FEATURES = [
    FeatureBoundary(
        name="CLI",
        product_face="Command-line interface with help, completion, and structured output",
        telemetry_collected=[
            "command name and subcommand",
            "argument pattern (hashed, not raw values)",
            "execution duration",
            "exit code",
            "error type on failure",
            "terminal width (for formatting)",
        ],
        experiments_enabled=[
            "usage frequency analysis",
            "command popularity ranking",
            "error rate tracking over releases",
            "argument anti-pattern detection",
        ],
        agent_improvement=[
            "command suggestions based on usage patterns",
            "autocomplete tuning from common workflows",
            "error message improvement from failure patterns",
        ],
        hidden_internals=[
            "raw argument values (hashed before storage)",
            "full terminal session content",
            "environment variables",
            "working directory history",
        ],
    ),
    FeatureBoundary(
        name="Repository Q&A (lyme ask)",
        product_face="Natural language Q&A about a repository with evidence citations",
        telemetry_collected=[
            "question topic category (not raw text)",
            "number of files consulted",
            "confidence score per claim",
            "evidence count per answer",
            "contradictions detected",
            "refused/unanswerable count",
            "citation types (file, function, git, command)",
        ],
        experiments_enabled=[
            "context selection effectiveness measurement",
            "hallucination rate by question type",
            "evidence quality scoring calibration",
            "refusal accuracy (knowing when not to answer)",
            "citation relevance precision/recall",
        ],
        agent_improvement=[
            "context retrieval ranking from usage patterns",
            "confidence calibration from user feedback",
            "hallucination detection from contradiction patterns",
            "evidence presentation from comprehension studies",
        ],
        hidden_internals=[
            "raw question text (stored only as hashed topic vector)",
            "full context window contents",
            "model internal activations",
            "user's repository contents",
        ],
    ),
    FeatureBoundary(
        name="Local Fix (lyme fix)",
        product_face="Analyze issues and propose/provide fixes with safety guarantees",
        telemetry_collected=[
            "issue type classification",
            "files affected count and categories",
            "fix strategy attempted",
            "fix success/failure",
            "rollback frequency",
            "edit validation results",
            "test outcomes after fix",
        ],
        experiments_enabled=[
            "fix success rate by issue type and model",
            "repair strategy effectiveness ranking",
            "safe edit protocol evaluation",
            "rollback necessity prediction",
            "edit validation accuracy",
        ],
        agent_improvement=[
            "strategy selection from success rate history",
            "risk estimation from past failures",
            "test selection from coverage patterns",
            "rollback triggers from damage assessment",
        ],
        hidden_internals=[
            "full file contents before/after edit",
            "generated patch content (stored only for replay)",
            "model prompts and completions",
            "tool call sequences",
        ],
    ),
    FeatureBoundary(
        name="Semantic Diff (lyme diff)",
        product_face="Classify and explain diffs by semantic impact category",
        telemetry_collected=[
            "diff size (lines added/removed/modified)",
            "semantic categories assigned",
            "classification confidence per category",
            "files changed and their subsystems",
            "user acceptance of classification",
        ],
        experiments_enabled=[
            "diff classification accuracy benchmark",
            "semantic category taxonomy validation",
            "human classification agreement study",
            "category distribution over project lifetime",
        ],
        agent_improvement=[
            "change impact prediction from historical diffs",
            "review prioritization from semantic severity",
            "edit safety assessment from diff patterns",
        ],
        hidden_internals=[
            "full diff content (stored for replay only)",
            "AST before/after comparison internals",
            "model confidence distributions per category",
        ],
    ),
    FeatureBoundary(
        name="Trace Viewer (lyme trace)",
        product_face="Visualize agent execution traces with timeline and decision trees",
        telemetry_collected=[
            "trace viewed event",
            "filter parameters used",
            "export format requested",
            "view duration (how long user spent)",
        ],
        experiments_enabled=[
            "trace comprehension effectiveness study",
            "visualization format comparison",
            "user attention heatmap analysis",
        ],
        agent_improvement=[
            "trace compression tuning from viewing patterns",
            "important event highlighting from user focus",
        ],
        hidden_internals=[
            "full trace event data (stored locally)",
            "model internal state snapshots",
            "raw timing data for all operations",
        ],
    ),
    FeatureBoundary(
        name="Memory Inspection (lyme memory)",
        product_face="Query and inspect persistent agent memory with search",
        telemetry_collected=[
            "memory query topic (hashed)",
            "results returned count",
            "memory type accessed",
            "memory staleness indicators",
        ],
        experiments_enabled=[
            "memory utilization patterns study",
            "forgetting curve measurement",
            "memory retrieval accuracy evaluation",
            "compression effectiveness over time",
        ],
        agent_improvement=[
            "retrieval ranking from usage patterns",
            "memory pruning from access frequency",
            "compression strategy from query coverage",
        ],
        hidden_internals=[
            "full memory content (stored locally)",
            "embedding vectors",
            "access timestamp patterns (privacy sensitive)",
        ],
    ),
    FeatureBoundary(
        name="Model Benchmarking (lyme bench)",
        product_face="Compare model performance on standardized coding tasks",
        telemetry_collected=[
            "model name and size",
            "task category",
            "score and sub-scores",
            "latency and token usage",
            "hardware info (GPU, RAM, CPU cores)",
        ],
        experiments_enabled=[
            "model ranking and capability matrix",
            "scaling law discovery (performance vs size)",
            "cost-performance tradeoff analysis",
            "benchmark saturation detection",
        ],
        agent_improvement=[
            "model selection recommendations from task type",
            "context budget tuning from benchmark results",
            "quantization impact assessment",
        ],
        hidden_internals=[
            "full model weights/structure",
            "individual benchmark run traces (aggregated only)",
            "proprietary model API keys",
        ],
    ),
    FeatureBoundary(
        name="Repo Doctor (lyme doctor)",
        product_face="Diagnose repository health: structure, risks, hotspots, suggestions",
        telemetry_collected=[
            "diagnosis categories triggered",
            "confidence scores per diagnosis",
            "risky files count and categories",
            "invariants inferred count",
            "circular dependencies found",
            "architectural hotspot count",
        ],
        experiments_enabled=[
            "diagnosis accuracy against expert review",
            "invariant discovery effectiveness by language",
            "repo health metric correlation with bug rates",
            "onboarding path quality assessment",
        ],
        agent_improvement=[
            "diagnosis priority from risk correlation",
            "invariant mining from repeated patterns",
            "suggestion relevance from adoption rates",
            "confidence calibration from user feedback",
        ],
        hidden_internals=[
            "full file content analysis (stored only as feature vectors)",
            "individual developer contribution patterns",
            "raw complexity metrics per file (aggregated only)",
        ],
    ),
    FeatureBoundary(
        name="History and Audit (lyme history / lyme audit)",
        product_face="Full action history with replay, undo, and audit trails",
        telemetry_collected=[
            "history queries and filters",
            "undo targets and success rate",
            "audit artifacts inspected",
            "patch verification requests",
        ],
        experiments_enabled=[
            "action reversibility study",
            "audit trail completeness analysis",
            "user trust calibration from undo patterns",
            "replay fidelity measurement",
        ],
        agent_improvement=[
            "action reversibility prediction",
            "risk estimation from audit patterns",
            "undo strategy from success rate history",
        ],
        hidden_internals=[
            "full action payload data (stored for replay only)",
            "patch content before/after (stored locally)",
            "session metadata and timing",
        ],
    ),
    FeatureBoundary(
        name="Cognitive Tracing",
        product_face="Hidden — powers confidence scoring and hallucination detection",
        telemetry_collected=[
            "decision points and alternatives considered",
            "branch exploration patterns",
            "confidence scores before/after actions",
            "thought step types and sequences",
            "tool selection rationale",
        ],
        experiments_enabled=[
            "cognition structure analysis",
            "decision quality vs outcome correlation",
            "branch efficiency measurement",
            "hallucination precursor detection",
        ],
        agent_improvement=[
            "hallucination detection from thought patterns",
            "context budget from decision efficiency",
            "tool selection from success rate per strategy",
            "confidence calibration from outcome correlation",
        ],
        hidden_internals=[
            "full thought step content (stored locally only)",
            "model internal representations",
            "raw confidence distributions",
            "individual decision trees",
        ],
    ),
    FeatureBoundary(
        name="Causal Graph Analysis",
        product_face="Hidden behind lyme graph — produces risk analysis for product use",
        telemetry_collected=[
            "graph topology metrics",
            "edge type distribution",
            "risk score distribution",
            "amplification zone characteristics",
        ],
        experiments_enabled=[
            "causal structure validation against bug history",
            "risk prediction accuracy measurement",
            "hidden dependency discovery rate",
        ],
        agent_improvement=[
            "risk-aware edit planning from causal paths",
            "impact estimation from dependency topology",
            "safe edit boundary detection",
        ],
        hidden_internals=[
            "full causal graph (stored locally)",
            "edge weight matrices",
            "propagation simulation internals",
        ],
    ),
    FeatureBoundary(
        name="Invariant Discovery",
        product_face="Hidden behind lyme discover — produces edit guardrails for product use",
        telemetry_collected=[
            "invariant type distribution",
            "violation detection rate",
            "repair suggestion acceptance rate",
            "confidence distribution across invariants",
        ],
        experiments_enabled=[
            "invariant completeness evaluation",
            "invariant evolution over project lifetime",
            "false positive rate measurement",
            "contradiction resolution effectiveness",
        ],
        agent_improvement=[
            "edit safety checks from invariant rules",
            "architectural guardrails from discovered constraints",
            "refactor safety from invariant violation patterns",
        ],
        hidden_internals=[
            "full invariant set (stored locally)",
            "violation details with code locations",
            "AST analysis internals",
        ],
    ),
    FeatureBoundary(
        name="Temporal Modeling",
        product_face="Hidden behind lyme evolution — produces trend forecasts for product use",
        telemetry_collected=[
            "trend metric types",
            "stability classification distribution",
            "forecast confidence scores",
            "anomaly detection rate",
        ],
        experiments_enabled=[
            "temporal decay curve measurement",
            "refactor wave pattern identification",
            "growth model validation",
            "anomaly prediction accuracy",
        ],
        agent_improvement=[
            "staleness detection from temporal models",
            "maintenance forecasting for proactive fixes",
            "memory pruning timing from decay curves",
        ],
        hidden_internals=[
            "full temporal history (stored locally)",
            "individual commit analysis details",
            "developer velocity metrics",
        ],
    ),
    FeatureBoundary(
        name="Scaling Law Discovery",
        product_face="Hidden — research infrastructure for model comparison",
        telemetry_collected=[
            "model performance at multiple sizes",
            "context budget vs accuracy curves",
            "emergence threshold locations",
            "diminishing return points",
        ],
        experiments_enabled=[
            "model size vs capability scaling",
            "context window utilization efficiency",
            "compression ratio vs accuracy tradeoff",
            "multi-agent scaling overhead",
        ],
        agent_improvement=[
            "optimal model selection for task type",
            "context budget tuning from scaling data",
            "compression ratio recommendation",
        ],
        hidden_internals=[
            "raw scaling experiment data",
            "individual model comparison details",
            "extrapolation models and confidence intervals",
        ],
    ),
    FeatureBoundary(
        name="Hallucination Study",
        product_face="Hidden — powers confidence scoring and verification gating",
        telemetry_collected=[
            "claim verification outcomes",
            "hallucination type distribution",
            "context correlation with hallucination",
            "verification method effectiveness",
        ],
        experiments_enabled=[
            "hallucination rate by model and task",
            "hallucination type taxonomy validation",
            "context quality vs hallucination correlation",
            "verification method comparison",
        ],
        agent_improvement=[
            "claim filtering from hallucination patterns",
            "uncertainty labeling from detection accuracy",
            "verification gating from false positive rate",
        ],
        hidden_internals=[
            "individual claim verification details",
            "false positive/negative logs",
            "model response comparisons",
        ],
    ),
    FeatureBoundary(
        name="Context Degradation Study",
        product_face="Hidden — powers context budget optimization",
        telemetry_collected=[
            "performance at multiple context sizes",
            "collapse point detection",
            "degradation curve characteristics",
            "file count vs accuracy relationship",
        ],
        experiments_enabled=[
            "context window efficiency measurement",
            "retrieval strategy comparison",
            "compression impact on degradation",
            "attention distribution analysis",
        ],
        agent_improvement=[
            "context windowing from degradation curves",
            "retrieval prioritization from collapse points",
            "compression tuning from efficiency data",
        ],
        hidden_internals=[
            "raw degradation experiment data",
            "individual attention patterns",
            "retrieval rank vs accuracy matrices",
        ],
    ),
    FeatureBoundary(
        name="Agent Coordination Studies",
        product_face="Hidden behind lyme society — produces coordination recommendations",
        telemetry_collected=[
            "debate outcome statistics",
            "specialization emergence rate",
            "coordination overhead measurements",
            "topology efficiency comparison",
        ],
        experiments_enabled=[
            "multi-agent scaling law discovery",
            "coordination overhead quantification",
            "specialization vs generality tradeoff",
            "communication topology optimization",
        ],
        agent_improvement=[
            "debate quality improvement from outcome patterns",
            "task routing from specialization data",
            "collaboration efficiency from overhead analysis",
        ],
        hidden_internals=[
            "individual agent profiles and histories",
            "full debate transcripts",
            "coordination graph topology",
        ],
    ),
]


class BoundaryRegistry:
    _instance: Optional["BoundaryRegistry"] = None

    def __init__(self):
        self._features: Dict[str, FeatureBoundary] = {
            f.name.lower().replace(" ", "_").replace("/", "_"): f
            for f in PRODUCT_FEATURES
        }

    @classmethod
    def get_instance(cls) -> "BoundaryRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get(self, name: str) -> Optional[FeatureBoundary]:
        key = name.lower().replace(" ", "_").replace("/", "_")
        return self._features.get(key)

    def list_features(self) -> List[str]:
        return [f.name for f in self._features.values()]

    def list_product_facing(self) -> List[str]:
        return [f.name for f in self._features.values()
                if not f.name.startswith("Hidden")]

    def list_research_only(self) -> List[str]:
        return [f.name for f in self._features.values()
                if f.name.startswith("Hidden")]

    def all_telemetry(self) -> Dict[str, List[str]]:
        return {f.name: f.telemetry_collected for f in self._features.values()}

    def all_experiments(self) -> List[str]:
        experiments = set()
        for f in self._features.values():
            experiments.update(f.experiments_enabled)
        return sorted(experiments)

    def to_dict(self) -> dict:
        return {
            "features": [f.to_dict() for f in self._features.values()],
            "total_features": len(self._features),
            "product_facing": len(self.list_product_facing()),
            "research_only": len(self.list_research_only()),
        }


def get_boundary() -> BoundaryRegistry:
    return BoundaryRegistry.get_instance()
