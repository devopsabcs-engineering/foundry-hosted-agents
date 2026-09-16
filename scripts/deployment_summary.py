import os
from pathlib import Path


REPOSITORY_URL = "https://github.com/devopsabcs-engineering/foundry-hosted-agents"
WEB_URL = "https://foundry-threat-chat-staging.purpletree-432267ca.eastus2.azurecontainerapps.io"
RESOURCE_GROUP_ID = (
    "/subscriptions/64c3d212-40ed-4c6d-a825-6adfbdf25dad"
    "/resourceGroups/rg-air-canada-threat-assessment-poc"
)


def portal(resource_id):
    return f"https://portal.azure.com/#resource{resource_id}"


def render():
    links = [
        ("Try staging web chatbot", WEB_URL, "Same-tenant pilot members only"),
        ("Web app health", f"{WEB_URL}/healthz", "Public process health; not an agent-invocation test"),
        ("Web app in Azure", portal(f"{RESOURCE_GROUP_ID}/providers/Microsoft.App/containerApps/foundry-threat-chat-staging"), "Revisions, logs and metrics"),
        ("Resource group", portal(RESOURCE_GROUP_ID), "Azure access required"),
        ("Container registry", portal(f"{RESOURCE_GROUP_ID}/providers/Microsoft.ContainerRegistry/registries/acraircanadapoc001"), "Image digests and remote builds"),
    ]
    for label, name in (("Staging", "air-canada-staging-vnet"),
                        ("Production PoC", "air-canada-threat-assessment-poc")):
        project_id = f"{RESOURCE_GROUP_ID}/providers/Microsoft.CognitiveServices/accounts/aif-{name}/projects/proj-{name}"
        endpoint = f"https://aif-{name}.services.ai.azure.com/api/projects/proj-{name}"
        links.extend([
            (f"{label} Foundry project", portal(project_id), "Azure access required"),
            (f"{label} Responses API", f"{endpoint}/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1", "Authenticated POST API, not a browser chat page"),
        ])
    links.extend([
        ("Staging Defender MCP", "https://mcp-staging-defender-server.purpletree-432267ca.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Staging anomaly MCP", "https://mcp-staging-anomaly-server.purpletree-432267ca.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Production PoC Defender MCP", "https://mcp-defender-server.redbush-f3ffad44.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Production PoC anomaly MCP", "https://mcp-anomaly-server.redbush-f3ffad44.eastus2.azurecontainerapps.io/mcp", "Synthetic MCP protocol endpoint, not a chat page"),
        ("Pilot guide and diagrams", f"{REPOSITORY_URL}/wiki/Web-Chat-Pilot", "Access, deployment, recovery and Teams roadmap"),
        ("Continuous test trends", f"{REPOSITORY_URL}/wiki/Continuous-Test-Trends", "Run-linked validation evidence"),
    ])
    rows = [f"| [{label}]({url}) | {note} |" for label, url, note in links]
    return "\n".join([
        "## Deployment Links", "",
        "Existing environment links, not proof that this run deployed or validated them.",
        "The web app targets staging only; no production web frontend is deployed.", "",
        "| Destination | Access and purpose |", "| --- | --- |", *rows, "",
    ])


if __name__ == "__main__":
    summary = render()
    if destination := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(destination).open("a", encoding="utf-8") as output:
            output.write("\n" + summary)
    else:
        print(summary)