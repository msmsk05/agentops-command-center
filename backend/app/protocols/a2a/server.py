from fastapi import FastAPI
from fastapi.responses import JSONResponse
from a2a.server.events.in_memory_queue_manager import InMemoryQueueManager
from a2a.server.request_handlers.default_request_handler_v2 import DefaultRequestHandlerV2
from a2a.server.routes.agent_card_routes import create_agent_card_routes
from a2a.server.routes.fastapi_routes import add_a2a_routes_to_fastapi
from a2a.server.routes.jsonrpc_routes import create_jsonrpc_routes
from a2a.server.routes.rest_routes import create_rest_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.request_handlers.response_helpers import agent_card_to_dict
from starlette.requests import Request
from starlette.routing import Route

from app.protocols.a2a.compliance_agent import ComplianceAgentExecutor, compliance_agent_card


def mount_a2a(app: FastAPI, public_url: str) -> None:
    card = compliance_agent_card(public_url)
    handler = DefaultRequestHandlerV2(agent_executor=ComplianceAgentExecutor(), task_store=InMemoryTaskStore(), agent_card=card, queue_manager=InMemoryQueueManager())
    async def compatibility_card(request: Request) -> JSONResponse:
        payload = agent_card_to_dict(card)
        payload['protocol'] = 'A2A'
        return JSONResponse(payload)

    card_routes = create_agent_card_routes(card)
    card_routes.append(Route('/.well-known/agent.json', endpoint=compatibility_card, methods=['GET']))
    add_a2a_routes_to_fastapi(app, agent_card_routes=card_routes, jsonrpc_routes=create_jsonrpc_routes(handler, rpc_url='/'), rest_routes=create_rest_routes(handler))
