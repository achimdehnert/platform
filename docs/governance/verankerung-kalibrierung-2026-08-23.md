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
