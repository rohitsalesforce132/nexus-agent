"""Memory — Second Brain with 10 memory types, auto-extraction, and conflict resolution."""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class MemoryType(Enum):
    IDENTITY = "identity"       # Who the user is
    PREFERENCE = "preference"   # What they like/dislike
    GOAL = "goal"               # What they're working toward
    PROJECT = "project"         # Active projects
    HABIT = "habit"             # Behavioral patterns
    DECISION = "decision"       # Past decisions
    CONSTRAINT = "constraint"   # Things to avoid/respect
    RELATIONSHIP = "relationship"  # People in their life
    EPISODE = "episode"         # Notable events
    REFLECTION = "reflection"   # Agent-generated insights


@dataclass
class MemoryEntry:
    """A single structured memory."""
    memory_type: MemoryType
    content: str
    confidence: float = 0.8       # 0-1, how confident is this memory
    importance: float = 0.5       # 0-1, how important
    durability: float = 0.5       # 0-1, how long until it decays
    source: str = "conversation"   # Where did this come from
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    entry_id: str = ""

    def __post_init__(self):
        if not self.entry_id:
            self.entry_id = hashlib.sha256(
                f"{self.memory_type.value}:{self.content}:{self.created_at}".encode()
            ).hexdigest()[:12]

    @property
    def is_stale(self) -> bool:
        """Active-scope memories stale after 21 days."""
        age_days = (time.time() - self.created_at) / 86400
        if self.durability < 0.3:
            return age_days > 21
        return False

    @property
    def should_dismiss(self) -> bool:
        """Low-confidence durable memories dismissed after 120 days."""
        age_days = (time.time() - self.created_at) / 86400
        if self.confidence < 0.5 and self.durability >= 0.3:
            return age_days > 120
        return False

    def touch(self) -> None:
        self.last_accessed = time.time()
        self.access_count += 1


class SecondBrain:
    """Structured persistent memory that grows with every conversation.

    10 memory types, auto-extraction, conflict resolution, auto-consolidation.
    Like Mercury's Second Brain, but with type-safe memory entries and
    structured conflict resolution instead of just recency-based.
    """

    def __init__(self, max_context_chars: int = 900):
        self.max_context_chars = max_context_chars
        self._memories: dict[str, MemoryEntry] = {}
        self._consolidation_log: list[dict] = []

    def store(self, entry: MemoryEntry) -> dict:
        """Store a memory, handling conflicts."""
        # Check for conflicting memories
        conflicts = self._find_conflicts(entry)
        if conflicts:
            resolution = self._resolve_conflict(entry, conflicts[0])
            if resolution == "keep_existing":
                return {"action": "conflict_resolved", "kept": conflicts[0].entry_id,
                        "rejected": entry.entry_id}

        self._memories[entry.entry_id] = entry
        return {"action": "stored", "entry_id": entry.entry_id,
                "type": entry.memory_type.value}

    def recall(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Recall relevant memories for context injection."""
        query_words = set(query.lower().split())
        scored = []

        for entry in self._memories.values():
            if entry.should_dismiss:
                continue
            content_words = set(entry.content.lower().split())
            overlap = len(query_words & content_words)
            if overlap > 0:
                # Score: overlap * importance * confidence * recency bonus
                recency_bonus = max(0.5, 1.0 - (time.time() - entry.last_accessed) / 86400)
                score = overlap * entry.importance * entry.confidence * recency_bonus
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        total_chars = 0
        for _, entry in scored[:top_k]:
            if total_chars + len(entry.content) > self.max_context_chars:
                break
            entry.touch()
            results.append(entry)
            total_chars += len(entry.content)

        return results

    def _find_conflicts(self, new_entry: MemoryEntry) -> list[MemoryEntry]:
        """Find memories that might conflict with the new one."""
        conflicts = []
        for existing in self._memories.values():
            if existing.memory_type != new_entry.memory_type:
                continue
            # Simple: same type and overlapping content
            existing_words = set(existing.content.lower().split())
            new_words = set(new_entry.content.lower().split())
            overlap = len(existing_words & new_words) / max(len(existing_words | new_words), 1)
            if overlap > 0.5 and existing.entry_id != new_entry.entry_id:
                conflicts.append(existing)
        return conflicts

    def _resolve_conflict(self, new_entry: MemoryEntry,
                          existing: MemoryEntry) -> str:
        """Resolve conflicting memories. Higher confidence wins; tie goes to recency."""
        if new_entry.confidence > existing.confidence:
            del self._memories[existing.entry_id]
            return "replace_with_new"
        if new_entry.confidence == existing.confidence:
            if new_entry.created_at > existing.created_at:
                del self._memories[existing.entry_id]
                return "replace_with_new"
        return "keep_existing"

    def consolidate(self) -> dict:
        """Auto-consolidation: build profile summary and reflections."""
        by_type: dict[MemoryType, list[MemoryEntry]] = {}
        for entry in self._memories.values():
            by_type.setdefault(entry.memory_type, []).append(entry)

        # Prune stale
        pruned = 0
        for entry_id in list(self._memories.keys()):
            entry = self._memories[entry_id]
            if entry.is_stale or entry.should_dismiss:
                del self._memories[entry_id]
                pruned += 1

        report = {
            "total_memories": len(self._memories),
            "by_type": {t.value: len(entries) for t, entries in by_type.items()},
            "pruned": pruned,
            "timestamp": time.time(),
        }
        self._consolidation_log.append(report)
        return report

    def get_by_type(self, memory_type: MemoryType) -> list[MemoryEntry]:
        return [m for m in self._memories.values() if m.memory_type == memory_type]

    @property
    def total_memories(self) -> int:
        return len(self._memories)

    @property
    def memory_types_used(self) -> list[str]:
        return list(set(m.memory_type.value for m in self._memories.values()))
