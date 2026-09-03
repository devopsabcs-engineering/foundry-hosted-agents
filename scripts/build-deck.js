// Renders deliverables/air-canada-foundry-hosted-agents-decision.pptx from deliverables/deck-outline.md.
// Idempotent: re-running regenerates the file from scratch each time (pptxgenjs is create-only).
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import PptxGenJS from 'pptxgenjs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const OUTPUT_PATH = path.join(REPO_ROOT, 'deliverables', 'air-canada-foundry-hosted-agents-decision.pptx');

// ── Color palette ────────────────────────────────────────────────────────
const C = {
  white: 'FFFFFF', bgLight: 'FAFBFC',
  blue: '0078D4', blueDark: '003D6B', blueDeep: '001B3D',
  teal: '00B7C3', green: '107C10', amber: 'C46A00', red: 'D13438', purple: '5C2D91',
  textPri: '1A1A1A', textSec: '484848', textLight: '767676',
  border: 'E1E5E8', card: 'FFFFFF', shadow: 'D0D4D8',
  accent5: 'F0F7FF', accent10: 'E1EFFF',
};

// ── Confidence tag legend (matches deck-outline.md § Confidence Tagging Legend) ──
const TAGS = {
  confirmed: { label: 'CONFIRMED', color: C.green },
  preview: { label: 'PREVIEW', color: C.blue },
  inferred: { label: 'INFERRED', color: C.purple },
  'requires-validation': { label: 'REQUIRES VALIDATION', color: C.red },
};

const appendixLog = [];
let coreSlideCounter = 0;
const CORE_SLIDE_TOTAL = 12;

// ── Helpers ──────────────────────────────────────────────────────────────

function newSlide(pptx) {
  const s = pptx.addSlide();
  s.background = { fill: C.bgLight };
  return s;
}

function footer(slide, sectionLabel) {
  slide.addShape('rect', { x: 0, y: 7.42, w: 13.33, h: 0.03, fill: { color: C.border } });
  slide.addText(sectionLabel, {
    x: 0.5, y: 7.15, w: 9, h: 0.28, fontSize: 9, color: C.textLight, fontFace: 'Segoe UI',
  });
  // Page number ("n / total") is stamped once at the end, after the final slide count is known.
}

function slideHeader(slide, { kicker, title, objective, accent = C.blue }) {
  slide.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.09, fill: { color: accent } });
  if (kicker) {
    slide.addText(kicker.toUpperCase(), {
      x: 0.5, y: 0.32, w: 12.3, h: 0.3, fontSize: 11, bold: true, color: accent,
      fontFace: 'Segoe UI', charSpacing: 1,
    });
  }
  slide.addText(title, {
    x: 0.5, y: 0.6, w: 12.3, h: 0.6, fontSize: 26, bold: true, color: C.blueDeep, fontFace: 'Segoe UI',
  });
  if (objective) {
    slide.addText(objective, {
      x: 0.5, y: 1.18, w: 12.3, h: 0.4, fontSize: 13, italic: true, color: C.textSec, fontFace: 'Segoe UI',
    });
  }
  slide.addShape('rect', { x: 0.5, y: objective ? 1.62 : 1.3, w: 12.3, h: 0.012, fill: { color: C.border } });
}

/** items: [{ tag: 'confirmed'|'preview'|'inferred'|'requires-validation', text }] */
function taggedBullets(slide, items, opts = {}) {
  const runs = [];
  for (const { tag, text } of items) {
    const t = TAGS[tag];
    if (!t) throw new Error(`Unknown confidence tag: ${tag}`);
    runs.push({
      text: `${t.label}  `,
      options: {
        bold: true, color: t.color, fontSize: opts.fontSize ? opts.fontSize - 1 : 10,
        fontFace: 'Segoe UI', bullet: { code: '25CF', indent: 18 },
      },
    });
    runs.push({
      text: `${text}\n`,
      options: {
        color: C.textPri, fontSize: opts.fontSize || 12, fontFace: 'Segoe UI', breakLine: true,
      },
    });
  }
  slide.addText(runs, {
    x: opts.x ?? 0.55, y: opts.y ?? 1.85, w: opts.w ?? 12.2, h: opts.h ?? 5.3,
    valign: 'top', lineSpacingMultiple: opts.lineSpacingMultiple ?? 1.12,
  });
}

function legendStrip(slide, { x = 0.55, y = 6.55, w = 12.2 } = {}) {
  const keys = Object.keys(TAGS);
  const segW = w / keys.length;
  keys.forEach((k, i) => {
    const t = TAGS[k];
    slide.addShape('ellipse', { x: x + i * segW, y: y + 0.04, w: 0.14, h: 0.14, fill: { color: t.color } });
    slide.addText(t.label, {
      x: x + i * segW + 0.2, y, w: segW - 0.25, h: 0.24, fontSize: 9, bold: true, color: t.color, fontFace: 'Segoe UI',
    });
  });
}

function dataTable(slide, { headers, rows, x = 0.4, y = 1.85, w = 12.5, colW, fontSize = 9, rowH }) {
  const headerRow = headers.map((h) => ({
    text: h,
    options: { bold: true, fill: { color: C.blueDark }, color: C.white, fontSize: fontSize + 1, fontFace: 'Segoe UI', valign: 'middle' },
  }));
  const bodyRows = rows.map((row, i) => row.map((cell) => ({
    text: String(cell),
    options: { fill: { color: i % 2 === 0 ? C.white : C.accent5 }, color: C.textPri, fontSize, fontFace: 'Segoe UI', valign: 'top' },
  })));
  slide.addTable([headerRow, ...bodyRows], {
    x, y, w, colW,
    ...(rowH ? { rowH } : {}),
    border: { color: C.border, pt: 0.5 },
    autoPage: false,
  });
}

// ── Core slide builder ──────────────────────────────────────────────────

function coreSlide(pptx, { title, objective, bullets, source }) {
  coreSlideCounter += 1;
  const s = newSlide(pptx);
  slideHeader(s, { kicker: `Core Slide ${coreSlideCounter} of ${CORE_SLIDE_TOTAL}`, title, objective });
  taggedBullets(s, bullets, { y: 1.85, h: 5.15 });
  if (source) s.addNotes(`Source: ${source}`);
  footer(s, 'Air Canada — Foundry Hosted Agents Decision');
  return s;
}

function appendixBulletSlide(pptx, { code, title, part, bullets, note, source }) {
  const s = newSlide(pptx);
  const label = `Appendix ${code}${part ? ` (${part})` : ''} — ${title}`;
  slideHeader(s, { kicker: 'Appendix', title: label, accent: C.purple });
  taggedBullets(s, bullets, { y: 1.7, h: note ? 4.7 : 5.3, fontSize: 12.5 });
  if (note) {
    s.addShape('rect', { x: 0.55, y: 6.45, w: 12.2, h: 0.01, fill: { color: C.border } });
    s.addText(note, { x: 0.55, y: 6.55, w: 12.2, h: 0.55, fontSize: 10.5, italic: true, color: C.textSec, fontFace: 'Segoe UI' });
  }
  if (source) s.addNotes(`Source: ${source}`);
  footer(s, 'Air Canada — Foundry Hosted Agents Decision · Appendix');
  appendixLog.push(label);
  return s;
}

function appendixTableSlide(pptx, { code, title, part, headers, rows, colW, note, fontSize, source }) {
  const s = newSlide(pptx);
  const label = `Appendix ${code}${part ? ` (${part})` : ''} — ${title}`;
  slideHeader(s, { kicker: 'Appendix', title: label, accent: C.purple });
  dataTable(s, { headers, rows, colW, fontSize: fontSize || 9, y: 1.75 });
  if (note) {
    s.addText(note, { x: 0.4, y: 6.85, w: 12.5, h: 0.45, fontSize: 9.5, italic: true, color: C.textSec, fontFace: 'Segoe UI' });
  }
  if (source) s.addNotes(`Source: ${source}`);
  footer(s, 'Air Canada — Foundry Hosted Agents Decision · Appendix');
  appendixLog.push(label);
  return s;
}

// ── Build the deck ───────────────────────────────────────────────────────

const pptx = new PptxGenJS();
pptx.author = 'Air Canada Foundry Hosted Agents PoC Team';
pptx.title = 'Air Canada — Foundry Hosted Agents Decision and Multi-Agent PoC';
pptx.layout = 'LAYOUT_WIDE';

// SLIDE — TITLE
{
  const s = newSlide(pptx);
  s.background = { fill: C.blueDeep };
  s.addShape('rect', { x: 0, y: 0, w: 13.33, h: 0.14, fill: { color: C.teal } });
  s.addText('Air Canada', {
    x: 0.9, y: 2.15, w: 11.5, h: 0.55, fontSize: 22, bold: true, color: C.teal, fontFace: 'Segoe UI', charSpacing: 2,
  });
  s.addText('Foundry Hosted Agents Decision and Multi-Agent PoC', {
    x: 0.9, y: 2.65, w: 11.5, h: 1.3, fontSize: 40, bold: true, color: C.white, fontFace: 'Segoe UI',
  });
  s.addText('Executive decision deck — LangGraph hosting options, phased PoC recommendation, and production-readiness gates', {
    x: 0.9, y: 3.95, w: 11.5, h: 0.6, fontSize: 16, color: C.accent10, fontFace: 'Segoe UI',
  });
  s.addShape('rect', { x: 0.9, y: 4.7, w: 4.2, h: 0.02, fill: { color: C.teal } });
  s.addText(
    'Every claim on this deck is labeled CONFIRMED / PREVIEW / INFERRED / REQUIRES VALIDATION — see Appendix B.',
    { x: 0.9, y: 6.9, w: 11.5, h: 0.4, fontSize: 11, italic: true, color: C.accent10, fontFace: 'Segoe UI' },
  );
  legendStrip(s, { x: 0.9, y: 6.45, w: 11.5 });
  s.addNotes('Source: research.md (Lines 1-6, task framing)');
}

// CORE SLIDES 1-12
coreSlide(pptx, {
  title: 'Decision Required',
  objective: 'Frame the single decision Air Canada must make: select a reusable hosting blueprint for LangGraph agents.',
  bullets: [
    { tag: 'confirmed', text: 'Decision framing: adopt, validate, or defer a hosting blueprint for future LangGraph agents.' },
    { tag: 'confirmed', text: 'Foundry Hosted Agents is the leading PoC candidate — not yet an unconditional production selection.' },
    { tag: 'confirmed', text: "This deck separates what today's evidence proves from what the PoC must still prove." },
  ],
  source: 'research.md (Lines 535-537, 5, 420, 27-32)',
});

coreSlide(pptx, {
  title: "Air Canada's Requirements",
  objective: 'Show the ten enterprise capabilities the PoC must prove.',
  bullets: [
    { tag: 'confirmed', text: 'Ten capabilities to prove: scaling, MCP tools, multi-agent behavior, evaluations, CI/CD, streaming, state, governance, cost, and production readiness.' },
    { tag: 'confirmed', text: 'These map 1:1 to the Production Decision Gates categories used later in the deck.' },
  ],
  source: 'research.md (Lines 538-539, 572-583)',
});

coreSlide(pptx, {
  title: 'Product Landscape — Five Operating Models',
  objective: 'Separate five materially different operating models without conflating open-source LangGraph and paid LangSmith topologies.',
  bullets: [
    { tag: 'confirmed', text: 'Model 1 — OSS LangGraph on customer-managed Azure compute: Air Canada owns runtime, queueing, scaling, persistence, and recovery.' },
    { tag: 'confirmed', text: 'Model 2 — LangSmith Deployment Cloud: LangChain operates Agent Server; separate SaaS billing and control plane.' },
    { tag: 'requires-validation', text: 'Model 3 — LangSmith self-hosted Enterprise on Azure: Enterprise license plus customer-operated stack; Azure BYOC is only "planned for 2H 2026."' },
    { tag: 'confirmed', text: 'Model 4 — Foundry Hosted Agent baseline: Foundry operates session compute; Air Canada owns graph code; no Cosmos DB, no Agent 365.' },
    { tag: 'requires-validation', text: 'Model 4 limits (capacity, SLA) are not yet quantified.' },
    { tag: 'confirmed', text: 'Model 5 — Phased Foundry target: baseline plus evidence-gated optional extensions (Cosmos DB, Agent 365, continuous evaluation, A2A); each extension individually requires validation.' },
    { tag: 'confirmed', text: 'Full dimension-by-dimension comparison lives in Appendix A.' },
  ],
  source: 'research.md (Lines 326-421, 489-506)',
});

coreSlide(pptx, {
  title: 'Recommendation',
  objective: 'Run a phased Foundry PoC with explicit go/no-go gates; separate the stable baseline from optional extensions.',
  bullets: [
    { tag: 'confirmed', text: 'Recommended baseline: one hosted deployment with a genuine LangGraph supervisor + specialist-agent graph, Responses SSE, external MCP via Foundry connections/Toolbox, Application Insights, and offline evaluations.' },
    { tag: 'confirmed', text: 'Cosmos DB, Agent 365, continuous evaluation, and a second A2A-hosted agent are separate, individually gated experiments — not baseline dependencies.' },
    { tag: 'confirmed', text: 'Why not the other four models: OSS LangGraph = highest engineering burden; LangSmith Cloud = separate SaaS/billing dependency; LangSmith Enterprise = licensing plus highest ops burden; Microsoft Agent Framework not selected because Air Canada has an existing LangGraph investment.' },
  ],
  source: 'research.md (Line 418, Lines 394-416, Lines 469-475)',
});

coreSlide(pptx, {
  title: 'Runtime Architecture — Multi-Agent',
  objective: 'Show genuine multi-agent behavior in one deployment; A2A shown only as a dashed future boundary.',
  bullets: [
    { tag: 'confirmed', text: 'Graph composition: Supervisor \u2192 Evidence Investigator + Risk Analyst \u2192 Report Composer, all inside one hosted LangGraph deployment.' },
    { tag: 'confirmed', text: 'Each role has separate prompts, tool permissions, state contracts, and evaluation criteria despite sharing one deployment.' },
    { tag: 'preview', text: 'Cross-deployment A2A delegation to a second hosted agent is a preview experiment, justified only by independent ownership/release/isolation/scaling needs — not a baseline requirement.' },
    { tag: 'requires-validation', text: 'No documented hard limit on graph node count or depth; the practical constraint is per-session sandbox CPU/memory, stated inconsistently across two Microsoft doc pages (0.5-2 vCPU fixed vs. 0.25-4.0 vCPU continuous).' },
  ],
  source: 'research.md (Lines 420-437, 386-388, 559)',
});

coreSlide(pptx, {
  title: 'Tools and MCP',
  objective: 'Separate implementation, hosting, registration, and consumption into four distinct layers.',
  bullets: [
    { tag: 'confirmed', text: 'Layer 1 — Implementation: custom MCP server code (Defender tools, Anomaly tools).' },
    { tag: 'confirmed', text: 'Layer 2 — Hosting: independent Azure runtime (Container Apps, Functions, or App Service); owns its own auth, networking, versioning, health checks, and throttling.' },
    { tag: 'confirmed', text: 'Layer 3 — Registration: Foundry connections define endpoint and credential policy per MCP server.' },
    { tag: 'requires-validation', text: 'Layer 3 private-path reachability is untested.' },
    { tag: 'confirmed', text: 'Layer 4 — Consumption: Foundry Toolbox aggregates registered tools for reuse; LangGraph consumes via supported client libraries.' },
    { tag: 'requires-validation', text: 'Layer 4 private connectivity requires validation.' },
    { tag: 'confirmed', text: 'Toolbox is the registration/aggregation layer, not the hosting runtime for custom MCP server code — a documented distinction to avoid at architecture review.' },
  ],
  source: 'research.md (Lines 424-430)',
});

coreSlide(pptx, {
  title: 'State and History',
  objective: 'Choose one runtime source of truth; compare Responses history, application-owned Cosmos checkpoints, and Standard Agent Setup capability hosts.',
  bullets: [
    { tag: 'confirmed', text: 'Option 1 — Foundry Responses history: platform-managed conversation history; sufficient for basic multi-turn interaction; no Cosmos DB required.' },
    { tag: 'confirmed', text: 'Option 2 package (langchain-azure-cosmosdb, CosmosDBSaver) is co-maintained by LangChain and Microsoft.' },
    { tag: 'inferred', text: 'Option 2 becomes authoritative graph state only when durable checkpoints, human-in-the-loop pause/resume, time travel, or app-controlled state are required — Hosted Agent pairing is untested.' },
    { tag: 'confirmed', text: 'Option 3 — Standard Agent Setup via capabilityHosts (BYO Cosmos DB / Storage / AI Search): needed only for data-residency/compliance, a separate Bicep tier from Basic Agent Setup.' },
    { tag: 'requires-validation', text: 'No user-scoped conversation-list API was found in the researched documentation — an evidence gap, not proof of absence.' },
    { tag: 'confirmed', text: 'A sidebar can store metadata/identifiers without duplicating message bodies; duplicate-content compliance requirements need explicit retention/deletion/legal-hold design.' },
  ],
  source: 'research.md (Lines 313-320, 373-400, 556-557)',
});

coreSlide(pptx, {
  title: 'Scaling and Cost',
  objective: 'Show that the scaling model is understood, but capacity and price are not yet quantified — unknowns stay visible.',
  bullets: [
    { tag: 'confirmed', text: 'Scaling model: per-session isolation (each session is its own VM-isolated sandbox), not per-replica; idle timeout 5-60 min (default 15) triggers scale-to-zero with automatic state restore.' },
    { tag: 'confirmed', text: 'Billing model: vCPU-hour + GiB-hour of active session compute only — closest to Azure Container Apps consumption plan, not AKS always-on or App Service continuous billing.' },
    { tag: 'requires-validation', text: 'Unknown / TBD: exact $/vCPU-hr and $/GiB-hr rates (public pricing page showed "N/A"); maximum concurrent sessions; requests-per-second ceiling; same-thread turn concurrency; cold-start latency distribution.' },
    { tag: 'confirmed', text: 'Known cost drivers (formulas, not totals): model tokens, active session vCPU/memory, idle window, MCP hosting, telemetry, evaluation tokens, optional Cosmos DB and Agent 365 licensing, operations labor — amounts require validation.' },
    { tag: 'confirmed', text: 'Full load-test matrix in Appendix E.' },
  ],
  source: 'research.md (Lines 388, 570, 576-579, 620)',
});

coreSlide(pptx, {
  title: 'Evaluation',
  objective: 'Gate production releases on security-task outcomes, not generic fluency.',
  bullets: [
    { tag: 'confirmed', text: 'Baseline: offline evaluation of versioned candidate outputs against a human-reviewed golden dataset (true/false positives, ambiguous evidence, missing data, conflicting tools, prompt injection, unauthorized actions, unsupported conclusions).' },
    { tag: 'confirmed', text: 'Deterministic checks: schema validity, required citations, allowed tool calls, policy constraints.' },
    { tag: 'confirmed', text: 'Model-based evaluators: relevance, groundedness, task adherence, rubric scoring (built-in evaluator catalog exists).' },
    { tag: 'confirmed', text: 'Human review required for high-impact vulnerability conclusions and any recommendation triggering remediation or operational change.' },
    { tag: 'preview', text: 'Continuous evaluation of sampled production traffic is a separate preview and privacy decision — redaction and retention must be defined before enabling.' },
    { tag: 'requires-validation', text: 'GitHub Action (microsoft/ai-agent-evals@v3-beta) targeting the deployed hosted-agent name/version, and portal visibility of action-created runs.' },
  ],
  source: 'research.md (Lines 298, 508-513, 566-567)',
});

coreSlide(pptx, {
  title: 'Automation (CI/CD)',
  objective: 'Evaluate every candidate before production traffic moves; show the full staging-to-rollback pipeline.',
  bullets: [
    { tag: 'confirmed', text: 'Pipeline: lint/unit tests/dependency scan \u2192 Bicep validate + what-if \u2192 deploy immutable candidate to staging \u2192 smoke/contract/streaming tests \u2192 offline evaluation quality gate \u2192 manual production approval \u2192 deploy production version \u2192 canary/explicit route switch \u2192 post-deploy checks/monitoring \u2192 rollback on breach.' },
    { tag: 'confirmed', text: 'Bicep provisions infrastructure; azd or Foundry APIs deploy agent versions as a separate lifecycle from infrastructure changes.' },
    { tag: 'confirmed', text: 'Evaluations run against a non-production candidate before traffic promotion; continuous evaluation (if approved) monitors production after release and does not replace the release gate.' },
  ],
  source: 'research.md (Lines 518-533)',
});

coreSlide(pptx, {
  title: 'Governance and Readiness',
  objective: 'Separate confirmed identity/RBAC controls from validation tracks and open blockers.',
  bullets: [
    { tag: 'confirmed', text: 'Confirmed baseline controls: each hosted agent gets an auto-created, dedicated Entra ID identity at deploy time (no manual managed-identity wiring); Foundry RBAC role family; Application Insights / OpenTelemetry tracing.' },
    { tag: 'confirmed', text: "Explicit warning: don't assign Cognitive Services * roles to a CI/CD identity — Foundry has its own role family for this." },
    { tag: 'inferred', text: 'Agent 365 governance/registry onboarding: Agent 365 and Entra Agent ID are GA; SDK packages exist for Foundry tooling and LangChain observability — but no dedicated Hosted Agent onboarding guide, no confirmed LangGraph-specific package, and no proof a platform-created identity can be migrated in place.' },
    { tag: 'requires-validation', text: 'Platform SLA / GA status / regions / quotas / capacity / cold starts / disaster recovery — first Production Decision Gate item.' },
  ],
  source: 'research.md (Lines 300-306, 568, 576)',
});

coreSlide(pptx, {
  title: 'PoC Plan and Decision Gates',
  objective: 'Four increments produce a defensible production decision, with owners, exit criteria, and a decision date.',
  bullets: [
    { tag: 'confirmed', text: 'Increment 1 — Baseline Hosted Agent & LangGraph Multi-Agent Runtime: supervisor graph + 3 specialist nodes; azure-ai-agentserver-langgraph wrapper on Responses protocol (port 8088); validate local run, Responses SSE, built-in conversation history; provision via Bicep, deploy via azd.' },
    { tag: 'confirmed', text: 'Increment 2 — Decoupled MCP Tool Hosting & Foundry Integration: Defender + Anomaly MCP servers on Container Apps with system-assigned managed identities and private networking; register as Foundry Custom Connections; bundle into Toolbox.' },
    { tag: 'confirmed', text: 'Increment 3 — Offline Security Evaluation Suite & Automated CI/CD Gates: versioned golden dataset; deterministic schema checks + LLM-as-judge rubrics; GitHub Actions gate with threshold-gated promotion.' },
    { tag: 'confirmed', text: 'Increment 4 — Validation Tracks, Load Testing & Production Decision Gates: Load & Scale Gate, State Experiment Track, Governance Validation Track, Continuous Evaluation Track, Deliverable Synthesis — plan of record; individual track outcomes require validation.' },
    { tag: 'confirmed', text: 'Decision gates requiring evidence before production approval: Platform status, Scale, Security, Data, Quality, Operations, Cost, Preview acceptance — full list in Appendix H.' },
    { tag: 'requires-validation', text: 'Owners and decision date: not specified in the research document — open item for the presenting team to fill in before delivery.' },
  ],
  source: 'research.md (Lines 572-611)',
});

// APPENDIX A — Five-Option Comparison Matrix (split across 3 slides for legibility)
{
  const cols = ['Dimension', 'OSS LangGraph on Azure compute', 'LangSmith Deployment Cloud', 'LangSmith self-hosted Enterprise', 'Foundry Hosted Agent baseline', 'Phased Foundry target'];
  const colW = [1.7, 2.16, 2.16, 2.16, 2.16, 2.16];
  const matrix = [
    ['Runtime ownership', 'Air Canada operates API, queue, scaling, persistence, recovery', 'LangChain operates Agent Server', 'Air Canada operates LangSmith stack on Azure', 'Foundry operates session compute; Air Canada owns graph code', 'Same as baseline plus evidence-approved extensions'],
    ['License and billing', 'No LangSmith hosting license; Azure compute/ops costs', 'LangSmith seats plus LCU/LSU usage', 'Enterprise license plus Azure infra/ops', 'Azure model, session compute, MCP hosting, telemetry', 'Baseline plus Cosmos DB and any Agent 365 licenses'],
    ['Azure fit', 'Full Azure control, highest engineering burden', 'Separate SaaS control and billing plane', 'Azure-hosted but separate licensed platform', 'Azure-native project, identity, deployment, monitoring', 'Azure-native runtime with optional M365 governance'],
    ['Scaling evidence', 'Determined by chosen App Service/Container Apps/AKS design', 'Managed by LangChain service', 'Customer-operated Kubernetes scaling', 'Per-session isolation and scale-to-zero documented; limits/SLA unverified', 'Same as baseline; dependencies add their own limits'],
    ['Tools and MCP', 'Customer builds hosting, auth, registry, reuse', 'LangGraph and custom MCP patterns', 'Same as Cloud but customer-operated', 'External MCP runtime plus Foundry connection and Toolbox aggregation', 'Same as baseline'],
    ['Multi-agent', 'Native LangGraph supervisor, subgraphs, handoffs', 'Same plus Agent Server services', 'Same plus self-hosted Agent Server services', 'Native LangGraph supervisor and specialist agents in one deployment', 'Optional A2A split after preview and boundary gates'],
    ['Streaming', 'Implement/operate selected LangGraph stream modes', 'Agent Server streaming', 'Agent Server streaming, customer-operated', 'Responses SSE confirmed; full LangGraph event parity unverified', 'Same as baseline'],
    ['State and history', 'Customer selects/operates checkpointer and conversation index', 'Native Agent Server threads and runs', 'Native Agent Server storage, customer-operated', 'Foundry Responses history baseline', 'Optional Cosmos graph checkpoints or Standard platform dependencies'],
    ['Evaluations', 'Customer-authored pipeline; Foundry batch evaluation can still score outputs', 'LangSmith evaluation stack', 'LangSmith evaluation stack', 'Foundry local and batch evaluation confirmed', 'Optional continuous evaluation and hosted-agent action integration after validation'],
    ['Governance', 'Azure-native controls designed by customer', 'LangSmith Enterprise controls', 'LangSmith controls plus Azure infra controls', 'Per-agent Entra identity, Foundry RBAC, Application Insights', 'Optional Agent 365 onboarding after tenant validation'],
    ['Operational burden', 'High', 'Low to medium', 'Highest', 'Lowest candidate', 'Medium, proportional to selected extensions'],
    ['Best fit', 'Maximum control without paid Agent Server features', 'Teams already buying LangSmith, accepting SaaS', 'Teams requiring LangSmith features and customer-owned data plane', 'Air Canada PoC baseline', 'Conditional production target after gates pass'],
  ];
  const parts = [matrix.slice(0, 4), matrix.slice(4, 8), matrix.slice(8, 12)];
  parts.forEach((rows, i) => {
    appendixTableSlide(pptx, {
      code: 'A', title: 'Five-Option Comparison Matrix', part: `${i + 1} of ${parts.length}`,
      headers: cols, rows, colW, fontSize: 8,
      note: 'Confidence: confirmed as a comparative synthesis of the five scenarios (each cell carries the same confidence tag as its corresponding scenario section, Core Slides 3-4).',
      source: 'research.md (Lines 489-506)',
    });
  });
}

// APPENDIX B — Evidence Confidence Register (split across 2 slides)
{
  const cols = ['Capability', 'Confidence', 'Customer-facing statement'];
  const colW = [3.6, 2.6, 6.3];
  const register = [
    ['LangGraph hosted as custom Foundry code', 'Confirmed by product documentation and samples', 'Suitable for PoC implementation'],
    ['Responses SSE progressive output', 'Confirmed; application parity untested', 'Supported, with PoC contract and reconnect testing required'],
    ['Per-session isolation and scale-to-zero', 'Confirmed mechanism; limits and SLA unknown', 'Promising scaling model, not yet a capacity commitment'],
    ['External MCP plus connection and Toolbox aggregation', 'Documented pattern; private path untested', 'Recommended decoupling design, subject to network and auth validation'],
    ['Supervisor and specialist agents in one graph', 'Confirmed LangGraph pattern', 'Production baseline for genuine multi-agent behavior'],
    ['Cross-deployment A2A delegation', 'Sampled but preview', 'Optional experiment, not a baseline dependency'],
    ['Foundry Responses conversation history', 'Confirmed for basic multi-turn use', 'Baseline state option; sidebar and retention requirements need testing'],
    ['Cosmos DB LangGraph checkpointer', 'Package confirmed; Hosted Agent pairing untested', 'Conditional state experiment'],
    ['Offline and batch evaluation of LangGraph outputs', 'Confirmed', 'Baseline release-gate mechanism'],
    ['Continuous evaluation', 'Documented but preview', 'Optional production-monitoring experiment'],
    ['GitHub Action targeting Hosted Agent versions and portal visibility', 'Not verified', 'Must be proven before claiming evaluation synchronization'],
    ['Agent 365 onboarding and LangGraph instrumentation', 'Partially evidenced, exact path unverified', 'Governance option to validate, not a confirmed architecture property'],
    ['Hosted Agent pricing, quotas, and SLA', 'Insufficient current evidence', 'Obtain live commercial and platform confirmation before production decision'],
  ];
  const parts = [register.slice(0, 7), register.slice(7)];
  parts.forEach((rows, i) => {
    appendixTableSlide(pptx, {
      code: 'B', title: 'Evidence Confidence Register', part: `${i + 1} of ${parts.length}`,
      headers: cols, rows, colW, fontSize: 9.5,
      note: i === parts.length - 1 ? 'This register is the source mapping for every CONFIRMED / PREVIEW / INFERRED / REQUIRES VALIDATION tag used throughout this deck.' : undefined,
      source: 'research.md (Lines 554-570)',
    });
  });
}

// APPENDIX C — Cost Assumptions
appendixBulletSlide(pptx, {
  code: 'C', title: 'Cost Assumptions',
  bullets: [
    { tag: 'confirmed', text: 'Cost drivers: model tokens, active session vCPU-hour + GiB-hour compute, idle window duration, MCP hosting compute, telemetry (Application Insights), evaluation tokens, optional Cosmos DB (RU + storage), optional Agent 365 licensing, operations labor.' },
    { tag: 'confirmed', text: 'Billing shape: pay only for active session compute while a session sandbox is warm; scale-to-zero on idle timeout (5-60 min, default 15 min) — architecturally closest to Azure Container Apps consumption plan.' },
    { tag: 'requires-validation', text: 'Unknown / TBD: exact $/vCPU-hr and $/GiB-hr session-compute rates (public pricing page returned "N/A" at research time); real workload token/session volumes; Cosmos DB RU consumption under load; Agent 365 add-on pricing per license tier.' },
  ],
  note: 'Slide recommendation: present a cost formula (tokens \u00d7 rate + session-compute-hours \u00d7 rate + fixed telemetry/MCP hosting + optional extensions), leaving rate cells as "unknown / TBD — Azure Pricing Calculator required." No slide may present an unverified figure as a specific number.',
  source: 'research.md (Lines 578-579, 570)',
});

// APPENDIX D — Evaluation Rubric
appendixBulletSlide(pptx, {
  code: 'D', title: 'Evaluation Rubric',
  bullets: [
    { tag: 'confirmed', text: 'Golden dataset composition: true positives, false positives, ambiguous evidence, missing data, conflicting tools, prompt injection, unauthorized actions, unsupported conclusions.' },
    { tag: 'confirmed', text: 'Release-gate criteria: triage correctness, evidence citation, tool selection, tool argument accuracy, unsupported-action refusal, task completion, output-schema validity, safety, latency, token use, session compute.' },
    { tag: 'confirmed', text: 'Evaluator types: deterministic checks (schema, citations, allowed tool calls, policy constraints) + model-based evaluators (relevance, groundedness, task adherence, rubric scoring). Built-in catalog includes quality, similarity, RAG, risk/safety, and agentic evaluator families.' },
    { tag: 'confirmed', text: 'Human review gate required for high-impact vulnerability conclusions and any recommendation triggering remediation or operational change.' },
    { tag: 'preview', text: 'Production sampling: continuous evaluation is a separate preview/privacy decision; redact sensitive content and define retention before enabling.' },
  ],
  source: 'research.md (Lines 510-513, 298)',
});

// APPENDIX E — Load-Test Plan
appendixBulletSlide(pptx, {
  code: 'E', title: 'Load-Test Plan',
  bullets: [
    { tag: 'confirmed', text: 'Scope (Increment 4 plan of record): 10-100 concurrent users/sessions; same-thread turn concurrency; cold-start latency distribution; active session compute measurement.' },
    { tag: 'requires-validation', text: 'Unmeasured today: maximum sessions, requests-per-second ceiling, MCP fan-out throughput, checkpoint size limits, downstream throttling behavior.' },
    { tag: 'requires-validation', text: 'State-experiment benchmark (same increment): Cosmos DB serverless CosmosDBSaver checkpointer — latency, RU cost, and private-endpoint reachability vs. the Responses-history baseline.' },
  ],
  source: 'research.md (Lines 609-610, 577)',
});

// APPENDIX F — RBAC Matrix (2 slides: roles, then Bicep resource types)
appendixTableSlide(pptx, {
  code: 'F', title: 'RBAC Matrix — Roles', part: '1 of 2',
  headers: ['Role', 'GUID', 'Scope', 'Use'],
  colW: [2.6, 3.6, 2.0, 4.3],
  rows: [
    ['Foundry Agent Consumer', 'eed3b665-ab3a-47b6-8f48-c9382fb1dad6', 'account/project/agent', 'invoke-only'],
    ['Foundry User', '53ca6127-db72-4b80-b1b0-d745d6d5456d', 'account/project', 'data-plane build/deploy — the correct role for CI/CD, not Cognitive Services *'],
    ['Foundry Project Manager', 'eadc314b-1a2d-4efa-be10-5d325db5065e', 'account', 'create/manage projects, publish agents'],
    ['Foundry Account Owner', 'e47c6f54-e4a2-4754-9501-8e0985b135e1', 'account', 'create projects/accounts, no data-plane build'],
    ['Foundry Owner', 'c883944f-8b7b-4483-af10-35834be79c4a', 'account', 'full control'],
  ],
  fontSize: 10,
  note: 'Plus Contributor at resource-group scope for azd provision, and AcrPush/AcrPull if using container-deploy mode instead of code-deploy. Confidence: confirmed (documented role definitions and GUIDs).',
  source: 'research.md (Lines 300-307)',
});

appendixTableSlide(pptx, {
  code: 'F', title: 'RBAC Matrix — Bicep Resource Types', part: '2 of 2',
  headers: ['Resource type', 'API version', 'Notes'],
  colW: [3.6, 2.6, 6.3],
  rows: [
    ['Microsoft.CognitiveServices/accounts', '2025-04-01-preview (sample) / 2025-06-01 (AVM)', "kind: 'AIServices', allowProjectManagement: true"],
    ['.../accounts/projects', '2025-04-01-preview', 'Foundry project'],
    ['.../accounts/projects/connections', '2025-04-01-preview', 'Cosmos DB/Storage/AI Search/OpenAI connections'],
    ['.../accounts/capabilityHosts, .../accounts/projects/capabilityHosts', '2025-04-01-preview / 2025-06-01', 'Standard Agent Setup only (BYO storage)'],
    ['Microsoft.DocumentDB/databaseAccounts', '2024-12-01-preview', 'Cosmos DB (BYO thread storage or app-level checkpointer store)'],
  ],
  fontSize: 9.5,
  source: 'research.md (Lines 313-320)',
});

// APPENDIX G — Product-Status Register
appendixTableSlide(pptx, {
  code: 'G', title: 'Product-Status Register',
  headers: ['Product capability', 'Status', 'Confidence tag'],
  colW: [5.5, 5.0, 2.0],
  rows: [
    ['Foundry Hosted Agents (custom-code hosting surface)', 'Public preview at research time — current GA status not reverified', 'requires-validation'],
    ['LangGraph as a supported hosted-agent framework', 'Documented, first-class', 'confirmed'],
    ['Responses protocol SSE streaming', 'Documented, confirmed mechanism', 'confirmed'],
    ['A2A delegation protocol', 'Preview', 'preview'],
    ['Continuous evaluation (EvaluationRule)', 'Documented but preview', 'preview'],
    ['Microsoft Agent 365 / Entra Agent ID', 'GA (platform), Hosted Agent onboarding path unverified', 'inferred'],
    ['microsoft/ai-agent-evals GitHub Action', 'Beta tag (@v3-beta); hosted-agent targeting not verified', 'requires-validation'],
    ['LangSmith Azure BYOC', 'Roadmap-stated "planned for 2H 2026," not a release commitment', 'requires-validation'],
  ],
  fontSize: 10,
  note: 'This register reframes Appendix B by product-capability GA/preview status rather than by claim; no separate product-status table exists in the research document.',
  source: 'research.md (Lines 5, 296, 356-369, 554-570)',
});

// APPENDIX H — Open Questions (2 slides)
{
  const items1 = [
    { tag: 'requires-validation', text: 'Scaling: per-session isolation, idle timeout, scale-to-zero documented; SLA, max sessions, RPS, same-session concurrency, cold-start distribution, model quota, and dependency limits are not established.' },
    { tag: 'requires-validation', text: 'Cost: drivers are known; actual rates and workload measurements are missing.' },
    { tag: 'requires-validation', text: 'Tools and MCP: custom MCP code needs its own Azure runtime; auth, private reachability, throttling, versioning, and failure handling must be validated in the PoC.' },
    { tag: 'confirmed', text: 'Multi-agent design: a supervisor coordinating specialists inside one hosted deployment is a genuine multi-agent system.' },
    { tag: 'preview', text: 'Separate A2A deployments are justified only by independent ownership/release/isolation/scaling needs and remain preview.' },
  ];
  const items2 = [
    { tag: 'confirmed', text: 'Evaluations: offline/batch scoring confirmed.' },
    { tag: 'preview', text: 'Continuous evaluation documented but preview.' },
    { tag: 'requires-validation', text: 'GitHub Action hosted-agent targeting, portal visibility, and multi-agent trace coverage require validation.' },
    { tag: 'confirmed', text: 'Automation: recommended flow (staging \u2192 smoke/contract/streaming/offline-eval gates \u2192 approval \u2192 promote \u2192 monitor \u2192 rollback); infrastructure and agent versions have separate deployment lifecycles.' },
    { tag: 'confirmed', text: 'Streaming: Responses SSE supports progressive output events.' },
    { tag: 'requires-validation', text: 'Parity with all required LangGraph events, reconnection, cancellation, and the existing UI contract must be tested.' },
    { tag: 'confirmed', text: 'Conversation state: Responses history is the baseline source of truth; adopt Cosmos checkpointer only for a documented durable-state requirement.' },
    { tag: 'requires-validation', text: 'No user-scoped conversation-list API was found — an evidence gap.' },
    { tag: 'confirmed', text: 'Governance: per-agent Entra identity, Foundry RBAC, and Application Insights are supported baseline controls.' },
    { tag: 'inferred', text: 'Agent 365 is a validation track because the exact Hosted Agent identity onboarding and LangGraph instrumentation path was not found.' },
    { tag: 'confirmed', text: 'Reusability: reuse comes from versioned Bicep modules, azure.yaml, a standard hosted-agent wrapper, independently owned MCP contracts, common evaluation datasets, and reusable GitHub workflows.' },
    { tag: 'requires-validation', text: 'Owners and decision date for the PoC plan: not specified anywhere in the research document — open item for the presenting team.' },
  ];
  appendixBulletSlide(pptx, { code: 'H', title: 'Open Questions', part: '1 of 2', bullets: items1, source: 'research.md (Lines 615-618)' });
  appendixBulletSlide(pptx, { code: 'H', title: 'Open Questions', part: '2 of 2', bullets: items2, source: 'research.md (Lines 619-624)' });
}

// ── Re-stamp footers now that final slide count is known ──────────────────
const allSlides = pptx.slides;
const total = allSlides.length;
allSlides.forEach((slide, i) => {
  slide.addText(`${i + 1} / ${total}`, {
    x: 12.5, y: 7.14, w: 0.7, h: 0.28, fontSize: 9, color: C.textLight, fontFace: 'Segoe UI', align: 'right',
  });
});

await pptx.writeFile({ fileName: OUTPUT_PATH });

console.log(`Wrote ${OUTPUT_PATH}`);
console.log(`Total slides: ${total} (1 title + ${CORE_SLIDE_TOTAL} core + ${appendixLog.length} appendix)`);
console.log('Appendix slide list:');
for (const label of appendixLog) console.log(`  - ${label}`);
