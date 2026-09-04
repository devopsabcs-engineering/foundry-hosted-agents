// Optional Cosmos DB serverless account for the Step 7.2 LangGraph
// checkpointer experiment (research.md lines 216-227, 601-603 / DR-04).
//
// Deliberately NOT referenced by ../main.bicep: this is an additive, clearly
// labeled, optional resource for the Increment 4 state-experiment track, not
// part of the Phases 1-6 baseline deployment. Deploy it standalone against
// the same resource group:
//
//   az deployment group create \
//     --resource-group rg-air-canada-threat-assessment-poc \
//     --template-file infra/modules/cosmos-db.bicep \
//     --parameters environmentName=air-canada-threat-assessment-poc \
//                  dataPlanePrincipalIds="['<your-object-id>']"
//
// The baseline hosted agent (threat-assessment-agent) is never modified by
// this deployment -- it does not read any output of this module.
targetScope = 'resourceGroup'

@description('Azure region for the Cosmos DB account')
param location string = resourceGroup().location

@description('Base name used to derive the Cosmos DB account name (matches the PoC environment name)')
param environmentName string

@description('Cosmos DB account name override. Defaults to a derived, globally-unique-ish name.')
param accountName string = 'cosmos-${environmentName}'

@description('Database name used by the LangGraph CosmosDBSaver checkpointer')
param databaseName string = 'threat-assessment-agent'

@description('Container name used by the LangGraph CosmosDBSaver checkpointer (matches state.get_checkpointer default)')
param containerName string = 'checkpoints'

@description('Principal IDs (Entra object IDs) to grant Cosmos DB Built-in Data Contributor for the benchmark/experiment. Leave empty to skip data-plane role assignment.')
param dataPlanePrincipalIds array = []

resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2024-11-15' = {
  name: accountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    locations: [
      {
        locationName: location
        failoverPriority: 0
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    // Public network access left enabled (default) for this PoC-scale
    // experiment: private-endpoint reachability from a Foundry Hosted Agent
    // sandbox is an open research question (research.md lines 216-227) that
    // this deployment does not itself resolve -- see experiments/
    // cosmos-checkpointer/report.md "Private-endpoint reachability" section.
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-11-15' = {
  parent: cosmosAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

resource checkpointContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-11-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: [
          '/partition_key'
        ]
        kind: 'Hash'
      }
    }
  }
}

@description('Cosmos DB Built-in Data Contributor role definition ID (data-plane RBAC, required since disableLocalAuth=true)')
var dataContributorRoleId = '00000000-0000-0000-0000-000000000002'

resource dataPlaneRoleAssignments 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = [
  for principalId in dataPlanePrincipalIds: {
    parent: cosmosAccount
    name: guid(cosmosAccount.id, principalId, dataContributorRoleId)
    properties: {
      roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/${dataContributorRoleId}'
      principalId: principalId
      scope: cosmosAccount.id
    }
  }
]

output accountName string = cosmosAccount.name
output accountEndpoint string = cosmosAccount.properties.documentEndpoint
output databaseName string = database.name
output containerName string = checkpointContainer.name
