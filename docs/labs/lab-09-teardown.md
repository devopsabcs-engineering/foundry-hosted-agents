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

## Delete and Verify

> [!CAUTION]
> Deletion removes every resource in the displayed group, including the model,
> agent project, MCP apps, images and logs. Only proceed for your disposable
> workshop group. Do not run `azd down` from a shared environment.

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

Group deletion does not promise removal of tenant-level Entra agent identities,
GitHub OIDC credentials or soft-deleted service records. The base workshop creates
no GitHub environment or web-chat app registration. Have an authorized tenant
administrator inspect any service-created identity retained after deletion;
do not delete shared identities or purge recoverable records without approval.
Check Cost Management later because usage charges can arrive after cleanup.

The workshop is complete when your results are recorded, limitations are named,
and your resource group is verified absent.
