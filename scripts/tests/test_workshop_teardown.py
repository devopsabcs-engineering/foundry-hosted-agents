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


@pytest.mark.parametrize('case,success,deleted', [
    ('preview', True, False), ('delete', True, True), ('wrong-confirmation', False, False),
    ('unexpected-app', False, False), ('injected-account', False, False),
    ('integrated-environment', False, False), ('azure-error', False, False),
    ('unexpected-project', False, False), ('invalid-project-inventory', False, False),
])
def test_hybrid_migration_scope(tmp_path, case, success, deleted):
    script = SCRIPT.parent / 'reset-hybrid-environments.ps1'
    command = r'''
    $global:Removed = $false
    $global:ProjectRemoved = $false
    function global:az {
        $global:LASTEXITCODE = if ($env:CASE -eq 'azure-error') { 1 } else { 0 }
        $verb = $args[0..2] -join ' '
        if ($args -contains 'delete') {
            if ($args -contains 'project') { $global:ProjectRemoved = $true }
            if ($verb -eq 'cognitiveservices account delete' -and -not $global:ProjectRemoved) {
                throw 'Project must be removed before its account'
            }
            $global:Removed = $true; Write-Host 'DELETE_CALLED'; return
        }
        if ($args -contains 'purge') { throw 'Unexpected purge' }
        if ($global:Removed) { '[]'; return }
        switch -Wildcard ($verb) {
            'containerapp list *' {
                $name = if ($env:CASE -eq 'unexpected-app') { 'not-approved' } else { 'mcp-defender-server' }
                ConvertTo-Json -InputObject @(@{name=$name; properties=@{
                    managedEnvironmentId='/environments/mcp-mcp-env'
                    configuration=@{ingress=@{fqdn='test'}};template=@{containers=@(@{image='digest'})}
                }}) -Depth 10 -Compress
            }
            'containerapp env list' {
                $network = if ($env:CASE -eq 'integrated-environment') { @{infrastructureSubnetId='subnet'} } else { $null }
                ConvertTo-Json -InputObject @(@{name='mcp-mcp-env';properties=@{vnetConfiguration=$network}}) -Depth 10
            }
            'cognitiveservices account list' {
                $injection = if ($env:CASE -eq 'injected-account') { @(@{scenario='agent'}) } else { $null }
                ConvertTo-Json -InputObject @(@{name='aif-air-canada-threat-assessment-poc';kind='AIServices';
                    location='eastus2';properties=@{networkInjections=$injection}}) -Depth 10
            }
            'cognitiveservices account project' {
                if ($env:CASE -eq 'invalid-project-inventory') { '{}'; return }
                $name = if ($env:CASE -eq 'unexpected-project') { 'unexpected' } else {
                    'aif-air-canada-threat-assessment-poc/proj-air-canada-threat-assessment-poc'
                }
                ConvertTo-Json -InputObject @(@{name=$name;id='/projects/test'}) -Compress
            }
            default { throw "Unexpected command $verb" }
        }
    }
    ''' + f"& '{script.as_posix()}' -SubscriptionId 64c3d212-40ed-4c6d-a825-6adfbdf25dad " + (
        f"-ResourceGroup rg-air-canada-threat-assessment-poc -EvidenceDirectory '{tmp_path.as_posix()}'"
    )
    if case != 'preview':
        confirmation = 'wrong' if case == 'wrong-confirmation' else 'rg-air-canada-threat-assessment-poc'
        command += f' -Delete -ConfirmResourceGroup {confirmation}'
    result = subprocess.run(
        [PWSH, '-NoProfile', '-NonInteractive', '-Command', command],
        env={**os.environ, 'CASE': case}, capture_output=True, text=True, timeout=30, check=False,
    )
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    assert ('DELETE_CALLED' in result.stdout) == deleted


AIR_CANADA_MOCK = r'''
$global:Gone = @{}
$global:Calls = [System.Collections.Generic.List[string]]::new()
function global:azd { $global:Calls.Add('azd down'); $global:Gone['rg-air-canada-threat-assessment-poc'] = $true; $global:LASTEXITCODE = 0 }
function global:az {
    $global:LASTEXITCODE = 0
    $verb = $args[0..2] -join ' '
    $group = $args[[array]::IndexOf($args, '--name') + 1]
    switch -Wildcard ($verb) {
        'group exists *' { if ($global:Gone[$group]) { 'false' } else { 'true' } }
        'group delete *' { $global:Calls.Add("group delete $group $($args -contains '--no-wait')"); $global:Gone[$group] = $true }
        'resource list *' { '[{"name":"r","type":"t","id":"/r"}]' }
        'identity show *' { '{"principalId":"p"}' }
        'role assignment *' {
            if ($args[2] -eq 'delete') { $global:Calls.Add("role delete $($args[4])"); return }
            '[{"id":"/sub-ra","roleDefinitionName":"Contributor","scope":"/subscriptions/s"},
              {"id":"/rg-ra","roleDefinitionName":"Foundry User","scope":"/subscriptions/s/resourceGroups/rg-air-canada-threat-assessment-poc"}]'
        }
        'cognitiveservices account list' { '[{"name":"aif-a","id":"/accounts/aif-a"}]' }
        'cognitiveservices account project' {
            if ($args[3] -eq 'delete') { $global:Calls.Add('project delete'); return }
            '[{"name":"aif-a/proj-a"}]'
        }
        'rest *' { '["/accounts/aif-a/capabilityHosts/h"]' }
        'resource delete *' { $global:Calls.Add('caphost delete') }
        'cognitiveservices account list-deleted' {
            '[{"name":"aif-a","location":"eastus2","id":"/subscriptions/s/resourceGroups/rg-air-canada-threat-assessment-poc/deletedAccounts/aif-a"}]'
        }
        'cognitiveservices account purge' { $global:Calls.Add('purge') }
        default { throw "Unexpected command $verb" }
    }
}
'''
BOTH = 'rg-air-canada-threat-assessment-poc,rg-air-canada-threat-assessment-msi'


@pytest.mark.parametrize('flags,ci,success,expected', [
    ('', False, True, []),
    ('-Delete -ConfirmResourceGroups wrong', False, False, []),
    ('-Delete -ConfirmResourceGroups rg-air-canada-threat-assessment-poc', False, False, []),
    (f'-Delete -ConfirmResourceGroups {BOTH} -Confirm:$false', False, True, [
        'project delete', 'caphost delete', 'azd down', 'purge',
        'group delete rg-air-canada-threat-assessment-msi False', 'role delete /sub-ra']),
    (f'-Delete -ConfirmResourceGroups {BOTH} -Confirm:$false', True, True, [
        'project delete', 'caphost delete', 'azd down', 'purge',
        'group delete rg-air-canada-threat-assessment-msi True']),
    ("-Delete -ConfirmResourceGroups 'rg-air-canada-threat-assessment-msi, rg-air-canada-threat-assessment-poc' "
     '-Confirm:$false', True, True, [
        'project delete', 'caphost delete', 'azd down', 'purge',
        'group delete rg-air-canada-threat-assessment-msi True']),
    ('-KeepPipelineIdentity -Delete -ConfirmResourceGroups rg-air-canada-threat-assessment-poc -Confirm:$false',
     False, True, ['project delete', 'caphost delete', 'azd down', 'purge']),
])
def test_air_canada_teardown(tmp_path, flags, ci, success, expected):
    script = SCRIPT.parent / 'teardown-air-canada.ps1'
    command = AIR_CANADA_MOCK + (
        f"& '{script.as_posix()}' -EvidenceDirectory '{tmp_path.as_posix()}' {flags}; "
        "Write-Output \"CALLS=$($global:Calls -join '|')\""
    )
    environment = {**os.environ, 'GITHUB_ACTIONS': 'true' if ci else 'false'}
    result = subprocess.run([PWSH, '-NoProfile', '-NonInteractive', '-Command', command],
                            env=environment, capture_output=True, text=True, timeout=30, check=False)
    assert (result.returncode == 0) == success, result.stdout + result.stderr
    if success:
        assert f"CALLS={'|'.join(expected)}" in result.stdout, result.stdout
    assert json.loads((tmp_path / 'inventory.json').read_text())['groups']
