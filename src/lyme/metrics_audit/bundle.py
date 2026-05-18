from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import time
from pathlib import Path


@dataclass
class EvidenceItem:
    metric_name: str
    result_value: float
    unit: str
    command_run: str
    output_summary: str
    exit_code: int
    timestamp: float
    repo_state: str
    valid: bool
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "result_value": self.result_value,
            "unit": self.unit,
            "command_run": self.command_run,
            "output_summary": self.output_summary[:300],
            "exit_code": self.exit_code,
            "timestamp": self.timestamp,
            "repo_state": self.repo_state,
            "valid": self.valid,
            "error": self.error,
        }


@dataclass
class EvidenceBundle:
    benchmark_name: str
    timestamp: str
    items: List[EvidenceItem]
    summary: Dict[str, float]
    passed: int
    failed: int
    total: int

    def to_dict(self) -> dict:
        return {
            "benchmark_name": self.benchmark_name,
            "timestamp": self.timestamp,
            "items": [i.to_dict() for i in self.items],
            "summary": self.summary,
            "passed": self.passed,
            "failed": self.failed,
            "total": self.total,
        }

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))
        print(f"  Evidence bundle saved: {path}")


class EvidenceCollector:
    def __init__(self):
        self.items: List[EvidenceItem] = []

    def add(self, metric_name: str, value: float, unit: str, command: str,
            output: str, exit_code: int, repo: str = "current", valid: bool = True,
            error: Optional[str] = None):
        self.items.append(EvidenceItem(
            metric_name=metric_name, result_value=value, unit=unit,
            command_run=command, output_summary=output[:300],
            exit_code=exit_code, timestamp=time.time(),
            repo_state=repo, valid=valid, error=error,
        ))

    def bundle(self, name: str = "benchmark") -> EvidenceBundle:
        passed = sum(1 for i in self.items if i.valid)
        failed = sum(1 for i in self.items if not i.valid)
        summary = {
            "avg_value": sum(i.result_value for i in self.items) / max(len(self.items), 1),
            "pass_rate": passed / max(len(self.items), 1),
            "total_items": len(self.items),
        }
        return EvidenceBundle(
            benchmark_name=name,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            items=self.items,
            summary=summary,
            passed=passed,
            failed=failed,
            total=len(self.items),
        )


evidence_collector = EvidenceCollector()
