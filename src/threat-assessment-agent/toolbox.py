"""Specialist tool access through the authenticated Foundry toolbox MCP endpoint."""

import asyncio
import os
from contextlib import asynccontextmanager
from urllib.parse import quote

import httpx
from azure.identity.aio import DefaultAzureCredential
from langchain.agents import create_agent
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp.client.streamable_http import streamable_http_client

from mcp import ClientSession

ALLOWED_TOOLS = {
    "defender-conn": {"defender-conn___get_device_risk", "defender-conn___list_vulnerabilities"},
    "anomaly-conn": {"anomaly-conn___detect_login_anomalies", "anomaly-conn___score_anomaly"},
}


class ToolboxAuth(httpx.Auth):
    def __init__(self, credential):
        self.credential = credential

    async def async_auth_flow(self, request):
        token = await self.credential.get_token("https://ai.azure.com/.default")
        request.headers["Authorization"] = f"Bearer {token.token}"
        yield request


def select_tools(tools, connection):
    allowed = ALLOWED_TOOLS[connection]
    selected = [tool for tool in tools if tool.name in allowed]
    if {tool.name for tool in selected} != allowed:
        raise RuntimeError(f"Required toolbox tools missing for {connection}")
    return selected


@asynccontextmanager
async def toolbox_tools(connection):
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"].rstrip("/")
    name = quote(os.environ.get("FOUNDRY_TOOLBOX_NAME", "security-tools"), safe="")
    version = quote(os.environ["FOUNDRY_TOOLBOX_VERSION"], safe="")
    url = f"{endpoint}/toolboxes/{name}/versions/{version}/mcp?api-version=v1"
    async with DefaultAzureCredential() as credential:
        async with httpx.AsyncClient(auth=ToolboxAuth(credential), timeout=120) as client:
            async with streamable_http_client(url, http_client=client) as (reader, writer, _):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    tools = await load_mcp_tools(session)
                    yield select_tools(tools, connection)


class ToolboxSpecialist:
    def __init__(self, connection, system_prompt, model_factory):
        self.connection = connection
        self.system_prompt = system_prompt
        self.model_factory = model_factory

    async def ainvoke(self, payload):
        async with toolbox_tools(self.connection) as tools:
            agent = create_agent(model=self.model_factory(), tools=tools,
                                 system_prompt=self.system_prompt)
            return await agent.ainvoke(payload)

    def invoke(self, payload):
        try:
            return asyncio.run(self.ainvoke(payload))
        except ExceptionGroup as group:
            error = group
            while isinstance(error, ExceptionGroup) and len(error.exceptions) == 1:
                error = error.exceptions[0]
            raise error from group