#requires -Version 7.3
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [switch]$Delete,
    [string[]]$ConfirmResourceGroups,
    [switch]$KeepPipelineIdentity,
    [string]$AzdEnvironment = 'air-canada-threat-assessment-poc',
    [string]$EvidenceDirectory = 'teardown-evidence',
    [int]$PollSeconds = 60
)

$ErrorActionPreference = 'Stop'
$SubscriptionId = '64c3d212-40ed-4c6d-a825-6adfbdf25dad'
$WorkloadGroup = 'rg-air-canada-threat-assessment-poc'
$IdentityGroup = 'rg-air-canada-threat-assessment-msi'
$IdentityName = 'msi-air-canada-threat-assessment'
$groups = @($WorkloadGroup) + @(if (-not $KeepPipelineIdentity) { $IdentityGroup })
$inCi = $env:GITHUB_ACTIONS -eq 'true'

function Invoke-Az([string[]]$Arguments) {
    $target = if ($Arguments -contains '--ids') { @() } else { @('--subscription', $SubscriptionId) }
    $raw = & az @Arguments @target --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure command failed: az $($Arguments[0..2] -join ' ')" }
    if ($raw) { ($raw -join "`n") | ConvertFrom-Json }
}
function Test-Group([string]$Name) {
    $exists = Invoke-Az @('group', 'exists', '--name', $Name)
    if ($exists -isnot [bool]) { throw 'Azure did not return a valid resource-group existence result.' }
    $exists
}
function Get-CapabilityHost([string]$AccountId) {
    $raw = & az rest --method get --url "https://management.azure.com$AccountId/capabilityHosts?api-version=2025-06-01" --query 'value[].{id:id, state:properties.provisioningState}' --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Could not list capability hosts for $AccountId." }
    if ($raw) { ($raw -join "`n") | ConvertFrom-Json }
}

$inventory = [ordered]@{
    subscriptionId = $SubscriptionId
    capturedAt = [DateTime]::UtcNow.ToString('o')
    groups = [ordered]@{}
    identityRoleAssignments = @()
}
foreach ($group in $groups) {
    if (-not (Test-Group $group)) { Write-Output "Already absent: $group"; continue }
    $resources = @(Invoke-Az @('resource', 'list', '--resource-group', $group))
    $inventory.groups[$group] = @($resources | ForEach-Object { [ordered]@{ name = $_.name; type = $_.type; id = $_.id } })
    Write-Output "$group ($($resources.Count) resources)"
    $resources | Group-Object type | Sort-Object Name | ForEach-Object { Write-Output ('  {0,3} {1}' -f $_.Count, $_.Name) }
}
if ($inventory.groups.Contains($IdentityGroup)) {
    $principalId = (Invoke-Az @('identity', 'show', '--name', $IdentityName, '--resource-group', $IdentityGroup)).principalId
    $inventory.identityRoleAssignments = @(Invoke-Az @('role', 'assignment', 'list', '--assignee', $principalId, '--all') |
        ForEach-Object { [ordered]@{ id = $_.id; role = $_.roleDefinitionName; scope = $_.scope } })
}
New-Item -ItemType Directory -Path $EvidenceDirectory -Force | Out-Null
$inventory | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $EvidenceDirectory 'inventory.json')

if (-not $Delete) { Write-Output 'Preview only. Nothing was deleted.'; return }
$expected = $groups -join ','
$confirmed = @($ConfirmResourceGroups -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object -Unique)
if (($confirmed -join ',') -cne (($groups | Sort-Object) -join ',')) { throw "Deletion requires -ConfirmResourceGroups '$expected'. Nothing was deleted." }
if (-not $PSCmdlet.ShouldProcess("$SubscriptionId/$expected", 'Permanently delete these resource groups')) { return }

if ($inventory.groups.Contains($WorkloadGroup)) {
    $scope = @('--resource-group', $WorkloadGroup)
    # Foundry rejects account deletion while child projects exist, and capability hosts keep agent subnets linked.
    $accounts = @(Invoke-Az (@('cognitiveservices', 'account', 'list') + $scope))
    foreach ($account in $accounts) {
        foreach ($project in @(Invoke-Az (@('cognitiveservices', 'account', 'project', 'list', '--name', $account.name) + $scope))) {
            $projectName = ($project.name -split '/')[-1]
            Write-Output "Deleting Foundry project $($account.name)/$projectName"
            Invoke-Az (@('cognitiveservices', 'account', 'project', 'delete', '--name', $account.name, '--project-name', $projectName) + $scope) | Out-Null
        }
    }
    # Capability host deletion takes tens of minutes each, so start them all and wait together.
    foreach ($capabilityHost in @($accounts | ForEach-Object { Get-CapabilityHost $_.id })) {
        if ($capabilityHost.state -eq 'Deleting') { Write-Output "Already deleting: $($capabilityHost.id)"; continue }
        Write-Output "Deleting capability host $($capabilityHost.id)"
        Invoke-Az @('resource', 'delete', '--ids', $capabilityHost.id, '--api-version', '2025-06-01', '--no-wait') | Out-Null
    }
    $deadline = (Get-Date).AddMinutes(120)
    while (($remaining = @($accounts | ForEach-Object { Get-CapabilityHost $_.id })).Count) {
        if ((Get-Date) -gt $deadline) { throw "Capability hosts still present after 120 minutes: $($remaining.id -join ', ')" }
        Write-Output "$(Get-Date -Format 'HH:mm:ss') waiting on $($remaining.Count) capability host(s): $(($remaining | ForEach-Object { "$(($_.id -split '/')[-1])=$($_.state)" }) -join ', ')"
        Start-Sleep -Seconds $PollSeconds
    }
    & azd down --force --purge --no-prompt --environment $AzdEnvironment --cwd (Split-Path $PSScriptRoot -Parent)
    if ($LASTEXITCODE -ne 0 -or (Test-Group $WorkloadGroup)) {
        Write-Warning "azd down did not remove $WorkloadGroup; falling back to az group delete."
        Invoke-Az @('group', 'delete', '--name', $WorkloadGroup, '--yes') | Out-Null
    }
    if (Test-Group $WorkloadGroup) { throw "Teardown incomplete: $WorkloadGroup still exists." }
    foreach ($account in @(Invoke-Az @('cognitiveservices', 'account', 'list-deleted'))) {
        if ($account.id -like "*/resourceGroups/$WorkloadGroup/*") {
            Invoke-Az @('cognitiveservices', 'account', 'purge', '--name', $account.name, '--location', $account.location, '--resource-group', $WorkloadGroup) | Out-Null
            Write-Output "Purged soft-deleted Foundry account $($account.name)"
        }
    }
    Write-Output "Verified absent: $WorkloadGroup"
}

if ($inventory.groups.Contains($IdentityGroup)) {
    if ($inCi) {
        # This run authenticates as the identity being deleted, so it cannot verify completion.
        Invoke-Az @('group', 'delete', '--name', $IdentityGroup, '--yes', '--no-wait') | Out-Null
        Write-Output "Deletion requested: $IdentityGroup. Verify locally with: az group exists --name $IdentityGroup"
        Write-Output 'Its subscription role assignments are orphaned; the inventory artifact lists them for cleanup.'
        return
    }
    Invoke-Az @('group', 'delete', '--name', $IdentityGroup, '--yes') | Out-Null
    if (Test-Group $IdentityGroup) { throw "Teardown incomplete: $IdentityGroup still exists." }
    foreach ($assignment in @($inventory.identityRoleAssignments | Where-Object { $_.scope -notlike "*/resourceGroups/$WorkloadGroup*" })) {
        Invoke-Az @('role', 'assignment', 'delete', '--ids', $assignment.id) | Out-Null
        Write-Output "Removed orphaned $($assignment.role) assignment at $($assignment.scope)"
    }
    Write-Output "Verified absent: $IdentityGroup"
}
