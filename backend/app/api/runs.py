from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from app.config.settings import Settings, get_settings
from app.protocols.a2a.client import A2AClient
from app.protocols.mcp.client import MCPClient
from app.repositories.runs import run_repository
from app.telemetry.events import telemetry
from app.workflows.runner import execute_adk_workflow

router = APIRouter(prefix='/api/runs', tags=['runs'])
request_windows: dict[str, deque[float]] = defaultdict(deque)


class RunRequest(BaseModel):
    task: str = Field(min_length=12, max_length=4000)


class RunResponse(BaseModel):
    run_id: str
    trace_id: str
    session_id: str


def _rate_limited(client: str) -> bool:
    window = request_windows[client]
    cutoff = time.time() - 60
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= 5:
        return True
    window.append(time.time())
    return False


@router.post('', response_model=RunResponse)
async def create_run(payload: RunRequest, request: Request, settings: Settings = Depends(get_settings)) -> RunResponse:
    client = request.client.host if request.client else 'unknown'
    if _rate_limited(client):
        raise HTTPException(status_code=429, detail='Too many runs. Please wait a minute and try again.')
    if not settings.azure_configured:
        raise HTTPException(status_code=503, detail='Azure OpenAI is not configured. Set DEMO_MODE=true only for explicit local tests.')
    if not settings.mcp_configured or not settings.a2a_configured:
        raise HTTPException(status_code=503, detail='MCP_SERVER_URL and A2A_COMPLIANCE_AGENT_URL are required for a real workflow.')
    run_id, trace_id, session_id = f'run_{uuid.uuid4().hex[:8]}', uuid.uuid4().hex, uuid.uuid4().hex
    telemetry.create_run(run_id, trace_id, session_id, payload.task)
    mcp_client = MCPClient(settings.mcp_server_url or '', run_id)
    a2a_client = A2AClient(settings.a2a_compliance_agent_url or '', run_id)
    asyncio.create_task(execute_adk_workflow(run_id, session_id, payload.task, settings, mcp_client, a2a_client))
    return RunResponse(run_id=run_id, trace_id=trace_id, session_id=session_id)


@router.get('/{run_id}')
async def get_run(run_id: str) -> dict:
    run = run_repository.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Run not found')
    return run


@router.get('/{run_id}/events')
async def events(run_id: str) -> EventSourceResponse:
    if run_repository.get(run_id) is None:
        raise HTTPException(status_code=404, detail='Run not found')

    async def stream() -> AsyncIterator[dict]:
        cursor = 0
        while True:
            events_for_run = run_repository.events(run_id)
            while cursor < len(events_for_run):
                yield {'event': 'telemetry', 'data': json.dumps(events_for_run[cursor])}
                cursor += 1
            if run_repository.get(run_id).get('status') in {'complete', 'error', 'canceled'} and cursor >= len(events_for_run):
                yield {'event': 'done', 'data': '{}'}
                break
            async with telemetry.waiters[run_id]:
                try:
                    await asyncio.wait_for(telemetry.waiters[run_id].wait(), timeout=15)
                except asyncio.TimeoutError:
                    yield {'event': 'heartbeat', 'data': '{}'}

    return EventSourceResponse(stream())
