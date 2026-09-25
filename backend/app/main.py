from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.monitoring import router as monitoring_router
from app.api.runs import router as runs_router
from app.config.settings import get_settings
from app.protocols.mcp.server import mcp

settings = get_settings()

# Built once so the FastAPI lifespan below can drive the same session manager instance mounted into the app.
mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(mcp_app.router.lifespan_context(mcp_app))
        yield


app = FastAPI(title='AgentOps Command Center API', version='2.0.0', lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['*'])
app.include_router(health_router)
app.include_router(runs_router)
app.include_router(monitoring_router)
app.include_router(integrations_router)

from app.protocols.a2a.server import mount_a2a

mount_a2a(app, settings.a2a_public_url)

# mcp_app already serves its own "/mcp" route internally, so mount at root to expose it at "/mcp".
app.mount('/', mcp_app)
