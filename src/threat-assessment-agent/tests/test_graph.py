"""Unit tests for the threat-assessment supervisor + specialist graph.

Specialist nodes are invoked directly with a stubbed supervisor decision
(a hand-built ThreatAssessmentState) rather than through the compiled graph,
and the LLM call (`graph._chat`) is monkeypatched so no real Azure OpenAI
credentials or network access are required.
"""

from __future__ import annotations

from typing import Any

import graph
from langgraph.graph import END
from state import ThreatAssessmentState, get_checkpointer


def _base_state(**overrides: Any) -> ThreatAssessmentState:
    state: ThreatAssessmentState = {
        "messages": [{"role": "user", "content": "Suspicious login from unknown IP."}],
        "evidence_report": None,
        "risk_report": None,
        "final_report": None,
        "evidence_complete": False,
        "risk_complete": False,
        "report_complete": False,
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
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "evidence summary")

    result = graph.evidence_investigator_node(_base_state())

    assert result == {"evidence_report": "evidence summary", "evidence_complete": True}


def test_risk_analyst_node(monkeypatch) -> None:
    monkeypatch.setattr(graph, "_chat", lambda system_prompt, content: "risk assessment")

    result = graph.risk_analyst_node(_base_state(evidence_report="evidence summary", evidence_complete=True))

    assert result == {"risk_report": "risk assessment", "risk_complete": True}


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

    assert result == {"final_report": "final report", "report_complete": True}
    assert "evidence summary" in captured["content"]
    assert "risk assessment" in captured["content"]


def test_build_graph_compiles_without_a_checkpointer(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_COSMOS_CHECKPOINTER", raising=False)

    compiled = graph.build_graph()

    assert compiled is not None
    assert hasattr(compiled, "invoke")


def test_get_checkpointer_is_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("ENABLE_COSMOS_CHECKPOINTER", raising=False)

    assert get_checkpointer() is None
