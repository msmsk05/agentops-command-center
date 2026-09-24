from fastapi import APIRouter, Depends

from app.config.settings import Settings, get_settings

router = APIRouter(prefix='/api/integrations', tags=['integrations'])


@router.get('')
async def integrations(settings: Settings = Depends(get_settings)) -> dict:
    return {
        'mcp': {'configured': settings.mcp_configured, 'status': 'configured' if settings.mcp_configured else 'unconfigured', 'server_url': settings.mcp_server_url, 'tools': ['search_documents_tool', 'get_company_profile_tool', 'retrieve_market_data_tool']},
        'a2a': {'configured': settings.a2a_configured, 'status': 'configured' if settings.a2a_configured else 'unconfigured', 'endpoint': settings.a2a_compliance_agent_url, 'agent': 'Compliance Agent'},
    }
