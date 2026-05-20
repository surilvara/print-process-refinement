"""Anthropic API pricing and cost computation.

Rates are USD per million tokens. Batch API applies a flat 50% discount to
input and output (cache rates inherit the same discount on the underlying
input rate, since cache pricing is defined as a multiple of base input).

Sources: Anthropic public pricing page (verified 2026-05). Update ``RATES`` if
Anthropic changes pricing or we adopt new models.

Verified multipliers (all model rows on the published table):
  5-minute cache write = 1.25 × base input
  1-hour cache write   = 2.00 × base input
  cache read / hit     = 0.10 × base input
  output               = 5.00 × base input
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

# Per-million-token base rates in USD. ``input`` = base input rate; ``output``
# = base output rate. Cache rates are derived from base input via the
# multipliers below (verified against Anthropic's published pricing table
# for all rows: 5m write = 1.25×, 1h write = 2.0×, cache hit = 0.10×).
RATES: dict[str, dict[str, float]] = {
    # Claude Opus 4.7 / 4.6 / 4.5 share the same pricing tier.
    "claude-opus-4-7": {"input": 5.0, "output": 25.0},
    "claude-opus-4-6": {"input": 5.0, "output": 25.0},
    "claude-opus-4-5": {"input": 5.0, "output": 25.0},
    # Opus 4.1 / 4.0 (deprecated) sit at the older premium tier.
    "claude-opus-4-1": {"input": 15.0, "output": 75.0},
    "claude-opus-4-20250514": {"input": 15.0, "output": 75.0},
    # Sonnet 4.6 / 4.5 share pricing.
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
    # Sonnet 4.0 (older dated ID).
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
}

# Cache multipliers applied to the base input rate.
# Default is the 5-minute ephemeral cache used throughout this module
# (``cache_control: {"type": "ephemeral"}``). If we ever opt into the 1-hour
# cache tier, switch to ``CACHE_WRITE_MULTIPLIER_1H``.
CACHE_WRITE_MULTIPLIER = 1.25  # 5-minute write
CACHE_WRITE_MULTIPLIER_1H = 2.0  # 1-hour write
CACHE_READ_MULTIPLIER = 0.10

BATCH_DISCOUNT = 0.5  # 50% off both input and output


@dataclass
class CostBreakdown:
    model: str
    batch: bool
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    input_cost_usd: float
    output_cost_usd: float
    cache_creation_cost_usd: float
    cache_read_cost_usd: float
    total_cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _usage_field(usage: Any, name: str) -> int:
    """Read a usage field from either a pydantic object or a dict."""
    if usage is None:
        return 0
    if isinstance(usage, dict):
        return int(usage.get(name) or 0)
    return int(getattr(usage, name, 0) or 0)


def compute_cost(usage: Any, model: str, batch: bool = False) -> CostBreakdown:
    """Compute a USD cost breakdown for a single Anthropic usage object.

    ``usage`` may be either the pydantic ``Usage`` object returned by the SDK
    or a plain dict with the same field names.
    """
    rates = RATES.get(model)
    if rates is None:
        # Unknown model — return zero-cost breakdown but preserve token counts.
        rates = {"input": 0.0, "output": 0.0}

    in_rate = rates["input"]
    out_rate = rates["output"]
    if batch:
        in_rate *= BATCH_DISCOUNT
        out_rate *= BATCH_DISCOUNT

    input_tokens = _usage_field(usage, "input_tokens")
    output_tokens = _usage_field(usage, "output_tokens")
    cache_write = _usage_field(usage, "cache_creation_input_tokens")
    cache_read = _usage_field(usage, "cache_read_input_tokens")

    input_cost = input_tokens * in_rate / 1_000_000
    output_cost = output_tokens * out_rate / 1_000_000
    cache_write_cost = cache_write * in_rate * CACHE_WRITE_MULTIPLIER / 1_000_000
    cache_read_cost = cache_read * in_rate * CACHE_READ_MULTIPLIER / 1_000_000

    return CostBreakdown(
        model=model,
        batch=batch,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_input_tokens=cache_write,
        cache_read_input_tokens=cache_read,
        input_cost_usd=round(input_cost, 6),
        output_cost_usd=round(output_cost, 6),
        cache_creation_cost_usd=round(cache_write_cost, 6),
        cache_read_cost_usd=round(cache_read_cost, 6),
        total_cost_usd=round(
            input_cost + output_cost + cache_write_cost + cache_read_cost, 6
        ),
    )


def add_cost_breakdowns(items: list[CostBreakdown]) -> CostBreakdown | None:
    """Sum a list of breakdowns (same model + batch flag expected)."""
    if not items:
        return None
    model = items[0].model
    batch = items[0].batch
    total = CostBreakdown(
        model=model,
        batch=batch,
        input_tokens=0,
        output_tokens=0,
        cache_creation_input_tokens=0,
        cache_read_input_tokens=0,
        input_cost_usd=0.0,
        output_cost_usd=0.0,
        cache_creation_cost_usd=0.0,
        cache_read_cost_usd=0.0,
        total_cost_usd=0.0,
    )
    for it in items:
        total.input_tokens += it.input_tokens
        total.output_tokens += it.output_tokens
        total.cache_creation_input_tokens += it.cache_creation_input_tokens
        total.cache_read_input_tokens += it.cache_read_input_tokens
        total.input_cost_usd += it.input_cost_usd
        total.output_cost_usd += it.output_cost_usd
        total.cache_creation_cost_usd += it.cache_creation_cost_usd
        total.cache_read_cost_usd += it.cache_read_cost_usd
        total.total_cost_usd += it.total_cost_usd
    # Round totals.
    for f in (
        "input_cost_usd",
        "output_cost_usd",
        "cache_creation_cost_usd",
        "cache_read_cost_usd",
        "total_cost_usd",
    ):
        setattr(total, f, round(getattr(total, f), 6))
    return total
