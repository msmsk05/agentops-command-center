from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.integrations import router as integrations_router
from app.api.monitoring import router as monitoring_router
from app.api.runs import router as runs_router
from app.config.settings import get_settings

settings = get_settings()
app = FastAPI(title='AgentOps Command Center API', version='2.0.0')
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=['GET', 'POST'], allow_headers=['*'])
app.include_router(health_router)
app.include_router(runs_router)
app.include_router(monitoring_router)
app.include_router(integrations_router)

from app.protocols.a2a.server import mount_a2a

mount_a2a(app, settings.a2a_public_url)
