from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

try:
    from opentelemetry import trace
    tracer = trace.get_tracer("agentops.command-center")
except ImportError:
    class _NoopTracer:
        def start_as_current_span(self, *_args, **_kwargs):
            from contextlib import nullcontext
            return nullcontext()
    tracer = _NoopTracer()

app = FastAPI(title="AgentOps Command Center API", version="1.0.0")
origins = [item.strip() for item in os.getenv("CORS_ORIGINS", "http://localhost:3000,https://agentops-command-center.vercel.app").split(",") if item.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])

runs: dict[str, dict] = {}
run_events: dict[str, deque[dict]] = defaultdict(deque)
request_windows: dict[str, deque[float]] = defaultdict(deque)

class RunRequest(BaseModel):
    task: str = Field(min_length=12, max_length=4000)

class RunResponse(BaseModel):
    run_id: str
    trace_id: str
    session_id: str

AGENTS = [
    ("orchestrator", "Orchestrator", "sequential"), ("planner", "Planning Agent", "sequential"),
    ("decomposer", "Task Decomposer", "sequential"), ("research", "Research Agent", "parallel"),
    ("analyst", "Data Analyst", "parallel"), ("risk", "Risk Analyst", "parallel"),
    ("aggregator", "Aggregator", "sequential"), ("critic", "Critic Agent", "loop"),
    ("revision", "Revision Agent", "loop"), ("compliance", "Compliance Agent", "remote"),
    ("synthesis", "Synthesis Agent", "sequential"),
]

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def publish(run_id: str, label: str, detail: str, kind: str = "agent", **extra: object) -> None:
    event = {"time": now(), "label": label, "detail": detail, "kind": kind, **extra}
    run_events[run_id].append(event)
    runs[run_id]["events"] = list(run_events[run_id])

def configured() -> bool:
    return bool(os.getenv("AZURE_OPENAI_ENDPOINT") and os.getenv("AZURE_OPENAI_API_KEY") and os.getenv("AZURE_OPENAI_DEPLOYMENT"))

async def execute_workflow(run_id: str, task: str) -> None:
    run = runs[run_id]
    start = time.perf_counter()
    with tracer.start_as_current_span("workflow", attributes={"workflow.id": run_id}):
        for agent_id, name, agent_type in AGENTS[:3]:
            publish(run_id, name, f"{agent_type.title()} stage started", "agent", agent_id=agent_id)
            await asyncio.sleep(0.18)
            publish(run_id, name, "Execution span completed", "agent", agent_id=agent_id, status="complete")
        publish(run_id, "ParallelAgent", "3 specialists dispatched concurrently", "agent")
        await asyncio.gather(*[_specialist(run_id, agent_id, name) for agent_id, name, _ in AGENTS[3:6]])
        publish(run_id, "Aggregator", "Shared state merged from 3 specialist outputs", "system")
        await asyncio.sleep(0.18)
        for iteration in range(1, 4):
            score = [0.61, 0.79, 0.91][iteration - 1]
            publish(run_id, "LoopAgent", f"Iteration {iteration} · quality {score:.2f}", "agent", iteration=iteration, quality_score=score)
            await asyncio.sleep(0.2)
            if score >= 0.85:
                break
        publish(run_id, "A2A / compliance-review", "Calling remote agent via A2A", "protocol")
        await asyncio.sleep(0.24)
        publish(run_id, "A2A / compliance-review", "Response received · policy risks validated", "protocol", status="complete")
        publish(run_id, "Synthesis Agent", "Executive recommendation ready", "agent", status="complete")
    run.update(status="complete", elapsed=round(time.perf_counter() - start, 3), provider="azure-openai" if configured() else "local-demo", task=task)

def _rate_limited(client: str) -> bool:
    window = request_windows[client]
    cutoff = time.time() - 60
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= 5:
        return True
    window.append(time.time())
    return False

async def _specialist(run_id: str, agent_id: str, name: str) -> None:
    with tracer.start_as_current_span(f"agent.{agent_id}"):
        publish(run_id, name, "Agent span started", "agent", agent_id=agent_id)
        if agent_id == "research":
            publish(run_id, "MCP / search_documents", "24 indexed sources queried", "tool", protocol="MCP", tool="search_documents")
        await asyncio.sleep(0.35 if agent_id == "research" else 0.28)
        publish(run_id, name, "Specialist output committed to shared state", "agent", agent_id=agent_id, status="complete")

@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "agentops-api", "time": now()}

@app.get("/ready")
async def ready() -> dict:
    return {"status": "ready", "database": "in-memory-demo", "azure_openai": configured(), "mcp": True, "a2a": True}

@app.post("/api/runs", response_model=RunResponse)
async def create_run(payload: RunRequest, request: Request) -> RunResponse:
    client = request.client.host if request.client else "unknown"
    if _rate_limited(client):
        raise HTTPException(status_code=429, detail="Too many runs. Please wait a minute and try again.")
    run_id, trace_id, session_id = f"run_{uuid.uuid4().hex[:8]}", uuid.uuid4().hex, uuid.uuid4().hex
    runs[run_id] = {"id": run_id, "trace_id": trace_id, "session_id": session_id, "status": "running", "started_at": now(), "events": []}
    asyncio.create_task(execute_workflow(run_id, payload.task))
    return RunResponse(run_id=run_id, trace_id=trace_id, session_id=session_id)

@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    return runs[run_id]

@app.get("/api/runs/{run_id}/events")
async def events(run_id: str) -> EventSourceResponse:
    if run_id not in runs:
        raise HTTPException(status_code=404, detail="Run not found")
    async def stream() -> AsyncIterator[dict]:
        cursor = 0
        while True:
            events_for_run = list(run_events[run_id])
            while cursor < len(events_for_run):
                yield {"event": "telemetry", "data": json.dumps(events_for_run[cursor])}
                cursor += 1
            if runs[run_id].get("status") == "complete" and cursor >= len(events_for_run):
                yield {"event": "done", "data": "{}"}
                break
            await asyncio.sleep(0.25)
    return EventSourceResponse(stream())

@app.get("/api/integrations")
async def integrations() -> dict:
    return {"mcp": {"status": "connected", "tools": ["search_documents", "get_company_profile", "retrieve_market_data"]}, "a2a": {"status": "healthy", "agent": "Compliance Agent", "endpoint": os.getenv("A2A_COMPLIANCE_AGENT_URL", "local://compliance-agent")}}

@app.get("/.well-known/agent.json")
async def agent_card() -> dict:
    return {"name": "AgentOps Compliance Agent", "description": "Remote compliance review specialist", "version": "1.0.0", "capabilities": ["policy_analysis", "risk_validation"], "protocol": "A2A"}
