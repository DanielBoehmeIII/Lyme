import time
import uuid
from .schema import (
    OpenAgentTrace, TraceHeader, AgentIdentity, SystemMetadata,
    ModelCallEvent, ToolCallEvent, FileReadEvent, FileEditEvent,
    TestRunEvent, FailedAttemptEvent, EvidenceClaimEvent,
    VerificationStepEvent, HumanInterventionEvent,
    ConfidenceChangeEvent, RollbackEvent,
)


def generate_simple_fix_trace() -> OpenAgentTrace:
    trace = OpenAgentTrace(
        header=TraceHeader(
            trace_id="oat-simple-fix-001",
            session_id="session-42",
            agent=AgentIdentity(
                name="fixer-agent",
                model="claude-3-opus-20240229",
                version="1.0.0",
                framework="lyme",
                capabilities=["code_edit", "test_run", "file_read"],
            ),
            system=SystemMetadata(
                os="linux",
                python_version="3.11",
                context_window_max=200000,
                repo_name="sample-project",
            ),
            tags={"task": "fix-bug", "difficulty": "easy"},
        )
    )

    trace.add_event(ModelCallEvent(
        model="claude-3-opus-20240229",
        provider="anthropic",
        prompt_tokens=450,
        completion_tokens=120,
        total_tokens=570,
        temperature=0.0,
        prompt_preview="Fix the off-by-one error in the pagination function...",
        completion_preview="The issue is in line 23 where `<=` should be `<`...",
        cost=0.00855,
        latency_ms=2340.0,
    ))

    trace.add_event(FileReadEvent(
        file_path="/src/pagination.py",
        bytes_read=2048,
        lines_read=47,
        content_preview="def paginate(items, page, per_page=20):\n    start = (page - 1) * per_page\n    end = start + per_page\n    return items[start:end]",
    ))

    trace.add_event(FileEditEvent(
        file_path="/src/pagination.py",
        edit_type="replace",
        old_text_preview="end = start + per_page",
        new_text_preview="end = min(start + per_page, len(items))",
        lines_added=1,
        lines_removed=1,
        patch_hash="abc123def456",
    ))

    trace.add_event(TestRunEvent(
        command="pytest tests/test_pagination.py -v",
        tests_passed=8,
        tests_failed=0,
        tests_skipped=0,
        total_tests=8,
        coverage_percent=92.0,
        duration=1.35,
        exit_code=0,
    ))

    trace.add_event(EvidenceClaimEvent(
        claim="The off-by-one error is caused by missing bounds check on `end` index",
        claim_type="inference",
        confidence=0.95,
        source="static_analysis",
        supporting_evidence=[
            {"type": "code_review", "detail": "end index can exceed list length when page * per_page > len(items)"},
            {"type": "reproduction", "detail": "Calling paginate(items, 100, 20) on 50-item list returns empty list instead of last page"},
        ],
        verified=True,
    ))

    trace.add_event(VerificationStepEvent(
        verification_type="test",
        target="/src/pagination.py",
        result="passed",
        evidence_ids=[trace.events[-1]["id"]],
        findings=["All pagination edge cases now handled"],
        verification_depth="standard",
    ))

    trace.finalize()
    return trace


def generate_complex_refactor_trace() -> OpenAgentTrace:
    trace = OpenAgentTrace(
        header=TraceHeader(
            trace_id="oat-refactor-002",
            session_id="session-43",
            agent=AgentIdentity(
                name="refactor-agent",
                model="gpt-4-turbo",
                version="2.0.0",
                framework="lyme",
                capabilities=["code_edit", "test_run", "file_read", "search", "rollback"],
            ),
            system=SystemMetadata(
                os="macos",
                python_version="3.12",
                context_window_max=128000,
                repo_name="legacy-ecommerce",
            ),
            parent_trace_id="oat-plan-001",
            tags={"task": "refactor-payment", "difficulty": "hard", "risk": "high"},
        )
    )

    trace.add_event(ModelCallEvent(
        model="gpt-4-turbo", provider="openai",
        prompt_tokens=3200, completion_tokens=850, total_tokens=4050,
        temperature=0.1,
        prompt_preview="Refactor the payment processing module to use strategy pattern...",
        completion_preview="I'll extract each payment method into its own strategy class...",
        cost=0.0405, latency_ms=5800.0,
    ))

    trace.add_event(FileReadEvent(file_path="/src/payment/processor.py", bytes_read=15600, lines_read=340))
    trace.add_event(FileReadEvent(file_path="/src/payment/gateways.py", bytes_read=8900, lines_read=195))
    trace.add_event(FileReadEvent(file_path="/tests/test_payment.py", bytes_read=4200, lines_read=98))

    trace.add_event(FileEditEvent(
        file_path="/src/payment/strategies/credit_card.py",
        edit_type="create",
        new_text_preview="class CreditCardStrategy:\n    def process(self, amount):...",
        lines_added=85, lines_removed=0,
        patch_hash="def789ghi012",
    ))
    trace.add_event(FileEditEvent(
        file_path="/src/payment/strategies/paypal.py",
        edit_type="create",
        new_text_preview="class PayPalStrategy:\n    def process(self, amount):...",
        lines_added=72, lines_removed=0,
        patch_hash="jkl345mno678",
    ))
    trace.add_event(FileEditEvent(
        file_path="/src/payment/strategies/crypto.py",
        edit_type="create",
        new_text_preview="class CryptoStrategy:\n    def process(self, amount):...",
        lines_added=90, lines_removed=0,
        patch_hash="pqr901stu234",
    ))
    trace.add_event(FileEditEvent(
        file_path="/src/payment/processor.py",
        edit_type="replace",
        old_text_preview="def process_payment(method, amount):\n    if method == 'credit':...",
        new_text_preview="STRATEGIES = {...}\n\ndef process_payment(method, amount):\n    strategy = STRATEGIES.get(method)...",
        lines_added=45, lines_removed=40,
        patch_hash="vwx567yza890",
    ))

    trace.add_event(FailedAttemptEvent(
        attempt_number=1, max_attempts=2,
        failure_reason="Tests failing: 3 integration tests broken by interface change",
        failure_category="regression",
        strategy_change="Added backward compatibility layer",
        retry_strategy="preserve_old_interface",
        lessons_learned="Always maintain backward compatibility during refactoring",
    ))

    trace.add_event(ConfidenceChangeEvent(
        prior_confidence=0.85, post_confidence=0.60,
        change_reason="Test failures revealed incomplete interface migration",
        related_event_id=trace.events[-1]["id"],
    ))

    trace.add_event(FileEditEvent(
        file_path="/src/payment/processor.py",
        edit_type="replace",
        old_text_preview="def process_payment(method, amount):\n    strategy = STRATEGIES.get(method)...",
        new_text_preview="def process_payment(method, amount, **kwargs):\n    strategy = STRATEGIES.get(method)...\n    if hasattr(strategy, 'legacy_process'):...",
        lines_added=12, lines_removed=2,
        patch_hash="bcd123efg456",
        verified=True,
    ))

    trace.add_event(TestRunEvent(
        command="pytest tests/test_payment.py tests/test_integration.py -v",
        tests_passed=24, tests_failed=0, tests_skipped=1, total_tests=25,
        coverage_percent=88.5, duration=4.2, exit_code=0,
    ))

    trace.add_event(VerificationStepEvent(
        verification_type="test",
        target="/src/payment/",
        result="passed",
        findings=["All payment tests pass", "Coverage >= 85%", "No regression in integration tests"],
        verification_depth="standard",
    ))

    trace.add_event(HumanInterventionEvent(
        intervention_type="approval",
        user_message="This looks good. Approved for merge.",
        effect="allowed",
        prior_confidence=0.60, post_confidence=0.95,
        duration_to_respond_ms=45000.0,
    ))

    trace.add_event(EvidenceClaimEvent(
        claim="Strategy pattern reduces payment processing cyclomatic complexity from 28 to 12",
        claim_type="observation",
        confidence=0.98,
        source="static_analysis",
        supporting_evidence=[
            {"type": "metric", "detail": "Complexity reduced: CC 28 -> 12"},
            {"type": "metric", "detail": "Lines of code: -15%"},
        ],
        verified=True,
    ))

    trace.finalize()
    return trace


def generate_failed_attempt_trace() -> OpenAgentTrace:
    trace = OpenAgentTrace(
        header=TraceHeader(
            trace_id="oat-failed-003",
            agent=AgentIdentity(name="novice-agent", model="claude-3-haiku", version="0.5.0"),
            system=SystemMetadata(repo_name="broken-project"),
            tags={"task": "fix-crash", "outcome": "failed"},
        )
    )

    trace.add_event(ModelCallEvent(model="claude-3-haiku", total_tokens=890, latency_ms=1200.0))

    trace.add_event(FileEditEvent(
        file_path="/src/database.py", edit_type="replace",
        old_text_preview="connection = create_connection()",
        new_text_preview="connection = create_connection(timeout=5)",
        lines_added=1, lines_removed=1,
        patch_hash="aaa111bbb222",
    ))

    trace.add_event(TestRunEvent(command="pytest", tests_passed=10, tests_failed=3, total_tests=13, exit_code=1,
                                  failure_messages=["AttributeError: 'NoneType' object has no attribute 'execute'",
                                                     "RuntimeError: connection already closed"]))

    trace.add_event(FailedAttemptEvent(
        attempt_number=1, max_attempts=3,
        failure_reason="Connection pooling not implemented — timeout fix insufficient",
        failure_category="wrong_root_cause",
        strategy_change="Implement proper connection pooling",
        lessons_learned="Timeout alone doesn't fix connection lifecycle issues",
    ))

    trace.add_event(FileEditEvent(
        file_path="/src/database.py", edit_type="replace",
        old_text_preview="connection = create_connection(timeout=5)",
        new_text_preview="from connection_pool import ConnectionPool\npool = ConnectionPool(max_connections=10)\nconnection = pool.get_connection()",
        lines_added=3, lines_removed=1,
        patch_hash="ccc333ddd444",
    ))

    trace.add_event(TestRunEvent(command="pytest", tests_passed=11, tests_failed=2, total_tests=13, exit_code=1,
                                  failure_messages=["ImportError: No module named 'connection_pool'"]))

    trace.add_event(FailedAttemptEvent(
        attempt_number=2, max_attempts=3,
        failure_reason="External dependency not available",
        failure_category="missing_dependency",
        strategy_change="Implement lightweight pool inline",
        retry_strategy="inline_dependency",
    ))

    trace.add_event(FileEditEvent(
        file_path="/src/database.py", edit_type="replace",
        new_text_preview="import queue\n\nclass ConnectionPool:\n    def __init__(self, max_connections=10):...",
        lines_added=45, lines_removed=3,
        patch_hash="eee555fff666",
    ))

    trace.add_event(ConfidenceChangeEvent(prior_confidence=0.70, post_confidence=0.30,
                                           change_reason="Two consecutive failures on same issue",
                                           confidence_level="low", previous_level="medium"))

    trace.add_event(HumanInterventionEvent(
        intervention_type="correction",
        user_message="The connection pool approach is over-engineering. The real issue is that create_connection() returns None when the DB is down. Add proper error handling.",
        effect="redirected",
        prior_confidence=0.30, post_confidence=0.95,
    ))

    trace.add_event(RollbackEvent(
        rollback_strategy="patch_inverse",
        target_event_id=trace.events[-1]["id"],
        target_description="Rollback connection pool, implement error handling instead",
        success=True, lines_restored=48,
        reason="Over-engineered solution: connection pool not needed for this codebase",
        redo_available=True,
    ))

    trace.finalize(status="abandoned")
    return trace


def generate_all_examples(output_dir: str = "lyme-output/standards/traces"):
    import json, os
    os.makedirs(output_dir, exist_ok=True)

    examples = [
        ("simple-fix-trace.json", generate_simple_fix_trace()),
        ("complex-refactor-trace.json", generate_complex_refactor_trace()),
        ("failed-attempt-trace.json", generate_failed_attempt_trace()),
    ]

    for name, trace in examples:
        path = os.path.join(output_dir, name)
        with open(path, "w") as f:
            f.write(trace.to_json())
        print(f"Wrote {path}")

    print(f"\nGenerated {len(examples)} example traces in {output_dir}")
    return examples
