#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
TEMP_DIR=$(mktemp -d)
if command -v cygpath >/dev/null 2>&1; then
  TEMP_DIR=$(cygpath -m "$TEMP_DIR")
fi
trap 'rm -rf "$TEMP_DIR"' EXIT
export TEMP_DIR
jq() { command jq "$@" | tr -d '\r'; }
azd() {
  if [ "$1 $2" = 'env get-values' ]; then
    printf '%s\n' '{"FOUNDRY_PROJECT_ENDPOINT":"https://project.test/api/projects/prod"}'
  elif [ "$1 $2" = 'env set' ]; then
    printf '%s' "$4" > "$TEMP_DIR/$3"
  else
    test "$(cat "$TEMP_DIR/AGENT_THREAT_ASSESSMENT_AGENT_NAME")" = threat-assessment-agent
    jq -cn --arg version "$(cat "$TEMP_DIR/AGENT_THREAT_ASSESSMENT_AGENT_VERSION")" \
      --arg status "${STATUS:-active}" '{version:$version,status:$status}'
  fi
}
az() {
  jq -cn --arg scenario "$SCENARIO" '{name:"threat-assessment-agent",state:"enabled",
    versions:{latest:{version:"33"}},agent_endpoint:{version_selector:{version_selection_rules:[
    {type:"FixedRatio",agent_version:"@latest",traffic_percentage:100}]}}}
    | if $scenario == "pinned" then .agent_endpoint.version_selector.version_selection_rules[0].agent_version="31"
      elif $scenario == "split" then .agent_endpoint.version_selector.version_selection_rules |= (. + .)
      elif $scenario == "disabled" then .state="disabled"
      elif $scenario == "invalid" then .versions.latest.version="invalid"
      else . end'
}
export -f az azd jq
for SCENARIO in latest pinned; do
  export SCENARIO
  VERSION=$(bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence")
  if [ "$SCENARIO" = latest ]; then test "$VERSION" = 33; else test "$VERSION" = 31; fi
done
for SCENARIO in split disabled invalid; do
  export SCENARIO
  if bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence"; then exit 1; fi
done
export SCENARIO=latest STATUS=failed
if bash "$SCRIPT_DIR/record-production-version.sh" threat-assessment-agent "$TEMP_DIR/evidence"; then exit 1; fi
echo 'PASS: fresh environment, latest/pinned routing; ambiguous, disabled, invalid and inactive versions rejected'