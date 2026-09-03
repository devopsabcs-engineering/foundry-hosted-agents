@description('Azure region for the Foundry account and project')
param location string = resourceGroup().location

@description('Name of the Microsoft.CognitiveServices/accounts (Foundry) resource')
param accountName string

@description('Name of the Foundry project')
param projectName string

@description('Display name shown in the Foundry portal for the project')
param projectDisplayName string = projectName

@description('Description of the Foundry project')
param projectDescription string = 'Threat assessment multi-agent PoC project'

@description('Model deployment name (referenced by azure.yaml AZURE_AI_MODEL_DEPLOYMENT_NAME)')
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
param modelSkuCapacity int = 10

// Basic Agent Setup: Microsoft-managed conversation/file/vector storage — no capabilityHosts.
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
  }
}

resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: modelDeploymentName
  sku: {
    name: modelSkuName
    capacity: modelSkuCapacity
  }
  properties: {
    model: {
      format: modelFormat
      name: modelName
      version: modelVersion
    }
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectDisplayName
    description: projectDescription
  }
}

// Placeholder so the project can reference the account's model deployment via AAD;
// category/metadata shape to be refined once agent-specific connection needs are known.
resource modelConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: '${modelDeploymentName}-connection'
  properties: {
    category: 'AzureOpenAI'
    target: account.properties.endpoint
    authType: 'AAD'
    isSharedToAll: true
    metadata: {
      ApiType: 'Azure'
      ResourceId: account.id
      DeploymentName: modelDeploymentName
    }
  }
  dependsOn: [
    modelDeployment
  ]
}

output accountId string = account.id
output accountName string = account.name
output accountEndpoint string = account.properties.endpoint
output accountPrincipalId string = account.identity.principalId
output projectId string = project.id
output projectName string = project.name
output projectPrincipalId string = project.identity.principalId
output modelDeploymentName string = modelDeployment.name
