from __future__ import annotations

import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from app.telemetry.events import telemetry


class MCPClient:
    def __init__(self, server_url: str, run_id: str | None = None) -> None:
        self.server_url = server_url
        self.run_id = run_id

    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> Any:
        started = time.perf_counter()
        status = 'error'
        try:
            async with streamable_http_client(self.server_url) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(tool, arguments)
                    status = 'complete'
                    return [content.model_dump() if hasattr(content, 'model_dump') else content for content in result.content]
        finally:
            if self.run_id:
                await telemetry.emit(self.run_id, f'MCP / {tool}', f'MCP tool call {status}', 'tool', protocol='MCP', tool=tool, status=status, duration_ms=round((time.perf_counter() - started) * 1000, 2))

    async def search_documents(self, query: str, limit: int = 5) -> Any:
        return await self.call_tool('search_documents_tool', {'query': query, 'limit': limit})

    async def get_company_profile(self, company: str) -> Any:
        return await self.call_tool('get_company_profile_tool', {'company': company})

    async def retrieve_market_data(self, segment: str = 'enterprise agents') -> Any:
        return await self.call_tool('retrieve_market_data_tool', {'segment': segment})
