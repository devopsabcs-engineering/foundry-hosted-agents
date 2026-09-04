# Load & Scale Gate — Step 7.1

PoC-scale probe against the live deployed hosted agent
(`threat-assessment-agent` v9, `rg-air-canada-threat-assessment-poc`,
eastus2). Not a production load-testing rig — a lightweight `asyncio`/
`aiohttp` script hitting the agent's Responses REST endpoint directly,
per the plan's guidance to avoid provisioning heavy external load-testing
infrastructure for a PoC.

## Files

* `load_test.py` — async load generator. Three run modes:
  * `concurrent-sessions` — fires N independent new-conversation requests
    concurrently, one turn each. Measures concurrent-session capacity and
    cold-start latency distribution (every new conversation is a fresh
    per-session sandbox per the Foundry hosted-agent scaling model).
  * `same-thread-turns` — fires N concurrent requests against the **same**
    conversation ID, to observe same-thread turn concurrency behavior
    (serialized, queued, or erroring).
  * `sequential-cold-start` — runs N new-conversation requests one at a
    time (no concurrency) to isolate a clean cold-start latency sample
    from any queuing/throttling effects that concurrent runs might add.
* `results/` — raw JSON output and the human-readable report for each run
  actually executed in this session.
* `report.md` — the Step 7.1 success-criteria report: measured
  concurrent-session capacity, cold-start p50/p95, observed vCPU/memory
  tier, and an explicit statement on whether a hard ceiling was observed.

## Auth

Uses `az account get-access-token --resource https://ai.azure.com` (the
same bearer-token mechanism already verified working in this repo for the
`tools/resolve` diagnostic — see repo memory
`foundry-hosted-agents-notes.md`). Requires the operator to already be
`az login`'d with access to the resource group (same identity used for
`azd provision`/`azd deploy` throughout this PoC).

## Endpoint

```text
https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/proj-air-canada-threat-assessment-poc/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1
```

Confirmed via `azd ai agent show threat-assessment-agent --no-prompt`
and the `.azure/air-canada-threat-assessment-poc/.env`
`AGENT_THREAT_ASSESSMENT_AGENT_RESPONSES_ENDPOINT` value.

## Run

```powershell
$env:AGENT_ENDPOINT = "https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/proj-air-canada-threat-assessment-poc/agents/threat-assessment-agent/endpoint/protocols/openai/responses?api-version=v1"
& "../../src/threat-assessment-agent/.venv-validate/Scripts/python.exe" load_test.py concurrent-sessions --count 5 --out results/concurrent-5.json
```

See `report.md` for the actual counts run and results.
