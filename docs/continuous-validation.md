---
lang: en
title: Continuous Validation and Test Trends
description: Run regression tests and staging probes in GitHub Actions and publish durable wiki trends.
nav_order: 0.5
---

> **[Version française](fr/continuous-validation.md)**

## Cadence

The `Continuous Validation` workflow runs offline tests on every push to `main`, every pull request,
and manual dispatch. After the offline job passes, main-branch runs evaluate the existing staging agent
against the golden dataset and issue five concurrent Responses requests. Pull requests do not receive
Azure credentials or run live tests.

This workflow does not provision, deploy, promote, or invoke production. The test-code SHA identifies
the checked-out tests, not necessarily the source running in staging. Evaluations bind to the discovered
active agent version. The load probe exercises the staging route, with before/after version checks;
its latency measurements are withheld if that route changes or cannot be verified.

`Deploy and Evaluate (Staging -> Production)` remains manual and approval-gated. Its offline and
evaluation results also feed the trend publisher. The direct manual deployment workflow shares the
same environment lock but does not produce quantitative trend artifacts.

All three workflows use the `foundry-shared-environments` concurrency group for Azure operations.
The release workflow holds the lock through production approval and monitoring. Live validation
waits during that period. GitHub's `queue: max` permits up to 100 pending runs/jobs without replacing
earlier pending work. Queue overflow can still cancel a run, and external/manual Azure changes are
outside this lock. Failed and cancelled source runs remain visible in the reporting table.

## Measurements

| Test family | Published measurements | Failure behavior |
| --- | --- | --- |
| Agent graph and deterministic tests | JUnit passed, failed, skipped, and summed testcase duration | Failing tests fail the job; collected results are still uploaded |
| Shell regression checks | Per-step outcomes in the publisher summary and retained aggregate JSON | A failed check fails its source job |
| Golden hosted evaluations | Captures, capture errors, deterministic policy failures, runtime tool receipt count, and three judge pass rates | Existing strict capture, evidence, and quality gates remain unchanged |
| Concurrent load probe | Success/error counts, wall time, successful-request p50/p95, five-request count | Non-200 HTTP, failed/incomplete/error events, malformed JSON, or missing completed assistant text fail the probe |

The load contract is `completed-text-v2`. Each request has a 180-second total timeout; the CI step
has a five-minute limit. The CLI permits 1-20 samples for manual experiments, but CI fixes concurrency
at five. A text delta and exactly one completed assistant message are required. Failed requests never
become successful latency samples. With no successes, latency is unavailable, not zero.

Live tests use synthetic fixtures. Five samples do not establish capacity, an SLA, or a statistically
stable tail percentile. The legacy `sequential-cold-start` mode does not prove a host cold start and is
not scheduled by CI. Historical load JSON files used an older success contract and are excluded from
the new trend series. Verified safety refusals remain deterministic checks, not model-judge passes.

Task-adherence evaluation uses the composer's full input, including captured specialist reports
and tool receipt count. See the [September 15 evaluation correction](task-adherence-20260915.md)
for the failed-case diagnosis, shared input contract, and controlled replay evidence.

## Summaries and Wiki History

Offline counts, evaluation summaries, and load numbers appear in the source workflow's job summaries.
`Publish Test Trends` starts when a trusted main-branch validation or release run completes, including
failure and cancellation. Its summary includes aggregate metrics, each job/check outcome, and a link
to the exact source run attempt. It retains a downloadable `ci-report-<run>-<attempt>` artifact.

The publisher checks out reporting code from trusted `main`, verifies the source repository, branch,
event and workflow path, and downloads only allowlisted artifacts for that attempt. It never executes
artifact contents or checks out pull-request code. Azure OIDC permission exists only on the live job;
the publisher uses read-only Actions access plus a separate wiki credential.

On successful publication the wiki contains:

* `Continuous-Test-Trends`: generated Mermaid bar charts and tables with exact run/attempt links.
* `trend-history/<run-id>-<attempt>.json`: durable aggregate evidence without prompts or responses.

The visible table covers the latest 50 attempts; each chart shows up to 12 available measurements.
Chart labels use V (validation) or R (release), workflow run number, and attempt; table links resolve
them to full run IDs. Bar-chart axes start at zero, and judge-rate charts use the full 0-100% range.
History files remain in the wiki repository. Replaying the same attempt is idempotent, and expired
source artifacts do not erase already stored measurements. Missing measurements appear as `N/A` and
are omitted from charts, never converted to zero. Failed workflow outcomes remain in the table even
when some individual measurements passed.

### Test Suite Growth

The wiki includes a run-linked inventory table and separate count charts for total offline tests,
agent graph tests, deterministic evaluation tests, and reporting/load-contract tests. These counts
come from the JUnit testcase records, including skipped tests. Shell checks remain per-step outcomes,
not invented testcase counts. Unknown JUnit file categories are grouped as Other JUnit when present.

Each column is one measured run or attempt, not a cumulative execution count. New tests increase
the inventory; rerunning an unchanged suite leaves its count flat. Removed tests remain visible as
decreases. The offline total already includes its component types, so do not add them together again.

Live evaluation cases, completed judge checks, and load requests have separate count charts. These
measure available results and may overlap or repeat scenarios; they are not extra offline test cases
or proof of coverage growth. Missing results remain N/A. A partial run may report fewer available tests.
The source offline summary and publisher summary also include the test-type breakdown.

Historical aggregates without type counts remain N/A for that breakdown. Replay their source attempts
while JUnit artifacts are retained to recover measured counts. To add another column, execute a new
validation run; replaying publication of the same attempt updates that point without duplicating it.

Evaluation series are separated by dataset and evaluator-code hashes, judge deployment, and environment.
Changing the model behind an existing judge deployment name is not automatically version-detected;
use a new deployment name when changing the judge if you need separately comparable series.
The table records agent-version changes alongside measurements. A deployment version is not a source SHA.

Raw offline/live artifacts are retained for 30 days in the validation workflow, release evaluation
artifacts for seven days, and aggregate publisher artifacts for 90 days. The wiki's sanitized history
outlives Actions artifact retention. Raw evaluation artifacts can contain synthetic prompts/responses;
they are not copied into the wiki.

## Activate Publishing

These workflows must be merged or pushed to `main` before automatic execution begins. The wiki page
is created by its first successful publisher run; adding files locally does not enable the service.

1. Verify the existing `staging` GitHub environment variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
   `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, and `FOUNDRY_MODEL_NAME`. The OIDC identity must
   already be authorized to invoke staging and create/read evaluations. The workflow does not add roles.
2. In repository **Settings > Secrets and variables > Actions**, create `WIKI_PUSH_TOKEN` using an
   organization-approved credential that supports Git clone/push to this repository's wiki.
   Grant the credential's account access only to the required repository where possible. A classic
   token for an internal/private wiki needs the appropriate `repo` access and any required SSO approval;
   confirm wiki support before choosing a fine-grained token or GitHub App alternative.
3. Do not paste credentials into chat or workflow files. Do not reuse an Azure credential for wiki access.
   The workflow does not assume the default `GITHUB_TOKEN` can push the separate wiki repository.
4. Push the approved workflow changes, or dispatch `Continuous Validation` on `main` after publication.
5. Check both the source run and its `Publish Test Trends` run. Confirm that the wiki page contains
   the matching source run ID and attempt, then add it to the wiki sidebar if desired.

Without `WIKI_PUSH_TOKEN`, the publisher deliberately fails its wiki step with an actionable message.
The aggregate summary and downloadable report are produced before that step and remain available.
No live CI run or wiki publication is implied by local validation alone.

## Replay a Publication

Dispatch `Publish Test Trends` with the completed source `run_id` and `attempt`. This rebuilds the
report without invoking the agent or redeploying anything. Replay promptly while source artifacts are
available. Attempt-scoped artifacts prevent earlier attempts from silently being reported as current.
Partial job reruns may have missing measurements for jobs not executed in that attempt.

Wiki publishing is serialized in its own queued concurrency group. It stages only the generated page
and `trend-history/`, leaving other pages alone. A concurrent manual wiki edit may reject the Git push;
the workflow never force-pushes. Replay publication to clone the new wiki head and retry safely.

## Local Verification

```powershell
.venv/Scripts/python.exe -m pytest scripts/tests/test_ci_results.py experiments/load-testing/test_load_test.py -q
.venv/Scripts/python.exe -m ruff check scripts/ci_results.py scripts/tests/test_ci_results.py experiments/load-testing/load_test.py experiments/load-testing/test_load_test.py
actionlint -ignore 'unexpected key "queue" for "concurrency" section' .github/workflows/*.yml
```

The narrow `actionlint` exception is needed while its concurrency schema lacks GitHub's documented
[`queue: max`](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency)
field. Other syntax, expression, and shell checks remain enabled. Remove the exception when the linter
supports that field. The focused tests cover false-green load responses, CLI failures, missing evidence,
zero judge pass rates, history replay, route changes, and chart generation from synthetic samples.
