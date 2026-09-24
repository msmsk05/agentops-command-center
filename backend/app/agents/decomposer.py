from typing import Any
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_decomposer(model: Any) -> LlmAgent:
    return agent('task_decomposer', 'Task decomposition specialist', 'Transform {plan} into structured subtasks for research, analysis, and risk review. Preserve the original user objective in every subtask.', model, 'decomposition')
