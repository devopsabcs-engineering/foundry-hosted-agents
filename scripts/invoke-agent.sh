#!/usr/bin/env bash
set -euo pipefail

PROJECT_ENDPOINT=$(azd env get-value FOUNDRY_PROJECT_ENDPOINT)
test -n "$PROJECT_ENDPOINT"
test -n "$AGENT_NAME"
test -n "$AGENT_VERSION"
SESSION_BODY=$(jq -cn --arg version "$AGENT_VERSION" '{version_indicator:{type:"version_ref",agent_version:$version}}')
SESSION_ID=$(az rest --method POST \
  --url "$PROJECT_ENDPOINT/agents/$AGENT_NAME/endpoint/sessions?api-version=v1" \
  --resource https://ai.azure.com --body "$SESSION_BODY" --query agent_session_id -o tsv)
test -n "$SESSION_ID"
TOKEN=$(az account get-access-token --resource https://ai.azure.com --query accessToken -o tsv)
jq -cn --arg session "$SESSION_ID" --arg prompt "$AGENT_TEST_PROMPT" \
  '{agent_session_id:$session,input:[{role:"user",content:$prompt}],stream:true,store:false}' |
  curl --fail-with-body --silent --show-error --max-time 180 \
    "$PROJECT_ENDPOINT/agents/$AGENT_NAME/endpoint/protocols/openai/responses?api-version=v1" \
    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data-binary @-