from urllib.parse import urlparse

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from app.config.settings import get_settings
from app.protocols.mcp.tools import get_company_profile, retrieve_market_data, search_documents


def _allowed_hosts() -> list[str]:
    # DNS-rebinding protection only allows loopback hosts by default; add the real deployment host(s) so
    # the mounted "/mcp" endpoint is reachable over its public/production Host header and under tests ("testserver").
    hosts = {'localhost', '127.0.0.1', 'testserver'}
    settings = get_settings()
    for url in (settings.a2a_public_url, settings.mcp_server_url):
        if url:
            host = urlparse(url).netloc
            if host:
                hosts.add(host)
    return sorted(hosts)


mcp = FastMCP(
    'agentops-knowledge-server',
    stateless_http=True,
    json_response=True,
    transport_security=TransportSecuritySettings(allowed_hosts=_allowed_hosts()),
)


@mcp.tool()
def search_documents_tool(query: str, limit: int = 5) -> list[dict]:
    return search_documents(query, limit)


@mcp.tool()
def get_company_profile_tool(company: str) -> dict:
    return get_company_profile(company)


@mcp.tool()
def retrieve_market_data_tool(segment: str = 'enterprise agents') -> list[dict]:
    return retrieve_market_data(segment)


if __name__ == '__main__':
    mcp.run(transport='streamable-http')
