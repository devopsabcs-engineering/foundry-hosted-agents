"""Minimal MCP server exposing mocked anomaly-detection tools.

Runs fully independently of the LangGraph agent process
(src/threat-assessment-agent) -- no shared runtime, module, or import. Tool
data is stubbed/mocked; this PoC demonstrates the decoupled MCP hosting
pattern, not real anomaly-detection integration.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))

mcp = FastMCP("anomaly-mcp-server", host="0.0.0.0", port=PORT)

_MOCK_BASELINES = {
    "failed_logins_per_hour": 3.0,
    "data_egress_mb_per_hour": 120.0,
}

_MOCK_LOGINS = {
    "crew-admin": {"anomalousLogins": 1, "failedMfaAttempts": 3, "successfulLoginAfterMfaFailures": True, "sourceIp": "203.0.113.45", "severity": "high"},
    "jdoe": {"anomalousLogins": 0, "approvedTravel": True, "corporateDeviceMatch": True, "severity": "low"},
    "svc-backup": {"failedLogins": 1, "severity": "unknown", "limitations": ["Missing historical baseline and corroborating target log"]},
    "jsmith": {"bruteForceConfirmed": True, "sourceIp": "198.51.100.7", "severity": "high"},
    "contractor-77": {"failedLogins": 1, "corroboratingSignals": 0, "severity": "unknown"},
    "user-042": {"anomalousLogins": 2, "impossibleTravelDetected": True, "confidence": 0.87},
}


@mcp.tool()
def score_anomaly(metric: str, value: float) -> dict:
    """Score an observed metric value against its historical baseline (mocked)."""
    baseline = _MOCK_BASELINES.get(metric)
    if baseline is None:
        return {"metric": metric, "value": value, "error": "unknown metric"}
    deviation = (value - baseline) / baseline if baseline else 0.0
    severity = "high" if deviation > 2 else "medium" if deviation > 0.5 else "low"
    return {
        "synthetic": True,
        "metric": metric,
        "value": value,
        "baseline": baseline,
        "deviation": round(deviation, 2),
        "severity": severity,
    }


@mcp.tool()
def detect_login_anomalies(user_id: str) -> dict:
    """Detect anomalous login patterns for a user account (mocked)."""
    return {
        "userId": user_id,
        "synthetic": True,
        **_MOCK_LOGINS.get(user_id, {"error": "No anomaly telemetry available for this account"}),
    }


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
