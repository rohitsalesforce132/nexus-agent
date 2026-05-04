"""Budget — Token budgets with per-model tracking and auto-concise."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BudgetAction(Enum):
    ALLOW = "allow"
    AUTO_CONCISE = "auto_concise"  # >70% used, auto-summarize context
    BLOCK = "block"               # Budget exhausted


class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    GOOGLE = "google"
    LOCAL = "local"


@dataclass
class ModelPricing:
    provider: Provider
    model: str
    input_per_1m: float   # Cost per 1M input tokens
    output_per_1m: float  # Cost per 1M output tokens


MODEL_PRICES = {
    "gpt-4o-mini": ModelPricing(Provider.OPENAI, "gpt-4o-mini", 0.15, 0.60),
    "gpt-4o": ModelPricing(Provider.OPENAI, "gpt-4o", 2.50, 10.00),
    "claude-sonnet": ModelPricing(Provider.ANTHROPIC, "claude-sonnet", 3.00, 15.00),
    "claude-haiku": ModelPricing(Provider.ANTHROPIC, "claude-haiku", 0.25, 1.25),
    "deepseek-chat": ModelPricing(Provider.DEEPSEEK, "deepseek-chat", 0.14, 0.28),
    "gemini-pro": ModelPricing(Provider.GOOGLE, "gemini-pro", 1.25, 5.00),
}


@dataclass
class UsageRecord:
    model: str
    input_tokens: int
    output_tokens: int
    timestamp: float = field(default_factory=time.time)

    @property
    def cost(self) -> float:
        pricing = MODEL_PRICES.get(self.model)
        if not pricing:
            return 0.0
        return (self.input_tokens / 1_000_000 * pricing.input_per_1m +
                self.output_tokens / 1_000_000 * pricing.output_per_1m)


class TokenBudget:
    """Daily token budget with per-model cost tracking.

    - Hard cap on daily tokens
    - Auto-concise when >70% used (reduces context to save tokens)
    - Per-model cost breakdown
    - Budget override for single requests
    """

    def __init__(self, daily_token_limit: int = 500_000,
                 concise_threshold: float = 0.70):
        self.daily_limit = daily_token_limit
        self.concise_threshold = concise_threshold
        self._used_tokens: int = 0
        self._records: list[UsageRecord] = []
        self._override_active: bool = False
        self._reset_at: float = time.time() + 86400

    def check(self, estimated_tokens: int) -> BudgetAction:
        """Check budget before a request."""
        if self._override_active:
            return BudgetAction.ALLOW

        if time.time() > self._reset_at:
            self.reset()

        usage_pct = (self._used_tokens + estimated_tokens) / self.daily_limit

        if usage_pct >= 1.0:
            return BudgetAction.BLOCK
        if usage_pct >= self.concise_threshold:
            return BudgetAction.AUTO_CONCISE
        return BudgetAction.ALLOW

    def record(self, model: str, input_tokens: int, output_tokens: int) -> UsageRecord:
        """Record actual token usage."""
        record = UsageRecord(model, input_tokens, output_tokens)
        self._used_tokens += input_tokens + output_tokens
        self._records.append(record)
        return record

    def override(self) -> None:
        """Override budget for one request."""
        self._override_active = True

    def clear_override(self) -> None:
        self._override_active = False

    def reset(self) -> None:
        self._used_tokens = 0
        self._records.clear()
        self._reset_at = time.time() + 86400

    @property
    def used_tokens(self) -> int:
        return self._used_tokens

    @property
    def remaining_tokens(self) -> int:
        return max(0, self.daily_limit - self._used_tokens)

    @property
    def usage_pct(self) -> float:
        return self._used_tokens / self.daily_limit if self.daily_limit > 0 else 0

    @property
    def total_cost(self) -> float:
        return sum(r.cost for r in self._records)

    def cost_by_model(self) -> dict[str, float]:
        costs: dict[str, float] = {}
        for r in self._records:
            costs[r.model] = costs.get(r.model, 0) + r.cost
        return costs

    @property
    def status(self) -> dict:
        return {
            "daily_limit": self.daily_limit,
            "used": self._used_tokens,
            "remaining": self.remaining_tokens,
            "usage_pct": round(self.usage_pct * 100, 1),
            "total_cost": round(self.total_cost, 4),
            "cost_by_model": {k: round(v, 4) for k, v in self.cost_by_model().items()},
            "override_active": self._override_active,
        }
