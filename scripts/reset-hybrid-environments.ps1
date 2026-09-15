#requires -Version 7.3
[CmdletBinding()]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [string]$EvidenceDirectory = 'migration-evidence',
    [switch]$Delete,
    [string]$ConfirmResourceGroup
)

$ErrorActionPreference = 'Stop'
if ("$SubscriptionId" -ne '64c3d212-40ed-4c6d-a825-6adfbdf25dad' -or
    $ResourceGroup -cne 'rg-air-canada-threat-assessment-poc') {
    throw 'This migration is restricted to the approved Air Canada subscription and resource group.'
}
if ($Delete -and $ConfirmResourceGroup -cne $ResourceGroup) {
    throw 'Deletion requires the exact resource group confirmation.'
}
$scope = @('--subscription', "$SubscriptionId", '--resource-group', $ResourceGroup)
function Read-Azure([string[]]$Arguments) {
    $raw = & az @Arguments --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure read failed: $($Arguments[0])" }
    $result = ($raw -join "`n") | ConvertFrom-Json -AsHashtable -NoEnumerate
    if ($null -eq $result) { throw 'Missing Azure inventory.' }
    return ,$result
}
function Write-Azure([string[]]$Arguments) {
    & az @Arguments --output none --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure operation failed: $($Arguments[0..2] -join ' ')" }
}
$environmentNames = @('mcp-mcp-env', 'mcp-staging-mcp-env')
$accountNames = @('aif-air-canada-threat-assessment-poc', 'aif-air-canada-threat-assessment-staging')
$appEnvironments = @{
    'mcp-defender-server' = 'mcp-mcp-env'
    'mcp-anomaly-server' = 'mcp-mcp-env'
    'mcp-staging-defender-server' = 'mcp-staging-mcp-env'
    'mcp-staging-anomaly-server' = 'mcp-staging-mcp-env'
    'foundry-threat-chat-staging' = 'mcp-staging-mcp-env'
}
$apps = Read-Azure (@('containerapp', 'list') + $scope)
$environments = Read-Azure (@('containerapp', 'env', 'list') + $scope)
$accounts = Read-Azure (@('cognitiveservices', 'account', 'list') + $scope)
foreach ($inventory in @($apps, $environments, $accounts)) {
    if ($inventory -isnot [array]) { throw 'Invalid resource inventory.' }
}
$targets = @($apps | Where-Object {
    $parentName = ($_.properties.managedEnvironmentId -split '/')[-1]
    if ($parentName -in $environmentNames -and -not $appEnvironments.ContainsKey($_.name)) {
        throw "Unexpected dependent app: $($_.name). Nothing was deleted."
    }
    if ($appEnvironments.ContainsKey($_.name)) {
        if ($parentName -ne $appEnvironments[$_.name]) { throw 'App environment mismatch.' }
        $true
    }
})
$targetAccounts = @($accounts | Where-Object { $_.name -in $accountNames })
$targetProjects = @()
foreach ($account in $targetAccounts) {
    if ($account.location -ne 'eastus2' -or $account.kind -ne 'AIServices') { throw 'Foundry account mismatch.' }
    if ($account.properties.networkInjections) { throw 'Refusing to reset an already network-injected account.' }
    $projects = Read-Azure (@('cognitiveservices', 'account', 'project', 'list', '--name', $account.name) + $scope)
    if ($projects -isnot [array]) { throw 'Invalid project inventory.' }
    $expectedProject = 'proj-' + $account.name.Substring(4)
    foreach ($project in $projects) {
        $projectName = ($project.name -split '/')[-1]
        if ($projectName -cne $expectedProject) { throw "Unexpected Foundry project: $($project.name). Nothing was deleted." }
        $targetProjects += @{ account = $account.name; name = $projectName; id = $project.id }
    }
}
$targetEnvironments = @($environments | Where-Object { $_.name -in $environmentNames })
foreach ($environment in $targetEnvironments) {
    if ($environment.properties.vnetConfiguration.infrastructureSubnetId) {
        throw 'Refusing to reset an already VNet-integrated environment.'
    }
}
$evidence = @{
    subscriptionId = "$SubscriptionId"
    resourceGroup = $ResourceGroup
    capturedAt = [DateTime]::UtcNow.ToString('o')
    apps = @($targets | ForEach-Object { @{
        name = $_.name; id = $_.id; identity = $_.identity
        environment = $_.properties.managedEnvironmentId
        fqdn = $_.properties.configuration.ingress.fqdn
        images = @($_.properties.template.containers | ForEach-Object { $_.image })
    } })
    accounts = @($targetAccounts | ForEach-Object { @{ name = $_.name; id = $_.id; location = $_.location } })
    projects = $targetProjects
    environments = @($targetEnvironments | ForEach-Object { @{ name = $_.name; id = $_.id } })
}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$evidence | ConvertTo-Json -Depth 12 | Set-Content (Join-Path $EvidenceDirectory 'inventory.json')
if (-not $Delete) { Write-Host 'Preview only. No resources deleted.'; return }
foreach ($app in $targets) {
    Write-Azure (@('containerapp', 'delete', '--name', $app.name, '--yes') + $scope)
}
foreach ($environment in $targetEnvironments) {
    Write-Azure (@('containerapp', 'env', 'delete', '--name', $environment.name, '--yes') + $scope)
}
foreach ($account in $targetAccounts) {
    foreach ($project in @($targetProjects | Where-Object { $_.account -eq $account.name })) {
        Write-Azure (@('cognitiveservices', 'account', 'project', 'delete', '--name', $account.name, '--project-name', $project.name) + $scope)
    }
    Write-Azure (@('cognitiveservices', 'account', 'delete', '--name', $account.name) + $scope)
}
$deletedAccounts = Read-Azure @('cognitiveservices', 'account', 'list-deleted', '--subscription', "$SubscriptionId")
if ($deletedAccounts -isnot [array]) { throw 'Invalid deleted-account inventory.' }
foreach ($account in $deletedAccounts) {
    $deletedGroup = ($account.id -split '/resourceGroups/')[1] -split '/'
    if ($account.name -in $accountNames -and $deletedGroup[0] -eq $ResourceGroup -and $account.location -eq 'eastus2') {
        Write-Azure (@('cognitiveservices', 'account', 'purge', '--name', $account.name, '--location', 'eastus2') + $scope)
    }
}
$remainingApps = Read-Azure (@('containerapp', 'list') + $scope)
$remainingEnvironments = Read-Azure (@('containerapp', 'env', 'list') + $scope)
$remainingAccounts = Read-Azure (@('cognitiveservices', 'account', 'list') + $scope)
if (@($remainingApps | Where-Object { $appEnvironments.ContainsKey($_.name) }).Count -or
    @($remainingEnvironments | Where-Object { $_.name -in $environmentNames }).Count -or
    @($remainingAccounts | Where-Object { $_.name -in $accountNames }).Count) {
    throw 'Teardown incomplete. Do not claim successful migration.'
}
Write-Host 'Verified target resources absent. Cosmos, registry, monitoring and shared identities preserved.'