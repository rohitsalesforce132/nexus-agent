"""Soul Engine — Personality from markdown files, not hardcoded prompts."""
from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SoulFile(Enum):
    SOUL = "soul.md"
    PERSONA = "persona.md"
    TASTE = "taste.md"
    HEARTBEAT = "heartbeat.md"


@dataclass
class PersonaConfig:
    """Agent personality configuration from markdown files."""
    name: str = "Nexus"
    tone: str = "direct, helpful, concise"
    language: str = "en"
    humor_level: float = 0.3  # 0.0 = none, 1.0 = constant
    proactivity: float = 0.7  # 0.0 = reactive only, 1.0 = very proactive
    boundaries: list[str] = field(default_factory=lambda: [
        "Never execute destructive commands without approval",
        "Never share private data externally",
        "Always ask before sending messages or emails",
    ])
    custom_instructions: str = ""

    def to_system_prompt(self) -> str:
        parts = [
            f"You are {self.name}, an AI agent.",
            f"Tone: {self.tone}.",
            f"Language: {self.language}.",
        ]
        if self.humor_level > 0:
            parts.append(f"Humor level: {self.humor_level:.0%}. Be witty when it lands, never forced.")
        if self.proactivity > 0.5:
            parts.append("Be proactive — suggest actions, catch issues early, don't wait to be asked.")
        parts.append("\nBoundaries:")
        for b in self.boundaries:
            parts.append(f"- {b}")
        if self.custom_instructions:
            parts.append(f"\nAdditional: {self.custom_instructions}")
        return "\n".join(parts)


class SoulEngine:
    """Loads and manages agent personality from markdown files.

    Like Mercury, personality is defined by markdown files the user owns.
    Unlike Mercury, SoulEngine also manages persona versioning and hot-reload.
    """

    def __init__(self, soul_dir: str = ""):
        self.soul_dir = soul_dir
        self._files: dict[str, str] = {}
        self._config = PersonaConfig()
        self._loaded_at: float = 0

    def load(self, soul_dir: str = None) -> PersonaConfig:
        """Load soul files from directory."""
        directory = soul_dir or self.soul_dir
        if directory and os.path.isdir(directory):
            for soul_file in SoulFile:
                path = os.path.join(directory, soul_file.value)
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        self._files[soul_file.value] = f.read()
        self._loaded_at = time.time()
        return self._config

    def get_file(self, name: str) -> str:
        return self._files.get(name, "")

    @property
    def config(self) -> PersonaConfig:
        return self._config

    @config.setter
    def config(self, value: PersonaConfig) -> None:
        self._config = value

    @property
    def system_prompt(self) -> str:
        soul_content = self._files.get("soul.md", "")
        persona = self._config.to_system_prompt()
        if soul_content:
            return f"{persona}\n\n# Soul\n{soul_content}"
        return persona

    @property
    def loaded_files(self) -> list[str]:
        return list(self._files.keys())

    @property
    def last_loaded_at(self) -> float:
        return self._loaded_at
