[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$ResourceGroup,
    [Parameter(Mandatory)][string]$EnvironmentName,
    [Parameter(Mandatory)][string]$Location,
    [string]$VnetName = 'vnet-air-canada-threat-assessment',
    [string]$AccountName = '',
    [string]$AgentSubnetName = '',
    [string]$McpNamePrefix = ''
)

$ErrorActionPreference = 'Stop'

function Get-AzureJson([string[]]$Arguments) {
    $raw = & az @Arguments --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure read failed: $($Arguments -join ' ')" }
    if ([string]::IsNullOrWhiteSpace(($raw -join "`n"))) { throw 'Azure returned empty evidence.' }
    $value = ($raw -join "`n") | ConvertFrom-Json -AsHashtable -NoEnumerate
    if ($null -eq $value) { throw 'Azure returned null evidence.' }
    return ,$value
}

$stage = if ($EnvironmentName.EndsWith('-staging')) { 'staging' } else { 'production' }
if (-not $AccountName) { $AccountName = "aif-$EnvironmentName" }
if (-not $AgentSubnetName) { $AgentSubnetName = "snet-agent-$stage" }
if (-not $McpNamePrefix) { $McpNamePrefix = if ($stage -eq 'staging') { 'mcp-staging' } else { 'mcp' } }
$network = Get-AzureJson @('network', 'vnet', 'show', '-g', $ResourceGroup, '-n', $VnetName)
if (-not $network.id -or $network.location -ne $Location -or $network.provisioningState -ne 'Succeeded') {
    throw 'Shared network is missing, not ready, or in the wrong region. Review infra/network.bicep.'
}
foreach ($name in @("snet-aca-$stage", $AgentSubnetName, 'snet-private-endpoints')) {
    $subnets = @($network.subnets | Where-Object { $_.name -eq $name })
    if ($subnets.Count -ne 1) { throw "Missing subnet: $name" }
    $subnet = $subnets[0]
    if ($name -eq 'snet-private-endpoints') {
        if ($subnet.privateEndpointNetworkPolicies -ne 'Disabled') { throw 'Private endpoint subnet policies mismatch.' }
    } elseif (@($subnet.delegations | Where-Object { $_.serviceName -eq 'Microsoft.App/environments' }).Count -ne 1) {
        throw "Incorrect delegation: $name"
    }
}
$links = Get-AzureJson @('network', 'private-dns', 'link', 'vnet', 'list', '-g', $ResourceGroup,
    '--zone-name', 'privatelink.documents.azure.com')
if (@($links | Where-Object {
    $_.virtualNetwork.id -eq $network.id -and $_.provisioningState -eq 'Succeeded' -and
    $_.virtualNetworkLinkState -eq 'Completed'
}).Count -ne 1) { throw 'Cosmos private DNS zone is not linked and ready for this VNet.' }

$scope = ($network.id -split '/providers/')[0]
$accounts = @{ value = Get-AzureJson @('cognitiveservices', 'account', 'list', '-g', $ResourceGroup) }
$environments = Get-AzureJson @('rest', '--method', 'get', '--url',
    "$scope/providers/Microsoft.App/managedEnvironments?api-version=2024-03-01")
foreach ($collection in @($accounts, $environments)) {
    if ($collection.value -isnot [array] -or $collection.nextLink) {
        throw 'Incomplete Azure resource inventory; resolve pagination or invalid response before provisioning.'
    }
}
$account = @($accounts.value | Where-Object { $_.name -eq $AccountName })
if ($account.Count -gt 0) {
    $injections = @($account[0].properties.networkInjections | Where-Object { $_.scenario -eq 'agent' })
    if ($injections.Count -ne 1 -or
        $injections[0].subnetArmId -ne "$($network.id)/subnets/$AgentSubnetName" -or
        $injections[0].useMicrosoftManagedNetwork -ne $false -or
        $account[0].properties.publicNetworkAccess -ne 'Enabled') {
        throw 'Foundry network mismatch. Stop for an approved migration; do not recreate the account automatically.'
    }
}
$environment = @($environments.value | Where-Object { $_.name -eq "$McpNamePrefix-mcp-env" })
if ($environment.Count -gt 0) {
    $config = $environment[0].properties.vnetConfiguration
    $profiles = @($environment[0].properties.workloadProfiles | Where-Object { $_.workloadProfileType -eq 'Consumption' })
    if ($config.infrastructureSubnetId -ne "$($network.id)/subnets/snet-aca-$stage" -or
        $config.internal -ne $false -or $profiles.Count -eq 0) {
        throw 'Container Apps network mismatch. Stop for an approved migration; do not recreate the environment automatically.'
    }
}
Write-Host "Network preflight passed for $EnvironmentName. This is control-plane evidence, not a Cosmos data-plane test."
