@description('Name of the existing Foundry (Microsoft.CognitiveServices/accounts) resource to scope role assignments to')
param accountName string

@description('Principal IDs to receive the Foundry roles in roleDefinitionIds')
param principalIds array

@description('Principal type applied to every entry in principalIds')
@allowed([
  'ServicePrincipal'
  'User'
  'Group'
])
param principalType string = 'ServicePrincipal'

@description('Foundry role definition GUIDs to assign to every principal in principalIds')
param roleDefinitionIds array = [
  '53ca6127-db72-4b80-b1b0-d745d6d5456d' // Foundry User
  'eadc314b-1a2d-4efa-be10-5d325db5065e' // Foundry Project Manager
  'eed3b665-ab3a-47b6-8f48-c9382fb1dad6' // Foundry Agent Consumer
]

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: accountName
}

var principalRolePairs = map(
  principalIds,
  principalId =>
    map(roleDefinitionIds, roleDefinitionId => {
      principalId: principalId
      roleDefinitionId: roleDefinitionId
    })
)
var assignmentPairs = reduce(principalRolePairs, [], (cur, next) => concat(cur, next))

resource roleAssignments 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for pair in assignmentPairs: {
    name: guid(account.id, pair.principalId, pair.roleDefinitionId)
    scope: account
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', pair.roleDefinitionId)
      principalId: pair.principalId
      principalType: principalType
    }
  }
]
