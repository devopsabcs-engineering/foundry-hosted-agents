"""Minimal MCP server exposing mocked Microsoft Defender-derived tools.

Runs fully independently of the LangGraph agent process
(src/threat-assessment-agent) -- no shared runtime, module, or import. Tool
data is stubbed/mocked; this PoC demonstrates the decoupled MCP hosting
pattern, not real Defender API integration.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

PORT = int(os.environ.get("PORT", "8000"))

mcp = FastMCP("defender-mcp-server", host="0.0.0.0", port=PORT)

_MOCK_DEVICES = {
    "device-001": {
        "deviceId": "device-001",
        "hostName": "yyz-gate-kiosk-01",
        "riskScore": "High",
        "exposureLevel": "Medium",
        "osPlatform": "Windows10",
        "healthStatus": "Active",
    },
    "device-002": {
        "deviceId": "device-002",
        "hostName": "yul-checkin-03",
        "riskScore": "Low",
        "exposureLevel": "Low",
        "osPlatform": "Windows11",
        "healthStatus": "Active",
    },
}

_MOCK_VULNERABILITIES = {
    "device-001": [
        {"cveId": "CVE-2024-21306", "severity": "Critical", "cvssScore": 9.8},
        {"cveId": "CVE-2024-30040", "severity": "High", "cvssScore": 8.1},
    ],
    "device-002": [],
}

_SCENARIO_DEVICES = {
    "CREW-PORTAL-01": {"riskScore": "High", "activeAlerts": ["Repeated MFA failures followed by successful login"], "sourceIp": "203.0.113.45"},
    "JDOE-LT-01": {"riskScore": "Low", "activeAlerts": [], "enrolledUser": "jdoe", "corporateDeviceMatch": True},
    "BACKUP-SRV-01": {"riskScore": "Unknown", "activeAlerts": [], "limitations": ["No login-time baseline or corroborating target log"]},
    "FIN-WKS-014": {"riskScore": "Unknown", "error": "Telemetry unavailable: agent offline for 24 hours"},
    "OPS-DB-02": {"riskScore": "Low", "activeAlerts": [], "scanResult": "Clean endpoint scan; network activity not assessed"},
    "AUTH-SRV-01": {"riskScore": "High", "activeAlerts": ["Confirmed brute-force against account jsmith"], "sourceIp": "198.51.100.7"},
    "CONTRACTOR-LT-77": {"riskScore": "Unknown", "activeAlerts": [], "limitations": ["Single failed login only; no corroborating signals"]},
}


@mcp.tool()
def get_device_risk(device_id: str) -> dict:
    """Look up the Defender risk profile for a device (mocked)."""
    if device_id in _SCENARIO_DEVICES:
        return {"deviceId": device_id, "synthetic": True, **_SCENARIO_DEVICES[device_id]}
    return _MOCK_DEVICES.get(
        device_id,
        {"deviceId": device_id, "riskScore": "Unknown", "error": "device not found"},
    )


@mcp.tool()
def list_vulnerabilities(device_id: str) -> dict:
    """List known vulnerabilities affecting a device (mocked)."""
    if device_id not in _MOCK_VULNERABILITIES:
        return {"deviceId": device_id, "synthetic": True, "error": "Vulnerability telemetry unavailable for this device"}
    return {"deviceId": device_id, "synthetic": True, "vulnerabilities": _MOCK_VULNERABILITIES[device_id]}


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
