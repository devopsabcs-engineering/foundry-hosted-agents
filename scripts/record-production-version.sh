#!/usr/bin/env bash
set -euo pipefail
AGENT_NAME=${1:?Agent service name is required}
EVIDENCE_PREFIX=${2:?Evidence prefix is required}
ENDPOINT=$(azd env get-values --output json | jq -er '.FOUNDRY_PROJECT_ENDPOINT | select(type == "string" and startswith("https://"))')
az rest --method GET --url "${ENDPOINT%/}/agents/$AGENT_NAME?api-version=v1" \
  --resource https://ai.azure.com --output json > "${EVIDENCE_PREFIX}-remote.json"
VERSION=$(jq -er --arg name "$AGENT_NAME" '
  select(.name == $name and .state == "enabled")
  | . as $agent
  | .agent_endpoint.version_selector.version_selection_rules
  | select(length == 1)
  | .[0] | select(.type == "FixedRatio" and .traffic_percentage == 100)
  | .agent_version
  | if . == "@latest" then $agent.versions.latest.version else . end
  | select(type == "string" and test("^[0-9]+$"))
' "${EVIDENCE_PREFIX}-remote.json")
SERVICE_KEY=$(printf '%s' "$AGENT_NAME" | tr '[:lower:]-' '[:upper:]_')
azd env set "AGENT_${SERVICE_KEY}_NAME" "$AGENT_NAME" > /dev/null
azd env set "AGENT_${SERVICE_KEY}_VERSION" "$VERSION" > /dev/null
azd ai agent show "$AGENT_NAME" --output json > "${EVIDENCE_PREFIX}.json"
jq -e --arg version "$VERSION" '.version == $version and .status == "active"' "${EVIDENCE_PREFIX}.json" > /dev/null
printf '%s\n' "$VERSION"