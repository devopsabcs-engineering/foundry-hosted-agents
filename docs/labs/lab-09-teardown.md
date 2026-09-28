---
permalink: /labs/lab-09-teardown
title: "Lab 09 - Teardown and Cost Cleanup"
description: "Preview, delete and verify removal of only your tagged learner resources."
---

[Version française](../fr/labs/lab-09-teardown)

## Overview

Allow 10-20 minutes, including Azure deletion time. Complete this lab even if
deployment or evaluation failed. Stopping an agent does not remove registry,
logging or other billable resources.

## Preserve Your Evidence

Keep the non-secret results in `.azure/workshop-evaluation/`,
`.azure/workshop-conversation/` and `.azure/workshop-load.json` locally before
deleting cloud resources. Do not commit `.azure/`: it contains environment state
and may contain connection data. Capture your environment, account, agent version
and evaluation run ID in your notes. Historical screenshots are not your evidence.

## Preview the Exact Group

Use the variables from Lab 02 in the same PowerShell session. If you lost the
session, recover your approved subscription, environment and group from your
own notes and `azd env list`; do not guess or copy an instructor's group.

```powershell
./scripts/remove-workshop.ps1 -SubscriptionId $SubscriptionId -EnvironmentName $WorkshopEnv -ResourceGroup $ResourceGroup
```

The script lists resources without deleting anything. It requires the name
`rg-<your fha-learn-* environment>` and both Lab 02 tags:
`purpose=workshop-validation` and `workshopEnv=<your environment>`.
A mismatch stops the script. Never add tags to an existing customer group to
bypass this guard. Missing tags require an ownership review with your instructor.

## Remove the Web Chat Identity

If you deployed the web chat in Lab 04, also delete its app registration and
security group. They are tenant objects, so deleting the resource group leaves them behind:

```powershell
$ChatAppId = az ad app list --display-name "$WorkshopEnv web chat" --query '[0].appId' -o tsv
if ($ChatAppId) { az ad app delete --id $ChatAppId }
$ChatGroupId = az ad group list --display-name "$WorkshopEnv-chat-users" --query '[0].id' -o tsv
if ($ChatGroupId) { az ad group delete --group $ChatGroupId }
```

## Delete and Verify

> [!CAUTION]
> Deletion removes every resource in the displayed group, including the model,
> agent project, MCP apps, images and logs. Only proceed for your disposable
> workshop group. Do not run `azd down` from a shared environment; instructors
> use the guarded procedure at the end of this lab.

```powershell
./scripts/remove-workshop.ps1 -SubscriptionId $SubscriptionId -EnvironmentName $WorkshopEnv -ResourceGroup $ResourceGroup -Delete -ConfirmResourceGroup $ResourceGroup
az group exists --subscription $SubscriptionId --name $ResourceGroup
```

Review the confirmation prompt and approve only the exact subscription/group.
Wait for completion. Success requires `Verified absent` and `false` from the
independent check, not merely acceptance of a delete request. If deletion fails,
inspect locks and policy errors with your administrator; do not remove a lock or
policy as a workaround. Rerunning after successful deletion reports `Already absent`.

Close terminals holding workshop variables. Keep local `.azure/` state until
cleanup is verified, then remove only your own learner environment folder if
you no longer need it. Never delete another environment's local state.

## Scope and Remaining Checks

Your disposable group includes the network, subnet delegations and private DNS
link from Lab 02, plus a private endpoint and checkpoint data if you ran the Cosmos
experiment. Retain approved evidence before deleting that data. Never use this
group-deletion procedure for the shared staging/production foundation or remove its
subnets independently. Service associations can delay deletion; inspect failures
with your administrator rather than deleting dependencies used by another environment.

Group deletion does not promise removal of tenant-level Entra agent identities,
GitHub OIDC credentials or soft-deleted service records. The base workshop creates
no GitHub environment; the optional web chat's app registration and group are
removed by the step above. Have an authorized tenant
administrator inspect any service-created identity retained after deletion;
do not delete shared identities or purge recoverable records without approval.
Check Cost Management later because usage charges can arrive after cleanup.

The workshop is complete when your results are recorded, limitations are named,
and your resource group is verified absent.

## Instructor Only: Tear Down the Shared Air Canada Environment

> [!WARNING]
> This removes the shared staging and production environment, including every
> agent version, the web chat pilot, container images and Cosmos data. Only the
> environment owner runs it, after exporting any evidence to keep.

The shared environment spans two resource groups:

| Resource group | Contents | Removed by |
|---|---|---|
| `rg-air-canada-threat-assessment-poc` | Foundry accounts, projects and agents; MCP and web chat container apps; registry; Cosmos DB; VNet and private DNS; monitoring | `azd down --force --purge` (azd-managed group) |
| `rg-air-canada-threat-assessment-msi` | `msi-air-canada-threat-assessment`, the GitHub OIDC identity used by every workflow | `az group delete` (not azd-managed) |

`azd down` alone is not enough: it only knows the azd-managed group, and Foundry
rejects account deletion while projects exist. `scripts/teardown-air-canada.ps1`
wraps it. The script saves an inventory, deletes Foundry projects and capability
hosts, runs `azd down --force --purge` (falling back to `az group delete`),
purges soft-deleted Foundry accounts, deletes the identity group, removes the
identity's orphaned subscription role assignments and verifies both groups are
absent. The Container Apps-managed `ME_*` groups disappear automatically.

### From Your Workstation

Run from the repository root, signed in to the Air Canada subscription, with the
local azd environment `air-canada-threat-assessment-poc`. The first command only
previews; the second deletes both groups:

```powershell
./scripts/teardown-air-canada.ps1
./scripts/teardown-air-canada.ps1 -Delete -ConfirmResourceGroups 'rg-air-canada-threat-assessment-poc,rg-air-canada-threat-assessment-msi'
```

Success requires `Verified absent` for both groups.

### From GitHub Actions

Open **Actions > Teardown Air Canada Environment > Run workflow**:

1. Preview: leave **execute** cleared, then review the job log and the
   `air-canada-teardown-inventory-<run>` artifact.
2. Delete workloads: select **execute** and set **confirm_resource_groups** to
   `rg-air-canada-threat-assessment-poc`. The `production` environment approval
   applies. The pipeline identity is kept, so you can rerun the workflow.
3. Optional final run: also select **delete_pipeline_identity** and confirm both
   groups, comma-separated. The run deletes its own identity, so it only requests
   deletion. Verify it locally:

```powershell
az group exists --name rg-air-canada-threat-assessment-msi
```

After the identity is gone, every workflow in this repository fails at Azure
sign-in until you recreate the identity, its federated credentials, roles and
repository variables. Its subscription role assignments become orphaned; remove
them with the IDs in the inventory artifact.

Tenant objects outside both groups remain: web chat app registrations, pilot
security groups and Entra agent identities. Remove them separately with tenant
administrator approval.
