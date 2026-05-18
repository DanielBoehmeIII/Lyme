"""PermissionManager — role-based access control for team operations."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class Role(Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Permission(Enum):
    RUN_AGENT = "run_agent"
    EDIT_CODE = "edit_code"
    REVIEW_PR = "review_pr"
    VIEW_METRICS = "view_metrics"
    MANAGE_TEAM = "manage_team"
    CONFIGURE = "configure"
    DEPLOY = "deploy"


ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {p for p in Permission},
    Role.DEVELOPER: {Permission.RUN_AGENT, Permission.EDIT_CODE, Permission.VIEW_METRICS},
    Role.REVIEWER: {Permission.REVIEW_PR, Permission.VIEW_METRICS},
    Role.VIEWER: {Permission.VIEW_METRICS},
}


@dataclass
class PermissionManager:
    roles: Dict[str, Role] = field(default_factory=dict)

    def assign(self, user: str, role: Role) -> None:
        self.roles[user] = role

    def check(self, user: str, permission: Permission) -> bool:
        role = self.roles.get(user)
        if not role:
            return False
        return permission in ROLE_PERMISSIONS.get(role, set())

    def require(self, user: str, permission: Permission) -> None:
        if not self.check(user, permission):
            raise PermissionError(f"User '{user}' lacks {permission.value} permission")

    def list_users(self, role: Optional[Role] = None) -> List[Dict[str, str]]:
        if role:
            return [{"user": u, "role": r.value} for u, r in self.roles.items() if r == role]
        return [{"user": u, "role": r.value} for u, r in self.roles.items()]
