"""Server-authored execution evidence carried in Responses metadata."""

import base64
import json
import zlib

from azure.ai.agentserver.langgraph.models.response_api_default_converter import ResponseAPIDefaultConverter

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