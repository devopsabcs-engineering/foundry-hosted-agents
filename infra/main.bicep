targetScope = 'resourceGroup'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Base name used to derive resource names (e.g. dev, poc)')
param environmentName string

@description('Foundry account (Microsoft.CognitiveServices/accounts) name')
param accountName string = 'aif-${environmentName}'

@description('Foundry project name')
param projectName string = 'proj-${environmentName}'

@description('Model deployment name')
param modelDeploymentName string = 'gpt-4o-mini'

@description('Model name to deploy')
param modelName string = 'gpt-4o-mini'

@description('Model publisher format')
param modelFormat string = 'OpenAI'

@description('Model version')
param modelVersion string = '2024-07-18'

@description('Model deployment SKU name')
param modelSkuName string = 'GlobalStandard'

@description('Model deployment SKU capacity (thousands of tokens-per-minute)')
param modelSkuCapacity int = endsWith(environmentName, '-staging') ? 50 : 10

@description('Principal IDs to receive Foundry RBAC roles (e.g. the CI/CD identity). Leave empty to skip role assignment.')
param principalIds array = []

@description('Principal type applied to every entry in principalIds')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

@description('Log Analytics workspace name')
param logAnalyticsWorkspaceName string = 'log-${environmentName}'

@description('Application Insights component name')
param applicationInsightsName string = 'appi-${environmentName}'

@description('Name of the existing Azure Container Registry hosting the built MCP server images. Leave empty to use the public placeholder image.')
param mcpAcrName string = ''

@description('Container image reference for the Defender MCP server')
param defenderMcpImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('Container image reference for the Anomaly MCP server')
param anomalyMcpImage string = 'mcr.microsoft.com/k8se/quickstart:latest'

@description('MCP resource prefix; staging must not share production tool apps.')
param mcpNamePrefix string = ''

@description('Shared network name; deploy infra/network.bicep separately before either environment')
param vnetName string = 'vnet-air-canada-threat-assessment'

var isStaging = endsWith(environmentName, '-staging')
var effectiveMcpNamePrefix = !empty(mcpNamePrefix) ? mcpNamePrefix : (isStaging ? 'mcp-staging' : 'mcp')

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName

  resource acaSubnet 'subnets' existing = {
    name: isStaging ? 'snet-aca-staging' : 'snet-aca-production'
  }

  resource agentSubnet 'subnets' existing = {
    name: isStaging ? 'snet-agent-staging' : 'snet-agent-production'
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    logAnalyticsWorkspaceName: logAnalyticsWorkspaceName
    applicationInsightsName: applicationInsightsName
  }
}

module aiFoundry 'modules/ai-foundry.bicep' = {
  name: 'ai-foundry'
  params: {
    location: location
    accountName: accountName
    projectName: projectName
    applicationInsightsResourceId: monitoring.outputs.applicationInsightsId
    applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString
    modelDeploymentName: modelDeploymentName
    modelName: modelName
    modelFormat: modelFormat
    modelVersion: modelVersion
    modelSkuName: modelSkuName
    modelSkuCapacity: modelSkuCapacity
    defenderMcpUrl: 'https://${mcpContainerApps.outputs.defenderContainerAppFqdn}/mcp'
    anomalyMcpUrl: 'https://${mcpContainerApps.outputs.anomalyContainerAppFqdn}/mcp'
    agentSubnetId: vnet::agentSubnet.id
  }
}

module rbac 'modules/rbac.bicep' = if (!empty(principalIds)) {
  name: 'rbac'
  params: {
    accountName: aiFoundry.outputs.accountName
    principalIds: principalIds
    principalType: principalType
  }
}

module mcpContainerApps 'modules/mcp-container-apps.bicep' = {
  name: 'mcp-container-apps'
  params: {
    location: location
    namePrefix: effectiveMcpNamePrefix
    acrName: mcpAcrName
    defenderImage: defenderMcpImage
    anomalyImage: anomalyMcpImage
    infrastructureSubnetId: vnet::acaSubnet.id
  }
}

output accountName string = aiFoundry.outputs.accountName
output accountEndpoint string = aiFoundry.outputs.accountEndpoint
output projectName string = aiFoundry.outputs.projectName
output modelDeploymentName string = aiFoundry.outputs.modelDeploymentName
output FOUNDRY_PROJECT_ENDPOINT string = aiFoundry.outputs.projectEndpoint
// ARM resource ID of the Foundry project -- required by azd's azure.ai.agent host
// target to publish/deploy hosted agents (distinct from the v2 data-plane project endpoint above).
output AZURE_AI_PROJECT_ID string = aiFoundry.outputs.projectId
output logAnalyticsWorkspaceId string = monitoring.outputs.logAnalyticsWorkspaceId
output applicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString
output DEFENDER_MCP_URL string = 'https://${mcpContainerApps.outputs.defenderContainerAppFqdn}/mcp'
output ANOMALY_MCP_URL string = 'https://${mcpContainerApps.outputs.anomalyContainerAppFqdn}/mcp'
