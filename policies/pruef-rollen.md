# Policy: Prüf-Rollen bei Bedarf (DB · Domain · UX)
<!-- rule_class: B | assessed_with: claude-opus-5 | reassess_by: 2027-03-31 (KONZ-038 D4) -->

**Trigger words:** prüf-rolle, prüf-rollen, db-prüfer, domain-prüfer, ux-prüfer,
db-experte, domain-experte, ux-experte, fachexperte, migration, migrationen

## Rule (Owner-Entscheid 2026-09-29)

Große Aufgaben bekommen **kein festes Rollen-Team**. Die Hauptsitzung baut
(sie IST der Developer). Eine Prüf-Rolle wird **nur gerufen, wenn ihr
Auslöser im Diff steht** — dann aber Pflicht, nicht Kür. Eine Rolle ist
kein neuer Agent, sondern ein Brief-Baustein für einen Subagenten:

- **Aufruf:** Agent-Tool, `subagent_type: Plan` (kein Edit/Write im
  Werkzeugsatz → read-only per Werkzeug, nicht per Bitte), **Modell Sonnet**
  (`session-routing.md`). Brief = Rollen-Block unten + konkretes Material
  (Diff, Dateipfade, Screenshots). Frischer Kontext ist der Zweck: der
  Prüfer hat den Code nicht geschrieben.
- **Ausgabe jeder Rolle:** Befundliste, je Befund `Severity · Beleg
  (Datei:Zeile, DOM, Quelle) · Vorschlag`. Befund ohne Beleg wird verworfen.
  „Nichts gefunden" ist ein gültiges Ergebnis.
- **Die Rolle ändert nichts.** Umsetzen entscheidet die Hauptsitzung.
- **Nicht rufen:** ohne Auslöser, bei Tippfehlern, reinen Doku-Änderungen,
  oder zweimal für denselben Diff.

## Rollen

### DB-Prüfer

- **Auslöser:** neue/geänderte Migration, Model-Feld, Index, Constraint,
  Roh-SQL, Datenmigration.
- **Liest zwingend:** den Migrations-Diff, das betroffene Model, die
  vorherige Migration derselben App; Datenmenge der Tabelle, wenn ermittelbar
  (sonst als Lücke benennen).
- **Prüft:** Sperrdauer auf großen Tabellen (Feld mit Default, Index ohne
  `CONCURRENTLY`), Rückwärtskompatibilität zum laufenden Code (Spalte
  entfernt/umbenannt, während alter Code sie liest), Rückweg (`reverse`
  vorhanden oder bewusst irreversibel markiert), `NOT NULL` ohne Backfill,
  fehlender Index für neue Filter/FKs, Datenmigration im selben Schritt wie
  Schemaänderung, Mandanten-/Tenant-Filter bei Datenmigrationen.

### Domain-Prüfer

- **Auslöser:** Änderung an Fachlogik — Berechnung, Frist, Statusübergang,
  Rechtsbezug, Fachbegriff in UI oder Datenmodell.
- **Liest zwingend:** die Fachquelle (Vorschrift, Norm, Fachkonzept/KONZ,
  Kundenunterlage, Akzeptanzkriterium im Issue). Die Hauptsitzung gibt sie
  im Brief mit.
- **Abbruchregel:** Liegt keine Fachquelle vor, prüft die Rolle **nicht aus
  eigenem Wissen**, sondern gibt „keine Quelle — Frage an Owner: …" zurück.
  Erfundenes Fachwissen klingt überzeugend und ist genau der Schaden, den
  diese Rolle verhindern soll.
- **Prüft:** Stimmt die Umsetzung mit der Quelle überein (je Befund mit
  Fundstelle)? Grenzfälle der Quelle abgedeckt? Fachbegriffe wie in der
  Quelle?

### UX-Prüfer

- **Auslöser:** sichtbare UI-Änderung (Template, Klickdummy, Formular,
  Fehlermeldung); Pflichtschritt in `/kd-review`.
- **Liest zwingend:** Screenshots bzw. gerenderten DOM der betroffenen
  Seiten, Fakten aus Playwright (Coverage, Console), falls vorhanden.
- **Prüft gegen das Plattform-Design-System:** `ADR-048` (HTMX-Playbook:
  `hx-target`/`hx-swap`/`hx-indicator`, `data-testid`), `ADR-049`
  (Design-Token `--pui-*`), `ADR-040` (Frontend-Completeness), `ADR-251`
  (UX-Gate am KD) + Nielsen-Heuristik (Sichtbarkeit des Status, Konsistenz,
  Fehlervermeidung, Erkennbarkeit statt Erinnerung).
- **Ausgabe zusätzlich:** Backlog nach Severity × Aufwand; keine
  spekulativen „könnte schöner sein"-Punkte.

## Warum

Ein Persona-Satz („Du bist DB-Experte") allein ändert wenig. Wert entsteht
aus drei Dingen: anderem Material (Schema, Fachquelle, Design-System),
eigenen Prüfkriterien und unabhängigem Kontext (Richter ≠ Angeklagter).
Ein festes Team je Aufgabe würde Kontext mehrfach einlesen — laut
Kontingent-Messung vom 2026-09-24 (7 Tage) gehen 76 % in wiedergelesenen
Kontext. Deshalb:
auslöserbasiert, read-only, belegpflichtig.

## Changelog

- 2026-09-29: Initial. DB- und Domain-Prüfer neu; UX-Prüfer aus
  `/kd-review` Step 4 hierher gezogen (dort nur noch Verweis).
