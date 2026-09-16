targetScope = 'resourceGroup'

@description('Region for the shared network; must match the Foundry accounts')
param location string = resourceGroup().location

@description('Shared virtual network deployed once before the environment stacks')
param vnetName string = 'vnet-air-canada-threat-assessment'

@description('Non-overlapping RFC 1918 address space; review against corporate networks before deployment')
param vnetAddressPrefix string = '10.30.0.0/16'

@description('Production Container Apps subnet prefix')
param acaProductionSubnetPrefix string = '10.30.0.0/23'

@description('Staging Container Apps subnet prefix')
param acaStagingSubnetPrefix string = '10.30.2.0/23'

@description('Production Foundry agent subnet prefix, exclusive to its account')
param agentProductionSubnetPrefix string = '10.30.4.0/24'

@description('Staging Foundry agent subnet prefix, exclusive to its account')
param agentStagingSubnetPrefix string = '10.30.5.0/24'

@description('Private endpoint subnet prefix')
param privateEndpointSubnetPrefix string = '10.30.6.0/24'

@description('Approved replacement staging account subnet prefix')
param agentStagingRecoverySubnetPrefix string = '10.30.7.0/24'

var delegatedSubnets = [
  { name: 'snet-aca-production', prefix: acaProductionSubnetPrefix }
  { name: 'snet-aca-staging', prefix: acaStagingSubnetPrefix }
  { name: 'snet-agent-production', prefix: agentProductionSubnetPrefix }
  { name: 'snet-agent-staging', prefix: agentStagingSubnetPrefix }
]

var workloadSubnets = [for subnet in delegatedSubnets: {
  name: subnet.name
  properties: {
    addressPrefix: subnet.prefix
    delegations: [
      {
        name: 'workload-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}]

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: vnetName
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: concat(workloadSubnets, [
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: privateEndpointSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-agent-staging-recovery'
        properties: {
          addressPrefix: agentStagingRecoverySubnetPrefix
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
    ])
  }
}

resource cosmosPrivateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
}

resource cosmosPrivateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cosmosPrivateDnsZone
  name: '${vnetName}-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

output vnetName string = vnet.name
output vnetId string = vnet.id
output acaProductionSubnetId string = vnet.properties.subnets[0].id
output acaStagingSubnetId string = vnet.properties.subnets[1].id
output agentProductionSubnetId string = vnet.properties.subnets[2].id
output agentStagingSubnetId string = vnet.properties.subnets[3].id
output privateEndpointSubnetId string = vnet.properties.subnets[4].id
output cosmosPrivateDnsZoneId string = cosmosPrivateDnsZone.id
