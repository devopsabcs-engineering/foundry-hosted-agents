import importlib.util
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


SCRIPT = Path(__file__).resolve().parents[1] / "deployment_summary.py"
SPEC = importlib.util.spec_from_file_location("deployment_summary", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_clickable_deployment_inventory():
    summary = MODULE.render()
    links = re.findall(r"\[([^]]+)\]\(([^)]+)\)", summary)
    assert len(links) == 15
    assert len({label for label, _ in links}) == len(links)
    assert all(urlsplit(url).scheme == "https" for _, url in links)
    assert f"[Try staging web chatbot]({MODULE.WEB_URL})" in summary
    assert "not proof that this run deployed" in summary
    assert "Authenticated POST API, not a browser chat page" in summary
    assert "no production web frontend" in summary


def test_current_urls_match_published_entry_points():
    summary = MODULE.render()
    for retired in ("wonderfulpebble-ce861678", "ambitioussea-69c7df60",
                    "aif-air-canada-threat-assessment-staging"):
        assert retired not in summary
    assert "aif-air-canada-staging-vnet" in summary
    assert "mcp-defender-server.redbush-f3ffad44" in summary
    for relative_path in ("README.md", "docs/index.md", "docs/fr/index.md"):
        content = (SCRIPT.parents[1] / relative_path).read_text(encoding="utf-8")
        assert MODULE.WEB_URL in content
        assert "wonderfulpebble-ce861678" not in content


def test_appends_without_overwriting_job_results(tmp_path):
    destination = tmp_path / "summary.md"
    destination.write_text("Existing test results\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, "GITHUB_STEP_SUMMARY": str(destination)},
        capture_output=True, text=True, check=True,
    )
    assert result.stdout == ""
    summary = destination.read_text(encoding="utf-8")
    assert summary.startswith("Existing test results\n")
    assert "## Deployment Links" in summary


def test_web_test_categories(tmp_path):
    from scripts.ci_results import junit_totals

    for name in ("backend", "frontend"):
        (tmp_path / f"{name}.xml").write_text(
            '<testsuites><testsuite><testcase name="example" time="0.1"/></testsuite></testsuites>',
            encoding="utf-8",
        )
    totals = junit_totals(tmp_path)
    assert totals["passed"] == 2
    assert totals["by_type"] == {"Web chat backend": 1, "Web chat frontend": 1}