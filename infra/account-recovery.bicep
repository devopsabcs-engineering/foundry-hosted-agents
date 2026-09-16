param location string = resourceGroup().location
param accountName string = 'aif-air-canada-staging-vnet'
param projectName string = 'proj-air-canada-staging-vnet'
param vnetName string = 'vnet-air-canada-threat-assessment'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' existing = {
  name: vnetName
}

resource subnet 'Microsoft.Network/virtualNetworks/subnets@2024-05-01' = {
  parent: vnet
  name: 'snet-agent-staging-recovery'
  properties: {
    addressPrefix: '10.30.7.0/24'
    delegations: [
      {
        name: 'workload-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

resource telemetry 'Microsoft.Insights/components@2020-02-02' existing = {
  name: 'appi-air-canada-threat-assessment-staging'
}

resource defender 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: 'mcp-staging-defender-server'
}

resource anomaly 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: 'mcp-staging-anomaly-server'
}

module foundry 'modules/ai-foundry.bicep' = {
  name: 'recovery-foundry'
  params: {
    location: location
    accountName: accountName
    projectName: projectName
    agentSubnetId: subnet.id
    applicationInsightsResourceId: telemetry.id
    applicationInsightsConnectionString: telemetry.properties.ConnectionString
    defenderMcpUrl: 'https://${defender.properties.configuration.ingress.fqdn}/mcp'
    anomalyMcpUrl: 'https://${anomaly.properties.configuration.ingress.fqdn}/mcp'
  }
}

output projectId string = foundry.outputs.projectId
output projectEndpoint string = foundry.outputs.projectEndpoint