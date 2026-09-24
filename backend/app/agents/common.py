from collections.abc import Callable
from typing import Any

from google.adk.agents import LlmAgent
from google.adk.tools.tool_context import ToolContext

from app.agents.schemas import QualityReview


def agent(name: str, description: str, instruction: str, model: Any, output_key: str, tools: list[Callable[..., Any]] | None = None, output_schema: Any = None) -> LlmAgent:
    return LlmAgent(name=name, description=description, model=model, instruction=instruction, output_key=output_key, tools=tools or [], output_schema=output_schema)


def make_quality_gate(threshold: float) -> Callable[..., dict[str, Any]]:
    def record_quality_review(quality_score: float, issues: list[str], passed: bool, tool_context: ToolContext) -> dict[str, Any]:
        actual_passed = passed and quality_score >= threshold
        tool_context.state['quality_score'] = quality_score
        tool_context.state['quality_issues'] = issues
        tool_context.state['quality_passed'] = actual_passed
        if actual_passed:
            tool_context.actions.escalate = True
        return {'quality_score': quality_score, 'issues': issues, 'passed': actual_passed}

    record_quality_review.__name__ = 'record_quality_review'
    record_quality_review.__doc__ = 'Persist a critic review and stop the quality loop when the configured threshold is met.'
    return record_quality_review
