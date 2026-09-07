import asyncio
from types import SimpleNamespace

import httpx
import pytest
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