---
permalink: /labs/lab-07-troubleshooting-rbac
title: "Lab 07 - Real-World Troubleshooting: RBAC 401"
description: "Investigate a hosted-agent 401 PermissionDenied error and verify recovery after redeployment with Azure CLI and azd."
---

> 🇫🇷 **[Version française](../fr/labs/lab-07-troubleshooting-rbac)**

## Overview

| | |
|---|---|
| **Duration** | 40 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 06](lab-06-cicd.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Reproduce the exact `az` commands used to rule RBAC configuration in or out as a root cause
* Read a built-in role definition's `dataActions` directly instead of trusting a support script's assumption
* Check whether Azure Policy could be silently overriding a resource property you're reading
* Enumerate tenant Conditional Access policies to rule out identity-layer blocks
* Explain why "the portal shows the role assigned" is not sufficient proof by itself

## The Symptom

This PoC hit a real, reproducible `401 PermissionDenied` when the hosted
agent's own Instance Identity calls Azure OpenAI chat completions:

```text
ERROR: agent error (server_error): Error code: 401 - {'error': {'code': 'PermissionDenied',
'message': 'The principal `<service-principal-id>` lacks the required data action
`Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action`
to perform `POST /openai/deployments/{deployment-id}/chat/completions` operation.'}}
```

This is tracked as **WI-11** in the project's
[wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/RBAC-401-Investigation)
and was escalated to Azure Support. On September 7, 2026, version 9 still
reproduced the 401, but a redeployment to version 32 completed an assessment
in a fresh session using the same instance identity. No source edits, role
changes, or CLI upgrades were made during this retry. The recovery is
verified for that invocation; its root cause and support-case closure are
not established. Follow the diagnostic steps below before retrying.

## Exercises

### Exercise 7.1: Don't Trust the Error Message's Own Diagnosis — Verify It

The error names a specific missing data action. Verify the assignment
directly instead of assuming the message is accurate:

```powershell
az role assignment list --assignee <service-principal-id> `
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account-name> `
  -o table
```

In this investigation, this came back showing **both** `Foundry User` and
`Cognitive Services OpenAI User` already assigned at the exact resource
scope — the assignment support asked to double-check was already correct.

### Exercise 7.2: Read the Role Definition Itself — Don't Assume It "Includes" a Data Action

A support reply hypothesized the *assigned role* didn't cover the exact
data action named in the error. Rather than take that on faith, read the
role definition's `dataActions` directly:

```powershell
az role definition list --name "Cognitive Services OpenAI User" -o json
```

> [!TIP]
> The result nests `dataActions` inside `permissions[0].dataActions`, not
> as a top-level property. A naive
> `... | ConvertFrom-Json | Select-Object -ExpandProperty dataActions`
> fails — you have to drill into `permissions[0]` first.

Confirm `Microsoft.CognitiveServices/accounts/OpenAI/deployments/chat/completions/action`
is explicitly listed. In this investigation, it was — directly refuting the
support hypothesis with the role definition's own source of truth.

### Exercise 7.3: Rule Out Resource-Level and Network Blocks

```powershell
az cognitiveservices account show --name <account-name> --resource-group <rg> `
  --query "{disableLocalAuth:properties.disableLocalAuth, publicNetworkAccess:properties.publicNetworkAccess, networkAcls:properties.networkAcls, privateEndpointConnections:properties.privateEndpointConnections}" -o json
```

Two things to reason through, not just read:

* `disableLocalAuth: true` blocks **API-key** auth only — it does not
  affect the managed-identity/AAD token auth this agent actually uses.
  Don't let a `true` value here become a false lead.
* `networkAcls: null` and an empty `privateEndpointConnections` array mean
  there's no network-layer restriction blocking the call either.

### Exercise 7.4: Check Whether a Policy Is Silently Overriding What You Just Read

A property showing `"publicNetworkAccess": "Enabled"` could, in principle,
be silently overridden by an **Azure Policy with a `Modify` effect** that
you haven't spotted yet. Verify what's actually been evaluated against
this specific resource:

```powershell
az policy state list --resource "/subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<account-name>" `
  --query "[].{policy:policyDefinitionName, assignment:policyAssignmentName, complianceState:complianceState}" -o json
```

If a governance initiative in your tenant *does* contain a policy that can
force-disable public network access, check its `policyRule`'s `if` clause
for the exact resource **type and kind** it targets:

```powershell
az policy definition show --name <policy-definition-name> --management-group <mg-id> --query "policyRule" -o json
```

In this investigation, a tenant-wide policy *did* exist that force-disables
public network access — but only for the older
`Microsoft.MachineLearningServices/workspaces` (`kind == 'Hub'`) resource
type. A quick `az resource list` on the resource group confirmed **no such
resource type exists in this deployment** (it uses the newer Cognitive
Services `AIServices` account + nested `.../accounts/projects` model), so
that policy could not be the cause.

### Exercise 7.5: Check Tenant-Level Conditional Access

```powershell
az rest --method get --url "https://graph.microsoft.com/v1.0/identity/conditionalAccess/policies" -o json
```

Look for any policy whose `conditions.clientApplications` is non-null —
that's the condition that targets service principals/workload identities
specifically, as opposed to human users. In this investigation, none of
the tenant's enabled policies targeted service principals; they were all
human-user-focused (MFA, sign-in risk, security info registration).

### Exercise 7.6: Compare With the Manual-Agent Workaround

While the hosted-agent's CLI/API path kept 401ing, a **manually created**
agent in the Foundry portal — using the same identity and model deployment
— succeeded.

![Manual agent created successfully in the portal](../assets/images/manual-agent-created.png)
![Manual agent chat succeeded where the hosted agent's own invoke path 401'd](../assets/images/manual-agent-chat-success.png)
![Manual agent's MCP tool calls succeeded too](../assets/images/manual-agent-mcp-tools-success.png)

This is a powerful diagnostic signal on its own: if RBAC were genuinely
wrong, **both** paths should fail identically. A working manual path next
to a failing hosted-agent path points at something specific to the hosted
agent's own token-acquisition code path — not the customer-visible RBAC
configuration.

### Exercise 7.7: Redeploy and Verify a Fresh Runtime

Select the intended environment explicitly before deploying. In this
investigation, passing `--environment` to `azd ai agent show` still selected
the stale environment; `azd env select` corrected the target.

```powershell
azd env select air-canada-threat-assessment-poc
azd deploy threat-assessment-agent --no-prompt
azd ai agent show threat-assessment-agent --output json
azd ai agent invoke threat-assessment-agent 'Assess a simulated suspicious sign-in for user test-user@example.invalid. State clearly when live evidence is unavailable.' --version 32 --new-session --new-conversation
azd ai agent monitor threat-assessment-agent --tail 40
```

Replace `32` with the version returned by your deployment. Compare the
instance principal, model endpoint, and actual response with the failing
run. An active deployment or HTTP 200 alone does not prove success because
streaming responses can contain application errors.

The Air Canada retry produced the following evidence:

| Check | Result |
| --- | --- |
| Environment | `air-canada-threat-assessment-poc` |
| Version | `32`, active |
| Instance principal | `59a21b26-5c3a-42aa-ad7f-05fe701fb25f`, unchanged from failing v9 |
| Model call | Assessment returned without a 401 in 16.222 seconds |
| Trace ID | `30a160169657c5238a02872ddca6cf84` |
| Runtime logs | `End of processing CreateResponse request.` |

> [!WARNING]
> Historical v32 result: the assessment used the existing degraded path. Defender and
> anomaly MCP evidence was unavailable because Toolbox resolution failed.
> Model-authentication recovery does not establish end-to-end tool success.
> Conversation-history retrieval also logged a nonfatal 404. Do not close
> the wider WI-11 tool-resolution investigation based on this retry alone.

The deployed package hash differs from v9, and remote build resolves loosely
constrained dependencies. Although no source edits were made during this
retry, it is not a controlled comparison of identical runtime artifacts.
Do not attribute recovery specifically to token refresh or RBAC propagation
without further evidence.

### Exercise 7.8: Verify Operational Resolution

On September 8, [run 34178081808](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34178081808)
completed the full staging-to-production pipeline: staging 6, production 34,
eight captures, 21/21 judge checks and 28 successful MCP receipts. WI-11 is
operationally resolved for this implementation, beyond v32's partial recovery.

![Successful MCP receipts and safety refusal, rendered from artifacts](../assets/images/release-tools.png)

The fixes use the versioned MCP endpoint, RemoteTool connections, current
protocol negotiation and refreshed Entra tokens. Specialist context and
independent risk lookups restore evidence; runtime receipts verify execution.
The fixtures are synthetic. The production principal remains unchanged.
Neither a successful redeployment nor this release proves an internal Azure
cache RCA. Support request 2609040400007027 remains a historical reference;
its closure has not been verified.

## Reflection

The earlier checks justified escalating an unexplained failure, not declaring
every possible customer-side cause eliminated. Later MCP and application fixes
were separate from model authentication recovery. Read the resolution and
preserved investigation history in the project wiki:
[RBAC 401 Investigation](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/RBAC-401-Investigation).

## Knowledge Check

* Name three customer-side layers checked before escalation. Why is escalation not proof of a platform RCA?
* Why is "the portal shows the role assigned" not sufficient — what did Exercise 7.2 add on top of that?
* What single piece of evidence in Exercise 7.6 most strongly points away from an RBAC-configuration cause?

## Next Steps

Continue to [Lab 08: Production Readiness and Decision Gates](lab-08-production-readiness.md).
