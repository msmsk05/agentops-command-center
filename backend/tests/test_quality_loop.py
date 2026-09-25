from __future__ import annotations

from typing import AsyncGenerator

import pytest
from google.adk.agents import BaseAgent, LoopAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agents.critic import create_critic
from app.agents.revision import create_revision_agent
from app.agents.synthesis import create_synthesis
from app.workflows.main_workflow import build_workflow

pytestmark = pytest.mark.anyio

QUALITY_THRESHOLD = 0.85


@pytest.fixture
def anyio_backend():
    return 'asyncio'


class FakeAggregator(BaseAgent):
    """Seeds the canonical draft the same way the real aggregator's output_key would."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={'current_investigation': 'draft-v0'}),
        )


class FakeCritic(BaseAgent):
    """Stands in for the LLM critic: pops the next scripted score and mimics record_quality_review."""

    scores: list[float] = []

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        index = ctx.session.state.get('critic_calls', 0)
        score = self.scores[index]
        passed = score >= QUALITY_THRESHOLD
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(
                state_delta={'critic_calls': index + 1, 'quality_score': score, 'quality_passed': passed},
                escalate=passed,
            ),
        )


class FakeRevision(BaseAgent):
    """Stands in for the LLM revision agent: overwrites the canonical draft, like the real output_key."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        current = ctx.session.state.get('current_investigation')
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={'current_investigation': f'{current}+revised'}),
        )


class FakeSynthesis(BaseAgent):
    """Fails exactly like the real bug did if the canonical draft key is missing."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        if 'current_investigation' not in ctx.session.state:
            raise KeyError("Context variable not found: `current_investigation` in agent 'synthesis'.")
        yield Event(
            invocation_id=ctx.invocation_id,
            author=self.name,
            branch=ctx.branch,
            actions=EventActions(state_delta={'final_response': ctx.session.state['current_investigation']}),
        )


async def _run_workflow(scores: list[float]) -> dict:
    critic = FakeCritic(name='critic', scores=scores)
    revision = FakeRevision(name='revision')
    loop = LoopAgent(name='quality_loop', sub_agents=[critic, revision], max_iterations=3)
    workflow = SequentialAgent(
        name='orchestrator',
        sub_agents=[FakeAggregator(name='aggregator'), loop, FakeSynthesis(name='synthesis')],
    )
    session_service = InMemorySessionService()
    session = await session_service.create_session(app_name='test', user_id='u1', session_id='s1', state={})
    runner = Runner(agent=workflow, app_name='test', session_service=session_service)
    message = types.Content(role='user', parts=[types.Part(text='go')])
    async for _ in runner.run_async(user_id='u1', session_id='s1', new_message=message):
        pass
    updated = await session_service.get_session(app_name='test', user_id='u1', session_id='s1')
    assert updated is not None
    return updated.state


async def test_case_a_first_pass_skips_revision_and_uses_latest_draft():
    state = await _run_workflow(scores=[0.91])

    assert state['quality_score'] == 0.91
    assert state['current_investigation'] == 'draft-v0'
    assert state['final_response'] == 'draft-v0'
    assert 'revised_investigation' not in state


async def test_case_b_failed_pass_runs_revision_then_synthesis_uses_revised_draft():
    state = await _run_workflow(scores=[0.76, 0.9])

    assert state['critic_calls'] == 2
    assert state['quality_score'] == 0.9
    assert state['current_investigation'] == 'draft-v0+revised'
    assert state['final_response'] == 'draft-v0+revised'


async def test_loop_terminates_deterministically_when_threshold_never_met():
    state = await _run_workflow(scores=[0.5, 0.6, 0.7])

    assert state['critic_calls'] == 3
    assert state['current_investigation'] == 'draft-v0+revised+revised+revised'
    assert state['final_response'] == 'draft-v0+revised+revised+revised'


def test_real_agents_share_the_canonical_current_investigation_state_key():
    model = 'test-model'
    critic = create_critic(model, lambda **_: {})
    revision = create_revision_agent(model)
    synthesis = create_synthesis(model)

    assert 'current_investigation' in critic.instruction
    assert 'current_investigation' in revision.instruction
    assert revision.output_key == 'current_investigation'
    assert 'current_investigation' in synthesis.instruction
    assert 'revised_investigation' not in synthesis.instruction


def test_workflow_wires_aggregator_output_into_canonical_state_key(monkeypatch):
    from app.config.settings import Settings

    settings = Settings(quality_threshold=QUALITY_THRESHOLD, max_loop_iterations=3)
    workflow = build_workflow(settings, mcp_client=_FakeMcp(), a2a_client=_FakeA2a(), model='test-model')

    aggregator = workflow.sub_agents[3]
    quality_loop = workflow.sub_agents[4]
    compliance_reviewer = workflow.sub_agents[5]
    synthesis = workflow.sub_agents[6]

    assert aggregator.output_key == 'current_investigation'
    assert isinstance(quality_loop, LoopAgent)
    assert quality_loop.max_iterations == 3
    assert compliance_reviewer.name == 'compliance_reviewer'
    assert compliance_reviewer.output_key == 'compliance_review'
    assert 'current_investigation' in synthesis.instruction
    assert 'compliance_review' in synthesis.instruction


class _FakeMcp:
    def search_documents(self, *args, **kwargs):
        raise NotImplementedError

    def get_company_profile(self, *args, **kwargs):
        raise NotImplementedError

    def retrieve_market_data(self, *args, **kwargs):
        raise NotImplementedError


class _FakeA2a:
    def assess_compliance(self, *args, **kwargs):
        raise NotImplementedError
