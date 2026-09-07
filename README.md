---
title: Air Canada Threat and Vulnerability Assessment Agent - Foundry Hosted Agents PoC
description: LangGraph hosted-agent proof of concept with isolated staging MCP fixtures and evaluation gates.
---

A proof of concept that hosts a LangGraph multi-agent threat-assessment workflow on **Microsoft Foundry Hosted Agents**, backed by two independent MCP tool servers (mocked Microsoft Defender and anomaly-detection data). The PoC evaluates Foundry Hosted Agents as a deployment target for Air Canada's existing LangGraph prototype and produces a decision-ready comparison against self-hosted LangGraph/LangSmith options.

📖 **Full investigation notes, RBAC troubleshooting, and manual-agent workaround live in the project [wiki](../../wiki):**
[Home](../../wiki/Home) · [Architecture](../../wiki/Architecture) · [Manual Agent Workaround](../../wiki/Manual-Agent-Workaround) · [RBAC 401 Investigation](../../wiki/RBAC-401-Investigation)

🎓 **A hands-on, bilingual (EN/FR) workshop built from this PoC — 9 labs plus a companion slide deck — is published at
[devopsabcs-engineering.github.io/foundry-hosted-agents](https://vigilant-guacamole-y8qe3rw.pages.github.io/)**
(source in [`docs/`](docs); requires sign-in since this repo is internal).

## Architecture

```mermaid
flowchart LR
    subgraph Foundry["Microsoft Foundry Project"]
        Agent["threat-assessment-agent\n(hosted agent, Responses protocol)"]
        Model["gpt-4o-mini deployment"]
        Agent --> Model
    end

    subgraph Graph["LangGraph supervisor graph (src/threat-assessment-agent)"]
        Supervisor((supervisor)) --> Investigator[Evidence Investigator]
        Supervisor --> Analyst[Risk Analyst]
        Supervisor --> Composer[Report Composer]
        Investigator --> Supervisor
        Analyst --> Supervisor
        Composer --> Supervisor
    end

    Agent --> Supervisor

    subgraph Toolbox["Foundry Toolbox (security-tools)"]
        DefenderConn["defender-conn"]
        AnomalyConn["anomaly-conn"]
    end

    Investigator -.MCP.-> DefenderConn
    Analyst -.MCP.-> AnomalyConn

    DefenderConn --> DefenderServer["mcp/defender-server\n(Container App)"]
    AnomalyConn --> AnomalyServer["mcp/anomaly-server\n(Container App)"]
```

* **Supervisor + specialists** — `graph.py` compiles a LangGraph `StateGraph` where a supervisor routes to three specialist nodes (Evidence Investigator, Risk Analyst, Report Composer) and only proceeds to reporting once both evidence and risk analysis are complete.
* **Tool isolation by role** — each specialist is restricted to a single Foundry Toolbox connection (Evidence Investigator → `defender-conn`, Risk Analyst → `anomaly-conn`); the Report Composer has no tool access and only synthesizes.
* Specialists use the authenticated, version-pinned toolbox MCP endpoint through [toolbox.py](src/threat-assessment-agent/toolbox.py), with exact read-only tool allowlists. Connections must use the ARM `RemoteTool` category; `GenericHttp` with anonymous authentication fails toolbox resolution. The obsolete per-agent tool-resolution API is no longer used.
* **MCP servers run independently** of the agent process — `mcp/defender-server` and `mcp/anomaly-server` are separate FastMCP apps, each deployed as its own Azure Container App and reached only via the Foundry Toolbox `remote-tool` connections declared in `azure.yaml`.

## Repository layout

| Path | Purpose |
|---|---|
| [`azure.yaml`](azure.yaml) | `azd` project manifest: Foundry project, model deployment, Toolbox connections, and the hosted agent service definition. |
| [`src/threat-assessment-agent/`](src/threat-assessment-agent) | The LangGraph agent: `graph.py` (supervisor + specialist nodes), `state.py` (graph state schema, optional Cosmos DB checkpointer extension point), `main.py` (Foundry Responses-protocol host entry point), `tests/`. |
| [`mcp/defender-server/`](mcp/defender-server) | Mocked Microsoft Defender MCP tool server (`get_device_risk`, `list_vulnerabilities`). |
| [`mcp/anomaly-server/`](mcp/anomaly-server) | Mocked anomaly-detection MCP tool server (`score_anomaly`, `detect_login_anomalies`). |
| [`infra/`](infra) | Bicep infrastructure: `main.bicep` composes `modules/ai-foundry.bicep`, `modules/monitoring.bicep`, `modules/rbac.bicep`, and `modules/mcp-container-apps.bicep`. `modules/cosmos-db.bicep` is a standalone, optional module used only by the Cosmos checkpointer experiment. |
| [`eval/`](eval) | Evaluation suite gated against `golden-dataset.jsonl`: `deterministic-tests/` (non-LLM schema/policy checks) and `rubrics/` (built-in Foundry evaluators plus custom LLM-as-judge rubrics — see [`eval/rubrics/README.md`](eval/rubrics/README.md)). |
| [`.github/workflows/`](.github/workflows) | `hosted-agent-cd.yml` (manual provision/deploy/smoke-test straight to the PoC environment) and `deploy-and-evaluate.yml` (lint → Bicep validate → staging deploy → smoke/contract/streaming tests → offline evaluation quality gate → manual production promotion). |
| [`experiments/`](experiments) | Phase 7 production-readiness probes: `load-testing/` (concurrent-session and cold-start measurements), `cosmos-checkpointer/` (optional persistent-state extension validation), `agent365-onboarding/` (Entra Agent ID / Agent 365 licensing probe), `continuous-evaluation/` (scheduled evaluation rule deployment). |
| [`deliverables/`](deliverables) | Decision materials for the engagement: `production-decision-gate-scorecard.md`, `deck-outline.md`, and the compiled `air-canada-foundry-hosted-agents-decision.pptx`. |
| [`docs/`](docs) | Bilingual (EN/FR) GitHub Pages workshop built from this PoC: `index.md` + `labs/` (English), `fr/` (French mirror), and `assets/decks/` (companion PPTX decks, generated by `scripts/build-workshop-deck.js`). |
| [`scripts/`](scripts) | `build-deck.js` (generates the decision deck via vendored `pptxgenjs`) and `test_mcp_servers.py` (ad hoc smoke probe against the deployed MCP Container Apps). |

## Getting started

### Prerequisites

* [Azure Developer CLI (`azd`)](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) with the Foundry extension: `azd ext install microsoft.foundry`
* Python 3.13
* An Azure subscription with access to Microsoft Foundry and a `gpt-4o-mini` model quota

### Provision and deploy

```powershell
azd auth login
azd env new air-canada-threat-assessment-poc
azd provision
azd deploy
```

### Run and test the agent

```powershell
azd ai agent show
azd ai agent invoke "Hello from local testing. Reply with a short confirmation that you are running and ready to assess threats."
```

### Local development

```powershell
python -m venv .venv
./.venv/Scripts/Activate.ps1
pip install -r src/threat-assessment-agent/requirements.txt -r src/threat-assessment-agent/requirements-dev.txt
pytest src/threat-assessment-agent/tests/ -v
```

## Evaluation

The golden scenarios use explicit synthetic device/account identifiers and matching mock records.
Unknown identifiers return missing-data results, not invented anomalies or evidence of safety.
The original incident accompanies each specialist handoff. Final-report task adherence uses
the Report Composer's actual instructions; deterministic checks separately enforce specialist
receipts, allowed connections, citations, and safety policy. All eight cases and the 100% gate remain.
Passing these fixtures demonstrates workflow behavior, not real Defender detection accuracy.

* **Deterministic checks** (`eval/deterministic-tests/`): schema validity, required citations, forbidden phrases, allowed-tool-call policy, degraded-mode policy, and conflict acknowledgement — run with `pytest eval/deterministic-tests/`.
* **Rubric-based / LLM-as-judge evaluation** (`eval/rubrics/`): built-in Foundry evaluators (coherence, groundedness, task adherence, tool-call accuracy) plus custom rubrics for triage correctness, evidence-citation quality, and conflicting-signal handling — see [`eval/rubrics/README.md`](eval/rubrics/README.md) for the full gating-criterion mapping.

## CI/CD

* **`hosted-agent-cd.yml`** — manual-dispatch pipeline that provisions and deploys straight to the shared PoC environment, then runs a smoke-test invoke.
* **`deploy-and-evaluate.yml`** — manual-dispatch, eval-gated release flow: lint and unit tests → Bicep validate/what-if → deploy an immutable candidate to staging → smoke/contract/streaming tests → offline evaluation quality gate → manual production approval → promote.

Both workflows authenticate via secretless OIDC federation (no stored client secrets).

The staging release workflow builds MCP images from the selected commit and pins them by digest.
Staging uses dedicated `mcp-staging-*` Container Apps and an image-pull identity, leaving the
existing `mcp-*` production apps unchanged. It rejects shared MCP URLs before deploying the agent.
Production approval remains manual. Before promotion, review the production MCP image references
and toolbox version together with the agent candidate; staging fixture changes are not automatically
promoted to production tools.

## Known issues

WI-11 (a persistent `401 PermissionDenied` on Azure OpenAI calls from the hosted agent's Instance Identity, confirmed as a platform-side bug with RBAC configuration verified correct) is tracked via Azure support request `2609040400007027`. Full diagnostic history is in the wiki's [RBAC 401 Investigation](../../wiki/RBAC-401-Investigation) page.

