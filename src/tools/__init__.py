"""Skills — Plugin architecture with install and cron scheduling."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class Skill:
    """An installable agent skill/plugin."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    handler: Callable = None
    installed_at: float = field(default_factory=time.time)

    def execute(self, params: dict = None) -> Any:
        if self.handler:
            return self.handler(params or {})
        return f"Skill {self.name} executed"


@dataclass
class ScheduledTask:
    """A recurring or one-shot scheduled task."""
    task_id: str
    skill_name: str
    schedule: str  # Cron expression or "delay:SECONDS"
    created_at: float = field(default_factory=time.time)
    last_run: Optional[float] = None
    run_count: int = 0
    active: bool = True


class SkillRegistry:
    """Install, list, and execute community skills."""

    def __init__(self):
        self._skills: dict[str, Skill] = {}

    def install(self, skill: Skill) -> dict:
        self._skills[skill.name] = skill
        return {"installed": skill.name, "version": skill.version}

    def uninstall(self, name: str) -> bool:
        return self._skills.pop(name, None) is not None

    def execute(self, name: str, params: dict = None) -> Any:
        skill = self._skills.get(name)
        if not skill:
            return f"Skill not found: {name}"
        return skill.execute(params)

    def list_skills(self) -> list[dict]:
        return [{"name": s.name, "version": s.version, "description": s.description}
                for s in self._skills.values()]

    @property
    def skill_count(self) -> int:
        return len(self._skills)


class TaskScheduler:
    """Schedule skills as recurring or one-shot tasks."""

    def __init__(self):
        self._tasks: dict[str, ScheduledTask] = {}

    def schedule(self, task_id: str, skill_name: str,
                 schedule: str) -> ScheduledTask:
        task = ScheduledTask(task_id, skill_name, schedule)
        self._tasks[task_id] = task
        return task

    def cancel(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.active = False
            return True
        return False

    def tick(self) -> list[ScheduledTask]:
        """Check and return tasks that should run now (simplified)."""
        due = []
        now = time.time()
        for task in self._tasks.values():
            if not task.active:
                continue
            if task.last_run is None or (now - task.last_run) > 60:
                task.last_run = now
                task.run_count += 1
                due.append(task)
        return due

    @property
    def task_count(self) -> int:
        return len(self._tasks)

    @property
    def active_tasks(self) -> list[ScheduledTask]:
        return [t for t in self._tasks.values() if t.active]
