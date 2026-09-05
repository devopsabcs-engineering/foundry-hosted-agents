---
layout: default
title: Home
nav_order: 0
permalink: /
---

> 🇫🇷 **[Version française](fr/)**

# Foundry Hosted Agents Workshop

Welcome to the **Foundry Hosted Agents Workshop** — a hands-on, progressive
workshop built directly from a real proof of concept: hosting a
**LangGraph multi-agent threat-assessment system** on
**Microsoft Foundry Hosted Agents**, backed by independent MCP tool
servers running on Azure Container Apps.

You will deploy the MCP tool servers, provision a Foundry project and a
hosted agent, invoke it, gate it with deterministic and LLM-as-judge
evaluations, walk the CI/CD pipeline that promotes a candidate to
production, and — uniquely — learn a real, still-open platform
troubleshooting investigation using nothing but the Azure CLI.

> [!NOTE]
> This workshop is built from the
> [`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents)
> repository — every command, screenshot, and log excerpt in these labs
> comes from that real deployment, not a simulation.

## Who Is This For?

| Audience | What You Will Learn |
|---|---|
| **AI / platform engineers** | Deploy a multi-agent LangGraph system on Foundry Hosted Agents end to end |
| **DevOps engineers** | Wire evaluation-gated CI/CD pipelines around an agent deployment |
| **Solution architects** | Compare Foundry Hosted Agents against self-hosted LangGraph/LangSmith options |
| **Support / SRE engineers** | Learn a methodical Azure RBAC/permission-troubleshooting workflow |

## Prerequisites

Before starting Lab 00, ensure you have the following:

- [Visual Studio Code](https://code.visualstudio.com/) (latest stable)
- [Python](https://www.python.org/) 3.13
- [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd)
- [Azure CLI (`az`)](https://learn.microsoft.com/cli/azure/install-azure-cli)
- An Azure subscription with access to Microsoft Foundry and `gpt-4o-mini` model quota
- A [GitHub account](https://github.com/) with GitHub Copilot access (optional, used in Lab 01)

## Labs

| # | Lab | Duration | Level |
|---|-----|----------|-------|
| 00 | [Prerequisites and Environment Setup](labs/lab-00-setup.md) | 20 min | Beginner |
| 01 | [Architecture Deep Dive](labs/lab-01-architecture.md) | 30 min | Beginner |
| 02 | [Deploy the MCP Tool Servers](labs/lab-02-mcp-servers.md) | 30 min | Intermediate |
| 03 | [Provision and Deploy the Hosted Agent](labs/lab-03-deploy-agent.md) | 35 min | Intermediate |
| 04 | [Invoke the Agent and Read Traces](labs/lab-04-invoke-agent.md) | 30 min | Intermediate |
| 05 | [Evaluations: Deterministic + LLM-as-Judge](labs/lab-05-evaluations.md) | 40 min | Intermediate |
| 06 | [CI/CD: Evaluation-Gated Release Pipeline](labs/lab-06-cicd.md) | 35 min | Advanced |
| 07 | [Real-World Troubleshooting: RBAC 401](labs/lab-07-troubleshooting-rbac.md) | 40 min | Advanced |
| 08 | [Production Readiness and Decision Gates](labs/lab-08-production-readiness.md) | 30 min | Advanced |

## Workshop Schedule

### Half-Day (3 hours)

| Time | Activity |
|------|----------|
| 0:00 – 0:20 | Lab 00: Prerequisites |
| 0:20 – 0:50 | Lab 01: Architecture Deep Dive |
| 0:50 – 1:20 | Lab 02: Deploy the MCP Tool Servers |
| 1:20 – 1:55 | Lab 03: Provision and Deploy the Hosted Agent |
| 1:55 – 2:10 | Break |
| 2:10 – 2:40 | Lab 04: Invoke the Agent and Read Traces |
| 2:40 – 3:00 | Lab 05: Evaluations (start) |

### Full-Day (6 hours)

| Time | Activity |
|------|----------|
| 0:00 – 3:00 | Half-Day labs (as above) |
| 3:00 – 3:15 | Break |
| 3:15 – 3:40 | Lab 05: Evaluations (continued) |
| 3:40 – 4:15 | Lab 06: CI/CD Pipeline |
| 4:15 – 4:55 | Lab 07: Real-World Troubleshooting: RBAC 401 |
| 4:55 – 5:10 | Break |
| 5:10 – 5:40 | Lab 08: Production Readiness and Decision Gates |
| 5:40 – 6:00 | Wrap-up and Q&A |

## Delivery Tiers

| Tier | Labs | Duration | Audience |
|---|---|---|---|
| **Half-Day** | Labs 00 – 05 (start) | ~3 hours | First exposure to Foundry Hosted Agents |
| **Full-Day** | Labs 00 – 08 | ~6 hours | End-to-end deployment, evaluation, CI/CD, and troubleshooting |

## Getting Started

1. Clone or fork the [`foundry-hosted-agents`](https://github.com/devopsabcs-engineering/foundry-hosted-agents) repository.
2. Complete [Lab 00: Prerequisites](labs/lab-00-setup.md) to set up your environment.
3. Work through the labs in order — each lab builds on the previous one.

> **Tip**: Labs 02–04 use resources that are already deployed for this
> workshop (MCP servers, Foundry project). If you're running your own
> environment, Lab 03 shows you how to provision everything from scratch
> with `azd`.

## Slide Deck

A companion slide deck (English and French) is available for instructor-led
delivery:

- [Workshop overview deck — English (PPTX)](assets/decks/foundry-hosted-agents-workshop-en.pptx)
- [Deck d'aperçu de l'atelier — Français (PPTX)](assets/decks/foundry-hosted-agents-workshop-fr.pptx)

## Related Resources

| Resource | Description |
|------------|-------------|
| [`foundry-hosted-agents` repository](https://github.com/devopsabcs-engineering/foundry-hosted-agents) | Full PoC source code, infra, evaluation suite, and CI/CD pipelines |
| [Project wiki](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki) | Architecture notes, manual-agent workaround, RBAC 401 investigation log |
| [Decision deliverables](https://github.com/devopsabcs-engineering/foundry-hosted-agents/tree/main/deliverables) | Production decision-gate scorecard and executive decision deck |

## License

This project is licensed under the [MIT License](https://github.com/devopsabcs-engineering/foundry-hosted-agents/blob/main/LICENSE).
