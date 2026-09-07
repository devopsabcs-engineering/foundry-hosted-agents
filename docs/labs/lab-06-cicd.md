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
| `deploy-and-evaluate.yml` | Manual (`workflow_dispatch`) | Lint/unit tests → Bicep validate/what-if → staging deployment → smoke/contract tests → evaluation gate → manual production approval → source rebuild → monitoring → manual recovery on failure. |

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

The isolated staging agent has a different instance principal from the PoC.
Its initial role-assignment query returned no assignments. After deployment,
`scripts/configure-agent-rbac.sh` discovers that principal and grants only
`Foundry User` and `Cognitive Services OpenAI User` at its own account scope
through the existing RBAC module. The CI identity must be authorized to create
these role assignments; the workflow does not silently skip permission errors.

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
> variables. The September 7 investigation initially found only `staging`
> and `github-pages`. The `production` environment was then created with
> `emmanuelknafo` as required reviewer and administrator bypass disabled.
> The user subsequently approved production for run `34157050648`.
> `environment: production` alone does
> not enforce manual approval without those repository settings.
> The current promotion rebuilds source rather than promoting the exact
> tested artifact. The unsafe rollback placeholder has been removed; recovery
> is manual until a prior-version restore path is verified. These remain release blockers;
> do not treat a passing smoke test as production-readiness approval.

### Exercise 6.6: Reject False-Green Evaluations

Run [34157050648](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34157050648)
reported evaluation success even though all eight cases errored and all scores
were unavailable. Its evaluation status was `completed`, not proof of passing
quality. After manual approval, production deployment succeeded before the RBAC
step failed with `RoleAssignmentExists`. Production was therefore changed.

The corrected workflow uses `eval/run_hosted_evaluation.py` instead of trusting
the report-only action exit code. It captures fresh, version-bound hosted
responses, submits recorded output to Foundry judges, and retains exact run IDs,
raw streams, results, and a summary in `evaluation-evidence`. All cases must be
present, error-free, scored, and passing each required metric (100% by default).
Malformed datasets, empty responses, and missing scores fail the job.

Scenario text now supplies grounding context; a case ID is not evidence.
Expected schema and tool requirements remain enforced separately. Hosted prose
does not expose structured graph state or independently verified tool traces,
so those requirements cannot currently qualify a release. Category-specific
custom judge rubrics remain follow-on work, not covered by the three built-ins.

During local validation, five staging cases returned valid responses. The
prompt-injection case was rejected by Azure's jailbreak filter and correctly
blocked the run. A diagnostic evaluation of one captured response produced
passing scores for coherence, groundedness, and task adherence with no evaluator
errors, but still failed the evidence gate. This is not an eight-case quality pass.
Do not disable safety filters or weaken the dataset to obtain a green run.

The RBAC helper now reuses equivalent unconditional assignments at the exact
account scope, regardless of assignment GUID, and creates only missing roles.
Production state and version evidence are uploaded even after partial failure.
Telemetry-query failures no longer become a zero-exception success. Exception
counts alone still do not prove traffic coverage or telemetry freshness.

```bash
bash scripts/test-agent-rbac.sh
python -m pytest eval/deterministic-tests/ -q
```

## Knowledge Check

* Which pipeline would you dispatch to test a change safely before it reaches the shared PoC environment?
* What does the evaluation gate actually block from being promoted?
* What's the concurrency hypothesis for the intermittent 401s, and how would you test it?

## Next Steps

Continue to [Lab 07: Real-World Troubleshooting: RBAC 401](lab-07-troubleshooting-rbac.md).
