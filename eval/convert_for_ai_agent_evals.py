"""Convert eval/golden-dataset.jsonl into the JSON envelope microsoft/ai-agent-evals expects.

The golden dataset (one JSON object per line) is this repo's source of truth,
also consumed directly by eval/deterministic-tests/. The ai-agent-evals
GitHub Action instead requires a single JSON document shaped like
{"name": ..., "evaluators": [...], "data": [{"query": ...}, ...]}
(see https://github.com/microsoft/ai-agent-evals#data-file). This script
performs a read-only, additive conversion so the source dataset's format
does not need to change.

Evaluator selection here uses only eval/rubrics/evaluator-mapping.yaml's
`default_evaluators.built_in` list (coherence, groundedness, task_adherence).
The richer per-category overrides and custom rubric files in that mapping
are NOT applied yet -- wiring custom rubrics into ai-agent-evals'
`openai_graders`/custom-evaluator inputs is tracked as follow-on work.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DEFAULT_EVALUATORS = [
    "builtin.coherence",
    "builtin.groundedness",
    "builtin.task_adherence",
]


def load_records(golden_dataset_path: Path) -> list[dict]:
    records = []
    with golden_dataset_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {golden_dataset_path}") from exc
    return records


def to_query(record: dict) -> str:
    messages = record.get("input", {}).get("messages", [])
    user_messages = [m["content"] for m in messages if m.get("role") == "user"]
    return user_messages[-1] if user_messages else ""


def convert(golden_dataset_path: Path, output_path: Path) -> None:
    records = load_records(golden_dataset_path)
    if not records:
        raise ValueError("Golden dataset is empty")
    data = []
    seen = set()
    for record in records:
        identifier = record.get("id")
        query = to_query(record)
        if not identifier or identifier in seen or not isinstance(query, str) or not query.strip():
            raise ValueError("Every golden record must have a unique id and a nonempty user query")
        if not isinstance(record.get("expected"), dict) or not record["expected"]:
            raise ValueError(f"Missing expectations for {identifier}")
        seen.add(identifier)
        data.append({"id": identifier, "query": query, "context": query, "expected": record["expected"]})
    envelope = {
        "name": "threat-assessment-agent-golden-dataset",
        "evaluators": DEFAULT_EVALUATORS,
        "data": data,
    }
    output_path.write_text(json.dumps(envelope, indent=2), encoding="utf-8")
    print(f"Wrote {len(data)} record(s) to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(
            "Usage: python convert_for_ai_agent_evals.py <golden-dataset.jsonl> <output.json>",
            file=sys.stderr,
        )
        sys.exit(1)
    convert(Path(sys.argv[1]), Path(sys.argv[2]))
