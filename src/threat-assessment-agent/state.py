"""Graph state schema for the threat-assessment LangGraph agent.

Responses history (managed by the Foundry Responses protocol) is the
baseline source of truth for conversation state in this phase. The optional
Cosmos DB checkpointer below is an isolated, feature-flagged extension
point: it is never imported or connected to at module load time, and is
disabled unless ENABLE_COSMOS_CHECKPOINTER is explicitly set (see DD-02).
"""

from __future__ import annotations

import operator
import os
from typing import Annotated, Any, Optional

from typing_extensions import NotRequired, TypedDict


def _append_messages(
    existing: list[dict[str, Any]], update: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Reducer that appends new messages to the running transcript."""
    return existing + update


class ThreatAssessmentState(TypedDict):
    """State contract shared by the supervisor and specialist nodes."""

    messages: Annotated[list[dict[str, Any]], _append_messages]
    evidence_report: Optional[str]
    risk_report: Optional[str]
    final_report: Optional[str]
    evidence_complete: bool
    risk_complete: bool
    report_complete: bool
    safety_blocked: NotRequired[bool]
    tool_calls: Annotated[list[dict[str, str]], operator.add]
    # Set True when the corresponding specialist could not reach its Foundry
    # Toolbox MCP tool (tool-resolution API unavailable) and fell back to a
    # plain-LLM analysis. See graph.py's ResourceNotFoundError handling.
    evidence_tool_unavailable: bool
    risk_tool_unavailable: bool


def get_checkpointer() -> Optional[Any]:
    """Return an optional LangGraph checkpointer.

    Disabled by default (returns None), which is how the baseline graph is
    compiled in this phase. Set ENABLE_COSMOS_CHECKPOINTER=true plus the
    COSMOS_* environment variables below to opt in.

    NOTE: validated in Phase 7 (experiments/cosmos-checkpointer/) -- the
    original implementation called CosmosDBSaver(endpoint=..., credential=...,
    database_name=..., container_name=...) directly, but CosmosDBSaver's
    constructor only accepts a pre-built container proxy (those kwargs
    belong to the async-context-manager `from_conn_info` classmethod, not
    `__init__`); this raised TypeError as soon as the flag was enabled, in
    any environment. Fixed to build the container proxy via the
    (synchronous, non-network-calling) client/database/container accessors
    instead, matching the pattern CosmosDBSaver.from_conn_info uses
    internally. The Cosmos account/database/container must already exist
    (see infra/modules/cosmos-db.bicep); this function does not create them.
    """
    if os.environ.get("ENABLE_COSMOS_CHECKPOINTER", "").lower() not in ("1", "true", "yes"):
        return None

    from azure.cosmos.aio import CosmosClient  # noqa: PLC0415
    from azure.identity.aio import DefaultAzureCredential  # noqa: PLC0415
    from langchain_azure_cosmosdb import CosmosDBSaver  # noqa: PLC0415

    client = CosmosClient(os.environ["COSMOS_ENDPOINT"], credential=DefaultAzureCredential())
    database = client.get_database_client(os.environ.get("COSMOS_DATABASE_NAME", "threat-assessment-agent"))
    container = database.get_container_client(os.environ.get("COSMOS_CONTAINER_NAME", "checkpoints"))
    return CosmosDBSaver(container)

