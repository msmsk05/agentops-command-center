from typing import Any, Callable
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_risk_analyst(model: Any, compliance_review: Callable[..., Any]) -> LlmAgent:
    return agent('risk_analyst', 'Risk and uncertainty specialist', 'Identify risks, missing evidence, assumptions, contradictions, and uncertainty in {decomposition}. Delegate the compliance portion to the remote A2A compliance_review tool and report its actual response.', model, 'risk_findings', [compliance_review])
