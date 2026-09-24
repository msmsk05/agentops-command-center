from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_revision_agent(model: Any) -> LlmAgent:
    return agent('revision', 'Revision specialist', 'Improve the aggregated answer using the latest {critique}. Resolve every supported issue, remove unsupported claims, and preserve evidence provenance.', model, 'revised_investigation')
