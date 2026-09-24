from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    demo_mode: bool = False
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = '2024-10-21'
    mcp_server_url: str | None = None
    a2a_compliance_agent_url: str | None = None
    a2a_public_url: str = 'http://localhost:8080'
    cors_origins: str = 'http://localhost:3000,https://agentops-command-center.vercel.app'
    max_loop_iterations: int = 3
    quality_threshold: float = 0.85
    database_url: str = 'sqlite:///./agentops.db'
    otel_exporter_otlp_endpoint: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

    @property
    def azure_configured(self) -> bool:
        return all((self.azure_openai_endpoint, self.azure_openai_api_key, self.azure_openai_deployment))

    @property
    def mcp_configured(self) -> bool:
        return bool(self.mcp_server_url)

    @property
    def a2a_configured(self) -> bool:
        return bool(self.a2a_compliance_agent_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
