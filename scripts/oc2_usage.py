#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class TokenUsage:
    input: float = 0
    output: float = 0
    reasoning: float = 0
    cache_read: float = 0
    cache_write: float = 0


@dataclass(frozen=True)
class TokenPricing:
    input: float
    output: float
    cache_read: float = 0
    cache_write: float = 0


def estimate_cost_usd(model: str, usage: TokenUsage, pricing: Mapping[str, TokenPricing]) -> float | None:
    """Estimate cost from OC2 token counters when native OC2 cost is unavailable.

    Rates are USD per one million tokens. Reasoning tokens use the output rate,
    matching OpenCode's legacy cost calculation. An unknown model returns None
    instead of reporting a misleading zero-dollar request.
    """
    rates = pricing.get(model)
    if rates is None:
        return None
    values = (usage.input, usage.output, usage.reasoning, usage.cache_read, usage.cache_write)
    if any(value < 0 for value in values):
        raise ValueError("token counts must be non-negative")
    cost = (
        usage.input * rates.input
        + (usage.output + usage.reasoning) * rates.output
        + usage.cache_read * rates.cache_read
        + usage.cache_write * rates.cache_write
    ) / 1_000_000
    return round(cost, 12)
