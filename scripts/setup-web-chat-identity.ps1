param(
    [string]$RedirectUri = 'http://localhost:8000',
    [string]$TenantId = 'aa93b9d9-037d-4f08-a26d-783cff0e2369',
    [string]$PilotGroupId = '201b962a-8619-401e-a1f0-733bca2cd7b2'
)

$ErrorActionPreference = 'Stop'
$displayName = 'Foundry Threat Assessment Web Chat'
$scopeId = 'c975c04e-a028-42da-b365-6d9dd4e9085e'
$roleId = 'ef52b0b1-2d8e-4a72-89ce-ac1212066351'

function Invoke-Graph([string]$Method, [string]$Path, $Body) {
    $arguments = @('rest', '--method', $Method, '--url', "https://graph.microsoft.com/v1.0/$Path", '--output', 'json')
    $temporary = $null
    try {
        if ($null -ne $Body) {
            $temporary = [System.IO.Path]::GetTempFileName()
            [System.IO.File]::WriteAllText($temporary, ($Body | ConvertTo-Json -Depth 20))
            $arguments += @('--headers', 'Content-Type=application/json', '--body', "@$temporary")
        }
        $result = & az @arguments
        if ($LASTEXITCODE -ne 0) { throw "Graph $Method $Path failed" }
        if ($result) { return ($result | ConvertFrom-Json) }
    }
    finally {
        if ($temporary) { Remove-Item $temporary -Force }
    }
}

$account = az account show -o json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $account.tenantId -ne $TenantId) { throw 'Sign in to the approved tenant first.' }
$group = Invoke-Graph GET "groups/$PilotGroupId" $null
if (-not $group.securityEnabled) { throw 'Pilot group must be security enabled.' }
$uri = [uri]$RedirectUri
if ($uri.Scheme -ne 'https' -and $RedirectUri -ne 'http://localhost:8000') {
    throw 'Only HTTPS or the approved localhost redirect is allowed.'
}

$apps = @(az ad app list --display-name $displayName -o json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $apps.Count -gt 1) { throw 'Cannot uniquely resolve the web-chat application.' }
if ($apps.Count -eq 0) {
    $application = Invoke-Graph POST 'applications' @{
        displayName = $displayName
        signInAudience = 'AzureADMyOrg'
    }
}
else { $application = $apps[0] }

$redirects = @($application.spa.redirectUris) + @('http://localhost:8000', $RedirectUri)
$redirects = @($redirects | Where-Object { $_ } | Sort-Object -Unique)
Invoke-Graph PATCH "applications/$($application.id)" @{
    signInAudience = 'AzureADMyOrg'
    identifierUris = @("api://$($application.appId)")
    groupMembershipClaims = 'SecurityGroup'
    spa = @{ redirectUris = $redirects }
    api = @{
        requestedAccessTokenVersion = 2
        oauth2PermissionScopes = @(@{
            id = $scopeId
            value = 'Chat.Access'
            type = 'Admin'
            isEnabled = $true
            adminConsentDisplayName = 'Access the pilot assessment chat'
            adminConsentDescription = 'Use the internal pilot web chat as the signed-in user.'
        })
    }
    requiredResourceAccess = @(@{
        resourceAppId = $application.appId
        resourceAccess = @(@{ id = $scopeId; type = 'Scope' })
    })
    appRoles = @(@{
        id = $roleId
        value = 'Pilot.User'
        displayName = 'Pilot user'
        description = 'Assigned member of the web-chat pilot.'
        allowedMemberTypes = @('User')
        isEnabled = $true
    })
} | Out-Null

$principals = @(az ad sp list --filter "appId eq '$($application.appId)'" -o json | ConvertFrom-Json)
if ($LASTEXITCODE -ne 0 -or $principals.Count -gt 1) { throw 'Cannot uniquely resolve the service principal.' }
if ($principals.Count -eq 0) {
    $principal = Invoke-Graph POST 'servicePrincipals' @{ appId = $application.appId; appRoleAssignmentRequired = $true }
}
else { $principal = $principals[0] }
Invoke-Graph PATCH "servicePrincipals/$($principal.id)" @{ appRoleAssignmentRequired = $true } | Out-Null
$assignments = Invoke-Graph GET "servicePrincipals/$($principal.id)/appRoleAssignedTo" $null
if (-not ($assignments.value | Where-Object { $_.principalId -eq $PilotGroupId -and $_.appRoleId -eq $roleId })) {
    Invoke-Graph POST "servicePrincipals/$($principal.id)/appRoleAssignedTo" @{
        principalId = $PilotGroupId; resourceId = $principal.id; appRoleId = $roleId
    } | Out-Null
}
$grants = Invoke-Graph GET "servicePrincipals/$($principal.id)/oauth2PermissionGrants" $null
if (-not ($grants.value | Where-Object { $_.resourceId -eq $principal.id -and $_.scope -eq 'Chat.Access' -and $_.consentType -eq 'AllPrincipals' })) {
    Invoke-Graph POST 'oauth2PermissionGrants' @{
        clientId = $principal.id; resourceId = $principal.id; consentType = 'AllPrincipals'; scope = 'Chat.Access'
    } | Out-Null
}
$verified = Invoke-Graph GET "applications/$($application.id)" $null
if ($verified.api.requestedAccessTokenVersion -ne 2 -or $verified.groupMembershipClaims -ne 'SecurityGroup') {
    throw 'Application configuration verification failed.'
}
[ordered]@{
    tenantId = $TenantId
    clientId = $application.appId
    applicationObjectId = $application.id
    servicePrincipalId = $principal.id
    pilotGroupId = $PilotGroupId
    redirectUris = $verified.spa.redirectUris
} | ConvertTo-Json -Depth 5