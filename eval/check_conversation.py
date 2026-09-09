"""Check routed hosted-agent history resubmission, as used by the web pilot."""

import argparse
import json
import os
import uuid
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from run_hosted_evaluation import completed_response


def check_conversation(invoke, reference):
    history = [{"role": "user", "content": (
        f"For this synthetic pilot check, remember the reference {reference}. "
        "Confirm the reference. No incident or device is being reported."
    )}]
    first = invoke(history)
    if reference not in first:
        raise ValueError("First response did not retain the synthetic reference")
    history = history + [{"role": "assistant", "content": first}, {"role": "user", "content": (
        "What exact pilot reference did I give in my previous message? "
        "Use only this conversation; do not infer device or account details."
    )}]
    follow_up = invoke(history)
    if reference not in follow_up:
        raise ValueError("Follow-up lost the earlier reference")
    independent = invoke([{"role": "user", "content": (
        "This is an independent conversation. What pilot reference have I provided here? "
        "If none is provided, say it is unknown; do not invent one."
    )}])
    if reference in independent:
        raise ValueError("Independent request inherited another conversation's reference")
    return {"reference": reference, "checks": 3, "passed": 3}


def main():
    from azure.identity import AzureCliCredential

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="Full staging Responses endpoint")
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    endpoint = urlparse(args.endpoint)
    if endpoint.scheme != "https" or not (endpoint.hostname or "").endswith(".services.ai.azure.com"):
        raise ValueError("Expected an HTTPS Foundry endpoint")
    if "-staging" not in (endpoint.hostname or ""):
        raise ValueError("This regression targets staging only")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    credential = AzureCliCredential()
    responses = []

    def invoke(messages):
        token = credential.get_token("https://ai.azure.com/.default").token
        request = Request(args.endpoint, data=json.dumps({
            "input": messages, "stream": True, "store": False,
        }).encode(), headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
        with urlopen(request, timeout=180) as response:
            raw = response.read().decode("utf-8")
        (args.output_dir / f"turn-{len(responses) + 1}.sse").write_text(raw, encoding="utf-8")
        parsed = completed_response(raw)
        responses.append(parsed["text"])
        return parsed["text"]

    try:
        result = check_conversation(invoke, "PILOT-" + uuid.uuid4().hex[:12].upper())
        (args.output_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("Conversation regression: 3/3 passed (reference, follow-up, independent request).")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
                summary.write("\n## Conversation Regression\n\n3/3 passed on the staging routed endpoint: "
                              "reference retention, full-history follow-up, independent request. "
                              "Synthetic responses retained in conversation-evidence.\n")
    finally:
        credential.close()


if __name__ == "__main__":
    main()