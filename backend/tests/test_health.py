from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_is_public():
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_agent_card_exposes_a2a_capabilities():
    response = client.get('/.well-known/agent.json')
    assert response.status_code == 200
    assert response.json()['protocol'] == 'A2A'
