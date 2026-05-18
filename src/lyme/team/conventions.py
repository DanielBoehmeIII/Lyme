from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .knowledge import team_knowledge


@dataclass
class ConventionEntry:
    name: str
    pattern: str
    description: str
    coverage: float = 0.0
    violations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "pattern": self.pattern,
            "description": self.description,
            "coverage": self.coverage,
            "violations": self.violations,
        }


class TeamConventions:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._knowledge = team_knowledge

    def list_conventions(self) -> List[Dict[str, Any]]:
        return self._knowledge.conventions()

    def add_convention(self, name: str, pattern: str, description: str) -> None:
        self._knowledge.record_convention(name, pattern, description)

    def add_standard(self, name: str, description: str, files: Optional[List[str]] = None) -> None:
        self._knowledge.record_standard(name, description, files or [])

    def add_fact(self, key: str, fact: str) -> None:
        self._knowledge.record_fact(key, fact)

    def report(self) -> str:
        lines = [f"## Team Knowledge\n"]
        conventions = self._knowledge.conventions()
        if conventions:
            lines.append(f"### Conventions ({len(conventions)})\n")
            for c in conventions:
                lines.append(f"- **{c['name']}**: {c['description']}")
            lines.append("")
        standards = self._knowledge.standards()
        if standards:
            lines.append(f"### Architectural Standards ({len(standards)})\n")
            for s in standards:
                lines.append(f"- **{s['name']}**: {s['description']}")
            lines.append("")
        facts = self._knowledge.facts()
        if facts:
            lines.append(f"### Repo Facts ({len(facts)})\n")
            for k, v in facts.items():
                fact = v["fact"] if isinstance(v, dict) else v
                lines.append(f"- **{k}**: {fact}")
            lines.append("")
        all_keys = self._knowledge.list_keys()
        if not conventions and not standards and not facts:
            lines.append("No team knowledge yet. Add conventions with `lyme team convention add`.")
        return "\n".join(lines)
