from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_risk_analyst(model: Any) -> LlmAgent:
    return agent('risk_analyst', 'Risk and uncertainty specialist', 'Identify risks, missing evidence, assumptions, contradictions, and uncertainty in {decomposition}. Note any compliance concerns for the dedicated compliance review stage to follow up on.', model, 'risk_findings')
