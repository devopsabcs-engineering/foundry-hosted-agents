export const sampleQueries = [
  {
    id: 'tp-001',
    title: 'Suspicious crew-admin login',
    prompt: 'Suspicious login from unknown IP 203.0.113.45 targeting the crew-scheduling admin portal at 02:14 UTC, followed by three failed MFA attempts and a successful login four minutes later from the same IP. Synthetic scenario identifiers: device ID CREW-PORTAL-01, account/user ID crew-admin.',
    tools: ['get_device_risk', 'list_vulnerabilities', 'detect_login_anomalies'],
  },
  {
    id: 'fp-001',
    title: 'Approved employee travel',
    prompt: "Login alert for employee jdoe from IP 198.51.100.22, a country the employee has not logged in from before. Employee's calendar shows an approved business trip to that country starting yesterday, and the device fingerprint matches jdoe's enrolled corporate laptop. Synthetic scenario device ID: JDOE-LT-01; account/user ID: jdoe.",
    tools: ['get_device_risk', 'list_vulnerabilities', 'detect_login_anomalies'],
  },
  {
    id: 'conflict-001',
    title: 'Conflicting egress signals',
    prompt: "Defender reports host OPS-DB-02 as clean with no active alerts, but the anomaly-detection tool independently scores the same host's outbound traffic pattern in the 99th percentile for data-exfiltration risk over the past hour. Synthetic scenario device ID: OPS-DB-02. Observed metric data_egress_mb_per_hour: 900 MB over the past hour; the 99th percentile is a separate reported signal, not a traffic measurement.",
    tools: ['get_device_risk', 'list_vulnerabilities', 'score_anomaly'],
  },
];