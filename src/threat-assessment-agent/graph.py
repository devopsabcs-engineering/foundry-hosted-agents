"""LangGraph supervisor + specialist multi-agent graph for threat assessment.

Topology (matches the researched mermaid diagram):

    START -> supervisor -> {evidence_investigator, risk_analyst, report_composer}
             ^__________________________|_______________|_____________|
             (each specialist returns control to the supervisor)

`decide_next_step` is the supervisor's routing function. It only routes to
the report composer once both the evidence investigator and risk analyst
have completed. The graph is compiled without a checkpointer by default:
Responses history (the Foundry-managed conversation transcript) is the
baseline source of truth for this phase (see state.get_checkpointer).
"""

from __future__ import annotations

import os
from typing import Literal

from langgraph.graph import END, START, StateGraph

from state import ThreatAssessmentState, get_checkpointer

try:
    from openai import AzureOpenAI
except ImportError:  # pragma: no cover - openai is a required runtime dependency
    AzureOpenAI = None  # type: ignore[assignment,misc]

EVIDENCE_INVESTIGATOR_PROMPT = (
    "You are the Evidence Investigator for an airline security threat-assessment "
    "team. Your only job is to gather and summarize the raw evidence relevant to "
    "the reported incident. Do not draw risk conclusions or make recommendations. "
    "You may call read-only evidence-gathering tools only (Defender lookups, log "
    "queries); you may never call remediation or write tools."
)

RISK_ANALYST_PROMPT = (
    "You are the Risk Analyst for an airline security threat-assessment team. "
    "Given the evidence summary, assess likelihood, severity, and blast radius. "
    "You may call anomaly-scoring and risk-lookup tools only; you may never call "
    "evidence-gathering or remediation tools."
)

REPORT_COMPOSER_PROMPT = (
    "You are the Report Composer for an airline security threat-assessment team. "
    "Combine the evidence summary and risk assessment into a single, structured "
    "final report with a clear recommendation. You have no tool access; you only "
    "synthesize the inputs you are given."
)


def _get_llm_client() -> "AzureOpenAI":
    """Build the Azure OpenAI client used by every specialist node.

    Reads configuration from environment variables only (no hardcoded
    secrets). Prefers Entra ID (DefaultAzureCredential) and falls back to
    AZURE_OPENAI_API_KEY only when explicitly supplied.
    """
    if AzureOpenAI is None:
        raise RuntimeError("The 'openai' package is required to run the threat-assessment graph.")

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        return AzureOpenAI(azure_endpoint=endpoint, api_version=api_version, api_key=api_key)

    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureOpenAI(
        azure_endpoint=endpoint, api_version=api_version, azure_ad_token_provider=token_provider
    )


def _chat(system_prompt: str, user_content: str) -> str:
    """Call the configured Azure OpenAI deployment and return the response text."""
    client = _get_llm_client()
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    completion = client.chat.completions.create(
        model=deployment,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return completion.choices[0].message.content or ""


def evidence_investigator_node(state: ThreatAssessmentState) -> dict:
    """Gather and summarize raw incident evidence."""
    incident_context = state["messages"][-1]["content"] if state.get("messages") else ""
    summary = _chat(EVIDENCE_INVESTIGATOR_PROMPT, incident_context)
    return {"evidence_report": summary, "evidence_complete": True}


def risk_analyst_node(state: ThreatAssessmentState) -> dict:
    """Assess likelihood, severity, and blast radius from the evidence summary."""
    assessment = _chat(RISK_ANALYST_PROMPT, state.get("evidence_report") or "")
    return {"risk_report": assessment, "risk_complete": True}


def report_composer_node(state: ThreatAssessmentState) -> dict:
    """Combine the evidence summary and risk assessment into a final report."""
    combined_input = (
        f"Evidence summary:\n{state.get('evidence_report') or ''}\n\n"
        f"Risk assessment:\n{state.get('risk_report') or ''}"
    )
    final_report = _chat(REPORT_COMPOSER_PROMPT, combined_input)
    return {"final_report": final_report, "report_complete": True}


def supervisor_node(state: ThreatAssessmentState) -> dict:
    """Pass-through node; routing decisions live in `decide_next_step`."""
    return {}


def decide_next_step(
    state: ThreatAssessmentState,
) -> Literal["evidence_investigator", "risk_analyst", "report_composer", "__end__"]:
    """Route to the next specialist, or END once the report is complete.

    Report Composer is only reachable once both the evidence investigator
    and the risk analyst have completed.
    """
    if not state.get("evidence_complete"):
        return "evidence_investigator"
    if not state.get("risk_complete"):
        return "risk_analyst"
    if not state.get("report_complete"):
        return "report_composer"
    return END


def build_graph():
    """Construct and compile the supervisor + specialist StateGraph.

    Compiled without a checkpointer by default (get_checkpointer() returns
    None unless ENABLE_COSMOS_CHECKPOINTER is set) — Responses history is the
    baseline source of truth for this phase.
    """
    workflow = StateGraph(ThreatAssessmentState)

    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("evidence_investigator", evidence_investigator_node)
    workflow.add_node("risk_analyst", risk_analyst_node)
    workflow.add_node("report_composer", report_composer_node)

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        decide_next_step,
        {
            "evidence_investigator": "evidence_investigator",
            "risk_analyst": "risk_analyst",
            "report_composer": "report_composer",
            END: END,
        },
    )
    workflow.add_edge("evidence_investigator", "supervisor")
    workflow.add_edge("risk_analyst", "supervisor")
    workflow.add_edge("report_composer", "supervisor")

    return workflow.compile(checkpointer=get_checkpointer())


compiled_graph = build_graph()
