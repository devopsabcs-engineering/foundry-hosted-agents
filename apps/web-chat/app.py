import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from azure.identity.aio import DefaultAzureCredential
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from httpx_sse import aconnect_sse
from pydantic import BaseModel, ConfigDict, Field

from auth import Identity, PilotAuth

logger = logging.getLogger("web_chat")


@dataclass(frozen=True)
class Settings:
    tenant_id: str
    client_id: str
    pilot_group_id: str
    agent_endpoint: str
    managed_identity_client_id: str | None = None
    session_ttl: int = 3600
    max_sessions: int = 128
    max_turns: int = 20

    @classmethod
    def from_env(cls):
        endpoint = os.environ["AGENT_ENDPOINT"]
        parsed = httpx.URL(endpoint)
        if parsed.scheme != "https" or not parsed.host.endswith(".services.ai.azure.com"):
            raise ValueError("AGENT_ENDPOINT must be a Foundry HTTPS endpoint")
        return cls(
            tenant_id=str(uuid.UUID(os.environ["ENTRA_TENANT_ID"])),
            client_id=str(uuid.UUID(os.environ["ENTRA_CLIENT_ID"])),
            pilot_group_id=str(uuid.UUID(os.environ["PILOT_GROUP_ID"])),
            agent_endpoint=endpoint,
            managed_identity_client_id=os.environ.get("AZURE_CLIENT_ID"),
        )


@dataclass
class Conversation:
    owner: Identity
    touched: float = field(default_factory=time.monotonic)
    messages: list = field(default_factory=list)
    busy: bool = False
    completed: dict[str, tuple[str, str]] = field(default_factory=dict)


class SessionStore:
    def __init__(self, settings):
        self.settings = settings
        self.sessions: dict[str, Conversation] = {}

    def create(self, owner):
        now = time.monotonic()
        self.sessions = {
            key: value for key, value in self.sessions.items()
            if value.busy or now - value.touched < self.settings.session_ttl
        }
        if len(self.sessions) >= self.settings.max_sessions:
            raise HTTPException(429, "Pilot capacity reached. Try again later.")
        if sum(session.owner == owner for session in self.sessions.values()) >= 5:
            raise HTTPException(429, "Close an existing conversation before starting another.")
        identifier = str(uuid.uuid4())
        self.sessions[identifier] = Conversation(owner)
        return identifier

    def get(self, identifier, owner):
        session = self.sessions.get(identifier)
        if session is None or session.owner != owner:
            raise HTTPException(404, "Conversation not found. Start a new conversation.")
        if not session.busy and time.monotonic() - session.touched >= self.settings.session_ttl:
            del self.sessions[identifier]
            raise HTTPException(404, "Conversation expired. Start a new conversation.")
        session.touched = time.monotonic()
        return session


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=8000)


class FoundryClient:
    def __init__(self, settings):
        self.settings = settings
        self.credential = DefaultAzureCredential(
            managed_identity_client_id=settings.managed_identity_client_id,
        )
        self.http = httpx.AsyncClient(timeout=httpx.Timeout(180, connect=15))

    async def close(self):
        await self.http.aclose()
        await self.credential.close()

    async def events(self, messages):
        token = await self.credential.get_token("https://ai.azure.com/.default")
        completion = None
        byte_count = 0
        async with asyncio.timeout(180):
            async with aconnect_sse(
                self.http, "POST", self.settings.agent_endpoint,
                headers={"Authorization": f"Bearer {token.token}"},
                json={"input": messages, "stream": True, "store": False},
            ) as stream:
                stream.response.raise_for_status()
                async for event in stream.aiter_sse():
                    byte_count += len(event.data)
                    if byte_count > 2_000_000:
                        raise ValueError("Response exceeds limit")
                    if event.data == "[DONE]":
                        continue
                    payload = json.loads(event.data)
                    response = payload.get("response") or {}
                    kind = payload.get("type", "")
                    if payload.get("error") or response.get("error") or kind in {
                        "error", "response.failed", "response.incomplete", "response.error",
                    }:
                        raise ValueError("Agent reported failure")
                    if kind == "response.completed":
                        if completion is not None or response.get("status") != "completed":
                            raise ValueError("Invalid completion")
                        texts = [
                            content["text"] for item in response.get("output", [])
                            if item.get("type") == "message" and item.get("role") == "assistant"
                            for content in item.get("content", [])
                            if content.get("type") == "output_text" and content.get("text", "").strip()
                        ]
                        completion = "\n\n".join(texts)
                        if not completion or len(completion) > 64000:
                            raise ValueError("Missing or oversized assistant response")
        if completion is None:
            raise ValueError("Incomplete response")
        yield {"type": "answer", "text": completion}


def sse(payload):
    return "data: " + json.dumps(payload, ensure_ascii=True) + "\n\n"


def create_app(settings=None, verifier=None, upstream=None):
    settings = settings or Settings.from_env()
    verifier = verifier or PilotAuth(settings.tenant_id, settings.client_id, settings.pilot_group_id)
    store = SessionStore(settings)
    slots = asyncio.Semaphore(4)

    @asynccontextmanager
    async def lifespan(application):
        application.state.upstream = upstream or FoundryClient(settings)
        yield
        if upstream is None:
            await application.state.upstream.close()

    application = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    application.state.store = store

    async def identity(authorization: str | None = Header(default=None)):
        return await verifier.authorize(authorization)

    @application.middleware("http")
    async def security_headers(request: Request, call_next):
        if request.headers.get("content-length", "").isdigit():
            if int(request.headers["content-length"]) > 40000:
                return JSONResponse({"detail": "Request too large."}, status_code=413)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self' https://login.microsoftonline.com; "
            "frame-src https://login.microsoftonline.com; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self' https://login.microsoftonline.com"
        )
        return response

    @application.get("/healthz")
    async def health():
        return {"status": "ok"}

    @application.get("/api/config")
    async def config():
        return {"tenantId": settings.tenant_id, "clientId": settings.client_id,
                "scope": f"api://{settings.client_id}/Chat.Access", "environment": "staging",
                "version": os.environ.get("APP_VERSION", "0.0.0-dev")}

    @application.get("/api/me")
    async def me(owner: Identity = Depends(identity)):
        return {"objectId": owner.object_id}

    @application.post("/api/conversations", status_code=201)
    async def create(owner: Identity = Depends(identity)):
        return {"id": store.create(owner)}

    @application.delete("/api/conversations/{identifier}", status_code=204)
    async def delete(identifier: uuid.UUID, owner: Identity = Depends(identity)):
        session = store.get(str(identifier), owner)
        if session.busy:
            raise HTTPException(409, "Stop the current response first.")
        del store.sessions[str(identifier)]

    @application.post("/api/conversations/{identifier}/messages")
    async def message(identifier: uuid.UUID, body: Message, owner: Identity = Depends(identity),
                      idempotency_key: uuid.UUID | None = Header(default=None)):
        session = store.get(str(identifier), owner)
        request_id = str(idempotency_key or uuid.uuid4())
        if request_id in session.completed:
            original, answer = session.completed[request_id]
            if original != body.text:
                raise HTTPException(409, "This request key was already used for a different message.")
            return StreamingResponse(iter([
                sse({"type": "status", "text": "Complete", "requestId": request_id}),
                sse({"type": "answer", "text": answer, "requestId": request_id}),
                sse({"type": "done"}),
            ]), media_type="text/event-stream",
                headers={"X-Accel-Buffering": "no", "X-Request-ID": request_id})
        if session.busy:
            raise HTTPException(409, "A response is already in progress.")
        if len(session.messages) >= settings.max_turns * 2:
            raise HTTPException(409, "Conversation limit reached. Start a new conversation.")
        if slots.locked():
            raise HTTPException(429, "The pilot is busy. Try again shortly.")
        session.busy = True
        await slots.acquire()

        async def generate():
            started = time.monotonic()
            task = None
            outcome = "cancelled"
            try:
                yield sse({"type": "status", "text": "Assessing", "requestId": request_id})
                user_message = {"role": "user", "content": [{"type": "input_text", "text": body.text}]}
                messages = session.messages + [user_message]

                async def result():
                    answer = None
                    async for event in application.state.upstream.events(messages):
                        if event["type"] == "answer":
                            answer = event["text"]
                    if not answer:
                        raise ValueError("No answer")
                    return answer

                task = asyncio.create_task(result())
                while not task.done():
                    await asyncio.wait({task}, timeout=10)
                    if not task.done():
                        yield ": keepalive\n\n"
                answer = task.result()
                session.messages = messages + [{"role": "assistant", "content": answer}]
                session.completed[request_id] = (body.text, answer)
                yield sse({"type": "answer", "text": answer, "requestId": request_id})
                yield sse({"type": "done"})
                outcome = "success"
            except (httpx.HTTPError, ValueError, TimeoutError) as exc:
                outcome = type(exc).__name__
                yield sse({"type": "error", "text": "The assessment could not complete. Try again.",
                           "requestId": request_id})
            except Exception as exc:
                outcome = type(exc).__name__
                yield sse({"type": "error", "text": "The service is temporarily unavailable.",
                           "requestId": request_id})
            finally:
                if task is not None and not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                session.busy = False
                session.touched = time.monotonic()
                slots.release()
                logger.warning("chat_request id=%s outcome=%s seconds=%.3f",
                               request_id, outcome, time.monotonic() - started)

        return StreamingResponse(generate(), media_type="text/event-stream",
                                 headers={"X-Accel-Buffering": "no", "X-Request-ID": request_id})

    dist = Path(__file__).parent / "frontend" / "dist"
    if dist.exists():
        application.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return application