from typing import Any, Callable
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_compliance_reviewer(model: Any, compliance_review: Callable[..., Any]) -> LlmAgent:
    return agent('compliance_reviewer', 'A2A compliance gate', 'Call the compliance_review tool exactly once with a concise compliance validation request summarizing {current_investigation}. Report the remote agent response verbatim, with no additional commentary.', model, 'compliance_review', [compliance_review])
