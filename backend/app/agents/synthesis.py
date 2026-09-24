from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent
from app.agents.schemas import SynthesisOutput


def create_synthesis(model: Any) -> LlmAgent:
    return agent('synthesis', 'Executive synthesis specialist', 'Create the final executive response from {revised_investigation} and the evidence in shared state. Make recommendations, tradeoffs, risks, and next actions clear. Return JSON matching the synthesis schema.', model, 'final_response', output_schema=SynthesisOutput)
