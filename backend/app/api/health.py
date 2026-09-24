from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings

router = APIRouter(tags=['health'])


@router.get('/health')
async def health() -> dict:
    return {'status': 'ok', 'service': 'agentops-api'}


@router.get('/ready')
async def ready(settings: Settings = Depends(get_settings)) -> dict:
    azure = {'configured': settings.azure_configured}
    mcp = {'configured': settings.mcp_configured, 'status': 'healthy' if settings.mcp_configured else 'unconfigured'}
    a2a = {'configured': settings.a2a_configured, 'status': 'healthy' if settings.a2a_configured else 'unconfigured'}
    status = 'ready' if settings.azure_configured and settings.mcp_configured and settings.a2a_configured else 'not_ready'
    return {'status': status, 'azure_openai': azure, 'mcp': mcp, 'a2a': a2a}
