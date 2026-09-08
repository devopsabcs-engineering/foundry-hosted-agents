<!-- markdownlint-disable-file -->
# Production Decision Gate Scorecard

**Related plan**: air-canada-foundry-hosted-agents-plan.instructions.md (Step 7.5)
**Date**: 2026-09-08
**Scope**: Current engineering evidence, including the successful staging-to-production release and the separately gated Phase 7 experiments. The production environment is a PoC release target, not enterprise security certification.

## Verified release

[Run 34178081808](https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34178081808)
passed all seven release jobs; recovery was skipped. Commit
`f3da486497450d24d540c994839db2876936d22a` deployed staging version 6 and
production version 34 (previously 33), with both required production approvals
and no protection bypass. The exact-version production smoke passed.

The release captured all eight cases, with zero deterministic policy failures,
21/21 checks across seven model-judged reports, and 28 successful runtime tool
receipts. `inject-001` passed the explicit deterministic safety-refusal policy
with no tool calls; it was not model-scored. Thresholds remained at 100%.
The MCP tools execute against synthetic fixtures, not live customer telemetry.

![Verified evaluation results rendered from saved artifacts](../docs/assets/images/release-evaluations.png)

[Release evidence and provenance](https://github.com/devopsabcs-engineering/foundry-hosted-agents/wiki/Release-Evidence)
include the source artifacts and SHA-256 manifest. WI-11 is operationally
resolved for this implementation. An internal Azure authorization cache remains
an unconfirmed RCA hypothesis; support-case closure is not asserted.

## How to read this scorecard

* **Pass** — evidence collected in this PoC directly satisfies the gate.
* **Conditional** — partial evidence exists; a specific, named follow-up closes the gap.
* **Fail** — evidence collected in this PoC contradicts or fails the gate as tested.
* **Not testable in this PoC** — requires a separate commercial/legal/platform confirmation outside this codebase's tooling (pricing, SLA, tenant licensing, Azure support).

## Production Decision Gates

| Gate | Status | Owner | Evidence pointer |
|---|---|---|---|
| **Platform status** — GA status, SLA, regions, quotas, capacity, cold starts, disaster recovery | Not testable in this PoC | Microsoft Foundry account team | Research Evidence Confidence Register ("Hosted Agent pricing, quotas, and SLA — Insufficient current evidence"); this PoC observed cold-start p50 ≈18-23s (`experiments/load-testing/report.md`) but cannot confirm GA/SLA/DR commitments |
| Scale: concurrency, fan-out, throttling | Conditional | Engineering lead | Earlier load tests exercised only 1-20 concurrent sessions and n=2 same-thread turns. They were not rerun after the MCP fixes. Extend to 50-100 sessions with a dedicated budget and measure real tool fan-out before claiming capacity. |
| **Security** — private endpoint reachability, identity propagation, least privilege, tool authorization, egress controls, prompt injection, destructive-action approval | Conditional | Security architect | Prompt-injection and unauthorized-action refusal ARE covered by `eval/golden-dataset.jsonl` + `eval/deterministic-tests/` (Phase 6, passing). Private endpoint reachability tested for Cosmos DB only, and inconclusively — public access is confirmed blocked (`experiments/cosmos-checkpointer/report.md`), but whether a Hosted Agent sandbox can reach a *private* endpoint at all was not established. Identity propagation: Phase 7.3 found the platform auto-creates Entra `AgentIdentity`/`AgentIdentityBlueprint` objects natively (promising signal, unconfirmed). **Follow-up**: provision a private endpoint + VNet-resident test harness for Cosmos; confirm Hosted Agent sandbox VNet-injection support with the Foundry product team |
| **Data** — classification, residency, retention, deletion, legal hold, checkpoint compatibility, telemetry redaction | Not testable in this PoC | Data governance / legal | No classification, residency, or legal-hold review was in scope for this engineering PoC. Checkpoint compatibility (Cosmos) is technically wired (bug found and fixed in `state.py`'s `get_checkpointer()`, see `experiments/cosmos-checkpointer/report.md`) but unbenchmarked due to the private-networking blocker above. Telemetry redaction policy for continuous evaluation was documented as a minimal synthetic-data policy only, not a real PII-redaction review (`experiments/continuous-evaluation/`) |
| Quality: versioned cases, deterministic policy, judge thresholds, regression gate | Pass for this synthetic release suite | Engineering lead | Run 34178081808: 8/8 captures, zero policy failures, 21/21 coherence/groundedness/task-adherence checks, verified injection refusal, 28 tool receipts. Strict staging gate ran before promotion. Category-specific custom rubrics and human review of real high-impact conclusions remain outside this automated pass. |
| Operations: release controls, alerts, recovery, incident ownership | Conditional | SRE/on-call owner | Full release, normal approvals, previous-version discovery, exact-version production smoke and monitoring passed. The wiki now includes an operations runbook. Monitoring returned zero AppExceptions in a trailing-ten-minute window, not a ten-minute soak or proof of complete tracing. MCP image digests are promoted; the hosted agent is rebuilt from the same source, not the identical binary. Recovery remains manual, without automatic rollback, canary or rehearsed disaster recovery. |
| **Cost** — model tokens, active session compute, idle window, Cosmos requests/storage, MCP hosting, telemetry, evaluation tokens, Agent 365 licensing, operations labor | Not testable in this PoC | Finance / commercial owner | Requires live Azure pricing/commercial confirmation per research's own Evidence Confidence Register entry ("Hosted Agent pricing, quotas, and SLA — Insufficient current evidence"). This tenant confirmed to lack Agent 365 licensing entirely (`experiments/agent365-onboarding/report.md`), which is itself a cost/procurement data point if Agent 365 governance is pursued |
| Preview acceptance: explicit approval for retained preview capabilities | Conditional | Business/product sponsor | Hosted-agent and Toolbox integrations work in the verified release, but technical success is not business acceptance of preview terms. The release uses the repository's custom evaluation runner, not `microsoft/ai-agent-evals`. Continuous EvaluationRule remains a separate blocked experiment. Obtain explicit approval for capabilities retained in a pilot. |

## Phase 7 experiment outcomes (source evidence)

| Track | Status | Key finding | Evidence |
|---|---|---|---|
| 7.1 Load & scale | Partial | No ceiling observed at 1-20 concurrent (target was 10-100; full range not exercised — honest scope limitation, not a pass on the full target) | `experiments/load-testing/report.md` |
| 7.2 Cosmos DB checkpointer | Partial | Infra deployed live; a real `TypeError` bug in `state.py`'s `get_checkpointer()` was found and fixed (18/18 tests still pass); live benchmark blocked by tenant-enforced private-only Cosmos networking (Bicep override did not take effect — confirmed governance policy, not a bug) | `experiments/cosmos-checkpointer/report.md` |
| 7.3 Agent 365 onboarding | Blocked (expected, valid outcome) | Tenant lacks Agent 365 licensing (M365 E5 without the required add-on) — probe correctly stopped rather than fabricating success. Bonus finding: the platform already auto-creates Entra `AgentIdentity`/`AgentIdentityBlueprint` objects at hosted-agent deploy time, a promising unconfirmed lead for future licensed re-testing | `experiments/agent365-onboarding/report.md`, `probe-evidence.json` |
| 7.4 Continuous evaluation | Blocked | `EvaluationRule` creation failed: `UserError` — the project's managed identity lacks the `Foundry User` role / the `Microsoft.CognitiveServices/accounts/AIServices/assets/read` data action needed to list datasets. This is a fixable RBAC gap, not a preview-unavailability finding | `experiments/continuous-evaluation/results/deployment-outcome.json` |

## Explicitly flagged known gaps (from Phases 5-7)

* WI-11 is resolved operationally: model calls recovered, the versioned MCP endpoint and RemoteTool connections work, and runtime receipts prove both specialists invoked their tools. The legacy resolver failure and v32 degraded response are historical evidence, not the current behavior.
* **Continuous evaluation RBAC gap (Phase 7.4)**: fixable by granting the project's managed identity (`7e9de957-4dfe-412e-9894-fc33ac9c9b57`) the `Foundry User` role at the project scope, then re-running `experiments/continuous-evaluation/deploy_evaluation_rule.py`. Not yet applied in this session (a live RBAC change against production-adjacent infrastructure) — recommend applying and re-testing before this line item is closed.
* **Cosmos private connectivity (Phase 7.2)**: whether a Hosted Agent's per-session sandbox can reach a private-endpoint-only resource at all is unconfirmed and requires a Foundry product-team answer, not just Azure-side Cosmos configuration.
* Earlier CI contract, environment and live-run gaps have been exercised successfully by run 34178081808. This does not close the separate manual-recovery rehearsal or reproducible hosted-agent binary-promotion gaps.

## Overall recommendation

Recommend a **conditional go for continued PoC-to-pilot investment**. The baseline now works end to end: hosted multi-agent execution, real MCP calls over synthetic data, strict evaluation, approved promotion, production smoke and monitoring. WI-11 is no longer a pilot blocker. Before a broader production commitment, establish named security/data/operations owners, review public MCP ingress and tool authorization, extend load testing, rehearse recovery, and obtain commercial/SLA/pricing and preview acceptance. Re-test continuous evaluation, Cosmos private connectivity and Agent 365 only if those optional capabilities are included in the target design.
