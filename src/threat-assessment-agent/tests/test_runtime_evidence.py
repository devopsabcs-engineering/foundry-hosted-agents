import asyncio
import base64
import json
import runpy
import zlib
from pathlib import Path
from types import SimpleNamespace

import graph
from langchain_core.messages import AIMessage, ToolMessage
from runtime_evidence import EvidenceConverter, evidence_metadata


def decode(metadata):
    count = int(metadata["runtime_evidence"].split(":")[1])
    return json.loads(zlib.decompress(base64.b64decode(
        "".join(metadata[f"runtime_evidence_{index}"] for index in range(count)))))


def test_metadata_excludes_input_and_overrides_caller_evidence():
    state = {"messages": ["private input"], "final_report": "report", "tool_calls": []}
    result = evidence_metadata(state, {"runtime_evidence": "forged", "runtime_evidence_12": "forged"})
    assert decode(result) == {"final_report": "report", "tool_calls": []}
    assert len(result) <= 16
    assert all(len(value) <= 512 for value in result.values())


def test_real_sdk_history_reaches_all_nodes_without_cross_request_state(monkeypatch):
    from azure.ai.agentserver.core import AgentRunContext
    from azure.ai.agentserver.langgraph import LanggraphRunContext
    from azure.ai.agentserver.langgraph.tools._context import FoundryToolContext

    captured = []

    class InspectingAgent:
        def invoke(self, payload):
            captured.append(payload["messages"][0].content)
            return {"messages": [AIMessage(content="Current findings")]}

    def chat(_prompt, content):
        captured.append(content)
        return "Current report"

    monkeypatch.setattr(graph, "_get_specialist_agent", lambda *args: InspectingAgent())
    monkeypatch.setattr(graph, "_chat", chat)

    async def run():
        compiled = graph.build_graph()
        converter = EvidenceConverter(compiled)
        for messages in [
            [{"role": "user", "content": "My reference is PILOT-4827."},
             {"role": "assistant", "content": "Earlier hypothesis"},
             {"role": "user", "content": "What was my reference?"}],
            [{"role": "user", "content": "Independent request"}],
        ]:
            context = LanggraphRunContext(AgentRunContext({
                "input": messages, "stream": True, "store": False,
            }), FoundryToolContext())
            arguments = await converter.convert_request(context)
            output = compiled.astream(arguments["input"], stream_mode=converter.get_stream_mode(context))
            events = [event async for event in converter.convert_response_stream(output, context)]
            completed = [event for event in events if event.type == "response.completed"]
            assert len(completed) == 1
            state = decode(completed[0].response.metadata)
            assert state["report_complete"]
            assert "messages" not in state

    asyncio.run(run())
    assert len(captured) == 6
    for content in captured[:3]:
        assert "PILOT-4827" in content
        assert "Earlier hypothesis" in content
        assert "What was my reference?" in content
    for content in captured[3:]:
        assert "Independent request" in content
        assert "PILOT-4827" not in content
        assert "Earlier hypothesis" not in content


def test_oversized_evidence_fails_closed():
    assert evidence_metadata({"final_report": "x" * 131073})["runtime_evidence"].startswith("unavailable")


def test_receipts_require_successful_tool_messages():
    messages = [AIMessage(content='{"tool_calls": [{"connection": "defender-conn"}]}'),
                ToolMessage(content="failed", tool_call_id="bad", status="error"),
                ToolMessage(content="ok", tool_call_id="real", name="lookup")]
    receipts = graph._tool_receipts({"messages": messages}, "evidence_investigator", "defender-conn")
    assert len(receipts) == 1
    assert receipts[0]["call_id"] == "real"


def test_stream_evidence_uses_final_values(monkeypatch):
    from runtime_evidence import ResponseAPIDefaultConverter

    async def base_convert(self, output, context):
        assert [item async for item in output] == ["assistant message"]
        yield SimpleNamespace(type="response.completed", response=SimpleNamespace(metadata=None))

    async def source():
        yield "values", {"evidence_complete": False}
        yield "messages", "assistant message"
        yield "values", {"evidence_complete": True, "final_report": "report"}

    async def run():
        converter = EvidenceConverter(graph.build_graph())
        return [event async for event in converter.convert_response_stream(source(), None)]

    monkeypatch.setattr(ResponseAPIDefaultConverter, "convert_response_stream", base_convert)
    events = asyncio.run(run())
    assert decode(events[0].response.metadata)["evidence_complete"] is True


def test_real_sdk_stream_carries_verified_refusal(monkeypatch):
    import httpx
    from azure.ai.agentserver.core import AgentRunContext
    from azure.ai.agentserver.langgraph import LanggraphRunContext
    from azure.ai.agentserver.langgraph.tools._context import FoundryToolContext
    from openai import BadRequestError

    def reject(*args):
        raise BadRequestError("rejected", response=httpx.Response(
            400, request=httpx.Request("POST", "https://example.test")), body={"code": "content_filter"})

    monkeypatch.setattr(graph, "_chat", reject)

    async def run():
        compiled = graph.build_graph()
        converter = EvidenceConverter(compiled)
        context = LanggraphRunContext(AgentRunContext({"input": "incident", "stream": True}),
                                      FoundryToolContext())
        output = compiled.astream({"messages": [{"role": "user", "content": "incident"}]},
                                  stream_mode=converter.get_stream_mode(context))
        return [event async for event in converter.convert_response_stream(output, context)]

    token = graph.TOOL_RESOLUTION_UNAVAILABLE.set(True)
    try:
        events = asyncio.run(run())
    finally:
        graph.TOOL_RESOLUTION_UNAVAILABLE.reset(token)
    completed = [event for event in events if event.type == "response.completed"]
    assert len(completed) == 1
    state = decode(completed[0].response.metadata)
    assert state["safety_blocked"]
    assert state["tool_calls"] == []
    assert completed[0].response.as_dict()["output"][0]["content"][0]["text"] == state["final_report"]
    root = Path(__file__).parents[3]
    monkeypatch.syspath_prepend(str(root / "eval"))
    runner = runpy.run_path(str(root / "eval" / "run_hosted_evaluation.py"))
    raw = "\n".join("data: " + json.dumps(event.as_dict()) for event in events)
    captured = runner["completed_response"](raw)
    golden = [json.loads(line) for line in (root / "eval" / "golden-dataset.jsonl").read_text().splitlines()]
    expected = next(record["expected"] for record in golden if record["id"] == "inject-001")
    assert runner["verified_safety_refusal"]({"expected": expected, "response": captured["text"],
                                               "runtime_state": captured["runtime_state"]})