"""Ad hoc smoke test for the deployed MCP tool servers (not part of the app).

Connects over streamable HTTP to each Container App and calls one tool to
prove the deployed servers are live and answering, independent of the
Foundry hosted agent.
"""

from __future__ import annotations

import asyncio

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVERS = {
    "mcp-defender-server": (
        "https://mcp-defender-server.ambitioussea-69c7df60.eastus2.azurecontainerapps.io/mcp",
        "get_device_risk",
        {"device_id": "device-001"},
    ),
    "mcp-anomaly-server": (
        "https://mcp-anomaly-server.ambitioussea-69c7df60.eastus2.azurecontainerapps.io/mcp",
        "score_anomaly",
        {"metric": "failed_logins_per_hour", "value": 12.0},
    ),
}


async def probe(label: str, url: str, tool: str, args: dict) -> None:
    print(f"\n=== {label} ({url}) ===")
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]
            print(f"tools: {names}")
            result = await session.call_tool(tool, args)
            print(f"call_tool({tool}, {args}) -> {result.content}")


async def main() -> None:
    for label, (url, tool, args) in SERVERS.items():
        await probe(label, url, tool, args)


if __name__ == "__main__":
    asyncio.run(main())
