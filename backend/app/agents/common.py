from collections.abc import Callable
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext

from app.agents.schemas import QualityReview


def agent(name: str, description: str, instruction: str, model: Any, output_key: str, tools: list[Callable[..., Any]] | None = None, output_schema: Any = None) -> LlmAgent:
    return LlmAgent(name=name, description=description, model=model, instruction=instruction, output_key=output_key, tools=tools or [], output_schema=output_schema)


def _coerce_quality_score(value: Any) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        score = 0.0
    return max(0.0, min(1.0, score))


def _coerce_issues(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value:
        return [value]
    return []


def _coerce_passed(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {'true', 'yes', '1'}
    return bool(value)


def make_quality_gate(threshold: float) -> Callable[..., dict[str, Any]]:
    def record_quality_review(quality_score: float, issues: list[str], passed: bool, tool_context: ToolContext) -> dict[str, Any]:
        score = _coerce_quality_score(quality_score)
        normalized_issues = _coerce_issues(issues)
        actual_passed = _coerce_passed(passed) and score >= threshold
        tool_context.state['quality_score'] = score
        tool_context.state['quality_issues'] = normalized_issues
        tool_context.state['quality_passed'] = actual_passed
        tool_context.state['_quality_review_recorded'] = True
        if actual_passed:
            tool_context.actions.escalate = True
        return {'quality_score': score, 'issues': normalized_issues, 'passed': actual_passed}

    record_quality_review.__name__ = 'record_quality_review'
    record_quality_review.__doc__ = 'Persist a critic review and stop the quality loop when the configured threshold is met.'
    return record_quality_review


def reset_quality_review_marker(callback_context: CallbackContext) -> None:
    """Runs before each Critic turn so a stale mark from a prior loop iteration can't hide a missed tool call."""
    callback_context.state['_quality_review_recorded'] = False


def enforce_quality_review_recorded(callback_context: CallbackContext) -> None:
    """Runs after each Critic turn; if record_quality_review never fired, force a failing (non-escalating) review so the loop still advances to Revision instead of silently reaching Synthesis."""
    if callback_context.state.get('_quality_review_recorded'):
        return
    callback_context.state['quality_score'] = 0.0
    callback_context.state['quality_issues'] = ['Critic did not invoke record_quality_review this turn; forcing a revision pass.']
    callback_context.state['quality_passed'] = False

