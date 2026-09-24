from typing import Any, Callable
from google.adk.agents import LlmAgent
from app.agents.common import agent


def create_researcher(model: Any, search_documents: Callable[..., Any], get_company_profile: Callable[..., Any], retrieve_market_data: Callable[..., Any]) -> LlmAgent:
    return agent('research', 'Evidence research specialist', 'Use the MCP tools to gather relevant source documents, company profiles, and market data for {decomposition}. Cite the retrieved evidence in your output. Never claim a source was retrieved unless a tool result supports it.', model, 'research_findings', [search_documents, get_company_profile, retrieve_market_data])
