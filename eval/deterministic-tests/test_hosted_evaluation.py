import base64
import json
import sys
import zlib
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from convert_for_ai_agent_evals import convert
from run_hosted_evaluation import (
    CaptureError,
    agent_instructions,
    capture,
    capture_summary,
    collect_output_items,
    completed_response,
    criteria,
    failed_judge_summary,
    runtime_state,
    task_query,
    validate_candidate_evidence,
    verified_safety_refusal,
)


@pytest.mark.parametrize("counts,expected_calls", [([5, 7], 2), ([5] * 7, 7), ([7], 1), ([8], 1)])
def test_output_collection_waits_only_for_missing_rows(monkeypatch, counts, expected_calls):
    calls = []
    delays = []
    pages = iter(counts)

    def list_items(**kwargs):
        calls.append(kwargs)
        return [SimpleNamespace(model_dump=lambda mode: {"id": "duplicate"}) for _ in range(next(pages))]

    client = SimpleNamespace(evals=SimpleNamespace(runs=SimpleNamespace(
        output_items=SimpleNamespace(list=list_items))))
    monkeypatch.setattr("run_hosted_evaluation.time.sleep", delays.append)
    result = collect_output_items(client, "evaluation", "run", 7)
    assert len(result) == counts[-1]
    assert len(calls) == expected_calls
    assert delays == [10] * (expected_calls - 1)
    assert all(call == {"eval_id": "evaluation", "run_id": "run"} for call in calls)
    assert all(item == {"id": "duplicate"} for item in result)


def filtered_stream():
    body = {"error": {"code": "content_filter", "innererror": {"code": "ResponsibleAIPolicyViolation"}}}
    return "data: " + json.dumps({"type": "error", "code": "server_error",
                                 "message": f"Error code: 400 - {body!r}"}) + "\n"


def test_safety_filter_is_not_a_completed_response():
    with pytest.raises(CaptureError) as error:
        completed_response(filtered_stream())
    assert error.value.code == "content_filter"


def test_capture_continues_after_filter_without_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("run_hosted_evaluation.shutil.which", lambda name: "bash")
    outputs = iter([filtered_stream(), stream()])
    calls = []

    def invoke(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=next(outputs), stderr="", returncode=0)

    monkeypatch.setattr("run_hosted_evaluation.subprocess.run", invoke)
    args = SimpleNamespace(output_dir=tmp_path, project_dir=tmp_path, agent="test", version="1")
    records = [{"id": "filtered", "query": "filter"}, {"id": "good", "query": "hello"}]
    captured = capture(records, args)
    assert len(calls) == 2
    for (command, options), record in zip(calls, records, strict=True):
        assert command == ["bash", "scripts/invoke-agent.sh"]
        assert options["cwd"] == tmp_path
        assert options["env"]["AGENT_NAME"] == "test"
        assert options["env"]["AGENT_VERSION"] == "1"
        assert options["env"]["AGENT_TEST_PROMPT"] == record["query"]
    assert captured[0]["capture_error"]["code"] == "content_filter"
    assert "response" not in captured[0]
    assert captured[1]["response"] == "Report"
    assert len(json.loads((tmp_path / "captured.json").read_text())) == 2
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "github-summary.md"))
    assert len(capture_summary(captured, args)) == 1
    assert "Release blocked" in (tmp_path / "github-summary.md").read_text()


def test_runtime_state_decodes_only_metadata():
    state = {"final_report": "report", "tool_calls": [], "safety_blocked": True}
    encoded = base64.b64encode(zlib.compress(json.dumps(state).encode())).decode()
    metadata = {"runtime_evidence": "v1:1", "runtime_evidence_0": encoded}
    assert runtime_state(metadata) == state
    assert runtime_state({"runtime_evidence": "v1:2", "runtime_evidence_0": encoded}) is None
    assert runtime_state({"runtime_evidence": "v1:1", "runtime_evidence_0": "bad"}) is None
    assert completed_response(stream(json.dumps(state)))["runtime_state"] is None


def test_runtime_state_rejects_decompression_overflow():
    encoded = base64.b64encode(zlib.compress(b"x" * 131073)).decode()
    assert runtime_state({"runtime_evidence": "v1:1", "runtime_evidence_0": encoded}) is None


def test_refusal_requires_explicit_policy_and_trusted_state():
    record = {"id": "inject", "response": "approved refusal", "expected": {
        "allow_safety_refusal": True, "safety_refusal_text": "approved refusal"},
        "runtime_state": {"safety_blocked": True, "final_report": "approved refusal", "tool_calls": []}}
    assert verified_safety_refusal(record)
    assert validate_candidate_evidence([record]) == []
    record["runtime_state"]["tool_calls"] = [{"connection": "defender-conn"}]
    assert not verified_safety_refusal(record)
    record["runtime_state"]["tool_calls"] = []
    record["expected"]["allow_safety_refusal"] = False
    assert not verified_safety_refusal(record)
    assert validate_candidate_evidence([record])


def stream(text="Report", status="completed"):
    response = {
        "status": status,
        "output": [
            {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}
        ],
    }
    return "data: " + json.dumps({"type": "response.completed", "response": response}) + "\n\n"


def test_captured_response():
    assert completed_response(stream().replace("\n", "\r\n"))["text"] == "Report"


def test_task_adherence_receives_real_agent_constraints():
    instructions = agent_instructions()
    assert "read-only" in instructions
    assert "explicitly decline to execute it" in instructions
    assert "You are the Report Composer" in instructions
    assert "Do not draw risk conclusions or make recommendations" not in instructions
    assert "You are the Evidence Investigator" not in instructions
    assert "You are the Risk Analyst" not in instructions
    mappings = {criterion["name"]: criterion["data_mapping"] for criterion in criteria("judge")}
    assert mappings["task_adherence"]["query"] == "{{item.task_query}}"
    assert mappings["groundedness"]["query"] == "{{item.query}}"
    assert mappings["coherence"]["query"] == "{{item.query}}"


@pytest.mark.parametrize("receipts", [[], [{"node": "evidence_investigator", "status": "success"}]])
def test_task_query_includes_composer_inputs_without_answer_leakage(receipts):
    record = {
        "query": "Reported attachment on FIN-WKS-014; telemetry unavailable for 24 hours.",
        "runtime_state": {
            "evidence_report": "Verification unavailable; device ID not supplied.",
            "risk_report": "Risk remains unknown; missing data is not safety.",
            "tool_calls": receipts,
            "final_report": "FINAL ANSWER MUST NOT BECOME INPUT EVIDENCE",
        },
    }
    messages = task_query(record)
    assert [message["role"] for message in messages] == ["system", "user"]
    assert messages[0]["content"] == agent_instructions()
    content = messages[1]["content"]
    assert record["query"] in content
    assert record["runtime_state"]["evidence_report"] in content
    assert record["runtime_state"]["risk_report"] in content
    assert f"recorded tool receipts: {len(receipts)}" in content
    assert record["runtime_state"]["final_report"] not in content


@pytest.mark.parametrize("state", [None, {}, {"evidence_report": "Evidence", "risk_report": "Risk"}])
def test_task_query_rejects_missing_composer_evidence(state):
    with pytest.raises(ValueError, match="composer"):
        task_query({"query": "Incident", "runtime_state": state})


def test_failed_judge_summary_identifies_case_and_preserves_reason():
    rows = failed_judge_summary([{
        "id": "4", "datasource_item": {"item": {"id": "miss-001"}},
        "results": [
            {"name": "coherence", "passed": True},
            {"name": "task_adherence", "passed": False, "reason": "Missing <detail>|reported\nobservation"},
        ],
    }])
    assert rows[-1] == "| miss-001 | task_adherence | Missing &lt;detail&gt;\\|reported observation |"
    assert not any("coherence" in row for row in rows)
    assert failed_judge_summary([]) == []


def test_failed_judge_summary_handles_missing_case_and_reason():
    rows = failed_judge_summary([{"id": "4", "results": [{"name": "task_adherence", "passed": False}]}])
    assert rows[-1] == "| 4 | task_adherence | No reason returned |"


def test_prose_cannot_claim_structured_or_tool_evidence():
    assert validate_candidate_evidence([{"id": "case", "response": "Everything passed"}])


def test_model_generated_json_is_not_runtime_evidence():
    assert validate_candidate_evidence([{"id": "case", "response": '{"tool_calls": []}'}])


def test_missing_tool_evidence_fails():
    record = {
        "id": "case",
        "runtime_state": {},
        "expected": {
            "allowed_tool_connections": {"evidence_investigator": ["defender-conn"]},
            "tool_unavailable_acceptable": False,
        },
    }
    assert validate_candidate_evidence([record])


@pytest.mark.parametrize(
    "raw",
    ["", stream(""), stream(status="failed"), stream() + 'data: {"type":"error"}\n', stream() + stream()],
)
def test_invalid_response(raw):
    with pytest.raises(ValueError):
        completed_response(raw)


def test_converter_preserves_all_cases_and_expectations(tmp_path):
    target = tmp_path / "dataset.json"
    convert(Path(__file__).parents[1] / "golden-dataset.jsonl", target)
    rows = json.loads(target.read_text())["data"]
    assert len(rows) == 8
    assert all(row["context"] == row["query"] and row["expected"] for row in rows)


@pytest.mark.parametrize("source", ["", "{bad json}", '{"id":"1"}', '{"id":"1","input":{"messages":[]}}'])
def test_converter_rejects_bad_dataset(tmp_path, source):
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text(source)
    with pytest.raises(ValueError):
        convert(dataset, tmp_path / "converted.json")
