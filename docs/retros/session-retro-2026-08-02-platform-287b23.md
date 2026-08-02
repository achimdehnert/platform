---
retro_schema: 1
date: 2026-08-02
repo_scope: [platform]
session_id: 287b23
footprint: full
findings_total: 10
findings_survived: 7
refuted_rate: 0.3
phase3_refuted: 3
pre_refuted: 0
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 4
  entscheidungsqualitaet: 4
gate_candidates: [drill-path-not-invocation-path]
recurring_findings: [claim-before-cheapest-check, planned-phase-no-issue, issue-not-reconciled-after-cross-repo-fix, always-instruction-without-enforcement, drill-path-not-invocation-path, gate-backlog-unpriorisiert, scanner-channel-blindspot, same-file-serial-prs]
---

# Session-Retro · platform · 2026-08-02 (287b23)

Session-Inhalt: Lotse-Ausbau-Programm KONZ-platform-038 (Regel-Lebenszyklus) — Konzept
(2 externe + 3 interne Reviews), regel-ritual-Workflow, Gate-Welle 1 (5 Slugs), D6-Baseline,
D7/D8. 10 PRs (1639, 1641, 1643–1646, 1648, 1653, 1655, 1658), alle einzeln owner-approved.
Pipeline: 1 Collector (haiku) + 3 Finder (sonnet) + 1 gebündelter Skeptiker (sonnet, nur
Bewertungsbefunde) + 1 Meta (sonnet).

## 1. Executive Summary

- Programm vollständig gemergt und owner-getaktet — aber der neue Drill-Mechanismus wiederholte
  strukturell das §7-Paradox, das er heilen sollte: Drills testeten den Interpreter-Pfad, nicht
  den echten settings-Aufrufpfad; 2 von 5 Gates lagen mit Mode 100644 im Index (fremder PR #1660
  musste fixen).
- Publizierter Claim „D1–D8 vollständig umgesetzt" (PR-1658-Kommentar) war falsch — D4 ist
  unausgeführt (0 `rule_class:`-Treffer) und fehlt in der §13-Tracking-Tabelle.
- Falsifikation wirkte: 3 von 3 Bewertungsbefunden REFUTED (Skills-Moratorium ist getrackt,
  Baseline-Wahl war vorregistriert+diskutiert, Einzel-Approvals waren owner-getaktet).
- Rückmeldung auf Gate-Issues nach dem Bau unterblieb teilweise (#1186/#1190 leer) — die
  Lesefläche-Lehre griff nicht überall.
- 14/18 Slug-Issues unberührt, Welle-2-Reihenfolge nach §5.2-Formel nirgends materialisiert.

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Drill testete Interpreter-Pfad statt settings-Aufrufpfad; 2/5 Gates Mode 100644, real nicht ausführbar; §13-K4 überzeichnet | fehlende Validierung | kritisch | SURVIVES (kommandobelegt) | `git ls-tree origin/main tools/claude-hooks/` → 100644 deferred/scope; Tests nutzen `importlib`, kein subprocess; PR #1660 OPEN fixt | Familie `dry-run-does-not-cover-write-path` (Memory existiert) → `drill-path-not-invocation-path` ×1 |
| 2 | Gate gebaut, Slug-Issue ohne Abschluss-Rückmeldung (#1186, #1190: 0 Kommentare) | Prozesslücke | hoch | SURVIVES (kommandobelegt) | `gh issue view 1186/1190 --json comments` → leer; Gates in gate-registry.json + gemergt | `issue-not-reconciled-after-cross-repo-fix` (bisher ×2 → ×3) |
| 3 | D4 unausgeführt (0 `rule_class:`-Treffer) + keine §13-Zeile + publizierter Claim „D1–D8 vollständig umgesetzt" | fehlende Validierung / Prozesslücke | hoch | SURVIVES (kommandobelegt) | `git grep -c "rule_class:" origin/main -- '*.md'` = 1 (nur KONZ-Doku); §13-Tabelle ohne D4; PR-1658-Kommentar 10:10 UTC | `planned-phase-no-issue` (×7 → ×8) + `claim-before-cheapest-check` (Vorkommen in DIESER Session, zählt ins Messfenster 1) |
| 4 | Welle-2-Backlog unpriorisiert: 14/18 Slug-Issues 0 Kommentare, §5.2-Formel (Zähler×Schadensklasse) nirgends auf Rest-Slugs angewendet | Prozesslücke | mittel | SURVIVES (kommandobelegt) | `gh issue view <n> --json comments` über alle 18 IDs | `gate-backlog-unpriorisiert` ×1 |
| 5 | §5.3 verspricht Lücken-Selbstprüfung (>20 Tage auf #1640), Workflow enthält sie nicht | Kommunikation (Doku > Realität) | niedrig | SURVIVES (kommandobelegt) | regel-ritual.yml voll gelesen; `git grep "20 Tage"` → 0 | `always-instruction-without-enforcement` (×4 → ×5) |
| 6 | deferred-Scanner-Lücken: „verschoben/verschieben" fehlt (FN); MCP-Tool-Aufrufe (`mcp__github__create_issue`) nicht als Tracking erkannt (FP-Klasse); beides untestet | Werkzeug (Scanner-Kalibrierung) | mittel | SURVIVES (kommandobelegt) | `git show origin/main:tools/claude-hooks/deferred_item_scanner.py` — Patterns + `_TRACKING_*` gelesen; Testdatei deckt beide Pfade nicht | `scanner-channel-blindspot` ×1 |
| 7 | regel-ritual.yml in 4 sequenziellen eigenen PRs geändert (1641, 1643, 1648, 1658) | Prozess (PR-Kadenz) | niedrig | SURVIVES (kommandobelegt) | `gh pr view <n> --json files` ×10 | `same-file-serial-prs` ×1 |
| 8 | Skills-Hebel angeblich ohne Wiederaufnahme-Tracking | — | mittel | REFUTED | §13-Zeile „D5-Zaun-Ablaufdatum mechanisch geprüft" mit Datum 2026-09-13 = zulässiges KONZ-Zeilen-Tracking (CLAUDE.md-Konvention) | — |
| 9 | Baseline-Fenster-Wahl angeblich unbegründet | — | mittel | REFUTED | §12-D6-Wortlaut „Baseline-Top-Slugs" (fensterbezogen, vorregistriert) + Abschnitt „Hinweis zur Zusammensetzung" im Baseline-Doc (Vergleichsgruppen-Argument) | — |
| 10 | Approval-Kadenz der letzten 3 PRs angeblich unnötig gestreckt | — | niedrig | REFUTED | 1658-firstCommit 10:01 = 38 Min NACH 1655-Merge 09:21 — Bündeln war ohne Zurückhalten des D6-Merges unmöglich; owner-getaktet | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | D1–D3, D5–D8 geliefert + gemessen (PRs 1639–1658); D4 offen + K4-Status überzeichnet (#1, #3) |
| architektur_design | 4 | Konzept extern validiert, Reconcile-vor-Bau trug (5/5 Gates unterschiedliche Fixes); Drill-Design-Blindfleck in-process-Import (#1) |
| code_konventionstreue | 4 | Format-Gate 2× gegriffen und befolgt; Mode-Bits übersehen (#1) |
| risiko_debt | 4 | Baseline/Registry/Ledger-Zeilen durabel; Backlog-Priorisierung + Issue-Rückmeldung fehlten (#2, #4) |
| prozess_effizienz | 4 | 10 PRs ohne Rework-Schleifen, Fremd-Kollisionen 0 (belegt); serielle Datei-Änderungen (#7), Fremd-PR musste nachfixen (#1) |
| entscheidungsqualitaet | 4 | 3/3 Bewertungs-Anklagen widerlegt (Entscheidungen waren dokumentiert+getaktet); „vollständig"-Claim ohne Item-Check (#3) |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Drill-Tests luden Hooks per `importlib`; settings ruft Datei direkt (100644 → Permission denied; PR #1660) | Hook-Contract-Test ruft die Datei per `subprocess` GENAU wie settings auf + `git diff --summary` vor jedem Commit neuer Executables in die Drill-Checkliste | #1 |
| Gate-PRs gemergt, Slug-Issues #1186/#1190 blieben stumm | D2-Sequenz um Schritt 4 ergänzen: Merge ⇒ Abschluss-Kommentar auf dem Slug-Issue im SELBEN Zug (Lesefläche-Regel) | #2 |
| „D1–D8 vollständig umgesetzt" publiziert; D4 = 0 Treffer, keine §13-Zeile | Jede §12-D-Zeile bekommt bei Anlage eine §13-Tracking-Zeile; ein „vollständig"-Claim erst nach Item-für-Item-Grep (billigster Check existierte: `git grep rule_class:`) | #3 |
| 14/18 Slug-Issues unberührt, keine Welle-2-Reihenfolge | §5.2-Formel einmal auf die 13 Rest-Slugs anwenden und als Kommentar auf Sammel-Issue #705 materialisieren | #4 |
| §5.3-Zusage „Lücken-Selbstprüfung" ohne Workflow-Implementierung | Doku-Sätze über Automatik nur im selben PR wie die Implementierung — sonst explizit als „offen (nicht gebaut)" markieren | #5 |
| Scanner-Muster/Tracking-Kanäle enger als die Realität (kein „verschoben", kein MCP-Kanal) | FP/FN-Kandidatenliste als Testfälle VOR dem blocking-Upgrade ins Kalibrierfenster aufnehmen | #6 |
| regel-ritual.yml 4× seriell angefasst | Workflow-Datei-Änderungen einer Session sammeln, wenn kein Owner-Gate dazwischen liegt (hier lagen Gates dazwischen — daher nur niedrig) | #7 |

## 5. Längsschnitt

`python3 tools/retro_kpis.py` (gehärtete Fassung, dieser Report noch exklusive): Top-Zähler
claim-before-cheapest-check ×34 → mit diesem Report ×35 — **das Vorkommen fällt ins
Messfenster 1 der eigenen K1-Baseline und zählt gegen die 0.500-Rate.** planned-phase-no-issue
×7→×8, issue-not-reconciled ×2→×3, always-instruction-without-enforcement ×4→×5 — alle vier
bereits gate-pflichtig/getrackt (#1185, #1188, #1633, #1182). Neu: `drill-path-not-invocation-path`
×1 (Familie der existierenden Drift-Memory `feedback_dry_run_does_not_cover_write_path` —
Existenz im Memory-Index belegt).

**5b Autonomie-Kalibrierung:** `over_ask: 0` — alle 10 Owner-Runden waren ruleset-erzwungen
(Review-Pflicht), nicht agent-gewählt. `over_act: 0` — keine der 5 Gate-Klassen autonom
überschritten (Issue-Anlage lief über das sanktionierte `--file-issues`; Cron ist
Actions-Schedule per Review-PR). Keine Charter-Schärfung nötig.

## 6. Verankerung (Vorschläge — Verankerung entscheidet der Mensch)

`memory_candidates`:
```markdown
---
name: feedback_drill_must_use_invocation_path
description: "Hook-Drill muss den ECHTEN Aufrufpfad nutzen (subprocess wie settings.json), nicht importlib — 2/5 Welle-1-Gates lagen mit 100644 im Index, fremder PR #1660 musste fixen"
metadata: {type: feedback, drift: true, drift_episode: 2026-08-02-mode-bit-drill}
---
🌀 Ein Drill, der das Modul per importlib lädt, beweist NICHT, dass der Hook läuft —
settings.json ruft die Datei DIREKT (Shebang braucht +x). 2026-08-02: deferred_item_ und
scope_checkpoint_scanner lagen mit Mode 100644 im Index; python3-Livetest verschleierte es.
**Why:** Testpfad ≠ Aufrufpfad ist dieselbe Klasse wie [[feedback_dry_run_does_not_cover_write_path]].
**How to apply:** Hook-Contract-Test per subprocess auf die Datei selbst; vor Commit neuer
Executables `git diff --summary` (zeigt mode); Drill-Definition in gate-registry entsprechend.
```

`adr_candidates`: keine (Additions folgen bestehendem KONZ-038-Muster; adr-threshold nicht erreicht).

## 7. Maßnahmen (Action-Board, aus dem Soll-Ablauf)

### 🟢 Offen — dein Zug

1. 🟢 Fremden Fix-PR mergen — https://github.com/achimdehnert/platform/pull/1660

### 🔵 Offen — ich kann sofort (nächste Session)

2. 🔵 Drill auf subprocess-Aufrufpfad + mode-Check (#1) — https://github.com/achimdehnert/platform/issues/1640
3. 🔵 Abschluss-Kommentar Gate gebaut (#2) — https://github.com/achimdehnert/platform/issues/1186
4. 🔵 Abschluss-Kommentar Gate gebaut (#2) — https://github.com/achimdehnert/platform/issues/1190
5. 🔵 D4 ausführen oder §13-Zeile „offen" + Claim-Korrektur (#3) — https://github.com/achimdehnert/platform/pull/1658
6. 🔵 Welle-2-Priorisierung per §5.2-Formel (#4) — https://github.com/achimdehnert/platform/issues/705
7. 🔵 §5.3-Zusage korrigieren oder bauen (#5) — https://github.com/achimdehnert/platform/issues/1640
8. 🔵 Scanner-Testfälle „verschoben"/MCP-Kanal (#6) — https://github.com/achimdehnert/platform/issues/1632

## 8. Nicht verifiziert (Restlücken)

- Chat-only-Entscheidungen: Finder ohne Transkript-Zugriff konnten nicht prüfen, ob eine
  wichtige Entscheidung nur im Chat fiel — billigster Check: Transkript-Grep gegen
  Entscheidungsliste (nächste Session, wenn gewünscht).
- Prod-Uptime-Canary-Failure 10:09 UTC: nicht dieser Session zugeordnet, nicht diagnostiziert —
  billigster Check: `gh run view` des Canary-Laufs.
- Maschinen-Kopien ~/.claude/hooks waren zur Prüfzeit executable (rwxr) — WER das Bit setzte
  (diese Session via chmod nur bei model_change_detector; deferred/scope unklar) ist nicht
  rekonstruiert; folgenlos, da Quell-Fix in #1660.
- Der Skeptiker lief gebündelt über 3 Befunde statt je-Befund (Skill erlaubt beides bei n=3);
  Einzel-Skeptiker hätten evtl. schärfer getrennt.
- Eigen-Befund am D6-Werkzeug (beim Pflicht-KPI-Lauf entdeckt): die neue Slug-Validierung
  wendet SLUG_RE auch auf `repo_scope` an und schließt legitime pfad-artige Werte aus
  (`~/.claude`, `bahn-sqf/pg-hub` in 3 Alt-Retros) — kosmetisch (repo_scope wird nicht
  aggregiert), aber ein Validator-False-Positive; billigster Fix: strikte Validierung nur
  für recurring_findings/gate_candidates.

**Abschluss-Vierer:** getan: Collector+3 Finder+1 Skeptiker, 10 Befunde, 3 falsifiziert ·
angenommen: Merge-Zeitstempel = Owner-Taktung (plausibel, chat-gestützt) · nicht verifizierbar:
Chat-only-Entscheidungen, Canary-Ursache · offen geblieben: Maßnahmen 2–5 (Board oben).
