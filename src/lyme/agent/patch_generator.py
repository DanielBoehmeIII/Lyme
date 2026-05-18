"""PatchGenerator — generates code patches from NL task descriptions."""
from __future__ import annotations
import difflib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .file_selector import FileSelection


@dataclass
class GeneratedPatch:
    file_path: str
    original_content: str = ""
    new_content: str = ""
    description: str = ""
    diff: str = ""
    confidence: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "description": self.description,
            "diff": self.diff[:500],
            "confidence": round(self.confidence, 4),
        }


class PatchGenerator:
    def __init__(self, model_fn: Optional[Callable] = None):
        self._model_fn = model_fn

    def set_model_fn(self, fn: Callable) -> None:
        self._model_fn = fn

    def generate(
        self,
        task: str,
        file_selection: FileSelection,
        context: Dict[str, str],
        failure_context: Optional[Dict[str, Any]] = None,
    ) -> List[GeneratedPatch]:
        patches: List[GeneratedPatch] = []

        for fp in file_selection.primary_files:
            content = context.get(fp, "")
            if not content:
                continue

            if self._model_fn:
                patch = self._generate_with_model(task, fp, content, failure_context)
            else:
                patch = self._generate_rule_based(task, fp, content)

            if patch:
                patches.append(patch)

        return patches

    def _generate_with_model(
        self,
        task: str,
        file_path: str,
        content: str,
        failure_context: Optional[Dict] = None,
    ) -> Optional[GeneratedPatch]:
        prompt = f"Task: {task}\n\n"
        if failure_context:
            prompt += f"Previous attempt failed. Failure context: {failure_context}\n\n"
        prompt += f"File: {file_path}\n\n```\n{content[:4000]}\n```\n\n"
        prompt += "Generate the complete new file content that implements the task."

        try:
            new_content = self._model_fn(prompt)
            if new_content and new_content != content:
                diff = self._compute_diff(file_path, content, new_content)
                return GeneratedPatch(
                    file_path=file_path,
                    original_content=content,
                    new_content=new_content,
                    description=f"Model-generated patch for: {task[:80]}",
                    diff=diff,
                    confidence=0.7,
                )
        except Exception:
            pass

        return None

    def _generate_rule_based(
        self,
        task: str,
        file_path: str,
        content: str,
    ) -> Optional[GeneratedPatch]:
        task_lower = task.lower()
        lines = content.split("\n")
        modified = False
        new_lines = list(lines)

        # Fix: Add missing imports
        if "import" in task_lower:
            for line in lines:
                if line.startswith("import ") or line.startswith("from "):
                    break
            else:
                new_lines.insert(0, "")
                modified = True

        # Fix: Add TODO comments
        if "todo" in task_lower or "note" in task_lower:
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("def ") or stripped.startswith("class "):
                    indent = " " * (len(line) - len(stripped))
                    new_lines.insert(i + 1, f"{indent}    # TODO: {task}")
                    modified = True
                    break

        # Fix: Replace pass with implementation note
        if "implement" in task_lower:
            for i, line in enumerate(lines):
                if line.strip() == "pass":
                    indent = line[:len(line) - len(line.lstrip())]
                    new_lines[i] = f"{indent}    # TODO: Implement {task}"
                    modified = True

        if modified:
            new_content = "\n".join(new_lines)
            diff = self._compute_diff(file_path, content, new_content)
            return GeneratedPatch(
                file_path=file_path,
                original_content=content,
                new_content=new_content,
                description=f"Rule-based patch for: {task[:80]}",
                diff=diff,
                confidence=0.3,
            )

        return None

    def _compute_diff(self, file_path: str, old: str, new: str) -> str:
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
        )
        return "".join(diff)
