param location string = resourceGroup().location
param jobName string = 'cosmos-private-network-probe'
param environmentName string = 'mcp-staging-mcp-env'
param accountName string = 'cosmos-air-canada-threat-assessment-poc'
param acrName string = 'acraircanadapoc001'
param image string
param expectedPrivateIps string

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: environmentName
}

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' existing = {
  name: accountName
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: acrName
}

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${jobName}-identity'
  location: location
  tags: { purpose: 'temporary-network-validation' }
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

resource dataRole 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = {
  parent: account
  name: guid(account.id, identity.id, 'network-probe')
  properties: {
    principalId: identity.properties.principalId
    roleDefinitionId: '${account.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    scope: '${account.id}/dbs/threat-assessment-agent/colls/checkpoints'
  }
}

resource job 'Microsoft.App/jobs@2024-03-01' = {
  name: jobName
  location: location
  tags: { purpose: 'temporary-network-validation' }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${identity.id}': {} }
  }
  dependsOn: [pullRole, dataRole]
  properties: {
    environmentId: environment.id
    configuration: {
      triggerType: 'Manual'
      replicaTimeout: 180
      replicaRetryLimit: 0
      manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'probe'
        image: image
        command: ['/bin/sh', '-c']
        args: ['pip install --quiet azure-cosmos==4.16.4 && python -c "import base64,os;exec(base64.b64decode(os.environ[\'PROBE_SOURCE\']))"']
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'COSMOS_ENDPOINT', value: account.properties.documentEndpoint }
          { name: 'EXPECTED_PRIVATE_IPS', value: expectedPrivateIps }
          { name: 'PROBE_SOURCE', value: base64(loadTextContent('../experiments/cosmos-checkpointer/private_network_probe.py')) }
        ]
      }]
    }
  }
}

output jobName string = job.name
output identityName string = identity.name
output pullRoleId string = pullRole.id
output dataRoleName string = dataRole.name
