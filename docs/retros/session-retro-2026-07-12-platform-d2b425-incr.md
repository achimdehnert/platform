---
retro_schema: 1
date: 2026-07-12
repo_scope: [platform]
session_id: d2b425-incr
footprint: full
findings_total: 5
findings_survived: 2
refuted_rate: 0.60
phase3_refuted: 0
pre_refuted: 3
scores:
  zielerreichung: 5
  architektur_design: 4
  code_konventionstreue: 4
  risiko_debt: 4
  prozess_effizienz: 3
  entscheidungsqualitaet: 5
gate_candidates: [stale-local-clone-as-ground-truth]
recurring_findings: [stale-local-clone-as-ground-truth, tracking-doc-stale-after-new-occurrence]
over_ask: 0
over_act: 0
footprint_reduction_reason: "full-Minimum (Increment mit Gate-3-Schritt: Ruleset-Bypass Episode 3), aber minimale Dichte (3 saubere/freigegebene/reversible Artefakte) → 1 kombinierter Finder statt 3 separater (alle 3 Dimensionen im engen Increment-Scope), 1 Skeptiker, Meta; Richter≠Angeklagter + Falsifikation gewahrt"
---

# Increment-Retro 2026-07-12 — platform (d2b425-incr)

Anchor auf das Abarbeiten der d2b425-Retro-Action-Items (nach ~18:20 UTC): Retro-Report #1109
via Ruleset-Bypass Episode 3 gemergt + Bypass-Audit-Kommentar, 3 memory_candidates verankert.
Increment-Regel: nur die neuen Artefakte in-scope, d2b425-Report-INHALT nicht re-litigiert.
Methode: Collector (haiku) + 1 Finder (sonnet, alle Dim im engen Scope) + 1 Skeptiker (sonnet,
`git fetch origin`-Pflicht) + Meta. Nur SURVIVES.

## 1. Executive Summary

- **Die frisch verankerte Bypass-Audit-Lektion (d2b425-Befund 3) wurde bei ihrer allerersten
  Anwendung sofort korrekt umgesetzt** — Episode 3 (#1109-Merge) trägt das durable Audit-Artefakt
  (Aktion/Fenster/Freigabe/Restore-Diff). Geschlossener Loop im selben Zug.
- **Überwiegend sauberes Abarbeiten:** 3 von 5 Finder-Punkten sind Gegenbeweise (Lektion angewandt,
  Memory schema-valide + nicht-duplizierend, keine neuen Fehler durch Merge/Memory).
- **Ironischster Survivor (I-4, mittel): die `stale-local-clone`-Falle schlug bei der Retro-KPI-
  Erzeugung selbst zu** — der Collector-`retro_kpis.py`-Lauf zeigte `×16` (lokaler Klon 1 Commit
  hinter origin/main, ohne die gemergte d2b425-Datei); korrekt ist `×17` auf origin/main. Das
  Muster trifft nicht nur Fleet-Aussagen, sondern das eigene Retro-Tooling.
- **Kleiner Survivor (I-2, niedrig-mittel): KONZ-019-Text nennt „heute 2×" Bypass**, Episode 3
  (19:26, nach PR-Erstellung 15:32) ist im Dokument nicht nachgeführt — das Tracking-Artefakt
  bestätigt seine eigene Maintainer-2028-Prognose real, ohne sie zu aktualisieren.
- **Autonomie sauber:** over_ask=over_act=0; Bypass Episode 3 nach wörtlicher Freigabe + auditiert.

## 2. Befund-Tabelle (nur SURVIVES)

| # | Befund | Kategorie | Severity | Verdikt | Beleg | Recurrence |
|---|---|---|---|---|---|---|
| I-2 | KONZ-019 (#1104 OPEN) benennt Bypass-Eskalation mit „heute 2×", Episode 3 (19:26) nicht nachgeführt — Tracking-Doc bestätigt seine eigene Prognose real, ohne sie zu aktualisieren | Tracking-Frische | niedrig-mittel | SURVIVES | rulesets/17621471/history 3 Episoden (09:17/12:19/19:26); #1104-Diff Z.272 „heute 2×" | `tracking-doc-stale-after-new-occurrence` (neu ×1) |
| I-4 | `stale-local-clone`-Falle bei der Retro-KPI-Erzeugung: Collector-Lauf zeigte `×16` (lokaler platform-Klon auf 536e14e, 1 hinter origin/main 07e840b, ohne d2b425-Datei); korrekt `×17` | Stale-Clone/Prozess | mittel | SURVIVES | `git log HEAD..origin/main` = 1 Commit; origin/main `recurring_findings:`-Feld-Zählung = 17 inkl. d2b425 | `stale-local-clone-as-ground-truth` (≥2, gate) |

**Gegenbeweise (pre_refuted, kein Fehler):** I-1 — Episode-3-Bypass trägt das durable Audit-
Artefakt (Befund-3-Lektion angewandt; „wörtliche Freigabe"-Zitat ohne Transkript nur als Hypothese
markiert). · I-3 — 3 Memory-Dateien schema-valide, `ci_replace` echt ERWEITERT (kein Duplikat),
🌀-Flags korrekt, 3 Index-Zeilen. · I-5 — keine neuen Fehler durch Merge/Memory; CI grün auf
07e840b; 36 Worktrees sind Altlast (0 „missing"), nicht increment-verursacht.

## 3. Scorecard (1–5, anker-basiert)

| Dimension | Score | Anker |
|---|---|---|
| zielerreichung | **5** | alle Action-Items abgearbeitet (Report gemergt, 3 Memory verankert, Lektion sofort angewandt) — vorbildlich |
| architektur_design | **4** | Memory-Struktur sauber (erweitern statt duplizieren, I-3); keine Architektur-Arbeit im Increment |
| code_konventionstreue | **4** | Memory-Schema + Bypass-Protokoll korrekt; kleiner Mangel: kein `git pull` vor KPI-Lauf (I-4) |
| risiko_debt | **4** | alles getrackt, Bypass mit Audit; Rest: KONZ-019-Tracking stale (I-2) |
| prozess_effizienz | **3** | Right-Sizing korrekt, aber I-4 (stale-clone im eigenen Tooling) + I-2 (Tracking-Frische) = 2 vermeidbare Prozesslücken |
| entscheidungsqualitaet | **5** | schlanker full statt Voll-Apparat (Dichte-Regel), Lektion sofort umgesetzt, ehrliche Gegenbeweise statt erfundene Befunde |

## 4. Soll-Ablauf (Ist → Soll; |Soll| == 2 Survivors)

| Ist (beobachtet, mit Beleg) | Soll (besserer Schritt) | eliminiert |
|---|---|---|
| KONZ-019 sagt „heute 2×", Episode 3 (nach PR-Erstellung) nirgends nachgetragen | Bei jeder neuen Occurrence eines in einem OFFENEN Konzept getrackten Risikos: Konzept/PR im selben Turn nachführen (Kommentar ODER Doc-Edit) | #I-2 |
| Collector lief `retro_kpis.py` gegen stale lokalen Klon → `×16` statt `×17` | Vor jedem Fleet-/KPI-Lauf `git -C ~/github/platform pull` ODER gegen `origin/main` zählen (`git show origin/main:...`), nie gegen den lokalen Checkout | #I-4 |

## 5. Längsschnitt (retro_kpis.py — maschinell, origin/main-Korpus)

`stale-local-clone-as-ground-truth` ist bereits ≥2 = gate-pflichtig; **Increment-Regel: dieser Slug
war schon im Parent d2b425 (Vorkommen-1, KONZ-018-Erdung), jetzt im Increment I-4 erneut (Vorkommen-2)
⇒ bestätigt gate-pflichtig, same-day.** Die Verschärfung: das Muster trifft nicht nur Fleet-
Aussagen, sondern das Retro-Tooling selbst — starkes Argument, es als echtes Gate zu verankern
(z.B. `retro_kpis.py`/Fleet-KPI-Skripte erzwingen intern `git fetch` + Zählung gegen `origin/<branch>`),
nicht als N-tes Memo. `tracking-doc-stale-after-new-occurrence` ist neu (×1, Beobachtung).

## 5b. Autonomie-Kalibrierung

- **over_ask = 0:** #1109-Merge korrekt als Gate 3 (Ruleset-Bypass) vorgelegt.
- **over_act = 0:** Bypass Episode 3 nach wörtlicher Freigabe („go ruleset-bypass für #1109") +
  auditiert + reversibel (Restore-Diff byte-gleich).
- **Meta zur Bypass-Frequenz (3×/Tag):** kein over_act (jede Episode freigegeben), aber I-2 belegt
  die Maintainer-2028-Prognose empirisch — die strukturelle Auflösung (KONZ-019 B1/SA-Policy) ist
  noch nicht wirksam; die Autonomie-Grenze bleibt bis dahin über Einzel-Freigaben gehalten.

## 6. Verankerung (kopierfertig — Mensch entscheidet)

**memory_candidates:**
```
name: fleet-kpi-scripts-fetch-before-count
type: feedback
drift: true
body: Vor jedem retro_kpis.py-/Fleet-KPI-/Längsschnitt-Lauf `git fetch`/`pull` ODER direkt gegen
  origin/<branch> zählen — nie gegen den lokalen Klon. Realfall 2026-07-12 (d2b425-incr I-4): der
  Retro-Collector zeigte claim-before-cheapest-check ×16, weil sein platform-Klon 1 Commit hinter
  origin/main stand (die gerade gemergte d2b425-Datei fehlte); korrekt ×17. Das gate-pflichtige
  Muster [[stale-local-clone-as-ground-truth]] trifft auch das Retro-Tooling selbst. Härtung:
  retro_kpis.py könnte intern `git fetch` + Zählung gegen origin erzwingen.
```

**adr_candidates:** keiner — Increment-Scope, kein Architektur-Thema.

## 7. Maßnahmen (Action-Board)

**🔵 Offen — ich kann sofort**
1. KONZ-019-Doc auf „3 Bypass-Episoden" nachführen (falls #1104 noch offen editierbar) — https://github.com/achimdehnert/platform/pull/1104

**🟢 Offen — dein Zug**
2. `stale-local-clone` als echtes Gate: `retro_kpis.py` internes `git fetch`+origin-Zählung — https://github.com/achimdehnert/platform/issues/1108 (verwandt) / neues Tooling-Issue
3. KONZ-019 B1/SA-Policy wirksam machen (löst die Bypass-Frequenz strukturell) — https://github.com/achimdehnert/platform/pull/1104

**✅ Erledigt (Increment, verifiziert)**
4. Bypass-Audit-Artefakt bei Episode 3 (Lektion angewandt) — https://github.com/achimdehnert/platform/pull/1109
5. 3 memory_candidates verankert — file:///home/devuser/.claude/projects/-home-devuser-github-platform/memory/

## 8. Nicht verifiziert (Restlücken)

- **„Wörtliche Freigabe"-Zitat im Bypass-Audit-Kommentar (I-1):** ohne Transkript-Zugriff nicht
  unabhängig prüfbar — als Hypothese geführt, nicht als bewiesen. Billigster Check: Session-Transkript
  gegen den Kommentar-Wortlaut halten.
- **36 Worktrees:** als Altlast klassifiziert (0 „missing"), nicht increment-verursacht — die
  genaue Attribution je Worktree (welche Session) wurde nicht gezogen. Billigster Check:
  `worktree-reaper.py --apply` (dry-run) listet gemergte/reap-bare auf.
