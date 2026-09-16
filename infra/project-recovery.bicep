@description('Existing injected Foundry account')
param accountName string

@description('New project name for testing same-name recreation recovery')
param projectName string

@description('Region of the existing Foundry account')
param location string = resourceGroup().location

param defenderMcpUrl string
param anomalyMcpUrl string

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' = {
  parent: account
  name: projectName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    displayName: projectName
    description: 'Threat assessment VNet migration recovery'
  }
}

resource defenderConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'defender-recovery'
  properties: {
    category: 'RemoteTool'
    target: defenderMcpUrl
    authType: 'None'
    isSharedToAll: false
    metadata: {
      ApiType: 'Azure'
    }
  }
}

resource anomalyConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-04-01-preview' = {
  parent: project
  name: 'anomaly-recovery'
  properties: {
    category: 'RemoteTool'
    target: anomalyMcpUrl
    authType: 'None'
    isSharedToAll: false
    metadata: {
      ApiType: 'Azure'
    }
  }
}

output projectId string = project.id
output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'