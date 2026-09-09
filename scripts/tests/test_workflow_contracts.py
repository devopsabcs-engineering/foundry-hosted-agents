from pathlib import Path

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