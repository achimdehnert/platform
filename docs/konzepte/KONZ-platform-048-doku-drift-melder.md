---
concept_id: KONZ-platform-048
title: "Doku-Drift-Melder — pruefbare Marker gegen die Wirklichkeit pruefen"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: "kein ADR — Melder-Werkzeug nach bestehendem Muster (Befund-Journal-Familie), keine Architekturentscheidung"
review_by: 2026-11-19
kill_criteria: >
  Ueber drei Laeufe liegt der Falsch-Positiv-Anteil ueber 50 Prozent (die
  hygiene_melder-Klasse aus #2054), oder die Ausnahmeliste waechst schneller
  als die Befundliste — dann prueft der Melder die Schreibweise statt der
  Sache und wird abgeschaltet statt nachgepflegt.
---

# KONZ-platform-048: Doku-Drift-Melder

**Status:** Entwurf · **Datum:** 2026-08-19 · **Anlass:** LLM-Readiness-Audit
ueber illustration-hub, music-lab, writing-hub · **Groesse:** T2

## Das Problem in einer Zahl

Ein einziges Audit ueber drei Repos fand am 2026-08-19 **sechs verifizierte
Drift-Faelle** in Meta-Dateien — jede einzelne eine Falle fuer das naechste
aufsetzende LLM:

| Datei | behauptet | wirklich |
|---|---|---|
| illustration-hub `NEXT.md` | Issue #272 offen, „entscheiden" | #272 CLOSED (am selben Tag) |
| illustration-hub `catalog-info.yaml` | Port 8092 | 8096 (compose, facts, reflex) |
| writing-hub `README.md` | Prod-Port 8095 | 8097 (compose.prod:18) |
| writing-hub `.env.example` | `manage.py init_llm_config` | Command existiert nicht |
| writing-hub `project-facts.md` | Stand 2026-06-15 | 2 Monate stale (skip-existing) |
| writing-hub `docs/adr/INDEX.md` | „Basis: ADR-150–202" | Tabelle endet bei 188 |

Keiner dieser Fehler wurde je *geschrieben* — sie sind alle *wahr gewesen*
und dann von der Wirklichkeit ueberholt worden, ohne dass es jemand merkte.

## Der Kernsatz

> Doku, die auf einen **pruefbaren Marker** zeigt (Issue-Nummer, Port,
> Command, Pfad), wird gegen den **Marker** geprueft — nicht gegen ihr Alter.

Die bestehende Staleness-Pruefung (`NEXT.md`: „stale nach 14 Tagen") ist
zeitbasiert und hat genau deshalb versagt: die Datei war 1 Tag alt und
trotzdem falsch. Wahrheitsbasiert heisst: der Melder fragt die Quelle.

## Warum ein starkes LLM das nicht selbst kompensiert

Die Audit-Erfahrung zeigt das Gegenteil einer Kompensation: je **spezifischer**
eine Angabe (eine Portnummer, eine Issue-Referenz), desto eher vertraut ihr
ein Modell ohne Gegenprobe — die spezifischste Angabe ist aber genau die, die
driftet. Einzelfixes (Paket A dieser Session) heilen sechs Symptome; die
Klasse heilt nur ein Melder.

## Mechanik (Minimalschnitt)

Ein Skript `tools/doku_drift_melder.py`, nightly je Repo (oder im
session-start-Runner als 0.7.x-Phase), prueft ausschliesslich **vier
maschinenlesbare Marker-Klassen** — bewusst keinen Freitext:

1. **Issue-/PR-Referenzen** in `NEXT.md` und im obersten Prio-Block von
   `AGENT_HANDOVER.md`: `#N` bzw. `owner/repo#N` → `gh issue/pr view --json
   state`. Befund nur, wenn die Referenz als **offen/zu tun** formuliert ist
   (Prio-Zeile, Checkbox), nicht bei historischem Zitat — die Unterscheidung
   ist die Lehre aus #2054/0.7.4: „Diskrepanz" melden, wo ein Text Erledigtes
   als Kontext zitiert, ist die invertierte Anzeige.
2. **Ports** in `catalog-info.yaml`, `project-facts.md`, `README.md` gegen
   die eine Quelle `registry/canonical.yaml` (SSoT seit ADR-234).
3. **Referenzierte Commands** (`manage.py <cmd>`, `make <target>`) →
   existiert das Target im Repo?
4. **Referenzierte Pfade** (Datei-Links in CLAUDE.md/CORE_CONTEXT/NEXT) →
   existiert die Datei?

Ausgabe: eine Zeile je Befund ins bestehende Befund-Journal
(`tools/befund_journal.py`-Familie) — mit Alter, wie dort ueblich. Kein
Auto-Fix, kein Issue-Spam: Issues erst ab dem dritten Lauf mit demselben
Befund.

## Right-Sizing und Reihenfolge

1. **Bestandsaufnahme vor Gate** (Hausregel „neues Gate braucht
   Bestandsaufnahme"): erster Lauf fleet-weit im reinen Zaehl-Modus —
   wie viele Befunde je Klasse, wie viele davon Falsch-Positive (Stichprobe
   von Hand). Erst danach entscheiden, welche Klassen scharf werden.
2. **SUGGEST-only** solange keine Baseline steht (Scanner-Disziplin).
3. Kein neuer Parser fuer Freitext-Behauptungen („ist deployed", „laeuft") —
   das ist der Verhaltens-Melder-Strang (KONZ-049 / #2058), nicht dieser.

## Abgrenzung

- **Nicht** dieses Konzept: project-facts-Regeneration reparieren
  (gen_project_facts „skip existing" — eigener kleiner Fix am Generator).
- **Nicht** dieses Konzept: hygiene_melder-Fix #2054 (invertierte Anzeige) —
  aber dieselbe Lehre gilt hier als Bau-Anforderung Nr. 1.

## Offene Fragen an den Owner

1. Nightly zentral (platform-Cron ueber alle Repos) oder je Repo im
   session-start-Runner? (Vorschlag: zentral — ein Leser, ein Journal.)
2. Gehoert Marker-Klasse 1 (Issue-Refs) sofort dazu, obwohl sie die
   fehleranfaelligste ist (Zitat vs. Prio)? (Vorschlag: ja, aber nur fuer
   `NEXT.md`-Zeilen mit Nummerierungs-/Checkbox-Praefix.)
