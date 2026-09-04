"""Benchmark script for Step 7.2 (Cosmos DB checkpointer experiment).

Two parts:

1. Direct Cosmos read/write benchmark (bypasses CosmosDBSaver) against the
   live `checkpoints` container provisioned by
   `infra/modules/cosmos-db.bicep`, using the actual `azure-cosmos` SDK so
   the per-operation RU charge (`x-ms-request-charge`) can be captured --
   `langchain_azure_cosmosdb.CosmosDBSaver`'s public API does not itself
   expose RU charge.
2. A real LangGraph integration test: compiles a small `StateGraph` typed
   with the actual `ThreatAssessmentState` schema from
   `src/threat-assessment-agent/state.py` (imported directly, not
   reimplemented), with dummy (non-LLM) node bodies producing
   representative-size report text, run through `CosmosDBSaver` across
   multiple turns on one thread_id. This exercises the real
   `state.get_checkpointer()` extension point end-to-end (same function the
   deployed agent's graph.py already calls at compile time) without
   incurring live Azure OpenAI cost/latency for every turn.

Requires: ENABLE_COSMOS_CHECKPOINTER=true, COSMOS_ENDPOINT, and (optionally)
COSMOS_DATABASE_NAME / COSMOS_CONTAINER_NAME environment variables pointing
at the live account deployed for this experiment. Authenticates via
DefaultAzureCredential (the same `az login` identity granted Cosmos DB
Built-in Data Contributor by cosmos-db.bicep's dataPlanePrincipalIds).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_SRC = REPO_ROOT / "src" / "threat-assessment-agent"
sys.path.insert(0, str(AGENT_SRC))

from state import ThreatAssessmentState, get_checkpointer  # noqa: E402

ACCOUNT_ENDPOINT = os.environ.get(
    "COSMOS_ENDPOINT", "https://cosmos-air-canada-threat-assessment-poc.documents.azure.com:443/"
)
DATABASE_NAME = os.environ.get("COSMOS_DATABASE_NAME", "threat-assessment-agent")
CONTAINER_NAME = os.environ.get("COSMOS_CONTAINER_NAME", "checkpoints")

# Representative report text sizes, modeled on the real reports observed in
# Step 7.1 smoke-test output (a few hundred to ~2KB of markdown per report).
_SAMPLE_REPORT = (
    "# Security Threat Assessment\n\n" + ("Representative finding text. " * 80)
)


async def _direct_cosmos_benchmark() -> dict:
    """Bypass CosmosDBSaver: raw upsert_item/read_item RU-charge capture."""
    from azure.cosmos.aio import CosmosClient
    from azure.identity.aio import DefaultAzureCredential

    credential = DefaultAzureCredential()
    results: dict = {"writes": [], "reads": []}
    try:
        async with CosmosClient(ACCOUNT_ENDPOINT, credential=credential) as client:
            database = client.get_database_client(DATABASE_NAME)
            container = database.get_container_client(CONTAINER_NAME)

            for i in range(3):
                doc_id = f"bench-{uuid.uuid4()}"
                doc = {
                    "id": doc_id,
                    "partition_key": doc_id,
                    "evidence_report": _SAMPLE_REPORT,
                    "risk_report": _SAMPLE_REPORT,
                    "final_report": _SAMPLE_REPORT,
                    "turn": i,
                }
                started = time.monotonic()
                resp = await container.upsert_item(doc)
                elapsed = time.monotonic() - started
                charge = resp.get_response_headers().get("x-ms-request-charge")
                results["writes"].append(
                    {"latency_seconds": round(elapsed, 4), "request_charge_ru": charge, "doc_id": doc_id}
                )

                started = time.monotonic()
                read_resp = await container.read_item(doc_id, partition_key=doc_id)
                elapsed = time.monotonic() - started
                read_charge = read_resp.get_response_headers().get("x-ms-request-charge")
                results["reads"].append({"latency_seconds": round(elapsed, 4), "request_charge_ru": read_charge})

                # Cleanup: keep the container empty of benchmark noise.
                await container.delete_item(doc_id, partition_key=doc_id)
    finally:
        await credential.close()
    return results


def _build_minimal_graph():
    """Compile a minimal StateGraph typed with the real ThreatAssessmentState.

    Dummy node bodies (no LLM calls) so this benchmark isolates checkpointer
    overhead from LLM completion latency, while still exercising a
    genuinely representative state shape and size.
    """
    from langgraph.graph import END, START, StateGraph

    def evidence_node(state: ThreatAssessmentState) -> dict:
        return {"evidence_report": _SAMPLE_REPORT, "evidence_complete": True, "evidence_tool_unavailable": False}

    def risk_node(state: ThreatAssessmentState) -> dict:
        return {"risk_report": _SAMPLE_REPORT, "risk_complete": True, "risk_tool_unavailable": False}

    def report_node(state: ThreatAssessmentState) -> dict:
        return {"final_report": _SAMPLE_REPORT, "report_complete": True}

    workflow = StateGraph(ThreatAssessmentState)
    workflow.add_node("evidence", evidence_node)
    workflow.add_node("risk", risk_node)
    workflow.add_node("report", report_node)
    workflow.add_edge(START, "evidence")
    workflow.add_edge("evidence", "risk")
    workflow.add_edge("risk", "report")
    workflow.add_edge("report", END)
    return workflow


async def _langgraph_integration_benchmark() -> dict:
    """Run the real state.get_checkpointer() extension point end-to-end."""
    os.environ["ENABLE_COSMOS_CHECKPOINTER"] = "true"
    os.environ.setdefault("COSMOS_ENDPOINT", ACCOUNT_ENDPOINT)
    os.environ.setdefault("COSMOS_DATABASE_NAME", DATABASE_NAME)
    os.environ.setdefault("COSMOS_CONTAINER_NAME", CONTAINER_NAME)

    checkpointer = get_checkpointer()
    assert checkpointer is not None, "get_checkpointer() returned None -- ENABLE_COSMOS_CHECKPOINTER not honored"

    workflow = _build_minimal_graph()
    graph = workflow.compile(checkpointer=checkpointer)

    thread_id = f"bench-thread-{uuid.uuid4()}"
    config = {"configurable": {"thread_id": thread_id}}

    turn_latencies = []
    for turn in range(3):
        started = time.monotonic()
        await graph.ainvoke(
            {"messages": [{"role": "user", "content": f"turn {turn}"}]},
            config=config,
        )
        turn_latencies.append(round(time.monotonic() - started, 4))

    started = time.monotonic()
    history = [c async for c in graph.aget_state_history(config)]
    list_latency = round(time.monotonic() - started, 4)

    # Baseline: same graph, no checkpointer, no persistence overhead.
    baseline_graph = _build_minimal_graph().compile(checkpointer=None)
    baseline_started = time.monotonic()
    await baseline_graph.ainvoke({"messages": [{"role": "user", "content": "baseline turn"}]})
    baseline_latency = round(time.monotonic() - baseline_started, 4)

    return {
        "thread_id": thread_id,
        "per_turn_latencies_seconds": turn_latencies,
        "checkpoint_history_count": len(history),
        "checkpoint_list_latency_seconds": list_latency,
        "baseline_no_checkpointer_latency_seconds": baseline_latency,
    }


async def main() -> None:
    direct = await _direct_cosmos_benchmark()
    integration = await _langgraph_integration_benchmark()

    summary = {"direct_cosmos_benchmark": direct, "langgraph_integration_benchmark": integration}
    print(json.dumps(summary, indent=2))

    out_path = Path(__file__).parent / "results" / "benchmark-results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Wrote results to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
