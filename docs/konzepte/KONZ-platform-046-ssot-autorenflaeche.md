---
concept_id: KONZ-platform-046
title: "SSoT der Autorenflaeche — git-first Eingaben, DB-first Erzeugnis"
pipeline_status: idea
tier: T2
owner: "Achim Dehnert"
spec_refs: []
adr_threshold: >
  ADR-wuerdig, sobald entschieden — die Frage beruehrt eine bestehende
  SSoT-Entscheidung, wirkt cross-repo (writing-hub plus Fach-Hubs) und hat
  eine Datensouveraenitaets-Dimension. Dieses KONZ haelt sie bis dahin fest,
  ohne eine Ratifizierung zu behaupten, die es nie gab.
review_by: 2026-10-31
kill_criteria: >
  Existiert bis 2026-10-31 weder ein verlustfreier Vertrags-Import noch ein
  Prosa-Import-Pfad, ist die bevorzugte Aufteilung praktisch nicht erreichbar.
  Dann bewusst auf git-first umstellen und die bestehende SSoT-Entscheidung
  fuer Buch-Artefakte einschraenken, statt einen Zielzustand weiter zu
  behaupten, den die Implementierung nicht traegt.
---

# KONZ-platform-046: SSoT der Autorenflaeche

**Status:** Vorschlag · **Datum:** 2026-08-19 · **Groesse:** T2
**Anlass:** Fund beim Schleusen-Durchgang — eine entscheidungsreife
Architekturfrage lag zehn Monate lang ausserhalb jedes Repos und waere mit
der Schleusenfrist verfallen.

## Warum dieses Dokument existiert

Am 2026-07-20 entstand ein vollstaendiges Review-Briefing fuer eine
Architekturentscheidung: Titel, Kontext, fuenf Entscheidungstreiber, drei
Optionen mit Pro/Contra, ein gewaehltes Ergebnis samt blockierender
Vorbedingung, Konsequenzen und ein datiertes Kill-Gate. Es wurde fuer eine
externe Zweitmeinung nach `~/shared/` gelegt — und dort blieb es.

Drei Befunde dazu, alle am 2026-08-19 geprueft:

1. **Die Antwort kam nie zurueck.** Zu 24 Uebergaben in der Schleuse
   existieren 5 Antwortdateien. Diese gehoert nicht dazu.
2. **Der ADR, auf den der Dateiname zeigt, ist ein anderer.** Die Uebergabe
   heisst `adr-handoff-ADR-279-...`; unter `ADR-279` liegt im Repo seit
   2026-07-11 ein voellig anderes Thema (adaptiver Text-Feedback-Loop in
   `iil-promptfw`). Eine Nummer, zwei Gegenstaende.
3. **Der beschriebene ADR existiert nirgends.** Volltextsuche ueber
   `platform` und `writing-hub`: null Treffer. Er wurde nie angelegt.

Die Schleusenregel sagt fuer diese Klasse „gehoert an den ADR und nach
Outline". Beides ging nicht: es gibt keinen ADR, an den sie gehoert, und
keine Zweitmeinung, die zu uebertragen waere. Der Inhalt selbst ist
allerdings zu gut, um ihn mit der Frist wegzuraeumen — insbesondere, weil
sein Kill-Gate auf den **2026-10-31** datiert ist und damit noch laeuft.

## Die Frage

Ein Authoring-Protokoll (Propose → Decide → Serialize → Verify → Persist)
erzeugt Inhalt im Chat, der ueber gepruefte YAML-Vertraege in eine
Django-Anwendung zurueckgespielt wird. Eine bestehende Entscheidung legt
fest, dass die App den Lebenszyklus des **produzierten Artefakts** besitzt
(Status, Revisionen, Freigabe, Export, Archiv). Sie sagt nichts ueber die
**Prae-Persist-Autorenflaeche** — den Ort, an dem der Mensch mit der KI
schreibt, bevor irgendetwas importiert wird. Dort liegt heute faktisch der
gesamte Inhalt. Diese Luecke ist der Gegenstand.

Gemessener Ist-Zustand aus einem end-to-end durchlaufenen Pilotprojekt:

| Artefakt | liegt heute | in der App-DB |
|---|---|---|
| Vertrags-YAMLs | git | teilweise materialisiert |
| Outline (30 Knoten) | — | vollstaendig, inkl. Akt/POV/Bogen |
| Prosa | git | gar nicht — es gibt keinen Import-Pfad |
| Revisionen / Status / Freigabe | — | fuer Buch-Kapitel ungenutzt |

## Entscheidungstreiber

- **D1 — Wo wird real geschrieben?** Der Inhalt entsteht im Chat und landet
  als Datei. Eine Loesung, die so tut, als entstuende er in der App,
  beschreibt nicht die Realitaet.
- **D2 — Die bestehende SSoT-Entscheidung nicht aushoehlen.** Freigabe,
  Revisionen, Multi-Owner-Authz und Revision-DAG sind implementiert und
  brauchen einen eindeutigen Eigentuemer.
- **D3 — Gemessene Import-Luecke.** Der Import ist verlustbehaftet: der
  Metadaten-Pfad schreibt nur Titel und Beschreibung, der Outline-Pfad
  verwirft Akt/POV/emotionalen Bogen, fuer Prosa existiert kein Pfad. Der
  Pilot musste am Import vorbei direkt ueber das ORM persistieren.
- **D4 — Keine zweite Wahrheit.** Zwei beschreibbare Kopien desselben
  Kapitels ohne definierte Richtung erzeugen genau die Drift, die hier
  verhindert werden soll.
- **D5 — Datensouveraenitaet.** Der Ansatz soll auf Fach-Hubs uebertragbar
  sein. Dort sind Artefakte Kundendaten, teils oeffentlich-rechtlich — ein
  allgemeines git-Repo ist dort keine Option.

## Optionen

**O1 — DB-first.** App-DB ist SSoT fuer Prosa und Vertraege, git nur
Export/Backup. Treu zur bestehenden Entscheidung, aber im Widerspruch zu D1
und **setzt einen verlustfreien Import voraus, den es nicht gibt** (D3).
Kein brauchbares Diff-/Review-Erlebnis fuer Langprosa, keine Offline-Arbeit.

**O2 — Git-first.** Repo ist SSoT fuer Vertraege und Prosa, DB ist
materialisierte Projektion. Entspricht D1, liefert Historie/Diff/Branch
gratis, ueberlebt App-Ausfaelle. Hoehlt aber die bestehende Entscheidung aus
— wem gehoert dann „freigegeben"? Multi-Owner-Authz auf einer Projektion ist
bedeutungslos. Bricht D5 fuer Hub-Artefakte.

**O3 — Aufteilung nach Artefakt-Klasse (bevorzugt).** Eingaben
(Vertrags-YAMLs) sind git-SSoT; sie verhalten sich wie Quellcode und werden
in die App hineinkompiliert. Produziertes Artefakt und Lebenszyklus sind
DB-SSoT. Das Manuskript-Repo haelt einen ausdruecklich als nicht-autoritativ
markierten Export der Prosa.

## Vorgeschlagenes Ergebnis

**O3**, mit vier Festlegungen:

1. Eingabe-Vertraege sind git-SSoT. Die App importiert sie, sie schreibt sie
   nicht zurueck.
2. Das produzierte Artefakt ist DB-SSoT — Revisionen, Status, Freigabe,
   Export bleiben bei der App.
3. **Blockierende Vorbedingung fuer Punkt 2:** Solange der Import
   verlustbehaftet ist und fuer Prosa gar nicht existiert, kann die DB ihre
   SSoT-Rolle fuer Prosa nicht ausueben. Bis dahin gilt der git-Stand
   uebergangsweise als Arbeitsautoritaet, ausdruecklich als Uebergang
   markiert.
4. Feldgebundene Hub-Artefakte sind ausgenommen; sie folgen ihrem Fach-Hub
   und dessen Datenregime.

Punkt 2 ist damit erst nach dem Import-Fix wirksam. Das Dokument beschreibt
bis dahin einen Zielzustand, keinen Ist-Zustand — bewusst so benannt statt
kaschiert.

## Offene Fragen (waren der Grund fuer die Zweitmeinung)

1. Ist die Grenze **Eingabe vs. Erzeugnis** tragfaehig, oder franst sie aus?
   Ein Outline ist Eingabe *und* Teil des Erzeugnisses — und wird heute in
   beiden Welten gefuehrt.
2. Ist die blockierende Vorbedingung ehrlich, oder ein getarntes „wir
   entscheiden spaeter", das einen unklaren Zustand als Entscheidung verkauft?
3. Skaliert O3 auf feldgebundene Hub-Artefakte, oder braucht es dort ein
   eigenes ADR?

Diese drei Fragen sind **unbeantwortet**. Sie waren der Auftrag an die
externe Zweitmeinung, die nie zurueckkam.

## Naechster Schritt

Entweder die Zweitmeinung erneut einholen (die Uebergabe ist vollstaendig
und wiederverwendbar) oder ohne sie entscheiden und als ADR ratifizieren.
Beides vor dem 2026-10-31, sonst greift das Kill-Kriterium oben.

## Herkunft

Quelle: `~/shared/adr-handoff-ADR-279-2026-07-20.md` (Briefing vom
2026-07-20, ohne Antwortdatei). Werktitel und Repo-Namen waren dort bereits
anonymisiert; dieses Dokument uebernimmt das unveraendert — `platform` ist
ein oeffentliches Repo.
