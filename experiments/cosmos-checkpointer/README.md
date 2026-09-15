---
title: Cosmos DB Checkpointer Experiment - Step 7.2
description: Optional checkpoint experiment, historical network blocker, and current private-network deployment guidance.
---

## What this is

An optional, additive experiment validating the Cosmos DB LangGraph
checkpointer extension point that already exists in
`src/threat-assessment-agent/state.py` (`get_checkpointer()`, feature-flagged
off by default via `ENABLE_COSMOS_CHECKPOINTER`). This experiment does **not**
change the deployed baseline hosted agent's behavior — the flag stays unset
in `azure.yaml`, so `threat-assessment-agent` v9 is completely unaffected.

## Files

* `../../infra/modules/cosmos-db.bicep` — standalone, optional Cosmos DB
  serverless account module. **Not** referenced by `infra/main.bicep`;
  deployed separately using [the private-network guide](../../docs/private-networking.md).
  The current module requires private endpoint subnet and DNS zone IDs. Its new
  configuration has not been deployed or benchmarked by this source change.
  The historical experiment deployed the original module into the existing
  `rg-air-canada-threat-assessment-poc` resource group (additive resource,
  no Phase 1-6 resource touched or recreated).
* `benchmark.py` — direct Cosmos read/write RU-charge benchmark + a real
  LangGraph `CosmosDBSaver` integration test (using the actual
  `ThreatAssessmentState` schema, dummy non-LLM node bodies so the benchmark
  isolates checkpointer overhead from LLM latency).
* `results/network-blocked-evidence.json` — what was actually provisioned,
  the code bug found and fixed in `state.py`, and why the live
  latency/RU/checkpoint-size benchmarks could not be executed in this
  session (tenant-enforced private-only Cosmos DB networking).
* `report.md` — the Step 7.2 success-criteria report.

## Real bug found and fixed

Reading `state.py`'s existing `get_checkpointer()` (per the plan's
instruction to read before assuming a hook exists or is correct) turned up a
genuine defect: it called `CosmosDBSaver(endpoint=..., credential=...,
database_name=..., container_name=...)`, but `CosmosDBSaver.__init__` only
accepts a pre-built container proxy — those four kwargs belong to the
async-context-manager classmethod `from_conn_info`, not `__init__`. This
would raise `TypeError` immediately in any environment the moment
`ENABLE_COSMOS_CHECKPOINTER=true` was set, independent of networking. Fixed
by building the container proxy via
`CosmosClient(...).get_database_client(...).get_container_client(...)`
(synchronous, non-network-calling accessors) and passing that into
`CosmosDBSaver(container)` directly — a minimal, additive fix (baseline
behavior with the flag unset is unchanged; verified via the full existing
pytest suite, 18/18 still passing).

## Why no live latency/RU numbers

This tenant/subscription enforces `publicNetworkAccess: Disabled` on Cosmos
DB accounts. An explicit Bicep override to `Enabled` deployed successfully
(no ARM error) but the property remained `Disabled` afterward — a genuine
out-of-band governance control, not a Bicep mistake. See
`results/network-blocked-evidence.json` for the full detail, including the
exact `CosmosHttpResponseError: (Forbidden)` reproduced through the real
(now-fixed) `state.get_checkpointer()` code path.
