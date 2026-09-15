import path from 'node:path';
import fs from 'node:fs';
import { imageSize } from 'image-size';
import { sampleQueries } from '../apps/web-chat/frontend/src/samples.js';

const evidenceDirectory = path.resolve(import.meta.dirname, '../assets/release-evidence');
const runUrl = 'https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34178081808';
const proof = [
  { image: 'pipeline', en: 'Verified Release: Staging to Production', fr: 'Mise en production vérifiée : staging vers production',
    notes: { en: 'Seven release jobs succeeded; recovery skipped. Staging 6; production 33 to 34. Both production gates used normal reviewer approval. PoC environment, not enterprise production certification.', fr: 'Sept jobs réussis, récupération ignorée. Staging 6 ; production de 33 à 34. Les deux portes de production ont reçu une approbation normale. Environnement PoC, pas une certification de production.' } },
  { image: 'evaluations', en: 'Quality Gate: 21 of 21 Judge Checks Passed', fr: 'Porte qualité : 21 vérifications sur 21 réussies',
    notes: { en: 'Eight captures; seven reports judged on coherence, groundedness, task adherence. All 21 passed at unchanged 100% thresholds. inject-001: deterministic safety refusal with no tools, not a judge pass. Zero policy failures. Incomplete output is retried, not rescored.', fr: 'Huit captures ; sept rapports évalués sur la cohérence, l’ancrage et le respect de la tâche. 21 réussites, seuils inchangés à 100 %. inject-001 : refus déterministe sans outil, pas un résultat de juge. Aucune violation. Résultats incomplets relus, pas réévalués.' } },
  { image: 'tools', en: 'Tool Execution Proven; Telemetry Is Synthetic', fr: 'Exécution des outils prouvée ; télémétrie synthétique',
    notes: { en: '28 ToolMessage-derived receipts. tp-001 shows both Defender and both Anomaly tools. Receipts prove execution, not semantic correctness. Synthetic fixtures are not live Defender or airline telemetry. Safety case: no further tools. Bounded evidence attached to response.completed.', fr: '28 reçus issus de ToolMessage. tp-001 montre les deux outils Defender et les deux outils Anomaly. Les reçus prouvent l’exécution, pas la justesse. Données synthétiques, pas une télémétrie Defender ou aérienne réelle. Cas de sécurité : aucun autre outil. Preuves bornées jointes à response.completed.' } },
  { image: 'production', en: 'Production 34: Active, Smoke Test Passed', fr: 'Production 34 : active, test de fumée réussi',
    notes: { en: 'Version 34 active, toolbox 1. Exact-version smoke succeeded. At 02:12:02 UTC AppExceptions for the trailing ten minutes returned zero. Not a ten-minute soak or complete tracing proof. Quality suite ran on staging. Production rebuilds the same source with evaluated MCP digests. Manual recovery; no automatic rollback or canary.', fr: 'Version 34 active, Toolbox 1. Test de cette version réussi. À 02:12:02 UTC, zéro AppExceptions sur les dix dernières minutes. Ni test d’endurance de dix minutes ni preuve de traçage complet. Évaluation en staging. Même code reconstruit en production avec les condensats MCP évalués. Récupération manuelle, sans rollback automatique ni canary.' } },
];

export function addReleaseSlides(pptx, language = 'en') {
  const latestRun = 'https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34427432731';
  const updates = [
    {
      en: ['Current pilot: working chat and verified releases', 'Entra tenant + pilot group', 'Authenticated React / FastAPI chat; public HTTPS, not a private-network deployment.', 'Full-history requests', 'Backend-owned user/assistant turns, store:false; no native conversation or previous_response_id.', 'Verified release and load', 'Release 34427432731 and Continuous Validation 34427429700 succeeded. Synthetic security data only.'],
      fr: ['Pilote actuel : chat et mises en production vérifiés', 'Tenant Entra + groupe pilote', 'Chat React / FastAPI authentifié ; HTTPS public, pas un déploiement réseau privé.', 'Requêtes avec historique complet', 'Tours utilisateur/assistant gérés par le backend, store:false ; sans conversation ni previous_response_id natifs.', 'Déploiement et charge vérifiés', 'Mise en production 34427432731 et validation continue 34427429700 réussies. Données de sécurité synthétiques.'],
    },
    {
      en: ['Live demo: three scenarios, four MCP tools', '1 / Suspicious crew-admin login', 'CREW-PORTAL-01 + crew-admin: correlate MFA failures and success; expect escalation with evidence limits.', '2 / Approved employee travel', 'JDOE-LT-01 + jdoe: reconcile travel and known device; do not invent a compromise.', '3 / Conflicting egress signals', 'OPS-DB-02 + data_egress_mb_per_hour: 900: compare clean endpoint with network anomaly; surface the conflict.'],
      fr: ['Démo : trois scénarios, quatre outils MCP', '1 / Connexion suspecte crew-admin', 'CREW-PORTAL-01 + crew-admin : corréler les échecs MFA et le succès ; escalade avec limites des preuves.', '2 / Déplacement professionnel approuvé', 'JDOE-LT-01 + jdoe : concilier voyage et appareil connu ; ne pas inventer de compromission.', '3 / Signaux réseau contradictoires', 'OPS-DB-02 + data_egress_mb_per_hour: 900 : comparer endpoint sain et anomalie réseau ; signaler le conflit.'],
      notes: sampleQueries.map(sample => `${sample.title}\n${sample.prompt}\nExpected tools: ${sample.tools.join(', ')}`).join('\n\n'),
    },
    {
      en: ['Conversation memory: explicit, bounded, owner-scoped', 'Recall in the same assessment', 'Add reference DEMO-73921, then ask for it without repeating it. All three specialists receive the supplied history.', 'Isolation and retry boundaries', 'A new assessment must not recall that reference. Completed identical message retries replay; changed text with the same key conflicts.', 'No durable history claim', 'Owner-bound in-memory sessions expire; restart loses server state and browser reload loses the local list. No Cosmos, Teams, or durable exactly-once guarantee.'],
      fr: ['Mémoire : explicite, bornée, isolée par propriétaire', 'Rappel dans la même évaluation', 'Ajouter DEMO-73921, puis demander la référence sans la répéter. Les trois spécialistes reçoivent tout l’historique fourni.', 'Isolation et limites des reprises', 'Une nouvelle évaluation ne doit pas rappeler cette référence. Reprise identique terminée : même réponse ; texte modifié avec la même clé : conflit.', 'Pas de persistance durable', 'Sessions en mémoire avec expiration ; redémarrage : état serveur perdu ; rechargement : liste locale perdue. Sans Cosmos, Teams ni garantie durable exactement-une-fois.'],
    },
    {
      en: ['Tool execution is evidence, not model prose', 'Deterministic lookup plan', 'Explicit user device/account/metric fields select real read-only MCP calls. Omitted fields retain prior context; new values replace that category.', 'Strict specialist permissions', 'Investigator: get_device_risk + list_vulnerabilities. Analyst: detect_login_anomalies + score_anomaly. Composer: no tools.', 'Validate actual receipts', 'Successful ToolMessage results become bounded response metadata. Synthetic fixtures and unavailable vulnerability telemetry must remain visible limitations.'],
      fr: ['Exécution des outils : preuves, pas prose du modèle', 'Plan de recherche déterministe', 'Les champs utilisateur appareil/compte/métrique choisissent les appels MCP en lecture seule. Champ omis : contexte conservé ; nouvelle valeur : catégorie remplacée.', 'Permissions des spécialistes', 'Enquêteur : get_device_risk + list_vulnerabilities. Analyste : detect_login_anomalies + score_anomaly. Rédacteur : aucun outil.', 'Vérifier les reçus réels', 'Les ToolMessage réussis alimentent les métadonnées bornées. Données synthétiques et télémétrie de vulnérabilités absente restent des limites explicites.'],
    },
    {
      en: ['Release operations: approval, telemetry, capacity', 'Approve the release, then monitoring', 'Both protected jobs use production approval. Continuous Validation queues behind the shared environment lock; it needs no manual approval.', 'Positive ingestion before zero exceptions', 'Correlate the raw response ID with AppTraces, then check AppExceptions. Empty or invalid query results fail; zero exceptions alone is insufficient.', 'Staging 50k TPM / production 10k TPM', 'Three load failures in 34424723263 correlated with model 429s. Approved staging-only increase; unchanged five-stream gate subsequently passed. Not an SLA or saturation test.'],
      fr: ['Opérations : approbation, télémétrie, capacité', 'Approuver la promotion, puis la surveillance', 'Deux jobs protégés par approbation production. La validation continue attend le verrou partagé ; aucune approbation manuelle pour elle.', 'Ingestion positive avant zéro exception', 'Corréler l’identifiant brut de réponse avec AppTraces, puis vérifier AppExceptions. Résultats vides ou invalides : échec ; zéro exception seul ne suffit pas.', 'Staging 50k TPM / production 10k TPM', 'Trois échecs de charge dans 34424723263 corrélés aux 429 modèle. Hausse staging approuvée ; contrôle inchangé à cinq flux réussi. Ni SLA ni test de saturation.'],
    },
  ];
  for (const update of updates) {
    const content = update[language];
    const slide = pptx.addSlide();
    slide.background = { color: 'FFFFFF' };
    slide.addText(content[0], { x: 0.5, y: 0.35, w: 12.3, h: 0.8, fontSize: 28, bold: true, color: '1A1A1A', fontFace: 'Segoe UI' });
    for (let row = 0; row < 3; row++) {
      const top = 1.5 + row * 1.65;
      slide.addShape('rect', { x: 0.5, y: top, w: 0.06, h: 1.25, fill: { color: ['1A1A1A', '0078D4', 'C8102E'][row] }, line: { transparency: 100 } });
      slide.addText(content[1 + row * 2], { x: 0.75, y: top, w: 11.8, h: 0.4, fontSize: 21, bold: true, color: '1A1A1A', fontFace: 'Segoe UI' });
      slide.addText(content[2 + row * 2], { x: 0.75, y: top + 0.5, w: 11.8, h: 0.85, fontSize: 18, color: '5A5A5A', fontFace: 'Segoe UI', breakLine: false });
    }
    slide.addText('Implementation snapshot | 2026-09-10 UTC | 15098b7 + demo UI refresh', { x: 0.5, y: 7.05, w: 11.7, h: 0.25, fontSize: 10, color: 'C8102E', hyperlink: { url: latestRun } });
    slide.addNotes(`${content.join('\n')}\n${update.notes ?? ''}\nDemo controls populate the draft; Send initiates the authenticated request. Start a new assessment for each independent scenario. Scenarios use exact reviewed English fixture prompts in both language tracks. Source: apps/web-chat/frontend/src/samples.js, src/threat-assessment-agent/graph.py, scripts/invoke-agent.sh, .github/workflows/deploy-and-evaluate.yml. ${latestRun}\nLoad: https://github.com/devopsabcs-engineering/foundry-hosted-agents/actions/runs/34427429700\nHistorical artifact slides that follow retain their original run and version labels.`);
  }
  for (const item of proof) {
    const slide = pptx.addSlide();
    slide.background = { color: 'FFFFFF' };
    slide.addText(`${language === 'en' ? 'Historical proof' : 'Preuve historique'}: ${item[language]}`, { x: 0.45, y: 0.16, w: 12.4, h: 0.55, fontSize: 22, bold: true, color: '1A1A1A', fontFace: 'Segoe UI' });
    const imagePath = path.join(evidenceDirectory, `${item.image}.png`);
    const dimensions = imageSize(fs.readFileSync(imagePath));
    const scale = Math.min(12.63 / dimensions.width, 5.87 / dimensions.height);
    const width = dimensions.width * scale;
    const height = dimensions.height * scale;
    slide.addImage({ path: imagePath, x: (13.33 - width) / 2, y: 0.85 + (5.87 - height) / 2, w: width, h: height, altText: item[language] });
    slide.addText(language === 'en' ? 'Artifact rendering, not a portal screenshot. Synthetic fixtures. Sources and SHA-256 hashes retained.' : 'Rendu des artefacts, pas une capture du portail. Données synthétiques. Sources et SHA-256 conservés.', { x: 0.45, y: 6.83, w: 12.4, h: 0.28, fontSize: 10, color: '5A5A5A', fontFace: 'Segoe UI' });
    slide.addText('GitHub Actions 34178081808 | f3da486 | 2026-09-08 UTC', { x: 0.45, y: 7.14, w: 11.5, h: 0.22, fontSize: 9, color: 'C8102E', hyperlink: { url: runUrl }, fontFace: 'Segoe UI' });
    slide.addNotes(`${item.notes[language]}\nSource: ${runUrl}\nEvidence: assets/release-evidence/source; SHA-256 manifest: assets/release-evidence/manifest.json. Images render downloaded artifacts, not native portal UI.`);
  }
}