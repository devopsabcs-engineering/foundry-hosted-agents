import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))
from convert_for_ai_agent_evals import convert
from run_hosted_evaluation import completed_response, validate_candidate_evidence


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
