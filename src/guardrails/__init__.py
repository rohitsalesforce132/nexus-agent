"""Guardrails — 3-layer safety: input validation, output filter, bias detection."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class GuardrailCategory(Enum):
    PROMPT_INJECTION = "prompt_injection"
    TOXICITY = "toxicity"
    PII = "pii"
    HARMFUL_INSTRUCTION = "harmful_instruction"
    SAFE = "safe"


class BiasType(Enum):
    GENDER = "gender"
    RACE = "race"
    AGE = "age"


@dataclass
class GuardResult:
    passed: bool
    category: GuardrailCategory = GuardrailCategory.SAFE
    sanitized: str = ""
    reasons: list[str] = field(default_factory=list)
    bias_detected: bool = False
    bias_type: str = ""


class InputGuard:
    """Input validation — catches prompt injection, PII, harmful instructions."""

    INJECTION_PATTERNS = [
        re.compile(r'ignore\s+(all\s+)?previous\s+instructions', re.I),
        re.compile(r'you\s+are\s+now\s+(?:DAN|jailbroken)', re.I),
        re.compile(r'forget\s+(everything|your\s+rules)', re.I),
        re.compile(r'system\s*:\s*you', re.I),
    ]

    PII_PATTERNS = {
        "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        "phone": re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
    }

    HARMFUL_PATTERNS = [
        re.compile(r'\b(?:DROP|DELETE|TRUNCATE)\s+TABLE\b', re.I),
        re.compile(r'\bsudo\s+rm\b'),
        re.compile(r'\bhow\s+to\s+(?:hack|exploit|attack)\b', re.I),
    ]

    def check(self, text: str) -> GuardResult:
        reasons = []
        sanitized = text
        category = GuardrailCategory.SAFE

        for p in self.INJECTION_PATTERNS:
            if p.search(text):
                category = GuardrailCategory.PROMPT_INJECTION
                reasons.append("Prompt injection detected")

        for p in self.HARMFUL_PATTERNS:
            if p.search(text):
                category = GuardrailCategory.HARMFUL_INSTRUCTION
                reasons.append("Harmful instruction detected")

        pii_found = {}
        for pii_type, pattern in self.PII_PATTERNS.items():
            if pattern.search(text):
                pii_found[pii_type] = True
                sanitized = pattern.sub(f'[{pii_type.upper()}-REDACTED]', sanitized)
        if pii_found:
            category = GuardrailCategory.PII
            reasons.append(f"PII detected: {list(pii_found.keys())}")

        return GuardResult(
            passed=len(reasons) == 0,
            category=category,
            sanitized=sanitized,
            reasons=reasons,
        )


class OutputGuard:
    """Output filtering — toxicity, PII leaks, and content safety."""

    TOXIC_KEYWORDS = {"hate", "violent", "kill", "attack", "harm", "threat"}

    def check(self, text: str, confidence: float = 1.0) -> GuardResult:
        reasons = []
        text_lower = text.lower()
        toxic = [w for w in self.TOXIC_KEYWORDS if w in text_lower]
        if toxic:
            reasons.append(f"Toxic content: {toxic}")
        if confidence < 0.5:
            reasons.append(f"Low confidence: {confidence:.2f}")
        return GuardResult(
            passed=len(reasons) == 0,
            category=GuardrailCategory.TOXICITY if toxic else GuardrailCategory.SAFE,
            reasons=reasons,
        )


class BiasDetector:
    """Detects bias in agent outputs — something Mercury doesn't have."""

    PROXY_TERMS = {
        BiasType.GENDER: {
            "male": ["he", "him", "his", "man", "husband", "father"],
            "female": ["she", "her", "hers", "woman", "wife", "mother"],
        },
    }

    def check(self, text: str) -> GuardResult:
        words = set(re.split(r'\W+', text.lower())) - {''}
        for bias_type, groups in self.PROXY_TERMS.items():
            for group, terms in groups.items():
                if words & set(terms):
                    # Just flagging presence — not blocking
                    return GuardResult(
                        passed=True,
                        bias_detected=True,
                        bias_type=bias_type.value,
                        reasons=[f"Gender-specific language detected"],
                    )
        return GuardResult(passed=True, bias_detected=False)
