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
    capture,
    capture_summary,
    completed_response,
    runtime_state,
    validate_candidate_evidence,
    verified_safety_refusal,
)


def filtered_stream():
    body = {"error": {"code": "content_filter", "innererror": {"code": "ResponsibleAIPolicyViolation"}}}
    return "data: " + json.dumps({"type": "error", "code": "server_error",
                                 "message": f"Error code: 400 - {body!r}"}) + "\n"


def test_safety_filter_is_not_a_completed_response():
    with pytest.raises(CaptureError) as error:
        completed_response(filtered_stream())
    assert error.value.code == "content_filter"


def test_capture_continues_after_filter_without_retry(monkeypatch, tmp_path):
    monkeypatch.setattr("run_hosted_evaluation.shutil.which", lambda name: "azd")
    outputs = iter([filtered_stream(), stream()])
    monkeypatch.setattr("run_hosted_evaluation.subprocess.run", lambda *args, **kwargs:
                        SimpleNamespace(stdout=next(outputs), stderr="", returncode=0))
    args = SimpleNamespace(output_dir=tmp_path, project_dir=tmp_path, agent="test", version="1")
    records = [{"id": "filtered", "query": "filter"}, {"id": "good", "query": "hello"}]
    captured = capture(records, args)
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
