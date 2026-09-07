---
retro_schema: 1
date: 2026-07-02
repo_scope: [frist-hub]
session_id: a50bc6
footprint: full
findings_total: 23
findings_survived: 8
refuted_rate: 0.0
phase3_refuted: 0
pre_refuted: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 3
  entscheidungsqualitaet: 4
gate_candidates: [claim-before-cheapest-check, lint-failure-no-local-gate, planned-phase-no-issue]  # nur ≥2-Rekurrenz (retro_kpis.py); ci-gate-maskiert-failure + handover-stale-vor-merge sind ×1 → nur recurring_findings
recurring_findings: [claim-before-cheapest-check, lint-failure-no-local-gate, planned-phase-no-issue, ci-gate-maskiert-failure, handover-stale-vor-merge]  # Zählregel (retro_kpis.py:108-119, verifiziert): 1 Slug = max +1 pro Retro-Report, unabhängig von der Anzahl der Einzel-Findings
---

# Session-Retro · frist-hub · 2026-07-02 (a50bc6)

Session-Inhalt: `/repo-optimize`-Audit (8 Finder + 4 Skeptiker, Report
`~/shared/repo-optimize-frist-hub-2026-07-02.md`) + Umsetzung: PR #2 (CI-Fix,
Deploy-Job raus), #3 (Doku-Sync), #4 (Robustheit) gemerged; #5 (BRMS-Recht)
Draft; Branch-Protection aktiviert. 14 CI-Runs auf `CI — frist-hub`
(5 success · 5 failure · 3 startup_failure · 1 dauerhaft queued).

## 1. Executive Summary

- **Kernziel erreicht:** CI von „lief nie" (alle Runs startup_failure seit
  Scaffolding) zu durchgängig grünem `main` mit aktiver Branch-Protection —
  in einer Session, mit ehrlich dokumentierten Selbstkorrekturen.
- **Schwerster Survivor (SI7):** Der neue Required-Check `ci / gate` schützt
  NICHT vor roten Integration-Tests (`continue-on-error: true` macht das
  needs-Result grün) — dasselbe Maskierungsmuster wie Audit-Befund T3, ein
  zweites unentdecktes Vorkommen im Platform-Workflow.
- **Wiederholungs-Muster bestätigt:** `claim-before-cheapest-check` trat mit
  2 Instanzen in der Session auf (Pipe-Exit als „lint-imports grün"; „Run
  gecancelt" auf Submit-Bestätigung — Run hängt real weiter queued), zählt
  nach retro_kpis.py-Konvention als EIN Session-Increment — Slug
  längsschnittlich ×3→×4, Gate war bereits seit ×2 pflichtig.
- **Follow-up-Disziplin ist die größte Lücke:** Fleet-Eskalation (SI5),
  Memory-Kandidaten (SI4), Coverage-Toleranz (EF9) existieren nur als Prosa/
  Chat — kein Issue, kein Artefakt; Handover ging veraltet auf main (SI6).
- **Prozess-Reibung quantifiziert:** ~7 der 14 CI-Runs waren Fehlversuche;
  davon 3 strukturell unvermeidbar (alte ci.yml auf Parallel-Branches),
  ~4 vermeidbar (Format-Iterationen ohne lokalen CI-identischen Check,
  Wiederholungs-Runs gegen bekannte Debt).

## 2. Befund-Tabelle

Verdikt: S = SURVIVES (Phase-3-Skeptiker, unabhängig nachgezogen) ·
„—" = nicht falsifiziert (M/N, außerhalb Skeptiker-Budget).

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 (SI7) | `ci / gate` maskiert rote Integration-Tests (`continue-on-error`) — Protection-Versprechen nur partiell | Wissenslücke/fehl. Validierung | hoch | S (verstärkt: 3× empirisch am Auditdatum) | Runs 28589529523/28588979006/28589188805: Integration=failure ∧ gate=success; `_ci-python.yml:317` ohne Begründungskommentar | ci-gate-maskiert-failure ×1 (Muster = Audit-T3) |
| 2 (PK5) | PR #2 mit 3 roten Checks gemerged, ohne Merge-Zeit-Vermerk; main 12:01–12:14Z rot | Prozesslücke | kritisch | S (mitigiert: PR-Body kündigte Neu-Befunde an; Lint-Fix lag parallel in #4; User-Freigabe der Merge-Reihenfolge lag im Chat vor, nicht am Artefakt) | PR#2 statusCheckRollup; 0 Kommentare; Protection erst 12:18:52Z (Org-Audit-Log) | — |
| 3 (SI5) | Fleet-Eskalation (platform-Template-Bug) nur Prosa — kein Issue, Template auf main unverändert fehlerhaft | fehlende Validierung | hoch | S | `docs/templates/ci.yml`-Blob main; 5 Issue-Suchen leer | planned-phase-no-issue ×2 ⇒ GATE |
| 4 (SI6) | AGENT_HANDOVER.md ging veraltet auf main („PR #2 offen", #4/#5/Protection fehlen) | Prozesslücke | hoch | S | b2886b0 (11:11Z) vs. #2-Merge 12:01Z vs. #3-Merge 12:18Z | handover-stale-vor-merge ×1 (vgl. Drift-Lehre 2026-06-24 im session-start-Skill, Phase 2.6) |
| 5 (SI4) | 3 Memory-Kandidaten nicht materialisiert; Entscheidung nur im Chat offen | Prozesslücke | hoch | S (mitigiert: „Mensch entscheidet" war Design; Entscheidung steht aus) | kein memory/ für frist-hub; Namen nur in Transcript-JSONL | — |
| 6 (EF4) | Rechtsamt-Vorbehalt PR #5 nur Draft+Text — kein technisches Gate (keine Reviews-Pflicht, kein CODEOWNERS, Rulesets leer) | Prozesslücke | hoch | S (Rest-Lücke: Org-Rulesets 403, s. §8) | gh pr view 5; CODEOWNERS 404; rulesets [] | — |
| 7 (PK2) | Identische 15 Alt-Lint-Findings + Coverage<80 in 3 Runs wiederholt — 2./3. Lauf vermeidbar (Fix lag offen in #4) | Prozesslücke | hoch | S (mitigiert: Erstentdeckung unvermeidbar — Debt erst durch ersten echten Lauf sichtbar) | Log-Diff Runs 28586597739/28588384399/28588419696 byte-identisch | — |
| 8 (K2N) | „Run gecancelt" gemeldet auf Submit-Bestätigung; Run 28585281217 hängt real bis jetzt queued | fehlende Validierung | mittel | S (aus Phase-2.5-Konflikt, skeptiker-verifiziert) | gh run view: status=queued, conclusion leer, kein Cancel-Event | claim-before-cheapest-check ×4 ⇒ GATE (längst) |
| 9 (SI1) | 5 Audit-Befunde (S4/S8/D6/D12/D14) in keiner Roadmap-Sektion — still gedroppt statt einsortiert | Prozesslücke | mittel | — | `~/shared/repo-optimize-frist-hub-2026-07-02.md` §Befund-Tabelle (Z.86-118) vs. §Roadmap (Z.131-156): IDs fehlen in allen 4 Buckets + „Nicht sofort ändern" | — |
| 10 (SI2) | D7 (OK.WOBIS in workflow.md) nur 1-Zeilen-Verweis, nicht substanziell adressiert | Kommunikation | niedrig | — | gh pr diff 3 | — |
| 11 (SI3) | Repo-weites ruff format in PR #4 überschreitet benannten Audit-Scope (transparent begründet) | verfrühte Festlegung | niedrig | — | 84c0015 --stat (41 Dateien) | — |
| 12 (EF1) | runs_on-Default nicht vor 1. Push geprüft — Override stand in der Input-Doku; 35 min Queue + 2. Anlauf | fehlende Validierung | mittel | — | _ci-python.yml:79; ae48999-Body | — |
| 13 (EF2) | Makefile bildet CI-Gate nicht ab (kein `format --check .`, kein Versions-Pin) — Lücke besteht fort | Werkzeug | mittel | — | Makefile lint-Target vs. _ci-python.yml:136-138 | lint-failure-no-local-gate ×2 ⇒ GATE |
| 14 (EF3) | Pipe-Exit-Falle (84c0015) — einmalig, in-Session selbst korrigiert, nicht rekurrent im Diff | fehlende Validierung | niedrig | — | 84c0015-Body; grep über Session-Diffs | claim-before-cheapest-check (Teil von ×4) |
| 15 (EF6) | ADR-041-Contract ersatzlos gestrichen (import-linter-2.x-Limit) — Schutz fällt auf Review zurück, kein Interims-Gate | verfrühte Festlegung | mittel | — | git show 6dae418 -- .importlinter | — |
| 16 (EF7) | allow_indirect_imports=True reduziert Views-Contract auf Direktimport-Prüfung (dokumentierter Kompromiss) | Werkzeug-Grenze | mittel | — | .importlinter:25-27 | — |
| 17 (EF8) | Deploy-Job-Entfernung ohne dokumentierte Abwägung der Environment-Gate-Alternative | verfrühte Festlegung | niedrig | — | PR#2-Body | — |
| 18 (EF9) | Integration-Coverage 53%<80 toleriert (continue-on-error) ohne Follow-up-Issue | Prozesslücke | mittel | — | Run-Log „total of 53 is less than fail-under=80"; issue list leer | planned-phase-no-issue (Teil von ×2) |
| 19 (PK1) | 3 startup_failures durch Parallel-Branches vor #2-Merge (bewusster Trade-off lt. PR#4-Body, s. PK4) | Prozesslücke | mittel | — | Run-IDs 28585628213/28586170086/28586490336 | — |
| 20 (PK3) | manage.py beim 1. Format-Pass übersehen → 3. CI-Anlauf | fehlende Validierung | niedrig | — | Runs 28588403586→28588741744→28588979006 | lint-failure-no-local-gate (Teil von ×2) |
| 21 (PK6) | Protection erst nach allen 3 Merges aktiv (pragmatisch erklärbar: Check war vorher nie grün setzbar) | Prozesslücke | mittel | — | Org-Audit-Log 12:18:52Z | — |
| 22 (PK7) | services.py in #3+#4+#5 angefasst → 2 manuelle Rebase-Konfliktauflösungen | verfrühte Festlegung | mittel | — | Parent-Kette b2886b0; 1× head_ref_force_pushed auf #5 | — |
| 23 (PK9) | Kein Stale-Run-Cancel-Check + 4 gemergte lokale Branches nicht geprunt | Werkzeug | niedrig | — | gh api run 28585281217; git branch -a | — |

**Positivbefunde (nicht gezählt):** SI8 (PR-#5-Vorbehalt vorbildlich dokumentiert) ·
SI9 (D8/D10/D11 sauber als Fleet-Scope kommuniziert) · EF5 (TENANCY_MODE-Fix korrekt
konsequenzlos) · PK4 (Parallelisierung explizit im PR-Body abgewogen) · PK8
(Commit-Messages als Audit-Trail vorbildlich, Selbstkorrekturen offen).

**Daten-Korrektur (Retro-intern):** Collector-Zahl „5× startup_failure + 3× failure"
war falsch; Skeptiker-verifiziert: 14 Runs = 5 success · 5 failure · 3 startup_failure ·
1 queued.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | Audit → grünes main + Protection in einer Session (#2/#3/#4 gemerged, #5 Draft); Mängel: Roadmap-Drops (#9), Handover stale (#4) |
| architektur_design | 4 | Idempotenz-Ledger, Contract-Suite, Hexagonal-Contract neu; Abzug: ADR-041-Schutzverlust (#15), Gate-Maskierung übernommen (#1) |
| code_konventionstreue | 4 | Lint/Format-Null repo-weit, Konventionen eingehalten; Abzug: erst nach 3 CI-Iterationen (#13/#20) |
| risiko_debt | 3 | #1 (gate maskiert), #2 (main 13 min bewusst rot ohne Vermerk — kritisch), #6 (Rechtsamt ohne technisches Gate), #18 (Coverage ohne Issue), #3 (Fleet-Bug untracked) — signifikante offene Risiken, alle benannt |
| prozess_effizienz | 3 | ~7/14 Runs Fehlversuche, 2 Rebase-Konflikte (#22), 35-min-Queue (#12); schnelle Selbstkorrektur als Gegengewicht |
| entscheidungsqualitaet | 4 | Deploy-Job-Entscheid, Draft-Gate, Merge-Sequenz tragfähig; Abzug: Rot-Merge ohne Vermerk (#2), Alternative nicht dokumentiert (#17) |

## 4. Soll-Ablauf (je verifiziertem Survivor)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| Required-Check `ci / gate` gesetzt, ohne zu inventarisieren, welche Jobs es maskiert (Runs zeigen Integration=failure ∧ gate=success) | Vor dem Setzen eines Required-Checks einen realen Run job-weise lesen: welche needs stehen auf continue-on-error → Liste in PR/Protection-Beschreibung | #1 |
| PR #2 bei rotem gate gemerged, Entscheid nur im Chat (0 PR-Kommentare) | Bewusster Rot-Merge bekommt 1-Zeilen-PR-Kommentar am Merge-Zeitpunkt: Grund + Verweis auf den Fix-PR | #2 |
| Fleet-Bug im Handover/Chat notiert, Template auf main weiter kaputt, kein Issue | Bei jedem [FLEET-PATTERN]-Survivor sofort Issue im Quell-Repo anlegen (2-min, gate-frei) — Prosa-Eskalation zählt nicht als Eskalation | #3 |
| Handover in Branch früh geschrieben, vor Merge nicht re-synchronisiert | AGENT_HANDOVER.md unmittelbar vor dem letzten Merge der Session aktualisieren (oder als separater letzter Mini-PR) | #4 |
| Memory-Entscheidung 3× im Chat erfragt, nirgends trackbar festgehalten | Offene Mensch-Entscheidungen beim Session-Ende in den Handover-P0-Block schreiben (Chat verfällt, Datei nicht) | #5 |
| Rechtslogik-PR nur durch Draft-Flag geschützt | Für fachlich-rechtliche Pfade Review technisch erzwingen: CODEOWNERS auf apps/fristen/services.py + required_pull_request_reviews (oder Org-Ruleset) | #6 |
| Nach dem ersten echten CI-Lauf liefen #3-Runs weiter gegen bekannte, in #4 bereits gefixte Debt | Sobald ein Debt-Fix-PR offen ist: abhängige PRs erst nach dessen Merge rebasen/pushen statt parallele Runs zu erzeugen | #7 |
| „Alter Run gecancelt" auf Basis „Request submitted" gemeldet; Run real weiter queued | Nach jedem state-changing gh-Kommando den Zielzustand nachlesen (gh run view status) — Submit ≠ Ergebnis | #8 |

## 5. Längsschnitt (retro_kpis.py, Pflichtlauf 2026-07-02)

- 🚨 `claim-before-cheapest-check` **×3 → ×4** (ein Session-Increment aus
  2 Instanzen: #8, #14 — Zählregel s. Frontmatter-Kommentar) — GATE-PFLICHT
  bestätigt (Gate existiert: `evidence_claim_scanner.py` Stop-Hook + CLAUDE.md-Gate;
  #8 zeigt: Hook greift nicht bei asynchronen Submit-vs.-Ergebnis-Claims → Gate-Lücke).
- `lint-failure-no-local-gate` ×1 → **mit #13 jetzt ×2 ⇒ GATE-PFLICHT** (Fix =
  Makefile-Target, das den exakten CI-Lint/Format-Lauf inkl. Pin repliziert — als
  Quell-Fix im platform-Template, nicht nur frist-hub).
- `planned-phase-no-issue` ×1 → **mit #3/#18 jetzt ×2 ⇒ GATE-PFLICHT** (Fix =
  Skill-Regel in repo-optimize/session-ende: [FLEET-PATTERN]-Survivor ⇒ Issue-Pflicht).
- `ci-gate-maskiert-failure` neu ×1 (strukturgleich Audit-T3 — Kandidat für
  Fleet-Fix in `_ci-python.yml`, nicht nur Memo).
- `handover-stale-vor-merge` neu ×1 (verwandt mit Drift-Lehre 2026-06-24 —
  session-start Phase 2.6 prüft Handover↔Memory am START; diese Session zeigt
  die Lücke am ENDE).
- refuted_rate dieser Retro: **0.0** — vierte Retro in Folge <0.2 (Band-Warnung
  „Falsifikation ist Theater"); Gegengewicht: Skeptiker korrigierte real den
  Collector (K1) und verifizierte K2 gegen die Session-Behauptung.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates** (zusätzlich zu den 3 noch offenen aus dem Audit-Report):

```markdown
---
name: ci-gate-maskiert-failure
description: continue-on-error-Jobs machen needs-Results grün — Required-Check "ci / gate" schützt NICHT vor deren Failures (frist-hub 2026-07-02, strukturgleich Audit-T3 Exit-5-Fallback)
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-07-02-frist-hub-gate-maskierung
---
In `_ci-python.yml` steht `test-integration` auf `continue-on-error: true` — sein needs-Result im gate-Job ist immer success, der rote Job blockiert nichts.
**Why:** Branch-Protection auf "ci / gate" suggeriert Vollschutz, der für maskierte Jobs nicht existiert (3× empirisch belegt, Runs 28589529523/28588979006/28589188805).
**How to apply:** Vor dem Setzen eines Required-Checks einen realen Run job-weise inventarisieren: continue-on-error-Jobs auflisten und bewusst entscheiden. Fleet-Fix in [[frist-hub-ci-nie-gelaufen]]-Kontext: _ci-python.yml Kommentar/Design klären.
```

```markdown
---
name: handover-stale-vor-merge
description: AGENT_HANDOVER.md früh im Branch geschrieben ging veraltet auf main (nannte gemergten PR #2 "offen") — Handover als LETZTEN Schritt vor Merge aktualisieren
metadata:
  type: feedback
---
**Why:** Der Handover ist die Wiedereinstiegsdatei; ein stale Handover kostet die Folge-Session Reconciliation-Arbeit (Spiegel-Lücke zu session-start Phase 2.6, die nur am Start prüft).
**How to apply:** Handover-Update ist der letzte Commit vor dem letzten Merge der Session — oder ein eigener Mini-PR danach.
```

**adr_candidates:** keine (alle Fixes folgen bestehenden Mustern — ADR-Threshold-
Policy: CHANGELOG/PR genügt; der platform-Template-Fix ist ein Bugfix, kein
Architektur-Entscheid).

## 7. Maßnahmen (Action Board, aus Soll-Ablauf abgeleitet)

**🟢 Offen — dein Zug**

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Fleet-Issue anlegen: Template-Bug ci.yml + importlinter-Altlasten + runs_on-Default + gate-Maskierung (#3, #1) | platform | Issue neu | 🟢 | Freigabe (du) — Text liefere ich (ich) |
| M2 | CODEOWNERS/Review-Gate für apps/fristen/services.py vor PR-#5-Merge (#6) | frist-hub | — | 🟢 | Entscheid Gate-Form (du) |
| M3 | Memory-Entscheidung: 3 Audit-Kandidaten + 2 neue aus §6 (#5) | — | — | 🟢 | „alle"/Auswahl (du) |

**🔵 Offen — ich kann sofort**

| # | Item | Repo | Status | Next Step |
|---|---|---|---|---|
| M4 | Makefile-Target `check-ci` = exakter CI-Lint/Format-Lauf inkl. ruff-Pin (#7-Prophylaxe, GATE lint-failure-no-local-gate) | frist-hub | 🔵 | PR (ich) |
| M5 | Handover-Refresh (PR #2-#4 gemerged, Protection aktiv, offene Entscheidungen als P0) (#4, #5) | frist-hub | 🔵 | Mini-PR (ich) |
| M6 | Zombie-Run 28585281217 real beenden + verifizieren; gemergte lokale Branches prunen (#8, #23) | frist-hub | 🔵 | Kommando + Nachweis (ich) |
| M7 | Follow-up-Issue Integration-Coverage 53%<80 (#18, GATE planned-phase-no-issue) | frist-hub | 🔵 | Issue (ich) |

## 8. Nicht verifiziert (Restlücken)

- **Org-Level-Rulesets meiki-lra** (EF4): 403 ohne admin:org — billigster Check:
  `gh auth refresh -s admin:org` + `gh api orgs/meiki-lra/rulesets`.
- **Exakter Integration-Coverage-Wert** (52,5 vs. 53): coverage-integration-Artifact
  laden und coverage.xml lesen.
- **Monitor-Fehlkonstruktionen der Session** (limit-6-Fenster beendete einen Monitor
  vorzeitig): nur durch Session-Gedächtnis gedeckt, kein gh/git-Artefakt → **Hypothese**,
  nicht als Befund gezählt.
- **User-Freigabe des Rot-Merges** (#2): liegt im Chat-Transkript, nicht am PR —
  für Dritte am Artefakt nicht nachvollziehbar (genau das ist der Soll-Schritt zu #2).

## Self-Review (Meta-Agent, nur Report-Qualität)

- Belegqualität: 22/23 Befunde mit hartem Artefakt-Anker (Run-ID/SHA/Datei:Zeile); Befund #9 (SI1) war ungenau belegt — Dateipfad nachgetragen.
- Invariante |Soll-Schritte|==|Survivors| exakt erfüllt (8==8, 1:1-Mapping #1–#8 verifiziert).
- Frontmatter schema-vollständig; findings_total=23 deckt sich mit den Tabellenzeilen.
- gate_candidates auf die 3 rekurrenz-bestätigten Slugs (≥2, retro_kpis.py) reduziert; die zwei ×1-Slugs laufen konsistent nur in recurring_findings zur nächsten Zählung.
- refuted_rate=0.0 korrekt als „vierte Retro <0.2 in Folge" ausgewiesen (mtime-verifiziert: 73003f→0181a7-incr→54a76c→a50bc6); Band-Warnung ehrlich, nicht verharmlost.
- Urteil: report-ready = ja (2 Nacharbeiten eingearbeitet).

## Extern-Review-Nachtrag (2026-07-02)

Externes Review fand eine Arithmetik-Inkonsistenz, die Phase-5-Meta-Review NICHT
gefangen hatte: §1 implizierte Baseline ×2 für `claim-before-cheapest-check`,
§5 sagte ×3→×4 — beide landeten zufällig bei ×4. Auflösung per billigstem Check
(retro_kpis.py:108-119 gelesen): Zählregel ist **1 Slug = max +1 pro Report**
(Option A) → §5 war korrekt, §1 korrigiert; Zählregel jetzt explizit im
Frontmatter-Kommentar. Zusätzlich: #2 (einziger kritisch-Befund) fehlte im
risiko_debt-Score-Anker — nachgetragen (Score unverändert 3, Herleitung
vollständig). Lehre für die Skill: Meta-Reviewer-Checkliste prüft Invarianten
und Frontmatter, aber keine **Quersummen-Konsistenz zwischen Sektionen** —
Kandidat für session-retro-Changelog (Phase-5-Checkliste um „Rekurrenz-Zahlen
§1/§5/Frontmatter konsistent?" erweitern).
