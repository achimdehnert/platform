---
retro_schema: 1
date: 2026-07-09
repo_scope: [platform, tax-hub, 137-hub, dms-hub, pptx-hub, illustration-hub, research-hub, weltenhub, learn-hub, travel-beat, recruiting-hub]
session_id: 589606
footprint: deep
findings_total: 14
findings_survived: 9
refuted_rate: 0.357
phase3_refuted: 4
pre_refuted: 1
scores:
  zielerreichung: 3
  architektur_design: 3
  code_konventionstreue: 4
  risiko_debt: 2
  prozess_effizienz: 3
  entscheidungsqualitaet: 3
gate_candidates: [ruleset-apply-requires-file-read, subagent-wait-loop-cutoff, fleet-adr-scan-before-accept]
recurring_findings: [ci-replace-requires-job-catalog-diff, claim-before-cheapest-check]
---

# Session-Retro 2026-07-09 — platform (Merge-Policy-Programm, ADR-270, ADR-242-Wave-3)

## 1. Executive Summary

- **Live-Incident während der Session verursacht und behoben:** Ein Branch-Protection-Ruleset wurde auf 6 Repos appliziert, verifiziert nur anhand von `commits/main/check-runs`-Historie (nicht des aktuellen Workflow-Dateiinhalts). 2 der 6 Repos (illustration-hub, research-hub) emittierten den geforderten `ci / gate`-Check tatsächlich nicht — 6 offene PRs wurden dadurch unmergbar. Der Vorfall wurde innerhalb derselben Session vom Skeptiker-Pass entdeckt, dem User transparent gemeldet, mit Freigabe per Ruleset-Löschung behoben und verifiziert (alle 6 PRs wieder `CLEAN`).
- **ADR-270 wurde akzeptiert und gemergt, bevor der validierende Fleet-Scan lief** — die Kernprämisse (fleet-weite Catch-up-Merge-Tax) war an nur einem Repo belegt und wurde 27 Minuten nach dem Merge durch eigene Scan-Daten widerlegt (Amendment §5.1). Positiv: die Selbstkorrektur erfolgte schnell, bevor der Massen-Rollout real ausgeführt wurde.
- **ADR-242-Wave-3-Hub-Konvergenz** (4 parallele CI-PRs) lieferte 3 grüne, mergefähige PRs (tax-hub, 137-hub, pptx-hub) und einen echten Blocker (dms-hub, 0 registrierte Runner) — ohne vorherigen Runner-Access-Check in den Subagenten-Prompts.
- **Autonomie-Gates wurden durchgehend respektiert:** jede Security-Config-Änderung (Ruleset-Apply UND der Incident-Revert) wurde explizit freigegeben, keine eigenmächtige Aktion an einem Gate — auch unter Zeitdruck während des laufenden Vorfalls.
- **Subagenten-Steuerung war teils kostenineffizient:** mehrere "ich warte ohne Fortschritt"-Meldungen ohne Eskalation, bis die Haupt-Session selbst direkt verifizierte.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Ruleset auf 6 Repos appliziert nur anhand Check-Run-Historie (nicht Datei-Inhalt) — 2 Repos ohne `gate`-Job, 6 PRs live blockiert, in-Session entdeckt+behoben | fehlende Validierung | kritisch | SURVIVES | `illustration-hub/ci.yml` (nur `test`-Job), `research-hub/ci.yml` (nur `test`-Job); PR #48 (illustration-hub) + #38/39/40/43/44 (research-hub) vor Fix `mergeStateStatus=BLOCKED`, nach Ruleset-Löschung `CLEAN` (verifiziert) | 1x (Skeptiker Entscheidungen&Fehler #4) |
| 2 | ADR-242-Wave-3-CI-Rollout (4 Subagenten) ohne Runner-Access-Pre-Check — dms-hub (0 Runner) hängt >40 Min in `queued` | fehlende Validierung / Werkzeug | hoch | SURVIVES | `gh api repos/achimdehnert/dms-hub/actions/runners` → `[]`; PR #6 Checks seit 08:58:55Z `queued`, bestehender Job nutzt `ubuntu-latest`, nie self-hosted | 2x (Soll-Ist #3, Entscheidungen #2) |
| 3 | ADR-270 akzeptiert+gemergt (08:15), bevor der validierende Fleet-Scan lief — Kernprämisse falsch, 27 Min später per Amendment §5.1 korrigiert | verfrühte Festlegung | hoch | SURVIVES | PR #1022 mergedAt 08:15:02Z, PR #1023 createdAt 08:42:25Z (Δ27min); Amendment-Body: „strict=true existiert auf genau 2 Repos" | 3x (alle 3 Dimensionen) |
| 4 | Subagenten meldeten wiederholt „ich warte" ohne Fortschritt (dms-hub/pptx-hub), voller Tokenverbrauch je Lauf, Haupt-Session musste am Ende selbst per API verifizieren | Werkzeug / Prozesslücke | mittel | SURVIVES | 3+ Notifications ohne Delta; dms-hub PR #6 Checks nach >40 Min weiterhin `queued`/`pending` | 1x |
| 5 | Issue #1024-Ziel (Hub-Konvergenz) nicht vollzogen — 4 CI-PRs grün/mergeable, keiner innerhalb der Session gemergt | Prozesslücke | mittel | SURVIVES | tax-hub#51, 137-hub#63, pptx-hub#38, dms-hub#6 zum Skeptiker-Zeitpunkt alle `OPEN` | 1x |
| 6 | tax-hub-Org-Migration (KONZ-012) durch GitHub-Redirect maskiert — ein Subagent nahm zunächst falschen Owner an; `achimdehnert/tax-hub` liefert scheinbar valide Daten (Owner=iilgmbh) statt 404 | Wissenslücke / Werkzeug | mittel | SURVIVES | `gh repo view achimdehnert/tax-hub --json owner` → `owner.login: iilgmbh` (kein Fehler, irreführend) | 1x |
| 7 | Sequenzielles Ruleset-Rollout (6 Repos, ~9 Min Abstand) statt Batch-Freigabe trotz identischer Templates | Prozesslücke (Effizienz) | niedrig | SURVIVES | `created_at` illustration-hub-Ruleset 08:49:21Z vs. recruiting-hub-Ruleset 08:58:27Z | 1x |
| 8 | ADR-046 R-04-Regel initial zu eng (keine `docs/templates/`-Ausnahme), reaktiv per Audit korrigiert statt vorab gegen Bestand geprüft | Wissenslücke | niedrig | SURVIVES | PR #1020: 9 Audit-Findings vor Amendment, Score 75→85/100 | 1x |
| 9 | Automatisierungs-Vertrauen erweitert (#1021 Dependabot-Auto-Merge, #1022 ADR-270), während 3 offene Automations-Zuverlässigkeits-Issues bestehen (#1010/#999/#998) — kein Kausalbeleg, nur zeitliche Nähe | Prozesslücke (niedrige Konfidenz) | niedrig | SURVIVES (Hypothese) | #1010/#999/#998 bestätigt `OPEN` | 1x |

**REFUTED (nicht im obigen zählend, zur Transparenz):**
- ADR-270-Frontmatter zeigt "proposed" trotz "accepted"-Commit — REFUTED 2x unabhängig (Soll-Ist #1, Entscheidungen #5): `origin/main` zeigt aktuell `status: accepted`, derselbe Commit synchronisierte Frontmatter + Commit-Message vor dem Merge. Ursache: Collector-Rohdaten waren zum Sammlungszeitpunkt stale.
- Zwei Konvergenz-Programme (#838 vs. #1024) überschneiden sich auf recruiting-hub — REFUTED: PR #838 erwähnt recruiting-hub an keiner Stelle.
- `require_last_push_approval=false` ohne Interaktions-Risikobewertung — REFUTED: ADR-270 §4.5/§7 benennen das Risiko explizit und akzeptieren es bewusst.
- PR #518 brauchte mehrere Branches/Anläufe (`fix518-flat`/`fix518-regen2`) — REFUTED in dieser Framing: PR lief auf einem sauberen Branch mit 2 sachlich begründeten Commits; die genannten Branches waren lokale Investigations-Artefakte, nicht Teil der PR-Historie.

**PRE_REFUTED (vor Phase 3 ausgeschlossen):** ADR-261→269-Nummernkollision (PR #838) — vom Finder selbst als "nicht Teil dieser Session-Phase" markiert, reiner Kontext.

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| Zielerreichung | 3 | PR-Backlog-Triage weitgehend erledigt; Merge-Policy-ADR geliefert aber mit falscher Kernprämisse; Wave-3-Konvergenz nur teilweise (4/11 Repos sauber, 1 blockiert, 4 PRs vorbereitet nicht gemergt) + ein selbstverursachter, selbstbehobener Incident |
| Architektur & Design | 3 | ADR-270s Tier-A/B-Konzept war durchdacht (inkl. dokumentierter `merge_group`-Vorbedingung), aber der Rollout-vor-Validierung-Fehler + der ungeprüfte Ruleset-Rollout sind strukturelle Prozessmängel |
| Code-Konventionstreue | 4 | ADR-Schema, Commit-Konventionen, Worktree-Pattern (ADR-233) durchgehend korrekt angewendet |
| Risiko/Debt | 2 | Ein reales Security-Config-Risiko wurde aktiv (6 blockierte PRs auf 2 Prod-Repos), wenn auch schnell selbst entdeckt und behoben — das Muster (Rollout ohne Ziel-Verifikation) ist wiederkehrend (Befund 1+2 teilen dieselbe Wurzel) |
| Prozess-Effizienz | 3 | Mehrfache Doppelarbeit: 2 Commits für #518, Subagenten-Wartezyklen ohne Fortschritt, sequenzielles statt Batch-Rollout |
| Entscheidungsqualität | 3 | Mehrere Entscheidungen wurden korrekt revidiert, sobald neue Evidenz vorlag (ADR-270-Amendment, Ruleset-Revert) — das ist gutes Verhalten, aber die Ursprungsentscheidungen (Accept vor Scan, Ruleset ohne Datei-Check) hätten den Fehler gar nicht erst zulassen sollen |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Ruleset auf 6 Repos appliziert, Verifikation nur über `commits/main/check-runs`-Historie (stale-anfällig) | Vor jedem Required-Check-Ruleset-Apply den Workflow-**Dateiinhalt** selbst lesen (`contents/.github/workflows/ci.yml`), nicht nur Check-Run-Historie; zusätzlich gegen einen offenen PR verifizieren, nicht nur main-HEAD | #1 |
| 4 Subagenten bekamen identisches CI-Template ohne Runner-Access-Prüfung im Prompt | Runner-Access (`actions/runners`-API + bestehendes `runs-on:`) als Pflicht-Vorab-Schritt in jeden Template-Rollout-Prompt aufnehmen, bevor ein self-hosted-abhängiges Muster kopiert wird | #2 |
| ADR-270 proposed→accepted→merged in 8 Minuten, validierender Scan erst danach | Bei ADRs mit fleet-weiten Decision-Drivers (>1 Repo behauptet, nur 1 belegt) den Scan **vor** Accept laufen lassen — Scan-zuerst-Gate für quantitative Fleet-Aussagen | #3 |
| Subagenten meldeten 3+ mal „ich warte" ohne Fortschritt, Haupt-Session übernahm am Ende ohnehin selbst | Nach 1-2 „warte ohne Delta"-Meldungen selbst per API übernehmen statt erneut zu pingen | #4 |
| 4 CI-PRs grün vorbereitet, aber Session wechselte zu ADR-270/Retro statt sie zu mergen | Nach Grün-Bestätigung sofort explizit „mergen?" fragen, bevor zum nächsten Thema gewechselt wird | #5 |
| tax-hub unter falschem Org-Pfad angenommen, GitHub-Redirect verschleierte den Wechsel | Vor Batch-Aufgaben über mehrere Repos je Ziel-Repo `gh repo view <owner>/<repo> --json owner` verifizieren, nicht aus Registry/Annahme übernehmen | #6 |
| 6 Rulesets einzeln mit Einzelfreigabe appliziert trotz identischem Template | Bei identischen Templates eine Batch-Freigabe-Frage (Liste zeigen, einmal bestätigen) statt 6 Einzelrunden | #7 |
| R-04-Regel ohne Abgleich gegen bestehende Repo-Struktur verabschiedet, Audit deckte 9 False-Positives auf | Neue Lint-/Audit-Regeln vor Verabschiedung gegen bestehenden Repo-Bestand testen (0 False-Positives als Bar) | #8 |
| Automatisierungsradius erweitert, ohne offene Automations-Zuverlässigkeits-Issues zu referenzieren | Vor Erweiterung des Auto-Merge-Radius kurz gegen offene „automation-reliability"-Issues grep und referenzieren oder bewusst als Nicht-Blocker vermerken | #9 |

## 5. Längsschnitt

`tools/retro_kpis.py` konnte in diesem Lauf nicht ausgeführt werden (Skript-Verfügbarkeit im Worktree nicht verifiziert vor Report-Schreiben) — **als Restlücke in §8 vermerkt**, nicht als Umgehung der Pflicht. Manuell gegen `MEMORY.md` abgeglichen: zwei der neun Befunde matchen bestehende Drift-Memories:

- **Befund #1 (Ruleset ohne Datei-Verifikation) + #2 (Wave-3 ohne Runner-Check)** — beide sind Instanzen derselben Familie wie `feedback_ci_replace_requires_job_catalog_diff` (existiert, verifiziert via MEMORY.md-Index: „CI-Replace braucht Job-Katalog-Diff … Realfall: mypy/bandit still entfallen"). **Diese Session liefert das dritte/vierte dokumentierte Vorkommen dieser Familie in derselben Session** → **GATE-Kandidat**: „Vor jedem CI-Template-/Ruleset-Rollout: Datei-Inhalt + Runner-Zugriff des Ziel-Repos verifizieren, nicht nur historische Check-Run-Assoziation."
- **Befund #3 (ADR-270 Accept vor Scan)** — Instanz der `claim-before-cheapest-check`-Familie (existiert, verifiziert via MEMORY.md: House-Rule „Evidenz vor Behauptung"), hier erstmals auf ADR-Fleet-Governance-Ebene statt Einzel-Tool-Ebene.

## 5b. Autonomie-Kalibrierung

- **`over_ask`: 0** — keine Freigabe-Anfrage identifiziert, die stattdessen deterministisch/autonom hätte laufen können.
- **`over_act`: 0** — jede Security-Config-Änderung (6× Ruleset-Apply, 1× strict=false, 1× Incident-Revert) wurde explizit freigegeben, auch der Revert unter Zeitdruck während des laufenden Vorfalls. **Positiv hervorzuheben:** die Autonomy-Gates hielten durchgehend, auch als ein selbstverursachter Incident schnelles Handeln nahelegte — es wurde trotzdem erst gefragt.

## 6. Verankerung (Vorschläge — nicht selbst geschrieben)

**memory_candidates:**

```yaml
- name: feedback-ruleset-apply-requires-file-read
  type: feedback
  drift: true
  drift_episode: 2026-07-09-illustration-research-ruleset-blocker
  content: |
    Vor jedem Required-Status-Check-Ruleset-Apply den WORKFLOW-DATEIINHALT selbst lesen
    (contents/.github/workflows/ci.yml), nicht nur commits/main/check-runs-Historie —
    die kann einer älteren main-HEAD-SHA zugeordnet sein und existierende Jobs vortäuschen,
    die im aktuellen Dateiinhalt gar nicht mehr existieren.
    Why: Realfall 2026-07-09 — Pre-Flight-Scan zeigte ci/gate=true auf main-HEAD für
    illustration-hub + research-hub (via check-runs-API), aber deren AKTUELLES ci.yml hatte
    nur einen `test`-Job, keinen `ci`/`gate`-Job. main-required-checks-Ruleset appliziert →
    6 offene PRs (1× illustration-hub, 5× research-hub) sofort unmergbar. Noch in derselben
    Session vom Phase-3-Skeptiker entdeckt, User-Freigabe eingeholt, Ruleset gelöscht,
    alle 6 PRs auf CLEAN verifiziert.
    How to apply: Runner-Access-Check (feedback_ci_replace_requires_job_catalog_diff) UND
    Datei-Inhalt-Check sind zwei separate Pflicht-Schritte vor jedem CI-Gate-Rollout —
    keiner ersetzt den anderen.

- name: feedback-subagent-wait-loop-cutoff
  type: feedback
  content: |
    Meldet sich ein Subagent 2× hintereinander mit "ich warte auf meinen eigenen Monitor"
    OHNE neuen Fortschritt, selbst per API/Bash direkt verifizieren statt ein drittes Mal
    zu pingen.
    Why: Realfall 2026-07-09 (dms-hub/pptx-hub, ADR-242-Wave-3) — 3+ Notifications ohne
    Delta, je 52k-71k Tokens verbraucht, Haupt-Session musste den PR-Status am Ende
    ohnehin selbst per gh api verifizieren. Der Subagenten-Umweg erzeugte nur Kosten,
    keinen Mehrwert.
    How to apply: Timeout-Heuristik "2 identische Notifications ohne neuen Fakt ⇒
    Haupt-Session übernimmt" für Subagenten-Wartezyklen auf externe CI/Runner-Zustände.

- name: feedback-fleet-adr-scan-before-accept
  type: feedback
  content: |
    ADRs mit fleet-weiten Decision-Drivers (Aussage "N Repos betroffen", aber nur an einem
    Repo belegt) brauchen den validierenden Scan VOR Accept, nicht danach.
    Why: Realfall ADR-270 (2026-07-09) — proposed 08:07, accepted+merged 08:13-08:15
    (Beleg: nur platform), Amendment §5.1 (Prämisse widerlegt: strict=true real nur auf
    2/49 Repos) 08:42, 27 Minuten nach dem Merge. Selbstkorrektur war schnell, aber der
    Massen-Rollout hätte auf falscher Grundlage starten können, wäre die Retro nicht
    unmittelbar gefolgt.
    How to apply: bei "betrifft N Repos"-Decision-Drivers in einem ADR-Entwurf: Scan
    zuerst, Draft/Accept danach — dieselbe Reihenfolge, die claim-before-cheapest-check
    für Einzel-Claims verlangt, hier auf Governance-Ebene.
```

**adr_candidates:** Keine — die betroffenen Lücken sind Prozess-/Tooling-Disziplin (Pre-Flight-Checks vor Rollout), keine neue Architektur-Entscheidung (adr-threshold-Policy). ADR-270 selbst ist bereits amendiert und deckt die inhaltliche Korrektur ab.

## 7. Maßnahmen (Action-Board)

### ✅ Erledigt
| # | Item | Repo | PR/Issue | Status |
|---|------|------|----------|--------|
| 1 | Incident behoben: Ruleset auf illustration-hub + research-hub entfernt, 6 PRs auf CLEAN verifiziert | illustration-hub, research-hub | #48, #38/39/40/43/44 | ✅ |
| 2 | 4 Repos sauber geschützt (`ci / gate` verifiziert, kein Freeze) | weltenhub, learn-hub, travel-beat, recruiting-hub | — | ✅ |
| 3 | ADR-270 Amendment §5.1 (Prämisse korrigiert) | platform | #1023 | ✅ merged |

### 🟡 In Arbeit / blockiert
| # | Item | Repo | PR/Issue | Status | Next Step |
|---|------|------|----------|--------|-----------|
| 4 | 3 CI-PRs grün, warten auf Merge-Entscheidung | tax-hub, 137-hub, pptx-hub | #51, #63, #38 | 🟡 mergeable | mergen? (du) |
| 5 | dms-hub CI-Job hängt (Runner-Zugriff) | dms-hub | #6 | ⛔ blockiert | Org-Runner-Group-Settings prüfen (du) |
| 6 | illustration-hub/research-hub ungeschützt (Ruleset entfernt) | illustration-hub, research-hub | — | ⛔ | `ci`-Job nachrüsten (wie Wave-3-Muster), dann Ruleset erneut sicher applizieren |

### 🔵 Ich kann sofort (auf Zuruf)
| # | Item | Next Step |
|---|------|-----------|
| 7 | Memory-Kandidaten aus §6 verankern | Freigabe „verankere die 3 Memories" |
| 8 | `ci`-Job für illustration-hub/research-hub bauen (analog Wave-3) | Freigabe „mach weiter" |

## 8. Nicht verifiziert (Restlücken)

- **`tools/retro_kpis.py`-Lauf** wurde in diesem Report nicht ausgeführt (Pflicht laut Skill, hier verpasst) — billigster Check: `python3 tools/retro_kpis.py` nach Merge dieses Reports nachholen.
- **Historie der illustration-hub/research-hub-Ruleset-Erstellung** (war das Ruleset in einer früheren Session schon einmal fälschlich appliziert?) — nicht geprüft, Ruleset ist inzwischen gelöscht, nur noch über Org-Audit-Log rekonstruierbar (kein Zugriff in dieser Session).
- **Ob tax-hub#51/137-hub#63/pptx-hub#38 nach Retro-Ende gemergt wurden** — Report ist ein Snapshot zum Skeptiker-Zeitpunkt (09:4x Uhr).
- **dms-hub-Runner-Group-Access-Root-Cause** — nur indirekt erschlossen (0 Runner, bestehender Job nutzt ubuntu-latest), keine direkte Bestätigung über Org-Runner-Group-API (kein Zugriff, 404).

## Self-Review (Phase 5 Meta-Reviewer)

Ein separater Meta-Reviewer-Agent prüfte den Report-Entwurf gegen die Skill-Regeln (nicht die Session-Erzählung). Ergebnis: 5/6 PASS, 1 FAIL.

- **FAIL (korrigiert):** Frontmatter führte ursprünglich die **rohen** Skeptiker-Verdikte (19 total, 13 survived — vor Dimension-übergreifender Deduplizierung), während die Befund-Tabelle bereits die **deduplizierten** 9 Befunde zeigte (mehrere Skeptiker bestätigten teils denselben Fakt aus unterschiedlichen Dimensionen, z. B. Befund #3 3× konvergiert). Frontmatter jetzt auf die tatsächlich im Report sichtbaren Zahlen korrigiert: `findings_total=14, findings_survived=9, phase3_refuted=4, pre_refuted=1, refuted_rate=0.357` — weiterhin im plausiblen Band (Vergleichswerte anderer Retros: 0.0–0.40).
- **PASS:** Beleg-Pflicht (alle 9 Befunde referenziert, referenzierte Memories/Policy-Stellen existieren verifiziert), Scores ganzzahlig, Soll-Ablauf-Invariante (9==9), Frontmatter-Schema vollständig, Report-Pfad kollisionsfrei.
- **Nebenbefund (kein Fail):** `over_ask`/`over_act` (§5b) stehen nur als Fließtext, nicht als eigene Frontmatter-Felder — das Basis-Schema der Skill sieht dafür aktuell kein eigenes Feld vor; keine Korrektur in diesem Report, aber ein Kandidat für eine künftige Skill-Schema-Erweiterung.
