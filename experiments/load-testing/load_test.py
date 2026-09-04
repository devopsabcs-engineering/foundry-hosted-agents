"""PoC-scale async load generator for the deployed threat-assessment-agent.

Hits the Responses SSE endpoint directly with aiohttp. Not a production
load-testing tool -- a lightweight probe sized for this PoC's time/cost
budget (see experiments/load-testing/README.md).

Usage:
    python load_test.py concurrent-sessions --count 5 --out results/x.json
    python load_test.py same-thread-turns --count 5 --out results/x.json
    python load_test.py sequential-cold-start --count 5 --out results/x.json

Auth: shells out to `az account get-access-token --resource https://ai.azure.com`
once per run and reuses the token for every request in that run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_ENDPOINT = (
    "https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/"
    "proj-air-canada-threat-assessment-poc/agents/threat-assessment-agent/endpoint/"
    "protocols/openai/responses?api-version=v1"
)

MESSAGE = (
    "A user reports their corporate laptop is running unusually slow and shows a "
    "pop-up asking to enter a password on an unfamiliar site. Give a brief threat "
    "assessment."
)


def _get_bearer_token() -> str:
    """Fetch a bearer token for the ai.azure.com resource via az CLI."""
    proc = subprocess.run(
        ["az", "account", "get-access-token", "--resource", "https://ai.azure.com", "--query", "accessToken", "-o", "tsv"],
        capture_output=True,
        text=True,
        check=True,
        shell=(sys.platform == "win32"),
    )
    token = proc.stdout.strip()
    if not token:
        raise RuntimeError("az account get-access-token returned an empty token")
    return token


async def _invoke_once(
    session: "Any",
    endpoint: str,
    message: str,
    conversation_id: str | None,
) -> dict[str, Any]:
    """Send one Responses-protocol request and measure end-to-end latency.

    Returns a dict with latency_seconds, status, event_count, conversation_id,
    and error (if any). Reads the full SSE stream to completion so latency
    reflects the whole response, not just the first byte.
    """
    body: dict[str, Any] = {
        "input": [{"role": "user", "content": [{"type": "input_text", "text": message}]}],
        "stream": True,
    }
    if conversation_id:
        body["conversation"] = conversation_id

    started = time.monotonic()
    result: dict[str, Any] = {"conversation_id": conversation_id, "error": None}
    try:
        async with session.post(endpoint, json=body) as resp:
            result["status"] = resp.status
            event_count = 0
            response_conversation_id = None
            async for line in resp.content:
                text = line.decode("utf-8", errors="replace").strip()
                if not text or not text.startswith("data:"):
                    continue
                event_count += 1
                payload = text[len("data:") :].strip()
                try:
                    parsed = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                conv = parsed.get("response", {}).get("conversation", {})
                if isinstance(conv, dict) and conv.get("id"):
                    response_conversation_id = conv["id"]
            result["event_count"] = event_count
            result["response_conversation_id"] = response_conversation_id
    except Exception as exc:  # noqa: BLE001 - a load probe must record every failure mode
        result["status"] = None
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        result["latency_seconds"] = round(time.monotonic() - started, 3)
    return result


async def run_concurrent_sessions(endpoint: str, token: str, count: int) -> list[dict[str, Any]]:
    """N independent new-conversation requests fired concurrently."""
    import aiohttp

    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        tasks = [_invoke_once(session, endpoint, MESSAGE, conversation_id=None) for _ in range(count)]
        return await asyncio.gather(*tasks)


async def run_same_thread_turns(endpoint: str, token: str, count: int) -> list[dict[str, Any]]:
    """N concurrent requests against ONE conversation (seeded first, single-threaded)."""
    import aiohttp

    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession(headers=headers) as session:
        seed = await _invoke_once(session, endpoint, MESSAGE, conversation_id=None)
        conv_id = seed.get("response_conversation_id")
        tasks = [
            _invoke_once(session, endpoint, f"Follow-up turn #{i}: any update?", conversation_id=conv_id)
            for i in range(count)
        ]
        results = await asyncio.gather(*tasks)
        return [seed, *results]


async def run_sequential_cold_start(endpoint: str, token: str, count: int) -> list[dict[str, Any]]:
    """N new-conversation requests run one at a time (no concurrency)."""
    import aiohttp

    headers = {"Authorization": f"Bearer {token}"}
    results = []
    async with aiohttp.ClientSession(headers=headers) as session:
        for _ in range(count):
            results.append(await _invoke_once(session, endpoint, MESSAGE, conversation_id=None))
    return results


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1))))
    return ordered[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["concurrent-sessions", "same-thread-turns", "sequential-cold-start"])
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--out", default=None, help="Path to write raw JSON results")
    args = parser.parse_args()

    token = _get_bearer_token()

    wall_started = time.monotonic()
    if args.mode == "concurrent-sessions":
        results = asyncio.run(run_concurrent_sessions(args.endpoint, token, args.count))
    elif args.mode == "same-thread-turns":
        results = asyncio.run(run_same_thread_turns(args.endpoint, token, args.count))
    else:
        results = asyncio.run(run_sequential_cold_start(args.endpoint, token, args.count))
    wall_elapsed = round(time.monotonic() - wall_started, 3)

    latencies = [r["latency_seconds"] for r in results if r.get("error") is None]
    errors = [r for r in results if r.get("error") is not None]

    summary = {
        "mode": args.mode,
        "requested_count": args.count,
        "wall_clock_seconds": wall_elapsed,
        "success_count": len(latencies),
        "error_count": len(errors),
        "latency_p50_seconds": _percentile(latencies, 50),
        "latency_p95_seconds": _percentile(latencies, 95),
        "latency_min_seconds": min(latencies) if latencies else None,
        "latency_max_seconds": max(latencies) if latencies else None,
        "results": results,
    }

    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote raw results to {out_path}")


if __name__ == "__main__":
    main()
