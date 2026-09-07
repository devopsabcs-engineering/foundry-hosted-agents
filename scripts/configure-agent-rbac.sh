#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR/.."
AGENT_NAME=${1:?Usage: configure-agent-rbac.sh AGENT_NAME}
PRINCIPAL_ID=$(azd ai agent show "$AGENT_NAME" --output json | jq -er '.instance_identity.principal_id | select(type == "string" and length > 0)')
PROJECT_ID=$(azd env get-values --output json | jq -er '.AZURE_AI_PROJECT_ID | select(type == "string" and length > 0)')
ACCOUNT_NAME=$(printf '%s' "$PROJECT_ID" | jq -Rer 'capture("/accounts/(?<name>[^/]+)/projects/[^/]+$").name')
RESOURCE_GROUP=$(printf '%s' "$PROJECT_ID" | jq -Rer 'capture("/resourceGroups/(?<name>[^/]+)/").name')
SUBSCRIPTION_ID=$(printf '%s' "$PROJECT_ID" | jq -Rer 'capture("^/subscriptions/(?<id>[^/]+)/").id')
OPENAI_ROLE=$(az role definition list --name 'Cognitive Services OpenAI User' --subscription "$SUBSCRIPTION_ID" --query '[0].name' --output tsv)
test -n "$OPENAI_ROLE"
PRINCIPALS=$(jq -cn --arg principal "$PRINCIPAL_ID" '[$principal]')
ROLES=$(jq -cn --arg openai "$OPENAI_ROLE" '["53ca6127-db72-4b80-b1b0-d745d6d5456d", $openai]')

az deployment group create \
  --name agent-runtime-rbac \
  --subscription "$SUBSCRIPTION_ID" \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/modules/rbac.bicep \
  --parameters accountName="$ACCOUNT_NAME" principalIds="$PRINCIPALS" roleDefinitionIds="$ROLES" \
  --query properties.provisioningState --output tsv