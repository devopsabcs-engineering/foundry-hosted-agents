#requires -Version 7.3
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory)][guid]$SubscriptionId,
    [Parameter(Mandatory)][ValidatePattern('^fha-learn-[a-z0-9-]+$')][string]$EnvironmentName,
    [Parameter(Mandatory)][string]$ResourceGroup,
    [switch]$Delete,
    [string]$ConfirmResourceGroup
)

$ErrorActionPreference = 'Stop'

function Invoke-AzureJson {
    param([string[]]$Arguments)
    $result = & az @Arguments --output json
    if ($LASTEXITCODE -ne 0) { throw "Azure command failed: $($Arguments[0..1] -join ' ')" }
    if ($result) { ($result -join "`n") | ConvertFrom-Json }
}

if ($ResourceGroup -cne "rg-$EnvironmentName") {
    throw 'Resource group must exactly match rg-<learner-environment>.'
}
if ($Delete -and $ConfirmResourceGroup -cne $ResourceGroup) {
    throw 'Deletion requires -ConfirmResourceGroup with the exact resource group name.'
}
$scope = @('--subscription', "$SubscriptionId", '--resource-group', $ResourceGroup)
$exists = Invoke-AzureJson (@('group', 'exists', '--name', $ResourceGroup, '--subscription', "$SubscriptionId"))
if ($exists -isnot [bool]) { throw 'Azure did not return a valid resource-group existence result.' }
if (-not $exists) {
    Write-Output "Already absent: $ResourceGroup"
    return
}
$group = Invoke-AzureJson (@('group', 'show', '--name', $ResourceGroup, '--subscription', "$SubscriptionId"))
if ($group.tags.purpose -cne 'workshop-validation' -or $group.tags.workshopEnv -cne $EnvironmentName) {
    throw 'Workshop ownership tags do not match. No resources were deleted.'
}
$resources = Invoke-AzureJson (@('resource', 'list') + $scope)
Write-Output "Subscription: $SubscriptionId; resource group: $ResourceGroup"
$resources | Select-Object name, type, id | Format-List
if (-not $Delete) {
    Write-Output 'Preview only. Review the inventory before using -Delete and -ConfirmResourceGroup.'
    return
}
if ($PSCmdlet.ShouldProcess("$SubscriptionId/$ResourceGroup", 'Permanently remove all resources in this group')) {
    Invoke-AzureJson (@('group', 'delete', '--name', $ResourceGroup, '--subscription', "$SubscriptionId", '--yes'))
    $exists = Invoke-AzureJson (@('group', 'exists', '--name', $ResourceGroup, '--subscription', "$SubscriptionId"))
    if ($exists -isnot [bool]) { throw 'Azure did not return a valid resource-group existence result.' }
    if ($exists) { throw 'Deletion has not completed. Inspect the group before claiming cleanup succeeded.' }
    Write-Output "Verified absent: $ResourceGroup"
}