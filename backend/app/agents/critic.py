from typing import Any, Callable
from google.adk.agents import LlmAgent
from app.agents.common import agent
from app.agents.schemas import QualityReview


def create_critic(model: Any, quality_gate: Callable[..., Any]) -> LlmAgent:
    return agent('critic', 'Quality evaluator', 'Evaluate the current aggregated answer for completeness, factual grounding, relevance, consistency, clarity, and unsupported assertions. Return JSON matching the quality schema, then call record_quality_review with the same values. Use the shared state from {investigation}.', model, 'critique', [quality_gate], QualityReview)
