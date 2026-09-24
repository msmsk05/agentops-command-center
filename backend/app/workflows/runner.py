from __future__ import annotations

import asyncio
from typing import Any

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.config.settings import Settings
from app.llm.pricing import estimate_cost
from app.telemetry.adk import record_adk_event
from app.telemetry.events import telemetry
from app.workflows.main_workflow import build_workflow


async def execute_adk_workflow(run_id: str, user_id: str, task: str, settings: Settings, mcp_client: Any, a2a_client: Any) -> None:
    model_name = settings.azure_openai_deployment or 'unconfigured'
    try:
        with telemetry.begin_span('adk.workflow', run_id, agent_id='orchestrator', model=model_name):
            workflow = build_workflow(settings, mcp_client, a2a_client)
            session_service = InMemorySessionService()
            await session_service.create_session(app_name='agentops', user_id=user_id, session_id=run_id, state={'task': task, 'quality_threshold': settings.quality_threshold})
            runner = Runner(agent=workflow, app_name='agentops', session_service=session_service)
            message = types.Content(role='user', parts=[types.Part(text=task)])
            async for event in runner.run_async(user_id=user_id, session_id=run_id, new_message=message):
                await record_adk_event(run_id, event, model_name)
            telemetry.finish(run_id, 'complete')
            await telemetry.emit(run_id, 'ADK workflow', 'Workflow completed from Runner event stream', 'system', status='complete', model=model_name)
    except asyncio.CancelledError:
        telemetry.finish(run_id, 'canceled')
        raise
    except Exception as exc:
        telemetry.finish(run_id, 'error', str(exc))
        await telemetry.emit(run_id, 'ADK workflow', 'Workflow failed', 'system', status='error', error=str(exc), model=model_name)
