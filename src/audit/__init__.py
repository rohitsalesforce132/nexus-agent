"""Audit Logger — Every tool call, permission decision, and memory write logged."""
from __future__ import annotations
import time
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AuditEventType(Enum):
    TOOL_CALL = "tool_call"
    PERMISSION_DECISION = "permission_decision"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    GUARDRAIL_TRIGGER = "guardrail_trigger"
    BUDGET_ACTION = "budget_action"
    CHANNEL_MESSAGE = "channel_message"
    DAEMON_EVENT = "daemon_event"


@dataclass
class AuditEntry:
    """A single audit log entry."""
    event_type: AuditEventType
    action: str
    actor: str = "nexus"
    target: str = ""
    result: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    risk_level: str = "low"  # low, medium, high

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "action": self.action,
            "actor": self.actor,
            "target": self.target,
            "result": self.result,
            "details": self.details,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "risk_level": self.risk_level,
        }


class AuditLogger:
    """Complete audit trail for agent operations.

    This is a key differentiator — Mercury has no audit logging.
    Every tool call, permission decision, memory write, and guardrail
    trigger is logged with timestamp, actor, and risk level.
    """

    def __init__(self, max_entries: int = 10_000):
        self.max_entries = max_entries
        self._entries: list[AuditEntry] = []

    def log(self, event_type: AuditEventType, action: str,
            target: str = "", result: str = "",
            details: dict = None, risk_level: str = "low",
            session_id: str = "") -> AuditEntry:
        entry = AuditEntry(
            event_type=event_type, action=action, target=target,
            result=result, details=details or {},
            risk_level=risk_level, session_id=session_id,
        )
        self._entries.append(entry)
        if len(self._entries) > self.max_entries:
            self._entries = self._entries[-self.max_entries:]
        return entry

    def query(self, event_type: AuditEventType = None,
              risk_level: str = None,
              since: float = None,
              limit: int = 100) -> list[AuditEntry]:
        entries = self._entries
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]
        if risk_level:
            entries = [e for e in entries if e.risk_level == risk_level]
        if since:
            entries = [e for e in entries if e.timestamp >= since]
        return entries[-limit:]

    @property
    def total_entries(self) -> int:
        return len(self._entries)

    @property
    def high_risk_count(self) -> int:
        return sum(1 for e in self._entries if e.risk_level == "high")

    @property
    def event_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for e in self._entries:
            key = e.event_type.value
            counts[key] = counts.get(key, 0) + 1
        return counts
