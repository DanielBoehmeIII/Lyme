from __future__ import annotations
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ChangeEntry:
    file_path: str
    change_type: str
    insertions: int = 0
    deletions: int = 0
    preview: str = ""
    risk: str = "low"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "change_type": self.change_type,
            "insertions": self.insertions,
            "deletions": self.deletions,
            "risk": self.risk,
        }


@dataclass
class ChangePreview:
    entries: List[ChangeEntry] = field(default_factory=list)
    total_insertions: int = 0
    total_deletions: int = 0
    files_changed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entries": [e.to_dict() for e in self.entries],
            "total_insertions": self.total_insertions,
            "total_deletions": self.total_deletions,
            "files_changed": self.files_changed,
        }

    def to_markdown(self) -> str:
        if not self.entries:
            return "No changes to preview."
        lines = [f"## Change Preview\n"]
        lines.append(f"**{self.files_changed} files changed**: +{self.total_insertions}/-{self.total_deletions}\n")
        for e in self.entries:
            risk_icon = "🔴" if e.risk == "high" else "🟡" if e.risk == "medium" else "🟢"
            lines.append(f"{risk_icon} **{e.file_path}** ({e.change_type})")
            lines.append(f"   +{e.insertions}/-{e.deletions} lines")
            if e.preview:
                lines.append(f"   ```\n   {e.preview[:200]}\n   ```")
        return "\n".join(lines)


def create_preview(repo_path: str = ".") -> ChangePreview:
    preview = ChangePreview()
    try:
        result = subprocess.run(
            ["git", "diff", "--stat"],
            capture_output=True, text=True, timeout=10,
            cwd=Path(repo_path).resolve(),
        )
        for line in result.stdout.splitlines():
            if "changed" in line:
                parts = line.split()
                for p in parts:
                    if p.startswith("+") and p[1:].isdigit():
                        preview.total_insertions += int(p[1:])
                    elif p.startswith("-") and p[1:].isdigit():
                        preview.total_deletions += int(p[1:])
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "diff", "--name-status"],
            capture_output=True, text=True, timeout=10,
            cwd=Path(repo_path).resolve(),
        )
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                status, filepath = parts
                change_type = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed"}.get(status, "modified")
                risk = "low"
                if change_type == "deleted":
                    risk = "high"
                elif change_type == "modified" and filepath.endswith((".py", ".ts", ".js")):
                    risk = "medium"
                entry = ChangeEntry(
                    file_path=filepath,
                    change_type=change_type,
                    risk=risk,
                )
                preview.entries.append(entry)
    except Exception:
        pass

    preview.files_changed = len(preview.entries)
    return preview
