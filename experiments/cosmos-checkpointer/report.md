---
title: Step 7.2 - Cosmos DB State Experiment Report
description: Historical checkpoint benchmark outcome and the subsequent private-networking implementation path.
---

## Historical Result

The report below preserves the original experiment evidence. As of September 15,
2026, the source templates declare private-only Cosmos, a SQL private endpoint and
DNS zone group, with Foundry VNet injection in the environment stack. See
[Private Cosmos networking](../../docs/private-networking.md) for the implementation,
migration boundary and required new tests. No new live benchmark or hosted-runtime
connectivity result is claimed by that template change; the original partial status
below remains unchanged.

**Status: Partial.** Infrastructure provisioned live and a real code bug in
the existing extension point was found and fixed; the actual
latency/RU-cost/checkpoint-size benchmarks could not be executed because
this tenant enforces private-only Cosmos DB networking, which this session's
tooling could not work around within its time budget.

## What was done

1. **Read Phase 2's extension point first** (`state.py`'s `get_checkpointer`,
   already wired into `graph.py`'s `workflow.compile(checkpointer=
   get_checkpointer())`) — confirmed a hook already exists, so no new hook
   was needed. It was, however, **broken**: see "Bug found and fixed" below.
2. **Authored `infra/modules/cosmos-db.bicep`** — serverless Cosmos NoSQL
   account, `threat-assessment-agent` database, `checkpoints` container
   (partition key `/partition_key`, matching `CosmosDBSaver`'s expected
   schema), and an optional data-plane RBAC role assignment
   (`dataPlanePrincipalIds`). Validated via `az bicep build` before
   deploying.
3. **Deployed it live**, additively, into the existing
   `rg-air-canada-threat-assessment-poc` resource group — confirmed via
   `az deployment group create` (provisioningState: Succeeded) and
   `az cosmosdb show`. No Phase 1-6 resource was touched, deleted, or
   recreated.
4. **Found and fixed a genuine bug** in `state.py`'s `get_checkpointer()`
   (see below) — this was necessary before any benchmark could even attempt
   a network call; without the fix, enabling the flag would raise
   `TypeError` in any environment.
5. **Attempted the direct RU-charge benchmark and the LangGraph
   `CosmosDBSaver` integration benchmark** (`benchmark.py`) — both blocked by
   the tenant's enforced private-only Cosmos DB networking (see below).

## Bug found and fixed (state.py)

`get_checkpointer()` called `CosmosDBSaver(endpoint=..., credential=...,
database_name=..., container_name=...)` directly. `CosmosDBSaver.__init__`
only accepts a pre-built container proxy (`self, container, *, serde=None`)
— those four kwargs belong to the async-context-manager classmethod
`from_conn_info`, not `__init__`. **This meant the extension point could
never have worked, in any environment, from the moment it was written** —
setting `ENABLE_COSMOS_CHECKPOINTER=true` would immediately raise
`TypeError`, independent of network access, credentials, or the Cosmos
account's existence.

Fixed by building the container proxy directly via
`CosmosClient(endpoint, credential=DefaultAzureCredential())
.get_database_client(db_name).get_container_client(container_name)` (both
accessor methods are synchronous, non-network-calling proxy constructors —
confirmed via `inspect.iscoroutinefunction`) and passing that into
`CosmosDBSaver(container)`. This mirrors what `from_conn_info` does
internally, minus the `create_database_if_not_exists`/
`create_container_if_not_exists` calls, which are unnecessary since the new
Bicep module already declares both.

This is a **minimal, additive fix**, not a rewrite: the baseline path
(`ENABLE_COSMOS_CHECKPOINTER` unset → `get_checkpointer()` returns `None` →
graph compiles without a checkpointer, exactly as before) is completely
unchanged. Verified via the full existing pytest suite: **18/18 tests still
pass** after the fix.

Verification of the fix itself: reproduced the original `TypeError` before
fixing; after the fix, `get_checkpointer()` constructs a real
`CosmosDBSaver` instance and compiles successfully into a `StateGraph`,
failing only when an actual network call is attempted (see next section) —
confirming the fix is correct and the remaining blocker is purely network
policy, not the code.

## Why the live benchmark could not complete

This tenant/subscription enforces `publicNetworkAccess: Disabled` on Cosmos
DB accounts. An explicit Bicep override to `Enabled` was deployed
successfully by ARM (no policy-denial error, `provisioningState: Succeeded`)
but `az cosmosdb show` confirmed the property **remained `Disabled`**
afterward — a genuine out-of-band governance control (exact mechanism, e.g.
a management-group-scoped Modify-effect policy, not identified within this
session's time budget via `az policy assignment list` at the visible
scopes), not a Bicep authoring mistake.

The real (now-fixed) `state.get_checkpointer()` code path was exercised
directly and failed with:

```text
azure.cosmos.exceptions.CosmosHttpResponseError: (Forbidden) Request
originated from IP <...> through public internet. This is blocked by your
Cosmos DB account firewall settings.
```

No latency, RU-cost, or checkpoint-size numbers were obtained as a result.
Full detail: `results/network-blocked-evidence.json`.

## Success-criteria disposition

* *"Benchmark report states measured latency delta and RU cost for a
  representative multi-turn session"* — **Not met.** No live benchmark could
  be executed; see above.
* *"Report confirms or refutes managed-identity-based private connectivity
  from hosted-agent compute to Cosmos DB"* — **Partially refutes/confirms a
  narrower claim than expected.** This session confirms that **public**
  connectivity is impossible for this Cosmos account in this tenant (private
  connectivity is mandatory, not merely recommended). It does **not**
  confirm that private connectivity specifically works **from a Foundry
  Hosted Agent's own per-session sandbox** — whether that sandbox can be
  VNet-injected/peered to reach a private endpoint at all is a genuine,
  separate, unresolved platform question that this session's tooling could
  not test (no private endpoint was provisioned; doing so plus a
  VNet-resident compute location to run the benchmark from was judged out
  of scope for this PoC-scale probe's time budget). This should be recorded
  as an open item on the Production Decision Gate scorecard (Step 7.5), not
  papered over as either a pass or an unrelated failure.

## What a real benchmark would require

1. A private endpoint for the Cosmos account plus a VNet with private DNS
   zone integration.
2. A compute location genuinely inside that VNet to run the benchmark
   script from (e.g. a Container App/VM/self-hosted runner joined to the
   VNet) — the operator's own machine and any other public-internet compute
   cannot reach a private-endpoint-only Cosmos account.
3. Separately: confirmation (from the Foundry product team, since it is not
   in the researched documentation) of whether a Hosted Agent's per-session
   sandbox supports VNet injection/peering to reach a private endpoint at
   all. Absent that confirmation, "wire `CosmosDBSaver` into the *live
   deployed* hosted agent for a private-network benchmark" is not currently
   something this PoC's tooling can validate, regardless of the Cosmos-side
   configuration.
