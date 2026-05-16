from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
import json
import time
import uuid


class NodeType(str, Enum):
    CLAIM = "claim"
    CODE_CHANGE = "code_change"
    TEST = "test"
    RUNTIME_TRACE = "runtime_trace"
    STATIC_ANALYSIS = "static_analysis"
    TYPE_CHECK = "type_check"
    USER_APPROVAL = "user_approval"
    BENCHMARK_RESULT = "benchmark_result"
    ROLLBACK_EVIDENCE = "rollback_evidence"


class EvidenceType(str, Enum):
    PASSED_TEST = "passed_test"
    FAILED_TEST = "failed_test"
    COVERAGE_REPORT = "coverage_report"
    LINT_PASS = "lint_pass"
    TYPE_CHECK_PASS = "type_check_pass"
    TYPE_CHECK_FAIL = "type_check_fail"
    STATIC_ANALYSIS_PASS = "static_analysis_pass"
    STATIC_ANALYSIS_WARN = "static_analysis_warn"
    RUNTIME_SUCCESS = "runtime_success"
    RUNTIME_ERROR = "runtime_error"
    USER_APPROVED = "user_approved"
    USER_REJECTED = "user_rejected"
    BENCHMARK_PASS = "benchmark_pass"
    BENCHMARK_REGRESSION = "benchmark_regression"
    ROLLBACK_CONFIRMED = "rollback_confirmed"
    ROLLBACK_NEEDED = "rollback_needed"
    CLAIM_VERIFIED = "claim_verified"
    CLAIM_REFUTED = "claim_refuted"
    CODE_REVIEWED = "code_reviewed"
    BUILD_PASSED = "build_passed"
    BUILD_FAILED = "build_failed"


@dataclass
class VerificationNode:
    id: str
    node_type: NodeType
    label: str
    description: str = ""
    timestamp: float = 0.0
    metadata: Dict = field(default_factory=dict)
    evidence: List[EvidenceType] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "label": self.label,
            "description": self.description,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
            "evidence": [e.value for e in self.evidence],
            "confidence": self.confidence,
        }


@dataclass
class VerificationEdge:
    source_id: str
    target_id: str
    relationship: str
    evidence: List[EvidenceType] = field(default_factory=list)
    strength: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "evidence": [e.value for e in self.evidence],
            "strength": self.strength,
        }


@dataclass
class Claim:
    id: str
    statement: str
    source: str
    confidence: float = 0.0
    verified: Optional[bool] = None
    verification_evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "statement": self.statement,
            "source": self.source,
            "confidence": self.confidence,
            "verified": self.verified,
            "verification_evidence": self.verification_evidence,
            "counter_evidence": self.counter_evidence,
        }


@dataclass
class CodeChange:
    id: str
    file_path: str
    diff: str
    author: str = ""
    risk_score: float = 0.0
    verification_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "file_path": self.file_path,
            "diff": self.diff[:200],
            "author": self.author,
            "risk_score": self.risk_score,
            "verification_ids": self.verification_ids,
        }


@dataclass
class TestResult:
    id: str
    test_name: str
    passed: bool
    duration_ms: float = 0.0
    coverage_pct: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "test_name": self.test_name,
            "passed": self.passed,
            "duration_ms": self.duration_ms,
            "coverage_pct": self.coverage_pct,
            "error_message": self.error_message,
        }


@dataclass
class RuntimeTrace:
    id: str
    operation: str
    success: bool
    duration_ms: float = 0.0
    error: str = ""
    trace_data: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "operation": self.operation,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "trace_data": self.trace_data,
        }


@dataclass
class StaticAnalysisResult:
    id: str
    tool: str
    issues_count: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    passed: bool = False
    details: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tool": self.tool,
            "issues_count": self.issues_count,
            "warnings_count": self.warnings_count,
            "errors_count": self.errors_count,
            "passed": self.passed,
            "details": self.details[:10],
        }


@dataclass
class TypeCheckResult:
    id: str
    tool: str
    passed: bool
    errors_count: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "tool": self.tool,
            "passed": self.passed,
            "errors_count": self.errors_count,
            "errors": self.errors[:5],
        }


@dataclass
class UserApproval:
    id: str
    approver: str
    approved: bool
    reason: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "approver": self.approver,
            "approved": self.approved,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }


@dataclass
class BenchmarkResult:
    id: str
    benchmark_name: str
    score: float
    baseline_score: float = 0.0
    regression: bool = False
    metrics: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "benchmark_name": self.benchmark_name,
            "score": self.score,
            "baseline_score": self.baseline_score,
            "regression": self.regression,
            "metrics": self.metrics,
        }


@dataclass
class RollbackEvidence:
    id: str
    rollback_reason: str
    success: bool
    prior_state_ref: str = ""
    recovery_time_ms: float = 0.0
    lessons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "rollback_reason": self.rollback_reason,
            "success": self.success,
            "prior_state_ref": self.prior_state_ref,
            "recovery_time_ms": self.recovery_time_ms,
            "lessons": self.lessons,
        }


@dataclass
class VerificationReport:
    action_id: str
    action_description: str
    nodes: List[VerificationNode]
    edges: List[VerificationEdge]
    claims: List[Claim]
    what_was_verified: List[str]
    how_verified: List[str]
    unverified: List[str]
    supporting_evidence: List[str]
    contradicting_evidence: List[str]
    overall_confidence: float = 0.0
    verdict: str = "unknown"
    timestamp: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "action_id": self.action_id,
            "action_description": self.action_description,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "claims": [c.to_dict() for c in self.claims],
            "what_was_verified": self.what_was_verified,
            "how_verified": self.how_verified,
            "unverified": self.unverified,
            "supporting_evidence": self.supporting_evidence,
            "contradicting_evidence": self.contradicting_evidence,
            "overall_confidence": self.overall_confidence,
            "verdict": self.verdict,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        lines = []
        lines.append(f"# Verification Report: {self.action_id}")
        lines.append(f"")
        lines.append(f"**Action**: {self.action_description}")
        lines.append(f"**Verdict**: {self.verdict.upper()}")
        lines.append(f"**Confidence**: {self.overall_confidence:.2f}")
        lines.append(f"")
        lines.append(f"## What Was Verified")
        for item in self.what_was_verified:
            lines.append(f"- ✅ {item}")
        lines.append(f"")
        lines.append(f"## How It Was Verified")
        for item in self.how_verified:
            lines.append(f"- 🔍 {item}")
        lines.append(f"")
        lines.append(f"## What Remains Unverified")
        for item in self.unverified:
            lines.append(f"- ⚠️ {item}")
        lines.append(f"")
        lines.append(f"## Supporting Evidence")
        for item in self.supporting_evidence:
            lines.append(f"- ✅ {item}")
        lines.append(f"")
        if self.contradicting_evidence:
            lines.append(f"## Contradicting Evidence")
            for item in self.contradicting_evidence:
                lines.append(f"- ❌ {item}")
            lines.append(f"")
        lines.append(f"## Graph Summary")
        lines.append(f"- **Nodes**: {len(self.nodes)} ({', '.join(set(n.node_type.value for n in self.nodes))})")
        lines.append(f"- **Edges**: {len(self.edges)}")
        lines.append(f"- **Claims**: {len(self.claims)}")
        return "\n".join(lines)


class VerificationGraph:
    def __init__(self):
        self._nodes: Dict[str, VerificationNode] = {}
        self._edges: List[VerificationEdge] = []
        self._claims: Dict[str, Claim] = {}
        self._reports: Dict[str, VerificationReport] = {}

    def add_node(self, node: VerificationNode) -> str:
        self._nodes[node.id] = node
        return node.id

    def add_edge(self, edge: VerificationEdge) -> None:
        self._edges.append(edge)

    def add_claim(self, claim: Claim) -> str:
        self._claims[claim.id] = claim
        return claim.id

    def get_node(self, node_id: str) -> Optional[VerificationNode]:
        return self._nodes.get(node_id)

    def get_edges_from(self, node_id: str) -> List[VerificationEdge]:
        return [e for e in self._edges if e.source_id == node_id]

    def get_edges_to(self, node_id: str) -> List[VerificationEdge]:
        return [e for e in self._edges if e.target_id == node_id]

    def build_action_verification(
        self,
        action_id: str,
        action_description: str,
        claims: List[Claim],
        changes: List[CodeChange],
        test_results: List[TestResult],
        traces: List[RuntimeTrace],
        static_results: List[StaticAnalysisResult],
        type_results: List[TypeCheckResult],
        approvals: List[UserApproval],
        benchmark_results: List[BenchmarkResult],
        rollback_evidence: List[RollbackEvidence],
    ) -> VerificationReport:
        for claim in claims:
            self.add_claim(claim)
            claim_node = VerificationNode(
                id=f"{action_id}_claim_{claim.id}",
                node_type=NodeType.CLAIM,
                label=claim.statement[:60],
                description=claim.statement,
                timestamp=time.time(),
                confidence=claim.confidence,
            )
            self.add_node(claim_node)

        for change in changes:
            change_node = VerificationNode(
                id=change.id,
                node_type=NodeType.CODE_CHANGE,
                label=f"Change: {change.file_path}",
                description=f"Risk: {change.risk_score:.2f}",
                timestamp=time.time(),
                metadata={"file": change.file_path, "risk": change.risk_score},
            )
            self.add_node(change_node)
            for c in claims:
                self.add_edge(VerificationEdge(
                    source_id=change.id,
                    target_id=f"{action_id}_claim_{c.id}",
                    relationship="addresses_claim",
                    strength=0.7,
                ))

        evidence_list: List[EvidenceType] = []

        for tr in test_results:
            tn = VerificationNode(
                id=tr.id,
                node_type=NodeType.TEST,
                label=f"Test: {tr.test_name}",
                description=f"Passed: {tr.passed}, Coverage: {tr.coverage_pct}%",
                timestamp=time.time(),
                evidence=[EvidenceType.PASSED_TEST if tr.passed else EvidenceType.FAILED_TEST],
                confidence=1.0 if tr.passed else 0.0,
                metadata={"duration_ms": tr.duration_ms, "coverage": tr.coverage_pct},
            )
            self.add_node(tn)
            evidence_list.append(EvidenceType.PASSED_TEST if tr.passed else EvidenceType.FAILED_TEST)
            for change in changes:
                self.add_edge(VerificationEdge(
                    source_id=tr.id, target_id=change.id,
                    relationship="tests_change", strength=tr.coverage_pct / 100.0,
                ))

        for trace in traces:
            rn = VerificationNode(
                id=trace.id,
                node_type=NodeType.RUNTIME_TRACE,
                label=f"Runtime: {trace.operation}",
                description=f"Success: {trace.success}",
                timestamp=time.time(),
                evidence=[EvidenceType.RUNTIME_SUCCESS if trace.success else EvidenceType.RUNTIME_ERROR],
                confidence=1.0 if trace.success else 0.0,
            )
            self.add_node(rn)
            evidence_list.append(EvidenceType.RUNTIME_SUCCESS if trace.success else EvidenceType.RUNTIME_ERROR)
            for change in changes:
                self.add_edge(VerificationEdge(
                    source_id=trace.id, target_id=change.id,
                    relationship="validates_behavior", strength=0.8,
                ))

        for sr in static_results:
            sn = VerificationNode(
                id=sr.id,
                node_type=NodeType.STATIC_ANALYSIS,
                label=f"Static: {sr.tool}",
                description=f"Passed: {sr.passed}, Issues: {sr.issues_count}",
                timestamp=time.time(),
                evidence=[EvidenceType.STATIC_ANALYSIS_PASS if sr.passed else EvidenceType.STATIC_ANALYSIS_WARN],
                confidence=0.9 if sr.passed else 0.3,
                metadata={"tool": sr.tool, "errors": sr.errors_count, "warnings": sr.warnings_count},
            )
            self.add_node(sn)
            evidence_list.append(EvidenceType.STATIC_ANALYSIS_PASS if sr.passed else EvidenceType.STATIC_ANALYSIS_WARN)
            for change in changes:
                self.add_edge(VerificationEdge(
                    source_id=sr.id, target_id=change.id,
                    relationship="analyzes_code", strength=0.7,
                ))

        for tcr in type_results:
            tcn = VerificationNode(
                id=tcr.id,
                node_type=NodeType.TYPE_CHECK,
                label=f"Type: {tcr.tool}",
                description=f"Passed: {tcr.passed}",
                timestamp=time.time(),
                evidence=[EvidenceType.TYPE_CHECK_PASS if tcr.passed else EvidenceType.TYPE_CHECK_FAIL],
                confidence=1.0 if tcr.passed else 0.0,
            )
            self.add_node(tcn)
            evidence_list.append(EvidenceType.TYPE_CHECK_PASS if tcr.passed else EvidenceType.TYPE_CHECK_FAIL)
            for change in changes:
                self.add_edge(VerificationEdge(
                    source_id=tcr.id, target_id=change.id,
                    relationship="type_checks", strength=0.8,
                ))

        for approval in approvals:
            an = VerificationNode(
                id=approval.id,
                node_type=NodeType.USER_APPROVAL,
                label=f"Approval: {approval.approver}",
                description=f"Approved: {approval.approved}",
                timestamp=approval.timestamp,
                evidence=[EvidenceType.USER_APPROVED if approval.approved else EvidenceType.USER_REJECTED],
                confidence=1.0 if approval.approved else 0.0,
            )
            self.add_node(an)
            evidence_list.append(EvidenceType.USER_APPROVED if approval.approved else EvidenceType.USER_REJECTED)

        for br in benchmark_results:
            bn = VerificationNode(
                id=br.id,
                node_type=NodeType.BENCHMARK_RESULT,
                label=f"Benchmark: {br.benchmark_name}",
                description=f"Score: {br.score:.2f}, Baseline: {br.baseline_score:.2f}",
                timestamp=time.time(),
                evidence=[EvidenceType.BENCHMARK_PASS if not br.regression else EvidenceType.BENCHMARK_REGRESSION],
                confidence=0.8 if not br.regression else 0.2,
            )
            self.add_node(bn)
            evidence_list.append(EvidenceType.BENCHMARK_PASS if not br.regression else EvidenceType.BENCHMARK_REGRESSION)
            for change in changes:
                self.add_edge(VerificationEdge(
                    source_id=br.id, target_id=change.id,
                    relationship="measures_performance", strength=0.6,
                ))

        for rb in rollback_evidence:
            rbn = VerificationNode(
                id=rb.id,
                node_type=NodeType.ROLLBACK_EVIDENCE,
                label=f"Rollback: {rb.rollback_reason[:40]}",
                description=f"Success: {rb.success}",
                timestamp=time.time(),
                evidence=[EvidenceType.ROLLBACK_CONFIRMED if rb.success else EvidenceType.ROLLBACK_NEEDED],
                confidence=0.9 if rb.success else 0.5,
            )
            self.add_node(rbn)
            evidence_list.append(EvidenceType.ROLLBACK_CONFIRMED if rb.success else EvidenceType.ROLLBACK_NEEDED)

        report = self._build_report(
            action_id, action_description, claims, changes,
            test_results, traces, static_results, type_results,
            approvals, benchmark_results, rollback_evidence,
            evidence_list,
        )
        self._reports[action_id] = report
        return report

    def _build_report(
        self, action_id, action_description, claims, changes,
        test_results, traces, static_results, type_results,
        approvals, benchmark_results, rollback_evidence,
        evidence_list,
    ) -> VerificationReport:
        what_verified = []
        how_verified = []
        unverified = []
        supporting = []
        contradicting = []

        if test_results:
            passed = [t for t in test_results if t.passed]
            failed = [t for t in test_results if not t.passed]
            what_verified.append(f"{len(test_results)} test(s) executed")
            how_verified.append(f"Test suite: {', '.join(t.test_name for t in test_results[:3])}")
            if passed:
                supporting.append(f"{len(passed)}/{len(test_results)} tests passed")
            if failed:
                contradicting.append(f"{len(failed)}/{len(test_results)} tests failed: {failed[0].error_message[:80]}")

        if static_results:
            passed_sa = [s for s in static_results if s.passed]
            what_verified.append(f"Static analysis via {', '.join(s.tool for s in static_results)}")
            how_verified.append(f"Static analysis tools ran: {', '.join(s.tool for s in static_results)}")
            if passed_sa:
                supporting.append("Static analysis passed")
            else:
                for s in static_results:
                    if s.errors_count > 0 or s.warnings_count > 0:
                        contradicting.append(f"{s.tool}: {s.errors_count} errors, {s.warnings_count} warnings")

        if type_results:
            passed_tc = [t for t in type_results if t.passed]
            what_verified.append(f"Type checking via {', '.join(t.tool for t in type_results)}")
            how_verified.append(f"Type check tools: {', '.join(t.tool for t in type_results)}")
            if passed_tc:
                supporting.append("Type checks passed")
            else:
                for t in type_results:
                    if not t.passed:
                        contradicting.append(f"Type check failed ({t.tool}): {t.errors[0][:80] if t.errors else 'unknown'}")

        if traces:
            successful = [t for t in traces if t.success]
            what_verified.append(f"Runtime verification: {len(traces)} operation(s)")
            how_verified.append(f"Runtime trace of {', '.join(t.operation for t in traces[:3])}")
            if successful:
                supporting.append(f"{len(successful)}/{len(traces)} runtime operations succeeded")
            failed_traces = [t for t in traces if not t.success]
            if failed_traces:
                contradicting.append(f"{len(failed_traces)} runtime failure(s): {failed_traces[0].error[:80]}")

        if approvals:
            approved = [a for a in approvals if a.approved]
            what_verified.append(f"{len(approvals)} user approval(s)")
            how_verified.append(f"User approval from: {', '.join(a.approver for a in approvals)}")
            if approved:
                supporting.append(f"{len(approved)}/{len(approvals)} approvals granted")
            rejected = [a for a in approvals if not a.approved]
            if rejected:
                contradicting.append(f"{len(rejected)} approval(s) denied")

        if benchmark_results:
            regressions = [b for b in benchmark_results if b.regression]
            what_verified.append(f"{len(benchmark_results)} benchmark(s)")
            how_verified.append(f"Benchmark: {', '.join(b.benchmark_name for b in benchmark_results[:3])}")
            if regressions:
                contradicting.append(f"{len(regressions)} benchmark regression(s)")
            else:
                supporting.append("No benchmark regressions")

        if rollback_evidence:
            what_verified.append("Rollback capability verified")
            for rb in rollback_evidence:
                if rb.success:
                    supporting.append(f"Rollback successful: {rb.rollback_reason}")
                else:
                    contradicting.append(f"Rollback failed: {rb.rollback_reason}")

        verified_count = len([e for e in evidence_list if e in (
            EvidenceType.PASSED_TEST, EvidenceType.STATIC_ANALYSIS_PASS,
            EvidenceType.TYPE_CHECK_PASS, EvidenceType.RUNTIME_SUCCESS,
            EvidenceType.USER_APPROVED, EvidenceType.BENCHMARK_PASS,
            EvidenceType.ROLLBACK_CONFIRMED, EvidenceType.CLAIM_VERIFIED,
        )])
        total_evidence = len(evidence_list) or 1
        confidence = verified_count / total_evidence

        if not test_results and not traces:
            unverified.append("No runtime verification performed")
        if not static_results:
            unverified.append("No static analysis performed")
        if not type_results:
            unverified.append("No type checking performed")
        if not benchmark_results:
            unverified.append("No benchmark comparison performed")
        if not rollback_evidence:
            unverified.append("Rollback path not verified")
        for claim in claims:
            if claim.verified is None:
                unverified.append(f"Claim unverified: {claim.statement[:60]}")
            elif not claim.verified:
                contradicting.append(f"Claim refuted: {claim.statement[:60]}")

        if len(contradicting) > 0 and confidence >= 0.5:
            confidence = max(0.1, confidence - 0.2 * len(contradicting))

        verdict = "verified" if confidence >= 0.7 and len(contradicting) == 0 else \
                  "partially_verified" if confidence >= 0.4 else \
                  "unverified" if confidence < 0.3 else \
                  "contested"

        return VerificationReport(
            action_id=action_id,
            action_description=action_description,
            nodes=list(self._nodes.values()),
            edges=self._edges,
            claims=claims,
            what_was_verified=what_verified,
            how_verified=how_verified,
            unverified=unverified,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            overall_confidence=round(confidence, 3),
            verdict=verdict,
            timestamp=time.time(),
        )

    def get_report(self, action_id: str) -> Optional[VerificationReport]:
        return self._reports.get(action_id)

    def get_all_reports(self) -> List[VerificationReport]:
        return list(self._reports.values())

    def to_dict(self) -> Dict:
        return {
            "nodes": {k: v.to_dict() for k, v in self._nodes.items()},
            "edges": [e.to_dict() for e in self._edges],
            "reports": {k: v.to_dict() for k, v in self._reports.items()},
        }

    def render_cli(self, report: VerificationReport) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append(f"  VERIFICATION GRAPH — {report.action_id}")
        lines.append("=" * 70)
        lines.append(f"  Action:     {report.action_description}")
        lines.append(f"  Verdict:    {report.verdict.upper()}")
        lines.append(f"  Confidence: {report.overall_confidence:.2f}")
        lines.append(f"  Timestamp:  {time.ctime(report.timestamp)}")
        lines.append("-" * 70)

        if report.what_was_verified:
            lines.append("  ✓ What Was Verified:")
            for item in report.what_was_verified:
                lines.append(f"    • {item}")

        if report.how_verified:
            lines.append("  🔍 How It Was Verified:")
            for item in report.how_verified:
                lines.append(f"    • {item}")

        if report.unverified:
            lines.append("  ⚠ What Remains Unverified:")
            for item in report.unverified:
                lines.append(f"    • {item}")

        if report.supporting_evidence:
            lines.append("  ✅ Supporting Evidence:")
            for item in report.supporting_evidence:
                lines.append(f"    • {item}")

        if report.contradicting_evidence:
            lines.append("  ❌ Contradicting Evidence:")
            for item in report.contradicting_evidence:
                lines.append(f"    • {item}")

        lines.append("-" * 70)
        lines.append(f"  Nodes: {len(report.nodes)} | Edges: {len(report.edges)} | Claims: {len(report.claims)}")
        lines.append("=" * 70)
        return "\n".join(lines)
