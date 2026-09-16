from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

from scripts.ci_results import run_label


ROOT = Path(__file__).resolve().parents[2]


def workflow(name):
    return yaml.safe_load((ROOT / ".github/workflows" / name).read_text(encoding="utf-8"))


def test_legacy_entrypoint_cannot_bypass_release_gates():
    legacy = workflow("hosted-agent-cd.yml")
    assert legacy["jobs"] == {"release": {
        "uses": "./.github/workflows/deploy-and-evaluate.yml", "secrets": "inherit"}}
    assert "concurrency" not in legacy
    release = workflow("deploy-and-evaluate.yml")
    assert "workflow_call" in release.get("on", release.get(True))
    assert release["concurrency"]["group"] == "foundry-shared-environments"
    publisher = workflow("publish-test-trends.yml")
    assert "Hosted Agent CI/CD" in publisher.get("on", publisher.get(True))["workflow_run"]["workflows"]


def test_legacy_release_has_release_trend_label():
    assert run_label({"workflow": "Hosted Agent CI/CD", "run_number": 12, "attempt": 2}) == "R12.2"


def test_smoke_uses_pinned_session_without_persisted_conversation():
    release = workflow("deploy-and-evaluate.yml")
    invocations = [step["run"] for job in release["jobs"].values() for step in job.get("steps", [])
                   if "bash scripts/invoke-agent.sh" in step.get("run", "")]
    assert len(invocations) == 2
    assert all("validate-agent-response.jq" in script for script in invocations)
    helper = (ROOT / "scripts/invoke-agent.sh").read_text(encoding="utf-8")
    assert 'agent_version:$version' in helper
    assert '/endpoint/sessions?api-version=v1' in helper
    assert 'agent_session_id:$session' in helper
    assert 'stream:true,store:false' in helper
    assert 'conversation' not in helper
    assert '--fail-with-body' in helper
    assert '--new-conversation' not in (ROOT / '.github/workflows/deploy-and-evaluate.yml').read_text()


def test_hosted_telemetry_uses_environment_specific_monitoring_output():
    config = yaml.safe_load((ROOT / "azure.yaml").read_text(encoding="utf-8"))
    settings = {item["name"]: item["value"] for item in
                config["services"]["threat-assessment-agent"]["environmentVariables"]}
    assert settings["APPLICATIONINSIGHTS_CONNECTION_STRING"] == "${applicationInsightsConnectionString}"
    assert settings["FOUNDRY_TOOLBOX_MCP_ENDPOINT"] == "${TOOLBOX_SECURITY_TOOLS_MCP_ENDPOINT}"
    assert "FOUNDRY_TOOLBOX_VERSION" not in settings
    assert "output applicationInsightsConnectionString string = monitoring.outputs.applicationInsightsConnectionString" in (
        ROOT / "infra/main.bicep").read_text(encoding="utf-8")
    infrastructure = (ROOT / "infra/main.bicep").read_text(encoding="utf-8")
    connection = (ROOT / "infra/modules/ai-foundry.bicep").read_text(encoding="utf-8")
    assert "applicationInsightsResourceId: monitoring.outputs.applicationInsightsId" in infrastructure
    assert "applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString" in infrastructure
    assert "category: 'AppInsights'" in connection
    assert "target: applicationInsightsResourceId" in connection
    assert "key: applicationInsightsConnectionString" in connection


def test_capacity_increase_is_staging_only():
    infrastructure = (ROOT / "infra/main.bicep").read_text(encoding="utf-8")
    assert "param modelSkuCapacity int = endsWith(environmentName, '-staging') ? 50 : 10" in infrastructure
    assert "modelSkuCapacity: modelSkuCapacity" in infrastructure


def test_project_identity_can_access_evaluation_assets():
    foundry = (ROOT / 'infra/modules/ai-foundry.bicep').read_text(encoding='utf-8')
    assignment = foundry.split('resource projectEvaluationRole ', 1)[1].split('\nresource ', 1)[0]
    assert 'scope: project' in assignment
    assert 'principalId: project.identity.principalId' in assignment
    assert "'53ca6127-db72-4b80-b1b0-d745d6d5456d'" in assignment


def test_release_checks_network_before_provisioning():
    release = workflow('deploy-and-evaluate.yml')
    validation = '\n'.join(step.get('run', '') for step in release['jobs']['bicep-validate']['steps'])
    for template in ('infra/network.bicep', 'infra/main.bicep', 'infra/modules/cosmos-db.bicep'):
        assert f'az bicep build --file {template}' in validation
    assert validation.index('test-network-readiness.ps1') < validation.index('az deployment group what-if')
    for job_name in ('deploy-staging', 'promote-production'):
        steps = release['jobs'][job_name]['steps']
        provision = next(step for step in steps if 'azd provision' in step.get('run', ''))
        assert provision['shell'] == 'pwsh'
        assert provision['run'].index('test-network-readiness.ps1') < provision['run'].index('azd provision')
        assert '-VnetName $env:VNET_NAME' in provision['run']
        assert any('azd env set VNET_NAME' in step.get('run', '') for step in steps)
    assert 'az deployment group create' not in validation


def test_staging_recovery_target_is_consistent():
    release = workflow('deploy-and-evaluate.yml')
    assert release['env']['STAGING_FOUNDRY_ACCOUNT_NAME'] == 'aif-air-canada-staging-vnet'
    assert release['env']['STAGING_FOUNDRY_PROJECT_NAME'] == 'proj-air-canada-staging-vnet'
    assert release['env']['STAGING_AGENT_SUBNET_NAME'] == 'snet-agent-staging-recovery'
    for job_name in ('bicep-validate', 'deploy-staging'):
        script = '\n'.join(step.get('run', '') for step in release['jobs'][job_name]['steps'])
        assert '-AccountName $env:STAGING_FOUNDRY_ACCOUNT_NAME' in script
        assert '-AgentSubnetName $env:STAGING_AGENT_SUBNET_NAME' in script
    staging = '\n'.join(step.get('run', '') for step in release['jobs']['deploy-staging']['steps'])
    for setting in ('FOUNDRY_ACCOUNT_NAME', 'FOUNDRY_PROJECT_NAME', 'AGENT_SUBNET_NAME'):
        assert f'azd env set {setting} "$STAGING_{setting}"' in staging
        assert ('https://${STAGING_FOUNDRY_ACCOUNT_NAME}.services.ai.azure.com/api/projects/'
            '${STAGING_FOUNDRY_PROJECT_NAME}') in staging
    endpoint = (f"https://{release['env']['STAGING_FOUNDRY_ACCOUNT_NAME']}.services.ai.azure.com/api/projects/"
                f"{release['env']['STAGING_FOUNDRY_PROJECT_NAME']}")
    continuous = workflow('continuous-validation.yml')
    assert any(job.get('env', {}).get('PROJECT_ENDPOINT') == endpoint for job in continuous['jobs'].values())
    web = (ROOT / 'infra/web-chat.bicep').read_text(encoding='utf-8')
    assert f"param foundryAccountName string = '{release['env']['STAGING_FOUNDRY_ACCOUNT_NAME']}'" in web
    assert f"param foundryProjectName string = '{release['env']['STAGING_FOUNDRY_PROJECT_NAME']}'" in web


def test_hybrid_network_contract_keeps_cosmos_optional():
    main = (ROOT / 'infra/main.bicep').read_text(encoding='utf-8')
    foundry = (ROOT / 'infra/modules/ai-foundry.bicep').read_text(encoding='utf-8')
    cosmos = (ROOT / 'infra/modules/cosmos-db.bicep').read_text(encoding='utf-8')
    private_endpoint = (ROOT / 'infra/modules/cosmos-private-endpoint.bicep').read_text(encoding='utf-8')
    aca = (ROOT / 'infra/modules/mcp-container-apps.bicep').read_text(encoding='utf-8')
    assert "publicNetworkAccess: 'Enabled'" in foundry
    assert 'subnetArmId: agentSubnetId' in foundry
    assert 'useMicrosoftManagedNetwork: false' in foundry
    assert "publicNetworkAccess: 'Disabled'" in cosmos
    assert 'disableLocalAuth: true' in cosmos
    assert "module privateEndpoint 'cosmos-private-endpoint.bicep'" in cosmos
    assert "groupIds: ['Sql']" in private_endpoint
    assert 'privateDnsZoneGroups' in private_endpoint
    assert "databaseAccounts@2024-11-15' existing" in private_endpoint
    assert 'sqlDatabases' not in private_endpoint
    assert "'/partition_key'" in cosmos
    assert 'infrastructureSubnetId: infrastructureSubnetId' in aca
    assert 'internal: false' in aca
    assert "workloadProfileType: 'Consumption'" in aca
    assert 'agentSubnetId: vnet::agentSubnet.id' in main
    assert 'infrastructureSubnetId: vnet::acaSubnet.id' in main
    assert 'cosmos-db.bicep' not in main
    assert "module network " not in main
    config = yaml.safe_load((ROOT / 'azure.yaml').read_text(encoding='utf-8'))
    settings = config['services']['threat-assessment-agent']['environmentVariables']
    assert not any(item['name'] == 'ENABLE_COSMOS_CHECKPOINTER' for item in settings)


@pytest.mark.parametrize("trace_count,exception_count,expected", [
    ("0", "0", 1),
    ("", "0", 1),
    ("invalid", "0", 1),
    ("1", "0", 0),
    ("1", "1", 1),
    ("1", "", 1),
])
def test_monitoring_gate_requires_ingestion(trace_count, exception_count, expected):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = str(git_bash) if git_bash.exists() else shutil.which("bash")
    assert bash, "Bash is required for workflow behavior checks"
    steps = workflow("deploy-and-evaluate.yml")["jobs"]["post-deploy-monitoring"]["steps"]
    gate = next(step["run"] for step in steps if step["name"].startswith("Check Application Insights"))
    gate = gate.replace("${{ vars.AZURE_RESOURCE_GROUP }}", "test-group")
    gate = gate.replace("${{ vars.LOG_ANALYTICS_WORKSPACE_NAME }}", "test-workspace")
    gate = gate.replace("/tmp/prod-smoke-response.sse", "/dev/null")
    stubs = f"""
az() {{
    case "$*" in
        *"workspace show"*) echo test-workspace ;;
        *"AppTraces"*)
            [[ "$*" == *"contains 'resp_probe'"* ]] || return 1
            printf '%s\\n' '{trace_count}' ;;
        *) printf '%s\\n' '{exception_count}' ;;
    esac
}}
jq() {{
    if [[ "$1" == *r* ]]; then echo resp_probe; else echo '\"resp_probe\"'; fi
}}
sleep() {{ :; }}
"""
    result = subprocess.run([bash, "-c", stubs + gate], capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == expected, result.stdout + result.stderr