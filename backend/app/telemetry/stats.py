from __future__ import annotations


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank-with-interpolation percentile over real recorded values (no simulation)."""
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return round(ordered[0], 2)
    rank = pct / 100 * (len(ordered) - 1)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = rank - lower
    return round(ordered[lower] + (ordered[upper] - ordered[lower]) * fraction, 2)


def latency_summary(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {'avg_latency_ms': None, 'p50_latency_ms': None, 'p95_latency_ms': None, 'p99_latency_ms': None, 'sample_size': 0}
    return {
        'avg_latency_ms': round(sum(values) / len(values), 2),
        'p50_latency_ms': percentile(values, 50),
        'p95_latency_ms': percentile(values, 95),
        'p99_latency_ms': percentile(values, 99),
        'sample_size': len(values),
    }


def sum_known_cost(costs: list[float | None]) -> float | None:
    """Sums only the costs that were actually computed; returns None (not 0) when pricing was never known."""
    known = [cost for cost in costs if cost is not None]
    if not known:
        return None
    return round(sum(known), 8)
