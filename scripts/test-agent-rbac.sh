#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
export PRINCIPAL=runtime-principal
export SCOPE=/subscriptions/sub/resourceGroups/group/providers/Microsoft.CognitiveServices/accounts/account
export FOUNDRY_ROLE=53ca6127-db72-4b80-b1b0-d745d6d5456d
export OPENAI_ROLE=openai-role

jq() {
  set -o pipefail
  command jq "$@" | tr -d '\r'
}

azd() {
  if [ "$1" = ai ]; then
    jq -cn --arg principal "$PRINCIPAL" '{instance_identity:{principal_id:$principal}}'
  else
    jq -cn --arg project "$SCOPE/projects/project" '{AZURE_AI_PROJECT_ID:$project}'
  fi
}
az() {
  case "$1 $2 $3" in
    'role definition list') printf '%s\n' "$OPENAI_ROLE" ;;
    'role assignment list')
      if [[ " $* " == *" --all "* ]]; then
        echo 'Scoped role lookup cannot use --all' >&2
        return 1
      fi
      if [ "$SCENARIO" = denied ]; then return 1; fi
      jq -cn --arg scenario "$SCENARIO" --arg scope "$SCOPE" --arg principal "$PRINCIPAL" \
        --arg foundry "$FOUNDRY_ROLE" --arg openai "$OPENAI_ROLE" '
        (if $scenario == "none" then [] elif $scenario == "partial" then [$foundry] else [$foundry,$openai] end)
        | map({principalId:$principal,scope:$scope,roleDefinitionId:("/roles/" + .),condition:null})
        | if $scenario == "conditioned" then map(.condition = "restricted")
          elif $scenario == "other-scope" then map(.scope += "/projects/other")
          elif $scenario == "other-principal" then map(.principalId = "someone-else")
          else . end' ;;
    'deployment group create')
      if [ "$SCENARIO" = existing ]; then echo 'Unexpected deployment' >&2; return 1; fi
      local expected="[\"$FOUNDRY_ROLE\",\"$OPENAI_ROLE\"]"
      if [ "$SCENARIO" = partial ]; then expected="[\"$OPENAI_ROLE\"]"; fi
      local argument
      for argument in "$@"; do
        if [[ "$argument" == roleDefinitionIds=* ]]; then
          jq -e --argjson expected "$expected" '. == $expected' <<< "${argument#roleDefinitionIds=}" > /dev/null || return 1
          echo Succeeded
          return 0
        fi
      done
      return 1 ;;
    *) return 1 ;;
  esac
}
export -f az azd jq
for SCENARIO in existing partial none conditioned other-scope other-principal; do
  export SCENARIO
  bash "$SCRIPT_DIR/configure-agent-rbac.sh" agent
done
export SCENARIO=denied
if bash "$SCRIPT_DIR/configure-agent-rbac.sh" agent; then
  echo 'FAIL: swallowed role lookup failure' >&2
  exit 1
fi
echo 'PASS: existing, missing, restricted and unrelated assignments; lookup failure rejected'