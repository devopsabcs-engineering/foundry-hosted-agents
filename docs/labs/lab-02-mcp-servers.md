---
permalink: /labs/lab-02-mcp-servers
title: "Lab 02 - Deploy the MCP Tool Servers"
description: "Explore, run, and smoke-test the two independent MCP tool servers that back the agent's specialists."
---

## Overview

| | |
|---|---|
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 01](lab-01-architecture.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain what each MCP tool server exposes and why it's mocked data
* Run an MCP server locally and call a tool over stdio
* Confirm the deployed Container Apps are live and answering real tool calls
* Explain why MCP servers are versioned/deployed independently of the agent

## Exercises

### Exercise 2.1: Read the Server Code

Both servers live under [`mcp/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/mcp) and are built with **FastMCP**:

| Server | Tools | Purpose |
|---|---|---|
| `mcp/defender-server` | `get_device_risk`, `list_vulnerabilities` | Mocked Microsoft Defender device-risk and vulnerability data |
| `mcp/anomaly-server` | `score_anomaly`, `detect_login_anomalies` | Mocked anomaly-detection scoring |

Open `mcp/defender-server/main.py` and `mcp/anomaly-server/main.py`. Note
that each is a standalone FastMCP app with its own `Dockerfile` — nothing
here imports from `src/threat-assessment-agent/`.

### Exercise 2.2: Confirm the Deployed Servers Are Live

The two servers for this workshop are already deployed as Azure Container
Apps. Confirm their status:

```powershell
az containerapp list --resource-group <your-resource-group> `
  --query "[].{name:name, provisioningState:properties.provisioningState, runningStatus:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn}" `
  -o table
```

Expected output:

```text
Name                 ProvisioningState    RunningStatus    Fqdn
-------------------  -------------------  ---------------  -----------------------------------------------------------------------
mcp-anomaly-server   Succeeded            Running          mcp-anomaly-server.<env>.<region>.azurecontainerapps.io
mcp-defender-server  Succeeded            Running          mcp-defender-server.<env>.<region>.azurecontainerapps.io
```

### Exercise 2.3: Call a Real Tool Over the Network

The repository ships an ad hoc smoke-test script,
[`scripts/test_mcp_servers.py`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/scripts/test_mcp_servers.py),
that connects over **streamable HTTP** to each Container App and calls one
tool — independent of the Foundry hosted agent entirely.

```powershell
pip install mcp
python scripts/test_mcp_servers.py
```

Expected output (values may differ):

```text
=== mcp-defender-server (https://mcp-defender-server...azurecontainerapps.io/mcp) ===
tools: ['get_device_risk', 'list_vulnerabilities']
call_tool(get_device_risk, {'device_id': 'device-001'}) -> [TextContent(... "riskScore": "High" ...)]

=== mcp-anomaly-server (https://mcp-anomaly-server...azurecontainerapps.io/mcp) ===
tools: ['score_anomaly', 'detect_login_anomalies']
call_tool(score_anomaly, {'metric': 'failed_logins_per_hour', 'value': 12.0}) -> [TextContent(... "severity": "high" ...)]
```

> [!NOTE]
> This script proves the MCP servers work correctly **on their own** —
> useful for isolating a bug: if this script fails, the problem is in the
> Container App; if it succeeds but the agent still can't reach a tool, the
> problem is in the Foundry Toolbox connection layer, not the tool server.

### Exercise 2.4: Why Independent Deployment?

`mcp/defender-server` and `mcp/anomaly-server` are each their own `azd`
service with their own `Dockerfile`, deployed to their own Container App.
This means:

* Each tool server can be updated, scaled, or rolled back **without
  redeploying the agent**.
* Each tool server needs its own auth, networking, versioning, health
  checks, and throttling — the Foundry Toolbox only registers the
  *connection*, it does not operate the runtime.
* The same MCP server could be registered into multiple Foundry Toolboxes
  for multiple agents.

## Knowledge Check

* Which layer from Lab 01 does `scripts/test_mcp_servers.py` test — implementation/hosting, or registration/consumption?
* If the smoke test in Exercise 2.3 succeeds but the agent still reports "tool unavailable," where would you look next?

## Next Steps

Continue to [Lab 03: Provision and Deploy the Hosted Agent](lab-03-deploy-agent.md).
