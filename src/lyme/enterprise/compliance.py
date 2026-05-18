"""Compliance — exports for SOC2, GDPR, and audit requirements."""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ComplianceExport:
    version: str = "1.0.0"
    generated_at: float = 0.0
    report_type: str = "audit"
    data: Dict[str, Any] = field(default_factory=dict)

    def to_json(self, path: str) -> None:
        self.generated_at = time.time()
        Path(path).write_text(json.dumps({
            "version": self.version,
            "generated_at": self.generated_at,
            "report_type": self.report_type,
            "data": self.data,
        }, indent=2))

    @classmethod
    def gdpr_report(cls, user_id: str, actions: List[Dict]) -> "ComplianceExport":
        return cls(
            report_type="gdpr",
            data={"user_id": user_id, "actions_count": len(actions), "actions": actions},
        )

    @classmethod
    def soc2_report(cls, audit_log: List[Dict]) -> "ComplianceExport":
        return cls(
            report_type="soc2",
            data={"total_entries": len(audit_log), "entries": audit_log[:1000]},
        )
