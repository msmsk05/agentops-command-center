from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_planner(model: Any) -> LlmAgent:
    return agent('planner', 'Planning specialist', 'Analyze the user objective and create an evidence-first execution plan. Return concrete research questions, decision criteria, and output requirements.', model, 'plan')
