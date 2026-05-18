from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import time
from pathlib import Path


def sanitize_for_public(text: str) -> str:
    sensitive = [
        ("/home/", "~/"),
        ("/Users/", "~/"),
        ("/private/var", "/var"),
        ("api_key", "***"),
        ("token", "***"),
        ("secret", "***"),
        ("password", "***"),
        ("credential", "***"),
        ("authorization", "***"),
    ]
    for old, new in sensitive:
        text = text.replace(old, new)
    import re
    text = re.sub(r'[0-9a-f]{8,}-[0-9a-f]{4,}-[0-9a-f]{4,}-[0-9a-f]{4,}-[0-9a-f]{12,}', '<UUID>', text)
    text = re.sub(r'gh[pousr]_[A-Za-z0-9]{36,}', '<TOKEN>', text)
    return text


@dataclass
class PublicBenchmarkReport:
    title: str
    version: str
    date: str
    summary: str
    metrics_summary: Dict[str, float]
    credibility_score: float
    evidence_count: int
    sanitized_results: List[dict]
    methodology: str
    limitations: List[str]
    reproducibility: str

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "version": self.version,
            "date": self.date,
            "summary": self.summary,
            "metrics_summary": self.metrics_summary,
            "credibility_score": round(self.credibility_score, 3),
            "evidence_count": self.evidence_count,
            "methodology": self.methodology,
            "limitations": self.limitations,
            "reproducibility": self.reproducibility,
        }

    def save_public_json(self, path: Path):
        clean = self.to_dict()
        raw = json.dumps(clean)
        safe = sanitize_for_public(raw)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(safe)
        print(f"  Public-safe report: {path}")

    def print_summary(self):
        print(f"{'='*60}")
        print(f"  {self.title}")
        print(f"{'='*60}")
        print(f"  Version: {self.version}")
        print(f"  Date: {self.date}")
        print(f"  Credibility: {self.credibility_score:.0%}")
        print(f"  Evidence items: {self.evidence_count}")
        print(f"\n  Summary: {self.summary}")
        print(f"\n  Methodology: {self.methodology[:200]}...")
        if self.limitations:
            print(f"\n  Limitations:")
            for lim in self.limitations:
                print(f"    • {lim}")
        print(f"{'='*60}")
