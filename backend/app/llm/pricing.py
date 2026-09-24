from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


PRICING: dict[str, ModelPricing] = {
    'gpt-4o': ModelPricing(input_per_million=2.50, output_per_million=10.00),
    'gpt-4o-mini': ModelPricing(input_per_million=0.15, output_per_million=0.60),
}


def estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    if input_tokens is None or output_tokens is None:
        return None
    pricing = next((value for key, value in PRICING.items() if key in model.lower()), None)
    if pricing is None:
        return None
    return round((input_tokens / 1_000_000 * pricing.input_per_million) + (output_tokens / 1_000_000 * pricing.output_per_million), 8)
