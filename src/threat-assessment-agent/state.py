"""Graph state schema for the threat-assessment LangGraph agent.

Responses history (managed by the Foundry Responses protocol) is the
baseline source of truth for conversation state in this phase. The optional
Cosmos DB checkpointer below is an isolated, feature-flagged extension
point: it is never imported or connected to at module load time, and is
disabled unless ENABLE_COSMOS_CHECKPOINTER is explicitly set (see DD-02).
"""

from __future__ import annotations

import os
from typing import Annotated, Any, Optional

from typing_extensions import TypedDict


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


def get_checkpointer() -> Optional[Any]:
    """Return an optional LangGraph checkpointer.

    Disabled by default (returns None), which is how the baseline graph is
    compiled in this phase. Set ENABLE_COSMOS_CHECKPOINTER=true plus the
    COSMOS_* environment variables below to opt in.

    NOTE: the Cosmos DB + Foundry Hosted Agent sandbox pairing is unverified
    (see planning log DR-04) and must be validated in Phase 7 before use;
    this function only defines the isolated extension point.
    """
    if os.environ.get("ENABLE_COSMOS_CHECKPOINTER", "").lower() not in ("1", "true", "yes"):
        return None

    from azure.identity import DefaultAzureCredential  # noqa: PLC0415
    from langchain_azure_cosmosdb import CosmosDBSaver  # noqa: PLC0415

    return CosmosDBSaver(
        endpoint=os.environ["COSMOS_ENDPOINT"],
        credential=DefaultAzureCredential(),
        database_name=os.environ.get("COSMOS_DATABASE_NAME", "threat-assessment-agent"),
        container_name=os.environ.get("COSMOS_CONTAINER_NAME", "checkpoints"),
    )
