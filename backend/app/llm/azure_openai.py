import os

from google.adk.models.lite_llm import LiteLlm

from app.config.settings import Settings


def create_azure_model(settings: Settings) -> LiteLlm:
    if not settings.azure_configured:
        raise RuntimeError('Azure OpenAI is not configured. Set DEMO_MODE=true for non-production graph tests.')
    os.environ['AZURE_API_KEY'] = settings.azure_openai_api_key or ''
    os.environ['AZURE_API_BASE'] = settings.azure_openai_endpoint or ''
    os.environ['AZURE_API_VERSION'] = settings.azure_openai_api_version
    return LiteLlm(model=f'azure/{settings.azure_openai_deployment}')
