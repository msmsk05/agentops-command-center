import httpx
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.main import app, lifespan

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return 'asyncio'


async def test_mcp_endpoint_is_mounted_and_serves_real_tool_call():
    async with lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as http_client:
            async with streamable_http_client('http://testserver/mcp', http_client=http_client) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    tools = await session.list_tools()
                    tool_names = {tool.name for tool in tools.tools}
                    assert {'search_documents_tool', 'get_company_profile_tool', 'retrieve_market_data_tool'} <= tool_names

                    result = await session.call_tool('search_documents_tool', {'query': 'specialization coordination', 'limit': 5})
                    assert result.isError is not True
                    assert len(result.content) > 0
