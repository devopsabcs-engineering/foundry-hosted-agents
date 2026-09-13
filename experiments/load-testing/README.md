---
title: "Load and Scale Gate"
description: "Run a bounded load probe against an explicitly selected Foundry endpoint."
---

## Scope

Historical PoC-scale probe against the deployed hosted agent
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

There is no default endpoint. Supply the HTTPS Responses URL from your own
approved learner environment, as prepared in [Lab 04](../../docs/labs/lab-04-invoke-agent.md).
Never copy a historical customer endpoint to run a new load test.

## Run

```powershell
python experiments/load-testing/load_test.py concurrent-sessions --count 5 --endpoint $ResponsesEndpoint --out .azure/workshop-load.json
```

Run from the repository root with the learner virtual environment active.
Failures produce evidence and a nonzero exit code. Five successful streams do
not establish an SLA or capacity ceiling. The legacy `same-thread-turns` mode
requires native conversation IDs and is not the supported full-history contract.

See `report.md` for the historical counts and results, not your own run outcome.
