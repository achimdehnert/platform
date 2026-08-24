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
