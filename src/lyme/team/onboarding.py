from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .knowledge import team_knowledge


@dataclass
class OnboardingSummary:
    repo_name: str = ""
    structure: str = ""
    key_commands: List[str] = field(default_factory=list)
    team_standards: List[str] = field(default_factory=list)
    conventions: List[str] = field(default_factory=list)
    first_steps: List[str] = field(default_factory=list)
    known_facts: List[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [f"# Onboarding: {self.repo_name}\n"]
        lines.append(f"## Structure\n{self.structure}\n")
        if self.key_commands:
            lines.append("## Key Commands\n")
            for c in self.key_commands:
                lines.append(f"- `{c}`")
            lines.append("")
        if self.team_standards:
            lines.append("## Team Standards\n")
            for s in self.team_standards:
                lines.append(f"- {s}")
            lines.append("")
        if self.conventions:
            lines.append("## Conventions\n")
            for c in self.conventions:
                lines.append(f"- {c}")
            lines.append("")
        if self.first_steps:
            lines.append("## First Steps\n")
            for i, s in enumerate(self.first_steps, 1):
                lines.append(f"{i}. {s}")
            lines.append("")
        if self.known_facts:
            lines.append("## Repo Knowledge\n")
            for f in self.known_facts:
                lines.append(f"- {f}")
            lines.append("")
        return "\n".join(lines)


class RepoOnboarding:
    def __init__(self, repo_path: str = "."):
        self._repo = Path(repo_path).resolve()
        self._knowledge = team_knowledge

    def generate(self) -> OnboardingSummary:
        summary = OnboardingSummary(repo_name=self._repo.name)
        summary.structure = self._describe_structure()
        summary.key_commands = self._discover_commands()
        summary.team_standards = self._get_standards()
        summary.conventions = self._get_conventions()
        summary.first_steps = self._suggest_first_steps()
        summary.known_facts = self._get_facts()
        return summary

    def print_onboarding(self) -> None:
        summary = self.generate()
        print(summary.to_markdown())

    def _describe_structure(self) -> str:
        dirs = []
        for d in sorted(self._repo.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and d.name != "__pycache__":
                dirs.append(d.name)
        top = "\n".join(f"- {d}/" for d in dirs[:12])
        return f"Top-level directories ({len(dirs)}):\n{top}"

    def _discover_commands(self) -> List[str]:
        commands = []
        try:
            result = subprocess.run(
                [sys.executable or "python3", "-m", "lyme", "--help"],
                capture_output=True, text=True, timeout=10,
                cwd=str(self._repo),
            )
            for line in result.stdout.splitlines():
                if "lyme" in line and "}" not in line:
                    cmd = line.strip().split()[0] if line.strip() else ""
                    if cmd and cmd.startswith("lyme"):
                        commands.append(cmd)
        except Exception:
            pass
        pyproject = self._repo / "pyproject.toml"
        if pyproject.exists():
            commands.append("pytest")
        if (self._repo / "Makefile").exists():
            commands.append("make")
        return commands[:8]

    def _get_standards(self) -> List[str]:
        standards = self._knowledge.standards()
        return [f"{s['name']}: {s['description']}" for s in standards]

    def _get_conventions(self) -> List[str]:
        convs = self._knowledge.conventions()
        return [f"{c['name']}: {c['description']}" for c in convs]

    def _get_facts(self) -> List[str]:
        facts = self._knowledge.facts()
        return [f"{k}: {v['fact']}" if isinstance(v, dict) else v for k, v in facts.items()]

    def _suggest_first_steps(self) -> List[str]:
        return [
            "Run `lyme start` for daily startup",
            "Run `lyme session start` to begin a tracked session",
            "Run `lyme intel all` for repo intelligence",
            "Run `lyme rhythm report` to build your developer profile",
        ]


import sys

repo_onboarding = RepoOnboarding()
