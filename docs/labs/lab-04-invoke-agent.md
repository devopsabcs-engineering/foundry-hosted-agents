---
permalink: /labs/lab-04-invoke-agent
title: "Lab 04 - Invoke the Agent and Read Traces"
description: "Invoke the hosted agent from the CLI and the portal, and read its Application Insights traces."
---

> 🇫🇷 **[Version française](../fr/labs/lab-04-invoke-agent)**

## Overview

| | |
|---|---|
| **Duration** | 30 minutes |
| **Level** | Intermediate |
| **Prerequisites** | [Lab 03](lab-03-deploy-agent.md) |

## Learning Objectives

By the end of this lab, you will be able to:

* Invoke a hosted agent from the CLI and from the Foundry Playground
* Read a multi-agent trace and identify which specialist node produced which part of the answer
* Explain the difference between the CLI invoke path and the portal Playground path
* Recognize a healthy response versus a degraded (tool-unavailable) response

## Exercises

### Exercise 4.1: Invoke from the CLI

```powershell
azd ai agent show
azd ai agent invoke "Suspicious login from unknown IP 203.0.113.45 targeting the crew-scheduling admin portal at 02:14 UTC, followed by three failed MFA attempts and a successful login four minutes later from the same IP."
```

`azd ai agent show` prints the agent's name, current version, model, and
endpoint. `invoke` sends one message through the Responses protocol and
prints the final report.

### Exercise 4.2: Invoke from the Foundry Playground

Open the agent's **Playground** tab in the Foundry portal and send the
same prompt. The Playground's live **Log stream** surfaces the underlying
Python process's stdout — useful for seeing exactly which specialist node
ran and in what order.

![Foundry portal live chat response](../assets/images/07-foundry-portal-live-chat-response.png)

### Exercise 4.3: Read the Trace

Open **Application Insights** → **Application Map** or **Transaction
search** for the agent's resource group.

![Foundry agent traces view](../assets/images/foundry-agent-traces.png)

Find the trace for your invocation and identify:

1. The **supervisor** dispatch decision (which specialist ran first).
2. The **Evidence Investigator**'s tool call to `defender-conn`.
3. The **Risk Analyst**'s tool call to `anomaly-conn`.
4. The **Report Composer**'s final synthesis span — note it has no
   outbound tool-call spans, consistent with Lab 01's tool-isolation design.

### Exercise 4.4: Recognize a Degraded Response

Compare the golden-dataset example `miss-001` (from
`eval/golden-dataset.jsonl`) — "Defender telemetry is unavailable" — with a
normal response. A degraded response should:

* Never claim the host is clean when data is missing.
* Explicitly state the data gap in a **Limitations** section.
* Still return HTTP 200 / a valid report — not crash the request.

This is the `evidence_tool_unavailable` flag from
[Lab 01](lab-01-architecture.md) surfacing in the actual report text.

## Knowledge Check

* What's the fastest way to see *which specialist node* handled a given request — the CLI response, or the trace?
* What should a report say when the Evidence Investigator's tool is unavailable, and what should it never say?

## Next Steps

Continue to [Lab 05: Evaluations](lab-05-evaluations.md).
