from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace


class TelemetryStore:
    def __init__(self) -> None:
        self.events: dict[str, deque[dict[str, Any]]] = defaultdict(deque)
        self.runs: dict[str, dict[str, Any]] = {}
        self.waiters: dict[str, asyncio.Condition] = defaultdict(asyncio.Condition)
        self.tracer = trace.get_tracer('agentops.command-center')

    def create_run(self, run_id: str, trace_id: str, session_id: str, task: str) -> None:
        self.runs[run_id] = {
            'id': run_id, 'trace_id': trace_id, 'session_id': session_id,
            'status': 'running', 'started_at': datetime.now(timezone.utc).isoformat(),
            'task': task, 'events': [], 'input_tokens': 0, 'output_tokens': 0,
            'total_tokens': 0, 'estimated_cost': 0.0, 'cost_known': False,
        }

    async def emit(self, run_id: str, label: str, detail: str, kind: str, **data: Any) -> None:
        event = {'time': datetime.now(timezone.utc).isoformat(), 'label': label, 'detail': detail, 'kind': kind, **data}
        self.events[run_id].append(event)
        if run_id in self.runs:
            self.runs[run_id]['events'] = list(self.events[run_id])
        async with self.waiters[run_id]:
            self.waiters[run_id].notify_all()

    def begin_span(self, name: str, run_id: str, **attributes: Any):
        return self.tracer.start_as_current_span(name, attributes={'run.id': run_id, **attributes})

    def record_usage(self, run_id: str, input_tokens: int | None, output_tokens: int | None, cost: float | None) -> None:
        run = self.runs[run_id]
        run['input_tokens'] += input_tokens or 0
        run['output_tokens'] += output_tokens or 0
        run['total_tokens'] = run['input_tokens'] + run['output_tokens']
        if cost is not None:
            run['estimated_cost'] = round(run['estimated_cost'] + cost, 8)
            run['cost_known'] = True

    def finish(self, run_id: str, status: str, error: str | None = None) -> None:
        run = self.runs[run_id]
        run['status'] = status
        run['finished_at'] = datetime.now(timezone.utc).isoformat()
        run['duration_ms'] = round((time.time() - _iso_to_epoch(run['started_at'])) * 1000, 2)
        if error:
            run['error'] = error

    def reset(self) -> None:
        """Test-only: clears all in-memory state. Never called from production code paths."""
        self.events.clear()
        self.runs.clear()
        self.waiters.clear()


def _iso_to_epoch(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


telemetry = TelemetryStore()
