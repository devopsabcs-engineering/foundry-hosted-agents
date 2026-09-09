import json
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import FoundryClient, SessionStore, Settings, create_app
from auth import Identity

SETTINGS = Settings("tenant", "client", "pilot", "https://test.services.ai.azure.com/responses")


class TestAuth:
    async def authorize(self, header):
        if header not in ("Bearer alice", "Bearer bob"):
            raise HTTPException(401, "Sign in")
        return Identity("tenant", header.split()[1])


class FakeAgent:
    def __init__(self):
        self.inputs = []
        self.fail = False

    async def events(self, messages):
        self.inputs.append(messages)
        if self.fail:
            raise ValueError("secret upstream error details")
        yield {"type": "answer", "text": "Assessment complete."}


@pytest.fixture
def client():
    agent = FakeAgent()
    app = create_app(SETTINGS, TestAuth(), agent)
    with TestClient(app) as client:
        client.headers["Authorization"] = "Bearer alice"
        yield client, agent, app.state.store


def test_real_client_lifespan_with_managed_identity(monkeypatch):
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://localhost/identity")
    monkeypatch.setenv("IDENTITY_HEADER", "test-only")
    application = create_app(SETTINGS, TestAuth())
    with TestClient(application) as startup_client:
        assert isinstance(application.state.upstream, FoundryClient)
        assert startup_client.get("/healthz").json() == {"status": "ok"}
    assert application.state.upstream.http.is_closed


def test_anonymous_denied(client):
    client, _, _ = client
    client.headers.clear()
    assert client.post("/api/conversations").status_code == 401
    assert client.get("/api/me").status_code == 401


def test_users_cannot_read_write_or_delete_other_sessions(client):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    client.headers["Authorization"] = "Bearer bob"
    assert client.post(f"/api/conversations/{identifier}/messages", json={"text": "Hi"}).status_code == 404
    assert client.delete(f"/api/conversations/{identifier}").status_code == 404
    assert agent.inputs == []


def test_multiturn_history_is_owned_by_server(client):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    for text in ["First incident", "Explain the recommendation"]:
        response = client.post(route, json={"text": text})
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert [event["type"] for event in events] == ["status", "answer", "done"]
    assert len(agent.inputs[1]) == 3
    assert agent.inputs[1][1] == {"role": "assistant", "content": "Assessment complete."}
    assert client.post(route, json={"text": "Hi", "history": []}).status_code == 422


@pytest.mark.parametrize("text", ["", "   ", "x" * 8001])
def test_invalid_message_rejected(client, text):
    client, agent, _ = client
    identifier = client.post("/api/conversations").json()["id"]
    assert client.post(f"/api/conversations/{identifier}/messages", json={"text": text}).status_code == 422
    assert agent.inputs == []


def test_failed_response_does_not_poison_history(client):
    client, agent, store = client
    identifier = client.post("/api/conversations").json()["id"]
    agent.fail = True
    response = client.post(f"/api/conversations/{identifier}/messages", json={"text": "Hi"})
    assert '"type": "error"' in response.text
    assert "secret upstream" not in response.text
    assert store.sessions[identifier].messages == []
    assert not store.sessions[identifier].busy


def test_busy_session_and_turn_limit(client):
    client, _, store = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    store.sessions[identifier].busy = True
    assert client.post(route, json={"text": "Hi"}).status_code == 409
    assert client.delete(f"/api/conversations/{identifier}").status_code == 409
    store.sessions[identifier].busy = False
    store.sessions[identifier].messages = [{}] * 40
    assert client.post(route, json={"text": "Hi"}).status_code == 409


def test_expired_session_and_capacity():
    store = SessionStore(SETTINGS)
    owner = Identity("tenant", "alice")
    identifier = store.create(owner)
    store.sessions[identifier].touched = time.monotonic() - 3601
    with pytest.raises(HTTPException) as failure:
        store.get(identifier, owner)
    assert failure.value.status_code == 404
    for _ in range(5):
        store.create(owner)
    with pytest.raises(HTTPException) as failure:
        store.create(owner)
    assert failure.value.status_code == 429


def test_no_secret_in_public_configuration(client):
    client, _, _ = client
    response = client.get("/api/config")
    assert set(response.json()) == {"tenantId", "clientId", "scope", "environment"}
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]