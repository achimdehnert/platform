---
status: accepted
date: 2026-05-18
decision-makers: [Achim Dehnert]
implementation_status: partial
related: [ADR-111, ADR-196, mcp-hub#59, platform#187, platform#191, platform#194]
---

# ADR-209: CI-Health als Konvergenz-Programm mit Verfallsdatum (Prävention vor Detektion)

## Status

accepted — v2. Skill `/ci-green-program`. v1 (reiner Wartungs-Loop) durch
Advocatus-Diaboli-Review (2026-05-18) verworfen, bevor #194 gemerged wurde.

## Kontext

48 Repos, je eigene unabhängig rottende CI. Lauf 1 (2026-05-18) lieferte den
entscheidenden Beweis selbst: **ein** Fix in der reusable `_ci-python.yml`
(gitleaks #191) entsperrte alle Consumer. D.h. der Hebel ist *geteilte
Quelle*, nicht ein ewiger Triage-Loop.

**Verworfene v1-Prämissen (Self-Red-Team):**
- v1 institutionalisierte die Sprawl-Krankheit (Maschinerie zum ewigen
  Rasenmähen statt Pflastern).
- v1 war reaktiv (detektieren→fixen) für an-der-Quelle-verhinderbare Klassen.
- v1 machte Opus zum *Eingang* → skaliert nicht, nicht modell-fortführbar.
- v1 pollte monatlich (= `--limit 1`-Fehler auf Makro-Ebene; CI ist ein
  Event-Stream).
- "durchgehend grün" ist Goodhart-anfällig — Lauf 1 senkte selbst Gates
  (deployment_mcp 80→35, `# noqa`).
- v1 hatte kein Verfallsdatum → würde selbst zu verwaister Infra.

## Entscheidung

CI-Health ist ein **zeitlich begrenztes Konvergenz-Programm**, kein stehender
Wartungs-Loop. Fünf Prinzipien:

1. **Prävention vor Detektion.** Primärziel: 48 per-Repo-CIs → *eine*
   gehärtete reusable Workflow-Familie (`_ci-*.yml`) + ein Conformance-Check.
   Python-Version aus `requires-python` abgeleitet, org-weite ruff-Config,
   `git+...#subdirectory`-Deps als Hard-Fail. Konvergenz eliminiert ganze
   Failure-Klassen *permanent* statt sie zu detektieren.
2. **Event-driven statt Polling.** Org-Level: CI-rot → klassifizieren →
   mechanische Klasse autonom fixen / sonst eskalieren. Survey nur als
   einmaliger Bootstrap, nicht wiederkehrend.
3. **Gates als Code, Opus als Eskalation.** G1–G7 (s.u.) werden ein
   deterministischer Klassifizierer. Default-Pfad autonom (Sonnet); Opus
   nur bei `UNKNOWN`/novel class. Damit modell-fortführbar.
4. **Anti-Goodhart-Invariante.** Ein Fix darf **kein** Gate (Coverage,
   Lint-Strenge, Test-Skip) senken ohne `@waiver(grund, expires=<datum>)`.
   Waiver werden in `docs/ci-waivers.md` registriert und verfallen; ein
   abgelaufener Waiver ist selbst ein CI-Fail. "Grün" muss verdient sein.
5. **Portfolio-Triage zuerst + Exit-Kriterium.** Vor Konvergenz: jedes Repo
   als *live / maintenance / dead* klassifizieren. Dead → archivieren (nicht
   grün-pflegen). **Exit:** ≥90 % der live-Repos auf shared CI **und**
   Red-Rate < 10 % über 30 Tage → Programm schrumpft auf einen
   Thin-Event-Handler; das Standing-Programm wird zurückgezogen.

**Gates G1–G7** (empirisch Lauf 1, jetzt Klassifizierer-Regeln):
G1 Status = letzter push/PR-Lauf (nie `--limit 1`). G2 Verify vor Handlung.
G3 Versions-/API-Check vor Dep-Swap. G4 Cross-cutting/shared zuerst.
G5 Deploy/Infra nie autonom. G6 Judgment (Test-vs-Code/Gate-Senkung) →
manuell. G7 Contract-First (Fix benennt wiederhergestellte erzwungene Regel).

**Modell-Routing:** Sonnet = Default (mechanisch, klassifiziert). Opus =
Eskalation + Konvergenz-Design. Cerebras verworfen (Tool-Use). Vgl. ADR-196.

## Konsequenzen

**Positiv:** eliminiert Failure-Klassen an der Quelle (skaliert besser als
n×fixen); event-driven = MTTR↓ ohne Polling-Blindheit; Opus kein Dauer-
Flaschenhals; Anti-Goodhart hält "grün" bedeutungsvoll; Selbstabschaltung
verhindert, dass das Programm eigene Rot-Fläche wird.

**Negativ / Risiko:** Konvergenz ist Vorab-Invest (Repos auf shared CI ziehen
ist Aufwand vor Ertrag); Klassifizierer-Skript ist neue zu wartende Komponente
(Mitigation: klein, Regeln explizit, fällt sicher auf Eskalation zurück);
Portfolio-Triage „dead" ist Judgment (G6, Opus/Human).

**Reversibel:** Skill + Labels + reusable Workflows; Abschalten = Skill nicht
triggern. Konvergenz selbst ist der Rückbau von Sprawl, kein Lock-in.

## Alternativen

- **v1 Wartungs-Loop** — verworfen (s. Self-Red-Team oben).
- **Voll-autonom ohne Gates** — verworfen (Lauf 1: 8-Repo-Downgrade-Beinahe).
- **Monorepo** — nicht jetzt; Konvergenz auf shared CI holt 80 % des
  Monorepo-Nutzens ohne dessen Migrationskosten.

## Implementierungsstand

Bootstrap-Loop + Lauf 1 **done** (platform#187/#191, iil-platform-context
0.7.0, 18 Issues). Konvergenz / Event-Handler / Klassifizierer-Skript /
Waiver-Registry / Portfolio-Triage = **geplant** (Phasenplan im Skill).
