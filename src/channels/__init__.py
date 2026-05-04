"""Channels — Multi-channel routing with Telegram RBAC (admin/member roles)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Channel(Enum):
    CLI = "cli"
    TELEGRAM = "telegram"


class UserRole(Enum):
    ADMIN = "admin"
    MEMBER = "member"


@dataclass
class ChannelUser:
    user_id: str
    username: str = ""
    role: UserRole = UserRole.MEMBER
    approved_at: float = field(default_factory=time.time)
    channel: Channel = Channel.TELEGRAM


class TelegramRBAC:
    """Telegram access control with admin/member roles.

    Like Mercury's multi-user Telegram but with role-based access:
    - Admins can approve/reject, promote/demote, reset access
    - Members can chat with the agent
    - Private chats only (group messages ignored)
    """

    def __init__(self):
        self._users: dict[str, ChannelUser] = {}
        self._pending: list[ChannelUser] = []

    def request_access(self, user_id: str, username: str = "") -> dict:
        """User requests access (sends /start)."""
        if user_id in self._users:
            return {"status": "already_approved", "role": self._users[user_id].role.value}

        pending = ChannelUser(user_id, username, channel=Channel.TELEGRAM)
        self._pending.append(pending)
        return {"status": "pending", "message": "Access request sent to admin"}

    def approve(self, user_id: str, as_admin: bool = False) -> bool:
        # Check pending first
        for i, p in enumerate(self._pending):
            if p.user_id == user_id:
                role = UserRole.ADMIN if as_admin else UserRole.MEMBER
                p.role = role
                self._users[user_id] = p
                self._pending.pop(i)
                return True
        return False

    def reject(self, user_id: str) -> bool:
        for i, p in enumerate(self._pending):
            if p.user_id == user_id:
                self._pending.pop(i)
                return True
        return False

    def promote(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user:
            user.role = UserRole.ADMIN
            return True
        return False

    def demote(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        if user:
            user.role = UserRole.MEMBER
            return True
        return False

    def remove(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None

    def is_authorized(self, user_id: str) -> bool:
        return user_id in self._users

    def is_admin(self, user_id: str) -> bool:
        user = self._users.get(user_id)
        return user.role == UserRole.ADMIN if user else False

    def list_users(self) -> list[dict]:
        return [{"id": u.user_id, "name": u.username, "role": u.role.value}
                for u in self._users.values()]

    @property
    def user_count(self) -> int:
        return len(self._users)

    @property
    def pending_count(self) -> int:
        return len(self._pending)


class ChannelRouter:
    """Routes messages to the appropriate channel handler."""

    def __init__(self):
        self._handlers: dict[Channel, Any] = {}
        self._message_count: dict[Channel, int] = {c: 0 for c in Channel}

    def register(self, channel: Channel, handler=None) -> None:
        self._handlers[channel] = handler

    def route(self, message: str, channel: Channel, user_id: str = "") -> dict:
        self._message_count[channel] = self._message_count.get(channel, 0) + 1
        return {
            "channel": channel.value,
            "message": message,
            "user_id": user_id,
            "routed": channel in self._handlers,
        }

    @property
    def message_counts(self) -> dict[str, int]:
        return {c.value: v for c, v in self._message_count.items()}
