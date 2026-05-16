import json
import time
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from enum import Enum


class CIMode(str, Enum):
    ADVISORY = "advisory"
    BLOCKING = "blocking"
    RESEARCH_TELEMETRY = "research_telemetry"


@dataclass
class CIConfig:
    mode: str = CIMode.ADVISORY
    output_dir: str = "lyme-output/ci"
    publish_artifacts: bool = True
    run_governance: bool = True
    detect_verification_gaps: bool = True
    update_cognition: bool = True
    fail_on_blocking: bool = True
    max_risk_threshold: float = 0.7


@dataclass
class CIArtifact:
    id: str = ""
    type: str = ""
    format: str = "json"
    content: dict = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)


@dataclass
class CIAuditPublish:
    run_id: str = ""
    repository: str = ""
    commit: str = ""
    branch: str = ""
    mode: str = ""
    risk_score: float = 0.0
    policy_decision: str = "allow"
    artifacts: List[dict] = field(default_factory=list)
    summary: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class CIRunner:
    def __init__(self, config: Optional[CIConfig] = None):
        self.config = config or CIConfig()
        self._runs = 0

    def run(self, repo: str, commit: str, branch: str,
            pr_data: Optional[dict] = None) -> CIAuditPublish:
        self._runs += 1
        run_id = f"ci-{int(time.time())}-{self._runs}"

        from ..pr_intelligence.analyzer import PRAnalyzer
        analyzer = PRAnalyzer()

        if pr_data:
            report = analyzer.analyze(pr_data)
            risk_score = report.risk_score.get("score", 0) if report.risk_score else 0
            violations = report.invariant_violations if report.invariant_violations else []
            gaps = report.test_gaps if report.test_gaps else []
        else:
            risk_score = 0.0
            violations = []
            gaps = []

        policy_decision = self._apply_governance(risk_score, violations)

        artifacts = []
        trace_artifact = CIArtifact(
            id=f"{run_id}-trace",
            type="open_agent_trace",
            content=self._build_trace(repo, commit, branch, risk_score, policy_decision),
        )
        artifacts.append(trace_artifact.to_dict())
        trace_artifact.save(f"{self.config.output_dir}/{run_id}-trace.json")

        if risk_score > 0:
            diff_artifact = CIArtifact(
                id=f"{run_id}-semantic-diff",
                type="semantic_diff",
                content=self._build_diff(pr_data or {}, risk_score),
            )
            artifacts.append(diff_artifact.to_dict())
            diff_artifact.save(f"{self.config.output_dir}/{run_id}-semantic-diff.json")

        if violations:
            gov_artifact = CIArtifact(
                id=f"{run_id}-governance",
                type="governance_check",
                content={
                    "policy_decision": policy_decision,
                    "violations": violations,
                    "gaps": gaps,
                },
            )
            artifacts.append(gov_artifact.to_dict())
            gov_artifact.save(f"{self.config.output_dir}/{run_id}-governance.json")

        audit = CIAuditPublish(
            run_id=run_id,
            repository=repo,
            commit=commit,
            branch=branch,
            mode=self.config.mode.value,
            risk_score=risk_score,
            policy_decision=policy_decision,
            artifacts=artifacts,
            summary=self._build_summary(risk_score, policy_decision, violations, gaps),
        )

        audit_path = f"{self.config.output_dir}/{run_id}-audit.json"
        os.makedirs(self.config.output_dir, exist_ok=True)
        with open(audit_path, "w") as f:
            f.write(audit.to_json())
        print(f"[Lyme CI] Audit published: {audit_path}")

        return audit

    def _apply_governance(self, risk_score: float, violations: List[dict]) -> str:
        if self.config.mode == CIMode.BLOCKING:
            if risk_score >= self.config.max_risk_threshold:
                return "block"
            for v in violations:
                if v.get("severity") in ("high", "critical"):
                    return "block"
            return "allow"

        if self.config.mode == CIMode.ADVISORY:
            if risk_score >= self.config.max_risk_threshold:
                return "warn"
            for v in violations:
                if v.get("severity") in ("high", "critical"):
                    return "warn"
            return "allow"

        return "allow"

    def _build_trace(self, repo: str, commit: str, branch: str,
                     risk_score: float, decision: str) -> dict:
        return {
            "schema": "open-agent-trace-standard",
            "schema_version": "0.7.0",
            "trace_id": f"ci-{int(time.time())}",
            "header": {
                "agent": {"name": "lyme-ci-runner", "version": "0.7.0", "framework": "lyme"},
                "system": {"repo_name": repo},
            },
            "events": [
                {"type": "system", "metadata": {"action": "ci_run", "commit": commit, "branch": branch}},
                {"type": "metric", "metadata": {"risk_score": risk_score, "decision": decision}},
            ],
            "summary": {"status": "completed", "decision": decision},
        }

    def _build_diff(self, pr_data: dict, risk_score: float) -> dict:
        return {
            "header": {"diff_id": f"ci-diff-{int(time.time())}"},
            "risk": {"overall": "high" if risk_score >= 0.5 else "low", "score": risk_score},
            "syntactic_changes": [
                {"file_path": f.get("filename", ""), "lines_added": f.get("additions", 0),
                 "lines_removed": f.get("deletions", 0)}
                for f in pr_data.get("files", [])
            ],
        }

    def _build_summary(self, risk_score: float, decision: str,
                       violations: list, gaps: list) -> str:
        return (f"Lyme CI [{self.config.mode.value}]: risk={risk_score:.2f}, "
                f"decision={decision}, violations={len(violations)}, gaps={len(gaps)}")
