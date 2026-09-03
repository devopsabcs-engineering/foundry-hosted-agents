<!-- markdownlint-disable-file -->
# Deck Outline: Air Canada Foundry Hosted Agents Decision and Multi-Agent PoC

Source document for `scripts/build-deck.js`. All content below is transcribed from `.copilot-tracking/research/2026-09-03/air-canada-foundry-hosted-agents-research.md` (cited as "research.md" below); no figures, comparisons, or gate criteria are invented here.

## Confidence Tagging Legend

Every claim below carries one of four tags, mapped from the Evidence Confidence Register (research.md Lines 554-570):

| Tag | Meaning | Register wording that maps to this tag |
|---|---|---|
| `confirmed` | Directly established by product documentation, official samples, or the register's "Confirmed" wording | "Confirmed by product documentation and samples", "Confirmed LangGraph pattern", "Confirmed", "Confirmed for basic multi-turn use" |
| `preview` | Documented but explicitly a preview/beta capability | "Sampled but preview", "Documented but preview" |
| `inferred` | Synthesized from two or more separately-confirmed facts that have not been observed working together | "Package confirmed; Hosted Agent pairing untested", "Partially evidenced, exact path unverified" |
| `requires-validation` | Mechanism or pattern is documented, but a limit, SLA, price, or integration path is unverified and must be proven in the PoC | "Confirmed mechanism; limits and SLA unknown", "Documented pattern; private path untested", "Not verified", "Insufficient current evidence" |

Any figure that is not directly confirmed (pricing, exact quotas, SLA numbers) is rendered on-slide as **"unknown / TBD — see appendix"**, never as a fabricated number.

## Title Slide

* **Title**: Air Canada — Foundry Hosted Agents Decision and Multi-Agent PoC
* **Subtitle**: Executive decision deck — LangGraph hosting options, phased PoC recommendation, and production-readiness gates
* Confidence banner note (rendered small, bottom of slide): "Every claim on this deck is labeled confirmed / preview / inferred / requires-validation — see Appendix B."
* Source: research.md (Lines 1-6, task framing)

---

## Core Slide 1 — Decision Required

**Objective**: Frame the single decision Air Canada must make: select a reusable hosting blueprint for LangGraph agents.

* Decision framing: adopt, validate, or defer a hosting blueprint for future LangGraph agents — `confirmed` (this is the stated task framing, not a technical claim). Source: research.md (Lines 535-537, storyboard slide 1)
* Position: Foundry Hosted Agents is the **leading PoC candidate**, not yet an unconditional production selection — `confirmed` (explicit framing repeated throughout research.md, e.g. Line 5, Line 420). Source: research.md (Line 5; Lines 535-537)
* This deck separates what today's evidence proves from what the PoC must still prove — `confirmed` (deck's own stated method). Source: research.md (Lines 27-32, Success Criteria)

---

## Core Slide 2 — Air Canada's Requirements

**Objective**: Show the ten enterprise capabilities the PoC must prove.

* The ten capabilities: scaling, MCP tools, multi-agent behavior, evaluations, CI/CD, streaming, state, governance, cost, and production readiness — `confirmed` (directly enumerated in storyboard). Source: research.md (Lines 538-539, storyboard slide 2)
* These map 1:1 to the Production Decision Gates categories used later in the deck — `confirmed` (cross-reference within research.md). Source: research.md (Lines 572-583)

---

## Core Slide 3 — Product Landscape (Five Operating Models)

**Objective**: Separate five materially different operating models without conflating open-source LangGraph and paid LangSmith topologies.

* Model 1 — OSS LangGraph on customer-managed Azure compute (Container Apps / App Service / AKS): Air Canada owns runtime, queueing, scaling, persistence, recovery — `confirmed` (documented scenario). Source: research.md (Lines 326-340, Scenario A1)
* Model 2 — LangSmith Deployment Cloud: LangChain operates Agent Server; separate SaaS billing/control plane — `confirmed`. Source: research.md (Lines 342-354, Scenario A2)
* Model 3 — LangSmith self-hosted Enterprise on Azure: Enterprise license + customer-operated Kubernetes/Postgres/Redis/ClickHouse; Azure BYOC listed only as "planned for 2H 2026" — `requires-validation` (roadmap statement, not a release commitment). Source: research.md (Lines 356-369, Scenario A3)
* Model 4 — Foundry Hosted Agent baseline (Basic Agent Setup): Foundry operates session compute; Air Canada owns graph code; no Cosmos DB, no Agent 365 — `confirmed` mechanism, `requires-validation` for limits. Source: research.md (Lines 371-392, Scenario B)
* Model 5 — Phased Foundry target: baseline plus evidence-gated optional extensions (Cosmos DB, Agent 365, continuous evaluation, A2A) — `confirmed` as a design pattern; each extension individually `requires-validation`. Source: research.md (Lines 394-416, Scenario C)
* Full dimension-by-dimension comparison lives in Appendix A. Source: research.md (Lines 489-506)

---

## Core Slide 4 — Recommendation

**Objective**: Run a phased Foundry PoC with explicit go/no-go gates; separate the stable baseline from optional extensions.

* Recommended baseline: one hosted deployment with a genuine LangGraph supervisor + specialist-agent graph, Responses SSE, external MCP via Foundry connections/Toolbox, Application Insights, offline evaluations — `confirmed` as an architecture pattern (component-level confidence detailed on Slides 5-9). Source: research.md (Line 418, Selected approach)
* Cosmos DB, Agent 365, continuous evaluation, and a second A2A-hosted agent are **separate, individually gated experiments** — not baseline dependencies — `confirmed` framing. Source: research.md (Lines 394-416, Scenario C; Line 418)
* Why not the other four models: OSS LangGraph = highest engineering burden; LangSmith Cloud = separate SaaS/billing dependency; LangSmith Enterprise = licensing + highest ops burden; Microsoft Agent Framework not selected because Air Canada has an existing LangGraph investment — `confirmed` rationale. Source: research.md (Lines 469-475, Considered Alternatives)

---

## Core Slide 5 — Runtime Architecture (Multi-Agent)

**Objective**: Show genuine multi-agent behavior in one deployment; A2A shown only as a dashed future boundary.

* Graph composition: Supervisor → Evidence Investigator + Risk Analyst → Report Composer, all inside one hosted LangGraph deployment — `confirmed` LangGraph pattern. Source: research.md (Lines 420-421, 428-437 diagram + Implementation Details)
* Each role has separate prompts, tool permissions, state contracts, and evaluation criteria despite sharing one deployment — `confirmed`. Source: research.md (Line 429)
* Cross-deployment A2A delegation to a second hosted agent is a **preview** experiment, justified only by independent ownership/release/isolation/scaling needs — not a baseline requirement — `preview`. Source: research.md (Line 431, 559 register row)
* No documented hard limit on graph node count or depth; the practical constraint is per-session sandbox CPU/memory, which two Microsoft doc pages state inconsistently (0.5-2 vCPU fixed vs. 0.25-4.0 vCPU continuous) — `requires-validation`. Source: research.md (Lines 386-388, Scenario B Limitations)

---

## Core Slide 6 — Tools and MCP

**Objective**: Separate implementation, hosting, registration, and consumption into four distinct layers.

* Layer 1 — Implementation: custom MCP server code (Defender tools, Anomaly tools) — `confirmed` requirement. Source: research.md (Lines 424-427, 430)
* Layer 2 — Hosting: independent Azure runtime such as Container Apps, Functions, or App Service; still needs its own auth, networking, versioning, health checks, throttling — `confirmed` requirement, ownership responsibilities explicit. Source: research.md (Line 430)
* Layer 3 — Registration: Foundry connections define endpoint and credential policy per MCP server — `confirmed` pattern; **private-path reachability untested** — `requires-validation`. Source: research.md (Line 430)
* Layer 4 — Consumption: Foundry Toolbox aggregates registered tools for reuse across one or more agents; LangGraph consumes via supported client libraries — `confirmed` pattern; `requires-validation` for private connectivity. Source: research.md (Line 430)
* Toolbox is the registration/aggregation layer, **not** the hosting runtime for custom MCP server code — a documented distinction to avoid at architecture review — `confirmed`. Source: research.md (Line 430)

---

## Core Slide 7 — State and History

**Objective**: Choose one runtime source of truth; compare Responses history, application-owned Cosmos checkpoints, and Standard Agent Setup capability hosts.

* Option 1 — Foundry Responses history: platform-managed conversation history; sufficient for basic multi-turn interaction; no Cosmos DB required — `confirmed` for basic multi-turn use. Source: research.md (Line 556 register row; Lines 373-374)
* Option 2 — Application-owned Cosmos DB LangGraph checkpointer (`langchain-azure-cosmosdb`, `CosmosDBSaver`): becomes authoritative graph state only when durable checkpoints, human-in-the-loop pause/resume, time travel, or app-controlled state are required — package co-maintained by LangChain and Microsoft is `confirmed`; **Hosted Agent pairing is untested** — `inferred`. Source: research.md (Line 557 register row; Lines 397-400)
* Option 3 — Standard Agent Setup via `capabilityHosts` (BYO Cosmos DB / Storage / AI Search): needed only for data-residency/compliance, a separate Bicep setup tier from Basic Agent Setup — `confirmed` as a documented resource pattern. Source: research.md (Lines 313-320, Bicep resource types table)
* No user-scoped conversation-list API was found in the researched documentation — an evidence gap, not proof of absence — `requires-validation`. Source: research.md (Lines 380-381)
* A sidebar can store metadata/identifiers without duplicating message bodies; duplicate-content compliance requirements need explicit retention/deletion/legal-hold design — `confirmed` design guidance. Source: research.md (state design pattern discussion, Key Discoveries section)

---

## Core Slide 8 — Scaling and Cost

**Objective**: Show that the scaling *model* is understood, but capacity and price are not yet quantified — unknowns stay visible.

* Scaling model: per-session isolation (each session = its own VM-isolated sandbox), not per-replica; idle timeout 5-60 min (default 15) triggers scale-to-zero with automatic state restore — `confirmed` mechanism. Source: research.md (Lines 388, Scaling/cost model discovery)
* Billing model: vCPU-hour + GiB-hour of active session compute only — closest to Azure Container Apps consumption plan, not AKS always-on or App Service continuous billing — `confirmed` mechanism.
* **Unknown / TBD**: exact $/vCPU-hr and $/GiB-hr rates (public pricing page showed "N/A" at research time); maximum concurrent sessions; requests-per-second ceiling; same-thread turn concurrency; cold-start latency distribution — `requires-validation`. Source: research.md (Line 570 register row; Lines 576-577, Production Decision Gates — Scale and Cost)
* Known cost drivers (formulas, not totals): model tokens, active session vCPU/memory, idle window, MCP hosting, telemetry, evaluation tokens, optional Cosmos DB and Agent 365 licensing, operations labor — `confirmed` as a driver list; amounts `requires-validation`. Source: research.md (Lines 578-579, Production Decision Gates — Cost)
* Full load-test matrix in Appendix E. Source: research.md (Line 620, Increment 4 — Load & Scale Gate)

---

## Core Slide 9 — Evaluation

**Objective**: Gate production releases on security-task outcomes, not generic fluency.

* Baseline: offline evaluation of versioned candidate outputs against a human-reviewed golden dataset (true positives, false positives, ambiguous evidence, missing data, conflicting tools, prompt injection, unauthorized actions, unsupported conclusions) — `confirmed`. Source: research.md (Lines 508-511, Evaluation Strategy)
* Deterministic checks: schema validity, required citations, allowed tool calls, policy constraints — `confirmed`. Source: research.md (Line 511)
* Model-based evaluators: relevance, groundedness, task adherence, rubric scoring — `confirmed` (built-in evaluator catalog exists). Source: research.md (Line 511; Line 298, evaluator catalog)
* Human review required for high-impact vulnerability conclusions and any recommendation triggering remediation or operational change — `confirmed` policy requirement. Source: research.md (Line 512)
* Continuous evaluation of sampled production traffic is a **separate preview and privacy decision** — redaction and retention must be defined before enabling — `preview`. Source: research.md (Line 513; Line 566 register row)
* GitHub Action (`microsoft/ai-agent-evals@v3-beta`) targeting the deployed hosted-agent name/version, and portal visibility of action-created runs — `requires-validation` (not verified in research). Source: research.md (Line 567 register row)

---

## Core Slide 10 — Automation (CI/CD)

**Objective**: Evaluate every candidate before production traffic moves; show the full staging-to-rollback pipeline.

* Pipeline stages: lint/unit tests/dependency scan → Bicep validate + what-if → deploy immutable candidate to staging → smoke/contract/streaming tests → offline evaluation quality gate → manual production approval → deploy production version → canary/explicit route switch → post-deploy checks/monitoring → rollback route to prior version on breach — `confirmed` documented pattern. Source: research.md (Lines 518-533, CI/CD and Release Control diagram)
* Bicep provisions infrastructure; `azd` or Foundry APIs deploy agent versions as a **separate lifecycle** from infrastructure changes — `confirmed`. Source: research.md (Line 533)
* Evaluations run against a non-production candidate before traffic promotion; continuous evaluation (if approved) monitors production after release and does **not** replace the release gate — `confirmed` policy. Source: research.md (Line 533)

---

## Core Slide 11 — Governance and Readiness

**Objective**: Separate confirmed identity/RBAC controls from validation tracks and open blockers.

* Confirmed baseline controls: each hosted agent gets an auto-created, dedicated Entra ID identity at deploy time (no manual managed-identity wiring); Foundry RBAC role family (Foundry User / Foundry Project Manager / Foundry Account Owner / Foundry Owner / Foundry Agent Consumer); Application Insights / OpenTelemetry tracing — `confirmed`. Source: research.md (Lines 300-306, RBAC roles table; explicit identity discovery discussion)
* Explicit warning carried from research: don't assign `Cognitive Services *` roles to a CI/CD identity — Foundry has its own role family for this — `confirmed` documented guidance. Source: research.md (Lines 300-306)
* Agent 365 governance/registry onboarding: Agent 365 and Entra Agent ID are GA; SDK packages exist for Foundry tooling and LangChain observability — but no dedicated Hosted Agent onboarding guide, no confirmed LangGraph-specific package, and no proof a platform-created identity can be migrated in place — `inferred` (partially evidenced, exact path unverified). Source: research.md (Line 568 register row)
* Platform SLA / GA status / regions / quotas / capacity / cold starts / disaster recovery — `requires-validation`, first Production Decision Gate item. Source: research.md (Line 576, Production Decision Gates — Platform status)

---

## Core Slide 12 — PoC Plan and Decision Gates

**Objective**: Four increments produce a defensible production decision, with owners, exit criteria, and a decision date.

* **Increment 1 — Baseline Hosted Agent & LangGraph Multi-Agent Runtime**: supervisor graph + 3 specialist nodes; `azure-ai-agentserver-langgraph` wrapper on Responses protocol (port 8088); validate local run, Responses SSE, built-in conversation history; provision via Bicep, deploy via `azd` — `confirmed` plan of record. Source: research.md (Lines 589-593)
* **Increment 2 — Decoupled MCP Tool Hosting & Foundry Integration**: Defender + Anomaly MCP servers on Container Apps with system-assigned managed identities and private networking; register as Foundry Custom Connections; bundle into Toolbox; validate tool calling, argument validation, error recovery — `confirmed` plan of record. Source: research.md (Lines 595-599)
* **Increment 3 — Offline Security Evaluation Suite & Automated CI/CD Gates**: versioned golden dataset; deterministic schema checks + LLM-as-judge rubrics; GitHub Actions gate (lint → Bicep validate → deploy candidate to staging → `microsoft/ai-agent-evals@v3-beta` → threshold-gated promotion) — `confirmed` plan of record. Source: research.md (Lines 601-605)
* **Increment 4 — Validation Tracks, Load Testing & Production Decision Gates**: Load & Scale Gate (10-100 concurrent users, same-thread turn concurrency, cold-start latency, active session compute); State Experiment Track (Cosmos serverless checkpointer benchmark: latency, RU cost, private endpoint reachability); Governance Validation Track (Agent 365 / Entra Agent ID onboarding probe); Continuous Evaluation Track (preview `EvaluationRule` for production sampling); Deliverable Synthesis (this deck + Production Decision Gate scorecard) — `confirmed` plan of record, individual track outcomes `requires-validation`. Source: research.md (Lines 607-611)
* Decision gates requiring evidence before production approval: Platform status, Scale, Security, Data, Quality, Operations, Cost, Preview acceptance — full list in Appendix H below. Source: research.md (Lines 572-583, Production Decision Gates)
* Owners and decision date: **not specified in the research document** — `requires-validation` / open item for the presenting team to fill in before delivery.

---

## Appendix A — Five-Option Comparison Matrix

Full dimension-by-dimension table, transcribed verbatim (columns: Runtime ownership, License and billing, Azure fit, Scaling evidence, Tools and MCP, Multi-agent, Streaming, State and history, Evaluations, Governance, Operational burden, Best fit — for OSS LangGraph on Azure compute / LangSmith Deployment Cloud / LangSmith self-hosted Enterprise / Foundry Hosted Agent baseline / Phased Foundry target).

Confidence: `confirmed` as a comparative synthesis of the five scenarios (each cell's underlying claim carries the same confidence tag as its corresponding scenario section, Slides 3-4 above). Source: research.md (Lines 489-506)

---

## Appendix B — Evidence Confidence Register

Full table, transcribed verbatim:

| Capability | Confidence | Customer-facing statement |
|---|---|---|
| LangGraph hosted as custom Foundry code | Confirmed by product documentation and samples | Suitable for PoC implementation |
| Responses SSE progressive output | Confirmed; application parity untested | Supported, with PoC contract and reconnect testing required |
| Per-session isolation and scale-to-zero | Confirmed mechanism; limits and SLA unknown | Promising scaling model, not yet a capacity commitment |
| External MCP plus connection and Toolbox aggregation | Documented pattern; private path untested | Recommended decoupling design, subject to network and auth validation |
| Supervisor and specialist agents in one graph | Confirmed LangGraph pattern | Production baseline for genuine multi-agent behavior |
| Cross-deployment A2A delegation | Sampled but preview | Optional experiment, not a baseline dependency |
| Foundry Responses conversation history | Confirmed for basic multi-turn use | Baseline state option; sidebar and retention requirements need testing |
| Cosmos DB LangGraph checkpointer | Package confirmed; Hosted Agent pairing untested | Conditional state experiment |
| Offline and batch evaluation of LangGraph outputs | Confirmed | Baseline release-gate mechanism |
| Continuous evaluation | Documented but preview | Optional production-monitoring experiment |
| GitHub Action targeting Hosted Agent versions and portal visibility | Not verified | Must be proven before claiming evaluation synchronization |
| Agent 365 onboarding and LangGraph instrumentation | Partially evidenced, exact path unverified | Governance option to validate, not a confirmed architecture property |
| Hosted Agent pricing, quotas, and SLA | Insufficient current evidence | Obtain live commercial and platform confirmation before production decision |

Source: research.md (Lines 554-570)

---

## Appendix C — Cost Assumptions

**Objective**: Show cost drivers as formulas/assumptions, never as false-precision totals.

* Cost drivers (confirmed list, `confirmed`): model tokens, active session vCPU-hour + GiB-hour compute, idle window duration, MCP hosting compute, telemetry (Application Insights), evaluation tokens, optional Cosmos DB (RU + storage), optional Agent 365 licensing, operations labor. Source: research.md (Lines 578-579, Production Decision Gates — Cost; Line 634, Open Customer Questions — Cost)
* Billing shape (`confirmed` mechanism): pay only for active session compute while a session sandbox is warm; scale-to-zero on idle timeout (5-60 min, default 15 min) — architecturally closest to Azure Container Apps consumption plan. Source: research.md (Scaling/cost model discovery, Key Discoveries section)
* **Unknown / TBD** (`requires-validation`): exact $/vCPU-hr and $/GiB-hr session-compute rates (public pricing page returned "N/A" at research time); real workload token/session volumes; Cosmos DB RU consumption under load; Agent 365 add-on pricing per license tier. Source: research.md (Line 570 register row; potential Next Research item, Lines ~50-53)
* Recommendation for the slide: present a cost **formula** (tokens × rate + session-compute-hours × rate + fixed telemetry/MCP hosting + optional extensions), leaving rate cells as "unknown / TBD — Azure Pricing Calculator required."

---

## Appendix D — Evaluation Rubric

* Golden dataset composition (`confirmed`): true positives, false positives, ambiguous evidence, missing data, conflicting tools, prompt injection, unauthorized actions, unsupported conclusions. Source: research.md (Line 510)
* Release-gate criteria (`confirmed`): triage correctness, evidence citation, tool selection, tool argument accuracy, unsupported-action refusal, task completion, output-schema validity, safety, latency, token use, session compute. Source: research.md (Line 511)
* Evaluator types (`confirmed`): deterministic checks (schema, citations, allowed tool calls, policy constraints) + model-based evaluators (relevance, groundedness, task adherence, rubric scoring). Built-in catalog includes quality, similarity, RAG, risk/safety, and agentic evaluator families. Source: research.md (Line 511; Line 298, evaluator catalog)
* Human review gate (`confirmed`): required for high-impact vulnerability conclusions and any recommendation triggering remediation or operational change. Source: research.md (Line 512)
* Production sampling (`preview`): continuous evaluation is a separate preview/privacy decision; redact sensitive content, define retention before enabling. Source: research.md (Line 513)

---

## Appendix E — Load-Test Plan

* Scope (`confirmed` plan of record, from Increment 4): 10-100 concurrent users/sessions; same-thread turn concurrency; cold-start latency distribution; active session compute measurement. Source: research.md (Line 609, Increment 4 — Load & Scale Gate)
* Unmeasured today (`requires-validation`): maximum sessions, requests-per-second ceiling, MCP fan-out throughput, checkpoint size limits, downstream throttling behavior. Source: research.md (Line 577, Production Decision Gates — Scale)
* State-experiment benchmark (`requires-validation`, part of the same increment): Cosmos DB serverless `CosmosDBSaver` checkpointer — latency, RU cost, and private-endpoint reachability vs. the Responses-history baseline. Source: research.md (Line 610, Increment 4 — State Experiment Track)

---

## Appendix F — RBAC Matrix

Full table, transcribed verbatim:

| Role | GUID | Scope | Use |
|---|---|---|---|
| Foundry Agent Consumer | `eed3b665-ab3a-47b6-8f48-c9382fb1dad6` | account/project/agent | invoke-only |
| Foundry User | `53ca6127-db72-4b80-b1b0-d745d6d5456d` | account/project | data-plane build/deploy — the correct role for CI/CD, not `Cognitive Services *` |
| Foundry Project Manager | `eadc314b-1a2d-4efa-be10-5d325db5065e` | account | create/manage projects, publish agents |
| Foundry Account Owner | `e47c6f54-e4a2-4754-9501-8e0985b135e1` | account | create projects/accounts, no data-plane build |
| Foundry Owner | `c883944f-8b7b-4483-af10-35834be79c4a` | account | full control |

Plus Contributor at resource-group scope for `azd provision`, and `AcrPush`/`AcrPull` if using container-deploy mode instead of code-deploy.

Confidence: `confirmed` (documented role definitions and GUIDs). Source: research.md (Lines 300-306, 307)

Related Bicep resource types (also `confirmed`), transcribed verbatim:

| Resource type | API version | Notes |
|---|---|---|
| `Microsoft.CognitiveServices/accounts` | `2025-04-01-preview` (sample) / `2025-06-01` (AVM) | `kind: 'AIServices'`, `allowProjectManagement: true` |
| `.../accounts/projects` | `2025-04-01-preview` | Foundry project |
| `.../accounts/projects/connections` | `2025-04-01-preview` | Cosmos DB/Storage/AI Search/OpenAI connections |
| `.../accounts/capabilityHosts`, `.../accounts/projects/capabilityHosts` | `2025-04-01-preview`/`2025-06-01` | Standard Agent Setup only (BYO storage) |
| `Microsoft.DocumentDB/databaseAccounts` | `2024-12-01-preview` | Cosmos DB (BYO thread storage or app-level checkpointer store) |

Source: research.md (Lines 313-320)

---

## Appendix G — Product-Status Register

This register reframes the Evidence Confidence Register (Appendix B) by product-capability GA/preview status rather than by claim. No separate product-status table exists in the research document; this view is derived from the same source rows.

| Product capability | Status | Confidence tag |
|---|---|---|
| Foundry Hosted Agents (custom-code hosting surface) | Public preview at research time — current GA status not reverified | `requires-validation` |
| LangGraph as a supported hosted-agent framework | Documented, first-class | `confirmed` |
| Responses protocol SSE streaming | Documented, confirmed mechanism | `confirmed` |
| A2A delegation protocol | Preview | `preview` |
| Continuous evaluation (`EvaluationRule`) | Documented but preview | `preview` |
| Microsoft Agent 365 / Entra Agent ID | GA (platform), Hosted Agent onboarding path unverified | `inferred` |
| `microsoft/ai-agent-evals` GitHub Action | Beta tag (`@v3-beta`); hosted-agent targeting not verified | `requires-validation` |
| LangSmith Azure BYOC | Roadmap-stated "planned for 2H 2026", not a release commitment | `requires-validation` |

Source: research.md (Line 5; Lines 356-369; Lines 554-570; Line 296)

---

## Appendix H — Open Questions

Transcribed from the Open Customer Questions section, each already separating established evidence from what the PoC must still prove:

* **Scaling**: per-session isolation, idle timeout, scale-to-zero documented; SLA, max sessions, RPS, same-session concurrency, cold-start distribution, model quota, and dependency limits are not established — `requires-validation`. Source: research.md (Line 615)
* **Cost**: drivers are known (tokens, session compute, idle window, MCP hosting, telemetry, evaluation tokens, optional state/governance services); actual rates and workload measurements are missing — `requires-validation`. Source: research.md (Line 616)
* **Tools and MCP**: custom MCP code needs its own Azure runtime; Foundry connections/Toolbox register and aggregate; auth, private reachability, throttling, versioning, and failure handling must be validated in the PoC — `requires-validation`. Source: research.md (Line 617)
* **Multi-agent design**: a supervisor coordinating specialists inside one hosted deployment is a genuine multi-agent system; separate A2A deployments are justified only by independent ownership/release/isolation/scaling needs and remain preview — `confirmed` baseline pattern / `preview` for A2A. Source: research.md (Line 618)
* **Evaluations**: offline/batch scoring confirmed; continuous evaluation documented but preview; GitHub Action hosted-agent targeting, portal visibility, and multi-agent trace coverage require validation — mixed `confirmed`/`preview`/`requires-validation`. Source: research.md (Line 619)
* **Automation**: recommended flow (staging → smoke/contract/streaming/offline-eval gates → approval → promote → monitor → rollback); infrastructure and agent versions have separate deployment lifecycles — `confirmed`. Source: research.md (Line 620)
* **Streaming**: Responses SSE supports progressive output events; parity with all required LangGraph events, reconnection, cancellation, and the existing UI contract must be tested — `confirmed` mechanism / `requires-validation` for parity. Source: research.md (Line 621)
* **Conversation state**: Responses history is the baseline source of truth; adopt Cosmos checkpointer only for a documented durable-state requirement; no user-scoped conversation-list API was found — `confirmed` baseline / `requires-validation` for the list API gap. Source: research.md (Line 622)
* **Governance**: per-agent Entra identity, Foundry RBAC, and Application Insights are supported baseline controls; Agent 365 is a validation track because the exact Hosted Agent identity onboarding and LangGraph instrumentation path was not found — `confirmed` baseline / `inferred` for Agent 365. Source: research.md (Line 623)
* **Reusability**: reuse comes from versioned Bicep modules, `azure.yaml`, a standard hosted-agent wrapper, independently owned MCP contracts, common evaluation datasets, and reusable GitHub workflows; Standard Agent Setup is a dependency-control choice, not mandatory for an app-owned Cosmos checkpointer — `confirmed`. Source: research.md (Line 624)
* **Owners and decision date** for the PoC plan (Core Slide 12): not specified anywhere in the research document — open item for the presenting team. `requires-validation` / not-yet-assigned.

---

## Traceability Summary

| Deck section | Research.md line range |
|---|---|
| Storyboard (Core Slides 1-12 objectives) | 535-553 |
| Five-Option Comparison Matrix (Appendix A) | 489-506 |
| Evidence Confidence Register (Appendix B) | 554-570 |
| Production Decision Gates (referenced Slide 12 + Appendix H) | 572-583 |
| RBAC roles + Bicep resource types (Appendix F) | 300-323 |
| Scenario A1/A2/A3/B/C (Slides 3-4) | 326-421 |
| Evaluation Strategy (Slide 9, Appendix D) | 508-516 |
| CI/CD and Release Control (Slide 10) | 518-533 |
| Four PoC Implementation Increments (Slide 12) | 587-611 |
| Open Customer Questions (Appendix H) | 613-635 |
