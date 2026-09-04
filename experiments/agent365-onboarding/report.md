# Step 7.3 — Agent 365 / Entra Agent ID Onboarding Probe

**Status: Blocked (expected, valid outcome) — licensing prerequisite not met.**
Per the plan's own framing, this is documented as an important, honest
finding, not a fabricated success.

## Licensing check (performed first, per the plan's instruction)

Queried the tenant's subscribed Microsoft 365 SKUs via Microsoft Graph
(`GET https://graph.microsoft.com/v1.0/subscribedSkus`):

```
FLOW_FREE
CCIBOTS_PRIVPREV_VIRAL
POWERAPPS_VIRAL
Microsoft_365_E5_(no_Teams)
POWERAPPS_DEV
```

No SKU or service plan matching "Agent 365," "Agent365," or an add-on name
was present in the full service-plan list for any subscribed SKU (searched
the complete `Microsoft_365_E5_(no_Teams)` service-plan list — over 90
entries — no match). Per research.md §5 (subagent research,
`microsoft-agent-365.md`): *"Agent 365 is included with Microsoft 365 E7 and
is available as an add-on to Microsoft E5/A5/Business Premium (or Microsoft
Defender Suite + Microsoft Purview Suite)."* This tenant has **M365 E5**,
which requires the **Agent 365 add-on** — and that add-on is **not present**
in this tenant's subscribed SKUs.

**Conclusion: this tenant does not have the licensing prerequisite for
Microsoft Agent 365.** Per the plan's explicit instruction, this is
documented as the expected, valid outcome and the probe stops here rather
than fabricating a successful onboarding.

## What was still confirmed (identity-layer evidence, does not require an Agent 365 license)

Even without Agent 365 licensing, `az ad sp show` against the two Entra
identities the Foundry platform auto-created for the deployed hosted agent
(from `azd ai agent show threat-assessment-agent`) revealed genuinely useful
evidence about the underlying identity model:

| Identity | Object/App ID | `servicePrincipalType` | `displayName` suffix |
|---|---|---|---|
| Instance identity | `59a21b26-5c3a-42aa-ad7f-05fe701fb25f` | `ServiceIdentity` | `...-AgentIdentity` |
| Blueprint identity | `e227baaa-48b3-4505-a19f-d840bfa2400d` (object) / `809d5ac4-8b64-4d0c-895a-c33f3e404b93` (app) | `Application` | `...-5e448-AgentIdentityBlueprint` |

Both display names and the `AgentIdentityBlueprint`/`AgentIdentity` naming
exactly match the **Entra Agent ID** terminology described in research.md
lines 168-171 and the subagent research file (`microsoft-agent-365.md` §2,
"agent identity blueprints" + "agent identities"). Both carry an
`agentGuid:5e44808f-0deb-4241-a915-1ed6f9170bef` tag matching the `azd ai
agent show` "Agent GUID" field.

**This is new evidence beyond what research.md could establish** (research
explicitly flagged: *"did not establish that a platform-created hosted-agent
identity can be migrated in place"*). What this session directly observed:
Azure AI Foundry **already creates native Entra Agent ID-shaped identity
constructs** (a blueprint + an instance identity, not a conventional app
registration/service-principal pair) automatically at hosted-agent deploy
time — it does not appear to be a plain legacy app registration needing the
documented migration path at all. This is a promising signal that the
"no in-place conversion... migration requires creating a new agent identity"
caveat in the research may not apply to Foundry Hosted Agents specifically,
since the platform seems to create Agent-ID-shaped identities natively.
**This is an inference from object naming/type/tags, not a confirmed
statement from Microsoft documentation** — it was not possible to verify
this via the Agent 365/Entra Agent ID admin surface itself (that surface
requires the Agent 365 license this tenant lacks), so it should be treated
as a promising lead for a follow-up session with proper licensing, not a
settled fact.

## Registry-visibility probe (Graph API guesses, inconclusive)

Attempted two Graph beta endpoint guesses to see if the Agent 365 registry
surfaced anything without a license:
`GET https://graph.microsoft.com/beta/directory/agentIdentities` and
`GET https://graph.microsoft.com/beta/agentApplications` — both returned
`400 Bad Request: Resource not found for the segment '...'`, meaning
neither path segment is recognized by this Graph beta schema version. This
is inconclusive (could mean wrong guessed path, or the surface genuinely
isn't exposed for this tenant/license) — no further endpoint names were
guessed, per the instruction not to keep retrying blind variations.
`microsoft-agent-365.md`'s own Gaps section separately notes the Agent
Registry Graph API is itself still in preview, consistent with not finding
a stable, documented endpoint here.

## Success-criteria disposition

* *"Outcome record states pass/fail for identity onboarding and, separately,
  whether LangGraph-specific constructs appear in Agent 365 observability"*
  — **Fail (licensing), not attempted (LangGraph-specific instrumentation)**.
  Identity onboarding into the Agent 365 registry could not be attempted at
  all because the tenant lacks the Agent 365 license; therefore whether
  LangGraph-specific constructs (nodes/edges/checkpoints) would appear in
  Agent 365 observability could not be tested either — this depends on a
  licensed tenant being available first.
* *"Licensing prerequisite ... is confirmed against the tenant before the
  probe is attempted"* — **Met.** Confirmed via `subscribedSkus` (above)
  before attempting anything further, per the plan's own success criterion
  and instruction order.

## What would unblock this

1. Acquire the Microsoft Agent 365 add-on for at least one licensed user in
   this tenant (or Microsoft Defender Suite + Microsoft Purview Suite, the
   alternative qualifying bundle per research.md §5), or move to a tenant
   that already has M365 E7 or the add-on.
2. Once licensed, re-run this probe against the Microsoft 365 admin center's
   Agent Registry (`learn.microsoft.com/microsoft-365/admin/manage/
   agent-registry`) to check whether `threat-assessment-agent`'s existing
   `AgentIdentityBlueprint`/`AgentIdentity` pair (found above) already
   appears there natively, or whether the documented manual migration path
   (`migrate-custom-app-registrations-to-agent-id`) is still required despite
   the identities already looking Agent-ID-shaped.
3. If the SDK-level integration is desired beyond identity/registry
   visibility, install `microsoft-agents-a365-observability-extensions-
   langchain` (confirmed to exist on PyPI per the subagent research) into
   the agent's `requirements.txt` and instrument `graph.py` — **not attempted
   in this session** since it depends on the licensing/registry question
   being resolved first, and would be an actual code change to Phase 1-6
   files that the plan's constraints require justifying carefully.
