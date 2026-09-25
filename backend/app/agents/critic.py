from typing import Any, Callable
from google.adk.agents import LlmAgent
from app.agents.common import agent, enforce_quality_review_recorded, reset_quality_review_marker
from app.agents.schemas import QualityReview


def create_critic(model: Any, quality_gate: Callable[..., Any]) -> LlmAgent:
    critic = agent('critic', 'Quality evaluator', 'Evaluate {current_investigation} for completeness, factual grounding, relevance, consistency, clarity, and unsupported assertions. First call record_quality_review exactly once with your computed quality_score, issues, and passed. Then answer with exactly the JSON object the tool returned, matching the quality schema.', model, 'critique', [quality_gate], QualityReview)
    critic.before_agent_callback = reset_quality_review_marker
    critic.after_agent_callback = enforce_quality_review_recorded
    return critic
