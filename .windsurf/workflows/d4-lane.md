---
description: KONZ-038-D4-Klassifikation einer Repo-Memory-Lane — Gegenprüfung aller Dateien ohne rule_class, direkte Klassifikation von Regel-Dateien, Extraktion eingebetteter Regeln aus Statusdateien; idempotent, mit maschinenlesbarem Abschlussdatensatz
mode: write
---

# /d4-lane — D4-Klassifikation einer Memory-Lane

> **Wann:** Eine Repo-Memory-Lane soll auf den KONZ-038-D4-Stand gebracht werden
> (jede Regel trägt `rule_class` A/B/C; eingebettete Regeln sind extrahiert).
> **Wann NICHT:** Neuanlage einzelner Memories (normale Memory-Pflege), Policy-Dateien
> (`~/.claude/policies/` — dort steht die Klassifikation im Kopf-Kommentar und wird
> per platform-PR gepflegt), ADRs/KONZe (eigene Lifecycle-Werkzeuge).

**Warum es diesen Skill gibt:** Die platform-Gegenprüfung am 2026-08-07 (platform#1640)
falsifizierte die Annahme „ohne rule_class = Nicht-Regel": 56 von 97 unklassifizierten
Dateien trugen Regelgehalt, das häufigste Muster war die **eingebettete Regel** in einer
Statusdatei. Das Verfahren (Gegenprüfung → direkte Klassifikation → Extraktion mit
Rückverweis) ist repo-unabhängig; dieser Skill macht es je Lane wiederholbar.

## Verwendung

```
/d4-lane <repo-ordner>            # z.B. /d4-lane ~/github/writing-hub
/d4-lane <repo-ordner> --dry-run  # nur Bericht, keine Schreibzugriffe
```

## Referenzlauf (Aufsetzpunkt für spätere Läufe/Modelle)

Erstlauf platform 2026-08-07: [#1640-Kommentare vom 07.08.](https://github.com/achimdehnert/platform/issues/1640)
— Befund-Kommentar (56/97-Falsifikation, Kandidatenliste) und Nachtrag (29 direkt
klassifiziert, 151/219). Wer diesen Skill verbessert oder einen abgebrochenen Lauf
fortsetzt, liest ZUERST die dortigen `d4-lane-status`-Datensätze (Schema in Step 6).

## Step 0: Lane auflösen und verifizieren (keine Pfade raten)

1. Lane-Slug aus dem Repo-Ordner ableiten: absoluter Pfad, `/` → `-`.
   `~/github/writing-hub` → `~/.claude/projects/-home-devuser-github-writing-hub/memory/`.
   Sonderfall globale Lane: Argument `global` → `~/.claude/projects/-home-devuser/memory/`.
2. Existenz prüfen: Lane-Verzeichnis UND mindestens eine `*.md` darin. Fehlt beides →
   **sauber abbrechen** mit Meldung „Lane leer/nicht vorhanden" — kein Verzeichnis anlegen.
3. Org bestimmen (`git -C <repo-ordner> remote get-url origin`). Bei `meiki-lra`/`ttz-lif`:
   Gov-Regel unten beachten (Step 6).
4. Klassendefinition lesen: `~/github/platform/docs/konzepte/KONZ-platform-038*.md` §5.1.
   Ist platform lokal nicht vorhanden: `git show` über GitHub-API (`achimdehnert/platform`,
   main) — die Definition NIE aus dem Gedächtnis rekonstruieren.

**Klassen (Kurzform; §5.1 ist maßgeblich):** A = Modell-Schwäche-Kompensation
(sunset-fähig) · B = Org-Präferenz (bleibt) · C = Schutz vor irreversiblem/externem
Schaden — Prod, Publish, Secrets, Dritte (nie sunset). **Grenzfall A/C → immer C.**

## Step 1: Bestandsaufnahme (idempotent)

```bash
LANE=<aufgelöstes Verzeichnis>
gesamt=$(ls "$LANE"/*.md | grep -v MEMORY.md | wc -l)
offen=$(grep -rLl "rule_class" "$LANE"/*.md | grep -v MEMORY.md | wc -l)
```

`MEMORY.md` ist der Index, nie Prüfgegenstand. Bereits klassifizierte Dateien werden
**übersprungen** — ein Wiederaufruf nach Abbruch ist dadurch gefahrlos und setzt genau
dort auf, wo der letzte Lauf stand. `offen = 0` → direkt zu Step 6 (Bericht „nichts zu tun").

## Step 2: Gegenprüfung — JEDE offene Datei vollständig lesen

Je Datei genau eine der drei Entscheidungen, mit der gelesenen Datei als Beleg:

- **(a) Datei IST eine Regel** → Step 3 (direkte Klassifikation).
- **(b) Statusdatei MIT eingebetteter Regel** (Handlungsanweisung mitten im
  Projekt-/Referenzstand) → Step 4 (Extraktion).
- **(c) reine Nicht-Regel** (Status, Fakten, Handoff) → unangetastet lassen, zählen.

`metadata.type` ist ein Hinweis, **nicht** die Entscheidung. Im Zweifel (a)/(b), nie (c).
**Ab ~30 offenen Dateien:** Fan-out über Subagenten oder Workflow im Muster
**Entwurf → adversariale Verifikation** (Verifizierer liest die Trägerdatei selbst nach
und versucht den Entwurf zu verwerfen); Schreibzugriffe bleiben IMMER zentral bei der
Hauptsession. Einzel-Agent-Urteile ohne Verifikation gelten als PLAUSIBLE, nicht als Beleg.

## Step 3: Direkte Klassifikation (Fall a)

Frontmatter im `metadata:`-Block ergänzen (byte-genau dieses Schema):

```yaml
  rule_class: <A|B|C>
  assessed_with: <exakte Modell-ID dieser Session, z.B. claude-fable-5>
  reassess_by: <A: heute +4 Monate; B/C: heute +12 Monate>
```

Alt-Schema-Dateien (top-level `type:`, fehlende `description`) dabei auf das
Standard-Schema normalisieren — das ist Teil des Auftrags, kein Scope-Creep.

## Step 4: Extraktion eingebetteter Regeln (Fall b)

1. Neue Datei `feedback_<slug>.md` in derselben Lane — Namen vorher per
   Verzeichnis-Listing auf Kollision prüfen. Inhalt: Haus-Frontmatter (Step-3-Schema
   **plus** `extracted_from: <trägerdatei>`), Regeltext, `**Why:**`, `**How to apply:**`,
   Schlusszeile `Herkunft: eingebettet in [[<trägerdatei>]] (D4-Extraktion <datum>)`.
2. Der Regeltext muss **wörtlich aus der Trägerdatei belegbar** sein — nichts erfinden,
   nichts verallgemeinern, was die Datei nicht hergibt.
3. **Nur bei Klasse C:** im Träger den Regel-Absatz durch Halbsatz +
   `Regel → [[<neue-datei>]]` ersetzen (Suchstring byte-genau und eindeutig; droht
   Informationsverlust → Träger unverändert lassen und den Fall im Bericht nennen).
   Bei A/B bleibt der Träger unverändert (Rückverweis genügt).
4. Je neuer Datei eine Zeile im `MEMORY.md`-Index der Lane (Bestandsformat, 🌀 bei drift).

## Step 5: Selbstverifikation (vor dem Bericht)

```bash
grep -rc "rule_class" "$LANE"/*.md | grep -v ":0" | wc -l   # neuer Stand
python3 - <<'EOF'                                            # Schema-Vollständigkeit
# je Datei mit rule_class: assessed_with UND reassess_by vorhanden? Fehlt eins → FIX vor Bericht.
EOF
```

Zusätzlich stichprobenartig 3 extrahierte Dateien gegen ihre Träger lesen (Treue-Check).

## Step 6: Abschlussdatensatz (Maschinen-Vertrag)

Kommentar auf [platform#1640](https://github.com/achimdehnert/platform/issues/1640) mit
Prosa-Kurzfassung **und** diesem JSON-Block (eine Zeile, exakt diese Schlüssel — spätere
Läufe und Auswertungen parsen ihn):

```json
{"d4-lane-status": {"repo": "<repo>", "datum": "<YYYY-MM-DD>", "gesamt": 0, "vorher_klassifiziert": 0, "direkt": 0, "extrahiert": 0, "nichtregeln": 0, "uebersprungen_mit_grund": 0, "stand": "x/y", "assessed_with": "<modell-id>", "offene_faelle": ["<datei>: <grund>"]}}
```

**Gov-Regel (meiki-lra/ttz-lif):** In den platform-Kommentar gehören NUR Zahlen und
Dateinamen — keine Regeltexte, keine Inhalte. Inhaltliche Befunde bleiben als Issue im
Gov-Repo selbst (Gov-Funde bleiben im Gov-Repo).

## Verboten

- Klasse C nach A/B abschwächen (Korrektur nur Richtung C)
- Statusdateien pauschal als Regel etikettieren (Anti-Muster aus #1640)
- Secrets/Personendaten in neue Dateien oder Berichte übernehmen — Zeiger statt Wert
- Trägerdateien löschen oder umbenennen; Bulk-Edit ohne Einzellesen
- Bericht ohne vorherige Selbstverifikation (Step 5)

## Abschluss-Checkliste (PFLICHT — jede Zeile explizit abhaken)

- [ ] Step 0: Lane verifiziert, KONZ-038 §5.1 gelesen (nicht aus Gedächtnis)
- [ ] Step 1: `gesamt`/`offen` erhoben, MEMORY.md ausgenommen
- [ ] Step 2: n/n offene Dateien gelesen (n aus Step 1 = n im Bericht)
- [ ] Step 3/4: jede neue/geänderte Datei mit vollständigem Frontmatter-Schema
- [ ] Step 4.4: MEMORY.md-Zeile je extrahierter Datei
- [ ] Step 5: Selbstverifikation gelaufen, 3er-Stichprobe dokumentiert
- [ ] Step 6: #1640-Kommentar mit JSON-Datensatz abgesetzt (Gov-Regel beachtet)
- [ ] Bewusst Ausgelassenes im Datensatz unter `offene_faelle` getrackt
