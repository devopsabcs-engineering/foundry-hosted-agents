# Agent 365 / Entra Agent ID Onboarding Probe — Step 7.3

See `report.md` for the full write-up. Summary: **licensing prerequisite not
met** (this tenant has M365 E5 without the Agent 365 add-on) — an expected,
valid outcome per the plan, documented rather than fabricated.

Raw evidence: `probe-evidence.json`.

## Commands used (for reproducibility)

```powershell
# 1. Licensing check (done FIRST, per the plan's instruction)
az rest --method get --url "https://graph.microsoft.com/v1.0/subscribedSkus" `
  --query "value[].{sku:skuPartNumber, enabled:capabilityStatus, servicePlans:servicePlans[].servicePlanName}" -o json

# 2. Identity-layer evidence (does not require an Agent 365 license)
azd ai agent show threat-assessment-agent --no-prompt   # source of the Blueprint/Instance identity IDs
az ad sp show --id 59a21b26-5c3a-42aa-ad7f-05fe701fb25f --query "{displayName, servicePrincipalType, appId, tags}" -o json
az ad sp show --id e227baaa-48b3-4505-a19f-d840bfa2400d --query "{displayName, servicePrincipalType, appId, tags}" -o json

# 3. Registry-visibility probe (inconclusive; two Graph beta endpoint guesses, both 400)
az rest --method get --url "https://graph.microsoft.com/beta/directory/agentIdentities"
az rest --method get --url "https://graph.microsoft.com/beta/agentApplications"
```
