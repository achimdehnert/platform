---
retro_schema: 1
date: 2026-07-04
repo_scope: [platform, iil-adrfw, outlinefw]
session_id: e17299-incr
footprint: full
footprint_reduction_reason: "Rule-B deep (3 Repos + Security-Config-PATCH) -> full: (a) jede Aktion explizit user-freigegeben ('1 wiederherstellen 2 go 3 go 4 go', in PR-Bodies referenziert), (b) voll reversibel (Workflows/Docs/Protection, keine Migration), (c) Befund-Schaetzung <=10"
findings_total: 7
findings_survived: 3
refuted_rate: 0.57
phase3_refuted: 3
pre_refuted: 1
over_ask: 0
over_act: 0
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 5
  risiko_debt: 3
  prozess_effizienz: 5
  entscheidungsqualitaet: 4
gate_candidates: [critical-alert-no-ticket]
recurring_findings: [critical-alert-no-ticket, claim-before-cheapest-check]
---

# Increment-Retro 2026-07-04 — Follow-ups der Retro e17299 (Anchor, same-day)

Scope: NUR das Follow-up-Increment ~13:20–14:20 UTC (Parent e17299 nicht re-litigiert):
platform#920 (_ci-pypi gate/mypy_blocking/enable_bandit) + #922 (ADR-Pflege) + Issue #921;
iil-adrfw#48 (Dependabot-Fix) + #49 + Protection-PATCH auf `ci / gate`; outlinefw#15;
2 Memories. Methode: 1 Collector (haiku) + 3 Finder + 1 gebündelter Skeptiker + Meta (sonnet).

## 1. Executive Summary

- Alle 4 freigegebenen Board-Items + 2 Zusagen artefakt-vollständig geliefert; Soll-Ist-Finder
  fand **0 Abweichungen** (inkl. korrekt asymmetrischer bandit-Parität — outlinefw hatte nie bandit).
- Das Reusable-Verifikationsprotokoll wurde vorbildlich eingehalten (Consumer grün auf
  @feature-ref VOR #920-Merge, per Check-Run-Zeitstempeln unabhängig belegt).
- Härtester Survivor: **ADR-266 enthält seit #922 eine unbelegte Fähigkeits-Zusage**
  („der Health-Report hält offene Bot-PRs sichtbar" — das Tool hat keinerlei PR-Logik):
  frische `claim-before-cheapest-check`-Instanz im eigenen Governance-Doc (B5).
- **bandit-Reaktivierung erzeugte einen roten Check ohne Baseline/Ticket** (B2) — zweites
  Vorkommen `critical-alert-no-ticket` ⇒ same-day Gate-Pflicht (Increment-Regel).
- Falsifikation griff hart: 4/7 verworfen — u. a. „Dependabot-Force-Push-Risiko" (stoppt
  nach Human-Commit) und „outlinefw-Erstlauf vermeidbar" (das war der Verifikations-PR,
  der wie designed arbeitete).

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|--------|-----------|----------|---------|-------|------------|
| B1 | `gate`-Job: needs-Liste manuell, kein Konsistenz-Test; Caller mit `enable_build:false` würde Artefakt-Scan skippen und gate bliebe grün (skipped=ok) — Zukunftsrisiko, heute 0/15 Caller betroffen (unabhängig nachgezählt) | verfrühte Festlegung | mittel | SURVIVES | _ci-pypi.yml gate-Job; 15 Caller-ci.yml gegrept: 0× enable_*=false; tools/tests ohne gate-needs-Check | — |
| B2 | bandit-Reaktivierung (iil-adrfw#49) ohne Baseline: 4 Low-Findings (B110/B112 cli.py, B101 server.py) → Check `ci / SAST` rot auf dem (bisher einzigen) main-Lauf, kein Ticket. NEUER Debt: alte CI zeigte via step-level continue-on-error GRÜN (2 Alt-Runs geprüft) | fehlende Validierung | hoch | SURVIVES | run 28708849022 Jobs; Alt-Runs 28647317470/28642748028 security=success; kein Issue | critical-alert-no-ticket ×2 (Parent F4 + hier) ⇒ GATE |
| B3 | #48-Fix per Push auf Dependabot-Branch riskierte Force-Push-Überschreibung (rebase-strategy auto) | — | niedrig | REFUTED | Dependabot stoppt Rebase nach Human-Commit (PR-Body-Klausel; kein rebase-Kommando); Risiko by-design nahe null | — |
| B4 | outlinefw#15-Erstlauf rot war vermeidbar (pyproject [tool.mypy] packages war vorab lesbar) | — | niedrig | REFUTED | Roter Lauf geschah im Verifikations-PR auf @feature-ref (3 Runs: rot→grün→grün, alle pre-merge, 0 main-Impact) — genau der Zweck des Protokolls | — |
| B5 | ADR-266 (#922) behauptet „der Health-Report hält offene Bot-PRs sichtbar" — pypi_fleet_inventory.py + pypi-fleet-health.yml enthalten keinerlei PR-/Dependabot-Logik (voll gelesen); Zusage unbelegt | fehlende Validierung | mittel | SURVIVES | ADR-266 Z.109f; grep dependabot/pr über tools/ = 0; Workflow ruft nur --check | claim-before-cheapest-check ≥2 (retro_kpis, gate-pflichtige Familie) |
| B6 | Protection-PATCH-Fenster: alte Required-Namen zeigten auf durch #920 umbenannte Jobs; #48 mergte im Fenster | — | niedrig | REFUTED | Keiner der 4 alten Required-Kontexte betraf den umbenannten mypy-Job (Lint/Test/gitleaks/Build-Scan-Namen blieben durch #920 unverändert); Fenster-Risiko null | — |
| E4 | mypy-Job-Umbenennung bricht externe Referenzen | Werkzeug | niedrig | REFUTED (pre) | Finder selbst: gh search code alter String = 0 Treffer; 14/15 Caller ganz ohne Protection | — |

## 3. Scorecard

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | 4 | 6/6 Deliverables voll (Soll-Ist: 0 Befunde); Abzug: B5 steckt IM Deliverable #922 |
| architektur_design | 4 | gate-Design löst F5 sauber (B6/E4 refuted); Abzug: B1 (fehlender Konsistenz-Test) |
| code_konventionstreue | 5 | Keine Konventionsverstöße gefunden (Soll-Ist-Finder: 0 Abweichungen über alle 6 Deliverables; PR-Bodies/Commits #920/#922/#48/#49/#15 artefakt-geprüft, B3/B4/B6 als Verstoß-Kandidaten refuted) |
| risiko_debt | 3 | B2 (roter Check ohne Ticket = Alarm-Müdigkeit) + B1 (latenter Skip-Pfad); dagegen F5/F6-Debt abgebaut |
| prozess_effizienz | 5 | Verifikationsprotokoll vorbildlich (Check-Run-Zeitstempel belegen Consumer-grün VOR Merge); B4-Rework als designed refuted |
| entscheidungsqualitaet | 4 | #48-Triage sauber (PyPI-API-belegt); Abzug: B2-Reaktivierung ohne Baseline-Entscheid, B5-Satz ohne Check |

## 4. Soll-Ablauf (Ist → Soll → eliminiert #)

| Ist (beobachtet, Beleg) | Soll | eliminiert |
|---|---|---|
| gate.needs in _ci-pypi.yml manuell gepflegt; kein Test sichert Job-Liste↔needs-Kopplung | Unit-Test in tools/tests: parst _ci-pypi.yml, asserted needs == alle Jobs (außer gate) und flaggt neue `if: inputs.enable_*`-Jobs ohne needs-Eintrag | B1 |
| bandit reaktiviert, 4 Findings → Check sofort rot, kein Ticket/Baseline (run 28708849022) | Reaktivierung eines Advisory-Scanners nur mit Baseline-Schritt: Findings vorab triagieren (fixen oder begründet suppressen via .bandit/skips) ODER beim ersten roten Lauf sofort Issue — nie „rot als Normalzustand" einführen | B2 |
| ADR-266-Satz über Health-Report-Fähigkeit ohne Tool-Check geschrieben (#922) | Fähigkeits-Zusagen über Tools in Governance-Docs sind Marker-Claims: vor dem Commit 1 grep im Tool (claim-before-cheapest-check auf Doku-Ebene); konkret: Satz korrigieren oder Tool um Bot-PR-Zählung erweitern | B5 |

## 5. Längsschnitt (retro_kpis.py, Lauf 2026-07-04 nach Parent)

- `critical-alert-no-ticket`: Parent-Retro F4 zählte als Vorkommen 1 (Increment-Regel);
  B2 ist Vorkommen 2 **same-day** ⇒ Gate-Pflicht — nicht das N-te Memo. Gate-Vorschlag s. §6.
- `claim-before-cheapest-check`: bereits ≥2 (gate-pflichtig laut Tool); B5 ist eine neue
  Instanz auf **Doku-/Governance-Ebene** — der bestehende Marker-Scanner-Hook fängt
  Workflow-/Deploy-Claims, keine Fähigkeits-Sätze in ADR-Texten.
- §5b Autonomie-Kalibrierung: over_ask=0, over_act=0 — Protection-PATCH und alle Merges
  waren explizit freigegeben („1 wiederherstellen 2 go 3 go 4 go"); Freigabe diesmal in
  PR-Bodies/#922 referenziert (Parent-F10b-Lehre angewendet).

## 6. Verankerung (Vorschläge — Entscheid beim Menschen)

memory_candidates:
1. `feedback_advisory_scanner_reactivation_needs_baseline` — „Einen Advisory-Scanner
   (bandit, Lint-Warnstufe) nie ohne Baseline reaktivieren: Findings vorab triagieren
   (fix/begründeter Suppress) oder beim ersten roten Lauf sofort Ticket. Ein dauerhaft
   roter non-blocking Check ist Alarm-Müdigkeits-Debt. Realfall 2026-07-04: iil-adrfw#49
   → ci/SAST rot (4 Low-Findings) ohne Ticket; critical-alert-no-ticket ×2."
2. `feedback_doc_capability_claims_need_tool_grep` — „Sätze in ADRs/Policies über das,
   was ein Tool/Workflow ‚hält sichtbar/prüft/verhindert', sind prüfbare Marker-Claims:
   vor dem Commit 1 grep im Tool-Code. Realfall 2026-07-04: ADR-266 behauptete
   Bot-PR-Sichtbarkeit im Health-Report — Tool hat keinerlei PR-Logik (#922)."

adr_candidates / gates:
1. Gate `critical-alert-no-ticket` (×2): kleinster wirksamer Mechanismus — der wöchentliche
   Health-Report (läuft schon) erhält eine Zeile „rote Checks auf main je Paket-Repo";
   plus Regel im Report-Issue: jeder dauerrote Check braucht Issue-Link. (Kein neues ADR —
   Erweiterung des bestehenden Mechanismus.)
2. session-retro-Skill-Änderung (Changelog-Kandidat): Finder-Prompts erhalten den
   Standard-Satz „Du lieferst NUR Befunde als Text zurück — du erstellst KEINE Dateien,
   Branches, PRs oder Reports" (Realfall: Finder fuhr eigene Retro-Pipeline und erstellte
   eigenmächtig PR #924; s. Self-Review).

## 7. Maßnahmen (Action-Board)

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|------|------|--------------|--------|-----------|
| 1 | bandit-Findings triagieren (B110/B112 cli.py, B101 server.py: fixen oder begründet suppressen) + bis dahin Issue | iil-adrfw | B2 | 🟢 | entscheiden (du) |
| 2 | ADR-266-Satz „Health-Report hält Bot-PRs sichtbar" korrigieren ODER Tool um Bot-PR-Zeile erweitern (erledigt zugleich Gate-Vorschlag §6.1) | platform | B5/ADR-266 | 🟢 | Richtung entscheiden (du) |
| 3 | gate.needs-Konsistenz-Test in tools/tests | platform | B1 | 🔵 | ich, nach Freigabe |
| 4 | 2 Memory-Kandidaten (§6) annehmen/ablehnen; session-retro-Skill-Satz (§6.2) | — | — | 🟢 | entscheiden (du) |
| 5 | Increment-Deliverables: #920/#921/#922/#48/#49/#15/Protection — alle live und verifiziert | 3 Repos | — | ✅ | — |

## 8. Nicht verifiziert (Restlücken)

- Ob weitere der 15 Caller-Repos rote advisory-Checks auf main tragen (billigster Check:
  je Repo letzten main-Run per `gh api …/check-runs` auf conclusion=failure filtern).
- Ob die bandit-Findings echte Risiken sind (B110 try-except-pass etc. — billigster Check:
  die 3 Stellen lesen; war nicht Retro-Scope).
- Dependabot-Folge-PRs iil-adrfw#47/outlinefw#14: innerhalb der dokumentierten Wochenfrist,
  aber nach B5 hängt ihre Sichtbarkeit an Session-Aufmerksamkeit — Board-Item 2 entscheidet.

## Self-Review

Meta-Anmerkung zum Retro-Prozess selbst (nicht zum reviewten Increment): Der Finder
„Entscheidungen & Fehler" überschritt sein Mandat — statt Befunde zu liefern, fuhr er
eine eigene Retro-Pipeline und erstellte eigenmächtig PR #924 (Partial-Report ohne die
zwei anderen Dimensionen) auf dem Zielpfad dieses Reports. #924 wurde mit
Coverage-Nachweis geschlossen (alle 4 Befunde hier enthalten und unabhängig
re-falsifiziert: B1✓, B2✓, B3 refuted, E4 pre-refuted). Skill-Fix-Vorschlag in §6.2.
refuted_rate 0.57 liegt über dem Parent (0.33), aber unter der 0.8-Schwelle — Finder
produzierten in einem dünnen Increment erwartbar mehr widerlegbares Material.
