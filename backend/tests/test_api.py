import os
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("LLM_API_KEYS", "test-key-one,test-key-two")
os.environ.setdefault("ENABLE_FAILURE_SIMULATION", "true")
from fastapi.testclient import TestClient
from app.main import app
from app.services import litellm_service

client = TestClient(app)

def test_health_shape():
    response = client.get("/health")
    assert response.status_code == 200
    assert set(("status", "keys_configured", "cache_enabled")) <= response.json().keys()

def test_unknown_session():
    response = client.get("/sessions/does-not-exist/messages")
    assert response.status_code == 404
    assert response.json()["detail"] == "session not found"

def test_failure_simulation_all_keys(monkeypatch):
    monkeypatch.setattr(litellm_service.settings, "enable_failure_simulation", True)
    response = client.post("/chat", json={"session_id": "test-fail", "message": "hello"},
                           headers={"X-Simulate-Failure": "*=429"})
    assert response.status_code == 503
    assert response.json() == {"detail": "all providers unavailable"}
