#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
cd "$SCRIPT_DIR"
VALIDATOR=validate-agent-response.jq
EVENTS='[
  {"type":"response.output_text.delta","delta":"Ready"},
  {"type":"response.completed","response":{
    "status":"completed","error":null,"output":[{
      "type":"message","role":"assistant","content":[
        {"type":"output_text","text":"Ready"}
      ]
    }]
  }}
]'

validate_events() {
  jq -cr '.[]' | sed 's/^/data: /' | jq -Rse -f "$VALIDATOR"
}

printf '%s' "$EVENTS" | validate_events
printf '%s' "$EVENTS" | jq -cr '.[]' | sed 's/^/data: /; s/$/\r/' | jq -Rse -f "$VALIDATOR"

for mutation in \
  'map(select(.type != "response.completed"))' \
  'map(select(.type != "response.output_text.delta"))' \
  '.[1].response.status = "incomplete"' \
  '.[1].response.output = []' \
  '.[1].response.output[0].content[0].text = " "' \
  '.[1].response.error = {"code":"PermissionDenied"}' \
  '. + [{"type":"error","message":"401 PermissionDenied"}]' \
  '. + [{"type":"response.failed"}]' \
  '. + [{"type":"response.incomplete"}]'; do
  if printf '%s' "$EVENTS" | jq "$mutation" | validate_events; then
    printf 'FAIL: accepted invalid stream: %s\n' "$mutation"
    exit 1
  fi
done

for payload in '' 'HTTP/2.0 401 Unauthorized' 'data: {malformed'; do
  if printf '%s' "$payload" | jq -Rse -f "$VALIDATOR"; then
    printf 'FAIL: accepted invalid payload: %s\n' "$payload"
    exit 1
  fi
done

printf 'PASS: valid LF/CRLF streams accepted; 12 invalid streams rejected\n'