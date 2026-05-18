"""ConflictDetector — detects and resolves edit conflicts across sessions."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .session import EditOperation


class ConflictType(Enum):
    SAME_FILE = "same_file"
    SAME_REGION = "same_region"
    DEPENDENCY = "dependency"
    RENAME_EDIT = "rename_edit"
    DELETE_EDIT = "delete_edit"


class ConflictResolution(Enum):
    KEEP_LATEST = "keep_latest"
    MERGE = "merge"
    MANUAL = "manual"
    ABORT = "abort"


@dataclass
class EditConflict:
    conflict_type: ConflictType
    operations: List[EditOperation] = field(default_factory=list)
    description: str = ""
    resolution: ConflictResolution = ConflictResolution.MANUAL
    file_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.conflict_type.value,
            "operations": [op.operation_id for op in self.operations],
            "description": self.description[:200],
            "resolution": self.resolution.value,
            "file_path": self.file_path,
        }


class ConflictDetector:
    def detect(self, new_op: EditOperation, existing_ops: List[EditOperation]) -> List[EditConflict]:
        conflicts: List[EditConflict] = []
        for existing in existing_ops:
            if existing.status != "applied":
                continue

            # Same file conflict
            if existing.file_path == new_op.file_path:
                conflicts.append(EditConflict(
                    conflict_type=ConflictType.SAME_FILE,
                    operations=[existing, new_op],
                    description=f"Multiple edits to {new_op.file_path}",
                    file_path=new_op.file_path,
                ))

            # Delete-edit conflict
            if new_op.operation_type.value == "delete" and existing.file_path == new_op.file_path:
                conflicts.append(EditConflict(
                    conflict_type=ConflictType.DELETE_EDIT,
                    operations=[existing, new_op],
                    description=f"Edit followed by delete on {new_op.file_path}",
                    resolution=ConflictResolution.ABORT,
                    file_path=new_op.file_path,
                ))

        return conflicts

    def auto_resolve(self, conflict: EditConflict) -> Optional[str]:
        if conflict.resolution == ConflictResolution.KEEP_LATEST:
            ops = sorted(conflict.operations, key=lambda o: o.timestamp, reverse=True)
            if ops:
                return ops[0].new_content
        return None
