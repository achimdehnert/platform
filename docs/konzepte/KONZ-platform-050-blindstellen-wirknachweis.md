---
concept_id: KONZ-platform-050
title: "Beweis der Wirkung statt gruener Haken — Blindstellen der Flotten-Detektoren"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: >
  Noch nicht ADR-wuerdig. Es aendert keine Architektur, sondern die Uebersetzung
  eines Melder-Ergebnisses in eine Statuszelle. ADR-wuerdig wird es erst, wenn
  daraus eine flottenweite Pflicht fuer alle Melder wird (dritter Statuswert,
  Wirknachweis-Pflicht je Automatismus) — dann beruehrt es ADR-233 und den
  Sitzungsstart als Ganzes.
review_by: 2026-10-15
kill_criteria: >
  Faengt der Blindstellen-Melder bis 2026-10-15 keinen Fall, den nicht ohnehin
  ein Mensch im selben Lauf gesehen haette, ist er selbst die Meta-Ebene, vor der
  der Advocatus Diabolus warnt — dann ersatzlos entfernen, nicht erweitern.
---

# KONZ-platform-050: Beweis der Wirkung statt gruener Haken

## Fakt

Am 2026-08-23 fielen in einer Sitzungsstunde sechs stille Ausfaelle an. Der
Sitzungsstart-Runner mit seinen 25 Phasen fing **drei** davon:

| # | Befund | Detektor | Ergebnis |
|---|---|---|---|
| F1 | platform-Haupt-Tree dirty, Sync-Loop blockiert | 0.2 platform-sync | ✅ gefangen (Ursache mehrdeutig) |
| F2 | Nachtlauf schrieb falsche Ausfall-Behauptung in ein durables Dokument | — | ❌ kein Detektor |
| F3 | Prio stand 19 Tage erledigt in der Liste | 0.7.4 prio-referenzen | ❌ **gruen gemeldet, blind** |
| F4 | verteilte Skill-Kopie 10 Tage veraltet | — | ❌ 0.7.5 deckt nur `tools/claude-hooks/` |
| F5 | coach-hub-Deploy 21 Laeufe rot | 0.7 + befund_journal | ✅ gefangen, mit Alter |
| F6 | 17 Wiederholungsbefunde nie gegated | 0.7.9 gate-deckung | ✅ gefangen |

F3 ist der Lehrfall. `handover_stale_reference_check.py` existiert genau fuer diese
Klasse — sein eigener Kommentar nennt den Anlass („am 2026-08-12 zeigte die
platform-Prio ZWEIMAL an einem Tag auf Ueberholtes"). Gegen das
`iil-klickdummy`-Handover meldete er `SKIP keine_prio_items`, waehrend die Datei
sieben Prio-Zeilen trug. Der Parser kennt nur nummerierte Listen (`^\d+\.\s`); die
Liste stand als Markdown-Tabelle da. Der Runner verbucht diesen SKIP als **PASS**.

## Analyse

Zwei getrennte Fehler, die sich gegenseitig verdecken:

**(1) Format-Blindheit.** Der Parser widerspricht seiner eigenen Dokumentation: er
beruft sich auf „das, was `handover_prio_mirror.sh` real spiegelt" — und der Hook
spiegelte die Tabellenzeilen an diesem Morgen nachweislich (Session-Start-Ausgabe).
Zwei Werkzeuge, ein Vertrag, zwei Parser.

**(2) SKIP wird als PASS verbucht.** Das ist der strukturelle Teil. „Konnte nicht
pruefen" und „geprueft, alles gut" landen in derselben gruenen Zelle. Ein Melder, der
nie lief, ist von einem, der sauber durchlief, nicht zu unterscheiden — und niemand
sucht nach einer Ursache fuer Gruen.

Das verallgemeinert: die Flotte misst durchgehend **Zustand**, nie **Wirkung**. Fuer
keinen Automatismus ist beantwortbar, wann er zuletzt bewiesen hat, dass er etwas
faengt. `gate_wirkung.py` misst das fuer Gates (8 von 20 rueckfaellig) — fuer die
Melder selbst gibt es kein Gegenstueck.

## Loesung

**Gebaut und real gelaufen (2026-08-23):** `tools/blindstellen.py` liest den Runner
und listet jeden `record`-Aufruf, der PASS meldet, obwohl seine eigene Notiz eine
Nicht-Pruefung beschreibt. Erster Lauf: **3 von 67** — `0.7.4` zweimal (Z.403, Z.408)
und `0.4.1 reflex` (Z.202, dort per Design). Das Werkzeug validiert sich selbst: parst
es null `record`-Aufrufe, ist das Exit 2, keine Erfolgsmeldung.

**Offen, in dieser Reihenfolge:**

1. Dritter Statuswert `SKIP` im Runner, eigene Spalte in der Summary — die Zelle darf
   nicht gruen sein, wenn nichts geprueft wurde.
2. `prio_items()` um Tabellenzeilen erweitern, mit Test gegen genau das
   `iil-klickdummy`-Handover, das heute durchrutschte.
3. Verteilungs-Drift der Skill-Kopien (F4) bekommt einen Melder oder faellt bewusst weg.

## Advocatus Diabolus

| Einwand | Antwort |
|---|---|
| 25 Phasen, 20 Gates — eine Meta-Ebene mehr ist die Krankheit | Traegt. Deshalb ein Lese-Werkzeug ohne Zustand, ohne Cron, ohne Gate — und ein Kill-Kriterium mit Datum. |
| Der Blindstellen-Melder kann selbst blind sein | Gemildert, nicht geloest: 0 geparste Aufrufe sind Exit 2. Gegen einen Parser, der die falschen Zeilen findet, hilft das nicht. |
| Die Detektoren fanden heute drei von sechs — ohne sie waere es schlechter | Richtig, und kein Argument gegen den Befund: F3 war **gruen**, nicht still. Ein falsches Gruen ist teurer als eine Luecke, weil es das Suchen beendet. |
| Regex auf Notiz-Text ist genau die Musterliste, an der `deferred-item-no-tracking-issue` 9x scheiterte | Traegt am staerksten. Der richtige Bau waere ein Statuswert an der Quelle (Loesung 1), nicht ein Muster am Text. Der Melder ist die Messung bis dahin, nicht der Fix. |

## Bezug

- Sitzung 2026-08-23 · [platform#2212](https://github.com/achimdehnert/platform/pull/2212) · [platform#2213](https://github.com/achimdehnert/platform/issues/2213)
- `tools/gate_wirkung.py` (Rueckfall je Gate) · `tools/gate_deckung.py` (nie gegatete Befunde)
- 🌀 `blind-gate-vs-red-test` · 🌀 `generator-output-through-own-gates` — dieselbe Klasse, andere Stelle
