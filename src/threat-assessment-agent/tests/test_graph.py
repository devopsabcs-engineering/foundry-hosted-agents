"""Unit tests for the threat-assessment supervisor + specialist graph.

Specialist nodes are invoked directly with a stubbed supervisor decision
(a hand-built ThreatAssessmentState) rather than through the compiled graph.
The Report Composer's LLM call (`graph._chat`) is monkeypatched so no real
Azure OpenAI credentials or network access are required. The Evidence
Investigator and Risk Analyst nodes are Toolbox-backed (via
`graph._get_specialist_agent`, which returns a LangChain agent bound to a
Foundry Toolbox MCP connection through `use_foundry_tools`); their tests
monkeypatch `graph._get_specialist_agent` with a fake agent stub so no real
Foundry project, model, or Toolbox connection is required.
"""

from __future__ import annotations

from typing import Any

import graph
from azure.core.exceptions import ResourceNotFoundError
from langgraph.graph import END
from state import ThreatAssessmentState, get_checkpointer


class _FakeSpecialistAgent:
    """Stand-in for a `create_agent(...)` compiled graph's `.invoke()` result."""

    def __init__(self, response_content: str) -> None:
        self._response_content = response_content

    def invoke(self, _input: dict) -> dict:
        return {"messages": [{"role": "assistant", "content": self._response_content}]}


class _ToolUnavailableSpecialistAgent:
    """Stand-in for a specialist agent whose Toolbox tool-resolution call 404s."""

    def invoke(self, _input: dict) -> dict:
        raise ResourceNotFoundError("Operation returned an invalid status 'Not Found'")


def _base_state(**overrides: Any) -> ThreatAssessmentState:
    state: ThreatAssessmentState = {
        "messages": [{"role": "user", "content": "Suspicious login from unknown IP."}],
        "evidence_report": None,
        "risk_report": None,
        "final_report": None,
        "evidence_complete": False,
        "risk_complete": False,
        "report_complete": False,
        "evidence_tool_unavailable": False,
        "risk_tool_unavailable": False,
    }
    state.update(overrides)  # type: ignore[typeddict-item]
    return state


def test_decide_next_step_routes_to_evidence_investigator_first() -> None:
    state = _base_state()
    assert graph.decide_next_step(state) == "evidence_investigator"


def test_decide_next_step_routes_to_risk_analyst_after_evidence() -> None:
    state = _base_state(evidence_complete=True)
    assert graph.decide_next_step(state) == "risk_analyst"


def test_decide_next_step_does_not_route_to_composer_before_risk_completes() -> None:
    state = _base_state(evidence_complete=True, risk_complete=False)
    assert graph.decide_next_step(state) != "report_composer"


def test_decide_next_step_routes_to_report_composer_only_after_both_complete() -> None:
    state = _base_state(evidence_complete=True, risk_complete=True)
    assert graph.decide_next_step(state) == "report_composer"


def test_decide_next_step_ends_when_report_complete() -> None:
    state = _base_state(evidence_complete=True, risk_complete=True, report_complete=True)
    assert graph.decide_next_step(state) == END


def test_evidence_investigator_node(monkeypatch) -> None:
    monkeypatch.setattr(
        graph,
        "_get_specialist_agent",
        lambda connection_id, system_prompt: _FakeSpecialistAgent("evidence summary"),
    )

    result = graph.evidence_investigator_node(_base_state())

    assert result == {
        "evidence_report": "evidence summary",
        "evidence_complete": True,
        "evidence_tool_unavailable": False,
    }


def test_evidence_investigator_node_falls_back_when_tool_resolution_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        graph,
        "_get_specialist_agent",
        lambda connection_id, system_prompt: _ToolUnavailableSpecialistAgent(),
    )
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "plain-llm evidence analysis")

    result = graph.evidence_investigator_node(_base_state())

    assert result["evidence_complete"] is True
    assert result["evidence_tool_unavailable"] is True
    assert "MCP tool unavailable" in result["evidence_report"]
    assert "plain-llm evidence analysis" in result["evidence_report"]


def test_evidence_investigator_node_falls_back_when_context_flags_tool_resolution_unavailable(
    monkeypatch,
) -> None:
    """Covers the real production failure mode: the hosting SDK's tool
    resolution 404s BEFORE the graph runs (outside this node entirely), so
    `main.py`'s adapter flags `TOOL_RESOLUTION_UNAVAILABLE` instead of an
    exception ever reaching `agent.invoke()` here.
    """

    def _fail_if_called(connection_id: str, system_prompt: str) -> None:
        raise AssertionError("_get_specialist_agent should not be called when tool resolution is flagged unavailable")

    monkeypatch.setattr(graph, "_get_specialist_agent", _fail_if_called)
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "plain-llm evidence analysis")

    token = graph.TOOL_RESOLUTION_UNAVAILABLE.set(True)
    try:
        result = graph.evidence_investigator_node(_base_state())
    finally:
        graph.TOOL_RESOLUTION_UNAVAILABLE.reset(token)

    assert result["evidence_complete"] is True
    assert result["evidence_tool_unavailable"] is True
    assert "MCP tool unavailable" in result["evidence_report"]
    assert "plain-llm evidence analysis" in result["evidence_report"]


def test_evidence_investigator_node_binds_defender_toolbox_connection(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_get_specialist_agent(connection_id: str, system_prompt: str) -> _FakeSpecialistAgent:
        captured["connection_id"] = connection_id
        return _FakeSpecialistAgent("evidence summary")

    monkeypatch.setattr(graph, "_get_specialist_agent", fake_get_specialist_agent)

    graph.evidence_investigator_node(_base_state())

    assert captured["connection_id"] == "defender-conn"


def test_risk_analyst_node(monkeypatch) -> None:
    monkeypatch.setattr(
        graph,
        "_get_specialist_agent",
        lambda connection_id, system_prompt: _FakeSpecialistAgent("risk assessment"),
    )

    result = graph.risk_analyst_node(_base_state(evidence_report="evidence summary", evidence_complete=True))

    assert result == {
        "risk_report": "risk assessment",
        "risk_complete": True,
        "risk_tool_unavailable": False,
    }


def test_risk_analyst_node_falls_back_when_tool_resolution_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        graph,
        "_get_specialist_agent",
        lambda connection_id, system_prompt: _ToolUnavailableSpecialistAgent(),
    )
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "plain-llm risk analysis")

    result = graph.risk_analyst_node(_base_state(evidence_report="evidence summary", evidence_complete=True))

    assert result["risk_complete"] is True
    assert result["risk_tool_unavailable"] is True
    assert "MCP tool unavailable" in result["risk_report"]
    assert "plain-llm risk analysis" in result["risk_report"]


def test_risk_analyst_node_falls_back_when_context_flags_tool_resolution_unavailable(monkeypatch) -> None:
    def _fail_if_called(connection_id: str, system_prompt: str) -> None:
        raise AssertionError("_get_specialist_agent should not be called when tool resolution is flagged unavailable")

    monkeypatch.setattr(graph, "_get_specialist_agent", _fail_if_called)
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "plain-llm risk analysis")

    token = graph.TOOL_RESOLUTION_UNAVAILABLE.set(True)
    try:
        result = graph.risk_analyst_node(
            _base_state(evidence_report="evidence summary", evidence_complete=True)
        )
    finally:
        graph.TOOL_RESOLUTION_UNAVAILABLE.reset(token)

    assert result["risk_complete"] is True
    assert result["risk_tool_unavailable"] is True
    assert "MCP tool unavailable" in result["risk_report"]
    assert "plain-llm risk analysis" in result["risk_report"]


def test_risk_analyst_node_binds_anomaly_toolbox_connection(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_get_specialist_agent(connection_id: str, system_prompt: str) -> _FakeSpecialistAgent:
        captured["connection_id"] = connection_id
        return _FakeSpecialistAgent("risk assessment")

    monkeypatch.setattr(graph, "_get_specialist_agent", fake_get_specialist_agent)

    graph.risk_analyst_node(_base_state(evidence_report="evidence summary", evidence_complete=True))

    assert captured["connection_id"] == "anomaly-conn"


def test_report_composer_node_combines_both_reports(monkeypatch) -> None:
    captured: dict[str, str] = {}

    def fake_chat(system_prompt: str, content: str) -> str:
        captured["content"] = content
        return "final report"

    monkeypatch.setattr(graph, "_chat", fake_chat)

    state = _base_state(
        evidence_report="evidence summary",
        risk_report="risk assessment",
        evidence_complete=True,
        risk_complete=True,
    )
    result = graph.report_composer_node(state)

    assert result["final_report"] == "final report"
    assert result["report_complete"] is True
    assert len(result["messages"]) == 1
    assert result["messages"][0].content == "final report"
    assert "evidence summary" in captured["content"]
    assert "risk assessment" in captured["content"]


def test_report_composer_node_adds_limitations_note_when_tool_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "final report")

    state = _base_state(
        evidence_report="evidence summary",
        risk_report="risk assessment",
        evidence_complete=True,
        risk_complete=True,
        evidence_tool_unavailable=True,
    )
    result = graph.report_composer_node(state)

    assert result["final_report"].startswith("final report")
    assert "Limitations" in result["final_report"]
    assert "Evidence Investigator" in result["final_report"]
    assert "Risk Analyst" not in result["final_report"]


def test_report_composer_node_omits_limitations_note_when_both_tools_available(monkeypatch) -> None:
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "final report")

    state = _base_state(
        evidence_report="evidence summary",
        risk_report="risk assessment",
        evidence_complete=True,
        risk_complete=True,
    )
    result = graph.report_composer_node(state)

    assert result["final_report"] == "final report"
    assert "Limitations" not in result["final_report"]


def test_build_graph_compiles_without_a_checkpointer(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_COSMOS_CHECKPOINTER", raising=False)

    compiled = graph.build_graph()

    assert compiled is not None
    assert hasattr(compiled, "invoke")


def test_get_checkpointer_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_COSMOS_CHECKPOINTER", raising=False)

    assert get_checkpointer() is None
