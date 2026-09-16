---
title: Hybrid Network Migration Validation
description: Verified private Cosmos connectivity, web recovery, and unresolved Foundry release evidence.
ms.date: 2026-09-16
---

## Release Status

The migration is not yet release-complete. The approved teardown succeeded in
[run 35035035564](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/35035035564).
The fresh staging deployment in
[run 35035668932](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/35035668932)
passed offline checks, infrastructure validation, provisioning, and agent deployment.
Candidate 14 reported `active`, but all three fresh-session smoke attempts returned
`NotFound: Project not found`. Evaluation and production promotion were skipped.
Production has not been restored following teardown. No gate was bypassed.

## Private Cosmos Evidence

Deployment `hybrid-cosmos-network-probe` created only a temporary Container Apps
job, dedicated managed identity, AcrPull assignment, and container-scoped Cosmos
Data Contributor assignment. The job ran inside `mcp-staging-mcp-env`.

Execution `cosmos-private-network-probe-548620i` succeeded from
`2026-09-15T23:46:23Z` to `2026-09-15T23:46:53Z`. Its retained console record in
Log Analytics workspace `mcp-staging-mcp-logs`, at `2026-09-15T23:46:46Z`, was:

```json
{
  "dns_addresses": ["10.30.6.4"],
  "operations": {
    "create": "passed",
    "read": "passed",
    "delete": "passed",
    "document_id": "private-network-probe-41c1280d-a19d-4bea-9000-fa47d165a459"
  },
  "checkpointing_enabled": false
}
```

The account retained disabled public access, disabled local authentication, and
automatic failover. The SQL private endpoint was Approved and Succeeded; its
private DNS records were `10.30.6.4` and `10.30.6.5`. The network-only deployment
did not redeploy database, container, backup, or indexing settings.

The probe job, identity, and its exact two role assignments were deleted after
validation. The shared resource group, Cosmos data, registry, and application
identities were preserved. This proves managed-identity CRUD from the staging
Container Apps VNet, not hosted-agent checkpoint durability or exactly-once execution.
`ENABLE_COSMOS_CHECKPOINTER` remains unset in the release baseline.

The reusable probe is [private_network_probe.py](../experiments/cosmos-checkpointer/private_network_probe.py),
with [deployment parameters](../infra/cosmos-network-probe.bicep) and
[focused tests](../scripts/tests/test_cosmos_network_probe.py).
Preview its deployment, supply the current expected private IPs and a reviewed
image containing Python and azure-identity, and remove only the returned job,
identity, and role identifiers after retaining the execution log.

## Web Recovery

Deployment `hybrid-web-chat-recovery` succeeded using the retained image digest
`sha256:63de6265f7a9d3812a1389181f88fba6b1710cc9f6c8660dde0b587a63426d1b`.
The existing managed identity and pilot application registration were preserved.
The new URL is:

<https://foundry-threat-chat-staging.purpletree-432267ca.eastus2.azurecontainerapps.io>

The new SPA callback was added while retaining the previous hostname and localhost
callback. Browser checks confirmed the page renders, `/healthz` returns 200, and
anonymous `POST /api/conversations` returns 401. Microsoft sign-in opens correctly.
Authenticated conversation and history validation remain pending.

## Foundry Diagnostic

ARM reports the recreated staging project as Succeeded. The exact data-plane
version read for candidate 14 succeeds, but session creation fails. A correctly
serialized request at `2026-09-15T23:57:03Z` returned HTTP 404 with APIM request ID
`af5ad8da-5dc1-4826-9b5c-54856b1dea6f` and `Project not found`.

The project had no capability host. With explicit approval, the isolated
[basic capability-host module](../infra/modules/basic-agent-capability-host.bicep)
was submitted as `hybrid-staging-basic-capability-host`, matching Microsoft's
[basic VNet template](https://github.com/microsoft-foundry/foundry-samples/tree/main/infrastructure/infrastructure-setup-bicep/11-private-network-basic-vnet).
This is a diagnostic hypothesis, not a confirmed fix, and is not wired into the
normal deployment. It uses platform-managed resources, not BYO checkpoint storage.
Bicep reports BCP037 for the official sample's `capabilityHostKind` property;
the deployment preview accepted the single-resource change.

The capability-host deployment subsequently Succeeded. A fresh session request at
`2026-09-16T00:01:07Z` still returned HTTP 404 and `Project not found`, with APIM
request ID `f9c195bc-f604-4d3f-aee1-d6a696066527`. The initialization experiment did
not resolve the blocker. The host remains in staging for diagnosis; it has not
been added to the release template or production. Do not repeat teardown or
change network boundaries as an unverified workaround. Escalate the project
routing discrepancy with these request IDs and the deployment run.

## Fresh Project Recovery Experiment

[Continuous validation run 35038446737](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/35038446737)
passed offline checks but captured zero of eight responses and failed all five
concurrent streams. Downloaded invocation stderr confirmed the same
`NotFound: Project not found` error as the release smoke test.

With approval, deployment `hybrid-staging-project-recovery` created
`proj-air-canada-threat-assessment-staging-vnet` under the existing injected
account. Shared connection names could not be recreated or resolved from that
project, so the isolated experiment uses `defender-recovery` and
`anomaly-recovery`, with the original agent-facing tool labels.

The original toolbox version 1 and local staging environment still referenced
obsolete MCP hostnames. Recovery connections and toolbox version 1 were instead
bound to the current `mcp-staging-*` apps on `purpletree-432267ca`.
The unchanged agent deployed successfully as version 1. Session creation still
returned HTTP 404 with request ID `0496fab8-5046-43eb-93d3-bef24e708898`.
The official `azd ai agent invoke --version 1 --new-session` command reproduced
the same error. A fresh project name alone therefore did not resolve routing.

The user subsequently approved an additive fresh-account experiment using
`aif-air-canada-staging-vnet`, project `proj-air-canada-staging-vnet`, and dedicated
subnet `snet-agent-staging-recovery` (`10.30.7.0/24`). The preview contains only
recovery additions and reuses existing MCP apps and telemetry. The account
deployment succeeded. The agent create request lost its HTTP/2 connection,
but an exact-version read confirmed version 1 was registered and active.
No duplicate deployment was needed.

At `2026-09-16T01:21:14Z`, version-pinned session creation returned HTTP 201,
request ID `fb510a99-d49d-4a58-a3cf-8277cf23f82c`. After granting the baseline
runtime roles, a Responses request with full input history and `store=false`
returned `response.completed`, request ID
`64c7d0a0-1a72-41ce-bba7-79ab23e3fd07`. The generic azd invoke default was rejected
because it uses persisted conversations, which this pilot intentionally forbids.
The successful response establishes runtime reachability, not golden-dataset
quality or production readiness.

Release provisioning, continuous validation, and web-chat defaults now target
the replacement staging account and project. The agent consumes the versioned
toolbox endpoint produced by azd instead of hardcoded toolbox version 1, which
could retain retired MCP hostnames. Production defaults and quality gates remain
unchanged. CI deployment and evaluation of these changes are still pending.
Foundry remains public, Cosmos remains private, and baseline checkpointing remains disabled.
The shared network template retains the approved subnet for future deployments.

## Local Verification

All 103 script tests passed, including the Cosmos probe, workflow contracts,
guarded teardown, and workshop documentation. Cloud promotion, hosted-agent invocation, evaluation, and
authenticated web testing still require successful live evidence.
