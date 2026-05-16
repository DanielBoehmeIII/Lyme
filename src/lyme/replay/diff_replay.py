import difflib
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path


@dataclass
class DiffFrame:
    timestamp: float = 0.0
    file_path: str = ""
    action: str = ""  # created, modified, deleted
    old_content: str = ""
    new_content: str = ""
    old_size: int = 0
    new_size: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    semantic_impact: str = "unknown"

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "file_path": self.file_path,
            "action": self.action,
            "old_size": self.old_size,
            "new_size": self.new_size,
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "semantic_impact": self.semantic_impact,
        }

    def unified_diff(self) -> str:
        old_lines = self.old_content.splitlines(keepends=True)
        new_lines = self.new_content.splitlines(keepends=True)
        return "".join(difflib.unified_diff(
            old_lines, new_lines,
            fromfile=f"a/{self.file_path}",
            tofile=f"b/{self.file_path}",
        ))


class DiffReplayer:
    def __init__(self):
        self._frames: Dict[str, List[DiffFrame]] = {}

    def capture_state(self, path: Path, previous_state: dict = None) -> dict:
        state = {}
        if path.is_dir():
            for f in sorted(path.rglob("*")):
                if f.is_file():
                    try:
                        state[str(f.relative_to(path))] = f.read_text()
                    except (UnicodeDecodeError, OSError):
                        state[str(f.relative_to(path))] = "[BINARY]"
        return state

    def compute_diffs(self, trace_id: str, before: dict, after: dict,
                      timestamp: float = 0) -> List[DiffFrame]:
        frames = []
        all_paths = set(before.keys()) | set(after.keys())

        for file_path in sorted(all_paths):
            old_content = before.get(file_path, "")
            new_content = after.get(file_path, "")

            if file_path not in before:
                frames.append(DiffFrame(
                    timestamp=timestamp,
                    file_path=file_path,
                    action="created",
                    old_content="",
                    new_content=new_content,
                    new_size=len(new_content),
                    lines_added=len(new_content.splitlines()),
                    semantic_impact="addition",
                ))
            elif file_path not in after:
                frames.append(DiffFrame(
                    timestamp=timestamp,
                    file_path=file_path,
                    action="deleted",
                    old_content=old_content,
                    new_content="",
                    old_size=len(old_content),
                    lines_removed=len(old_content.splitlines()),
                    semantic_impact="removal",
                ))
            elif old_content != new_content:
                old_lines = old_content.splitlines()
                new_lines = new_content.splitlines()
                matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
                added = sum(j2 - j1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag == "insert")
                removed = sum(i2 - i1 for tag, i1, i2, j1, j2 in matcher.get_opcodes() if tag == "delete")

                frames.append(DiffFrame(
                    timestamp=timestamp,
                    file_path=file_path,
                    action="modified",
                    old_content=old_content,
                    new_content=new_content,
                    old_size=len(old_content),
                    new_size=len(new_content),
                    lines_added=added,
                    lines_removed=removed,
                    semantic_impact=self._classify_semantic_impact(old_content, new_content),
                ))

        self._frames[trace_id] = frames
        return frames

    def _classify_semantic_impact(self, old: str, old_content: str = "",
                                   new_content: str = "") -> str:
        if not old and not new_content:
            return "none"
        if not old:
            return "addition"
        if not new_content:
            return "deletion"

        old_lines = set(old.splitlines())
        new_lines = set(new_content.splitlines())

        added_keywords = ["def ", "class ", "import ", "from "]
        for line in new_lines - old_lines:
            for kw in added_keywords:
                if kw in line:
                    return "structural"

        changed = old_lines ^ new_lines
        if any("import" in l or "from" in l for l in changed):
            return "dependency"

        removed_only = old_lines - new_lines
        if any("def " in l or "class " in l for l in removed_only):
            return "removal"

        if any("return" in l or "=" in l for l in changed):
            return "behavioral"

        return "cosmetic"

    def get_diffs(self, trace_id: str) -> List[DiffFrame]:
        return self._frames.get(trace_id, [])

    def summarize_changes(self, trace_id: str) -> dict:
        frames = self.get_diffs(trace_id)
        if not frames:
            return {"total_changes": 0}

        return {
            "total_changes": len(frames),
            "files_created": sum(1 for f in frames if f.action == "created"),
            "files_modified": sum(1 for f in frames if f.action == "modified"),
            "files_deleted": sum(1 for f in frames if f.action == "deleted"),
            "total_lines_added": sum(f.lines_added for f in frames),
            "total_lines_removed": sum(f.lines_removed for f in frames),
            "by_semantic_impact": dict(
                Counter(f.semantic_impact for f in frames)
            ),
        }
