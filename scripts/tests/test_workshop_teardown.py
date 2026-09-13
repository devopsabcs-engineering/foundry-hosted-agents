import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "remove-workshop.ps1"
PWSH = shutil.which("pwsh")
pytestmark = pytest.mark.skipif(PWSH is None, reason="PowerShell 7 is required for teardown tests")


@pytest.mark.parametrize("group,purpose,owner,flags,success,deleted", [
    ("rg-customer", "workshop-validation", "fha-learn-test", "", False, False),
    ("rg-fha-learn-test", "production", "fha-learn-test", "", False, False),
    ("rg-fha-learn-test", "workshop-validation", "another-env", "", False, False),
    ("rg-fha-learn-test", "workshop-validation", "fha-learn-test", "", True, False),
    ("rg-fha-learn-test", "workshop-validation", "fha-learn-test", "-Delete -ConfirmResourceGroup wrong", False, False),
    ("rg-fha-learn-test", "workshop-validation", "fha-learn-test", "-Delete -ConfirmResourceGroup rg-fha-learn-test -WhatIf", True, False),
    ("rg-fha-learn-test", "workshop-validation", "fha-learn-test", "-Delete -ConfirmResourceGroup rg-fha-learn-test -Confirm:$false", True, True),
])
def test_teardown_guards(group, purpose, owner, flags, success, deleted):
    environment = {
        **os.environ,
        "MOCK_GROUP": json.dumps({"tags": {"purpose": purpose, "workshopEnv": owner}}),
    }
    command = r"""
    $global:Deleted = $false
    function global:az {
        $global:LASTEXITCODE = 0
        switch ("$($args[0]) $($args[1])") {
            'group exists' { if ($global:Deleted) { 'false' } else { 'true' } }
            'group show' { $env:MOCK_GROUP }
            'resource list' { '[]' }
            'group delete' { $global:Deleted = $true; Write-Host 'DELETE_CALLED' }
            default { throw 'Unexpected Azure call' }
        }
    }
    """ + f"& '{SCRIPT.as_posix()}' -SubscriptionId 00000000-0000-0000-0000-000000000001 -EnvironmentName fha-learn-test -ResourceGroup {group} {flags}"
    result = subprocess.run([PWSH, "-NoProfile", "-NonInteractive", "-Command", command],
                            env=environment, capture_output=True, text=True, timeout=30, check=False)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    assert ("DELETE_CALLED" in result.stdout) == deleted


@pytest.mark.parametrize("state,exit_code", [("null", 0), ("", 0), ('"false"', 0), ("false", 9)])
def test_teardown_rejects_unreliable_existence_result(state, exit_code):
    command = (
        f"function global:az {{ $global:LASTEXITCODE = {exit_code}; $env:MOCK_STATE }}; "
        f"& '{SCRIPT.as_posix()}' -SubscriptionId 00000000-0000-0000-0000-000000000001 "
        "-EnvironmentName fha-learn-test -ResourceGroup rg-fha-learn-test"
    )
    result = subprocess.run(
        [PWSH, "-NoProfile", "-NonInteractive", "-Command", command],
        env={**os.environ, "MOCK_STATE": state}, capture_output=True,
        text=True, timeout=30, check=False,
    )
    assert result.returncode != 0
    assert "Already absent" not in result.stdout
    assert "Verified absent" not in result.stdout
