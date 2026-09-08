import importlib.util
import json
import os
from pathlib import Path

spec = importlib.util.spec_from_file_location("ci_results", Path(__file__).parents[1] / "ci_results.py")
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


def run(attempt=1):
    return {
        "id": 123,
        "run_attempt": attempt,
        "name": "Continuous Validation",
        "head_sha": "a" * 40,
        "created_at": "2026-09-08T00:00:00Z",
        "conclusion": "failure",
        "repository": {"full_name": "owner/repo"},
    }


def test_missing_evidence_is_not_zero(tmp_path):
    record = report.collect(tmp_path, run(), {"jobs": [{"name": "tests", "conclusion": "failure"}]})
    assert record["tests"] is None
    assert record["evaluation"] is None
    assert record["load"] is None
    assert "N/A" in report.summary(record)
    assert "failure" in report.render_trends([record])


def test_junit_counts_cases_without_double_counting_nested_suites(tmp_path):
    (tmp_path / "tests.xml").write_text(
        '<testsuites><testsuite><testsuite><testcase time="1"/><testcase><failure/></testcase>'
        '<testcase><skipped/></testcase></testsuite></testsuite></testsuites>'
    )
    totals = report.junit_totals(tmp_path)
    assert totals == {
        "tests": 3, "failed": 1, "skipped": 1, "passed": 1, "seconds": 1.0,
        "by_type": {"Other JUnit": 3},
    }


def test_history_is_idempotent_and_preserves_attempts(tmp_path):
    record = report.collect(tmp_path, run(), {"jobs": []})
    report.publish_history(record, tmp_path)
    report.publish_history(record, tmp_path)
    report.publish_history(report.collect(tmp_path, run(2), {"jobs": []}), tmp_path)
    assert len(list((tmp_path / "trend-history").glob("*.json"))) == 2
    assert "123.2" in (tmp_path / "Continuous-Test-Trends.md").read_text()


def test_malformed_evidence_is_visible(tmp_path):
    folder = tmp_path / "evaluation-evidence"
    folder.mkdir()
    (folder / "captured.json").write_text("not json")
    record = report.collect(tmp_path, run(), {"jobs": []})
    assert record["evaluation"] is None
    assert record["data_issues"]


def test_load_route_change_withholds_timings(tmp_path):
    folder = tmp_path / "load-test-evidence"
    folder.mkdir()
    (folder / "concurrent-sessions.json").write_text(
        json.dumps(
            {
                "contract": "completed-text-v2",
                "mode": "concurrent-sessions",
                "requested_count": 5,
                "success_count": 5,
                "error_count": 0,
                "latency_p50_seconds": 3,
                "latency_p95_seconds": 5,
                "wall_clock_seconds": 5,
                "results": [{}] * 5,
            }
        )
    )
    (folder / "context.json").write_text(
        json.dumps({"environment": "staging", "agent_version": "6", "version_after": "7"})
    )
    record = report.collect(tmp_path, run(), {"jobs": []})
    assert record["load"]["latency_p95_seconds"] is None
    assert record["data_issues"]


def test_real_release_results_remain_valid():
    directory = Path(__file__).parents[2] / "assets/release-evidence/source"
    totals = report.evaluation_totals(directory)
    assert totals["captured"] == 8
    assert totals["policy_failures"] == 0
    assert totals["judge_rates"] == dict.fromkeys(report.METRICS, 1.0)


def test_expired_artifacts_do_not_erase_stored_measurements(tmp_path):
    record = report.collect(tmp_path, run(), {"jobs": []})
    record["tests"] = {"tests": 1, "passed": 1, "failed": 0, "skipped": 0, "seconds": 1}
    report.publish_history(record, tmp_path)
    report.publish_history(report.collect(tmp_path, run(), {"jobs": []}), tmp_path)
    assert report.read_json(tmp_path / "trend-history/123-1.json")["tests"]["passed"] == 1


def test_zero_judge_pass_rate_is_reported_not_missing(tmp_path):
    directory = Path(__file__).parents[2] / "assets/release-evidence/source"
    results = report.read_json(directory / "results.json")
    for item in results["items"]:
        for metric in item["results"]:
            metric["passed"] = False
    (tmp_path / "results.json").write_text(json.dumps(results))
    totals = report.evaluation_totals(tmp_path)
    assert totals["judge_rates"] == dict.fromkeys(report.METRICS, 0.0)


def test_charts_and_run_links_with_failed_and_missing_samples(tmp_path):
    records = []
    for index in range(3):
        record = report.collect(tmp_path, run(), {"jobs": []})
        record["run_id"] = index + 100
        record["url"] = f"https://github.com/owner/repo/actions/runs/{index + 100}/attempts/1"
        record["tests"] = {"tests": 2, "passed": 2 - index, "failed": index, "skipped": 0}
        record["context"] = {
            "environment": "staging", "agent_version": "6", "dataset_sha256": "a" * 64,
            "evaluator_sha256": "b" * 64, "judge_deployment": "test-judge",
        }
        record["evaluation"] = {"judge_rates": dict.fromkeys(report.METRICS, 1 - index / 2)}
        record["load"] = {
            "contract": "completed-text-v2", "requested_count": 5,
            "latency_p50_seconds": None if index == 1 else 3 + index,
            "latency_p95_seconds": None if index == 1 else 5 + index,
        }
        records.append(record)
    text = report.render_trends(records)
    assert text.count("```mermaid") == 7
    assert 'bar [100.0, 50.0, 0.0]' in text
    assert 'bar [3, 5]' in text
    assert all(record["url"] in text for record in records)
    preview = os.environ.get("CI_TREND_PREVIEW")
    if preview:
        Path(preview).write_text("Synthetic rendering fixture, not executed CI results.\n\n" + text)


def test_junit_inventory_by_type_includes_skipped_and_empty_suites(tmp_path):
    (tmp_path / "agent.xml").write_text('<testsuite><testcase/><testcase><skipped/></testcase></testsuite>')
    (tmp_path / "deterministic.xml").write_text('<testsuite><testcase><failure/></testcase></testsuite>')
    (tmp_path / "reporting.xml").write_text('<testsuite/>')
    totals = report.junit_totals(tmp_path)
    assert totals["by_type"] == {
        "Agent graph": 2, "Deterministic evaluation": 1, "Reporting and load contracts": 0,
    }
    assert totals["tests"] == sum(totals["by_type"].values()) == 3
    assert totals["skipped"] == 1


def test_test_counts_do_not_invent_historical_breakdowns_or_missing_live_counts():
    counts = report.test_counts({"tests": {"tests": 124}})
    assert counts["Total offline tests"] == 124
    assert all(value is None for name, value in counts.items() if name != "Total offline tests")


def test_inventory_charts_show_growth_and_decline_not_cumulative_runs(tmp_path):
    records = []
    for index, count in enumerate([2, 4, 3], start=1):
        record = report.collect(tmp_path, run(), {"jobs": []})
        record["run_id"] = index
        record["run_number"] = index
        record["tests"] = {
            "tests": count, "passed": count, "failed": 0, "skipped": 0,
            "by_type": {"Agent graph": count},
        }
        records.append(record)
    text = report.render_trends(records)
    assert 'x-axis ["V1.1", "V2.1", "V3.1"]' in text
    assert text.count("bar [2, 4, 3]") == 2
    assert "bar [2, 6, 9]" not in text
    assert "N/A" in text
    assert "| Agent graph | 3 |" in report.summary(records[-1])


def test_live_counts_keep_cases_judges_and_load_requests_separate():
    counts = report.test_counts({
        "evaluation": {"captured": 8, "judged": 7, "judge_rates": dict.fromkeys(report.METRICS, 1)},
        "load": {"requested_count": 5, "success_count": 4, "error_count": 1},
    })
    assert counts["Live evaluation cases"] == 8
    assert counts["Judge checks"] == 21
    assert counts["Load requests"] == 5
    assert counts["Total offline tests"] is None


def test_judge_inventory_without_case_count_remains_unknown():
    counts = report.test_counts({
        "evaluation": {"judge_rates": dict.fromkeys(report.METRICS, 1)},
    })
    assert counts["Judge checks"] is None
