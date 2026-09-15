"""Capture version-bound hosted responses, evaluate them, and enforce a quality gate."""

import argparse
import ast
import base64
import binascii
import html
import json
import os
import runpy
import shutil
import subprocess
import time
import zlib
from pathlib import Path

from evaluation_gate import METRICS, validate_results


class CaptureError(ValueError):
    def __init__(self, message: str, code: str = "response_error"):
        super().__init__(message)
        self.code = code


def stream_error(event: dict) -> CaptureError:
    error = event.get("response", {}).get("error") or event.get("error") or event
    message = error.get("message", "Agent stream contains an error or incomplete response")
    code = error.get("code", "response_error")
    if message.startswith("Error code: 400 - "):
        try:
            body = ast.literal_eval(message.removeprefix("Error code: 400 - "))
            if body.get("error", {}).get("code") == "content_filter":
                code = "content_filter"
        except (SyntaxError, ValueError, AttributeError):
            pass
    if code == "content_filter":
        return CaptureError(
            "Azure safety filter rejected the request; no assistant response was generated", code
        )
    return CaptureError(message, code)


def completed_response(raw: str) -> dict:
    events = [
        json.loads(line[6:])
        for line in raw.splitlines()
        if line.startswith("data: ") and line[6:] != "[DONE]"
    ]
    for event in events:
        if event.get("type") in ("error", "response.failed", "response.incomplete"):
            raise stream_error(event)
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
    return {
        "text": text,
        "output": response["output"],
        "runtime_state": runtime_state(response.get("metadata")),
    }


def runtime_state(metadata) -> dict | None:
    if not isinstance(metadata, dict) or not isinstance(metadata.get("runtime_evidence"), str):
        return None
    descriptor = metadata["runtime_evidence"].split(":")
    if len(descriptor) != 2 or descriptor[0] != "v1" or not descriptor[1].isdigit():
        return None
    count = int(descriptor[1])
    if not 1 <= count <= 15:
        return None
    try:
        chunks = [metadata[f"runtime_evidence_{index}"] for index in range(count)]
        if any(not isinstance(chunk, str) or len(chunk) > 512 for chunk in chunks):
            return None
        compressed = base64.b64decode("".join(chunks), validate=True)
        decoder = zlib.decompressobj()
        payload = decoder.decompress(compressed, 131073)
        if len(payload) > 131072 or not decoder.eof or decoder.unused_data:
            return None
        state = json.loads(payload)
        return state if isinstance(state, dict) else None
    except (KeyError, ValueError, binascii.Error, zlib.error, UnicodeDecodeError):
        return None


def capture(records: list[dict], args) -> list[dict]:
    executable = shutil.which("bash")
    if not executable:
        raise RuntimeError("bash is required to capture hosted responses")
    captured = []
    for index, record in enumerate(records, 1):
        query = record.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError(f"Dataset row {index} has no query")
        response = None
        failure = None
        for attempt in range(1, 4):
            prefix = args.output_dir / f"case-{index}-attempt-{attempt}"
            try:
                result = subprocess.run(
                [executable, "scripts/invoke-agent.sh"],
                cwd=args.project_dir,
                env={**os.environ, "AGENT_NAME": args.agent, "AGENT_VERSION": args.version,
                     "AGENT_TEST_PROMPT": query},
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
                check=False,
                )
            except subprocess.TimeoutExpired as error:
                for suffix, output in ((".sse", error.stdout), (".stderr", error.stderr)):
                    if isinstance(output, bytes):
                        output = output.decode("utf-8", errors="replace")
                    prefix.with_suffix(suffix).write_text(output or "", encoding="utf-8")
                failure = {"code": "timeout", "message": "Hosted invocation exceeded 180 seconds"}
                continue
            prefix.with_suffix(".sse").write_text(result.stdout, encoding="utf-8")
            prefix.with_suffix(".stderr").write_text(result.stderr, encoding="utf-8")
            try:
                if result.returncode:
                    raise ValueError(f"Hosted invocation exited with {result.returncode}")
                response = completed_response(result.stdout)
                failure = None
                break
            except ValueError as error:
                failure = {"code": getattr(error, "code", "response_error"), "message": str(error)}
                print(f"Case {index}, attempt {attempt}: {error}", flush=True)
                if failure["code"] == "content_filter":
                    break
        if response is None:
            captured.append({**record, "capture_error": failure})
        else:
            captured.append({**record, "response": response["text"], "output_items": response["output"],
                             "runtime_state": response["runtime_state"]})
        (args.output_dir / "captured.json").write_text(json.dumps(captured, indent=2), encoding="utf-8")
        status = "FAILED" if response is None else "Captured"
        print(f"{status} case {index}/{len(records)} from {args.agent}:{args.version}", flush=True)
    return captured


def capture_summary(captured: list[dict], args) -> list[dict]:
    failures = [record for record in captured if record.get("capture_error")]
    lines = ["## Hosted Capture", "", f"Completed responses: {len(captured) - len(failures)}/{len(captured)}",
             "", "| Case | Capture outcome |", "| --- | --- |"]
    for record in captured:
        outcome = record.get("capture_error", {}).get("code", "completed")
        identifier = str(record["id"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {identifier} | {outcome} |")
    if failures:
        lines.extend(["", "Release blocked: failed captures are not scored or counted as passes."])
    text = "\n".join(lines) + "\n"
    (args.output_dir / "capture-summary.md").write_text(text, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(text)
    print(text)
    return failures


def verified_safety_refusal(record: dict) -> bool:
    expected = record.get("expected", {})
    state = record.get("runtime_state")
    refusal = expected.get("safety_refusal_text")
    return bool(
        expected.get("allow_safety_refusal") is True
        and isinstance(state, dict)
        and state.get("safety_blocked") is True
        and isinstance(refusal, str) and refusal
        and state.get("final_report") == record.get("response") == refusal
        and state.get("tool_calls") == []
        and not any(state.get(field) for field in ("evidence_complete", "risk_complete", "report_complete"))
    )


def validate_candidate_evidence(captured: list[dict]) -> list[dict]:
    run_all_checks = runpy.run_path(str(Path(__file__).parent / "deterministic-tests" / "checks.py"))[
        "run_all_checks"
    ]

    failures = []
    for record in captured:
        if verified_safety_refusal(record):
            continue
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
        if candidate.get("safety_blocked"):
            failures.append(
                {"id": record["id"], "error": "Safety refusal does not satisfy this case's policy"}
            )
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


def agent_instructions() -> str:
    source = Path(__file__).parents[1] / "src" / "threat-assessment-agent" / "graph.py"
    names = {"REPORT_COMPOSER_PROMPT"}
    prompts = {}
    for statement in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    prompts[target.id] = ast.literal_eval(statement.value)
    if prompts.keys() != names or any(not isinstance(value, str) or not value for value in prompts.values()):
        raise ValueError("Cannot resolve agent instructions for task-adherence evaluation")
    return "\n\n".join(prompts.values())


def task_query(record: dict) -> list[dict]:
    state = record.get("runtime_state")
    if (
        not isinstance(state, dict)
        or any(not isinstance(state.get(field), str) or not state[field].strip()
               for field in ("evidence_report", "risk_report"))
        or not isinstance(state.get("tool_calls"), list)
    ):
        raise ValueError("Missing structured composer input evidence")
    source = Path(__file__).parents[1] / "src" / "threat-assessment-agent" / "report_input.py"
    build_report_input = runpy.run_path(str(source))["build_report_input"]
    return [
        {"role": "system", "content": agent_instructions()},
        {"role": "user", "content": build_report_input(
            record["query"], state["evidence_report"], state["risk_report"], len(state["tool_calls"])
        )},
    ]


def criteria(deployment: str) -> list[dict]:
    return [
        {
            "type": "azure_ai_evaluator",
            "name": metric,
            "evaluator_name": f"builtin.{metric}",
            "initialization_parameters": {"deployment_name": deployment},
            "data_mapping": {
                "query": "{{item.task_query}}" if metric == "task_adherence" else "{{item.query}}",
                "context": "{{item.context}}",
                "response": "{{item.output_items}}" if metric == "task_adherence" else "{{item.response}}",
            },
        }
        for metric in METRICS
    ]


def collect_output_items(client, eval_id: str, run_id: str, expected_count: int) -> list[dict]:
    for attempt in range(7):
        items = [
            item.model_dump(mode="json")
            for item in client.evals.runs.output_items.list(eval_id=eval_id, run_id=run_id)
        ]
        if len(items) >= expected_count or attempt == 6:
            return items
        print(f"Evaluation outputs available: {len(items)}/{expected_count}; retrying retrieval", flush=True)
        time.sleep(10)


def failed_judge_summary(items: list[dict]) -> list[str]:
    rows = []
    for item in items:
        source = item.get("datasource_item") or {}
        record = source.get("item", source)
        identifier = record.get("id", item.get("id", "unknown"))
        for result in item.get("results", []):
            if result.get("passed") is False:
                values = [
                    identifier, result.get("name", "unknown"), result.get("reason") or "No reason returned",
                ]
                cells = [html.escape(str(value)).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
                         for value in values]
                rows.append("| " + " | ".join(cells) + " |")
    return (["", "### Failed Judge Checks", "", "| Case | Metric | Judge reason |",
             "| --- | --- | --- |", *rows] if rows else [])


def evaluate(captured: list[dict], args) -> None:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    evaluation_records = [
        {**record, "task_query": task_query(record)}
        for record in captured
    ]
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
                        "task_query": {"type": "array"},
                        "context": {"type": "string"},
                        "response": {"type": "string"},
                        "output_items": {"type": "array"},
                    },
                    "required": ["query", "task_query", "context", "response", "output_items"],
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
                    "content": [{"item": record} for record in evaluation_records],
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
        items = collect_output_items(client, evaluation.id, run.id, len(captured))
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
        summary.extend(failed_judge_summary(items))
        try:
            validate_results(result["run"], items, len(captured), args.minimum_pass_rate)
        except ValueError as error:
            summary.extend(["", f"**FAIL:** {error}"])
            raise
        else:
            summary.extend(["", "**PASS:** model-judged responses satisfy quality policy; "
                            "the release also requires capture and deterministic policy checks."])
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
    failures = capture_summary(captured, args)
    successful = [record for record in captured if not record.get("capture_error")]
    policy_failures = validate_candidate_evidence(successful)
    (args.output_dir / "candidate-policy.json").write_text(
        json.dumps(policy_failures, indent=2), encoding="utf-8"
    )
    refusals = [record["id"] for record in successful if verified_safety_refusal(record)]
    policy_summary = (
        f"\n## Candidate Policy\n\nVerified safety refusals: {refusals}\n\n"
        f"Deterministic policy failures: {len(policy_failures)}\n"
    )
    (args.output_dir / "policy-summary.md").write_text(policy_summary, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(policy_summary)
    judged = [record for record in successful if not verified_safety_refusal(record)]
    if judged:
        evaluate(judged, args)
    if failures:
        raise ValueError(f"{len(failures)}/{len(captured)} cases failed capture; release blocked")
    if policy_failures:
        raise ValueError(
            f"Candidate evidence policy failed ({len(policy_failures)} checks); see candidate-policy.json"
        )


if __name__ == "__main__":
    main()
