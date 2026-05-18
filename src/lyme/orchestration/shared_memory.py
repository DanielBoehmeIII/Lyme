"""SharedMemory — inter-agent communication bus."""
from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class MemoryMessage:
    id: str
    sender: str
    recipient: Optional[str]
    message_type: str
    content: str
    timestamp: float
    ttl_sec: float
    priority: int
    read: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "type": self.message_type,
            "content": self.content[:100],
            "priority": self.priority,
            "read": self.read,
        }


@dataclass
class SharedMemoryState:
    key: str
    value: Any
    setter: str
    timestamp: float
    ttl_sec: float

    def to_dict(self) -> Dict:
        return {
            "key": self.key,
            "value": str(self.value)[:80],
            "setter": self.setter,
            "ttl_sec": self.ttl_sec,
        }


@dataclass
class SharedMemoryReport:
    total_messages: int
    total_states: int
    active_agents: List[str]
    message_types: Dict[str, int]
    recent_activity: str
    stale_count: int

    def render_cli(self) -> str:
        lines = []
        lines.append("=" * 70)
        lines.append("  SHARED MEMORY BUS")
        lines.append("=" * 70)
        lines.append(f"  Messages: {self.total_messages} | States: {self.total_states}")
        lines.append(f"  Active Agents: {', '.join(self.active_agents[:5])}")
        lines.append(f"  Recent: {self.recent_activity}")
        if self.message_types:
            lines.append("")
            lines.append("  Message Types:")
            for mtype, count in sorted(self.message_types.items(), key=lambda x: -x[1])[:5]:
                lines.append(f"    {mtype}: {count}")
        lines.append("=" * 70)
        return "\n".join(lines)


class SharedMemory:
    def __init__(self):
        self._messages: List[MemoryMessage] = []
        self._states: Dict[str, SharedMemoryState] = {}

    def send(self, sender: str, message_type: str, content: str,
             recipient: Optional[str] = None,
             priority: int = 0, ttl_sec: float = 3600) -> str:
        msg_id = str(uuid.uuid4())[:8]
        self._messages.append(MemoryMessage(
            id=msg_id,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            content=content,
            timestamp=time.time(),
            ttl_sec=ttl_sec,
            priority=priority,
        ))
        return msg_id

    def read(self, agent_id: str, message_type: Optional[str] = None,
             limit: int = 10) -> List[MemoryMessage]:
        now = time.time()
        relevant = []
        for msg in self._messages:
            if msg.read:
                continue
            if now - msg.timestamp > msg.ttl_sec:
                continue
            if msg.recipient and msg.recipient != agent_id:
                continue
            if message_type and msg.message_type != message_type:
                continue
            relevant.append(msg)

        relevant.sort(key=lambda m: (-m.priority, -m.timestamp))
        result = relevant[:limit]
        for msg in result:
            msg.read = True
        return result

    def broadcast(self, sender: str, message_type: str, content: str,
                  priority: int = 0) -> str:
        return self.send(sender, message_type, content, recipient=None, priority=priority)

    def set_state(self, key: str, value: Any, setter: str, ttl_sec: float = 3600) -> None:
        self._states[key] = SharedMemoryState(
            key=key,
            value=value,
            setter=setter,
            timestamp=time.time(),
            ttl_sec=ttl_sec,
        )

    def get_state(self, key: str) -> Optional[Any]:
        state = self._states.get(key)
        if not state:
            return None
        if time.time() - state.timestamp > state.ttl_sec:
            del self._states[key]
            return None
        return state.value

    def get_all_state(self) -> Dict[str, Any]:
        now = time.time()
        stale_keys = [k for k, s in self._states.items()
                      if now - s.timestamp > s.ttl_sec]
        for k in stale_keys:
            del self._states[k]
        return {k: s.value for k, s in self._states.items()}

    def report(self) -> SharedMemoryReport:
        now = time.time()
        active = set()
        for msg in self._messages:
            if now - msg.timestamp < 300:
                active.add(msg.sender)
                if msg.recipient:
                    active.add(msg.recipient)

        mtypes: Dict[str, int] = {}
        for msg in self._messages:
            mtypes[msg.message_type] = mtypes.get(msg.message_type, 0) + 1

        stale = sum(1 for s in self._states.values()
                    if now - s.timestamp > s.ttl_sec)

        recent_count = sum(1 for msg in self._messages
                           if now - msg.timestamp < 60)

        return SharedMemoryReport(
            total_messages=len(self._messages),
            total_states=len(self._states),
            active_agents=sorted(active),
            message_types=mtypes,
            recent_activity=f"{recent_count} messages in last 60s",
            stale_count=stale,
        )

    def clear(self) -> None:
        self._messages.clear()
        self._states.clear()
