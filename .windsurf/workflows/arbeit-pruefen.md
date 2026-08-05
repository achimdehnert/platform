---
description: Eingereichte studentische Arbeit formal prüfen — mechanische Befunde per Werkzeug, jede Quelle gegen das Original, Antwort als Entwurf (kein Versand)
mode: write
---

# /arbeit-pruefen — Formalprüfung einer eingereichten Arbeit

> **Wann:** Eine Abschlussarbeit (Bachelor/Master) liegt vor der Abgabe vor und du willst
> eine belastbare **formale** Rückmeldung — Deckblatt, Verzeichnisse, Nummerierung,
> Abbildungsunterschriften, Belege und Literaturverzeichnis.
> **Wann NICHT:** Inhaltliche Begutachtung (Methodik, Ergebnisse, Note) — das bleibt
> Handarbeit und ist ausdrücklich **nicht** Gegenstand dieses Skills. Mail lesen ohne
> Prüfung → `/read-mail`. Antwort versenden → `/send-mail` (eigenes Versand-Gate).

**Warum es diesen Skill gibt:** Die Prüfung am 2026-08-05 (Masterarbeit, 127 Seiten) fand
13 Klassen formaler Mängel. Zwei Zahlen der ersten, rein manuellen Fassung waren **falsch**
— 17 statt 32 betroffene Abbildungen, 24 statt 26 Belege —, und zwei Befunde fehlten ganz
(ein Beleg ohne Verzeichniseintrag, eine Quelle mit zwei verschiedenen Jahren). Genau die
zählbaren Dinge macht jetzt das Werkzeug, damit die Aufmerksamkeit für das Urteil bleibt.

## Verwendung

```
/arbeit-pruefen <pfad-zur-datei.pdf>
/arbeit-pruefen --aus-mail <nachrichten-id>     # Anhang aus dem Mail-Bestand holen
```

## Step 0: Herkunft klären (keine Pfade hartkodieren)

- Datei liegt lokal → direkt weiter zu Step 1.
- Datei kam per Mail → Anhang aus dem **Mail-Bestand** holen (`mail_anhang --nachricht <id>
  --nach <verz>`), nicht per IMAP nachladen. Das Postfach ist die Quelle des Bestandes,
  nicht die Arbeitsfläche.
- Rollen/Konten kommen aus der Maschinen-Config (`~/.claude/mail-roles.json`,
  `~/.claude/mail-<konto>.env`) — **nie** Adressen oder Konten in den Skill schreiben.

## Step 1: Mechanische Prüfung (Werkzeug, nicht Prosa)

```bash
python3 tools/dokument_formalpruefung.py <datei.pdf>
python3 tools/dokument_formalpruefung.py <datei.pdf> --json   # für Weiterverarbeitung
```

Dreizehn Prüfungen (F01–F13): Ligaturverlust und Erzeugungsweg, Titel-Konsistenz, leere
Deckblatt-Felder, Verzeichnisse ohne Eintrag im Inhaltsverzeichnis, Nummerierungslücken und
-dubletten bei Tabellen und Abbildungen, Unterschriften die Dateinamen sind, leere
Pflichtabschnitte, fehlende Standardteile, Belegdichte je Kapitel, Verzeichnis als
nummeriertes Kapitel, Extraktion der Literatureinträge, Belege ohne Verzeichniseintrag.

`[!]` = Befund aus dem Dokument. `[?]` = Verdacht, der eine eigene Prüfung braucht.

**Exit 2 heißt: nicht gelesen.** Eine leere Befundliste aus einem ungelesenen Dokument nie
als „keine Mängel" weiterreichen.

## Step 2 — GATE: jede Quelle gegen das Original

**Pflicht, nicht Empfehlung.** Für **jeden** Eintrag aus F12 einen Abruf (WebFetch/WebSearch)
und Autoren, Jahr, Titel, Publikationsort abgleichen. Ergebnis je Eintrag:
`bestätigt` · `abweichend (mit korrekter Fassung)` · `nicht auffindbar` · `nicht geprüft`.

Drei Regeln, jede aus einem realen Fehlschlag:

1. **Kein Marker ≠ korrekt.** Am Realfall trugen **3 von 9** falsch zugeschriebenen
   Einträgen keinen Marker, der auf das Autorenfeld zeigt; **2 davon trugen überhaupt
   keinen** (`Athanasopoulos, R. J.` für Hyndman & Athanasopoulos, `G. Rajaguru, S. L.`
   für Rajaguru, Lim & O'Neill). Sie waren formal sauber gesetzt und trotzdem falsch.
   Ein vierter (`Léo Grinsztajn, E. O.`) wurde erst gefunden, nachdem die
   Zeichenklasse Akzente zuließ — vorher zählte er stillschweigend als unauffällig.
2. **Nie aus dem Gedächtnis korrigieren.** Eine erfundene Korrektur in einer Rückmeldung an
   eine:n Studierende:n ist der teuerste Fehler dieses Ablaufs: Sie sieht autoritativ aus
   und ist falsifizierbar. Ohne Abruf gilt der Eintrag als `nicht geprüft` — das steht so im
   Bericht, statt weggelassen zu werden.
3. **Positivprobe vor Abwesenheitsaussage.** „Quelle existiert nicht" erst behaupten, wenn
   derselbe Suchweg nachweislich eine bekannte Quelle findet. Sonst ist die Null der Filter.

## Step 3: Bericht als Datei

Ergebnis nach `docs/pruefungen/<jjjj-mm-tt>-<kurzname>.md` — die Mail ist flüchtig, die
Zweitkorrektur und die Verteidigung brauchen ein Artefakt. Enthält: Werkzeug-Ausgabe,
Quellentabelle aus Step 2 mit Verdikt je Eintrag, und ausdrücklich die **nicht geprüften**
Punkte.

> ⚠️ Enthält der Bericht Personendaten (Name, Matrikelnummer, Anschrift) und ist das
> Ziel-Repo öffentlich, gehört er **nicht** dorthin. `platform` ist öffentlich.

## Step 4: Antwort als Entwurf — kein Versand

`draft_mail.py --role <rolle> --account <konto> --in-reply-to <message-id>`. Die Rolle
bestimmt Absender und Signatur; `--role` allein wechselt **nicht** das Postfach, `--account`
muss dazu. Ohne `--in-reply-to` reißt der Strang beim Empfänger.

Aufbau der Rückmeldung: zwingend vor Abgabe → Verzeichnisse/Nummerierung → Abbildungen →
PDF-Export → Literaturverzeichnis → Belege → offene Fragen der einreichenden Person.
Zusagen mit Datum (»Rückmeldung bis …«) sind Zusagen **im Namen des Owners** — im Bericht
kenntlich machen, damit sie bewusst bestätigt werden.

## Output-Format

```
1. Werkzeug-Ausgabe (F01–F13)
2. Quellentabelle: Eintrag | Verdikt | korrekte Fassung
3. Bericht docs/pruefungen/<datum>-<name>.md
4. Entwurf im Postfach <konto>/Entwürfe, UID genannt, NICHT gesendet
5. Ausdrücklich: was nicht geprüft wurde
```

## Anti-Patterns

- ❌ Eine Autorenkorrektur schreiben, ohne die Quelle abgerufen zu haben.
- ❌ Einen Eintrag ohne Verdachtsmarker als geprüft ausweisen.
- ❌ Einen Eintrag, der nicht geprüft wurde, aus dem Bericht weglassen.
- ❌ Zahlen aus einer eigenen Ad-hoc-Extraktion melden, statt aus dem Werkzeug — die
  erste manuelle Zählung lag bei Abbildungen und Belegen daneben.
- ❌ Die Antwort senden. Dieser Skill legt **ausschließlich** Entwürfe ab.
- ❌ Einen Bericht mit Personendaten in ein öffentliches Repo committen.
- ❌ Inhaltliche Bewertung als „Prüfung" ausgeben — dieser Skill deckt nur das Formale.

## Abschluss-Checkliste (PFLICHT)

| # | Check | Status |
|---|-------|--------|
| 1 | Werkzeug gelaufen, Exit 0, Ausgabe gezeigt (Step 1) | ☐ |
| 2 | JEDER F12-Eintrag hat ein Verdikt — auch `nicht geprüft` (Step 2 Gate) | ☐ |
| 3 | Positivprobe gefahren, bevor eine Quelle als nicht existent gilt | ☐ |
| 4 | Bericht geschrieben, Ablageort auf Personendaten geprüft (Step 3) | ☐ |
| 5 | Entwurf abgelegt, `--account` gesetzt, `--in-reply-to` gesetzt, NICHT gesendet | ☐ |
| 6 | Termin-/Inhaltszusagen im Namen des Owners benannt | ☐ |
| 7 | Nicht-Geprüftes ausdrücklich aufgezählt | ☐ |

## Changelog

- 2026-08-05: v1 — aus der Prüfung einer Masterarbeit (127 S.) entstanden. Mechanik in
  `tools/dokument_formalpruefung.py` (13 Prüfungen, 28 Tests), Skill trägt Orchestrierung,
  Quellen-Gate und Entwurfs-Regel. Bewusst Werkzeug statt Prosa-Prüfliste — dieselbe Lehre
  wie KONZ-platform-038 D6 (eine Regel ohne maschinellen Konsumenten ist Prosa).
