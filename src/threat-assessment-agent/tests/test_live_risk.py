import json
import os
from pathlib import Path

import graph
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_STAGING_RISK") != "1",
    reason="Requires explicit opt-in and authenticated staging model/toolbox endpoints",
)


@pytest.mark.parametrize("case_id", ["conflict-001", "unauth-001"])
def test_risk_independently_verifies_supplied_inputs(case_id):
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    assert "-staging.services.ai.azure.com/" in endpoint
    assert "-staging" in os.environ["AZURE_OPENAI_ENDPOINT"]
    root = Path(__file__).resolve().parents[3]
    cases = [json.loads(line) for line in (root / "eval/golden-dataset.jsonl").read_text().splitlines()]
    case = next(item for item in cases if item["id"] == case_id)
    state = {"messages": case["input"]["messages"], "tool_calls": []}
    evidence = graph.evidence_investigator_node(state)
    result = graph.risk_analyst_node({**state, **evidence})
    receipts = result["tool_calls"]
    expected_tool = "score_anomaly" if case_id == "conflict-001" else "detect_login_anomalies"
    assert any(item["tool"] == f"anomaly-conn___{expected_tool}" for item in receipts)
    assert all(item["connection"] == "anomaly-conn" for item in receipts)