from __future__ import annotations

from typing import Any

import pytest

from app.agents.common import enforce_quality_review_recorded, make_quality_gate, reset_quality_review_marker
from app.agents.compliance import create_compliance_reviewer
from app.config.settings import Settings
from app.llm.pricing import estimate_cost
from app.telemetry.adk import record_adk_event
from app.telemetry.events import TelemetryStore
from app.workflows.main_workflow import build_workflow

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


class _StubActions:
    def __init__(self) -> None:
        self.escalate: bool | None = None


class _StubToolContext:
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = state if state is not None else {}
        self.actions = _StubActions()


class _StubCallbackContext:
    def __init__(self, state: dict[str, Any] | None = None) -> None:
        self.state: dict[str, Any] = state if state is not None else {}


# ------------------------------------------------------------------
# Issue 2: Critic structured output / tool state parsing
# ------------------------------------------------------------------

def test_record_quality_review_coerces_malformed_model_arguments():
    gate = make_quality_gate(threshold=0.85)
    ctx = _StubToolContext()

    result = gate(quality_score='0.92', issues='Minor formatting nit', passed='true', tool_context=ctx)

    assert result == {'quality_score': 0.92, 'issues': ['Minor formatting nit'], 'passed': True}
    assert ctx.state['quality_score'] == 0.92
    assert ctx.state['quality_passed'] is True
    assert ctx.state['_quality_review_recorded'] is True
    assert ctx.actions.escalate is True


def test_record_quality_review_clamps_out_of_range_score_and_fails_closed():
    gate = make_quality_gate(threshold=0.85)
    ctx = _StubToolContext()

    result = gate(quality_score=5, issues=[], passed=True, tool_context=ctx)

    assert result['quality_score'] == 1.0
    assert result['passed'] is True

    ctx2 = _StubToolContext()
    result2 = gate(quality_score='not-a-number', issues=None, passed=True, tool_context=ctx2)
    assert result2['quality_score'] == 0.0
    assert result2['issues'] == []
    assert result2['passed'] is False
    assert ctx2.actions.escalate is None


# ------------------------------------------------------------------
# Issue 1: Quality loop must not silently skip Revision when the Critic's
# tool call never actually fires against the real Azure OpenAI/ADK path.
# ------------------------------------------------------------------

def test_reset_marker_then_enforce_fallback_when_tool_never_invoked():
    ctx = _StubCallbackContext(state={'quality_score': 0.91, 'quality_passed': True})
    reset_quality_review_marker(ctx)
    assert ctx.state['_quality_review_recorded'] is False

    # Critic's model turn produced text but never called record_quality_review.
    enforce_quality_review_recorded(ctx)

    assert ctx.state['quality_passed'] is False
    assert ctx.state['quality_score'] == 0.0
    assert 'did not invoke record_quality_review' in ctx.state['quality_issues'][0]


def test_enforce_quality_review_recorded_is_a_noop_when_tool_did_fire():
    ctx = _StubCallbackContext(state={'_quality_review_recorded': True, 'quality_score': 0.9, 'quality_passed': True})

    enforce_quality_review_recorded(ctx)

    assert ctx.state['quality_score'] == 0.9
    assert ctx.state['quality_passed'] is True


# ------------------------------------------------------------------
# Issue 3: A2A must actually execute via a dedicated post-loop stage.
# ------------------------------------------------------------------

def test_compliance_reviewer_is_wired_to_the_real_a2a_client_method():
    calls: list[str] = []

    async def fake_assess_compliance(request: str) -> str:
        calls.append(request)
        return 'compliant'

    reviewer = create_compliance_reviewer('test-model', fake_assess_compliance)

    assert reviewer.name == 'compliance_reviewer'
    assert reviewer.output_key == 'compliance_review'
    assert fake_assess_compliance in reviewer.tools
    assert 'current_investigation' in reviewer.instruction


class _FakeA2aClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def assess_compliance(self, request: str) -> str:
        self.calls.append(request)
        return 'compliant'


class _FakeMcp:
    def search_documents(self, *args, **kwargs):
        raise NotImplementedError

    def get_company_profile(self, *args, **kwargs):
        raise NotImplementedError

    def retrieve_market_data(self, *args, **kwargs):
        raise NotImplementedError


def test_workflow_places_compliance_stage_between_quality_loop_and_synthesis_using_real_a2a_client():
    a2a_client = _FakeA2aClient()
    settings = Settings(quality_threshold=0.85, max_loop_iterations=3)
    workflow = build_workflow(settings, mcp_client=_FakeMcp(), a2a_client=a2a_client, model='test-model')

    names = [sub_agent.name for sub_agent in workflow.sub_agents]
    assert names.index('quality_loop') < names.index('compliance_reviewer') < names.index('synthesis')

    compliance_reviewer = workflow.sub_agents[names.index('compliance_reviewer')]
    assert a2a_client.assess_compliance in compliance_reviewer.tools


# ------------------------------------------------------------------
# Issue 4: cost accounting must not silently drop to zero for
# arbitrary Azure deployment aliases that don't match a PRICING key.
# ------------------------------------------------------------------

class _FakeUsageMetadata:
    def __init__(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        self.prompt_token_count = input_tokens
        self.candidates_token_count = output_tokens
        self.total_token_count = total_tokens


class _FakeAdkEvent:
    def __init__(self, input_tokens: int, output_tokens: int, total_tokens: int) -> None:
        self.author = 'synthesis'
        self.usage_metadata = _FakeUsageMetadata(input_tokens, output_tokens, total_tokens)
        self.content = None

    def is_final_response(self) -> bool:
        return True


def test_estimate_cost_returns_none_for_an_arbitrary_deployment_alias():
    # Documents the underlying bug: deployment aliases rarely match a PRICING key.
    assert estimate_cost('prod-analyst-v2', 109_922, 19_387) is None


async def test_record_adk_event_uses_model_family_for_pricing_not_the_deployment_alias():
    store = TelemetryStore()
    run_id = 'run_00c80c67'
    store.create_run(run_id, trace_id='t', session_id='s', task='task')

    event = _FakeAdkEvent(input_tokens=109_922, output_tokens=19_387, total_tokens=129_309)

    import app.telemetry.adk as adk_module
    original_telemetry = adk_module.telemetry
    adk_module.telemetry = store
    try:
        await record_adk_event(run_id, event, model='prod-analyst-v2', pricing_model='gpt-4o')
    finally:
        adk_module.telemetry = original_telemetry

    run = store.runs[run_id]
    assert run['input_tokens'] == 109_922
    assert run['output_tokens'] == 19_387
    assert run['total_tokens'] == 129_309
    assert run['estimated_cost'] > 0
