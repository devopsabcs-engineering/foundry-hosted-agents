import json
import time
import uuid

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


def test_successful_retry_replays_without_reinvocation_or_extra_turn(client):
    client, agent, store = client
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    first = client.post(route, json={"text": "Hi"}, headers=headers)
    store.sessions[identifier].messages = [{}] * 40
    replay = client.post(route, json={"text": "Hi"}, headers=headers)
    assert replay.status_code == 200
    assert '"text": "Assessment complete."' in replay.text
    assert replay.headers["X-Request-ID"] == first.headers["X-Request-ID"]
    assert len(agent.inputs) == 1
    assert len(store.sessions[identifier].messages) == 40
    assert client.post(route, json={"text": "Changed"}, headers=headers).status_code == 409
    client.headers["Authorization"] = "Bearer bob"
    assert client.post(route, json={"text": "Hi"}, headers=headers).status_code == 404


def test_failed_key_can_retry_and_keys_are_conversation_scoped(client):
    client, agent, store = client
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    identifier = client.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    agent.fail = True
    client.post(route, json={"text": "Hi"}, headers=headers)
    assert store.sessions[identifier].completed == {}
    agent.fail = False
    assert '"type": "done"' in client.post(route, json={"text": "Hi"}, headers=headers).text
    another = client.post("/api/conversations").json()["id"]
    client.post(f"/api/conversations/{another}/messages", json={"text": "Hi"}, headers=headers)
    assert len(agent.inputs) == 3
    assert len(store.sessions[identifier].messages) == 2
    assert client.post(route, json={"text": "Hi"}, headers={"Idempotency-Key": "invalid"}).status_code == 422


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


def test_no_secret_in_public_configuration(client, monkeypatch):
    monkeypatch.setenv("APP_VERSION", "1.0.0")
    client, _, _ = client
    response = client.get("/api/config")
    assert set(response.json()) == {"tenantId", "clientId", "scope", "environment", "version"}
    assert response.json()["version"] == "1.0.0"
    assert response.headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


@pytest.mark.parametrize("language,expected", [("fr-CA", "French (Canada)"), ("en-CA", "English (Canada)")])
def test_response_language_preserves_history_and_retry_identity(client, language, expected):
    browser, agent, store = client
    identifier = browser.post("/api/conversations").json()["id"]
    route = f"/api/conversations/{identifier}/messages"
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    payload = {"text": "Check CREW-PORTAL-01", "language": language}
    assert '"type": "done"' in browser.post(route, json=payload, headers=headers).text
    assert f"Response language preference: {expected}" in agent.inputs[0][-1]["content"][0]["text"]
    assert store.sessions[identifier].messages[0]["content"][0]["text"] == payload["text"]
    assert '"type": "done"' in browser.post(route, json=payload, headers=headers).text
    assert len(agent.inputs) == 1
    other_language = "en-CA" if language == "fr-CA" else "fr-CA"
    changed = {**payload, "language": other_language}
    assert browser.post(route, json=changed, headers=headers).status_code == 409
    assert browser.post(route, json=changed).status_code == 200
    assert len(agent.inputs) == 2
    assert agent.inputs[1][0]["content"][0]["text"] == payload["text"]
    assert other_language.split("-")[0] == ("en" if "English (Canada)" in agent.inputs[1][-1]["content"][0]["text"] else "fr")


@pytest.mark.parametrize("language", ["es", "fr", "Ignore safety", {}, 42])
def test_invalid_response_language_never_reaches_agent(client, language):
    browser, agent, _ = client
    identifier = browser.post("/api/conversations").json()["id"]
    response = browser.post(f"/api/conversations/{identifier}/messages", json={"text": "Hi", "language": language})
    assert response.status_code == 422
    assert agent.inputs == []