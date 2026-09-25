from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.telemetry.events import telemetry

pytestmark = pytest.mark.anyio

client = TestClient(app)


@pytest.fixture
def anyio_backend():
    return 'asyncio'


async def _seed_two_runs() -> None:
    telemetry.reset()

    telemetry.create_run('run_a', trace_id='t-a', session_id='s-a', task='Analyze the competitive landscape ' * 10)
    await telemetry.emit('run_a', 'planner', 'Planner output', 'agent', protocol='ADK', model='gpt-4o',
                         input_tokens=50, output_tokens=20, total_tokens=70, estimated_cost=0.0005,
                         agent_latency_ms=None, final=True)
    telemetry.record_usage('run_a', 50, 20, 0.0005)
    await telemetry.emit('run_a', 'synthesis', 'Synthesis output', 'agent', protocol='ADK', model='gpt-4o',
                         input_tokens=50, output_tokens=30, total_tokens=80, estimated_cost=0.0005,
                         agent_latency_ms=120.5, final=True)
    telemetry.record_usage('run_a', 50, 30, 0.0005)
    await telemetry.emit('run_a', 'MCP / search_documents_tool', 'MCP tool call complete', 'tool',
                         protocol='MCP', tool='search_documents_tool', status='complete', duration_ms=200.0)
    await telemetry.emit('run_a', 'A2A / compliance-review', 'A2A task complete', 'protocol',
                         protocol='A2A', status='complete', duration_ms=300.0, remote_agent='http://compliance')
    telemetry.finish('run_a', 'complete')
    telemetry.runs['run_a']['duration_ms'] = 1000.0

    telemetry.create_run('run_b', trace_id='t-b', session_id='s-b', task='Short task')
    await telemetry.emit('run_b', 'MCP / search_documents_tool', 'MCP tool call error', 'tool',
                         protocol='MCP', tool='search_documents_tool', status='error', duration_ms=50.0)
    telemetry.record_usage('run_b', 10, 5, None)
    await telemetry.emit('run_b', 'ADK workflow', 'Workflow failed', 'system', status='error', error='boom')
    telemetry.finish('run_b', 'error', error='boom')
    telemetry.runs['run_b']['duration_ms'] = 500.0


async def test_summary_calculates_from_actual_stored_telemetry():
    await _seed_two_runs()

    response = client.get('/api/monitoring/summary')
    assert response.status_code == 200
    body = response.json()

    assert body['total_runs'] == 2
    assert body['active_runs'] == 0
    assert body['completed_runs'] == 1
    assert body['failed_runs'] == 1
    assert body['success_rate'] == 50.0
    assert body['avg_latency_ms'] == 750.0
    assert body['p50_latency_ms'] == 750.0
    assert body['p95_latency_ms'] == 975.0
    assert body['p99_latency_ms'] == 995.0
    assert body['total_input_tokens'] == 110
    assert body['total_output_tokens'] == 55
    assert body['total_tokens'] == 165
    assert body['estimated_cost'] == pytest.approx(0.001)
    assert body['agent_executions'] == 2
    assert body['tool_calls'] == 2
    assert body['mcp_calls'] == 2
    assert body['a2a_calls'] == 1
    assert body['errors'] == 2


async def test_summary_handles_no_runs_without_fabricating_values():
    telemetry.reset()

    response = client.get('/api/monitoring/summary')
    body = response.json()

    assert body['total_runs'] == 0
    assert body['success_rate'] is None
    assert body['avg_latency_ms'] is None
    assert body['estimated_cost'] is None


async def test_recent_runs_returns_known_fields_and_respects_limit():
    await _seed_two_runs()

    response = client.get('/api/monitoring/runs')
    assert response.status_code == 200
    by_id = {run['run_id']: run for run in response.json()['runs']}

    assert by_id['run_a']['status'] == 'complete'
    assert by_id['run_a']['trace_id'] == 't-a'
    assert by_id['run_a']['total_tokens'] == 150
    assert by_id['run_a']['estimated_cost'] == pytest.approx(0.001)
    assert len(by_id['run_a']['task_summary']) <= 140
    assert by_id['run_b']['status'] == 'error'
    assert by_id['run_b']['error'] == 'boom'
    assert by_id['run_b']['estimated_cost'] is None

    limited = client.get('/api/monitoring/runs', params={'limit': 1})
    assert len(limited.json()['runs']) == 1


async def test_latency_reports_real_measured_points_only():
    await _seed_two_runs()

    response = client.get('/api/monitoring/latency')
    body = response.json()

    assert sorted(point['run_id'] for point in body['workflow']['points']) == ['run_a', 'run_b']
    assert body['workflow']['p50_latency_ms'] == 750.0

    assert len(body['agent']['points']) == 1
    assert body['agent']['points'][0]['agent'] == 'synthesis'
    assert body['agent']['points'][0]['duration_ms'] == 120.5

    assert len(body['mcp']['points']) == 2
    assert body['mcp']['avg_latency_ms'] == 125.0

    assert len(body['a2a']['points']) == 1
    assert body['a2a']['points'][0]['duration_ms'] == 300.0


async def test_usage_totals_and_per_agent_breakdown():
    await _seed_two_runs()

    response = client.get('/api/monitoring/usage')
    body = response.json()

    assert body['totals']['input_tokens'] == 110
    assert body['totals']['output_tokens'] == 55
    assert body['totals']['total_tokens'] == 165
    assert body['totals']['estimated_cost'] == pytest.approx(0.001)

    by_run = {row['run_id']: row for row in body['by_run']}
    assert by_run['run_a']['estimated_cost'] == pytest.approx(0.001)
    assert by_run['run_b']['estimated_cost'] is None

    by_agent = {row['agent_name']: row for row in body['by_agent']}
    assert by_agent['planner']['total_tokens'] == 70
    assert by_agent['planner']['estimated_cost'] == pytest.approx(0.0005)
    assert by_agent['synthesis']['total_tokens'] == 80


async def test_protocols_reports_success_and_failure_counts():
    await _seed_two_runs()

    response = client.get('/api/monitoring/protocols')
    body = response.json()

    assert body['mcp']['call_count'] == 2
    assert body['mcp']['success_count'] == 1
    assert body['mcp']['failure_count'] == 1
    assert body['mcp']['average_latency_ms'] == 125.0

    assert body['a2a']['call_count'] == 1
    assert body['a2a']['success_count'] == 1
    assert body['a2a']['failure_count'] == 0
    assert body['a2a']['average_latency_ms'] == 300.0
    assert body['a2a']['recent_calls'][0]['run_id'] == 'run_a'


async def test_agents_only_counts_final_events_and_has_no_fabricated_failures():
    await _seed_two_runs()

    response = client.get('/api/monitoring/agents')
    by_agent = {row['agent_name']: row for row in response.json()['agents']}

    assert by_agent['planner']['executions'] == 1
    assert by_agent['planner']['successes'] == 1
    assert by_agent['planner']['failures'] == 0
    assert by_agent['planner']['average_latency_ms'] is None

    assert by_agent['synthesis']['executions'] == 1
    assert by_agent['synthesis']['average_latency_ms'] == 120.5
    assert by_agent['synthesis']['estimated_cost'] == pytest.approx(0.0005)


async def test_trace_endpoint_categorizes_events_and_preserves_ids():
    await _seed_two_runs()

    response = client.get('/api/monitoring/runs/run_a/trace')
    assert response.status_code == 200
    body = response.json()

    assert body['trace_id'] == 't-a'
    assert body['session_id'] == 's-a'
    assert body['status'] == 'complete'
    categories = {event['label']: event['category'] for event in body['events']}
    assert categories['planner'] == 'ADK'
    assert categories['synthesis'] == 'ADK'
    assert categories['MCP / search_documents_tool'] == 'MCP'
    assert categories['A2A / compliance-review'] == 'A2A'

    error_response = client.get('/api/monitoring/runs/run_b/trace')
    error_body = error_response.json()
    error_categories = {event['label']: event['category'] for event in error_body['events']}
    # status == 'error' takes priority over the event's own protocol tag.
    assert error_categories['MCP / search_documents_tool'] == 'error'
    assert error_categories['ADK workflow'] == 'error'


async def test_trace_endpoint_404_for_unknown_run():
    telemetry.reset()
    response = client.get('/api/monitoring/runs/does-not-exist/trace')
    assert response.status_code == 404
