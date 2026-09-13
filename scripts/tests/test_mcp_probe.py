import asyncio
import importlib.util
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest


spec = importlib.util.spec_from_file_location(
    "mcp_probe", Path(__file__).resolve().parents[1] / "test_mcp_servers.py"
)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_endpoints_are_required(monkeypatch):
    monkeypatch.delenv("DEFENDER_MCP_URL", raising=False)
    monkeypatch.delenv("ANOMALY_MCP_URL", raising=False)
    with pytest.raises(SystemExit) as error:
        probe.parse_args([])
    assert error.value.code == 2


def test_explicit_endpoints_override_environment(monkeypatch):
    monkeypatch.setenv("DEFENDER_MCP_URL", "https://old.example/mcp")
    args = probe.parse_args([
        "--defender-url", "https://defender.example/mcp",
        "--anomaly-url", "https://anomaly.example/mcp",
    ])
    assert args.defender_url == "https://defender.example/mcp"
    assert args.anomaly_url == "https://anomaly.example/mcp"


@pytest.mark.parametrize("url", ["http://example/mcp", "https:///mcp", "https://user:secret@example/mcp"])
def test_invalid_endpoint_is_rejected(url):
    with pytest.raises(SystemExit):
        probe.parse_args(["--defender-url", url, "--anomaly-url", "https://example/mcp"])


@pytest.mark.parametrize("names,content,is_error,error", [
    ([], ['{"risk":"low"}'], False, "required tool"),
    (["get_device_risk"], [], False, "no content"),
    (["get_device_risk"], ['{"risk":"low"}'], True, "failed"),
    (["get_device_risk"], ['{"error":"telemetry unavailable"}'], False, "telemetry unavailable"),
    (["get_device_risk"], ['{"risk":"low"}'], False, None),
])
def test_probe_requires_successful_tool_result(monkeypatch, names, content, is_error, error):
    session = SimpleNamespace(
        initialize=AsyncMock(),
        list_tools=AsyncMock(return_value=SimpleNamespace(tools=[SimpleNamespace(name=name) for name in names])),
        call_tool=AsyncMock(return_value=SimpleNamespace(
            isError=is_error, content=[SimpleNamespace(type="text", text=text) for text in content],
        )),
    )

    @asynccontextmanager
    async def transport(url):
        yield None, None, None

    @asynccontextmanager
    async def client(read, write):
        yield session

    monkeypatch.setattr(probe, "streamablehttp_client", transport)
    monkeypatch.setattr(probe, "ClientSession", client)
    if error:
        with pytest.raises(RuntimeError, match=error):
            asyncio.run(probe.probe("defender", "https://example/mcp", "get_device_risk", {}))
    else:
        asyncio.run(probe.probe("defender", "https://example/mcp", "get_device_risk", {}))
        session.call_tool.assert_awaited_once_with("get_device_risk", {})