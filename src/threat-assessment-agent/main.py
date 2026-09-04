"""Entry point that serves the compiled threat-assessment graph over the
Foundry Responses protocol on port 8088.

Prefers azure.ai.agentserver.langgraph.from_langgraph; falls back to
langchain_azure_ai.agents.hosting.ResponsesHostServer when the former
package is unavailable in the current environment.
"""

from __future__ import annotations

import os

from graph import TOOL_RESOLUTION_UNAVAILABLE, compiled_graph

PORT = 8088


def _load_host_server_run():
    """Return the bound `.run` callable for the Responses host server."""
    try:
        from azure.ai.agentserver.langgraph import LangGraphAdapter, LanggraphRunContext
        from azure.core.exceptions import ResourceNotFoundError

        class _GracefulToolResolutionAdapter(LangGraphAdapter):
            """LangGraphAdapter that degrades gracefully instead of failing the
            whole request when Foundry Toolbox tool resolution is unavailable.

            `LangGraphAdapter.agent_run` resolves ALL registered Foundry tools
            (via `setup_lg_run_context` -> `resolve_from_registry`) BEFORE the
            graph runs. When that resolution 404s -- confirmed via `azd ai
            agent monitor` traceback to be a known platform-side gap for this
            account/region as of 2026-09-03, not a code defect -- the
            exception happens entirely outside graph.py's node functions, so
            a try/except around a node's `agent.invoke(...)` call never sees
            it. Catch it here instead, flag the request via
            `TOOL_RESOLUTION_UNAVAILABLE`, and let the graph proceed with an
            empty (unresolved) tool set so the specialist nodes fall back to
            an honestly-labeled, plain-LLM analysis instead of crashing.
            """

            async def setup_lg_run_context(self, agent_run_context):
                try:
                    return await super().setup_lg_run_context(agent_run_context)
                except ResourceNotFoundError:
                    TOOL_RESOLUTION_UNAVAILABLE.set(True)
                    from azure.ai.agentserver.langgraph.tools._context import (  # noqa: PLC0415
                        FoundryToolContext,
                    )

                    return LanggraphRunContext(agent_run_context, FoundryToolContext())

        return _GracefulToolResolutionAdapter(compiled_graph).run
    except ImportError:
        from langchain_azure_ai.agents.hosting import ResponsesHostServer

        return ResponsesHostServer(compiled_graph).run


def main() -> None:
    os.environ.setdefault("PORT", str(PORT))
    run = _load_host_server_run()
    try:
        run(port=PORT)
    except TypeError:
        run()


if __name__ == "__main__":
    main()
