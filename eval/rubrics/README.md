# LLM-as-Judge Rubrics

Model-based evaluation for the threat-assessment agent, gated against
`eval/golden-dataset.jsonl`. This directory covers the parts of the
Evaluation Strategy (research §"Evaluation Strategy", lines 508-516) that
require judgment rather than a deterministic string/schema check:
relevance, groundedness, task adherence, and rubric-scored triage quality.

## Strategy: built-in evaluators first, custom rubrics only where needed

Per the built-in evaluator catalog (research lines 315-323), Foundry ships
agentic evaluators — Coherence, Groundedness, TaskAdherence,
ToolCallAccuracy (plus IntentResolution and newer Tool Selection / Output
Utilization / Input Accuracy evaluators) — and can auto-generate **Rubric
evaluators from agent instructions** (i.e. directly from `graph.py`'s
`EVIDENCE_INVESTIGATOR_PROMPT` / `RISK_ANALYST_PROMPT` /
`REPORT_COMPOSER_PROMPT`). We use those built-ins wherever they cover the
gating criterion, and only define a custom rubric file for domain-specific
judgments the catalog does not already score.

| Gating criterion (research lines 508-516) | Mechanism |
|---|---|
| Output-schema validity | Deterministic (`eval/deterministic-tests/`) |
| Required evidence citation (presence) | Deterministic (`eval/deterministic-tests/`) |
| Allowed tool calls / policy constraints | Deterministic (`eval/deterministic-tests/`) |
| Coherence / fluency of the final report | **Built-in**: `builtin.coherence` |
| Groundedness (report matches gathered evidence) | **Built-in**: `builtin.groundedness` |
| Task adherence (specialist stayed in its lane) | **Built-in**: `builtin.task_adherence` |
| Tool selection / argument accuracy | **Built-in**: `builtin.tool_call_accuracy` |
| Triage correctness (true/false positive, severity) | Custom — [`triage-correctness.rubric.yaml`](./triage-correctness.rubric.yaml) |
| Evidence citation *quality* (relevance, not just presence) | Custom — [`evidence-citation.rubric.yaml`](./evidence-citation.rubric.yaml) |
| Conflicting-signal handling | Custom — [`conflict-handling.rubric.yaml`](./conflict-handling.rubric.yaml) |

[`evaluator-mapping.yaml`](./evaluator-mapping.yaml) lists, per golden-dataset
category, which built-in evaluators and which custom rubric(s) apply — this
is the file `.github/workflows/deploy-and-evaluate.yml` and any manual
Foundry evaluation run should reference.

## Status

These rubric definitions describe the intended evaluator configuration.
The exact `azure-ai-projects` evaluator registration call and the precise
`microsoft/ai-agent-evals@v3-beta` action inputs for wiring custom rubrics
alongside built-in evaluators are **not yet independently verified in this
repository** — see the Evidence Confidence Register entry "GitHub Action
targeting Hosted Agent versions and portal visibility: Not verified". Treat
these files as the authored specification to validate against a live
Foundry project in Phase 7, not as a already-proven pipeline.
