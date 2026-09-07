---
permalink: /labs/lab-06-cicd
title: "Lab 06 - CI/CD: Evaluation-Gated Release Pipeline"
description: "Walk both GitHub Actions pipelines: the direct PoC pipeline and the full staging-to-production, evaluation-gated release flow."
---

> 🇫🇷 **[Version française](../fr/labs/lab-06-cicd)**

## Overview

| | |
|---|---|
| **Duration** | 35 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 05](lab-05-evaluations.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain the difference between the two pipelines in this repository and why both exist
* Trace the full staging → evaluation-gate → manual-approval → production flow
* Explain why this repository authenticates with OIDC instead of stored secrets
* Recognize a plausible cause of a real intermittent-401 symptom this project hit in CI

## Exercises

### Exercise 6.1: Two Pipelines, Two Purposes

Open [`.github/workflows/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/.github/workflows):

| Pipeline | Trigger | What it does |
|---|---|---|
| `hosted-agent-cd.yml` | Manual (`workflow_dispatch`) | Provisions and deploys **straight to the shared PoC environment**, then runs one smoke-test invoke. No staging, no evaluation gate. |
| `deploy-and-evaluate.yml` | Manual (`workflow_dispatch`) | Full release-control flow: lint/unit tests → Bicep validate/what-if → deploy an **immutable candidate to staging** → smoke/contract/streaming tests → **offline evaluation quality gate** → manual production approval → promote → post-deploy monitoring → rollback on breach. |

Both are **manual-dispatch only** — read the comment block at the top of
each file. This wasn't the original design; it's a lesson learned:
auto-firing both pipelines on every push to `main` caused them to race
concurrently against the same shared Cognitive Services account.

### Exercise 6.2: The Evaluation Gate

In `deploy-and-evaluate.yml`, find the stage that runs after "deploy
candidate to staging" and before "manual production approval." This stage
runs the deterministic checks and rubric evaluators from
[Lab 05](lab-05-evaluations.md) against the **staging candidate**, not
against production traffic. A release only reaches the manual-approval gate
if this stage passes.

### Exercise 6.3: Secretless Authentication

Both workflows authenticate via **OIDC federation** — no `AZURE_CLIENT_SECRET`
or stored credential is present anywhere in the repository. Find the
`permissions: id-token: write` block at the top of each workflow file; this
is what allows GitHub Actions to request a short-lived OpenID Connect token
that Azure trusts via a federated credential, instead of a long-lived
secret.

### Exercise 6.4: A Real Concurrency Lesson

Read the comment block at the top of `hosted-agent-cd.yml` carefully:

> Auto-firing on every push to main raced concurrently against
> `deploy-and-evaluate.yml`'s own provision/deploy cycles against the same
> Cognitive Services account, which is the likely true cause of
> intermittent `401 PermissionDenied` errors seen on hosted agent invokes.

This is a genuinely useful lesson for any CI/CD design: **two independent
pipelines writing to the same shared resource can look exactly like an
RBAC bug from the outside**, even when the role assignment itself is
correct. [Lab 07](lab-07-troubleshooting-rbac.md) shows the methodical
process for ruling this in or out.

### Exercise 6.5: Verify the Target and the Smoke-Test Contract

The September 4 run [33899929713](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/33899929713)
failed with a 401. Its deployment log also showed that the job labeled
staging deployed version 31 to the production PoC account. Staging inherited
the repository's production project variables. Retries reused the same
failed session, so they did not test a fresh runtime.

The corrected workflow selects the staging project explicitly, verifies its
endpoint before deploying, and passes that actual endpoint to evaluation.
It reads `.version` from `azd ai agent show --output json`; unknown versions
fail instead of becoming timestamp placeholders. Each smoke attempt uses
`--version`, `--new-session`, and `--new-conversation`.

The contract gate uses `azd ai agent invoke --output raw`, which returns SSE,
not JSON. It requires a non-empty text delta and a completed assistant text
response, and rejects error, failed, incomplete, malformed, and empty streams.
There is no non-empty-console-output fallback. Staging response evidence is
retained as the `staging-smoke-evidence` artifact.

Run the local regression checks before dispatching:

```bash
bash scripts/test-agent-response.sh
actionlint -shellcheck= .github/workflows/deploy-and-evaluate.yml
```

On September 7, the validator passed against a live PoC version 32 response
using the CI prompt, and rejected all 12 invalid regression cases. This
does not verify staging's CI identity or the complete GitHub Actions run.
Model responses still disclose unavailable live MCP evidence; a transport
smoke pass is not a tool-functionality or evaluation-quality pass.

> [!WARNING]
> Before running the production portion, create the `production` GitHub
> environment with required reviewers and verify its OIDC federation and
> variables. On September 7, only `staging` and `github-pages` existed;
> `environment: production` alone does not enforce manual approval.
> The current promotion rebuilds source rather than promoting the exact
> tested artifact, and the existing rollback step redeploys current source
> rather than restoring the recorded version. These remain release blockers;
> do not treat a passing smoke test as production-readiness approval.

## Knowledge Check

* Which pipeline would you dispatch to test a change safely before it reaches the shared PoC environment?
* What does the evaluation gate actually block from being promoted?
* What's the concurrency hypothesis for the intermittent 401s, and how would you test it?

## Next Steps

Continue to [Lab 07: Real-World Troubleshooting: RBAC 401](lab-07-troubleshooting-rbac.md).
