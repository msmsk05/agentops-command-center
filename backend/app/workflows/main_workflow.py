from __future__ import annotations

from typing import Any

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent

from app.agents.analyst import create_analyst
from app.agents.common import agent, make_quality_gate
from app.agents.critic import create_critic
from app.agents.decomposer import create_decomposer
from app.agents.planner import create_planner
from app.agents.research import create_researcher
from app.agents.revision import create_revision_agent
from app.agents.risk import create_risk_analyst
from app.agents.synthesis import create_synthesis
from app.config.settings import Settings
from app.llm.azure_openai import create_azure_model


def build_workflow(settings: Settings, mcp_client: Any, a2a_client: Any, model: Any = None) -> SequentialAgent:
    model = model or create_azure_model(settings)
    planner = create_planner(model)
    decomposer = create_decomposer(model)
    research = create_researcher(model, mcp_client.search_documents, mcp_client.get_company_profile, mcp_client.retrieve_market_data)
    analyst = create_analyst(model)
    risk = create_risk_analyst(model, a2a_client.assess_compliance)
    parallel = ParallelAgent(name='parallel_investigation', description='Concurrent research, analysis, and risk investigation', sub_agents=[research, analyst, risk])
    aggregator = agent('aggregator', 'Shared-state aggregator', 'Merge {research_findings}, {analysis_findings}, and {risk_findings} into an evidence-linked investigation brief. Preserve contradictions and uncertainty.', model, 'current_investigation')
    quality_gate = make_quality_gate(settings.quality_threshold)
    critic = create_critic(model, quality_gate)
    revision = create_revision_agent(model)
    quality_loop = LoopAgent(name='quality_loop', description='Critique and revision loop with a bounded iteration limit', sub_agents=[critic, revision], max_iterations=settings.max_loop_iterations)
    synthesis = create_synthesis(model)
    return SequentialAgent(name='orchestrator', description='Enterprise intelligence orchestration workflow', sub_agents=[planner, decomposer, parallel, aggregator, quality_loop, synthesis])
