# Kalibrierung `zusage-ohne-verankerung` — 2026-08-23

Messgrundlage fuer das Gate `zusage-ohne-verankerung`
(`tools/verankerung_pruefer.py`, [platform#2211](https://github.com/achimdehnert/platform/issues/2211)).
Alle Zahlen stammen aus echten Laeufen dieses Tages gegen echte PR-Texte; nichts
hier ist geschaetzt. Modell: `qwen2.5:14b` ueber loopback-lokales Ollama
(`127.0.0.1:11434`) — kein Egress, keine Kosten.

## 1. Warum ueberhaupt ein zweiter Weg

Der Zielfall ist der Abschnitt „Bewusste Restueberschneidung" in
[PR #2007](https://github.com/achimdehnert/platform/pull/2007), von Retro
`9d861a` als Befund #3 protokolliert: eine bewusst aufgeschobene Konsolidierung
ohne Tracking-Artefakt.

Beide bestehenden Muster-Scanner wurden an genau diesem Text gemessen:

| Werkzeug | Lauf am Originaltext | Ergebnis |
|---|---|---|
| `tools/deferral_anchor_check.py` | ganzer PR-Text | **`✅ jede angekuendigte Auslassung hat eine Issue-Referenz`** |
| `DEFERRAL_PATTERNS` (`deferred_item_scanner.py`) | die Zeile selbst | **kein Treffer** |

Zwei unabhaengige Ursachen, beide isoliert nachgestellt:

**A — Auszeichnung.** Der Text lautet `bewusst **nicht** mitgemacht`. Ohne die
vier Sternchen treffen *beide* Muster (`AUFSCHUB` → `bewusst nicht`,
`DEFERRAL_PATTERNS` → `bewusst nicht mitgemacht`); mit ihnen keines. Der Wortlaut
war am 2026-08-16 eigens wegen dieses Retros nachgetragen worden — und blieb
blind fuer das Artefakt, fuer das er nachgetragen wurde.

**B — Naehe statt Zustaendigkeit.** Auch mit entfernter Auszeichnung verschwindet
der Fund. Im selben Satz steht `#2005` — ein **Pull Request**, der eine Herkunft
belegt („aus #2005") und nichts verfolgt.

Und das ist nicht einmal der schwerere Teil. Nachdem beide Gates PR-Verweise
nicht mehr als Anker zaehlen, bleibt die Stelle fuer das Naehe-Verfahren
**weiterhin** unsichtbar: geraeumt wird sie jetzt von **`#1953`**, einer voellig
fremden Issue-Nummer aus einer Beleg-Aufzaehlung vier Zeilen darueber. Ein
Zeilenfenster kann Zustaendigkeit prinzipiell nicht von Nachbarschaft trennen —
in einem dichten PR-Text steht fast immer irgendeine Nummer in Reichweite.

Damit ist die Grenze des Muster-Ansatzes nicht argumentiert, sondern gemessen:
zwei Reparaturen an `deferral_anchor_check.py` (Normalisierung, PR-Ausschluss)
sind echte Verbesserungen und heilen den Realfall **nicht**. Erst die
Anker-Pruefung **im Segment** statt im Fenster sieht ihn.

Damit ist die Frage aus [#2143](https://github.com/achimdehnert/platform/issues/2143)
(„ausweiten oder umbauen") fuer diesen Slug entschieden: **umbauen.** Ausweiten
haette A bis zur naechsten Auszeichnung geheilt und B gar nicht.

## 2. Gemessene Guete (Welle 1, Klasse `vertagung`)

Vier echte PR-Texte, Standardaufruf (`--klassen vertagung`, Gegenprobe an):

| PR | Segmente | gemeldet | davon richtig | Bemerkung |
|---|---|---|---|---|
| [#2007](https://github.com/achimdehnert/platform/pull/2007) | 12 | 1 | **1** | der Zielfall, mit Zitat „ist hier bewusst nicht mitgemacht" |
| [#2196](https://github.com/achimdehnert/platform/pull/2196) | 10 | 1 | 0 | **Fehlalarm**: „Dublettenfilter entfernt. Idempotenz braucht ihn nicht" ist erledigte Arbeit |
| [#2209](https://github.com/achimdehnert/platform/pull/2209) | 7 | 0 | — | sauber |
| [#2200](https://github.com/achimdehnert/platform/pull/2200) | 8 | 0 | — | sauber |
| PR dieses Umbaus (Text vor dem Anlegen geprueft) | 25 | 3 | 0 | **alle drei falsch** — siehe unten |
| **Summe** | **62** | **5** | **1** | Praezision 0,20 · ohne den Meta-Text 0,50 · Recall am bekannten Zielfall 1/1 |

Der Vergleich, der zaehlt: auf demselben Zielfall melden die beiden bestehenden
Scanner **null**. Der Grund fuer `mode=advisory` steht trotzdem in derselben
Tabelle — vier von fuenf Meldungen sind Fehlalarme.

### Die unangenehmste Messung: Texte UEBER Vertagungen

Der PR-Text dieses Umbaus wurde vor dem Anlegen durch das eigene Werkzeug
geschickt. Ergebnis: 3 Meldungen, **keine** davon richtig.

| Stelle | warum es keine Zusage ist |
|---|---|
| „ist bewusst nicht mitgemacht" | **Zitat des Zielfalls**, nicht eigene Vertagung |
| „NICHT PRUEFBAR, Exit 2" | Beschreibung des gebauten Verhaltens |
| „wirkt sie nicht" | Messergebnis ueber die Gegenprobe |

Ein Text, der von Vertagungen handelt, liest sich fuer den Klassifikator wie
eine. Umgekehrt hat derselbe Lauf den **echten** Aufschub-Abschnitt dieses PRs
(„Bewusst nicht in diesem PR") korrekt **nicht** gemeldet — er traegt seine
Issue-Nummer im selben Abschnitt. Der Anker-Teil arbeitet also richtig; die
Schwaeche sitzt allein in der Klassifikation.

Konsequenz fuer das Kalibrierfenster: Retro-Reports, Gate-Dokumentation und
Meta-PRs sind eine eigene Textklasse und muessen getrennt ausgewertet werden —
sonst faerbt sie die Quote fuer den Normalfall ein. Getrackt in
[#2214](https://github.com/achimdehnert/platform/issues/2214).

## 2a. Was die Reparatur des alten Gates gebracht hat

`tools/deferral_anchor_check.py` ist in diesem Zug zweimal praeziser geworden —
mit Drills und ohne Anspruch auf mehr:

| Fall | vorher | nachher |
|---|---|---|
| `bewusst **nicht** mitgemacht`, keine fremde Nummer in der Naehe | uebersehen | **gefunden** |
| Aufschub mit `[#N](…/pull/N)` im selben Satz | geraeumt | **gefunden** |
| Realfall PR #2007 (fremde `#1953` vier Zeilen darueber) | uebersehen | **weiterhin uebersehen** |

Die letzte Zeile steht als Test im Drill (`test_should_die_grenze_der_naehe_festhalten`),
damit die Grenze nicht wieder in Vergessenheit geraet.

## 2b. Generalisierung — der eigentliche Punkt des Umbaus

Ein Muster-Scanner kann nur finden, was jemand aufgezaehlt hat. Gegenprobe mit
einer gewoehnlichen, aber unaufgezaehlten Vertagung:

> „Das Aufraeumen der Altlast in der alten Struktur hebe ich mir fuer den
> naechsten Durchgang auf."

| Werkzeug | Ergebnis |
|---|---|
| `DEFERRAL_PATTERNS` (Stop-Hook) | kein Treffer |
| `AUFSCHUB` (PR-Gate) | kein Treffer |
| `verankerung_pruefer.py` | **`[vertagung]`**, Zitat „hebe ich mir fuer den naechsten Durchgang auf" |

Die Haelfte dieser Messung, die ohne Modell auskommt (beide Muster schweigen),
steht als Drill fest: `test_should_belegen_dass_beide_musterlisten_bei_neuer_formulierung_schweigen`.

## 3. Was die einzelnen Stufen gebracht haben

| Schritt | Befunde auf #2007 | davon richtig |
|---|---|---|
| erster Prompt, `qwen2.5:7b`, alle Klassen | 5 | 1 |
| Prompt mit Negativ-Beispielen, `7b` | 3 | 1 |
| derselbe Prompt, `qwen2.5:14b` | 2 | 1 |
| + Beiwerk-Filter (Signatur/`Closes #N` sind keine Segmente) | **1** | **1** |

Der Beiwerk-Filter kam aus einem echten Fehlalarm: die Zeile
`🤖 Generated with Claude Code` erbte die Ueberschrift „Bewusste
Restueberschneidung" und wurde als `restarbeit` gemeldet.

**Gegenprobe (zweite, typisierte Frage „steht die Arbeit noch aus?"):** isoliert
gemessen an #2200, Klasse `restarbeit` — **2 Befunde ohne, 1 mit** Gegenprobe.
Der verworfene war ein Fehlalarm. Auf den `vertagung`-Fehlalarm in #2196 hatte
sie **keine** Wirkung. Ihr Nutzen ist damit teilweise belegt, nicht vollstaendig.

## 4. Warum Welle 1 nur `vertagung` meldet

`restarbeit` und `freigabe` sind implementiert und ueber `--klassen` erreichbar,
aber ihre Praezision ist schlechter: im Lauf ueber alle Klassen erzeugten sie auf
#2007 und #2200 zusammen vier Fehlalarme (u. a. „Verifiziert"-Abschnitte und
Messwert-Prosa). Sie bleiben deshalb aus der Vorgabe heraus, bis eigene Zahlen
vorliegen — getrackt, nicht vergessen.

## 5. Offene Punkte fuer die Auswertung des Kalibrierfensters

1. Der Fehlalarm aus #2196 — genuegt eine Prompt-Praezisierung, oder braucht die
   Klasse eine zweite unabhaengige Stimme?
2. Laufzeit: rund eine Minute je zehn Segmente auf `14b`. Fuer den Sitzungs-Abschluss
   tragbar, fuer einen Hook je Turn nicht — deshalb ist das Gate dort **nicht** verdrahtet.
3. `covers` beansprucht bewusst nur `deferred-item-no-tracking-issue`. Jede weitere
   Zeile braucht einen eigenen Positivbeleg, keine Plausibilitaet.

## 6. Fehlalarm 2026-08-23 (Sitzungsende) — Anker im Segment, aber nicht gesehen

Lauf ueber die eigenen PR-Texte der Sitzung. Gemeldet wurde
[#2220](https://github.com/achimdehnert/platform/pull/2220):

> Zitat: „Bewusst nicht in diesem PR"
> Anker: keine Issue-Referenz im Segment

**Das ist ein Fehlalarm.** Der Abschnitt lautet vollstaendig:

```
## Bewusst nicht in diesem PR

- **Verteilung der Skill-Aenderung** (`session-start.md`) erst **nach** dem Merge —
  eine hand-verteilte Kopie aus einem ungemergten Zweig waere ungeprueffter Kontext.
- **Wiedervorlage fuer die Gate-Registry** (`gate_wirkung.py`) — dieselbe Krankheit,
  anderes Register. Beides als Checkliste in #2215.
- Reparatur von coach-hub und bahn-hub selbst.
```

`#2215` steht drei Zeilen unter der Ueberschrift, im selben Abschnitt — und das
Issue traegt die beiden Punkte tatsaechlich als Checkliste
([Kommentar](https://github.com/achimdehnert/platform/issues/2215#issuecomment-5385174586)).
Das Tracking existiert also; der Pruefer hat es nicht gefunden.

**Vermutete Ursache, nicht verifiziert:** der Anker sitzt nicht neben der
Vertagungsformulierung („erst nach dem Merge"), sondern eine Aufzaehlungsebene
tiefer und **hinter** einem zweiten Satz. Ein Anker-Test, der im unmittelbaren
Umfeld der Formulierung sucht, verfehlt ihn. Billigster Check fuer die Auswertung:
denselben Text mit `#2215` direkt hinter „erst **nach** dem Merge" erneut durch
den Pruefer schicken — meldet er dann nichts, ist die Naehe die Ursache.

**Stand des Fensters damit:** 5 echte PR-Texte, 1 Treffer, **2 Fehlalarme**
(#2196 und #2220), 2 saubere Texte. Praezision faellt von 0,50 auf **0,33**.
Das ist ein Argument gegen Scharfschaltung, kein Argument fuer eine weitere
Musterzeile — dieselbe Lehre wie beim Gate, das der Pruefer ersetzen soll.

---

## 6. Fenster-Zeilen (fortlaufend)

### 2026-08-23, Phase 0g auf den eigenen PR-Texten dieser Sitzung

| Text | Meldung | Urteil |
|---|---|---|
| PR #2232 (Sweep-Werkzeug) | `[vertagung]` „umzubauen (13): ..." | **Fehlalarm** — Ergebnisliste eines Trockenlaufs, keine Zusage |
| PR #2232 | `[vertagung]` „übersprungen (14)" | **Fehlalarm** — dieselbe Liste, andere Haelfte |
| Flotten-PR-Text (13× identisch) | `✅` keine Meldung | richtig: der Abschnitt „Nicht verifiziert" traegt seine Issue-Nummer |

Dieselbe Schwaeche wie beim Meta-Text in §2a: eine Aufzaehlung von Repos, die
umgebaut *werden sollen*, liest sich fuer den Klassifikator wie eine Vertagung.
Der Unterschied zwischen „steht noch aus" und „ist das Ergebnis einer Messung"
ist genau die Grenze, an der die Klasse `vertagung` bisher scheitert.

**Vierte Fehlalarm-Klasse: das Stichwort ist ein Fachbegriff der Domaene.** Drei
Meldungen in einer Sitzung (risk-hub, 2026-08-24), alle drei auf demselben Wort, und
keine davon war eine Vertagung:

- **#672** *„Anhang III auf **02.12.2027** verschoben, Anhang I auf 02.08.2028"* — das
  ist eine **Rechtsfrist**, die der europaeische Gesetzgeber verschoben hat. Der Autor
  des PR-Textes verschiebt nichts; er berichtet, was verschoben WURDE.
- **#673** *„die Meldung, der AI Act sei verschoben worden"* — eine **zitierte
  Fremdaussage**, die der Text im selben Absatz **widerlegt** („verschoben wurden die
  Hochrisiko-Pflichten, die Kennzeichnung nicht"). Der Klassifikator meldet also genau
  den Satz, der eine Vertagung **bestreitet**.
- **#674** *„Schwerpunkt verschiebt sich vollstaendig"* — eine **Metapher** ueber
  Gewichtung zwischen zwei Dokumenten.

Das unterscheidet diese Klasse von den drei bisherigen: bei Meta-Text (§6), Konjunktiv
ueber Behobenes (#2239) und Konditional (#2247) trug das Wort noch seine
Vertagungs-Bedeutung, nur eben nicht als Zusage des Autors. Hier trifft es einen
**anderen Wortsinn**. Kein Tempus-, Modus- oder Subjekt-Signal hilft: „verschoben"
in *„die Frist wurde verschoben"* ist grammatisch identisch mit *„wir haben das
verschoben"*. Der Unterschied liegt allein daran, **wer** verschiebt — und das steht
im Satz, nicht in seiner Form.

Praktische Folge fuer die Auswertung: jedes Repo, dessen Fachsprache ein
Vertagungs-Stichwort als Terminus fuehrt — Recht (Fristen), Bau (Termine), Logistik
(Sendungen) —, erzeugt strukturell Fehlalarme. risk-hub ist als Compliance-Plattform
der Regelfall dafuer, nicht die Ausnahme.

**Stand des Fensters:** 19 geprueste Texte · 12 Meldungen · 1 richtig · 11 Fehlalarme.
Praezision 0,083 (vorher 0,111). Sechs weitere Texte, drei weitere Meldungen, keine
davon richtig — die Richtung des Fensters ist damit deutlicher als sein Endstand.

**Nachtrag 2026-08-26 (Sitzung 0d4b7c, zwei Meldungen, beide Fehlalarm):** `verankerung_pruefer.py` meldete #2327 und #2329 (je „Bewusst ausgelassen, getrackt"). Zitat #2329: „Pilot (K1–K5) → KONZ-051 Kill-Gate-Tabelle, Frist 2026-09-30" — das Tracking-Artefakt ist eine KONZ-Zeile mit Datum (laut Hausregel gleichwertig zum Issue), die der Pruefer nur als Issue-Nummer erkennt. Zitat #2327: „Skill `/ux-review` selbst: Folge-PR nach Akzeptanz dieses Konzepts" — inzwischen erfuellt (#2329). Stand des Fensters: 21 gepruefte Texte · 14 Meldungen · 1 richtig · 13 Fehlalarme (Praezision 0,071). Neue Fehlalarm-Klasse: **Tracking per KONZ-/Ledger-Zeile statt Issue** — der Pruefer kennt nur den Issue-Anker.

**Nachtrag 2026-08-27 (Sitzung 329244, drei Texte, eine Meldung, Fehlalarm):**
`verankerung_pruefer.py` lief ueber #2370, #2371 und #2375. Die ersten beiden sauber
(4 bzw. 3 Segmente). Bei #2375 eine Meldung, Klasse `vertagung`, Zitat:
*„~/.claude/CLAUDE.md bleibt unversioniert"*.

Das ist **keine Vertagung, sondern eine getroffene Entscheidung**. Der Owner hat den
Vorschlag, die Datei zu versionieren, an diesem Tag ausdruecklich abgelehnt; es gibt
keine aufgeschobene Restarbeit, die ein Issue verfolgen koennte. Durabel abgelegt ist
der Entscheid als Memory-Datei (`feedback_global_claude_md_stays_unversioned`) samt der
Folge, die daraus fuer den Code gilt — der Pruefer kennt diesen Anker-Typ nicht, wie
schon beim Nachtrag vom 2026-08-26 die KONZ-/Ledger-Zeile.

Neue Fehlalarm-Klasse: **abgelehnte Option statt aufgeschobener Arbeit.** „bleibt X"
und „wird nicht Y" beschreiben einen Endzustand, kein Spaeter. Die Unterscheidung ist
praktisch wichtig, weil die Gegenmassnahme sonst Issue-Spam erzeugt: jede bewusst
verworfene Option bekaeme ein Ticket, das nie geschlossen wird. Signal, das hier traegt
und in den bisherigen Klassen fehlte: die Aussage nennt **keinen spaeteren Zeitpunkt und
keine Bedingung** — weder „spaeter", „sobald", „nach", noch ein Datum.

**Stand des Fensters:** 24 gepruefte Texte · 15 Meldungen · 1 richtig · 14 Fehlalarme.
Praezision 0,067 (vorher 0,071).

### 2026-08-23 abends, Phase 0g auf den vier Gate-PRs (#2236–#2239)

| Text | Meldung | Urteil |
|---|---|---|
| PR #2236 (22 Segmente) | `✅` keine Meldung | richtig — jede Zusage traegt #2234/#2235 |
| PR #2237 (11 Segmente) | `✅` keine Meldung | richtig |
| PR #2238 (12 Segmente) | `✅` keine Meldung | richtig — die neun offenen Slugs nennen #2234 im selben Abschnitt |
| PR #2239 | `[vertagung]` „haette still bis zum Fristablauf gesammelt" | **Fehlalarm** — Konjunktiv II ueber den BEHOBENEN Zustand |

Der Satz im Volltext lautet: *„… konnte nie entscheidungsreif werden und haette
still bis zum Fristablauf gesammelt; das ist jetzt ein eigener, lauter Zustand
`unbestimmt`."* Der Nebensatz nach dem Semikolon sagt, dass es behoben ist — der
Klassifikator sieht den Konjunktiv davor und liest eine Vertagung.

**Neue Fehlalarm-Klasse, verwandt mit den Meta-Texten aus §6, aber nicht dieselbe:**
bisher waren es *Berichte ueber* Vertagungen (Trockenlauf-Listen, Meta-PRs). Hier ist
es die **Beschreibung des alten Verhaltens im Konjunktiv**, unmittelbar gefolgt von
der Behebung. Ein PR-Text, der erklaert, was ohne den Fix passiert waere, klingt
zwangslaeufig nach einer offenen Zusage. Das ist kein Randfall: so ist fast jede
gute Fehlerbeschreibung gebaut.

Praezision faellt damit von 0,14 auf 0,125. Der Vorschlag aus
[#2214](https://github.com/achimdehnert/platform/issues/2214) traegt weiter, muss
aber um diese zweite Klasse ergaenzt werden: **Tempus/Modus des Segments** ist ein
Signal, das der Klassifikator bisher nicht auswertet — „haette gesammelt" ist keine
Zusage, „sammelt weiter" waere eine.

---

## Lauf 2026-08-24 — vier PR-Texte (ADR-297-Strang)

| PR | Meldung | Verdikt |
|---|---|---|
| #2247 | `[vertagung]` „gehoeren gemeinsam verschoben" | **Fehlalarm** — Kopplungs-Bedingung, keine Zusage |
| #2252 | — | sauber |
| #2255 | — | sauber |
| #2257 | — | sauber |

Der Satz im Volltext lautet: *„`writing-hub` und `weltenhub` sind über `iil-weltenfw`
und eine laufende API verbunden. Sie gehören **zusammen** verschoben oder gar nicht —
eine Aufteilung auf zwei Orgs wäre schlechter als der Ist-Zustand."*

**Warum kein Tracking fehlt:** Das ist keine aufgeschobene Arbeit, sondern eine
**Bedingung für den Fall, dass** etwas getan wird — ein Konditional ohne Zusage. Der
Text sagt nicht „wir verschieben sie später", sondern „falls verschoben wird, dann
gemeinsam". Das Tracking-Artefakt für den Transfer selbst ist das ADR, in dem der
Satz steht: `status: proposed`, mit vier offenen Punkten und einem Kill-Gate zum
2026-11-24.

**Dritte Fehlalarm-Klasse, und die schwerste bisher:** nicht Meta-Text (§6), nicht
Konjunktiv über Behobenes (#2239), sondern eine **Bedingung im Entscheidungstext
selbst**. Ein ADR besteht wesentlich aus solchen Sätzen — „wenn X, dann gemeinsam mit
Y", „nur nach Z", „erst wenn". Ein Klassifikator, der jede Konditionalstruktur als
Vertagung liest, meldet auf ADRs strukturell falsch, und ADRs sind genau die Texte,
in denen Vertagungen am teuersten wären. Das Signal aus #2239 (Tempus/Modus) reicht
hier nicht — „gehören verschoben" steht im Indikativ Präsens. Nötig wäre die Frage,
ob das Segment ein **Subjekt mit Handlungsabsicht** hat („wir machen später") oder
eine **Eigenschaft** beschreibt („sie gehören zusammen").

gut geschriebene Texte — das ist der eigentliche Befund: der Klassifikator bestraft
Texte, die ihre Bedingungen ausformulieren.

---

## Nachtrag 2026-08-24 — PR #2265, vierte Fehlalarm-Klasse: der Verweis steht im Dokument, nicht im Segment

Gemeldet wurde in [#2265](https://github.com/achimdehnert/platform/pull/2265):

> Zitat: „blockiert sie ausdruecklich"
> Anker: keine Issue-Referenz im Segment

Der Satz lautet vollständig: *„Offener Punkt 5 (Gegenzeichnung des zweiten Owners)
blockiert sie ausdrücklich."* Er beschreibt keine Vertagung, sondern **verweist auf einen
Punkt, der im selben PR eine eigene Zeile in der Offene-Punkte-Tabelle des ADR hat** —
mitsamt Tracking-Spalte. Der Klassifikator liest das Segment, das Tracking steht eine
Tabelle weiter oben im selben Diff.

**Fehlalarm.** Nachweis, dass der Punkt getrackt war und nicht versandete: OP-5 ist am
selben Tag entschieden worden, dokumentiert im Abschnitt „Annahme" von ADR-297, mit
Verweis auf [#2263](https://github.com/achimdehnert/platform/issues/2263), wohin die
Substanz (getesteter Vertretungsweg) verschoben wurde.

**Die Klasse:** Bisher waren die Fehlalarme Meta-Text (§6), Konjunktiv über Behobenes
(#2239) und Bedingungen im Entscheidungstext (#2259). Diese vierte ist strukturell anders:
das Segment ist **korrekt als Verweis erkannt**, nur ist der Anker nicht im Segment,
sondern im Dokument. Ein Text, der seine offenen Punkte sauber in einer Tabelle führt und
im Fließtext darauf verweist, wird dafür bestraft — dieselbe Perversion wie bei #2259,
nur eine Ebene höher: dort traf es ausformulierte Bedingungen, hier trifft es
**Querverweise auf die eigene Struktur**.

Nötig wäre, den Anker-Test nicht auf das Segment, sondern auf das **Dokument** zu
erweitern: nennt der Text an anderer Stelle eine Tabellenzeile oder Überschrift, die
denselben Punkt trägt, ist er verankert.

Präzision 0,100 (vorher 0,111).

---

## Zusammenfuehrung 2026-08-30 (Konfliktaufloesung PR #2276)

Die drei Abschnitte oben lagen seit dem 2026-08-24 auf einem Branch, waehrend `main`
dieselbe Datei in einer zweiten Linie weiterschrieb (19 → 21 → 24 gepruefte Texte).
Inhaltlich ueberschneiden sie sich nicht: `main` kennt weder #2236, ADR-297, #2259
noch #2265.

**Die Zaehlerstaende sind bewusst NICHT addiert.** Der Branch zaehlte 5 → 9 → 13 → 14,
`main` unabhaengig davon bis 24 — beide zaehlen dasselbe Kalibrierfenster ab demselben
Start. Ob die hier dokumentierten Laeufe in den 24 von `main` schon enthalten sind,
laesst sich aus den Dokumenten **nicht** entscheiden; eine Summe waere eine erfundene
Zahl in genau dem Dokument, das vor erfundenen Zahlen warnt.

**Massgeblich bleibt daher der Stand aus `main`: 24 gepruefte Texte · 15 Meldungen ·
1 richtig · 14 Fehlalarme (Praezision 0,067).** Die Abschnitte oben tragen die
Fehlalarm-**Klassen** bei, nicht die Zahlen. Die Rekonstruktion des tatsaechlichen
Zaehlerstands haengt an #2469.
