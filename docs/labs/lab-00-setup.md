---
permalink: /labs/lab-00-setup
title: "Lab 00 - Prerequisites and Environment Setup"
description: "Install required tools, clone the repository, create a Python virtual environment, and verify Azure access."
---

> 🇫🇷 **[Version française](../fr/labs/lab-00-setup)**

## Overview

| Item | Value |
| --- | --- |
| **Duration** | 20 minutes |
| **Level** | Beginner |
| **Prerequisites** | None |

## Learning Objectives

By the end of this lab, you will be able to:

* Install the tools needed to provision and invoke a Foundry Hosted Agent
* Clone the `foundry-hosted-agents` repository and set up a Python virtual environment
* Sign in to Azure and select an approved subscription for your own isolated workshop resources
* Run the repository's own test suites as a sanity check

## Exercises

Before Lab 02, obtain approval for a VNet, delegated subnets and a private DNS zone,
including the proposed non-overlapping address space and scoped network permissions.
Cosmos, when used, requires a private endpoint and a network-connected test location;
a public laptop cannot test its data plane. Foundry remains public for authenticated
access. See [Private Cosmos networking](../private-networking.md). If policies also
require private Foundry, registry or MCP ingress, stop: that is outside this profile.

### Exercise 0.1: Install Required Tools

1. **Python 3.13** — <https://www.python.org/downloads/>

   ```powershell
   python --version
   ```

2. **Azure Developer CLI (`azd`)** — <https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd>

   ```powershell
   azd version
   ```

3. **Azure CLI (`az`)** — <https://learn.microsoft.com/cli/azure/install-azure-cli>

   ```powershell
   az version
   ```

4. **Visual Studio Code** — <https://code.visualstudio.com/>

The commands in these labs use **PowerShell 7.3 or newer**. The invocation,
RBAC and evaluation helpers also require **Git Bash, jq and curl**. On Windows,
install Git for Windows and jq through your approved software channel (for
example `winget install --id Git.Git --exact` and
`winget install --id jqlang.jq --exact`). Restart your terminal after installing.
Do not change corporate execution or network policies to install a dependency.

In each new PowerShell session, activate Python as shown below and verify
the shell helpers. Windows' `System32/bash.exe` launches WSL, not Git Bash.
Adjust the Git path if your organization installs it elsewhere.

```powershell
$env:PATH = "C:\Program Files\Git\bin;$env:LOCALAPPDATA\Microsoft\WinGet\Links;$env:PATH"
$env:MSYS_NO_PATHCONV = '1'
Get-Command git, bash, jq, curl.exe, az, azd
bash -lc 'command -v az azd jq curl && jq --version'
```

`MSYS_NO_PATHCONV` prevents Git Bash from rewriting Azure resource IDs into
Windows paths. Keep the same session through Labs 02-08; its variables identify
your disposable resources. If you lose the session, recover your own environment
values, never substitute the resource names from historical screenshots.

### Exercise 0.2: Install the Foundry `azd` Extension

Foundry Hosted Agents are provisioned through an `azd` extension:

```powershell
azd ext install microsoft.foundry
```

### Exercise 0.3: Clone the Repository and Set Up Python

```powershell
git clone https://github.com/devopsabcs-engineering/foundry-hosted-agents.git
cd foundry-hosted-agents
python -m venv .venv
./.venv/Scripts/Activate.ps1
python -m pip install -r src/threat-assessment-agent/requirements.txt -r src/threat-assessment-agent/requirements-dev.txt
```

### Exercise 0.4: Sign In to Azure

```powershell
azd auth login
az login
```

Use a subscription where you are authorized to create billable resources and assign
resource-scoped roles. Do not reuse the instructor's or an existing customer resource group.
Sign in with your own approved identity; the security scenarios use synthetic fixtures,
not employee or customer data. Confirm the subscription and tenant before continuing:

```powershell
az account show --query "{name:name, id:id, tenantId:tenantId}" -o table
```

### Exercise 0.5: Run the Existing Test Suites

Before touching any infrastructure, confirm the repository's own tests pass
in your environment — this is the same command the CI pipeline runs.

```powershell
python -m pytest eval/deterministic-tests/ -v
python -m pytest src/threat-assessment-agent/tests/ -v
```

Expected result: both commands exit successfully with no failed tests. Counts grow as
the workshop evolves; do not compare them with an old screenshot or release report.
Some opt-in tests are skipped by default. Use `python -m pytest -rs` with the same test
paths to see the skip reasons. If either suite fails, re-check Exercise 0.3 before continuing.

> [!TIP]
> These two test suites don't touch Azure at all — they run entirely
> against local fixtures and a compiled LangGraph state machine. They're a
> fast way to confirm your Python environment is correct before Lab 02.

## Knowledge Check

* What's the difference between `az` and `azd`, and why does this workshop need both?
* Which two test suites did you just run, and what does each one validate?

## Next Steps

Continue to [Lab 01: Architecture Deep Dive](lab-01-architecture.md).
