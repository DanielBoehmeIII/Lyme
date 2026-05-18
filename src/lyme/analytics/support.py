import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TicketStatus(str, Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class IssueTicket:
    ticket_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    description: str = ""
    category: str = ""
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    reporter: str = ""
    assignee: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    tags: list = field(default_factory=list)
    related_commands: list = field(default_factory=list)
    environment: dict = field(default_factory=dict)
    comments: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "priority": self.priority.value,
            "status": self.status.value,
            "reporter": self.reporter,
            "assignee": self.assignee,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "resolved_at": self.resolved_at,
            "tags": self.tags,
            "related_commands": self.related_commands,
            "environment": self.environment,
            "comments": self.comments,
        }


class SupportWorkflow:
    def __init__(self, storage_dir: str = ".lyme/analytics/support"):
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._tickets: dict[str, IssueTicket] = {}
        self._load()

    def _tickets_path(self) -> Path:
        return self._storage_dir / "tickets.json"

    def _load(self):
        path = self._tickets_path()
        if path.exists():
            try:
                data = json.loads(path.read_text())
                for d in data:
                    ticket = IssueTicket(
                        ticket_id=d.get("ticket_id"),
                        title=d.get("title", ""),
                        description=d.get("description", ""),
                        category=d.get("category", ""),
                        priority=TicketPriority(d.get("priority", "medium")),
                        status=TicketStatus(d.get("status", "open")),
                        reporter=d.get("reporter", ""),
                        assignee=d.get("assignee", ""),
                        created_at=d.get("created_at", time.time()),
                        updated_at=d.get("updated_at", time.time()),
                        resolved_at=d.get("resolved_at"),
                        tags=d.get("tags", []),
                        related_commands=d.get("related_commands", []),
                        environment=d.get("environment", {}),
                        comments=d.get("comments", []),
                    )
                    self._tickets[ticket.ticket_id] = ticket
            except Exception:
                pass

    def _save(self):
        data = [t.to_dict() for t in self._tickets.values()]
        self._tickets_path().write_text(json.dumps(data, indent=2))

    def create_ticket(
        self,
        title: str,
        description: str = "",
        category: str = "bug",
        priority: TicketPriority = TicketPriority.MEDIUM,
        reporter: str = "",
        tags: list = None,
        related_commands: list = None,
    ) -> IssueTicket:
        ticket = IssueTicket(
            title=title,
            description=description,
            category=category,
            priority=priority,
            reporter=reporter,
            tags=tags or [],
            related_commands=related_commands or [],
        )
        self._tickets[ticket.ticket_id] = ticket
        self._save()
        return ticket

    def add_comment(self, ticket_id: str, author: str, message: str):
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket.comments.append({
                "author": author,
                "message": message,
                "timestamp": time.time(),
            })
            ticket.updated_at = time.time()
            self._save()

    def update_status(self, ticket_id: str, status: TicketStatus):
        ticket = self._tickets.get(ticket_id)
        if ticket:
            ticket.status = status
            ticket.updated_at = time.time()
            if status in (TicketStatus.RESOLVED, TicketStatus.CLOSED):
                ticket.resolved_at = time.time()
            self._save()

    def get_triage_queue(self) -> list[IssueTicket]:
        open_tickets = [
            t for t in self._tickets.values()
            if t.status in (TicketStatus.OPEN, TicketStatus.TRIAGING)
        ]
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        open_tickets.sort(key=lambda t: (priority_order.get(t.priority.value, 99), t.created_at))
        return open_tickets

    def get_triage_summary(self) -> dict:
        if not self._tickets:
            return {"total": 0, "open": 0, "in_progress": 0, "resolved": 0, "by_status": {}, "by_priority": {}, "by_category": {}, "avg_resolution_time_s": 0}
        by_status = {}
        by_priority = {}
        by_category = {}
        for t in self._tickets.values():
            by_status[t.status.value] = by_status.get(t.status.value, 0) + 1
            by_priority[t.priority.value] = by_priority.get(t.priority.value, 0) + 1
            by_category[t.category or "uncategorized"] = by_category.get(t.category or "uncategorized", 0) + 1
        return {
            "total": len(self._tickets),
            "open": sum(1 for t in self._tickets.values() if t.status == TicketStatus.OPEN),
            "in_progress": sum(1 for t in self._tickets.values() if t.status == TicketStatus.IN_PROGRESS),
            "resolved": sum(1 for t in self._tickets.values() if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_category": by_category,
            "avg_resolution_time_s": self._avg_resolution_time(),
        }

    def _avg_resolution_time(self) -> float:
        resolved = [t for t in self._tickets.values() if t.resolved_at]
        if not resolved:
            return 0.0
        times = [t.resolved_at - t.created_at for t in resolved]
        return sum(times) / len(times) if times else 0.0


support_workflow = SupportWorkflow()
