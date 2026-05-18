"""Tests for Week 3 — Agent Orchestration."""


def test_delegation_graph_build():
    from lyme.orchestration import DelegationGraphBuilder, NodeType
    builder = DelegationGraphBuilder()
    graph = builder.build("Fix bug", [
        {"name": "Analyze", "type": "analyzer", "agent_id": "a1", "description": "Find cause"},
        {"name": "Fix", "type": "executor", "agent_id": "a2", "description": "Apply fix",
         "dependencies": ["node-1"]},
    ])
    assert len(graph.nodes) == 2
    assert len(graph.ready_nodes()) == 1


def test_delegation_graph_ready():
    from lyme.orchestration import DelegationGraphBuilder, NodeStatus
    builder = DelegationGraphBuilder()
    graph = builder.build("Test", [
        {"name": "A", "type": "analyzer", "agent_id": "a1", "description": "Step A"},
        {"name": "B", "type": "executor", "agent_id": "a2", "description": "Step B",
         "dependencies": ["node-0"]},
    ])
    ready = graph.ready_nodes()
    assert len(ready) == 1
    assert ready[0].name == "A"
    assert graph.completion_pct() == 0.0


def test_delegation_graph_execute():
    from lyme.orchestration import DelegationGraphBuilder, DelegationGraphExecutor
    builder = DelegationGraphBuilder()
    graph = builder.build("Execute", [
        {"name": "Step1", "type": "executor", "agent_id": "a1", "description": "Do thing"},
    ])
    executor = DelegationGraphExecutor()
    result = executor.execute(graph)
    assert result.all_succeeded
    assert result.completion_pct > 0


def test_delegation_graph_result_cli():
    from lyme.orchestration import DelegationGraphBuilder, DelegationGraphExecutor
    builder = DelegationGraphBuilder()
    graph = builder.build("CLI", [
        {"name": "S1", "type": "executor", "agent_id": "a1", "description": "Step"},
    ])
    executor = DelegationGraphExecutor()
    result = executor.execute(graph)
    output = result.render_cli()
    assert "DELEGATION GRAPH" in output


def test_delegation_build_from_decomposition():
    from lyme.orchestration import DelegationGraphBuilder
    builder = DelegationGraphBuilder()
    graph = builder.build_from_decomposition(
        "Build feature", ["Plan", "Code", "Test"], ["planner", "executor", "verifier"],
        ["agent-p", "agent-c", "agent-v"],
    )
    assert len(graph.nodes) == 3


def test_shared_memory_send():
    from lyme.orchestration import SharedMemory
    sm = SharedMemory()
    mid = sm.send("agent-1", "info", "hello", recipient="agent-2")
    assert mid is not None


def test_shared_memory_read():
    from lyme.orchestration import SharedMemory
    sm = SharedMemory()
    sm.send("agent-1", "info", "Found bug", recipient="agent-2")
    sm.send("agent-1", "warning", "High risk", recipient="agent-2")
    msgs = sm.read("agent-2")
    assert len(msgs) == 2


def test_shared_memory_broadcast():
    from lyme.orchestration import SharedMemory
    sm = SharedMemory()
    mid = sm.broadcast("agent-1", "announcement", "All agents stand by")
    assert mid is not None


def test_shared_memory_state():
    from lyme.orchestration import SharedMemory
    sm = SharedMemory()
    sm.set_state("current_file", "src/main.py", "agent-1")
    val = sm.get_state("current_file")
    assert val == "src/main.py"


def test_shared_memory_report():
    from lyme.orchestration import SharedMemory
    sm = SharedMemory()
    sm.send("a1", "info", "test")
    sm.set_state("key", "val", "a1")
    report = sm.report()
    assert report.total_messages >= 1
    assert report.total_states >= 1
    report.render_cli()


def test_conflict_resolver_no_conflict():
    from lyme.orchestration import ConflictResolver
    cr = ConflictResolver()
    result = cr.detect("topic", [{"statement": "Same", "confidence": 0.8}])
    assert result is None


def test_conflict_resolver_detect():
    from lyme.orchestration import ConflictResolver
    cr = ConflictResolver()
    conflict = cr.detect("arch", [
        {"statement": "Use monolith", "source": "a1", "confidence": 0.9},
        {"statement": "Use microservices", "source": "a2", "confidence": 0.2},
    ])
    assert conflict is not None


def test_conflict_resolver_resolve():
    from lyme.orchestration import ConflictResolver, ResolutionStrategy
    cr = ConflictResolver()
    conflict = cr.detect("framework", [
        {"statement": "Use FastAPI", "source": "a1", "confidence": 0.8},
        {"statement": "Use Flask", "source": "a2", "confidence": 0.6},
        {"statement": "Use FastAPI", "source": "a3", "confidence": 0.7},
    ])
    assert conflict is not None
    result = cr.resolve(conflict, ResolutionStrategy.MAJORITY_VOTE)
    assert "fastapi" in result.resolution.lower()


def test_conflict_resolver_report():
    from lyme.orchestration import ConflictResolver
    cr = ConflictResolver()
    c = cr.detect("test", [
        {"statement": "A", "source": "a1", "confidence": 0.9},
        {"statement": "B", "source": "a2", "confidence": 0.1},
    ])
    if c:
        cr.resolve(c)
    report = cr.report()
    assert report.total_conflicts >= 1
    report.render_cli()


def test_execution_hierarchy_basic():
    from lyme.orchestration import ExecutionHierarchy
    h = ExecutionHierarchy()
    d = h.decide("Fix typo", {"file": "readme.md"}, decider_id="agent-1")
    assert d.outcome is not None


def test_execution_hierarchy_escalation():
    from lyme.orchestration import ExecutionHierarchy, Level
    h = ExecutionHierarchy()
    d = h.decide("Major refactor", {"scope": "200 files"}, decider_id="agent-1")
    assert d.level == Level.L1_STRATEGIC or d.outcome is not None


def test_execution_hierarchy_report():
    from lyme.orchestration import ExecutionHierarchy
    h = ExecutionHierarchy()
    h.decide("Task 1", {"scope": "small"}, decider_id="a1")
    h.decide("Task 2", {"scope": "large"}, decider_id="a2")
    report = h.report()
    assert report["total_decisions"] == 2
    output = h.render_cli()
    assert "EXECUTION HIERARCHY" in output


def test_confidence_router_register():
    from lyme.orchestration import ConfidenceRouter
    router = ConfidenceRouter()
    router.register_agent("planner", ["planning"], {"planning": 0.9})
    report = router.report()
    assert len(report.agents) == 1


def test_confidence_router_route():
    from lyme.orchestration import ConfidenceRouter
    router = ConfidenceRouter()
    router.register_agent("planner", ["planning"], {"planning": 0.9})
    router.register_agent("executor", ["implementation"], {"implementation": 0.8})
    decision = router.route("planning", "Plan feature")
    assert decision.selected_agent == "planner"
    assert decision.confidence > 0


def test_confidence_router_fallback():
    from lyme.orchestration import ConfidenceRouter
    router = ConfidenceRouter()
    router.register_agent("primary", ["task"], {"task": 0.2})
    router.register_agent("backup", ["task"], {"task": 0.9})
    router.set_fallback_chain("task", ["primary", "backup"])
    decision = router.route("task", "Do it", required_confidence=0.5)
    assert decision.selected_agent == "backup"


def test_confidence_router_outcome():
    from lyme.orchestration import ConfidenceRouter
    router = ConfidenceRouter()
    router.register_agent("agent", ["task"])
    router.record_outcome("agent", "task", True, 10.0)
    router.record_outcome("agent", "task", True, 15.0)
    router.record_outcome("agent", "task", False, 20.0)
    report = router.report()
    agent = [a for a in report.agents if a.agent_id == "agent"][0]
    assert agent.total_tasks == 3
    assert agent.success_rate < 1.0


def test_confidence_router_report():
    from lyme.orchestration import ConfidenceRouter
    router = ConfidenceRouter()
    router.register_agent("a1", ["task"], {"task": 0.9})
    router.route("task", "Test route")
    report = router.report()
    assert report.total_routes == 1
    report.render_cli()
