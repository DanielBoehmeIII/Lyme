from .schema import (
    SemanticDiff, DiffHeader, SyntacticChange, BehavioralIntent,
    AffectedInvariant, ArchitecturalImpact, RiskScore,
    VerificationResult, RollbackStrategy, DiffReport,
    DiffType, IntentType, InvariantType, ImpactLevel,
    RiskLevel, VerificationStatus,
)


def generate_bug_fix_diff() -> SemanticDiff:
    sd = SemanticDiff(
        header=DiffHeader(
            diff_id="sd-bugfix-001",
            source_commit="a1b2c3d4e5f6",
            target_commit="b2c3d4e5f6a1",
            branch="fix/pagination-off-by-one",
            repository="sample-project",
            author="fixer-agent",
            pr_url="https://github.com/example/sample-project/pull/42",
        )
    )

    sd.add_syntactic_change(SyntacticChange(
        file_path="/src/pagination.py",
        diff_type=DiffType.MODIFICATION,
        lines_added=1, lines_removed=1, hunks=1,
        old_code_preview="end = start + per_page",
        new_code_preview="end = min(start + per_page, len(items))",
        language="python", change_scope="function",
        function_name="paginate",
    ))

    sd.add_syntactic_change(SyntacticChange(
        file_path="/tests/test_pagination.py",
        diff_type=DiffType.ADDITION,
        lines_added=12, lines_removed=0, hunks=1,
        new_code_preview="def test_paginate_last_page():\n    items = list(range(50))\n    result = paginate(items, 100, 20)\n    assert len(result) > 0",
        language="python", change_scope="test",
        function_name="test_paginate_last_page",
    ))

    sd.set_intent(BehavioralIntent(
        intent_type=IntentType.BUG_FIX,
        description="Fix off-by-one error in pagination where last page returns empty",
        motivation="When page number is large enough that start + per_page exceeds list length, "
                   "slicing returns empty list instead of remaining items",
        expected_behavior="pagination returns correct remaining items on any valid page",
        previous_behavior="last page returns empty list for large page numbers",
        backward_compatible=True,
    ))

    sd.add_invariant(AffectedInvariant(
        invariant_type=InvariantType.DATA_INVARIANT,
        description="paginate() always returns a subset of input items",
        location="/src/pagination.py",
        status="preserved",
        confidence=0.99,
        evidence=["All items in result are from input list", "Result length never exceeds per_page"],
    ))

    sd.set_architectural_impact(ArchitecturalImpact(
        impact_level=ImpactLevel.LOW,
        affected_subsystems=["pagination module"],
        complexity_delta=1,
        coupling_change=0.0,
    ))

    sd.set_risk(RiskScore(
        overall=RiskLevel.LOW,
        regression_risk=RiskLevel.LOW,
        risk_factors=["Small change, 1 line modified"],
        risk_score_numeric=0.15,
    ))

    sd.set_verification(VerificationResult(
        status=VerificationStatus.PASSED,
        tests_run=12, tests_passed=12, tests_failed=0,
        coverage_percent=95.0,
        static_analysis_passed=True,
        type_checks_passed=True,
        lint_passed=True,
    ))

    sd.set_rollback(RollbackStrategy(
        strategy="git_revert",
        complexity="simple",
        estimated_time_minutes=2,
        steps=["git revert <commit>", "Verify pagination tests pass"],
    ))

    sd.confidence = 0.97
    sd.finalize()
    return sd


def generate_risky_refactor_diff() -> SemanticDiff:
    sd = SemanticDiff(
        header=DiffHeader(
            diff_id="sd-refactor-002",
            source_commit="c3d4e5f6a1b2",
            target_commit="d4e5f6a1b2c3",
            branch="refactor/payment-strategy",
            repository="legacy-ecommerce",
            author="refactor-agent",
        )
    )

    sd.add_syntactic_change(SyntacticChange(
        file_path="/src/payment/processor.py",
        diff_type=DiffType.MODIFICATION,
        lines_added=45, lines_removed=40, hunks=5,
        language="python", change_scope="module",
    ))
    sd.add_syntactic_change(SyntacticChange(
        file_path="/src/payment/strategies/credit_card.py",
        diff_type=DiffType.ADDITION,
        lines_added=85, lines_removed=0, hunks=3,
        language="python", change_scope="class",
        class_name="CreditCardStrategy",
    ))
    sd.add_syntactic_change(SyntacticChange(
        file_path="/src/payment/strategies/paypal.py",
        diff_type=DiffType.ADDITION,
        lines_added=72, lines_removed=0, hunks=3,
        language="python", change_scope="class",
        class_name="PayPalStrategy",
    ))

    sd.set_intent(BehavioralIntent(
        intent_type=IntentType.REFACTORING,
        description="Replace conditional payment dispatch with strategy pattern",
        motivation="Reduce cyclomatic complexity and make adding new payment methods easier",
        expected_behavior="Same payment behavior, decoupled dispatch logic",
        previous_behavior="Single function with if/elif chain for each payment method",
        backward_compatible=True,
        affected_interfaces=["process_payment() signature preserved"],
        migration_required=False,
    ))

    sd.add_invariant(AffectedInvariant(
        invariant_type=InvariantType.INTERFACE_CONTRACT,
        description="process_payment() accepts (method, amount) and returns TransactionResult",
        location="/src/payment/processor.py",
        status="preserved",
        confidence=0.92,
    ))

    sd.add_invariant(AffectedInvariant(
        invariant_type=InvariantType.BUSINESS_RULE,
        description="All payment methods validate amount > 0 before processing",
        location="/src/payment/strategies/*.py",
        status="preserved",
        confidence=0.88,
    ))

    sd.set_architectural_impact(ArchitecturalImpact(
        impact_level=ImpactLevel.MEDIUM,
        affected_subsystems=["payment", "checkout"],
        dependency_changes=["Old monolithic processor.py -> 4 strategy files"],
        coupling_change=-0.25,
        cohesion_change=0.35,
        complexity_delta=-16,
        architecture_description="Migrated from conditional dispatch to strategy pattern. "
                                 "Each payment method is now independently testable.",
    ))

    sd.set_risk(RiskScore(
        overall=RiskLevel.MEDIUM,
        regression_risk=RiskLevel.HIGH,
        security_risk=RiskLevel.LOW,
        performance_risk=RiskLevel.LOW,
        compatibility_risk=RiskLevel.MEDIUM,
        deploy_risk=RiskLevel.MEDIUM,
        rollback_difficulty=RiskLevel.MEDIUM,
        risk_factors=[
            "Core payment processing refactored",
            "3 new files, 1 heavily modified",
            "Integration tests needed before deploy",
            "Backward compatibility layer required for external callers",
        ],
        risk_score_numeric=0.55,
    ))

    sd.set_verification(VerificationResult(
        status=VerificationStatus.PASSED,
        tests_run=25, tests_passed=25, tests_failed=0,
        coverage_percent=88.0,
        static_analysis_passed=True,
        type_checks_passed=True,
        lint_passed=True,
        verification_gaps=["No security audit of new strategy dispatch"],
    ))

    sd.set_rollback(RollbackStrategy(
        strategy="patch_inverse",
        complexity="moderate",
        estimated_time_minutes=15,
        steps=[
            "git revert <merge-commit>",
            "Restore original processor.py",
            "Remove strategies/ directory",
            "Verify all payment tests pass",
        ],
    ))

    sd.confidence = 0.78
    sd.finalize()
    return sd


def generate_security_fix_diff() -> SemanticDiff:
    sd = SemanticDiff(
        header=DiffHeader(
            diff_id="sd-security-003",
            source_commit="e5f6a1b2c3d4",
            target_commit="f6a1b2c3d4e5",
            branch="fix/sql-injection",
            repository="legacy-ecommerce",
        )
    )

    sd.add_syntactic_change(SyntacticChange(
        file_path="/src/users/auth.py",
        diff_type=DiffType.MODIFICATION,
        lines_added=2, lines_removed=2, hunks=1,
            old_code_preview='cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")',
            new_code_preview='cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))',
        language="python", change_scope="function",
        function_name="get_user",
    ))

    sd.set_intent(BehavioralIntent(
        intent_type=IntentType.SECURITY,
        description="Fix SQL injection vulnerability in get_user()",
        motivation="user_id parameter was interpolated directly into SQL string, allowing injection",
        expected_behavior="Parameterized query prevents SQL injection",
        previous_behavior="String interpolation allowed malicious input to modify query",
        backward_compatible=True,
    ))

    sd.add_invariant(AffectedInvariant(
        invariant_type=InvariantType.SECURITY_POLICY,
        description="All database queries must use parameterized statements",
        location="/src/users/auth.py",
        status="restored",
        confidence=0.99,
    ))

    sd.set_architectural_impact(ArchitecturalImpact(
        impact_level=ImpactLevel.LOW,
        complexity_delta=0,
    ))

    sd.set_risk(RiskScore(
        overall=RiskLevel.LOW,
        security_risk=RiskLevel.NONE,
        risk_score_numeric=0.05,
        risk_factors=["Minimal change, clear improvement"],
    ))

    sd.set_verification(VerificationResult(
        status=VerificationStatus.PASSED,
        tests_run=15, tests_passed=15,
        static_analysis_passed=True,
        verification_gaps=["No SQL injection penetration test in CI"],
    ))

    sd.set_rollback(RollbackStrategy(
        strategy="git_revert", complexity="simple",
        estimated_time_minutes=1,
        steps=["git revert HEAD"],
    ))

    sd.confidence = 0.99
    sd.finalize()
    return sd


def generate_all_examples(output_dir: str = "lyme-output/standards/semantic-diffs"):
    import json, os
    os.makedirs(output_dir, exist_ok=True)

    examples = [
        ("bug-fix-semantic-diff.json", generate_bug_fix_diff(), "Bug fix: Pagination off-by-one"),
        ("risky-refactor-semantic-diff.json", generate_risky_refactor_diff(), "Refactor: Payment strategy pattern"),
        ("security-fix-semantic-diff.json", generate_security_fix_diff(), "Security fix: SQL injection"),
    ]

    from .renderer import MarkdownRenderer, HTMLRenderer
    md_renderer = MarkdownRenderer()
    html_renderer = HTMLRenderer()

    for name, sd, desc in examples:
        with open(os.path.join(output_dir, name), "w") as f:
            f.write(sd.to_json())
        md_name = name.replace(".json", ".md")
        with open(os.path.join(output_dir, md_name), "w") as f:
            f.write(md_renderer.render_semantic_diff(sd))
        html_name = name.replace(".json", ".html")
        with open(os.path.join(output_dir, html_name), "w") as f:
            f.write(html_renderer.render_semantic_diff(sd))
        print(f"Wrote {output_dir}/{name}, {md_name}, {html_name}")

    return examples
