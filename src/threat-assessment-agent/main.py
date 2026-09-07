"""Entry point that serves the compiled threat-assessment graph over the
Foundry Responses protocol on port 8088.

Prefers azure.ai.agentserver.langgraph.from_langgraph; falls back to
langchain_azure_ai.agents.hosting.ResponsesHostServer when the former
package is unavailable in the current environment.
"""

from __future__ import annotations

import os

from graph import compiled_graph

PORT = 8088


def _load_host_server_run():
    """Return the bound `.run` callable for the Responses host server."""
    try:
        from azure.ai.agentserver.langgraph import LangGraphAdapter
        from runtime_evidence import EvidenceConverter

        return LangGraphAdapter(
            compiled_graph, converter=EvidenceConverter(compiled_graph)
        ).run
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
