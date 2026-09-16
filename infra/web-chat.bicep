param location string = resourceGroup().location
param appName string = 'foundry-threat-chat-staging'
param environmentName string = 'mcp-staging-mcp-env'
param acrName string = 'acraircanadapoc001'
param image string
param tenantId string = 'aa93b9d9-037d-4f08-a26d-783cff0e2369'
param clientId string = '9cfb9dc7-f433-47f6-826b-14bc90a817bc'
param pilotGroupId string = '201b962a-8619-401e-a1f0-733bca2cd7b2'
param foundryAccountName string = 'aif-air-canada-staging-vnet'
param foundryProjectName string = 'proj-air-canada-staging-vnet'

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: environmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: foundryAccountName
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' existing = {
  parent: account
  name: foundryProjectName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${appName}-identity'
  location: location
}

resource pullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'AcrPull')
  scope: registry
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  }
}

resource invokeRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(project.id, identity.id, 'FoundryUser')
  scope: project
  properties: {
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '53ca6127-db72-4b80-b1b0-d745d6d5456d')
  }
}

resource web 'Microsoft.App/containerApps@2024-03-01' = {
  name: appName
  location: location
  tags: {
    environment: 'staging'
    purpose: 'internal-pilot-web-chat'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  dependsOn: [pullRole, invokeRole]
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        allowInsecure: false
        targetPort: 8000
        transport: 'http'
      }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'web-chat'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'ENTRA_TENANT_ID', value: tenantId }
          { name: 'ENTRA_CLIENT_ID', value: clientId }
          { name: 'PILOT_GROUP_ID', value: pilotGroupId }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'AGENT_ENDPOINT', value: 'https://${foundryAccountName}.services.ai.azure.com/api/projects/${foundryProjectName}/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1' }
        ]
        probes: [
          { type: 'Liveness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 15, periodSeconds: 30 }
          { type: 'Readiness', httpGet: { path: '/healthz', port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
        ]
      }]
      scale: { minReplicas: 1, maxReplicas: 1 }
    }
  }
}

output url string = 'https://${web.properties.configuration.ingress.fqdn}'
output principalId string = identity.properties.principalId
