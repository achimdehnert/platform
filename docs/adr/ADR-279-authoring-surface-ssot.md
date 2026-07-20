---
id: ADR-279
title: "SSoT der Autorenfläche: Vertrags-Payloads git-first, produziertes Artefakt DB-first — mit Import-Vorbedingung"
status: proposed
decision_date: 2026-07-20
deciders: [Achim Dehnert]
consulted: [Claude Code]
informed: [iilgmbh]
scope: platform
supersedes: []
related: [ADR-273, ADR-274, ADR-182, ADR-183, ADR-095, KONZ-platform-026]
tags: [ssot, authoring, writing-hub, artefakte, blueprint, datensouveraenitaet, import]
drift_check_paths:
  - "docs/konzepte/KONZ-platform-026-authoring-blueprint.md"
---

# ADR-279: SSoT der Autorenfläche

## Kontext

Der Authoring-Blueprint (KONZ-platform-026) beschreibt ein Mensch↔KI-Protokoll
**Propose → Decide → Serialize → Verify → Persist**: im Chat entsteht Inhalt, der über
verifizierte Verträge in die App zurückgespielt wird. Pilot 2 („Das Erwachen") ist
2026-07-19/20 end-to-end durchlaufen und hat den Zustand **gemessen**, nicht vermutet:

| Artefakt | liegt heute | in der App-DB |
|---|---|---|
| `metadata.yaml`, `band1_outline.yaml`, `autorenstil.yaml`, `systems.yaml` | git (`achimdehnert/manuskripte`) | teilweise materialisiert |
| Outline (30 Kapitel-Knoten) | — | ✅ `OutlineNode` inkl. `act`/`beat_phase`/`emotional_arc` |
| Prosa (Kap. 1–2) | git | ❌ **gar nicht** — es gibt keinen Import-Pfad für Prosa |
| Revisionen / Status / Freigabe | — | ❌ für `BookProject`-Kapitel nicht genutzt |

**ADR-273 Invariante 1** sagt: `writing-hub` „owns the produced artifact's lifecycle
(status, revisions, approval, export, archive)". Das ist eindeutig — für das **produzierte
Artefakt**. ADR-273 sagt aber **nichts** über die **Prä-Persist-Autorenfläche**: den Ort, an
dem der Mensch mit der KI schreibt, bevor irgendetwas importiert wird. Genau dort liegt heute
faktisch der gesamte Inhalt. Diese Lücke ist der Anlass dieses ADR.

Zweiter Anlass: Die Artefakte lagen bis 2026-07-20 unversioniert in einem Scratch-Verzeichnis
(`~/shared/books`, kein Repo, kein Backup). Die Sofortmaßnahme war ein privates Repo
`achimdehnert/manuskripte`. Dessen README hält ausdrücklich fest: **Sicherungskopie, nicht
Autorität** — die Autoritätsfrage ist genau dieser ADR.

## Decision Drivers

- **D1 — Wo wird real geschrieben?** Der Inhalt entsteht im Chat und landet als Datei. Jede
  Lösung, die so tut, als entstünde er in der App, beschreibt nicht die Realität.
- **D2 — ADR-273 nicht aushöhlen.** Lifecycle-Funktionen (Freigabe, Revisionen, Multi-Owner-
  Authz nach ADR-182, Revision-DAG nach ADR-183) brauchen einen eindeutigen Eigentümer.
- **D3 — Gemessene Import-Lücke.** Der Import ist heute **verlustbehaftet**: `_commit_metadata`
  schreibt nur `title`+`description` (#254), `_commit_outline` verwirft `act`/POV/`emotional_arc`
  (WH-7 an #254), und für **Prosa existiert überhaupt kein Import**. Der Persist von Pilot 2
  musste deshalb am Import vorbei direkt über das ORM laufen.
- **D4 — Keine zweite Wahrheit.** Zwei beschreibbare Kopien desselben Kapitels ohne definierte
  Richtung erzeugen genau die Drift, die dieses ADR verhindern soll.
- **D5 — Datensouveränität.** Der Blueprint soll auf `risk-hub` (Ex-Schutz-Dokumente) und
  `ausschreibungs-hub` übertragbar sein. Dort sind Artefakte **Kundendaten**, teils
  öffentlich-rechtlich (`ttz-lif`, `meiki-lra`) — ein allgemeines git-Repo ist dort keine Option.

## Optionen

### O1 — DB-first (ADR-273 wörtlich)
App-DB ist SSoT für Prosa **und** Verträge; git ist reiner Export/Backup.
*Pro:* maximal ADR-273-treu; Lifecycle-Infrastruktur existiert bereits.
*Contra:* widerspricht D1; **setzt einen verlustfreien Import voraus, den es nicht gibt** (D3);
kein brauchbares Review-/Diff-Erlebnis für Langprosa; Offline-Arbeit entfällt.

### O2 — Git-first
Repo ist SSoT für Verträge **und** Prosa; die DB ist eine materialisierte Projektion.
*Pro:* entspricht D1; Historie/Diff/Branch/Review gratis; überlebt App-Ausfälle.
*Contra:* höhlt ADR-273 Invariante 1 aus — wem gehört dann „freigegeben"? Multi-Owner-Authz
(ADR-182) auf einer Projektion ist bedeutungslos; bricht D5 für Hub-Artefakte.

### O3 — Aufteilung nach Artefakt-Klasse (**empfohlen**)
- **Eingaben** (`_blueprint/*.yaml`: metadata, outline, autorenstil, systems) → **git ist SSoT**.
  Sie verhalten sich wie Quellcode: von Hand/KI erzeugt, versioniert, reviewbar, in die App
  *hineinkompiliert*.
- **Produziertes Artefakt + Lifecycle** (Prosa-Revisionen, Status, Freigabe, Export) →
  **DB ist SSoT**, wie ADR-273 Invariante 1 es verlangt.
- Das Manuskript-Repo hält einen **als nicht-autoritativ markierten Export** der Prosa
  (Backup/Diff), keinen zweiten Schreibpfad.

*Pro:* respektiert D1 (Eingaben entstehen außerhalb) **und** D2 (Lifecycle bleibt in der App);
klare Compile-Analogie; keine zweite Wahrheit, weil die Richtung je Klasse eindeutig ist.
*Contra:* verlangt, dass Prosa überhaupt erst importierbar wird (D3) — bis dahin ist O3 nur
teilweise wirksam; und die Grenze „Eingabe vs. Erzeugnis" muss je Artefakt sauber gezogen werden.

## Decision Outcome

**Gewählt: O3 — Aufteilung nach Artefakt-Klasse**, mit einer expliziten **Vorbedingung**:

1. **Eingabe-Verträge sind git-SSoT.** `_blueprint/*.yaml` werden im Manuskript-Repo (bzw. beim
   jeweiligen Fach-Hub) versioniert. Die App importiert sie; sie schreibt sie nicht zurück.
2. **Das produzierte Artefakt ist DB-SSoT** — Prosa-Revisionen, Status, Freigabe, Export bleiben
   bei `writing-hub` (ADR-273 Invariante 1 unverändert gültig).
3. **Vorbedingung (blockierend für Punkt 2):** Solange der Import verlustbehaftet ist und für
   Prosa gar nicht existiert (#254, WH-7, #268), **kann** die DB ihre SSoT-Rolle für Prosa nicht
   ausüben. Bis dahin gilt der git-Stand übergangsweise als Arbeitsautorität, **ausdrücklich als
   Übergang markiert**, nicht als Dauerzustand.
4. **Hub-gebundene Artefakte sind ausgenommen.** Feldgebundene Dokumente (ADR-274) —
   Ex-Schutz, Ausschreibung, Gutachten — folgen ihrem Fach-Hub und dessen Datenregime. Für sie
   gilt Punkt 1 **nicht** in Form eines allgemeinen git-Repos (D5).

## Konsequenzen

**Positiv:** Die Richtung ist je Artefakt-Klasse eindeutig; ADR-273 bleibt intakt; der reale
Schreibort wird nicht wegdefiniert; die Übertragung auf Fach-Hubs ist vorgezeichnet.

**Negativ / Kosten:** Punkt 2 ist erst nach dem Import-Fix wirksam — das ADR beschreibt bis
dahin einen Zielzustand, keinen Ist-Zustand. Das ist bewusst so benannt statt kaschiert.

**Folgearbeit:** #254 (+WH-7) verlustfrei machen; einen Prosa-Import-Pfad definieren
(`Chapter.content` + Revision); #268 (Längen-Gate deckt nur 1 von 2 Schreibpfaden) schließen.

## Kill-Gate

Wenn bis **2026-10-31** kein verlustfreier Import für Verträge **und** kein Prosa-Import-Pfad
existiert, ist O3 praktisch nicht erreichbar → dann bewusst auf **O2 (git-first)** umstellen und
ADR-273 Invariante 1 für Buch-Artefakte einschränken, statt einen Zielzustand weiter zu behaupten,
den die Implementierung nicht trägt. Exception-Budget: eine Verlängerung bis 2026-12-31.

| Kriterium | Status | Beleg |
|---|---|---|
| #254 + WH-7 verlustfrei | offen | — |
| Prosa-Import-Pfad existiert | offen | — |
| #268 geschlossen (beide Schreibpfade) | offen | — |
| Übergangs-Markierung im Manuskript-Repo gesetzt | ✅ | README „Sicherungskopie, nicht Autorität" |

## Offene Fragen für die externe Review

1. Ist die Grenze „Eingabe vs. Erzeugnis" tragfähig, oder franst sie aus (ein Outline ist
   Eingabe *und* Teil des Erzeugnisses)?
2. Ist die Vorbedingung (Punkt 3) ehrlich — oder ein getarntes „wir entscheiden später"?
3. Skaliert O3 auf feldgebundene Hub-Artefakte, oder braucht es dort ein eigenes ADR?
