#requires -Version 7.3
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [switch]$Delete,
    [string[]]$ConfirmResourceGroups,
    [switch]$KeepPipelineIdentity,
    [string]$AzdEnvironment = 'air-canada-threat-assessment-poc',
    [string]$EvidenceDirectory = 'teardown-evidence'
)

$ErrorActionPreference = 'Stop'
$SubscriptionId = '64c3d212-40ed-4c6d-a825-6adfbdf25dad'
$WorkloadGroup = 'rg-air-canada-threat-assessment-poc'
$IdentityGroup = 'rg-air-canada-threat-assessment-msi'
$IdentityName = 'msi-air-canada-threat-assessment'
$groups = @($WorkloadGroup) + @(if (-not $KeepPipelineIdentity) { $IdentityGroup })
$inCi = $env:GITHUB_ACTIONS -eq 'true'

function Invoke-Az([string[]]$Arguments) {
    $raw = & az @Arguments --subscription $SubscriptionId --output json --only-show-errors
    if ($LASTEXITCODE -ne 0) { throw "Azure command failed: az $($Arguments[0..2] -join ' ')" }
    if ($raw) { ($raw -join "`n") | ConvertFrom-Json }
}
function Test-Group([string]$Name) {
    $exists = Invoke-Az @('group', 'exists', '--name', $Name)
    if ($exists -isnot [bool]) { throw 'Azure did not return a valid resource-group existence result.' }
    $exists
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
if (($ConfirmResourceGroups -join ',') -cne $expected) { throw "Deletion requires -ConfirmResourceGroups '$expected'. Nothing was deleted." }
if (-not $PSCmdlet.ShouldProcess("$SubscriptionId/$expected", 'Permanently delete these resource groups')) { return }

if ($inventory.groups.Contains($WorkloadGroup)) {
    $scope = @('--resource-group', $WorkloadGroup)
    # Foundry rejects account deletion while child projects exist, and capability hosts keep agent subnets linked.
    foreach ($account in @(Invoke-Az (@('cognitiveservices', 'account', 'list') + $scope))) {
        foreach ($project in @(Invoke-Az (@('cognitiveservices', 'account', 'project', 'list', '--name', $account.name) + $scope))) {
            $projectName = ($project.name -split '/')[-1]
            Write-Output "Deleting Foundry project $($account.name)/$projectName"
            Invoke-Az (@('cognitiveservices', 'account', 'project', 'delete', '--name', $account.name, '--project-name', $projectName) + $scope) | Out-Null
        }
        $hosts = & az rest --method get --url "https://management.azure.com$($account.id)/capabilityHosts?api-version=2025-06-01" --query 'value[].id' --output json --only-show-errors
        if ($LASTEXITCODE -ne 0) { throw "Could not list capability hosts for $($account.name)." }
        foreach ($hostId in @(($hosts -join "`n") | ConvertFrom-Json)) {
            Write-Output "Deleting capability host $hostId"
            Invoke-Az @('resource', 'delete', '--ids', $hostId, '--api-version', '2025-06-01') | Out-Null
        }
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
