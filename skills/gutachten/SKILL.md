---
name: gutachten
description: Inhaltliches Gutachten zu einer eingereichten Abschlussarbeit erstellen — Punkteschema aus der Vorlage, jede Quelle gegen das Original, Kritik-Tabelle mit Seitenbelegen; Notenzeile bleibt offen (Prüfer entscheidet)
metadata:
  mode: write
  scope: plattformweit
  statefulness: zustandslos
  trigger: interaktiv
---

# /gutachten — Inhaltliche Begutachtung einer Abschlussarbeit

> **Wann:** Eine Abschlussarbeit ist eingereicht und es soll ein **Gutachten** entstehen —
> Bewertung nach dem Punkteschema der Prüfungsvorlage, mit belegten Beispielen und
> Verbesserungsvorschlägen.
> **Wann NICHT:** Reine Formalprüfung vor der Abgabe → `/arbeit-pruefen` (Deckblatt,
> Verzeichnisse, Nummerierung, Belegmechanik). Rückmeldung an Studierende zu einem
> Zwischenstand ist eine normale Mail, kein Gutachten.

**Verhältnis zu `/arbeit-pruefen`:** Die beiden Skills teilen sich die Arbeit, sie ersetzen
einander nicht. `/arbeit-pruefen` liefert die **zählbaren** Befunde und läuft deshalb
**zuerst**; dieser Skill nimmt dessen Ausgabe als Eingabe und fügt das hinzu, was gezählt
werden kann: Urteil, Einordnung, Punktvergabe. Wer nur begutachtet, ohne vorher zu zählen,
produziert falsche Zahlen — genau der Fehler, der `/arbeit-pruefen` überhaupt ausgelöst hat.

## Verwendung

```
/gutachten <pfad-zur-arbeit.pdf> [--vorlage <pfad-zur-bewertungsvorlage.pdf>]
/gutachten <verzeichnis>            # Arbeit + Vorlage im selben Ordner
```

## Grundregeln, die den ganzen Lauf bestimmen

1. **Die Note setzt der Prüfer, nicht der Skill.** Das erzeugte Gutachten trägt einen
   Punktevorschlag mit Begründung je Kriterium und eine **offene Notenzeile**. Ändert der
   Prüfer die Note, werden die Teilpunkte nachgezogen und die geänderten Kriterien im
   Antworttext benannt — nie stillschweigend passend gerechnet.
2. **Das Punkteschema kommt aus der Vorlage, nicht aus dem Prompt.** Nennt der Auftrag
   andere Kategorien als die Vorlage, gewinnt die Vorlage; die Zuordnung wird im
   Antworttext offengelegt.
3. **Jede prüfbare Aussage wird geprüft.** Seitenangaben, Jahreszahlen, Normversionen,
   Autorennamen: gegen das Original, nicht gegen die Erinnerung. Was nicht geprüft werden
   konnte, wird als ungeprüft gekennzeichnet.
4. **Personendaten bleiben lokal.** Name, Matrikelnummer, Geburtsdatum und Bewertung gehen
   nie in ein Repo, nie in eine Memory-Datei, nie an einen externen Dienst. Auch nicht in
   ein Artifact. Ablage ausschließlich im lokalen Arbeitsverzeichnis.

## Step 0: Unterlagen sichten

```bash
ls -la <verzeichnis>
pdfinfo <arbeit.pdf> | head -8
```

Erwartet werden zwei Dateien: die Arbeit und die **Bewertungsvorlage** des Prüfungsamts.
Fehlt die Vorlage, wird der Lauf **abgebrochen** — ohne Punkteschema entsteht kein
Gutachten, sondern eine Meinung. Beim Owner nachfragen, nicht ein Schema erfinden.

## Step 1: Mechanische Prüfung zuerst (Werkzeug vor Handarbeit)

```bash
python3 tools/dokument_formalpruefung.py <arbeit.pdf>
```

Die Ausgabe ist Eingabe für Schritt 5, nicht Beiwerk. `[!]`-Befunde sind belegt,
`[?]`-Befunde brauchen eine eigene Prüfung.

**Nicht überspringen, auch wenn die Arbeit „sauber aussieht".** Der Lauf am 2026-08-18
wurde erst nach der Handanalyse gestartet; er bestätigte einen Befund, den die Handanalyse
ebenfalls gefunden hatte — aber die Reihenfolge war falsch herum und hätte bei einer
größeren Arbeit Zahlen gekostet.

## Step 2: Vorlage auslesen und Schema festhalten

```bash
pdftotext -layout <vorlage.pdf> vorlage.txt
```

Festzuhalten sind: Bewertungskategorien, Maximalpunkte je Kategorie, die Einzelkriterien
je Kategorie, die Bewertungsstufen (typisch `+ / o / −`) und der **Notenschlüssel**.
Der Notenschlüssel wird wörtlich übernommen und nicht interpoliert.

## Step 3: Arbeit seitenweise extrahieren

```bash
python3 - <<'PY'
import subprocess
pdf = "<arbeit.pdf>"; out = "arbeit_seiten.txt"
n = int(subprocess.run(["pdfinfo", pdf], capture_output=True, text=True)
        .stdout.split("Pages:")[1].split()[0])
with open(out, "w") as f:
    for p in range(1, n + 1):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), pdf, "-"],
                           capture_output=True, text=True).stdout
        f.write(f"\n<<<PDFSEITE {p}>>>\n" + t)
PY
```

**Den Seitenversatz einmal bestimmen und notieren.** Die Paginierung der Arbeit beginnt
später als die des PDF (Deckblatt, Verzeichnisse). Alle Fundstellen im Gutachten werden in
der **Paginierung der Arbeit** angegeben — das ist die Nummer, die die Verfasserin sieht.

## Step 4: Vollständig lesen, nicht überfliegen

Pflichtlektüre in dieser Reihenfolge: Zusammenfassung, Einleitung mit Forschungsfrage,
**Methodenkapitel vollständig**, Ergebniskapitel, Konzept-/Gestaltungsteil, Diskussion,
Fazit, Verzeichnisse. Das Methodenkapitel entscheidet über die halbe Bewertung und wird
deshalb nie quergelesen.

Beim Lesen mitschreiben, was später Beleg werden soll: Seite, wörtliches Zitat, Kategorie.
Ein Befund ohne wörtlichen Beleg kommt nicht ins Gutachten.

## Step 5: Strukturprüfungen per Skript, nicht per Gefühl

Diese vier Prüfungen finden zuverlässig, was beim Lesen durchrutscht:

```bash
# a) Quellenangaben unter Abbildungen und Tabellen — welche fehlen?
# b) Fundstellen je Kurzbeleg mit Seitenzahl der Arbeit
# c) Quellen im Literaturverzeichnis, die im Text nie zitiert werden
# d) Zitierstil-Brüche: Klammerbelege in einer Fußnoten-Arbeit
```

Muster für (a) und (b): über `arbeit_seiten.txt` laufen, `<<<PDFSEITE n>>>` als
Seitenzähler mitführen, Treffer mit `n − versatz` ausgeben. Für (c) die Nachnamen aus dem
Literaturverzeichnis gegen den Fußnotenapparat prüfen — eine Quelle im Verzeichnis ohne
einen einzigen Beleg ist ein eigener Befund, ebenso ein Beleg ohne Verzeichniseintrag.

## Step 6: Quellenprüfung im Netz

Zu prüfen sind mindestens: alle Belege mit Seitenangabe auf Plausibilität gegen den Umfang
der Quelle, alle Normversionen, alle Autorennamen, alle DOI-Felder.

- **Widersprüche innerhalb der Arbeit zuerst** — zwei unvereinbare Seitenangaben zur selben
  Quelle sind ohne jede Netzrecherche beweisbar und wiegen schwerer als eine externe
  Abweichung.
- **Normen und Standards immer live prüfen.** Versionsstände altern zwischen Themenvergabe
  und Abgabe; ein „Stand <Jahr>" im Text ist eine überprüfbare Tatsachenbehauptung.
- **Was nicht auflösbar ist, bleibt Hypothese** und wird im Gutachten als solche formuliert
  („zu prüfen", nicht „falsch").

## Step 7: Bewerten

Je Einzelkriterium der Vorlage **genau ein ganzer Satz**, der eine Aussage trifft — nicht
den Kriteriennamen wiederholt. Der Satz nennt, woran die Bewertung hängt, und wo das im
Text steht.

Punktermittlung je Kategorie, transparent und reproduzierbar:

```
Punkte = Max × (Anzahl "+" + 0,5 × Anzahl "o") / Anzahl Kriterien
```

kaufmännisch gerundet. Abweichungen von dieser Regel sind erlaubt, müssen aber im
Antworttext begründet werden — etwa wenn ein einzelnes Kriterium die Kategorie dominiert.

Die Gesamtnote wird **ausschließlich** über den Notenschlüssel der Vorlage aus der
Punktsumme abgelesen.

## Step 8: Gutachten und Kritik-Tabelle schreiben

Zwei Dateien im lokalen Arbeitsverzeichnis:

**`gutachten-<nachname>.md`** — Kopf nach Vorlage (Verfasser, Kurs, Prüfer, Titel, Daten,
Umfang in Zahlen), je Kategorie eine Tabelle mit Stufe, Kriterium und Bewertungssatz,
Punktesumme, Notenzeile, dann das **Fließtext-Gutachten**: Gegenstand, Stärken mit Belegen,
Schwächen mit Belegen, Praxistransfer, Gesamturteil. Fünf bis sieben Absätze, keine
Aufzählungen — ein Gutachten ist ein Text.

**`kritik-tabelle-<nachname>.md`** — sechs Spalten, sortiert nach Kategorie (erst positiv,
dann negativ) und darin nach Seite aufsteigend:

| Spalte | Inhalt |
|---|---|
| Anmerkung | Der Befund in einem Halbsatz |
| Beispiele der Verfasserin | Wörtliche Zitate mit Seite, **mehrere**, bevorzugt kontrastierend |
| Meine Anmerkung | Warum das zählt — Wirkung, nicht Wiederholung |
| Verbesserungsvorschlag (generisch) | Die Regel, die den Fehler künftig verhindert |
| Beispiel für die Verbesserung (explizit) | Der konkrete Ersatztext, kopierfähig |
| Seite(n) | Paginierung der Arbeit; `LV` für das Literaturverzeichnis |

**Kontrastierende Beispiele sind der Kern der Spalte 2.** „Hier fehlt die Quellenangabe"
überzeugt niemanden; „Tab. 3 (S. 47) ohne Quellenzeile, während Tab. 1 (S. 44) und Tab. 7
(S. 79) eine tragen" ist ein Befund.

## Output-Format

```
📊 Bewertung nach Punkteschema
| Kategorie | Max | Ist | Kurzbegründung |
...
| Summe | 60 | 47 | Note 2,3 (Vorschlag) |

🔴 Gewichtigste Mängel      (# | Befund | Seite)
🟢 Tragende Stärken         (# | Befund | Seite)
📂 Artefakte                (Pfad | Inhalt)

Danach: Begründung der Note in Prosa, dann die Liste der geprüften Quellen mit Ergebnis.
```

Die Kritik-Tabelle wird **nicht** in den Chat gerendert — sechs Spalten sprengen jede
Terminalbreite. Im Chat steht der Pfad, der Inhalt steht in der Datei.

## Anti-Patterns

- ❌ Note setzen, ohne sie als **Vorschlag** zu kennzeichnen — die Note gehört dem Prüfer
- ❌ Teilpunkte an eine vorgegebene Note anpassen, ohne zu sagen **welche Kriterien** sich geändert haben
- ❌ Das Punkteschema aus dem Prompt nehmen, wenn eine Vorlage vorliegt
- ❌ Ohne Bewertungsvorlage loslegen und ein Schema erfinden
- ❌ `dokument_formalpruefung.py` erst nach der Handanalyse laufen lassen — oder gar nicht
- ❌ Befunde ohne wörtlichen Beleg und Seitenzahl
- ❌ Seitenzahlen der PDF-Datei statt der Paginierung der Arbeit angeben
- ❌ Eine Quellenabweichung behaupten, die nicht am Original geprüft wurde
- ❌ Name, Matrikelnummer oder Bewertung in ein Repo, eine Memory-Datei oder ein Artifact schreiben
- ❌ Das Gutachten versenden — der Skill schreibt Dateien, der Prüfer zeichnet und versendet

## Abschluss-Checkliste (PFLICHT, jede Zeile abhaken)

- [ ] Bewertungsvorlage lag vor; Schema und Notenschlüssel daraus übernommen
- [ ] `dokument_formalpruefung.py` lief **vor** der Handanalyse; Ausgabe eingearbeitet
- [ ] Seitenversatz bestimmt; alle Fundstellen in der Paginierung der Arbeit
- [ ] Methodenkapitel vollständig gelesen, nicht quergelesen
- [ ] Strukturprüfungen (a) bis (d) aus Step 5 gelaufen
- [ ] Quellen geprüft; jede Aussage entweder belegt oder als Hypothese markiert
- [ ] Je Einzelkriterium **ein** Bewertungssatz, keiner leer
- [ ] Punkte je Kategorie nachrechenbar; Note aus dem Notenschlüssel abgelesen
- [ ] Notenzeile als Vorschlag gekennzeichnet, Unterschriftsfeld offen
- [ ] Beide Dateien lokal; nichts in Repo, Memory oder externem Dienst
- [ ] Nichts versendet

## Changelog

- 2026-08-18: Initial. Ausgelöst durch den ersten Gutachten-Auftrag (Masterthesis, 149 PDF-Seiten,
  132 Seiten Textteil, 126 Fußnoten, 30 Literaturquellen). `/arbeit-pruefen` schloss inhaltliche
  Begutachtung ausdrücklich aus („bleibt Handarbeit") — dieser Skill füllt die Lücke und
  übernimmt die Formalprüfung als Vorstufe. Lehren aus dem Dogfood-Lauf, die hier zu Regeln
  wurden: Werkzeug vor Handarbeit (Step 1), Seitenversatz einmal bestimmen (Step 3),
  Widersprüche in der Arbeit vor externer Recherche (Step 6), kontrastierende Beispiele in der
  Kritik-Tabelle (Step 8), Personendaten bleiben lokal (Grundregel 4).
