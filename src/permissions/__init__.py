"""Permissions — Shell blocklist, folder scoping, and human approval flow."""
from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PermissionMode(Enum):
    ASK_ME = "ask_me"        # Require approval for every action
    ALLOW_ALL = "allow_all"  # Allow all (still enforce blocklist)


class PermissionDecision(Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    PENDING = "pending"       # Awaiting human approval


class ActionType(Enum):
    SHELL_COMMAND = "shell_command"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    NETWORK_REQUEST = "network_request"
    GIT_OPERATION = "git_operation"
    MEMORY_WRITE = "memory_write"
    MESSAGE_SEND = "message_send"


@dataclass
class ScopeRule:
    """Folder-level read/write scoping."""
    path: str
    allow_read: bool = True
    allow_write: bool = False
    allow_delete: bool = False
    description: str = ""

    def allows(self, action: ActionType, target_path: str) -> bool:
        if not target_path.startswith(self.path):
            return False
        if action == ActionType.FILE_READ:
            return self.allow_read
        if action == ActionType.FILE_WRITE:
            return self.allow_write
        if action == ActionType.FILE_DELETE:
            return self.allow_delete
        return False


@dataclass
class PermissionResult:
    decision: PermissionDecision
    action: ActionType
    target: str
    reason: str = ""
    timestamp: float = field(default_factory=time.time)
    requires_approval: bool = False


class PermissionGuard:
    """Permission-hardened execution guard.

    Features Mercury doesn't have:
    - Shell command blocklist with pattern matching
    - Folder-level scope rules
    - Pending approval flow
    - Full audit trail of every permission decision
    """

    SHELL_BLOCKLIST = [
        re.compile(r'\bsudo\b'),
        re.compile(r'\brm\s+-rf\s+/'),
        re.compile(r'\bmkfs\b'),
        re.compile(r'\bdd\s+if='),
        re.compile(r'\bformat\b', re.I),
        re.compile(r'>\s*/dev/sd'),
        re.compile(r'\bchmod\s+777'),
        re.compile(r'\bchown\s+root'),
        re.compile(r'\bsystemctl\s+(stop|disable)\s+(ssh|sshd|firewall)', re.I),
        re.compile(r'\biptables\s+-F'),
        re.compile(r'\bcurl\s+.*\|\s*sh'),
        re.compile(r'\bwget\s+.*\|\s*sh'),
        re.compile(r'\beval\b'),
        re.compile(r'\bexec\b'),
    ]

    def __init__(self, mode: PermissionMode = PermissionMode.ASK_ME):
        self.mode = mode
        self._scope_rules: list[ScopeRule] = []
        self._pending: list[PermissionResult] = []
        self._log: list[PermissionResult] = []

    def add_scope(self, rule: ScopeRule) -> None:
        self._scope_rules.append(rule)

    def check(self, action: ActionType, target: str = "",
              command: str = "") -> PermissionResult:
        """Check if an action is permitted."""
        # 1. Shell blocklist check
        if action == ActionType.SHELL_COMMAND and command:
            for pattern in self.SHELL_BLOCKLIST:
                if pattern.search(command):
                    result = PermissionResult(
                        PermissionDecision.BLOCKED, action, target,
                        f"Command matches blocklist pattern: {pattern.pattern}"
                    )
                    self._log.append(result)
                    return result

        # 2. Folder scope check
        if action in (ActionType.FILE_READ, ActionType.FILE_WRITE, ActionType.FILE_DELETE):
            scoped = any(rule.allows(action, target) for rule in self._scope_rules)
            if not scoped and self._scope_rules:
                result = PermissionResult(
                    PermissionDecision.BLOCKED, action, target,
                    f"Path not in allowed scopes: {target}"
                )
                self._log.append(result)
                return result

        # 3. Approval flow
        if self.mode == PermissionMode.ASK_ME:
            dangerous = action in (ActionType.FILE_DELETE, ActionType.MESSAGE_SEND,
                                  ActionType.SHELL_COMMAND)
            if dangerous:
                result = PermissionResult(
                    PermissionDecision.PENDING, action, target,
                    f"Requires approval for {action.value}",
                    requires_approval=True
                )
                self._pending.append(result)
                self._log.append(result)
                return result

        result = PermissionResult(PermissionDecision.ALLOWED, action, target)
        self._log.append(result)
        return result

    def approve(self, index: int = -1) -> bool:
        """Approve a pending action."""
        if self._pending:
            item = self._pending.pop(index)
            item.decision = PermissionDecision.ALLOWED
            item.requires_approval = False
            return True
        return False

    def deny(self, index: int = -1) -> bool:
        """Deny a pending action."""
        if self._pending:
            item = self._pending.pop(index)
            item.decision = PermissionDecision.BLOCKED
            return True
        return False

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def log(self) -> list[PermissionResult]:
        return list(self._log)

    @property
    def block_count(self) -> int:
        return sum(1 for r in self._log if r.decision == PermissionDecision.BLOCKED)
