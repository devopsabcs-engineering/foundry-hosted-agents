import asyncio
import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("load_probe", Path(__file__).with_name("load_test.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Response:
    def __init__(self, status, events):
        self.status = status
        self.events = events
        self.content = self
        self.headers = {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def __aiter__(self):
        async def lines():
            for event in self.events:
                yield ("data: " + json.dumps(event) + "\n\n").encode()

        return lines()


class Session:
    def __init__(self, response):
        self.response = response

    def post(self, *args, **kwargs):
        assert kwargs["json"]["store"] is False
        assert "conversation" not in kwargs["json"]
        return self.response


@pytest.mark.parametrize(
    "status,events",
    [
        (401, []),
        (200, [{"type": "error", "error": {"message": "denied"}}]),
        (200, [{"type": "response.failed"}]),
        (200, [{"type": "response.incomplete"}]),
        (200, []),
        (200, [{"type": "response.completed", "response": {"status": "cancelled"}}]),
        (200, [None]),
        (200, [{"type": "response.output_text.delta", "delta": None}]),
        (200, [{"type": "response.completed", "response": {"status": "completed", "output": []}}]),
    ],
)
def test_errors_are_not_successful_latency_samples(status, events):
    result = asyncio.run(
        probe._invoke_once(Session(Response(status, events)), "https://example.test", "test", None)
    )
    assert result["error"] is not None


def test_failure_retains_codes_without_prompt_or_error_message():
    events = [{"type": "error", "error": {
        "code": "rate_limit_exceeded", "request_id": "request-123",
        "message": "potentially sensitive prompt body",
    }}]
    result = asyncio.run(
        probe._invoke_once(Session(Response(200, events)), "https://example.test", "test", None)
    )
    assert result["error"] is not None
    assert result["failure_code"] == "rate_limit_exceeded"
    assert result["failure_request_id"] == "request-123"
    assert "potentially sensitive" not in json.dumps(result)


def test_failure_retains_only_bounded_correlation_headers():
    response = Response(200, [{"type": "error", "code": "server_error"}])
    response.headers = {
        "X-MS-Agent-Session-ID": "session-123", "X-Request-ID": "r" * 300,
        "Set-Cookie": "private", "Authorization": "Bearer private",
    }
    result = asyncio.run(
        probe._invoke_once(Session(response), "https://example.test", "test", None)
    )
    assert result["error"] is not None
    assert result["correlation_headers"] == {
        "X-MS-Agent-Session-ID": "session-123", "X-Request-ID": "r" * 200,
    }
    assert "private" not in json.dumps(result)


def test_completed_text_is_successful():
    events = [
        {"type": "response.output_text.delta", "delta": "Ready"},
        {
            "type": "response.completed",
            "response": {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": "Ready"}],
                    }
                ],
            },
        },
    ]
    result = asyncio.run(
        probe._invoke_once(Session(Response(200, events)), "https://example.test", "test", None)
    )
    assert result["error"] is None


def test_cli_failure_writes_evidence_and_exits_nonzero(monkeypatch, tmp_path):
    output = tmp_path / "load.json"
    monkeypatch.setattr(
        "sys.argv", ["load_test.py", "concurrent-sessions", "--count", "1", "--out", str(output)]
    )
    monkeypatch.setattr(probe, "_get_bearer_token", lambda: "unused")

    async def failures(*args):
        return [{"error": "HTTP 401", "latency_seconds": 1}]

    monkeypatch.setattr(probe, "run_concurrent_sessions", failures)
    with pytest.raises(SystemExit) as failure:
        probe.main()
    assert failure.value.code == 1
    data = json.loads(output.read_text())
    assert data["error_count"] == 1
    assert data["latency_p95_seconds"] is None


@pytest.mark.parametrize("count", ["0", "-1", "21"])
def test_cli_bounds_count_before_authentication(monkeypatch, count):
    monkeypatch.setattr("sys.argv", ["load_test.py", "concurrent-sessions", "--count", count])
    with pytest.raises(SystemExit) as failure:
        probe.main()
    assert failure.value.code == 2
