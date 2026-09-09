import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
import toolbox
from toolbox import ALLOWED_TOOLS, ToolboxAuth, ToolboxSpecialist, select_tools


@pytest.mark.parametrize("connection", ALLOWED_TOOLS)
def test_specialist_tool_allowlist(connection):
    tools = [SimpleNamespace(name=name) for names in ALLOWED_TOOLS.values() for name in names]
    tools.append(SimpleNamespace(name="defender-conn___disable_account"))
    assert {tool.name for tool in select_tools(tools, connection)} == ALLOWED_TOOLS[connection]


def test_missing_required_tools_fail_closed():
    with pytest.raises(RuntimeError, match="Required toolbox tools missing"):
        select_tools([], "defender-conn")


def test_unknown_connection_fails_closed():
    with pytest.raises(KeyError):
        select_tools([], "unapproved")


def test_single_task_group_error_preserves_model_error(monkeypatch):
    from openai import BadRequestError

    error = BadRequestError("filtered", response=httpx.Response(
        400, request=httpx.Request("POST", "https://example.test")),
        body={"code": "content_filter"})

    async def fail(payload):
        raise ExceptionGroup("MCP session", [ExceptionGroup("transport", [error])])

    specialist = ToolboxSpecialist("defender-conn", "read-only", lambda: None)
    monkeypatch.setattr(specialist, "ainvoke", fail)
    with pytest.raises(BadRequestError) as caught:
        specialist.invoke({})
    assert caught.value is error


def test_auth_requests_fresh_token_for_each_request():
    class Credential:
        calls = 0

        async def get_token(self, scope):
            assert scope == "https://ai.azure.com/.default"
            self.calls += 1
            return SimpleNamespace(token=f"token-{self.calls}")

    async def run():
        auth = ToolboxAuth(Credential())
        for number in (1, 2):
            request = httpx.Request("POST", "https://example.test")
            async for authenticated in auth.async_auth_flow(request):
                assert authenticated.headers["Authorization"] == f"Bearer token-{number}"

    asyncio.run(run())


@pytest.mark.parametrize("fails", [False, True])
def test_repeated_invocations_close_model_clients_before_loop_ends(monkeypatch, fails):
    models = []

    def model_factory():
        model = SimpleNamespace(root_client=MagicMock(), root_async_client=AsyncMock())
        models.append(model)
        return model

    @asynccontextmanager
    async def tools(connection):
        yield []

    invocation = AsyncMock(side_effect=ValueError("model failed") if fails else None,
                           return_value={"messages": []})
    monkeypatch.setattr(toolbox, "toolbox_tools", tools)
    monkeypatch.setattr(toolbox, "create_agent", lambda **kwargs: SimpleNamespace(ainvoke=invocation))
    specialist = ToolboxSpecialist("defender-conn", "read-only", model_factory)
    for attempt in range(2):
        if fails:
            with pytest.raises(ValueError, match="model failed"):
                specialist.invoke({"messages": []})
        else:
            assert specialist.invoke({"messages": []}) == {"messages": []}
        models[attempt].root_async_client.__aexit__.assert_awaited_once()
        models[attempt].root_client.__exit__.assert_called_once()
    assert models[0] is not models[1]


@pytest.mark.parametrize("account_ids", [[], ["jsmith"]])
def test_login_tool_requires_explicit_user_identifier(monkeypatch, account_ids):
    from langchain_core.messages import ToolMessage
    invocation = AsyncMock(side_effect=lambda call: ToolMessage(
        content="synthetic evidence", tool_call_id=call["id"], name=call["name"]))

    @asynccontextmanager
    async def tools(connection):
        yield [SimpleNamespace(name=name, ainvoke=invocation) for name in ALLOWED_TOOLS[connection]]

    captured = []
    def agent_factory(**kwargs):
        captured.extend(tool.name for tool in kwargs["tools"])
        return SimpleNamespace(ainvoke=AsyncMock(return_value={"messages": []}))

    monkeypatch.setattr(toolbox, "toolbox_tools", tools)
    monkeypatch.setattr(toolbox, "create_agent", agent_factory)
    model = SimpleNamespace(root_client=MagicMock(), root_async_client=AsyncMock())
    specialist = ToolboxSpecialist("anomaly-conn", "read-only", lambda: model)
    specialist.invoke({"messages": [], "required_tools": [
        {"name": "anomaly-conn___detect_login_anomalies", "args": {"user_id": account}}
        for account in account_ids]})
    assert invocation.await_count == len(account_ids)
    assert captured == []