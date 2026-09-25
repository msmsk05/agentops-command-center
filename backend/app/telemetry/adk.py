from __future__ import annotations

import time
from typing import Any

from app.llm.pricing import estimate_cost
from app.telemetry.events import telemetry

# Wall-clock timestamp of the previous ADK event per run, used to derive a real
# (measured, not simulated) per-event agent latency from actual event gaps.
_last_event_at: dict[str, float] = {}


def usage_from_event(event: Any) -> tuple[int | None, int | None, int | None]:
    metadata = getattr(event, 'usage_metadata', None)
    if metadata is None:
        return None, None, None
    input_tokens = getattr(metadata, 'prompt_token_count', None)
    output_tokens = getattr(metadata, 'candidates_token_count', None)
    total_tokens = getattr(metadata, 'total_token_count', None)
    return input_tokens, output_tokens, total_tokens


async def record_adk_event(run_id: str, event: Any, model: str, pricing_model: str | None = None) -> None:
    author = getattr(event, 'author', 'workflow')
    input_tokens, output_tokens, total_tokens = usage_from_event(event)
    cost = estimate_cost(pricing_model or model, input_tokens, output_tokens)
    telemetry.record_usage(run_id, input_tokens, output_tokens, cost)
    content = getattr(event, 'content', None)
    detail = 'ADK event emitted'
    if content and getattr(content, 'parts', None):
        detail = ' '.join(getattr(part, 'text', '') for part in content.parts if getattr(part, 'text', None))[:240] or detail
    now = time.perf_counter()
    previous = _last_event_at.get(run_id)
    agent_latency_ms = round((now - previous) * 1000, 2) if previous is not None else None
    _last_event_at[run_id] = now
    await telemetry.emit(run_id, author, detail, 'agent', protocol='ADK', model=model,
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         total_tokens=total_tokens, estimated_cost=cost, agent_latency_ms=agent_latency_ms,
                         final=bool(getattr(event, 'is_final_response', lambda: False)()))
