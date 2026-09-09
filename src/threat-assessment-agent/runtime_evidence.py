"""Server-authored execution evidence carried in Responses metadata."""

import base64
import json
import os
import zlib
from urllib.parse import quote

from azure.ai.agentserver.langgraph.models.response_api_default_converter import ResponseAPIDefaultConverter
from azure.ai.agentserver.langgraph.models.response_api_request_converter import convert_item_resource_to_message
from azure.ai.agentserver.core.logger import get_project_endpoint
from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncOpenAI

STATE_FIELDS = (
    "evidence_report", "risk_report", "final_report", "evidence_complete",
    "risk_complete", "report_complete", "evidence_tool_unavailable",
    "risk_tool_unavailable", "safety_blocked", "tool_calls",
)


def evidence_metadata(state, metadata=None):
    metadata = {key: value for key, value in (metadata or {}).items()
                if not key.startswith("runtime_evidence")}
    payload = json.dumps({field: state[field] for field in STATE_FIELDS if field in state},
                         separators=(",", ":")).encode("utf-8")
    encoded = base64.b64encode(zlib.compress(payload)).decode("ascii")
    chunks = [encoded[index:index + 512] for index in range(0, len(encoded), 512)]
    available = 16 - len(metadata) - 1
    if len(chunks) > available or len(payload) > 131072:
        return {"runtime_evidence": "unavailable: metadata capacity exceeded"}
    metadata["runtime_evidence"] = f"v1:{len(chunks)}"
    metadata.update({f"runtime_evidence_{index}": chunk for index, chunk in enumerate(chunks)})
    return metadata


class EvidenceConverter(ResponseAPIDefaultConverter):
    async def _fetch_historical_items(self, conversation_id):
        endpoint = get_project_endpoint()
        if not endpoint:
            raise RuntimeError("Conversation history requires a configured project endpoint")
        agent_name = os.environ.get("AGENT_NAME")
        if not agent_name:
            raise RuntimeError("Conversation history requires a configured agent name")
        async with DefaultAzureCredential() as credential:
            token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
            async with AsyncOpenAI(
                base_url=f"{endpoint.rstrip('/')}/agents/{quote(agent_name, safe='')}/endpoint/protocols/openai",
                api_key=token_provider,
                default_query={"api-version": "v1"},
            ) as client:
                items = [item async for item in client.conversations.items.list(conversation_id, order="asc")]
        messages = []
        for item in items:
            item_data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
            message = convert_item_resource_to_message(item_data)
            if message is not None:
                messages.append(message)
        return self._filter_incomplete_tool_calls(messages)

    def get_stream_mode(self, context):
        return ["messages", "values"] if context.agent_run.stream else "updates"

    async def convert_response_non_stream(self, output, context):
        response = await super().convert_response_non_stream(output, context)
        response.metadata = evidence_metadata(output, response.metadata)
        return response

    async def convert_response_stream(self, output, context):
        state = {}

        async def messages():
            nonlocal state
            async for mode, value in output:
                if mode == "values":
                    state = value
                elif mode == "messages":
                    yield value

        async for event in super().convert_response_stream(messages(), context):
            if event.type == "response.completed":
                event.response.metadata = evidence_metadata(state, event.response.metadata)
            yield event