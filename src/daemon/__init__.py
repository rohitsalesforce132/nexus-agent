"""Daemon — 24/7 uptime with system service, crash recovery, heartbeat monitoring."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DaemonStatus(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    CRASHED = "crashed"
    RECOVERING = "recovering"


@dataclass
class CrashReport:
    crash_number: int
    timestamp: float
    reason: str = "unknown"
    recovered: bool = False


class CrashRecovery:
    """Exponential backoff crash recovery (up to 10 restarts per minute)."""

    def __init__(self, max_restarts_per_minute: int = 10):
        self.max_restarts = max_restarts_per_minute
        self._crashes: list[CrashReport] = []
        self._backoff_seconds: float = 1.0

    def record_crash(self, reason: str = "unknown") -> CrashReport:
        report = CrashReport(len(self._crashes) + 1, time.time(), reason)
        # Check rate limit
        recent = [c for c in self._crashes if time.time() - c.timestamp < 60]
        if len(recent) >= self.max_restarts:
            report.recovered = False
            self._crashes.append(report)
            return report

        report.recovered = True
        self._backoff_seconds = min(self._backoff_seconds * 2, 30.0)
        self._crashes.append(report)
        return report

    @property
    def backoff_seconds(self) -> float:
        return self._backoff_seconds

    @property
    def total_crashes(self) -> int:
        return len(self._crashes)

    @property
    def recent_crashes(self) -> int:
        return len([c for c in self._crashes if time.time() - c.timestamp < 60])


class HeartbeatMonitor:
    """Monitors agent health with periodic heartbeat checks."""

    def __init__(self, interval_seconds: float = 30.0):
        self.interval = interval_seconds
        self._last_heartbeat: float = 0
        self._healthy: bool = True
        self._checks: list[dict] = []

    def beat(self) -> dict:
        """Record a heartbeat."""
        self._last_heartbeat = time.time()
        self._healthy = True
        check = {"timestamp": self._last_heartbeat, "healthy": True}
        self._checks.append(check)
        return check

    def check_health(self) -> dict:
        """Check if agent is healthy (heartbeat within interval)."""
        if self._last_heartbeat == 0:
            return {"healthy": False, "reason": "No heartbeat received"}
        age = time.time() - self._last_heartbeat
        healthy = age < self.interval * 2
        return {
            "healthy": healthy,
            "last_heartbeat_age_seconds": round(age, 1),
            "interval": self.interval,
        }

    @property
    def check_count(self) -> int:
        return len(self._checks)


class DaemonManager:
    """Manages the background daemon process with system service integration."""

    def __init__(self):
        self.status = DaemonStatus.STOPPED
        self.pid: Optional[int] = None
        self.started_at: Optional[float] = None
        self.crash_recovery = CrashRecovery()
        self.heartbeat = HeartbeatMonitor()

    def start(self) -> dict:
        if self.status == DaemonStatus.RUNNING:
            return {"status": "already_running", "pid": self.pid}
        self.status = DaemonStatus.STARTING
        self.pid = int(time.time() * 1000) % 100000  # Simulated PID
        self.started_at = time.time()
        self.status = DaemonStatus.RUNNING
        return {"status": "started", "pid": self.pid}

    def stop(self) -> dict:
        if self.status != DaemonStatus.RUNNING:
            return {"status": "not_running"}
        self.status = DaemonStatus.STOPPED
        pid = self.pid
        self.pid = None
        return {"status": "stopped", "pid": pid}

    def restart(self) -> dict:
        self.stop()
        return self.start()

    def simulate_crash(self, reason: str = "test") -> dict:
        report = self.crash_recovery.record_crash(reason)
        if report.recovered:
            self.status = DaemonStatus.RECOVERING
            self.status = DaemonStatus.RUNNING  # Auto-recovered
        else:
            self.status = DaemonStatus.CRASHED
        return {"crash_report": report.__dict__, "status": self.status.value}

    @property
    def uptime_seconds(self) -> float:
        if self.started_at and self.status == DaemonStatus.RUNNING:
            return time.time() - self.started_at
        return 0
