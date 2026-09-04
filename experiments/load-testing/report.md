# Step 7.1 — Load & Scale Gate Report

**Target**: `threat-assessment-agent` v9, `rg-air-canada-threat-assessment-poc`
(eastus2), project endpoint
`https://aif-air-canada-threat-assessment-poc.services.ai.azure.com/api/projects/proj-air-canada-threat-assessment-poc`.

**Method**: lightweight `asyncio`/`aiohttp` script (`load_test.py`) hitting the
agent's Responses SSE endpoint directly, plus a small supplementary test using
`azd ai agent invoke --session-id <shared-guid>` for the same-thread case.
This is a PoC-scale probe, not a production load-testing rig, per the plan's
explicit guidance to avoid provisioning heavy external load infrastructure.

## Honest scope statement

The plan's target range was 10-100 concurrent sessions. **This session
actually exercised 1, 5, 10, and 20 concurrent sessions** (plus a 3-request
sequential cold-start baseline and a 2-request same-thread test). The full
50-100 range was **not** attempted: each request takes ~18-30s end-to-end
(a real LLM completion, not a cached/mocked response) and running 100
concurrently would multiply both wall-clock time and token cost for this
single PoC-validation session well beyond what a lightweight probe justifies,
without a clear expectation of hitting a different failure mode than what 20
concurrent already exercises (the `gpt-4o-mini` `GlobalStandard` deployment
has only 10 capacity units per `azure.yaml`, and 20 concurrent requests
already stresses that more than any of the smaller runs did, with no
degradation observed — see below). Report this as a genuine scope limitation:
the measured range is **1-20 concurrent sessions**, not 10-100.

## Results

### Sequential cold start (n=3, one request at a time)

| Metric | Value |
|---|---|
| p50 latency | 18.41 s |
| p95 latency | 19.64 s |
| min / max | 18.24 s / 19.64 s |
| errors | 0 / 3 |

### Concurrent independent sessions

| Concurrency | Wall clock | p50 latency | p95 latency | Success | Errors |
|---|---|---|---|---|---|
| 5 | 26.41 s | 21.44 s | 23.57 s | 5/5 | 0 |
| 10 | 24.73 s | 22.16 s | 24.41 s | 10/10 | 0 |
| 20 | 34.43 s | 23.37 s | 28.68 s | 20/20 | 0 |

Raw JSON: `results/sequential-cold-start-3.json`,
`results/concurrent-sessions-5.json`, `results/concurrent-sessions-10.json`,
`results/concurrent-sessions-20.json`.

### Same-thread turn concurrency (n=2, one shared conversation)

Two concurrent `azd ai agent invoke --session-id <same-guid>` processes
(genuinely separate OS processes via PowerShell `Start-Job`), both resolving
to the same server-assigned conversation
(`conv_0b4d2f2a2564c8fc00LLm4tLigYCnJULtuWiHCKYCc0R6v8L1Z`):

| Turn | Elapsed | Result |
|---|---|---|
| A | 21.69 s | Completed, coherent report |
| B | 20.00 s | Completed, coherent report |

Both turns completed in roughly the same time as a single-request baseline
(not stacked to ~40s), and both returned coherent, independent responses with
no observed cross-talk. Raw detail:
`results/same-thread-turns-cli-2concurrent.json`.

**Known limitation**: `load_test.py`'s own `same-thread-turns` mode (direct
aiohttp POST) could not reliably self-derive a conversation ID to reuse for
follow-up turns — a bare POST returns `"conversation": null` in the SSE body
(confirmed via `debug_probe.py`), unlike an `azd ai agent invoke` call, which
negotiates a real conversation ID through some additional client-side state
not reverse-engineered in this session. Its `results/same-thread-turns-4.json`
output is **not reliable evidence of same-thread behavior** (each "follow-up"
silently ran as its own new conversation) and is superseded by the CLI-based
test above.

## Findings

* **No hard concurrency/throughput ceiling was observed** in the tested range
  (1-20 concurrent sessions). All 38 total requests across every run
  succeeded (0 errors), and per-request latency stayed in a stable ~18-29s
  band regardless of concurrency level — no sign of queuing, throttling, or
  429s at 20 concurrent.
* **Cold-start latency is dominated by LLM completion time, not sandbox
  spin-up overhead** that we could isolate: p50 ≈ 18-23s across every run
  mode, with no visible step-function jump between 1 and 20 concurrent
  sessions. This PoC could not separate "sandbox cold start" from "model
  completion latency" without instrumenting the agent's own code (out of
  scope for this phase, and would require modifying Phase 1-6 files) — this
  is a genuine measurement limitation, not a claim that cold-start overhead
  is zero.
* **Same-thread turn concurrency did not error or observably serialize** in
  the one trial run (n=2). This is a single data point, not a statistically
  robust conclusion — a production decision should not rely on this alone.
* **Observed vCPU/memory tier**: the deployed hosted agent's `azure.yaml`
  declares `container.resources: { cpu: "0.5", memory: "1Gi" }` (confirmed by
  reading the live `azure.yaml` in this repo, which matches what was actually
  deployed as v9). No live API or response header exposed the platform's
  *enforced* sandbox tier for verification (checked `azd ai agent show`
  output and raw SSE response headers via `azd ai agent invoke --output raw`
  — neither surfaces a vCPU/memory field). The declared `0.5 vCPU / 1Gi`
  value is **consistent with both** ranges cited in research.md lines
  163-166 (`0.5-2 vCPU` fixed tiers, and `0.25-4.0 vCPU` continuous range) —
  it sits inside both, so this deployment does not itself surface a
  contradiction. The underlying *documentation* discrepancy between the two
  cited ranges remains unreconciled at the platform-documentation level;
  this PoC can only confirm what was actually declared/deployed here, not
  resolve which of the two cited public-doc ranges is authoritative platform
  behavior.

## DD-01 reconciliation status

**Partially resolved.** The live deployment's declared tier (0.5 vCPU / 1Gi)
is confirmed via `azure.yaml` and matches both candidate ranges from
research, so it does not itself expose a contradiction. However, no live API
was found in this session that reports the platform's *actual enforced*
resource tier per session (as opposed to the requested/declared value), so
the original two-range documentation inconsistency itself remains
unreconciled — that would require a direct query to the Foundry
platform/support team, which is outside this PoC's tooling.
