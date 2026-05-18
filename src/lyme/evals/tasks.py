"""Concrete evaluation tasks wired from existing benchmark scenarios."""
from .registry import EvalRegistry, EvalTask, EvalSuite
from .metrics import EvalMetrics, SuccessRate, LatencyMetric, TokenUsage, EditPrecision


def _register_all():
    suite = EvalSuite(
        name="core",
        description="Core coding agent capabilities",
        tags=["core", "coding", "agent"],
    )

    suite.add_task(EvalTask(
        id="latency-baseline",
        name="Latency Baseline",
        description="Measure response time for a simple code query",
        category="latency",
        difficulty=0.1,
    ))
    suite.add_task(EvalTask(
        id="latency-tool-call",
        name="Tool Call Latency",
        description="Measure time for a tool-call round trip",
        category="latency",
        difficulty=0.3,
    ))
    suite.add_task(EvalTask(
        id="tool-call-accuracy",
        name="Tool Call Accuracy",
        description="Accuracy of tool parameter generation",
        category="tool_use",
        difficulty=0.5,
    ))
    suite.add_task(EvalTask(
        id="search-efficiency",
        name="Search Efficiency",
        description="Efficiency of file search across a codebase",
        category="file_navigation",
        difficulty=0.6,
    ))
    suite.add_task(EvalTask(
        id="context-retention-baseline",
        name="Context Retention Baseline",
        description="Ability to retain task constraints",
        category="context_retention",
        difficulty=0.4,
    ))
    suite.add_task(EvalTask(
        id="multi-file-edit-consistency",
        name="Multi-File Edit Consistency",
        description="Consistency of edits across multiple files",
        category="multi_file_edit",
        difficulty=0.7,
    ))
    suite.add_task(EvalTask(
        id="repair-syntax-error",
        name="Syntax Error Repair",
        description="Fix a syntax error with test feedback",
        category="repair",
        difficulty=0.3,
    ))
    suite.add_task(EvalTask(
        id="repair-logic-error",
        name="Logic Error Repair",
        description="Fix a logic bug with test feedback",
        category="repair",
        difficulty=0.6,
    ))
    suite.add_task(EvalTask(
        id="hallucination-detection",
        name="Hallucination Detection",
        description="Detect non-existent APIs in generated code",
        category="hallucination",
        difficulty=0.5,
    ))
    suite.add_task(EvalTask(
        id="long-horizon-todo-app",
        name="Long-Horizon Todo App",
        description="Build a complete todo app with multiple features",
        category="long_horizon",
        difficulty=0.7,
    ))

    EvalRegistry.register_suite(suite)

    # Regression suite
    regression = EvalSuite(
        name="regression",
        description="Regression detection tasks",
        tags=["regression", "cognition"],
    )

    cognition_dims = ["planning", "evidence_grounding", "tool_use",
                      "memory_retrieval", "verification", "safe_editing",
                      "uncertainty_communication", "cross_repo_transfer"]

    for i, dim in enumerate(cognition_dims):
        regression.add_task(EvalTask(
            id=f"cognition-{dim}",
            name=f"Cognition: {dim.replace('_', ' ').title()}",
            description=f"Cognitive regression detection for {dim}",
            category="cognition",
            difficulty=0.3 + (i * 0.08),
        ))

    EvalRegistry.register_suite(regression)

    # Stress suite
    stress = EvalSuite(
        name="stress",
        description="Stress testing tasks",
        tags=["stress", "scaling"],
    )

    for size in [5, 10, 25, 50]:
        stress.add_task(EvalTask(
            id=f"stress-repo-size-{size}",
            name=f"Stress: {size} file repo",
            description=f"Task completion on a {size}-file synthetic repo",
            category="stress",
            difficulty=min(0.9, 0.2 + size * 0.015),
        ))

    EvalRegistry.register_suite(stress)


_register_all()
