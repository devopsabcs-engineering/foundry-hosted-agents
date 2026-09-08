import path from 'node:path';
import fs from 'node:fs';
import { imageSize } from 'image-size';

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
  for (const item of proof) {
    const slide = pptx.addSlide();
    slide.background = { color: 'FFFFFF' };
    slide.addText(item[language], { x: 0.45, y: 0.16, w: 12.4, h: 0.55, fontSize: 24, bold: true, color: '146C54', fontFace: 'Segoe UI' });
    const imagePath = path.join(evidenceDirectory, `${item.image}.png`);
    const dimensions = imageSize(fs.readFileSync(imagePath));
    const scale = Math.min(12.63 / dimensions.width, 5.87 / dimensions.height);
    const width = dimensions.width * scale;
    const height = dimensions.height * scale;
    slide.addImage({ path: imagePath, x: (13.33 - width) / 2, y: 0.85 + (5.87 - height) / 2, w: width, h: height, altText: item[language] });
    slide.addText(language === 'en' ? 'Artifact rendering, not a portal screenshot. Synthetic fixtures. Sources and SHA-256 hashes retained.' : 'Rendu des artefacts, pas une capture du portail. Données synthétiques. Sources et SHA-256 conservés.', { x: 0.45, y: 6.83, w: 12.4, h: 0.28, fontSize: 10, color: '53635E', fontFace: 'Segoe UI' });
    slide.addText('GitHub Actions 34178081808 | f3da486 | 2026-09-08 UTC', { x: 0.45, y: 7.14, w: 11.5, h: 0.22, fontSize: 9, color: '075C9B', hyperlink: { url: runUrl }, fontFace: 'Segoe UI' });
    slide.addNotes(`${item.notes[language]}\nSource: ${runUrl}\nEvidence: assets/release-evidence/source; SHA-256 manifest: assets/release-evidence/manifest.json. Images render downloaded artifacts, not native portal UI.`);
  }
}