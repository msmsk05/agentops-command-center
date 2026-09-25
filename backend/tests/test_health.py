from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import get_settings

client = TestClient(app)

def test_health_is_public():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_agent_card_exposes_a2a_capabilities():
    response = client.get('/.well-known/agent.json')
    assert response.status_code == 200
    assert response.json()['protocol'] == 'A2A'

def test_agent_card_standard_endpoint_matches_legacy():
    response = client.get('/.well-known/agent-card.json')
    assert response.status_code == 200
    legacy = client.get('/.well-known/agent.json').json()
    assert response.json()['name'] == legacy['name']

def test_agent_card_default_public_url_is_localhost_for_local_dev():
    response = client.get('/.well-known/agent-card.json')
    interfaces = response.json()['supportedInterfaces']
    assert interfaces[0]['url'] == get_settings().a2a_public_url

def test_agent_card_uses_configured_public_url(monkeypatch):
    monkeypatch.setenv('A2A_PUBLIC_URL', 'https://compliance-agent.example-container-apps.io')
    get_settings.cache_clear()
    try:
        from app.protocols.a2a.compliance_agent import compliance_agent_card

        settings = get_settings()
        card = compliance_agent_card(settings.a2a_public_url)
        assert card.supported_interfaces[0].url == 'https://compliance-agent.example-container-apps.io'
    finally:
        monkeypatch.delenv('A2A_PUBLIC_URL', raising=False)
        get_settings.cache_clear()
