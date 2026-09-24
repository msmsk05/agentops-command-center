from __future__ import annotations

from typing import Any

from app.llm.pricing import estimate_cost
from app.telemetry.events import telemetry


def usage_from_event(event: Any) -> tuple[int | None, int | None, int | None]:
    metadata = getattr(event, 'usage_metadata', None)
    if metadata is None:
        return None, None, None
    input_tokens = getattr(metadata, 'prompt_token_count', None)
    output_tokens = getattr(metadata, 'candidates_token_count', None)
    total_tokens = getattr(metadata, 'total_token_count', None)
    return input_tokens, output_tokens, total_tokens


async def record_adk_event(run_id: str, event: Any, model: str) -> None:
    author = getattr(event, 'author', 'workflow')
    input_tokens, output_tokens, total_tokens = usage_from_event(event)
    cost = estimate_cost(model, input_tokens, output_tokens)
    telemetry.record_usage(run_id, input_tokens, output_tokens, cost)
    content = getattr(event, 'content', None)
    detail = 'ADK event emitted'
    if content and getattr(content, 'parts', None):
        detail = ' '.join(getattr(part, 'text', '') for part in content.parts if getattr(part, 'text', None))[:240] or detail
    await telemetry.emit(run_id, author, detail, 'agent', protocol='ADK', model=model,
                         input_tokens=input_tokens, output_tokens=output_tokens,
                         total_tokens=total_tokens, estimated_cost=cost,
                         final=bool(getattr(event, 'is_final_response', lambda: False)()))
