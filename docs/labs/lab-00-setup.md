---
permalink: /labs/lab-00-setup
title: "Lab 00 - Prerequisites and Environment Setup"
description: "Install required tools, clone the repository, create a Python virtual environment, and verify Azure access."
---

## Overview

| | |
|---|---|
| **Duration** | 20 minutes |
| **Level** | Beginner |
| **Prerequisites** | None |

## Learning Objectives

By the end of this lab, you will be able to:

* Install the tools needed to provision and invoke a Foundry Hosted Agent
* Clone the `foundry-hosted-agents` repository and set up a Python virtual environment
* Sign in to Azure and confirm you can see the Foundry project used in this workshop
* Run the repository's own test suites as a sanity check

## Exercises

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
pip install -r src/threat-assessment-agent/requirements.txt -r src/threat-assessment-agent/requirements-dev.txt
```

### Exercise 0.4: Sign In to Azure

```powershell
azd auth login
az login
```

Confirm you're pointed at the subscription that hosts this workshop's
resources:

```powershell
az account show --query "{name:name, id:id}" -o table
```

### Exercise 0.5: Run the Existing Test Suites

Before touching any infrastructure, confirm the repository's own tests pass
in your environment — this is the same command the CI pipeline runs.

```powershell
pytest eval/deterministic-tests/ -v
pytest src/threat-assessment-agent/tests/ -v
```

Expected result: **12 passed** for the deterministic evaluation checks and
**18 passed** for the agent's unit tests. If either suite fails, re-check
Exercise 0.3 (dependency installation) before continuing.

> [!TIP]
> These two test suites don't touch Azure at all — they run entirely
> against local fixtures and a compiled LangGraph state machine. They're a
> fast way to confirm your Python environment is correct before Lab 02.

## Knowledge Check

* What's the difference between `az` and `azd`, and why does this workshop need both?
* Which two test suites did you just run, and what does each one validate?

## Next Steps

Continue to [Lab 01: Architecture Deep Dive](lab-01-architecture.md).
