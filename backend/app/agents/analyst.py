from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_analyst(model: Any) -> LlmAgent:
    return agent('data_analyst', 'Data analysis specialist', 'Analyze the research objective and decomposition in {decomposition}. Produce explicit comparisons, patterns, calculations, and evidence limitations. Do not invent data.', model, 'analysis_findings')
