from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.repositories.runs import run_repository
from app.telemetry.stats import latency_summary, percentile, sum_known_cost

router = APIRouter(prefix='/api/monitoring', tags=['monitoring'])

FINISHED_STATUSES = {'complete', 'error', 'canceled'}


def _run_cost(run: dict[str, Any]) -> float | None:
    return run.get('estimated_cost') if run.get('cost_known') else None


def _all_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for run in run_repository.list_runs():
        for event in run_repository.events(run['id']):
            events.append({**event, 'run_id': run['id']})
    return events


@router.get('/summary')
async def summary() -> dict:
    runs = run_repository.list_runs()
    events = _all_events()

    total_runs = len(runs)
    active_runs = sum(1 for run in runs if run['status'] == 'running')
    completed_runs = sum(1 for run in runs if run['status'] == 'complete')
    failed_runs = sum(1 for run in runs if run['status'] == 'error')
    finished_runs = sum(1 for run in runs if run['status'] in FINISHED_STATUSES)
    success_rate = round(completed_runs / finished_runs * 100, 2) if finished_runs else None

    durations = [run['duration_ms'] for run in runs if run.get('duration_ms') is not None]
    latency = latency_summary(durations)

    costs = [_run_cost(run) for run in runs]

    agent_executions = sum(1 for event in events if event.get('kind') == 'agent')
    tool_calls = sum(1 for event in events if event.get('kind') == 'tool')
    mcp_calls = sum(1 for event in events if event.get('protocol') == 'MCP')
    a2a_calls = sum(1 for event in events if event.get('protocol') == 'A2A')
    errors = sum(1 for event in events if event.get('status') == 'error')

    return {
        'total_runs': total_runs,
        'active_runs': active_runs,
        'completed_runs': completed_runs,
        'failed_runs': failed_runs,
        'success_rate': success_rate,
        'avg_latency_ms': latency['avg_latency_ms'],
        'p50_latency_ms': latency['p50_latency_ms'],
        'p95_latency_ms': latency['p95_latency_ms'],
        'p99_latency_ms': latency['p99_latency_ms'],
        'total_input_tokens': sum(run.get('input_tokens', 0) for run in runs),
        'total_output_tokens': sum(run.get('output_tokens', 0) for run in runs),
        'total_tokens': sum(run.get('total_tokens', 0) for run in runs),
        'estimated_cost': sum_known_cost(costs),
        'agent_executions': agent_executions,
        'tool_calls': tool_calls,
        'mcp_calls': mcp_calls,
        'a2a_calls': a2a_calls,
        'errors': errors,
    }


@router.get('/runs')
async def recent_runs(limit: int = Query(default=20, ge=1, le=200)) -> dict:
    runs = sorted(run_repository.list_runs(), key=lambda run: run['started_at'], reverse=True)[:limit]
    return {
        'runs': [
            {
                'run_id': run['id'],
                'trace_id': run['trace_id'],
                'status': run['status'],
                'task_summary': (run.get('task') or '')[:140],
                'started_at': run.get('started_at'),
                'finished_at': run.get('finished_at'),
                'duration_ms': run.get('duration_ms'),
                'total_tokens': run.get('total_tokens', 0),
                'estimated_cost': _run_cost(run),
                'error': run.get('error'),
            }
            for run in runs
        ]
    }


@router.get('/latency')
async def latency() -> dict:
    runs = run_repository.list_runs()
    events = _all_events()

    workflow_points = [
        {'run_id': run['id'], 'started_at': run.get('started_at'), 'duration_ms': run['duration_ms']}
        for run in runs
        if run.get('duration_ms') is not None
    ]
    agent_points = [
        {'run_id': event['run_id'], 'agent': event.get('label'), 'time': event.get('time'), 'duration_ms': event['agent_latency_ms']}
        for event in events
        if event.get('kind') == 'agent' and event.get('agent_latency_ms') is not None
    ]
    mcp_points = [
        {'run_id': event['run_id'], 'tool': event.get('tool'), 'time': event.get('time'), 'duration_ms': event['duration_ms']}
        for event in events
        if event.get('protocol') == 'MCP' and event.get('duration_ms') is not None
    ]
    a2a_points = [
        {'run_id': event['run_id'], 'remote_agent': event.get('remote_agent'), 'time': event.get('time'), 'duration_ms': event['duration_ms']}
        for event in events
        if event.get('protocol') == 'A2A' and event.get('duration_ms') is not None
    ]

    return {
        'workflow': {'points': workflow_points, **latency_summary([point['duration_ms'] for point in workflow_points])},
        'agent': {'points': agent_points, **latency_summary([point['duration_ms'] for point in agent_points])},
        'mcp': {'points': mcp_points, **latency_summary([point['duration_ms'] for point in mcp_points])},
        'a2a': {'points': a2a_points, **latency_summary([point['duration_ms'] for point in a2a_points])},
    }


@router.get('/usage')
async def usage() -> dict:
    runs = run_repository.list_runs()
    events = _all_events()
    adk_events = [event for event in events if event.get('kind') == 'agent']

    by_run = [
        {
            'run_id': run['id'],
            'input_tokens': run.get('input_tokens', 0),
            'output_tokens': run.get('output_tokens', 0),
            'total_tokens': run.get('total_tokens', 0),
            'estimated_cost': _run_cost(run),
        }
        for run in runs
    ]

    by_agent: dict[str, dict[str, Any]] = {}
    for event in adk_events:
        agent_name = event.get('label') or 'unknown'
        bucket = by_agent.setdefault(agent_name, {'agent_name': agent_name, 'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0, '_costs': []})
        bucket['input_tokens'] += event.get('input_tokens') or 0
        bucket['output_tokens'] += event.get('output_tokens') or 0
        bucket['total_tokens'] += event.get('total_tokens') or 0
        bucket['_costs'].append(event.get('estimated_cost'))

    by_agent_list = []
    for bucket in by_agent.values():
        costs = bucket.pop('_costs')
        bucket['estimated_cost'] = sum_known_cost(costs)
        by_agent_list.append(bucket)

    total_input = sum(run.get('input_tokens', 0) for run in runs)
    total_output = sum(run.get('output_tokens', 0) for run in runs)
    total_tokens = sum(run.get('total_tokens', 0) for run in runs)
    total_cost = sum_known_cost([_run_cost(run) for run in runs])

    return {
        'by_run': by_run,
        'by_agent': by_agent_list,
        'totals': {
            'input_tokens': total_input,
            'output_tokens': total_output,
            'total_tokens': total_tokens,
            'estimated_cost': total_cost,
        },
    }


@router.get('/protocols')
async def protocols() -> dict:
    events = _all_events()

    def _protocol_stats(protocol: str) -> dict[str, Any]:
        protocol_events = [event for event in events if event.get('protocol') == protocol]
        durations = [event['duration_ms'] for event in protocol_events if event.get('duration_ms') is not None]
        success_count = sum(1 for event in protocol_events if event.get('status') == 'complete')
        failure_count = sum(1 for event in protocol_events if event.get('status') == 'error')
        recent = sorted(protocol_events, key=lambda event: event.get('time') or '', reverse=True)[:10]
        return {
            'protocol': protocol,
            'call_count': len(protocol_events),
            'success_count': success_count,
            'failure_count': failure_count,
            'average_latency_ms': latency_summary(durations)['avg_latency_ms'],
            'p95_latency_ms': percentile(durations, 95),
            'recent_calls': [
                {
                    'run_id': event.get('run_id'),
                    'time': event.get('time'),
                    'label': event.get('label'),
                    'status': event.get('status'),
                    'duration_ms': event.get('duration_ms'),
                }
                for event in recent
            ],
        }

    return {'mcp': _protocol_stats('MCP'), 'a2a': _protocol_stats('A2A')}


@router.get('/agents')
async def agents() -> dict:
    events = [event for event in _all_events() if event.get('kind') == 'agent']

    by_agent: dict[str, dict[str, Any]] = {}
    for event in events:
        # Every observed ADK event for an agent implies that turn ran to completion (a run-halting
        # exception stops the event stream entirely), so there is no genuine per-agent failure
        # signal in current telemetry beyond the workflow-level run status.
        if not event.get('final'):
            continue
        agent_name = event.get('label') or 'unknown'
        bucket = by_agent.setdefault(agent_name, {
            'agent_name': agent_name, 'executions': 0, 'successes': 0, 'failures': 0,
            'total_tokens': 0, 'input_tokens': 0, 'output_tokens': 0, '_latencies': [], '_costs': [],
        })
        bucket['executions'] += 1
        bucket['successes'] += 1
        bucket['total_tokens'] += event.get('total_tokens') or 0
        bucket['input_tokens'] += event.get('input_tokens') or 0
        bucket['output_tokens'] += event.get('output_tokens') or 0
        if event.get('agent_latency_ms') is not None:
            bucket['_latencies'].append(event['agent_latency_ms'])
        bucket['_costs'].append(event.get('estimated_cost'))

    result = []
    for bucket in by_agent.values():
        latencies = bucket.pop('_latencies')
        costs = bucket.pop('_costs')
        bucket['average_latency_ms'] = latency_summary(latencies)['avg_latency_ms']
        bucket['estimated_cost'] = sum_known_cost(costs)
        result.append(bucket)

    return {'agents': result}


@router.get('/runs/{run_id}/trace')
async def trace(run_id: str) -> dict:
    run = run_repository.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Run not found')

    def _category(event: dict[str, Any]) -> str:
        if event.get('status') == 'error':
            return 'error'
        protocol = event.get('protocol')
        if protocol in {'ADK', 'MCP', 'A2A'}:
            return protocol
        return 'system'

    events = [{**event, 'category': _category(event)} for event in run_repository.events(run_id)]
    return {
        'run_id': run['id'],
        'trace_id': run['trace_id'],
        'session_id': run['session_id'],
        'status': run['status'],
        'started_at': run.get('started_at'),
        'finished_at': run.get('finished_at'),
        'duration_ms': run.get('duration_ms'),
        'error': run.get('error'),
        'events': events,
    }

