export const meta = {
  name: 'repo-audit-deep',
  description: 'Tiefes Multi-Agent Single-Repo-Audit: Inventar → 9 Dimensionen fan-out → adversariale Verifikation jedes Befunds → Synthese (Steelman + 3 Rollen + Top-5 + Roadmap)',
  whenToUse: 'DEEP-Pfad von /repo-audit. Due-Diligence/vollständige Tiefe eines Repos. Teuer (Opus × ~9 Agents + Verify) — opt-in, nicht für schnelle Checks.',
  phases: [
    { title: 'Inventar', detail: 'Repo-Inventar + Hochrisiko-Zonen (1 Agent)' },
    { title: 'Review', detail: '1 Agent pro Dimension, Befunde mit Evidence-Ledger' },
    { title: 'Verify', detail: 'adversariale Refutation jedes Befunds' },
    { title: 'Synth', detail: 'Steelman + 3 Rollen + Top-5 + Roadmap + Schlussurteil' },
  ],
}

// args: { repo: "<pfad oder ORG/REPO>", goal?: "<1-5 Sätze>", date?: "YYYY-MM-DD" }
const repo = (args && args.repo) || '.'
const goal = (args && args.goal) || '(kein expliziter Kontext übergeben — aus dem Repo selbst ableiten)'
const stamp = (args && args.date) || 'undatiert'

// --- Platform-Verträge P1–P9 (als Prompt-Fragment für jeden Agent) ---
const PLATFORM = `
Platform-Verträge (iil.gmbh) — Verstöße als eigene Befunde mit Präfix PLAT-:
- P1 Service-Layer: kein ORM (.objects./.filter(/.save() direkt in views.py
- P2 Integer-PK: kein UUIDField(primary_key=True)
- P3 HTMX-Triple: jedes hx-* mit hx-target + hx-swap + hx-indicator (alle drei)
- P4 PG-only Tests (ADR-179): kein sqlite in Test-Settings
- P5 Test-Naming: test_should_{verhalten}
- P6 Shared-CI: uses achimdehnert/platform/.github/workflows/_ci-python.yml@main statt Inline-CI
- P7 Commit-Konvention: [feat|fix|refactor|docs|test|chore](scope): …
- P8 Secrets-Hygiene: keine Klartext-Secrets getrackt, secrets.env gitignored
- P9 ADR-Pflicht: neue Dep/Service-Grenze/Cross-Cutting ohne ADR = Lücke (reine Addition braucht keinen ADR)
Bekannte Stolpersteine: Index-Rename-Migration → SeparateDatabaseAndState; gitleaks-403 = fehlende pull-requests:write Permission; ttz-lif/meiki-lra = Data-Sovereignty der repo-CLAUDE.md.`

const LEDGER = `
Evidence-Ledger (bindend): jede Aussage braucht E1 (Datei+Zeile) / E2 (Befehl+Output) / E3 (CI/PR/Commit) / E4 (extern/CVE) / H (Hypothese, MUSS markiert sein). Kein hoher/kritischer Befund ohne E1–E4. Aktiv Gegenbelege suchen. Keine erfundenen Dateien/Zeilen. Nicht-prüfbares explizit sagen. Secrets nie vollständig ausgeben.`

const DIMENSIONS = [
  { key: 'architektur', prompt: 'Schichten/Verantwortlichkeiten (P1 Service-Layer), zyklische Deps, globaler State, Abstraktion externer Systeme, Fehler-als-Architektur, God-Module, Code-vs-Doku, ADR-Abdeckung (P9).' },
  { key: 'daten', prompt: 'Datenmodell-Konsistenz (P2 Integer-PK), Migrationsrisiken (Index-Rename→SeparateDatabaseAndState), Transaktionen/Idempotenz, Races/Lost-Updates, Daten-Ownership, fehlende Constraints, Retention/Löschung, gefährliche Datenkopien.' },
  { key: 'security', prompt: 'Secrets in Repo/Tests/Config/Logs (P8), zentrale vs verstreute AuthZ, Objekt-/Mandanten-Zugriffskontrolle, Injection/SSRF/Path-Traversal/Deser/Template-Injection, Supply-Chain, CI-Rechte/Tokens, unsichere Defaults, Rate-Limits, Debug/Admin-Endpunkte, Krypto/Session/Token-Lifetime.' },
  { key: 'datenschutz', prompt: 'PII, sensibles Logging, Retention/Export/Löschung/Zweckbindung, Mandantentrennung, prod-nahe Testdaten, Abfluss via Monitoring/Analytics, Data-Sovereignty (ttz-lif/meiki-lra).' },
  { key: 'tests', prompt: 'Testarten, echte vs Schein-Coverage, brittle/flaky, fehlende Negativtests, Contract/Integration an Grenzen, Determinismus, PG-only (P4, kein sqlite), Fehlerfälle/Rechtewechsel/Parallelität/Migrationen, test_should_* (P5), Happy-Path-Bias, Snapshot-Tests die Änderungen verdecken.' },
  { key: 'cicd', prompt: 'Reproduzierbarkeit (P6 Shared-CI _ci-python.yml), getrennte Envs (ADR-210), Release/Rollback, Migrations-Validierung, Health-Checks (/livez/), Observability, Artefakt-Versionierung, minimale CI-Rechte (gitleaks pull-requests:write sonst 403), Gates, gefährliche continue-on-error/skip/allow_failure (legitim vs stille Umgehung), Local↔CI-Drift.' },
  { key: 'performance', prompt: 'N+1, unbounded Queries/Loops/Queues/Payloads, Caching, Backpressure, Timeouts/Retries, Leaks, unbegrenzte Parallelität, synchrone Großoperationen im Request-Pfad, fehlende Pagination/Limits.' },
  { key: 'codequalitaet', prompt: 'riskante Duplikation, überladene Module, tote Pfade, God-Funktionen, Fehlerbehandlung, Typisierung, Lint/Format enforced (ruff), magische Strings, nur-kommentierte statt enforcete Verträge, Framework-Interna-Kopplung.' },
  { key: 'doku', prompt: 'README/ADR/Kommentar/Code-Konsistenz, Onboarding-Lücken, realistische Setup-Schritte, dokumentierte Betriebs-/Security-/Migrations-Annahmen, gefährlich veraltete Doku, CLAUDE.md/CORE_CONTEXT.md/AGENT_HANDOVER.md aktuell.' },
  { key: 'platform', prompt: 'Reiner Platform-Konformitäts-Pass: jeden Vertrag P1–P9 einzeln prüfen und mit konkretem grep/Datei-Beleg als erfüllt/verletzt/nicht-zutreffend deklarieren.' },
]

const FINDINGS_SCHEMA = {
  type: 'object',
  properties: {
    dimension: { type: 'string' },
    flach_geprueft: { type: 'boolean', description: 'true wenn aus Zeit/Evidenz-Mangel nur oberflächlich' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          id: { type: 'string', description: 'Präfix AD-/SEC-/PRIV-/TEST-/OPS-/ARCH-/PERF-/DOC-/PLAT-/M28-/PRO-' },
          befund: { type: 'string' },
          evidenz: { type: 'string', description: 'E1 Datei+Zeile / E2 Befehl+Output / E3 / E4 / H' },
          evidenz_typ: { type: 'string', enum: ['E1', 'E2', 'E3', 'E4', 'H'] },
          schweregrad: { type: 'string', enum: ['kritisch', 'hoch', 'mittel', 'niedrig', 'positiv', 'stark positiv'] },
          confidence: { type: 'string', enum: ['hoch', 'mittel', 'niedrig'] },
          betroffener_teil: { type: 'string' },
        },
        required: ['id', 'befund', 'evidenz', 'evidenz_typ', 'schweregrad', 'confidence'],
      },
    },
  },
  required: ['dimension', 'findings'],
}

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    id: { type: 'string' },
    bestaetigt: { type: 'boolean', description: 'true nur wenn Befund der Refutation standhält' },
    begruendung: { type: 'string' },
    korrigierter_schweregrad: { type: 'string', enum: ['kritisch', 'hoch', 'mittel', 'niedrig', 'positiv', 'stark positiv'] },
  },
  required: ['id', 'bestaetigt', 'begruendung'],
}

// ---------------------------------------------------------------------------

phase('Inventar')
const inventar = await agent(
  `Du auditierst das Repo: ${repo}\nKontext/Ziel: ${goal}\n\nErstelle Zwischenlieferung A: (1) Repo-Inventar (Sprachen/Frameworks/Lockfiles/Einstiegspunkte/Module/DBs/Queues/Auth/Deploy/Config/Migrationen/Observability — jedes mit Datei-Evidenz), (2) die 3-5 wahrscheinlichsten Hochrisiko-Zonen mit Begründung. NUR lesen, keine destruktiven Befehle.\n${LEDGER}`,
  { label: 'inventar', phase: 'Inventar' },
)

// Phase 4: pro Dimension review → adversariale Verifikation jedes Befunds.
// Pipeline: Dimension D wird verifiziert, während Dimension E noch reviewt — keine Barriere.
const auditiert = await pipeline(
  DIMENSIONS,
  (d) => agent(
    `Repo: ${repo}\nKontext: ${goal}\n\nInventar/Hochrisiko-Zonen aus Phase A:\n${inventar}\n\nAuditiere TIEF die Dimension "${d.key}": ${d.prompt}\n${PLATFORM}\n${LEDGER}\n\nGib strukturierte Befunde zurück. Wenn du eine Dimension aus Evidenz-Mangel nur flach prüfen konntest, setze flach_geprueft=true (ehrlich, nicht vortäuschen).`,
    { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA },
  ),
  (review, d) => {
    const findings = (review && review.findings) || []
    // Nur substanzielle Befunde adversarial prüfen; positive/niedrige direkt übernehmen.
    const zuPruefen = findings.filter((f) => ['kritisch', 'hoch', 'mittel'].includes(f.schweregrad))
    const direkt = findings.filter((f) => !['kritisch', 'hoch', 'mittel'].includes(f.schweregrad))
    return parallel(
      zuPruefen.map((f) => () =>
        agent(
          `Repo: ${repo}\n\nVersuche diesen Audit-Befund zu WIDERLEGEN (Advocatus Diabolus gegen den Befund selbst). Default: bestaetigt=false bei Unsicherheit. Prüfe die zitierte Evidenz real nach.\n\nBefund [${f.id}] (${f.schweregrad}): ${f.befund}\nZitierte Evidenz: ${f.evidenz}\n${LEDGER}`,
          { label: `verify:${d.key}:${f.id}`, phase: 'Verify', schema: VERDICT_SCHEMA },
        ).then((v) => ({ ...f, dimension: d.key, verdict: v })),
      ),
    ).then((geprueft) => ({
      dimension: d.key,
      flach_geprueft: !!(review && review.flach_geprueft),
      bestaetigt: geprueft.filter(Boolean).filter((f) => f.verdict && f.verdict.bestaetigt),
      direkt_uebernommen: direkt.map((f) => ({ ...f, dimension: d.key })),
    }))
  },
)

// Sammeln (plain code, keine Barriere nötig — pipeline ist schon durch)
const valide = []
const flachGeprueft = []
for (const a of auditiert.filter(Boolean)) {
  if (a.flach_geprueft) flachGeprueft.push(a.dimension)
  valide.push(...a.bestaetigt, ...a.direkt_uebernommen)
}
log(`Verifizierte/übernommene Befunde: ${valide.length} · flach geprüfte Dimensionen: ${flachGeprueft.join(', ') || 'keine'}`)

phase('Synth')
const report = await agent(
  `Repo: ${repo}\nKontext: ${goal}\nDatum: ${stamp}\n\nInventar (Phase A):\n${inventar}\n\nVerifizierte Befunde (JSON):\n${JSON.stringify(valide, null, 2)}\n\nFlach geprüfte Dimensionen (ehrlich deklarieren): ${flachGeprueft.join(', ') || 'keine'}\n\nSynthetisiere das vollständige Audit als Markdown in dieser Struktur:\n1. Executive Summary (max 10 Sätze: Urteil/Stärke/Risiko/Maßnahme/Unsicherheit)\n2. Scope & Evidenzbasis (Modus=DEEP, Branch/Commit, flach geprüfte Dimensionen)\n3. Repo-Inventar\n4. Steelman (3-7 evidenzbasierte Sätze ZUERST)\n5. Befunde (Tabelle: ID|Rolle|Kategorie|Befund|Evidenz|Schweregrad|Confidence|Teil)\n6. Top-5-Risiken (je: Schadensszenario/Wahrscheinlichkeit/Dringlichkeit/kleinster Fix/Evidenz/geprüfte Gegenbelege)\n7. Rollenanalyse (🟢 Proponent · 😈 Advocatus Diabolus · 🔮 Maintainer 2028)\n8. Platform-Konformität P1–P9\n9. Out-of-the-Box (≥3 Ansätze: Idee/Vorteil/Nachteil/wann/warum verwerfen)\n10. Empfehlungen REC-N (je: Befund-ID/Ziel/Änderung/Aufwand S-M-L/Risiko/Verifikation/Akzeptanzkriterium)\n11. 30/60/90-Tage-Roadmap\n12. Schlussurteil (gesund/brauchbar mit Risiken/riskant aber sanierbar/architektonisch gefährdet/nicht belastbar)\n\nSteelman zuerst, dann Kritik. Keine erfundenen Belege. Hypothesen als H markiert lassen.`,
  { label: 'synth', phase: 'Synth' },
)

return { repo, datum: stamp, modus: 'DEEP', befunde_valide: valide.length, flach_geprueft: flachGeprueft, report }
