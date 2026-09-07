---
permalink: /labs/lab-03-deploy-agent
title: "Lab 03 - Provision and Deploy the Hosted Agent"
description: "Use azd to provision a Foundry project, model deployment, Toolbox connections, and the hosted agent itself."
---

> 🇫🇷 **[Version française](../fr/labs/lab-03-deploy-agent)**

## Overview

| | |
|---|---|
| **Duration** | 35 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 02](lab-02-mcp-servers.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Read an `azure.yaml` manifest that mixes infra services and a hosted agent service
* Provision a Foundry project, model deployment, and Toolbox with `azd provision`
* Deploy the hosted agent's code with `azd deploy`
* Locate the deployed agent, its model, and its identity in the Foundry portal

## Exercises

### Exercise 3.1: Read the Agent Service Definition

Open `azure.yaml` at the repository root. The `threat-assessment-agent`
service is the interesting one:

```yaml
threat-assessment-agent:
    project: ./src/threat-assessment-agent
    host: azure.ai.agent
    language: python
    uses:
        - ai-project
        - security-tools
    codeConfiguration:
        dependencyResolution: remote_build
        entryPoint: main.py
        runtime: python_3_13
    container:
        resources:
            cpu: "0.5"
            memory: 1Gi
    kind: hosted
    protocols:
        - protocol: responses
          version: 2.0.0
```

Key fields:

| Field | Meaning |
|---|---|
| `host: azure.ai.agent` | This is a Foundry-hosted agent service, not a container app or function |
| `kind: hosted` | Foundry operates the session compute; you own only the graph code |
| `uses: [ai-project, security-tools]` | Wires in the model deployment and the MCP Toolbox from Lab 01 |
| `dependencyResolution: remote_build` | Foundry builds your Python dependencies server-side from `requirements.txt` |
| `protocol: responses` | The agent speaks the OpenAI-compatible Responses protocol (supports streaming) |

### Exercise 3.2: Provision

```powershell
azd auth login
azd env new <your-workshop-env-name>
azd provision
```

This creates (or confirms) the Foundry account, project, `gpt-4o-mini`
model deployment, and the two Toolbox connections from Lab 01
(`defender-conn`, `anomaly-conn`) — everything **except** the agent code
itself.

### Exercise 3.3: Deploy the Agent

```powershell
azd deploy
```

This step uploads `src/threat-assessment-agent/` and builds it remotely
per `dependencyResolution: remote_build`, then publishes a new hosted-agent
version.

> **Troubleshooting: `no Foundry project endpoint resolved`**
>
> If `azd deploy` fails on the `security-tools` or `threat-assessment-agent`
> service with this error, your environment was provisioned before the
> Foundry project endpoint was added as a bicep output. Re-run
> `azd provision` to pick it up, or set it manually for this environment:
>
> ```powershell
> azd env set FOUNDRY_PROJECT_ENDPOINT "https://<accountName>.services.ai.azure.com/api/projects/<projectName>"
> ```
>
> `<accountName>` and `<projectName>` are the `accountName`/`projectName`
> values already in your `.azure/<env>/.env` file.

> **Troubleshooting: `failed to resolve connection "defender-conn"` (or `anomaly-conn`)**
>
> This means the connection doesn't exist yet on the Foundry project. The
> `defender-conn`/`anomaly-conn` Toolbox connections are created by
> `azd provision` from bicep (not by `azd deploy`), so if your environment
> was provisioned before these connections were added as bicep resources,
> they were never created. Re-run `azd provision` to create them, then
> retry `azd deploy`.

> **Troubleshooting: `AZURE_AI_PROJECT_ID is not set`**
>
> The `threat-assessment-agent` service needs the Foundry project's ARM
> resource ID (distinct from `FOUNDRY_PROJECT_ENDPOINT`). If your
> environment was provisioned before this was added as a bicep output,
> re-run `azd provision` to pick it up, or set it manually:
>
> ```powershell
> azd env set AZURE_AI_PROJECT_ID "/subscriptions/<subscriptionId>/resourceGroups/<resourceGroup>/providers/Microsoft.CognitiveServices/accounts/<accountName>/projects/<projectName>"
> ```

### Exercise 3.4: Find the Agent in the Portal

![Foundry project overview in the Azure Portal](../assets/images/03-azure-foundry-project-overview.png)

![Foundry portal project overview](../assets/images/04-foundry-portal-project-overview.png)

![Foundry portal agents list showing the deployed threat-assessment-agent](../assets/images/05-foundry-portal-agents-list.png)

![Foundry portal agent detail page](../assets/images/06-foundry-portal-agent-detail.png)

Navigate to your Foundry project in the portal and confirm you can see:

1. The `threat-assessment-agent` in the agents list, with a version number.
2. The agent's detail page, showing its model (`gpt-4o-mini`) and Toolbox
   (`security-tools`).
3. **A dedicated Entra ID identity** was auto-created for this agent at
   deploy time — you did not manually wire a managed identity. Find it
   under the agent's **Identity** tab.

> [!TIP]
> This auto-created "Instance Identity" is what actually calls Azure
> OpenAI and the MCP Toolbox at runtime. It's the same identity you'll
> investigate with `az role assignment list` in
> [Lab 07](lab-07-troubleshooting-rbac.md).

## Knowledge Check

* What does `remote_build` mean, and why might that matter for a large dependency like `langgraph`?
* Where does the agent's runtime identity come from — did you create it?
* Name the two Toolbox connections wired into this agent, and which specialist node uses which.

## Next Steps

Continue to [Lab 04: Invoke the Agent and Read Traces](lab-04-invoke-agent.md).
