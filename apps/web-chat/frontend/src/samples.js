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

const frenchSamples = {
  'tp-001': {
    title: 'Connexion suspecte du compte crew-admin',
    prompt: "Connexion suspecte depuis l'adresse IP inconnue 203.0.113.45 au portail d'administration de planification des \u00e9quipages \u00e0 02:14 UTC, suivie de trois \u00e9checs MFA et d'une connexion r\u00e9ussie quatre minutes plus tard depuis la m\u00eame adresse IP. Identifiants du sc\u00e9nario synth\u00e9tique : appareil CREW-PORTAL-01, compte/utilisateur crew-admin.",
  },
  'fp-001': {
    title: 'D\u00e9placement professionnel approuv\u00e9',
    prompt: "Alerte de connexion pour jdoe depuis l'adresse IP 198.51.100.22, dans un pays depuis lequel cette personne ne s'est jamais connect\u00e9e. Son calendrier indique un d\u00e9placement professionnel approuv\u00e9 dans ce pays depuis hier, et l'empreinte de l'appareil correspond \u00e0 son ordinateur portable professionnel inscrit. Identifiants du sc\u00e9nario synth\u00e9tique : appareil JDOE-LT-01; compte/utilisateur jdoe.",
  },
  'conflict-001': {
    title: 'Signaux contradictoires de trafic sortant',
    prompt: "Defender indique que l'h\u00f4te OPS-DB-02 est sain et sans alerte active, mais l'outil de d\u00e9tection d'anomalies classe ind\u00e9pendamment son trafic sortant au 99e percentile du risque d'exfiltration de donn\u00e9es au cours de la derni\u00e8re heure. Identifiant d'appareil du sc\u00e9nario synth\u00e9tique : OPS-DB-02. Mesure observ\u00e9e data_egress_mb_per_hour : 900 MB au cours de la derni\u00e8re heure; le 99e percentile est un signal rapport\u00e9 distinct, et non une mesure du trafic.",
  },
};

export function queriesForLanguage(language) {
  return sampleQueries.map(sample => language === 'fr-CA'
    ? { ...sample, ...frenchSamples[sample.id] } : sample);
}