import json
import os
from pathlib import Path

import graph
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_LIVE_STAGING_RISK") != "1",
    reason="Requires explicit opt-in and authenticated staging model/toolbox endpoints",
)


@pytest.mark.parametrize("repeat", [1, 2])
@pytest.mark.parametrize("case_id", ["conflict-001", "unauth-001", "fp-001"])
def test_specialists_verify_inputs_and_report_format(case_id, repeat):
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    assert "-staging.services.ai.azure.com/" in endpoint
    assert "-staging" in os.environ["AZURE_OPENAI_ENDPOINT"]
    root = Path(__file__).resolve().parents[3]
    cases = [json.loads(line) for line in (root / "eval/golden-dataset.jsonl").read_text().splitlines()]
    case = next(item for item in cases if item["id"] == case_id)
    state = {"messages": case["input"]["messages"], "tool_calls": []}
    evidence = graph.evidence_investigator_node(state)
    assert {item["tool"] for item in evidence["tool_calls"]} == {
        "defender-conn___get_device_risk", "defender-conn___list_vulnerabilities",
    }
    assert all(item["connection"] == "defender-conn" for item in evidence["tool_calls"])
    result = graph.risk_analyst_node({**state, **evidence})
    receipts = result["tool_calls"]
    expected_tool = "score_anomaly" if case_id == "conflict-001" else "detect_login_anomalies"
    assert any(item["tool"] == f"anomaly-conn___{expected_tool}" for item in receipts)
    assert all(item["connection"] == "anomaly-conn" for item in receipts)
    if case_id == "conflict-001":
        assert all(item["tool"] != "anomaly-conn___detect_login_anomalies" for item in receipts)
    report = graph.report_composer_node({**state, **evidence, **result})["final_report"]
    assert "report" in report.lstrip().splitlines()[0].casefold()
    assert not any(line.strip() in {"---", "***", "___", "```"} for line in report.splitlines())