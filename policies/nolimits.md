# Policy: #nolimits — Optionsraum vor Konvergenz
<!-- rule_class: B | assessed_with: claude-opus-5 | reassess_by: 2026-12-01 (KONZ-038 D4) -->

**Trigger words:** #nolimits, #nolimits_aus, optionsraum, konzeptphase, evaluierungsphase,
welche moeglichkeiten, alternativen, was gibt es noch, denk breiter, entfessle

## Rule (User-Weisung 2026-08-10)

In der **Evaluierungs- und Konzeptphase** gelten andere Regeln als beim Bauen. `#nolimits`
schaltet für die Dauer der Phase Mechanismen ab, die auf **Konvergenz** optimieren, und
Mechanismen an, die auf **Vollständigkeit und Schärfe** optimieren.

Ende der Phase: `#nolimits_aus` — oder spätestens, sobald etwas gebaut wird.

### Was NICHT abgeschaltet wird

`#nolimits` erweitert **Latitüde im Denken**, nicht **Befugnis im Handeln**. Unverändert
in Kraft:

- **Evidenz-Disziplin** (`evidence-discipline.md`) — sie verlangsamt, aber sie verengt
  nicht. Sie ist der Grund, warum Optionen mit Kill-Kriterien statt mit Meinungen kommen.
- **Alle fünf Gates** (`autonomy-gates.md`). In dieser Phase wird ohnehin nichts gebaut,
  nichts ausgegeben, nichts deployt — die Gates sind schlicht nicht berührt.
- **Sicherheits- und Rechtsgrenzen**, Secrets-Regeln, Datensouveränität.

Ein Vorschlag im Optionsraum ist ein **Vorschlag**. Er wird nicht dadurch umgesetzt, dass
er ausgesprochen wurde.

## Die drei Mechanismen

### 1. Abruf erzwingen, nicht Kreativität

Das Problem ist selten fehlendes Wissen, sondern **nicht abgerufenes** Wissen: Assoziation
aktiviert die Nachbarschaft des zuletzt Besprochenen. Wer über LoRA-Training redet, ruft
LoRA-Nachbarschaft ab — und nicht die Alternative, die das Training überflüssig macht.

**Verfahren:** Vor jeder Bewertung ein **Inventar ohne Bewertung** — 10–15 Verfahren,
Werkzeuge, Modelle oder Standards des Feldes, je ein Satz, ungefiltert, ohne Bezug zum
konkreten Projekt. Erst danach die Frage, was davon trifft.

Die Trennung ist der Wirkmechanismus: Bewerten während des Sammelns filtert weg, was noch
nicht als relevant erkannt ist.

### 2. Prämissen-Verbot

Kein Satz der Form *„wir haben X entschieden"* zählt als Argument. Jede frühere
Entscheidung wird aus ihren **Tatsachen** neu hergeleitet oder sie fällt.

Das ist kein Misstrauen gegen alte Entscheidungen, sondern gegen alte **Grundlagen**: eine
Entscheidung, die unter anderen Tatsachen richtig war, wird durch Zitieren nicht wieder
richtig.

### 3. Umkehrfragen statt Zielfragen

„Wie erreichen wir das Ziel" erzeugt Varianten desselben Wegs. Wege wechselt man mit:

- **Was würde dieses Ziel überflüssig machen?**
- **Was würden wir wegwerfen, wenn wir heute anfingen?**
- **Was macht diese Festlegung für immer teuer?**
- **Was täte hier jemand, der gar nicht erst in unserer Technik denkt?**

## Schärfe: Kill-Kriterium vor Auswahl

Breite allein erzeugt ein Menü, keine Entscheidung. Jede Option kommt mit **der einen
billig prüfbaren Beobachtung, die sie erledigt** — und der billigste dieser Checks läuft
zuerst. Damit wird Breite zu Entscheidung statt zu Auswahlschmerz.

Ohne Kill-Kriterium ist eine Option kein Beitrag, sondern ein Einfall.

## Frischer Kopf

Das Retro-Prinzip **Richter ≠ Angeklagter** gilt hier genauso: wer die bisherige Arbeit
kennt, spannt einen engeren Optionsraum auf. Bei substanziellen Konzeptfragen deshalb
einen Unteragenten mit **nur der Problemstellung** starten — ohne Historie, ohne
akzeptierten Zielzustand, mit ausdrücklichem Rechercheverbot zur Projektvergangenheit —
und sein Ergebnis gegen das eigene halten.

Kostet Tokens; im Konzeptteil einer Entscheidung, die Monate trägt, ist das billig.

## Grenze der Selbstauskunft

Ein Inventar zeigt, **was abgerufen wird** — nicht, **was fehlt**. Gegen diese Lücke hilft
keine Introspektion, sondern nur eine Außenquelle: Web-Recherche, ein zweites Modell, ein
Mensch vom Fach. Bei allem, was sich schnell ändert (Modelllizenzen, Werkzeug-Ökosysteme,
Preise), ist der eigene Wissensstand als **Ausgangspunkt** zu behandeln, nicht als Befund.

## Herkunft

Owner-Weisung 2026-08-10 nach einem konkreten Fehlschlag in `illustration-hub`: acht
Stunden Arbeit an einem LoRA-Programm für fünf Figuren, während die Alternative — ein
Basismodell, für das reife Identitäts-Übertragung existiert und das jedes Training
überflüssig gemacht hätte — nie zur Sprache kam. Alle Tatsachen lagen vor; sie wurden
nicht zusammengesetzt.

Ursache war nicht fehlendes Wissen und nicht die Governance, sondern **Verankerung** an
einer Entscheidung, deren Grundlage sich geändert hatte, plus der Konvergenzdruck aus
Zielzustand, Scope-Checkpoints und Artefakt-Budget. Diese drei bleiben beim Bauen richtig
— in der Konzeptphase sind sie der Fehler.

**Selbstbetreffend gekennzeichnet:** Diese Policy erweitert die Latitüde des Agenten in
der Konzeptphase. Sie wurde auf ausdrückliche Weisung angelegt und lässt Gates,
Evidenz-Disziplin und Sicherheitsgrenzen unberührt.

## Changelog

- 2026-08-10: Initial. Owner-Weisung, Anlass siehe Herkunft.
