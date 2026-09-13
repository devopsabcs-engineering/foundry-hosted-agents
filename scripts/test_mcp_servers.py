"""Ad hoc smoke test for the deployed MCP tool servers (not part of the app).

Connects over streamable HTTP to each Container App and calls all four tools to
prove the deployed servers are live and answering, independent of the
Foundry hosted agent.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from urllib.parse import urlparse

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--defender-url", default=os.getenv("DEFENDER_MCP_URL"))
    parser.add_argument("--anomaly-url", default=os.getenv("ANOMALY_MCP_URL"))
    args = parser.parse_args(argv)
    for label, url in (("defender", args.defender_url), ("anomaly", args.anomaly_url)):
        if not url:
            parser.error(f"Set --{label}-url or {label.upper()}_MCP_URL for your environment")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            parser.error(f"{label} URL must be an HTTPS endpoint without embedded credentials")
    return args


async def probe(label: str, url: str, tool: str, args: dict) -> None:
    print(f"\n=== {label} ({url}) ===")
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [tool_info.name for tool_info in tools.tools]
            print(f"tools: {names}")
            if tool not in names:
                raise RuntimeError(f"{label}: required tool {tool} is missing")
            result = await session.call_tool(tool, args)
            if result.isError or not result.content:
                raise RuntimeError(f"{label}: {tool} failed or returned no content")
            for content in result.content:
                if content.type == "text":
                    payload = json.loads(content.text)
                    if isinstance(payload, dict) and payload.get("error"):
                        raise RuntimeError(f"{label}: {tool}: {payload['error']}")
            print(f"call_tool({tool}, {args}) -> {result.content}")


async def main(args: argparse.Namespace) -> None:
    calls = [
        ("defender", args.defender_url, "get_device_risk", {"device_id": "CREW-PORTAL-01"}),
        ("defender", args.defender_url, "list_vulnerabilities", {"device_id": "device-001"}),
        ("anomaly", args.anomaly_url, "score_anomaly", {"metric": "data_egress_mb_per_hour", "value": 900.0}),
        ("anomaly", args.anomaly_url, "detect_login_anomalies", {"user_id": "crew-admin"}),
    ]
    for label, url, tool, tool_args in calls:
        await asyncio.wait_for(probe(label, url, tool, tool_args), timeout=90)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
