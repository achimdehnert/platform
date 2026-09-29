---
retro_schema: 1
date: 2026-09-29
repo_scope: [platform]
session_id: 381fb9
footprint: lean
findings_total: 3
findings_survived: 2
refuted_rate: 0.33
phase3_refuted: 0
pre_refuted: 1
scores:
  zielerreichung: 4
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 3
  prozess_effizienz: 4
  entscheidungsqualitaet: 3
gate_candidates: [privater-inhalt-in-public-repo-artefakt]
recurring_findings: [claim-before-cheapest-check, gate-claim-before-cheapest-check-wirkungslos]
gates_caught: [main-tree-guard-recurring-incident, direct-gh-pr-merge-bypasses-sa-m, check-ohne-positivkontrolle]
over_ask_klassen: []
over_act_klassen: []
widerlegung: "n/a (lean)"
streichkandidaten: []
streich_begruendung: "Keiner, weil die Sitzung nur eine Policy berührte und alle drei feuernden Hooks einen realen Fehler verhinderten — kein Melder ohne Wirkung beobachtet."
footprint_reduction_reason: "1 PR (#3613), 1 Schreib-Repo, ein fremdes Repo nur gelesen; kein Prod-Schritt, keine Migration, kein ADR → lean, 0 Finder-/Skeptiker-Subagenten."
---

# Session-Retro 2026-09-29 — Prüf-Rollen DB · Domain · UX (#3613)

> Lean, Inline-Pass über zwei Dimensionen (Soll-Ist & Scope · Entscheidungen & Fehler).
> Kein frischer Richter — Regel-1-Restlücke in §8.

## 0. Wirkungsbilanz (Phase 0.0)

`gate_wirkung.py`: 8 Gates RUECKFAELLIG. Von dieser Sitzung berührt:

| Gate | Rückfälle seit Bau | Ursache | Konsequenz |
|---|---|---|---|
| claim-before-cheapest-check | 6 (+1 hier, #2) | Quelle: der Stop-Hook prüft Behauptungen in Turns ohne Tool-Lauf, sieht aber keine Datumsangabe, die aus einer Memory-Indexzeile falsch gelesen wurde | **nachschärfen** — Beleg an [#2666](https://github.com/achimdehnert/platform/issues/2666) (Zeitangaben) angehängt |
| check-ohne-positivkontrolle | 2 | Quelle abgedeckt: der Stop-Hook hat die 0-Treffer-Suche angemahnt, die Positivkontrolle wurde nachgeholt | kein neuer Rückfall — als `gates_caught` geführt |

Die übrigen 6 RUECKFAELLIG-Gates wurden nicht berührt; ihre Behandlung ist offen geblieben (§8).

## 1. Executive Summary
- Zielzustand vor Arbeitsbeginn vorgelegt und vom Owner akzeptiert; alle vier Akzeptanzkriterien geliefert und im Zielkontext belegt (Hook-Trigger, `/kd-review`-Kopie mit Drift 0, Probelauf).
- **Kern-Befund #1:** Der erste PR-Text im öffentlichen Repo enthielt Interna aus einem privaten Hub-Repo (Feldnamen, Pfad, Commit). Nach 5 Minuten bereinigt; die erste Fassung bleibt im Bearbeitungsverlauf.
- **#2:** Ein Datum im Chat aus einer Memory-Indexzeile falsch gelesen (geplante Messung als erfolgte gewertet), selbst entdeckt und gemeldet.
- Drei Hooks verhinderten reale Fehler: Branch-Wechsel im Haupt-Tree, direkter `gh pr merge`, leere PR-Body-Datei.
- Trigger-Rauschen der neuen Policy gemessen und unkritisch (7 von 4 085 echten Prompts treffen „Migration").

## 2. Befund-Tabelle

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| 1 | Interna eines privaten Repos im PR-Body eines öffentlichen Repos | fehlende Validierung | hoch | SURVIVES | #3613 `userContentEdits`: Erstfassung 08:14:47Z, Bereinigung 08:19:26Z; Scan danach 0 Treffer, Positivkontrolle 1 | Familie mit `pii-in-public-fixtures` (×1) und `kundenname-in-public-repo-artefakt` (×1) — drei Slugs, eine Klasse |
| 2 | Datum der Kontingent-Messung aus einer Memory-Indexzeile falsch abgeleitet (01.10. statt 24.09.) | fehlende Validierung | mittel | SURVIVES | Memory `project_kontingent_kontextdiaet.md` Zeile 11 („Messung 7 Tage", modified 2026-09-25) vs. erste Chat-Antwort | claim-before-cheapest-check ×97 → Gate rückfällig |
| 3 | Trigger „migration" bläht die Grundlast (Kontingent-Memory) | Werkzeug | niedrig | REFUTED (pre) | 7 von 4 085 Nutzer-Prompts treffen `\bmigration(en)?\b` | — |

5-Why #1: Akzeptanzkriterium „Probelauf an echter Migration" → echte Migrationen liegen in privaten Repos → Befunde mit Datei:Zeile wurden als Nachweis in den PR-Body übernommen → der Public-Hinweis in `CLAUDE.md` ist Lesestoff, kein Check vor `gh pr create` → kein Gate prüft PR-/Issue-Texte in platform auf Namen oder SHAs privater Repos.

## 3. Scorecard

| Dimension | Score | verankert an |
|---|---|---|
| zielerreichung | 4 | alle Kriterien belegt; #1 als Mangel am Nachweis |
| architektur_design | 4 | Rolle als Brief-Baustein statt Agent, read-only per Werkzeugsatz |
| code_konventionstreue | 4 | Worktree, Commit-Format, SA-M-Merge-Weg angemahnt (gates_caught) |
| risiko_debt | 3 | #1: Erstfassung bleibt im Bearbeitungsverlauf |
| prozess_effizienz | 4 | 5 Fehlerläufe, alle Hook-Stopps ohne Folgeschaden |
| entscheidungsqualitaet | 3 | #1 (Wahl des Nachweises), #2 (ungeprüftes Datum) |

## 4. Soll-Ablauf

| Ist (beobachtet, mit Beleg) | Soll (verbesserter Ablauf) | eliminiert |
|---|---|---|
| Probelauf-Befunde aus privatem Repo wörtlich in den PR-Body von #3613 | Nachweise aus privaten Repos im öffentlichen Repo nur abstrakt („privates Hub-Repo, 3 Befunde, 2 gegengeprüft"), Details im privaten Repo oder Chat; vor `gh pr create` in platform Body gegen Namen privater Repos scannen | #1 |
| Datum aus einer Memory-Indexzeile übernommen, ohne die Datei zu öffnen | Zeit- und Mengenangaben aus Memory nur nach Lesen der Datei nennen, sonst als Hypothese markieren | #2 |

## 5. Längsschnitt
`retro_kpis.py`: `claim-before-cheapest-check` ×97 und `gate-claim-before-cheapest-check-wirkungslos` ×3 → GATE-PFLICHT, beide schon als Gate bzw. Issue [#2666](https://github.com/achimdehnert/platform/issues/2666) verankert. Befund #1 ist das dritte Vorkommen einer Klasse unter drei verschiedenen Slugs, `retro_kpis.py` zählt deshalb nur ×1 je Slug. Gate-Kandidat `privater-inhalt-in-public-repo-artefakt` (Familien-Slug).

### 5a. Rückfall-Prüfung
`claim-before-cheapest-check` ist rückfällig. Entscheidung: **ausweiten** auf Zeitangaben, die aus Memory abgeleitet werden. Der Gate-Edit mit `revised` und `revision_note` läuft über #2666 und nicht in diesem Retro-PR. Das ist bis dahin ein Kandidat, kein Eintrag.

### 5b. Autonomie-Kalibrierung
over_ask 0: die Zielzustand-Frage war policy-pflichtig (substanziell, öffentliches Repo). over_act 0: Merge in einem Nicht-Deploy-Repo bei grüner CI ist durch autonomy-gates gedeckt. Gemergt hat am Ende ein anderes Konto, siehe §8.

## 6. Verankerung (Vorschläge, nicht geschrieben)

Memory-Kandidat (drift):
```markdown
---
name: feedback_privat_belege_nie_in_platform
description: Belege aus privaten Repos (Pfade, Feldnamen, SHAs) nie in platform-PR/Issue-Texte
metadata:
  type: feedback
  drift: true
  drift_episode: 2026-09-29-pruef-rollen-pr-body
---
Nachweise aus privaten Repos in platform nur abstrakt nennen.
**Why:** #3613, Erstfassung mit Interna eines privaten Repos; der Bearbeitungsverlauf bleibt öffentlich.
**How to apply:** vor `gh pr create/edit` und `gh issue create/comment` in platform Body auf private Repo-Namen und SHAs prüfen.
```
Gate-Kandidat: **kein neues Gate.** `tools/checks/mandantendaten_gate.py` ausweiten. Es läuft schon beim Push (Ausgabe „Mandantendaten (oeffentliches Repo)“), sieht aber nur Commits und keine PR- oder Issue-Texte. Die Ausweitung umfasst einen PreToolUse-Aufruf auf `gh pr|issue create|edit|comment` für `achimdehnert/platform` und die Prüfung auf private Repo-Namen sowie fremde SHAs.

## 7. Maßnahmen

| # | Item | Repo | PR/Issue/ADR | Status | Next Step |
|---|---|---|---|---|---|
| M1 | Mandantendaten-Gate auf PR-Texte | platform | — | 🟢 | Owner: Ausweitung freigeben |
| M2 | Zeitangaben-Ausweitung | platform | [#2666](https://github.com/achimdehnert/platform/issues/2666) | 🟢 | Beleg angehängt, Umsetzung dort |
| M3 | Erstfassung #3613 löschen | platform | [#3613](https://github.com/achimdehnert/platform/pull/3613) | 🟢 | Owner: Bearbeitungsverlauf entscheiden |
| M4 | Streichbahn | platform | — | ✅ | keiner, Grund im Frontmatter |

## 8. Nicht verifiziert (Restlücken)
- **Regel 1:** Lean-Inline-Pass ohne frischen Richter; beide SURVIVES sind unfalsifiziert. Billigster Check: ein Sonnet-Skeptiker auf #1 und #2 (~55k Tokens).
- Warum ein anderes Konto #3613 gemergt hat (08:19:08Z, vor dem eigenen SA-M-Versuch). Billigster Check: Workflow-Runs und Automerge-Konfiguration um diese Uhrzeit ansehen.
- 6 weitere RUECKFAELLIG-Gates aus 0.0 wurden nicht behandelt, weil diese Sitzung sie nicht berührt hat.
- Ob die Erstfassung des PR-Bodies schon indexiert oder gespiegelt wurde.

**Vierklang** — getan: Policy #3613 gemergt, Pin und Kopie aktualisiert, Probelauf, PR-Body bereinigt, Retro · angenommen: Merge durch das andere Konto ist legitim · nicht verifizierbar: Indexierung der Erstfassung · offen geblieben: M1–M3, 6 Gates aus 0.0.

## Widerlegung
n/a — Footprint `lean` (Phase 3b erst ab `full`). Abdeckung: keine.

## Streichbahn
Keiner, weil die Sitzung nur eine Policy berührte und alle drei feuernden Hooks einen realen Fehler verhinderten (Haupt-Tree-Wechsel, direkter Merge, leere Body-Datei). Ein Melder ohne Wirkung wurde nicht beobachtet.
