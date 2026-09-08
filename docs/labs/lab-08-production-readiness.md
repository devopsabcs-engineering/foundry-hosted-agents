---
permalink: /labs/lab-08-production-readiness
title: "Lab 08 - Production Readiness and Decision Gates"
description: "Read the PoC's production decision-gate scorecard and understand how phased experiments feed a conditional go/no-go decision."
---

> 🇫🇷 **[Version française](../fr/labs/lab-08-production-readiness)**

## Overview

| | |
|---|---|
| **Duration** | 30 minutes |
| **Level** | Advanced |
| **Prerequisites** | [Lab 07](lab-07-troubleshooting-rbac.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Explain the difference between "Pass," "Conditional," "Fail," and "Not testable in this PoC" gate statuses
* Map each production decision gate to the experiment that produced its evidence
* Explain why a PoC can honestly recommend "conditional go" instead of a clean yes/no
* Locate the executive decision deck and scorecard used to communicate this to stakeholders

## Exercises

### Exercise 8.1: The Four Experiment Tracks

Open [`experiments/`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/experiments):

| Track | Question it answers | Outcome |
|---|---|---|
| `load-testing/` | How many concurrent sessions before something breaks? | Partial — no ceiling observed at 1–20 concurrent, but the target range (10–100) wasn't fully exercised |
| `cosmos-checkpointer/` | Can the agent use Cosmos DB as durable LangGraph state? | Partial — infra deployed and a real bug was found and fixed, but live benchmarking was blocked by tenant-enforced private-only networking |
| `agent365-onboarding/` | Can this agent be registered under Entra Agent ID / Agent 365? | Blocked, but validly so — the tenant lacks Agent 365 licensing; the probe correctly stopped instead of faking success |
| `continuous-evaluation/` | Can production traffic be continuously evaluated? | Blocked by a fixable RBAC gap (missing `Foundry User` role on the project's managed identity for dataset listing) |

Open `experiments/load-testing/report.md` and find its **"Honest scope
statement"** section — note how it explicitly states what was *not*
tested, rather than silently extrapolating from a smaller sample.

### Exercise 8.2: Read the Scorecard

Open [`deliverables/production-decision-gate-scorecard.md`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/deliverables/production-decision-gate-scorecard.md)
and find the status legend:

| Status | Meaning |
|---|---|
| **Pass** | Evidence collected in this PoC directly satisfies the gate |
| **Conditional** | Partial evidence exists; a specific, named follow-up closes the gap |
| **Fail** | Evidence collected contradicts or fails the gate as tested |
| **Not testable in this PoC** | Requires a separate commercial/legal/platform confirmation (pricing, SLA, tenant licensing) |

Find the **Quality** gate row — this is the only gate marked **Pass**
outright. Trace its evidence pointer back to the exact artifacts from
[Lab 05](lab-05-evaluations.md): the golden dataset and strict policy gate,
then run 34178081808's eight captures, 21/21 judge checks, verified injection
refusal and 28 tool receipts. This is a pass for the synthetic suite, not
statistical proof of security efficacy on real customer data.

### Exercise 8.3: Why "Conditional Go," Not a Clean Yes/No

Read the scorecard's **Overall recommendation** section. It recommends a
**conditional go for continued PoC-to-pilot investment**, explicitly gated
on:

1. Named security, data and operations owners, including public MCP ingress and authorization review.
2. Extended load testing with working MCP calls and a rehearsed manual recovery path.
3. Formal commercial/SLA/pricing confirmation and preview acceptance.
4. Re-tests of continuous evaluation, Cosmos and Agent 365 only if retained in the pilot design.

WI-11 is now operationally resolved and the complete release pipeline passed;
it is no longer listed as an open pilot blocker.

This is a deliberately honest pattern: a PoC's job is to **separate what's
proven from what still needs proving**, not to manufacture false
confidence in either direction.

### Exercise 8.4: The Executive Deck

Open [`deliverables/deck-outline.md`](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/deliverables/deck-outline.md)
and its **Confidence Tagging Legend**:

| Tag | Meaning |
|---|---|
| `confirmed` | Directly established by product documentation, samples, or this PoC's own testing |
| `preview` | Documented but explicitly a preview/beta capability |
| `inferred` | Synthesized from separately-confirmed facts not yet observed working together |
| `requires-validation` | Documented, but a limit, SLA, price, or integration path is unverified |

Every claim in the compiled deck
(`deliverables/air-canada-foundry-hosted-agents-decision.pptx`, generated
by `scripts/build-deck.js`) carries one of these four tags — a pattern you
can reuse any time you need to present technical findings to a
non-technical stakeholder audience without overstating certainty.

## Knowledge Check

* Which gate is the only one marked "Pass" outright, and what evidence backs it?
* Why did the Agent 365 onboarding experiment count as a valid outcome even though it was "blocked"?
* What are the four confidence tags used in the executive deck, and what's the difference between `inferred` and `requires-validation`?

## Workshop Wrap-Up

You've now taken one PoC from architecture, through deployment, invocation,
evaluation, verified CI/CD, a resolved troubleshooting investigation, and finally
to an honest production-readiness recommendation. The full source for
everything in this workshop lives in
[`devopsabcs-engineering/foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents) —
fork it, and the [wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki)
preserves the WI-11 history, current release proof and remaining readiness gaps.
