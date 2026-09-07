import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def load_server(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "mcp" / name / "main.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_unknown_identifiers_do_not_fabricate_telemetry():
    defender = load_server("defender-server")
    anomaly = load_server("anomaly-server")
    assert "error" in defender.get_device_risk("198.51.100.7")
    assert "error" in defender.list_vulnerabilities("unknown")
    result = anomaly.detect_login_anomalies("unknown")
    assert "error" in result
    assert "anomalousLogins" not in result


@pytest.mark.parametrize("device", [
    "CREW-PORTAL-01", "JDOE-LT-01", "BACKUP-SRV-01", "OPS-DB-02", "AUTH-SRV-01", "CONTRACTOR-LT-77",
])
def test_scenario_devices_have_explicit_synthetic_records(device):
    result = load_server("defender-server").get_device_risk(device)
    assert result["deviceId"] == device
    assert result["synthetic"] is True
    assert "error" not in result


def test_missing_and_conflicting_evidence_stay_distinct():
    defender = load_server("defender-server")
    anomaly = load_server("anomaly-server")
    assert "offline" in defender.get_device_risk("FIN-WKS-014")["error"]
    assert defender.get_device_risk("OPS-DB-02")["riskScore"] == "Low"
    assert anomaly.score_anomaly("data_egress_mb_per_hour", 900)["severity"] == "high"
    assert anomaly.detect_login_anomalies("jdoe")["severity"] == "low"
    assert anomaly.detect_login_anomalies("jsmith")["bruteForceConfirmed"] is True


def test_golden_inputs_match_mock_identifiers():
    lines = (ROOT / "eval/golden-dataset.jsonl").read_text().splitlines()
    records = {record["id"]: record for record in map(json.loads, lines)}
    assert len(records) == 8
    identifiers = {
        "tp-001": ("CREW-PORTAL-01", "crew-admin"),
        "fp-001": ("JDOE-LT-01", "jdoe"),
        "amb-001": ("BACKUP-SRV-01", "svc-backup"),
        "unauth-001": ("AUTH-SRV-01", "jsmith"),
        "unsup-001": ("CONTRACTOR-LT-77", "contractor-77"),
    }
    for case_id, (device_id, user_id) in identifiers.items():
        content = records[case_id]["input"]["messages"][0]["content"]
        assert device_id in content and user_id in content
        assert "error" not in load_server("defender-server").get_device_risk(device_id)
        assert "error" not in load_server("anomaly-server").detect_login_anomalies(user_id)
        assert records[case_id]["reviewed_by"] == "repository-owner"
    conflict = records["conflict-001"]["input"]["messages"][0]["content"]
    assert "data_egress_mb_per_hour: 900" in conflict
    assert "OPS-DB-02" in conflict