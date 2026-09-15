---
permalink: /labs/lab-02-mcp-servers
title: "Lab 02 - Deploy the MCP Tool Servers"
description: "Explore, run, and smoke-test the two independent MCP tool servers that back the agent's specialists."
---

> 🇫🇷 **[Version française](../fr/labs/lab-02-mcp-servers)**

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 01](lab-01-architecture.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain what each MCP tool server exposes and why it's mocked data
* Build both server images remotely without installing Docker
* Confirm the deployed Container Apps are live and answering real tool calls
* Explain why MCP servers are versioned/deployed independently of the agent

## Exercises

### Exercise 2.1: Read the Server Code

Both servers live under [`mcp/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/mcp) and are built with **FastMCP**:

| Server | Tools | Purpose |
| --- | --- | --- |
| `mcp/defender-server` | `get_device_risk`, `list_vulnerabilities` | Mocked Microsoft Defender device-risk and vulnerability data |
| `mcp/anomaly-server` | `score_anomaly`, `detect_login_anomalies` | Mocked anomaly-detection scoring |

Open `mcp/defender-server/main.py` and `mcp/anomaly-server/main.py`. Note
that each is a standalone FastMCP app with its own `Dockerfile` — nothing
here imports from `src/threat-assessment-agent/`.

### Exercise 2.2: Build and Deploy Your Own Servers

Use PowerShell 7.3 or later at the repository root, with the virtual
environment from Lab 00 active. These resources incur charges. Use an
approved subscription and a new group, never an existing customer group.
The endpoints are public and unauthenticated for synthetic fixtures only;
do not connect real Defender data or send customer information.

Replace the subscription placeholder. Keep this terminal open for Lab 03.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$SubscriptionId = '<approved-subscription-id>'
$Suffix = [guid]::NewGuid().ToString('N').Substring(0, 8)
$WorkshopEnv = "fha-learn-$Suffix"
$ResourceGroup = "rg-$WorkshopEnv"
$Location = 'eastus2'
$Registry = "acrfhalearn$Suffix"
$McpPrefix = 'mcp-learn'
$ImageTag = 'workshop-v1'
az account set --subscription $SubscriptionId
az account show --subscription $SubscriptionId --query '{name:name,id:id,tenantId:tenantId}'
if ((az group exists --subscription $SubscriptionId --name $ResourceGroup) -eq 'true') {
    throw 'Choose a new workshop name; this group already exists.'
}
az group create --subscription $SubscriptionId --name $ResourceGroup --location $Location `
  --tags purpose=workshop-validation "workshopEnv=$WorkshopEnv" --output none
azd auth login
azd env new $WorkshopEnv --subscription $SubscriptionId --location $Location
azd env set AZURE_RESOURCE_GROUP $ResourceGroup -e $WorkshopEnv
az acr create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name $Registry --sku Basic --admin-enabled false --output none
```

Deploy the shared network once, before either environment stack. Have your network
owner approve the default `10.30.0.0/16` range; if it overlaps, adjust all subnet
prefixes in the preview and deployment together. This new learner group uses the
production-named subnet pair because `$WorkshopEnv` does not end in `-staging`;
the names do not make it a production system. Do not use these steps to migrate
existing resources. See [Private Cosmos networking](../private-networking.md).

```powershell
$VnetName = "vnet-$WorkshopEnv"
$NetworkParameters = @("vnetName=$VnetName", "location=$Location")
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/network.bicep --parameters @NetworkParameters
```

Approve only the new network, five subnets, private DNS zone and VNet link in your
learner group. The shared network template is their sole owner; do not deploy it
independently for staging and production or remove one environment's subnets.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-network --template-file infra/network.bicep --parameters @NetworkParameters --output none
$NetworkOutputs = az deployment group show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-network --query properties.outputs -o json | ConvertFrom-Json
$AcaSubnetId = $NetworkOutputs.acaProductionSubnetId.value
azd env set VNET_NAME $VnetName -e $WorkshopEnv
```

Build the actual MCP images. The Bicep template's default quickstart images
are placeholders, not working MCP servers. Remote builds require permission
to run ACR Tasks; Docker Desktop is not required.

```powershell
az acr build --subscription $SubscriptionId --registry $Registry `
  --image "defender:$ImageTag" ./mcp/defender-server
az acr build --subscription $SubscriptionId --registry $Registry `
  --image "anomaly:$ImageTag" ./mcp/anomaly-server
$LoginServer = az acr show --subscription $SubscriptionId --name $Registry --query loginServer -o tsv
$DefenderImage = "${LoginServer}/defender:$ImageTag"
$AnomalyImage = "${LoginServer}/anomaly:$ImageTag"
azd env set MCP_ACR_NAME $Registry -e $WorkshopEnv
azd env set MCP_NAME_PREFIX $McpPrefix -e $WorkshopEnv
azd env set DEFENDER_MCP_IMAGE $DefenderImage -e $WorkshopEnv
azd env set ANOMALY_MCP_IMAGE $AnomalyImage -e $WorkshopEnv
$McpParameters = @("namePrefix=$McpPrefix", "acrName=$Registry", "defenderImage=$DefenderImage", "anomalyImage=$AnomalyImage")
$McpParameters += "infrastructureSubnetId=$AcaSubnetId"
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/modules/mcp-container-apps.bicep --parameters @McpParameters
```

Confirm the preview targets only your new group. Deploy, then discover the
endpoints from deployment outputs rather than copying an instructor's URL.
The `mcp-learn` prefix enables a dedicated image-pull identity with an
`AcrPull` assignment scoped to your registry.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-mcp --template-file infra/modules/mcp-container-apps.bicep `
  --parameters @McpParameters --output none
$McpOutputs = az deployment group show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-mcp --query properties.outputs -o json | ConvertFrom-Json
$env:DEFENDER_MCP_URL = "https://$($McpOutputs.defenderContainerAppFqdn.value)/mcp"
$env:ANOMALY_MCP_URL = "https://$($McpOutputs.anomalyContainerAppFqdn.value)/mcp"
az containerapp list --subscription $SubscriptionId --resource-group $ResourceGroup `
  --query '[].{name:name,state:properties.provisioningState,fqdn:properties.configuration.ingress.fqdn}' -o table
```

Both apps must show `Succeeded`. A running container is not proof that MCP
works; perform the tool check below. If deployment fails, inspect its error
before retrying. Do not substitute an existing customer's registry or URL.

### Exercise 2.3: Call a Real Tool Over the Network

The repository ships an ad hoc smoke-test script,
[`scripts/test_mcp_servers.py`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/scripts/test_mcp_servers.py),
that connects over **streamable HTTP** and calls all four tools independently
of Foundry. It requires your endpoints and fails on missing tools, empty
responses, protocol errors, application errors, or a 90-second call timeout.

```powershell
python scripts/test_mcp_servers.py --defender-url $env:DEFENDER_MCP_URL --anomaly-url $env:ANOMALY_MCP_URL
```

Expect four successful calls and exit code zero. The vulnerability check
uses `device-001`, which has known synthetic vulnerabilities. Other
fixtures intentionally represent missing telemetry and are not health checks.

> [!NOTE]
> This checks the network path from your machine, not the agent's identity
> or network path. On failure, check endpoint selection, local connectivity,
> container logs and fixtures. If it passes but the agent fails, investigate
> Toolbox registration, identity permissions, model access and agent logs.

### Exercise 2.4: Why Independent Deployment?

`mcp/defender-server` and `mcp/anomaly-server` have their own `Dockerfile`
and Container App. Bicep deploys them; they are not separate services in
the root `azure.yaml`.
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

If you stop here or deployment fails, complete [Lab 09: Teardown](lab-09-teardown.md).
