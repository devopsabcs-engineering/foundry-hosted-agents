// Container Apps environment and two apps hosting the decoupled MCP tool
// servers (defender, anomaly). Self-contained: this module provisions its
// own Log Analytics workspace and does not reference infra/modules/ai-foundry.bicep
// or any other Phase 1 module, so it compiles and can be deployed independently.
//
// Ingress remains external (public HTTPS); the workload-profiles environment
// uses the shared VNet for egress. Deploy the network foundation first.
// Images are built and pushed via `az acr build` (see acrName param) rather
// than the previous public placeholder.

@description('Location for the MCP Container Apps environment and apps.')
param location string = resourceGroup().location

@description('Base name used to derive resource names.')
param namePrefix string = 'mcp'

@description('Name of the existing Azure Container Registry hosting the built MCP server images.')
param acrName string = ''

@description('Container image for the Defender MCP server.')
param defenderImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Container image for the Anomaly MCP server.')
param anomalyImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Port exposed by each MCP server container (matches PORT env var in mcp/*/main.py).')
param containerPort int = 8000

@description('Delegated Container Apps infrastructure subnet; existing non-VNet environments require migration')
param infrastructureSubnetId string

var useAcr = !empty(acrName)
var isolatedPullIdentity = useAcr && namePrefix != 'mcp'

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = if (useAcr) {
  name: acrName
}

resource pullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (isolatedPullIdentity) {
  name: '${namePrefix}-image-pull'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (isolatedPullIdentity) {
  name: guid(acr!.id, pullIdentity!.id, 'AcrPull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: pullIdentity!.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

var logAnalyticsWorkspaceName = '${namePrefix}-mcp-logs'
var environmentName = '${namePrefix}-mcp-env'

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsWorkspaceName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsWorkspace.properties.customerId
        sharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
      }
    }
    vnetConfiguration: {
      infrastructureSubnetId: infrastructureSubnetId
      internal: false
    }
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

resource defenderContainerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-defender-server'
  location: location
  identity: isolatedPullIdentity ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity!.id}': {}
    }
  } : {
    type: 'SystemAssigned'
  }
  dependsOn: [pullRole]
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
      }
      registries: useAcr
        ? [
            {
              server: acr.properties.loginServer
              identity: isolatedPullIdentity ? pullIdentity!.id : 'system'
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'defender-server'
          image: defenderImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

// AcrPull for both container apps' system-assigned identities is already granted
// out-of-band (pre-existing role assignments on the ACR). Bicep-managed
// roleAssignment resources here previously conflicted with those existing
// assignments (ARM enforces one assignment per principal+role+scope, regardless
// of resource name), causing RoleAssignmentExists failures on every
// `azd provision` re-run. Intentionally not re-declared here; run
// `az role assignment list --scope <acr-id>` to verify the grants still exist.

resource anomalyContainerApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-anomaly-server'
  location: location
  identity: isolatedPullIdentity ? {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${pullIdentity!.id}': {}
    }
  } : {
    type: 'SystemAssigned'
  }
  dependsOn: [pullRole]
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
      }
      registries: useAcr
        ? [
            {
              server: acr.properties.loginServer
              identity: isolatedPullIdentity ? pullIdentity!.id : 'system'
            }
          ]
        : []
    }
    template: {
      containers: [
        {
          name: 'anomaly-server'
          image: anomalyImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
}

output containerAppsEnvironmentId string = containerAppsEnvironment.id
output defenderContainerAppFqdn string = defenderContainerApp.properties.configuration.ingress.fqdn
output anomalyContainerAppFqdn string = anomalyContainerApp.properties.configuration.ingress.fqdn
