"""One-off diagnostic: prints raw SSE lines from a direct aiohttp POST to the
Responses endpoint. Used to discover that a bare POST (no azd-internal
session negotiation) returns "conversation": null -- explains why
load_test.py's same-thread-turns mode could not self-derive a reusable
conversation id; see README.md and results/same-thread-turns-cli-2concurrent.json
for the corrected same-thread experiment (via azd CLI --session-id instead).
"""

import asyncio, json, subprocess, sys
import aiohttp

def get_token():
    p = subprocess.run(["az","account","get-access-token","--resource","https://ai.azure.com","--query","accessToken","-o","tsv"], capture_output=True, text=True, check=True, shell=True)
    return p.stdout.strip()

ENDPOINT = "https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/proj-air-canada-threat-assessment-poc/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1"

async def main():
    token = get_token()
    body = {"input":[{"role":"user","content":[{"type":"input_text","text":"debug ping"}]}], "stream": True}
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {token}"}) as session:
        async with session.post(ENDPOINT, json=body) as resp:
            n = 0
            async for line in resp.content:
                n += 1
                if n <= 3 or n >= 8:
                    print(repr(line[:300]))
asyncio.run(main())
