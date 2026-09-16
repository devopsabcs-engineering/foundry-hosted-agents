import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PWSH = shutil.which('pwsh')


@pytest.mark.skipif(PWSH is None, reason='PowerShell 7 is required for network preflight tests')
@pytest.mark.parametrize('case,success', [
    ('fresh', True), ('compatible', True), ('production', True), ('missing-subnet', False),
    ('wrong-delegation', False), ('missing-dns', False), ('wrong-agent-subnet', False),
    ('public-foundry-disabled', False), ('legacy-aca', False), ('azure-error', False),
    ('null-response', False), ('incomplete-inventory', False), ('legacy-foundry', False),
    ('recovery', True), ('recovery-wrong-subnet', False),
])
def test_network_readiness(case, success):
    stage = 'production' if case == 'production' else 'staging'
    environment_name = 'test-poc' if stage == 'production' else 'test-staging'
    prefix = 'mcp' if stage == 'production' else 'mcp-staging'
    network_id = '/subscriptions/test/resourceGroups/test/providers/Microsoft.Network/virtualNetworks/test'
    network = {
        'id': network_id, 'location': 'eastus2', 'provisioningState': 'Succeeded',
        'subnets': [
            {'name': f'snet-{kind}-{stage}', 'delegations': [{'serviceName': 'Microsoft.App/environments'}]}
            for kind in ('aca', 'agent')
        ] + [{'name': 'snet-private-endpoints', 'privateEndpointNetworkPolicies': 'Disabled'}],
    }
    links = [{'virtualNetwork': {'id': network_id}, 'provisioningState': 'Succeeded',
              'virtualNetworkLinkState': 'Completed'}]
    accounts = {'value': [{'name': f'aif-{environment_name}', 'properties': {
        'publicNetworkAccess': 'Enabled', 'networkInjections': [{
            'scenario': 'agent', 'subnetArmId': f'{network_id}/subnets/snet-agent-{stage}',
            'useMicrosoftManagedNetwork': False,
        }],
    }}]}
    environments = {'value': [{'name': f'{prefix}-mcp-env', 'properties': {
        'vnetConfiguration': {
            'infrastructureSubnetId': f'{network_id}/subnets/snet-aca-{stage}', 'internal': False,
        },
        'workloadProfiles': [{'name': 'Consumption', 'workloadProfileType': 'Consumption'}],
    }}]}
    if case.startswith('recovery'):
        network['subnets'][1]['name'] = 'snet-agent-staging-recovery'
        accounts['value'][0]['name'] = 'aif-recovery'
        accounts['value'][0]['properties']['networkInjections'][0]['subnetArmId'] = (
            f'{network_id}/subnets/snet-agent-staging-recovery' if case == 'recovery' else 'wrong'
        )
    elif case == 'fresh':
        accounts['value'] = environments['value'] = []
    elif case == 'missing-subnet':
        network['subnets'].pop()
    elif case == 'wrong-delegation':
        network['subnets'][0]['delegations'] = []
    elif case == 'missing-dns':
        links = []
    elif case == 'wrong-agent-subnet':
        accounts['value'][0]['properties']['networkInjections'][0]['subnetArmId'] = 'wrong'
    elif case == 'public-foundry-disabled':
        accounts['value'][0]['properties']['publicNetworkAccess'] = 'Disabled'
    elif case == 'legacy-aca':
        environments['value'][0]['properties']['vnetConfiguration'] = None
    elif case == 'legacy-foundry':
        accounts['value'][0]['properties']['networkInjections'] = None
    elif case == 'null-response':
        network = None
    elif case == 'incomplete-inventory':
        environments['nextLink'] = 'more-results'
    command = r'''
    function global:az {
        $global:LASTEXITCODE = if ($env:CASE -eq 'azure-error') { 1 } else { 0 }
        switch -Wildcard ($args -join ' ') {
            'network vnet show *' { $env:NETWORK }
            'network private-dns link vnet list *' { $env:LINKS }
            'cognitiveservices account list *' { $env:ACCOUNTS }
            '*Microsoft.App/managedEnvironments*' { $env:ENVIRONMENTS }
            default { throw 'Unexpected Azure command' }
        }
    }
    ''' + f"& '{(ROOT / 'scripts/test-network-readiness.ps1').as_posix()}' " + (
        f'-ResourceGroup test -EnvironmentName {environment_name} -Location eastus2 -VnetName test'
    )
    result = subprocess.run(
        [PWSH, '-NoProfile', '-NonInteractive', '-Command', command + (
            ' -AccountName aif-recovery -AgentSubnetName snet-agent-staging-recovery'
            if case.startswith('recovery') else '')],
        env={**os.environ, 'CASE': case, 'NETWORK': json.dumps(network), 'LINKS': json.dumps(links),
             'ACCOUNTS': json.dumps(accounts['value']), 'ENVIRONMENTS': json.dumps(environments)},
        capture_output=True, text=True, timeout=30, check=False,
    )
    assert (result.returncode == 0) == success, result.stdout + result.stderr
