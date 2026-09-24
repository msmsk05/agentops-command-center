from mcp.server.fastmcp import FastMCP

from app.protocols.mcp.tools import get_company_profile, retrieve_market_data, search_documents

mcp = FastMCP('agentops-knowledge-server', stateless_http=True, json_response=True)


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
