// Renders bilingual (EN/FR) overview decks for the Foundry Hosted Agents
// Workshop from the shared SLIDES content below into
// docs/assets/decks/foundry-hosted-agents-workshop-{en,fr}.pptx.
// Idempotent: re-running regenerates both files from scratch each time.
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(REPO_ROOT, 'docs', 'assets', 'decks');

const C = {
  bgLight: 'FAFBFC',
  blue: '0078D4', blueDark: '003D6B', blueDeep: '001B3D',
  teal: '00B7C3', green: '107C10', amber: 'C46A00', red: 'D13438', purple: '5C2D91',
  textPri: '1A1A1A', textSec: '484848', textLight: '767676',
  border: 'E1E5E8',
};

function newSlide(pptx) {
  const s = pptx.addSlide();
  s.background = { fill: C.bgLight };
  return s;
}

function footer(slide, label) {
  slide.addShape('rect', { x: 0, y: 7.42, w: 13.33, h: 0.03, fill: { color: C.border } });
  slide.addText(label, {
    x: 0.5, y: 7.15, w: 9, h: 0.28, fontSize: 9, color: C.textLight, fontFace: 'Segoe UI',
  });
}

function header(slide, { kicker, title, accent = C.blue }) {
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.09, fill: { color: accent } });
  if (kicker) {
    slide.addText(kicker.toUpperCase(), {
      x: 0.5, y: 0.32, w: 12.3, h: 0.3, fontSize: 11, bold: true, color: accent,
      fontFace: 'Segoe UI', charSpacing: 1,
    });
  }
  slide.addText(title, {
    x: 0.5, y: 0.6, w: 12.3, h: 0.7, fontSize: 26, bold: true, color: C.blueDeep, fontFace: 'Segoe UI',
  });
  slide.addShape('rect', { x: 0.5, y: 1.3, w: 12.3, h: 0.012, fill: { color: C.border } });
}

function bullets(slide, items, opts = {}) {
  const runs = [];
  for (const text of items) {
    runs.push({
      text: `${text}\n`,
      options: {
        color: C.textPri, fontSize: opts.fontSize || 15, fontFace: 'Segoe UI',
        breakLine: true, bullet: { code: '25CF', indent: 20 },
      },
    });
  }
  slide.addText(runs, {
    x: opts.x ?? 0.6, y: opts.y ?? 1.6, w: opts.w ?? 12.1, h: opts.h ?? 5.5,
    valign: 'top', lineSpacingMultiple: 1.25,
  });
}

// ── Shared bilingual slide content ──────────────────────────────────────
// Each entry: { kicker, title: {en, fr}, bullets: {en: [...], fr: [...]} }
const SLIDES = [
  {
    isTitle: true,
    title: {
      en: 'Foundry Hosted Agents Workshop',
      fr: 'Atelier Foundry Hosted Agents',
    },
    subtitle: {
      en: 'Hands-on: hosting a real LangGraph multi-agent system on Microsoft Foundry',
      fr: 'Pratique : héberger un véritable système multi-agent LangGraph sur Microsoft Foundry',
    },
  },
  {
    kicker: { en: 'Agenda', fr: 'Programme' },
    title: { en: 'Nine Labs, One Real Deployment', fr: 'Neuf labs, un déploiement réel' },
    bullets: {
      en: [
        'Lab 00 — Prerequisites and environment setup',
        'Lab 01 — Architecture deep dive (LangGraph supervisor/specialists)',
        'Lab 02 — Deploy the MCP tool servers',
        'Lab 03 — Provision and deploy the hosted agent (azd)',
        'Lab 04 — Invoke the agent and read traces',
        'Lab 05 — Evaluations: deterministic + LLM-as-judge',
        'Lab 06 — CI/CD: evaluation-gated release pipeline',
        'Lab 07 — Real-world troubleshooting: RBAC 401',
        'Lab 08 — Production readiness and decision gates',
      ],
      fr: [
        'Lab 00 — Prérequis et configuration de l\u2019environnement',
        'Lab 01 — Plongée dans l\u2019architecture (superviseur/spécialistes LangGraph)',
        'Lab 02 — Déployer les serveurs d\u2019outils MCP',
        'Lab 03 — Provisionner et déployer l\u2019agent hébergé (azd)',
        'Lab 04 — Invoquer l\u2019agent et lire les traces',
        'Lab 05 — Évaluations : déterministes + LLM-as-judge',
        'Lab 06 — CI/CD : pipeline contrôlé par évaluation',
        'Lab 07 — Dépannage réel : erreur RBAC 401',
        'Lab 08 — Préparation à la production et portes de décision',
      ],
    },
  },
  {
    kicker: { en: 'Architecture', fr: 'Architecture' },
    title: { en: 'Supervisor + Specialist Graph', fr: 'Graphe superviseur + spécialistes' },
    bullets: {
      en: [
        'A LangGraph supervisor routes to three specialist nodes: Evidence Investigator, Risk Analyst, Report Composer',
        'Each specialist has its own prompt, tool permissions, and evaluation criteria',
        'Tool isolation by role: Evidence Investigator \u2192 defender-conn only, Risk Analyst \u2192 anomaly-conn only',
        'The Report Composer has zero tool access — it only synthesizes',
        'A known platform-side tool-resolution gap degrades gracefully to an honestly-labeled plain-LLM analysis instead of crashing',
      ],
      fr: [
        'Un superviseur LangGraph route vers trois nœuds spécialistes : Enquêteur de preuves, Analyste de risque, Rédacteur de rapport',
        'Chaque spécialiste a son propre prompt, ses permissions d\u2019outils et ses critères d\u2019évaluation',
        'Isolation des outils par rôle : Enquêteur de preuves \u2192 defender-conn uniquement, Analyste de risque \u2192 anomaly-conn uniquement',
        'Le Rédacteur de rapport n\u2019a aucun accès aux outils — il ne fait que synthétiser',
        'Une lacune connue côté plateforme dans la résolution d\u2019outils dégrade gracieusement vers une analyse LLM simple, honnêtement étiquetée, plutôt que de planter',
      ],
    },
  },
  {
    kicker: { en: 'Tools', fr: 'Outils' },
    title: { en: 'Four Layers: Implement, Host, Register, Consume', fr: 'Quatre couches : implémenter, héberger, enregistrer, consommer' },
    bullets: {
      en: [
        'Layer 1 — Implementation: custom MCP server code (Defender tools, anomaly tools)',
        'Layer 2 — Hosting: independent Azure Container Apps, own auth/networking/health checks',
        'Layer 3 — Registration: Foundry connections define endpoint + credential policy per MCP server',
        'Layer 4 — Consumption: Foundry Toolbox aggregates registered tools for reuse across agents',
        'The Toolbox is the registration/aggregation layer — not the hosting runtime for your MCP code',
      ],
      fr: [
        'Couche 1 — Implémentation : code de serveur MCP personnalisé (outils Defender, outils anomalie)',
        'Couche 2 — Hébergement : Azure Container Apps indépendantes, authentification/réseau/santé propres',
        'Couche 3 — Enregistrement : les connexions Foundry définissent le point de terminaison + la politique d\u2019identifiants par serveur MCP',
        'Couche 4 — Consommation : la Foundry Toolbox agrège les outils enregistrés pour réutilisation entre agents',
        'La Toolbox est la couche d\u2019enregistrement/agrégation — pas le runtime d\u2019hébergement de votre code MCP',
      ],
    },
  },
  {
    kicker: { en: 'Deployment', fr: 'Déploiement' },
    title: { en: 'One Manifest: azure.yaml + azd', fr: 'Un manifeste : azure.yaml + azd' },
    bullets: {
      en: [
        'azure.yaml wires the Foundry project, model deployment, Toolbox connections, and the hosted agent service',
        'kind: hosted \u2014 Foundry operates the session compute; you own only the graph code',
        'dependencyResolution: remote_build \u2014 Foundry builds your Python dependencies server-side',
        'protocol: responses \u2014 OpenAI-compatible Responses protocol with streaming support',
        'azd provision creates infrastructure; azd deploy publishes a new agent version — separate lifecycles',
      ],
      fr: [
        'azure.yaml câble le projet Foundry, le déploiement de modèle, les connexions Toolbox et le service d\u2019agent hébergé',
        'kind: hosted — Foundry exploite le calcul de session ; vous ne possédez que le code du graphe',
        'dependencyResolution: remote_build — Foundry construit vos dépendances Python côté serveur',
        'protocol: responses — protocole Responses compatible OpenAI avec support du streaming',
        'azd provision crée l\u2019infrastructure ; azd deploy publie une nouvelle version d\u2019agent — cycles de vie séparés',
      ],
    },
  },
  {
    kicker: { en: 'Evaluation', fr: 'Évaluation' },
    title: { en: 'Deterministic Checks + LLM-as-Judge Rubrics', fr: 'Vérifications déterministes + rubriques LLM-as-judge' },
    bullets: {
      en: [
        'Golden dataset: 8 categories (true/false positive, ambiguous, missing data, conflicting tools, prompt injection, unauthorized actions, unsupported conclusions)',
        'Deterministic: schema validity, required citations, allowed tool calls, policy constraints — fast, reproducible',
        'Built-in Foundry evaluators first: coherence, groundedness, task adherence, tool-call accuracy',
        'Custom rubrics only where the catalog doesn\u2019t reach: triage correctness, citation quality, conflict handling',
        'Policy rules (e.g. never claim an unauthorized remediation action) stay deterministic, not LLM-judged',
      ],
      fr: [
        'Jeu de données de référence : 8 catégories (vrai/faux positif, ambigu, données manquantes, outils contradictoires, injection de prompt, actions non autorisées, conclusions non étayées)',
        'Déterministe : validité du schéma, citations requises, appels d\u2019outils autorisés, contraintes de politique — rapide, reproductible',
        'Évaluateurs Foundry intégrés en premier : cohérence, ancrage, adhérence à la tâche, précision des appels d\u2019outils',
        'Rubriques personnalisées uniquement là où le catalogue ne suffit pas : justesse du triage, qualité des citations, gestion des conflits',
        'Les règles de politique (ex. ne jamais prétendre avoir agi sans autorisation) restent déterministes, pas jugées par LLM',
      ],
    },
  },
  {
    kicker: { en: 'CI/CD', fr: 'CI/CD' },
    title: { en: 'Evaluation-Gated Release Pipeline', fr: 'Pipeline de mise en production contrôlé par évaluation' },
    bullets: {
      en: [
        'Two pipelines: hosted-agent-cd.yml (direct to shared PoC env) and deploy-and-evaluate.yml (full staging \u2192 production flow)',
        'Full flow: lint/tests \u2192 Bicep validate \u2192 deploy immutable candidate to staging \u2192 smoke/contract/streaming tests',
        'Offline evaluation quality gate runs against the staging candidate before any manual production approval',
        'Secretless OIDC federation — no stored client secrets in either pipeline',
        'Lesson learned: auto-firing both pipelines on every push raced against the same shared resource — now manual-dispatch only',
      ],
      fr: [
        'Deux pipelines : hosted-agent-cd.yml (direct vers l\u2019environnement PoC partagé) et deploy-and-evaluate.yml (flux complet staging \u2192 production)',
        'Flux complet : lint/tests \u2192 validation Bicep \u2192 déploiement d\u2019un candidat immuable en staging \u2192 tests de fumée/contrat/streaming',
        'La porte de qualité d\u2019évaluation hors ligne s\u2019exécute contre le candidat de staging avant toute approbation manuelle de production',
        'Fédération OIDC sans secret — aucun secret client stocké dans les deux pipelines',
        'Leçon apprise : déclencher automatiquement les deux pipelines à chaque push entrait en concurrence sur la même ressource partagée — désormais manuel uniquement',
      ],
    },
  },
  {
    kicker: { en: 'Real-world troubleshooting', fr: 'Dépannage réel' },
    title: { en: 'Diagnosing a Live RBAC 401 (Still Open)', fr: 'Diagnostiquer un vrai 401 RBAC (encore ouvert)' },
    accent: C.red,
    bullets: {
      en: [
        'Symptom: 401 PermissionDenied on Azure OpenAI chat completions from the hosted agent\u2019s own Instance Identity',
        'Don\u2019t trust the error message\u2019s own diagnosis — verify the role assignment directly with az role assignment list',
        'Read the built-in role\u2019s dataActions from az role definition list — proves the role does cover the exact data action',
        'Check disableLocalAuth, networkAcls, and Azure Policy state to rule out silent overrides',
        'Enumerate tenant Conditional Access policies for service-principal-targeted conditions',
        'A working manual-agent path next to a failing hosted-agent path points at the platform, not customer-side RBAC',
      ],
      fr: [
        'Symptôme : 401 PermissionDenied sur les complétions de chat Azure OpenAI depuis l\u2019identité propre de l\u2019agent hébergé',
        'Ne pas faire confiance au diagnostic du message d\u2019erreur — vérifier directement l\u2019attribution de rôle avec az role assignment list',
        'Lire les dataActions du rôle intégré via az role definition list — prouve que le rôle couvre bien l\u2019action de données exacte',
        'Vérifier disableLocalAuth, networkAcls et l\u2019état des politiques Azure pour écarter les remplacements silencieux',
        'Énumérer les politiques d\u2019accès conditionnel du tenant ciblant les principaux de service',
        'Un chemin d\u2019agent manuel fonctionnel à côté d\u2019un chemin d\u2019agent hébergé défaillant pointe vers la plateforme, pas le RBAC côté client',
      ],
    },
  },
  {
    kicker: { en: 'Production readiness', fr: 'Préparation à la production' },
    title: { en: 'Honest Gates, Not False Confidence', fr: 'Des portes honnêtes, pas une fausse confiance' },
    bullets: {
      en: [
        'Four experiment tracks: load testing, Cosmos DB checkpointer, Agent 365 onboarding, continuous evaluation',
        'Quality gate: Pass — golden dataset + 12/12 deterministic checks + rubric mapping',
        'Scale, Security, Operations gates: Conditional — partial evidence, named follow-ups',
        'Platform status, Data, Cost gates: Not testable in this PoC — require commercial/legal/platform confirmation',
        'Overall recommendation: conditional go for continued PoC-to-pilot investment, not an unconditional yes/no',
      ],
      fr: [
        'Quatre pistes d\u2019expérimentation : test de charge, checkpointer Cosmos DB, intégration Agent 365, évaluation continue',
        'Porte Qualité : Pass — jeu de données de référence + 12/12 vérifications déterministes + correspondance des rubriques',
        'Portes Échelle, Sécurité, Opérations : Conditional — preuves partielles, suivis nommés',
        'Portes Statut de plateforme, Données, Coût : Not testable in this PoC — nécessitent une confirmation commerciale/juridique/plateforme',
        'Recommandation globale : go conditionnel pour poursuivre l\u2019investissement PoC vers pilote, pas un oui/non net',
      ],
    },
  },
  {
    kicker: { en: 'Wrap-up', fr: 'Conclusion' },
    title: { en: 'Everything Here Is Real', fr: 'Tout ici est réel' },
    bullets: {
      en: [
        'Every command, screenshot, and log excerpt in this workshop comes from a real deployment, not a simulation',
        'Repository: github.com/devopsabcs-engineering/foundry-hosted-agents',
        'Wiki: architecture notes, manual-agent workaround, and the live RBAC 401 investigation log',
        'Full bilingual step-by-step labs: this deck\u2019s companion GitHub Pages site',
        'Fork it, run it, and follow WI-11 as it resolves',
      ],
      fr: [
        'Chaque commande, capture d\u2019écran et extrait de journal de cet atelier provient d\u2019un déploiement réel, pas d\u2019une simulation',
        'Dépôt : github.com/devopsabcs-engineering/foundry-hosted-agents',
        'Wiki : notes d\u2019architecture, contournement manuel de l\u2019agent, et le journal d\u2019investigation RBAC 401 en direct',
        'Labs complets, bilingues, pas à pas : le site GitHub Pages compagnon de ce deck',
        'Forkez-le, exécutez-le, et suivez la résolution de WI-11',
      ],
    },
  },
];

function buildDeck(lang) {
  const pptx = new PptxGenJS();
  pptx.defineLayout({ name: 'WIDE', width: 13.33, height: 7.5 });
  pptx.layout = 'WIDE';

  SLIDES.forEach((def, i) => {
    const s = newSlide(pptx);
    if (def.isTitle) {
      s.addShape('rect', { x: 0, y: 0, w: 13.33, h: 7.5, fill: { color: C.blueDeep } });
      s.addText(def.title[lang], {
        x: 0.8, y: 2.7, w: 11.7, h: 1.3, fontSize: 40, bold: true, color: 'FFFFFF', fontFace: 'Segoe UI',
      });
      s.addText(def.subtitle[lang], {
        x: 0.8, y: 3.9, w: 11.7, h: 0.8, fontSize: 18, color: 'CFE4FA', fontFace: 'Segoe UI', italic: true,
      });
      s.addText(lang === 'en' ? 'devopsabcs-engineering/foundry-hosted-agents' : 'devopsabcs-engineering/foundry-hosted-agents', {
        x: 0.8, y: 6.7, w: 11.7, h: 0.4, fontSize: 12, color: '8AB4E0', fontFace: 'Segoe UI',
      });
      return;
    }
    header(s, { kicker: def.kicker[lang], title: def.title[lang], accent: def.accent });
    bullets(s, def.bullets[lang]);
    footer(s, `${lang === 'en' ? 'Foundry Hosted Agents Workshop' : 'Atelier Foundry Hosted Agents'} — ${i} / ${SLIDES.length - 1}`);
  });

  return pptx;
}

async function main() {
  const fs = await import('node:fs');
  fs.mkdirSync(OUT_DIR, { recursive: true });

  const en = buildDeck('en');
  await en.writeFile({ fileName: path.join(OUT_DIR, 'foundry-hosted-agents-workshop-en.pptx') });

  const fr = buildDeck('fr');
  await fr.writeFile({ fileName: path.join(OUT_DIR, 'foundry-hosted-agents-workshop-fr.pptx') });

  console.log('Wrote:', OUT_DIR);
}

main();
