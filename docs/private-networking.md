---
title: Private Cosmos and Public Foundry
description: Hybrid networking, migration boundaries, and private Cosmos verification for the threat assessment workshop.
permalink: /private-networking
---

[Version française](fr/private-networking.md)

## Network Boundary

This configuration follows the FSI sibling's hybrid pattern. It is not a fully
private deployment and does not claim compliance with policies beyond this boundary.

| Component | Access | Responsibility |
| --- | --- | --- |
| Foundry account | Public endpoint; authenticated clients | Dedicated agent injection subnet for outbound traffic |
| MCP Container Apps | Public HTTPS with synthetic fixtures only | Workload-profiles environment with VNet egress |
| Cosmos checkpoint experiment | Public access disabled; Entra authentication only | SQL private endpoint, DNS zone group and data-plane RBAC |
| Registry, web chat, monitoring | Existing access model retained | Separate security reviews; not made private by this change |

Cosmos is optional. `infra/main.bicep` does not deploy it, and `azure.yaml` does not
enable `ENABLE_COSMOS_CHECKPOINTER`. Private connectivity does not enable persistent
state, replace Foundry-managed storage, or establish durable exactly-once behavior.

## Shared Network Ownership

Deploy `infra/network.bicep` once per resource group before the environment stacks.
It owns the VNet, all five subnets, `privatelink.documents.azure.com`, and its VNet
link. Environment templates use `existing` references, avoiding competing writes
to the same VNet. An intentional later network update must preserve all subnets and
their service associations. Never redeploy a partial subnet inventory.

| Subnet | Default CIDR | Consumer |
| --- | --- | --- |
| `snet-aca-production` | `10.30.0.0/23` | Production Container Apps environment |
| `snet-aca-staging` | `10.30.2.0/23` | Staging Container Apps environment |
| `snet-agent-production` | `10.30.4.0/24` | Production Foundry account |
| `snet-agent-staging` | `10.30.5.0/24` | Staging Foundry account |
| `snet-private-endpoints` | `10.30.6.0/24` | Cosmos private endpoints |

The first four are delegated to `Microsoft.App/environments`. The private endpoint
subnet has no delegation and disables private endpoint network policies. Each
Foundry account needs its own agent subnet. An environment name ending in
`-staging` selects staging; all others select the production-named pair.

The network owner must approve non-overlapping address ranges, routing, DNS ownership
and permissions before provisioning. Change all CIDR parameters together when
necessary. If enterprise DNS is centralized, integrate its approved forwarding and
zone ownership rather than creating a competing zone. This template assumes a zone
in the same resource group and Azure-provided DNS on the VNet.

## Fresh Workshop Deployment

[Lab 02](labs/lab-02-mcp-servers.md) previews and deploys the network in a new,
disposable learner group, records `VNET_NAME`, and supplies the infrastructure
subnet to MCP. [Lab 03](labs/lab-03-deploy-agent.md) runs the read-only
`scripts/test-network-readiness.ps1` before provisioning Foundry. Keep the selected
Azure subscription consistent with the azd environment; the preflight uses the
current Azure CLI subscription.

Compile without creating deployment artifacts or contacting Azure:

```powershell
az bicep build --file infra/network.bicep --stdout | Out-Null
az bicep build --file infra/main.bicep --stdout | Out-Null
az bicep build --file infra/modules/cosmos-db.bicep --stdout | Out-Null
```

Compilation does not establish region availability, policy compatibility, capacity,
permissions or connectivity. Review `what-if` before every actual deployment.

## Existing Shared Environment Migration

Do not run the fresh learner deployment against the existing PoC group. The old
Foundry accounts have no agent injection and the old Container Apps environments
have no infrastructure subnet. Treat these as migration boundaries, not mutable
flags. The preflight stops before provisioning when an existing resource's settings
do not match. It never deletes or recreates resources.

1. Inventory current account/project IDs, agent versions, app environment IDs,
   role assignments, URLs, redirect URIs and Cosmos data. Retain rollback targets.
2. Obtain network, policy and migration approval. Prefer a separate staging group
   and new globally unique environment/account names, with a fresh dedicated subnet.
   Do not attach a second account to an already claimed agent subnet.
3. Preview and deploy the complete network foundation under one owner. Set the
   repository `VNET_NAME` variable and azd `VNET_NAME` consistently. If using new
   environment names, update the workflow's staging/production environment names
   and approved endpoint/resource variables as part of that migration change.
4. Provision and deploy staging. Re-establish the new agent identity's scoped RBAC,
   model and Toolbox access. Update web-chat backend targets and any changed sign-in
   redirect URIs. Verify normal authenticated chat before testing optional Cosmos.
5. Complete private DNS and data-plane tests below, then test the hosted runtime
   separately if checkpointing will be enabled. Retain version, identity and network
   evidence. Do not lower evaluation thresholds or reuse a previous release's pass.
6. Migrate production only after a fresh release and required approval. Keep the old
   route available for rollback until acceptance; retire old resources separately.

If migration must reuse names, require an explicitly approved downtime and recovery
plan. A failed agent provisioning attempt can leave subnet service associations;
inspect them and use a fresh approved subnet when necessary rather than attempting
blind deletion. This repository change performs no live migration.

## Optional Cosmos Deployment

Use the variables and `$NetworkOutputs` from your own Lab 02 session. These commands
create billable storage and a private endpoint. Supply the object ID of the identity
that will actually run the experiment, not the Foundry account/project identity by
assumption. A hosted agent has its own identity, created at agent deployment time.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$ExperimentPrincipalId = '<approved-experiment-identity-object-id>'
$CosmosAccount = "cosmos-$WorkshopEnv"
$PrincipalIds = ConvertTo-Json -InputObject @($ExperimentPrincipalId) -Compress
$CosmosParameters = @(
    "environmentName=$WorkshopEnv", "accountName=$CosmosAccount", "location=$Location",
    "privateEndpointSubnetId=$($NetworkOutputs.privateEndpointSubnetId.value)",
    "privateDnsZoneId=$($NetworkOutputs.cosmosPrivateDnsZoneId.value)",
    "dataPlanePrincipalIds=$PrincipalIds"
)
az deployment group what-if --subscription $SubscriptionId --resource-group $ResourceGroup `
  --template-file infra/modules/cosmos-db.bicep --parameters @CosmosParameters
```

Approve only your experiment resources and the scoped Cosmos data-plane role. Do
not grant a real learner the historical principal from the example parameter file.
That file alone is insufficient: the subnet and DNS zone IDs are now mandatory.

```powershell
az deployment group create --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name workshop-cosmos --template-file infra/modules/cosmos-db.bicep `
  --parameters @CosmosParameters --output none
$Cosmos = az cosmosdb show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name $CosmosAccount -o json | ConvertFrom-Json
if ($Cosmos.publicNetworkAccess -ne 'Disabled' -or -not $Cosmos.disableLocalAuth) {
    throw 'Cosmos access policy mismatch'
}
$Endpoint = az network private-endpoint show --subscription $SubscriptionId --resource-group $ResourceGroup `
  --name "pe-$CosmosAccount" -o json | ConvertFrom-Json
if (@($Endpoint.privateLinkServiceConnections | Where-Object {
    $_.privateLinkServiceConnectionState.status -eq 'Approved'
}).Count -ne 1) { throw 'Private endpoint is not approved' }
$env:COSMOS_ENDPOINT = $Cosmos.documentEndpoint
```

`Succeeded` and `Approved` are control-plane evidence only. The template preserves
the `threat-assessment-agent` database, `checkpoints` container and `/partition_key`.
It does not migrate or delete existing checkpoint documents.

## Verify the Private Data Path

Run the next checks on approved compute with a route to the private endpoint and
the linked private DNS view, such as a network-connected workstation or runner.
Ordinary GitHub-hosted runners and public laptops have no private Cosmos route.
Recover your own variables there; never use a historical endpoint or share tokens.

```powershell
$ErrorActionPreference = 'Stop'
$PSNativeCommandUseErrorActionPreference = $true
$PrivateAddresses = @(az network nic show --subscription $SubscriptionId `
  --ids $Endpoint.networkInterfaces[0].id --query 'ipConfigurations[].privateIPAddress' -o json | ConvertFrom-Json)
$ResolvedAddresses = @([System.Net.Dns]::GetHostAddresses(([uri]$env:COSMOS_ENDPOINT).DnsSafeHost) |
    Where-Object { $_.AddressFamily -eq 'InterNetwork' } | ForEach-Object { $_.IPAddressToString })
if (-not $ResolvedAddresses.Count -or @($ResolvedAddresses | Where-Object { $_ -notin $PrivateAddresses }).Count) {
    throw 'Cosmos DNS does not resolve exclusively to this private endpoint'
}
$env:ENABLE_COSMOS_CHECKPOINTER = 'true'
$env:COSMOS_DATABASE_NAME = 'threat-assessment-agent'
$env:COSMOS_CONTAINER_NAME = 'checkpoints'
try {
    python experiments/cosmos-checkpointer/benchmark.py
    if ($LASTEXITCODE -ne 0) { throw 'Cosmos benchmark failed' }
} finally {
    Remove-Item Env:ENABLE_COSMOS_CHECKPOINTER -ErrorAction SilentlyContinue
}
```

The benchmark writes synthetic documents and produces local evidence. Review its
results for both direct Cosmos operations and LangGraph checkpoint execution; a
successful run from a workstation does not prove the hosted agent's identity or
network path. Before enabling checkpointing on a hosted candidate, grant its actual
identity Cosmos data-plane RBAC and test persistence and thread isolation there.
Do not turn the flag on in the baseline release merely because a private endpoint
exists. The historical blocked experiment remains historical, not a new benchmark.

## CI and Evidence

The release workflow compiles all three templates, checks the shared network before
staging what-if, and repeats the preflight before staging and production provisioning.
The foundation is not redeployed by those jobs. Missing infrastructure or incompatible
existing resources block the release. OIDC, hosted evaluations, production approval
and monitoring gates remain in place. Public Foundry access lets the existing CI
runners invoke the agent; it does not let them run direct Cosmos data-plane tests.

Retain separate evidence for effective policy settings, endpoint approval, DNS/IP
resolution, authenticated Cosmos operations, hosted-runtime persistence, and release
gates. Compilation and mocked tests alone cannot satisfy these live checks.

## Teardown and References

Use [Lab 09](labs/lab-09-teardown.md) only for your tagged disposable learner group.
Its private endpoint and network are included in group teardown. Never delete a shared
DNS zone, VNet or subnet while another environment still uses it. Cosmos deletion
destroys experiment state; retain approved evidence before removing it.

* [Foundry networking deep dive](https://learn.microsoft.com/azure/foundry/agents/concepts/agents-networking-deep-dive)
* [Source deployment firewall requirements](https://learn.microsoft.com/azure/foundry/agents/how-to/deploy-hosted-agent-code#firewall-requirements-for-private-virtual-networks)
* [Cosmos private endpoints](https://learn.microsoft.com/azure/cosmos-db/how-to-configure-private-endpoints)
