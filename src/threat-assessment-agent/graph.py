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
from contextvars import ContextVar
from functools import wraps
from typing import Any, Literal

from azure.core.exceptions import ResourceNotFoundError
from langgraph.graph import END, START, StateGraph
from openai import BadRequestError
from state import ThreatAssessmentState, get_checkpointer

try:
    from openai import AzureOpenAI
except ImportError:  # pragma: no cover - openai is a required runtime dependency
    AzureOpenAI = None  # type: ignore[assignment,misc]

try:
    from azure.ai.agentserver.langgraph.tools import use_foundry_tools
    from langchain.agents import create_agent
    from langchain_core.messages import HumanMessage
    from langchain_openai import AzureChatOpenAI
except ImportError:  # pragma: no cover - required for Toolbox-backed specialist nodes
    use_foundry_tools = None  # type: ignore[assignment,misc]
    create_agent = None  # type: ignore[assignment,misc]
    HumanMessage = None  # type: ignore[assignment,misc]
    AzureChatOpenAI = None  # type: ignore[assignment,misc]

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


def _message_content(message: Any) -> str:
    """Return message text whether `message` is a dict or a LangChain message object."""
    if isinstance(message, dict):
        return message.get("content", "")
    return getattr(message, "content", "") or ""


DEFENDER_TOOLBOX_CONNECTION = "defender-conn"
ANOMALY_TOOLBOX_CONNECTION = "anomaly-conn"

# Built (and registered into the SDK's global Foundry tool registry) at
# *import* time rather than lazily inside the node functions. The hosting
# SDK snapshots that registry once per request, before the graph runs
# (LangGraphAdapter.setup_lg_run_context -> resolve_from_registry), so a
# lazy first-call registration would miss the very first request after a
# cold start. Building `use_foundry_tools(...)` here is safe: it only
# constructs a tool descriptor and appends to an in-memory list; it reads no
# environment variables and makes no network calls.
_SPECIALIST_MIDDLEWARE: dict[str, Any] = {}
if use_foundry_tools is not None:
    _SPECIALIST_MIDDLEWARE[DEFENDER_TOOLBOX_CONNECTION] = use_foundry_tools(
        [{"type": "mcp", "project_connection_id": DEFENDER_TOOLBOX_CONNECTION}]
    )
    _SPECIALIST_MIDDLEWARE[ANOMALY_TOOLBOX_CONNECTION] = use_foundry_tools(
        [{"type": "mcp", "project_connection_id": ANOMALY_TOOLBOX_CONNECTION}]
    )


def _get_langchain_chat_model() -> "AzureChatOpenAI":
    """Build the LangChain chat model used by Toolbox-backed specialist nodes.

    Same auth strategy as `_get_llm_client` (Entra ID preferred, API key
    fallback) but returns a LangChain `BaseChatModel`, which `create_agent`
    and `use_foundry_tools` require.
    """
    if AzureChatOpenAI is None:
        raise RuntimeError(
            "The 'langchain-openai' package is required to run the threat-assessment graph."
        )

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    api_version = os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        return AzureChatOpenAI(
            azure_endpoint=endpoint,
            azure_deployment=deployment,
            api_version=api_version,
            api_key=api_key,
        )

    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return AzureChatOpenAI(
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_version=api_version,
        azure_ad_token_provider=token_provider,
    )


_specialist_agent_cache: dict[str, Any] = {}


def _get_specialist_agent(connection_id: str, system_prompt: str) -> Any:
    """Lazily build and cache a Toolbox-backed LangChain agent for one MCP connection.

    Each agent binds exactly one Foundry Toolbox MCP connection via the
    pre-registered `use_foundry_tools` middleware (see `_SPECIALIST_MIDDLEWARE`
    above), which wraps both the model call (tool schemas fetched from the
    Toolbox) and tool execution (routed through `FoundryToolRuntime`) so calls
    never bypass the Toolbox to hit the MCP server directly.
    """
    if connection_id not in _specialist_agent_cache:
        middleware = _SPECIALIST_MIDDLEWARE.get(connection_id)
        if create_agent is None or middleware is None:
            raise RuntimeError(
                "The 'langchain' and 'azure-ai-agentserver-langgraph' packages are "
                "required to run the threat-assessment graph."
            )
        _specialist_agent_cache[connection_id] = create_agent(
            model=_get_langchain_chat_model(),
            tools=[],
            system_prompt=system_prompt,
            middleware=[middleware],
        )
    return _specialist_agent_cache[connection_id]


def _last_ai_message_content(result: dict) -> str:
    """Extract the last non-empty message's text content from an agent invoke result."""
    for message in reversed(result.get("messages", [])):
        content = _message_content(message)
        if content:
            return content
    return ""


# Shown in place of a tool-grounded report when the Foundry Toolbox
# tool-resolution API is unavailable (see repo memory / research notes: this
# is a known platform-side gap for this account/region, not a code defect).
_TOOL_UNAVAILABLE_NOTE = (
    "[MCP tool unavailable: Azure Foundry Toolbox tool-resolution API returned "
    "404 for this account/region — this is a known platform limitation, not a "
    "code defect. Analysis below is based on the incident description only, "
    "without live tool-augmented data.]"
)

# Set True for the duration of a single request by main.py's
# `_GracefulToolResolutionAdapter.setup_lg_run_context` when the hosting SDK's
# per-request Foundry Toolbox tool resolution (which runs BEFORE the graph
# starts) 404s. That failure happens entirely outside these node functions,
# so the `except ResourceNotFoundError` blocks below (which guard the case
# where a specialist agent's own `.invoke()` call raises directly, e.g. in
# unit tests or a future SDK version) can never observe it -- this
# ContextVar is the real signal for that production failure mode. Defaults
# to False, so it is a no-op unless main.py's adapter explicitly sets it.
TOOL_RESOLUTION_UNAVAILABLE: ContextVar[bool] = ContextVar(
    "tool_resolution_unavailable", default=False
)


def _degraded_specialist_result(
    system_prompt: str, content: str, report_key: str, complete_key: str, unavailable_key: str
) -> dict:
    """Build a node result for a specialist whose Toolbox MCP tool is unreachable.

    Falls back to a plain-LLM (`_chat`) analysis of the available context so
    the pipeline still produces a coherent, honest report instead of nothing.
    """
    fallback = _chat(system_prompt, content)
    return {
        report_key: f"{_TOOL_UNAVAILABLE_NOTE}\n\n{fallback}",
        complete_key: True,
        unavailable_key: True,
    }


def _handle_content_filter(node):
    @wraps(node)
    def guarded(state: ThreatAssessmentState) -> dict:
        try:
            return node(state)
        except BadRequestError as error:
            body = error.body if isinstance(error.body, dict) else {}
            details = body.get("error", body)
            if not isinstance(details, dict) or details.get("code") != "content_filter":
                raise
            from langchain_core.messages import AIMessage

            refusal = (
                "I cannot continue this request because it was blocked by the safety policy. "
                "I cannot disclose internal instructions or perform destructive actions. "
                "No further tools will run. Submit an incident description without instructions "
                "to override safeguards."
            )
            return {"safety_blocked": True, "final_report": refusal,
                    "report_complete": False, "messages": [AIMessage(content=refusal)]}
    return guarded


def _tool_receipts(result: dict, node: str, connection: str) -> list[dict[str, str]]:
    from langchain_core.messages import ToolMessage

    return [
        {"node": node, "connection": connection, "call_id": message.tool_call_id,
         "tool": message.name or "", "status": "success"}
        for message in result.get("messages", [])
        if isinstance(message, ToolMessage) and message.status == "success"
    ]


@_handle_content_filter
def evidence_investigator_node(state: ThreatAssessmentState) -> dict:
    """Gather and summarize raw incident evidence via the Defender MCP tool (Toolbox-backed)."""
    incident_context = _message_content(state["messages"][-1]) if state.get("messages") else ""
    if TOOL_RESOLUTION_UNAVAILABLE.get():
        return _degraded_specialist_result(
            EVIDENCE_INVESTIGATOR_PROMPT,
            incident_context,
            "evidence_report",
            "evidence_complete",
            "evidence_tool_unavailable",
        )
    agent = _get_specialist_agent(DEFENDER_TOOLBOX_CONNECTION, EVIDENCE_INVESTIGATOR_PROMPT)
    try:
        result = agent.invoke({"messages": [HumanMessage(content=incident_context)]})
    except ResourceNotFoundError:
        return _degraded_specialist_result(
            EVIDENCE_INVESTIGATOR_PROMPT,
            incident_context,
            "evidence_report",
            "evidence_complete",
            "evidence_tool_unavailable",
        )
    summary = _last_ai_message_content(result)
    return {
        "evidence_report": summary,
        "evidence_complete": True,
        "evidence_tool_unavailable": False,
        "tool_calls": _tool_receipts(result, "evidence_investigator", DEFENDER_TOOLBOX_CONNECTION),
    }


@_handle_content_filter
def risk_analyst_node(state: ThreatAssessmentState) -> dict:
    """Assess likelihood, severity, and blast radius via the anomaly MCP tool (Toolbox-backed)."""
    evidence_report = state.get("evidence_report") or ""
    if TOOL_RESOLUTION_UNAVAILABLE.get():
        return _degraded_specialist_result(
            RISK_ANALYST_PROMPT,
            evidence_report,
            "risk_report",
            "risk_complete",
            "risk_tool_unavailable",
        )
    agent = _get_specialist_agent(ANOMALY_TOOLBOX_CONNECTION, RISK_ANALYST_PROMPT)
    try:
        result = agent.invoke({"messages": [HumanMessage(content=evidence_report)]})
    except ResourceNotFoundError:
        return _degraded_specialist_result(
            RISK_ANALYST_PROMPT,
            evidence_report,
            "risk_report",
            "risk_complete",
            "risk_tool_unavailable",
        )
    assessment = _last_ai_message_content(result)
    return {
        "risk_report": assessment,
        "risk_complete": True,
        "risk_tool_unavailable": False,
        "tool_calls": _tool_receipts(result, "risk_analyst", ANOMALY_TOOLBOX_CONNECTION),
    }


@_handle_content_filter
def report_composer_node(state: ThreatAssessmentState) -> dict:
    """Combine the evidence summary and risk assessment into a final report."""
    combined_input = (
        f"Evidence summary:\n{state.get('evidence_report') or ''}\n\n"
        f"Risk assessment:\n{state.get('risk_report') or ''}"
    )
    final_report = _chat(REPORT_COMPOSER_PROMPT, combined_input)

    degraded_specialists = []
    if state.get("evidence_tool_unavailable"):
        degraded_specialists.append("Evidence Investigator (Defender MCP tool)")
    if state.get("risk_tool_unavailable"):
        degraded_specialists.append("Risk Analyst (anomaly MCP tool)")
    if degraded_specialists:
        final_report += (
            "\n\n---\n**Limitations:** "
            + " and ".join(degraded_specialists)
            + " ran without live tool-augmented data because the Azure Foundry "
            "Toolbox tool-resolution API is currently unavailable for this "
            "account/region. This assessment is based on the incident "
            "description alone and should be treated as preliminary."
        )

    from langchain_core.messages import AIMessage  # noqa: PLC0415

    return {
        "final_report": final_report,
        "report_complete": True,
        "messages": [AIMessage(content=final_report)],
    }


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
    if state.get("safety_blocked"):
        return END
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
