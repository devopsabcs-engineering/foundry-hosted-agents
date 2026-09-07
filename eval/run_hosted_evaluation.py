"""Capture version-bound hosted responses, evaluate them, and enforce a quality gate."""

import argparse
import json
import os
import runpy
import shutil
import subprocess
import time
from pathlib import Path

from evaluation_gate import METRICS, validate_results


def completed_response(raw: str) -> dict:
    events = [
        json.loads(line[6:])
        for line in raw.splitlines()
        if line.startswith("data: ") and line[6:] != "[DONE]"
    ]
    if any(event.get("type") in ("error", "response.failed", "response.incomplete") for event in events):
        raise ValueError("Agent stream contains an error or incomplete response")
    completed = [event["response"] for event in events if event.get("type") == "response.completed"]
    if len(completed) != 1 or completed[0].get("status") != "completed" or completed[0].get("error"):
        raise ValueError("Agent stream has no successful completed response")
    response = completed[0]
    text = "\n".join(
        part["text"]
        for output in response.get("output", [])
        if output.get("type") == "message" and output.get("role") == "assistant"
        for part in output.get("content", [])
        if part.get("type") == "output_text"
    )
    if not text.strip():
        raise ValueError("Agent returned no assistant text")
    return {"text": text, "output": response["output"]}


def capture(records: list[dict], args) -> list[dict]:
    executable = shutil.which("azd")
    if not executable:
        raise RuntimeError("azd is required to capture hosted responses")
    captured = []
    for index, record in enumerate(records, 1):
        query = record.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Dataset row {index} has no query")
        for attempt in range(1, 4):
            result = subprocess.run(
                [
                    executable,
                    "ai",
                    "agent",
                    "invoke",
                    args.agent,
                    query,
                    "--version",
                    args.version,
                    "--new-session",
                    "--new-conversation",
                    "--output",
                    "raw",
                ],
                cwd=args.project_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                check=False,
            )
            prefix = args.output_dir / f"case-{index}-attempt-{attempt}"
            prefix.with_suffix(".sse").write_text(result.stdout, encoding="utf-8")
            prefix.with_suffix(".stderr").write_text(result.stderr, encoding="utf-8")
            try:
                if result.returncode:
                    raise ValueError(f"azd exited with {result.returncode}")
                response = completed_response(result.stdout)
                break
            except ValueError as error:
                print(f"Case {index}, attempt {attempt}: {error}", flush=True)
                if attempt == 3:
                    raise
        captured.append({**record, "response": response["text"], "output_items": response["output"]})
        print(f"Captured case {index}/{len(records)} from {args.agent}:{args.version}", flush=True)
    return captured


def validate_candidate_evidence(captured: list[dict]) -> list[dict]:
    run_all_checks = runpy.run_path(str(Path(__file__).parent / "deterministic-tests" / "checks.py"))[
        "run_all_checks"
    ]

    failures = []
    for record in captured:
        candidate = record.get("runtime_state")
        if candidate is None:
            failures.append(
                {
                    "id": record["id"],
                    "error": "No structured graph state in hosted response; "
                    "schema and tool-execution requirements cannot be verified.",
                }
            )
            continue
        if not isinstance(candidate, dict):
            failures.append({"id": record["id"], "error": "Hosted state must be an object"})
            continue
        failures.extend(
            {"id": record["id"], "check": result.check_name, "error": result.message}
            for result in run_all_checks(record["expected"], candidate)
            if not result.passed
        )
        if not record["expected"].get("tool_unavailable_acceptable", False):
            required = record["expected"].get("allowed_tool_connections", {})
            receipts = {
                (item.get("node"), item.get("connection")) for item in candidate.get("tool_calls", [])
            }
            if any(
                not any((node, connection) in receipts for connection in connections)
                for node, connections in required.items()
            ):
                failures.append(
                    {"id": record["id"], "error": "Missing required specialist tool-call evidence"}
                )
    return failures


def criteria(deployment: str) -> list[dict]:
    return [
        {
            "type": "azure_ai_evaluator",
            "name": metric,
            "evaluator_name": f"builtin.{metric}",
            "initialization_parameters": {"deployment_name": deployment},
            "data_mapping": {
                "query": "{{item.query}}",
                "context": "{{item.context}}",
                "response": "{{item.output_items}}" if metric == "task_adherence" else "{{item.response}}",
            },
        }
        for metric in METRICS
    ]


def evaluate(captured: list[dict], args) -> None:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=args.endpoint, credential=credential) as project,
        project.get_openai_client() as client,
    ):
        evaluation = client.evals.create(
            name=f"Hosted CI {args.agent}:{args.version}",
            data_source_config={
                "type": "custom",
                "include_sample_schema": False,
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "context": {"type": "string"},
                        "response": {"type": "string"},
                        "output_items": {"type": "array"},
                    },
                    "required": ["query", "context", "response", "output_items"],
                },
            },
            testing_criteria=criteria(args.deployment),
        )
        run = client.evals.runs.create(
            eval_id=evaluation.id,
            name=f"{args.agent}:{args.version}",
            data_source={
                "type": "jsonl",
                "source": {
                    "type": "file_content",
                    "content": [{"item": record} for record in captured],
                },
            },
        )
        identity = {
            "eval_id": evaluation.id,
            "run_id": run.id,
            "endpoint": args.endpoint,
            "agent": args.agent,
            "version": args.version,
        }
        (args.output_dir / "run-identity.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
        print(f"Evaluation {evaluation.id}, run {run.id}", flush=True)
        deadline = time.monotonic() + 1200
        while run.status not in ("completed", "failed", "canceled", "cancelled"):
            if time.monotonic() >= deadline:
                raise TimeoutError(f"Evaluation exceeded 20 minutes: {run.id}")
            time.sleep(10)
            run = client.evals.runs.retrieve(eval_id=evaluation.id, run_id=run.id)
        items = [
            item.model_dump(mode="json")
            for item in client.evals.runs.output_items.list(eval_id=evaluation.id, run_id=run.id)
        ]
        result = {"run": run.model_dump(mode="json"), "items": items}
        (args.output_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        summary = [
            f"## Hosted Evaluation: {args.agent}:{args.version}",
            f"Run: {run.id}",
            "",
            "| Metric | Passed | Errored | Failed |",
            "| --- | --- | --- | --- |",
        ]
        for metric in result["run"].get("per_testing_criteria_results", []):
            summary.append(
                f"| {metric['testing_criteria']} | {metric['passed']} | "
                f"{metric.get('errored', 'unknown')} | {metric['failed']} |"
            )
        try:
            failures = validate_candidate_evidence(captured)
            (args.output_dir / "candidate-policy.json").write_text(
                json.dumps(failures, indent=2), encoding="utf-8"
            )
            validate_results(result["run"], items, len(captured), args.minimum_pass_rate)
            if failures:
                raise ValueError(
                    f"Candidate evidence policy failed ({len(failures)} checks); see candidate-policy.json"
                )
        except ValueError as error:
            summary.extend(["", f"**FAIL:** {error}"])
            raise
        else:
            summary.extend(["", "**PASS:** all results complete and within policy."])
        finally:
            text = "\n".join(summary) + "\n"
            (args.output_dir / "summary.md").write_text(text, encoding="utf-8")
            if os.environ.get("GITHUB_STEP_SUMMARY"):
                with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
                    handle.write(text)
            print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--deployment", required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--project-dir", type=Path, default=Path.cwd())
    parser.add_argument("--minimum-pass-rate", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 < args.minimum_pass_rate <= 1:
        parser.error("minimum-pass-rate must be in (0, 1]")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(args.dataset.read_text(encoding="utf-8"))["data"]
    if not records:
        raise ValueError("Evaluation dataset is empty")
    environment = subprocess.run(
        [shutil.which("azd") or "azd", "env", "get-values", "--output", "json"],
        cwd=args.project_dir,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=True,
    )
    if json.loads(environment.stdout).get("FOUNDRY_PROJECT_ENDPOINT", "").rstrip("/") != args.endpoint.rstrip(
        "/"
    ):
        raise ValueError("Selected azd environment does not match the evaluation endpoint")
    captured = capture(records, args)
    (args.output_dir / "captured.json").write_text(json.dumps(captured, indent=2), encoding="utf-8")
    evaluate(captured, args)


if __name__ == "__main__":
    main()
