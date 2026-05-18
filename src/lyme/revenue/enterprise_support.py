"""EnterpriseSupport — support ticket system for enterprise customers."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SupportTicket:
    id: str = ""
    subject: str = ""
    description: str = ""
    priority: str = "normal"
    status: str = "open"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject[:80],
            "priority": self.priority,
            "status": self.status,
        }


class EnterpriseSupport:
    def __init__(self):
        self._tickets: List[SupportTicket] = []

    def create_ticket(self, subject: str, description: str,
                      priority: str = "normal") -> SupportTicket:
        import uuid
        ticket = SupportTicket(
            id=str(uuid.uuid4())[:12],
            subject=subject, description=description, priority=priority,
        )
        self._tickets.append(ticket)
        return ticket

    def resolve(self, ticket_id: str) -> bool:
        for t in self._tickets:
            if t.id == ticket_id:
                t.status = "resolved"
                return True
        return False

    def list_tickets(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        tickets = self._tickets
        if status:
            tickets = [t for t in tickets if t.status == status]
        return [t.to_dict() for t in sorted(tickets, key=lambda t: t.created_at, reverse=True)]
