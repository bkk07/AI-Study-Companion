"""Per-model LLM price estimates (USD per 1M tokens) — PRD §14 cost tracking.

These are PLACEHOLDER estimates for relative cost attribution across
features/models, not billing figures. Replace with current contract
pricing before any cost claim leaves the building. Unknown models return
None (cost unknown) rather than a fabricated number.
"""

from decimal import Decimal

# model -> {"input": $/1M prompt tokens, "output": $/1M completion tokens}
USD_PER_MTOK: dict[str, dict[str, float]] = {
    # Inception Labs Mercury 2.5 — paid promo rate per Inception docs
    # ($0.04/$0.15 per 1M in/out). Re-check if promo ends.
    "mercury-2.5": {"input": 0.04, "output": 0.15},
    # Groq hosted OSS models — placeholders against Groq list pricing.
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "qwen/qwen3-32b": {"input": 0.29, "output": 0.59},
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}


def estimate_cost_usd(
    model: str | None,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> Decimal | None:
    """Estimated cost for one call, or None when model/tokens unknown."""
    if not model or prompt_tokens is None or completion_tokens is None:
        return None
    prices = USD_PER_MTOK.get(model.strip())
    if prices is None:
        return None
    cost = (
        Decimal(str(prices["input"])) * prompt_tokens
        + Decimal(str(prices["output"])) * completion_tokens
    ) / Decimal(1_000_000)
    return cost.quantize(Decimal("0.000001"))
