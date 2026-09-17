@description('Existing Foundry account with agent subnet injection')
param accountName string

@description('Existing Foundry project to initialize')
param projectName string

@description('Platform-managed Agents capability host name')
param capabilityHostName string = 'agents'

resource account 'Microsoft.CognitiveServices/accounts@2025-04-01-preview' existing = {
  name: accountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-04-01-preview' existing = {
  parent: account
  name: projectName
}

resource capabilityHost 'Microsoft.CognitiveServices/accounts/projects/capabilityHosts@2025-04-01-preview' = {
  parent: project
  name: capabilityHostName
  properties: {
    capabilityHostKind: 'Agents'
  }
}

output capabilityHostId string = capabilityHost.id
