---
concept_id: KONZ-platform-035
title: Deckungsausweis — Vollständigkeit von Sachverhalts-Darlegungen aus E-Mail
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []          # kein Klickdummy; betrifft Werkzeug- und Antwortkonvention (begründet leer)
adr_threshold: Amendment   # ADR-284 §2 dehnt den Coverage-Contract auf Live-Antworten aus
review_by: 2026-10-27
kill_criteria: "Eine Sachverhalts-Darlegung lässt bis 2026-09-30 eine relevante Mail aus, die INNERHALB des ausgewiesenen Deckungsbereichs lag → Konzept verfehlt seinen Zweck, wird verworfen statt geflickt. Ausserhalb des Bereichs = kein Fehlschlag, sondern eine Scope-Entscheidung."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: docs/adr/ADR-284-mail-intelligence-action-system.md, commit_or_pr: "2c3b2f11/main", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-286-mail-agent-crypto-shredding-derived-index.md, commit_or_pr: "#1488", opened_in_session: true}
  - {claim_id: C3, source_path: tools/mail_agent/read_mail.py, commit_or_pr: "#1487", opened_in_session: true}
  - {claim_id: C4, source_path: tools/mail_agent/graph_mail.py, commit_or_pr: "#1485", opened_in_session: true}
  - {claim_id: C5, source_path: tools/mail_agent/vorgang.py, commit_or_pr: "#1490", opened_in_session: true}
  - {claim_id: C6, source_path: .windsurf/workflows/mailcheck.md, commit_or_pr: "#1485", opened_in_session: true}
  - {claim_id: C7, source_path: "session-run", commit_or_pr: "vorgang.py --topic SUBJECT 2026-07-27", opened_in_session: true}
created: 2026-07-27
---

# KONZ-platform-035: Deckungsausweis

**Tier T3.** Die Konvention wirkt über die org-weit verteilten Mail-Skills (`mailcheck`,
`briefing`, `iil-mail`, `read-mail`, `organize-mail`) in alle Repos, und sie verschiebt den
Datenschutz-Perimeter: Ein Pflicht-Scope über *alle* Ordner berührt mehr personenbezogene Daten
als der heutige Zuschnitt. Beides sind T3-Trigger. Zusätzlich amendiert sie einen `accepted`
ADR. Der bei T3 vorgesehene Agenten-Fan-out entfällt zugunsten einer **externen Zweitmeinung**
(`/adr-handoff-extern`) — Owner-Entscheid, und die stärkere Prüfung von beiden.

---

## 1 Executive Summary

Am 2026-07-27 sind an einem Tag **drei** Sachverhalts-Darlegungen unvollständig gewesen, und
zwar jede aus einem anderen Grund. Keiner davon war Nachlässigkeit; jeder war eine Abfrage, die
plausibel aussah und weniger maß, als sie zu messen schien. Der teuerste Fall führte dazu, dass
eine betroffene Person eine **zweite** Authentifizierungsanfrage in einem laufenden Art.-17-
Verfahren erhielt.

**Vorschlag:** Jede Sachverhalts-Darlegung trägt einen maschinell erzeugten **Deckungsausweis** —
welche Frage, welche Konten, wie viele Ordner, welches Zeitfenster, welche Kriterien mit je
eigener Trefferzahl, wie viel geprüft, und ausdrücklich: **was nicht gedeckt war**. Ohne ihn gilt
die Darlegung als unvollständig.

**Der Kern ist eine Umkehrung der Beweislast.** Heute behauptet die Antwort implizit
Vollständigkeit und niemand kann sie prüfen. Künftig weist sie ihre Grenzen aus, und die
Vollständigkeit ergibt sich — oder eben nicht — aus einer nachrechenbaren Angabe.

**Was das Konzept ausdrücklich nicht verspricht:** Relevanz. Es sichert die **Deckung**. Welche
der gedeckten Nachrichten zum Sachverhalt gehören, entscheidet der Mensch. Diese Grenze ist keine
Schwäche des Entwurfs, sondern ein Ergebnis (§7.2).

---

## 2 Scope & Evidenzbasis

**Geöffnet in dieser Session** (C1–C7): ADR-284 (Coverage-Contract, Scope-Tabelle), ADR-286 §4.9
(Vorgangs-Graph, deterministische Signale), die drei Mail-Werkzeuge samt der heute an ihnen
vorgenommenen Änderungen, der `/mailcheck`-Skill, und ein Live-Lauf der ordnerübergreifenden
Suche.

**Nicht geöffnet und deshalb Hypothese:** wie sich der Vorschlag auf Postfächer verhält, die
deutlich größer sind als die gemessenen (46.065 Nachrichten / 110 Ordner), und ob die
Laufzeitmessung auf anderen Servern trägt.

**Was ausdrücklich außerhalb liegt:** der Index aus ADR-284 Phase 1 (existiert nicht),
semantische Relevanzbestimmung (§7.2), und jede Persistenz — dieses Konzept fügt kein
speicherndes Element hinzu.

---

## 3 Infrastruktur-Fit

Die Bausteine sind zum großen Teil **heute schon da** — sie greifen nur nicht ineinander und
niemand verpflichtet sie zu einer gemeinsamen Aussage.

| Baustein | Ort | Stand |
|---|---|---|
| Filterfreie Ordner-Aufzählung | `graph_mail --find --all` (C4) | vorhanden, seit #1485 |
| Laute Warnung bei stiller Verwerfung | `graph_mail._match_messages` (C4) | vorhanden, seit #1485 |
| Nenner in jeder Liste | `read_mail._bilanz` (C3) | vorhanden, seit #1487 |
| Ordnerübergreifende Sachsuche | `vorgang.py --topic` (C5) | vorhanden, seit #1490 |
| Warnung zur Trefferqualität | `vorgang.such_hinweis` (C5) | vorhanden, seit #1490 |
| Vorgangs-Zuordnung über Ordnerbaum | `vorgang.py --suggest` (C5) | vorhanden, seit #1490 |
| **Gemeinsame Deckungsaussage über all das** | — | **fehlt** |
| **Verpflichtung, sie auszuweisen** | — | **fehlt** |

**Root-Cause-Prüfung (Pflicht, gegen Konzepte für gelöste Probleme):** ADR-284 §2 Nr. 1 führt
**bereits** einen Coverage-Contract — „100 % der für den Connector sichtbaren Nachrichten in
explizit benannten Accounts + Ordner-Scope zu einem ausgewiesenen Quell-Watermark". Der Mechanismus
ist also erfunden. Aber §3 bindet ihn ausdrücklich auf **Phase 1 = den Index**, und die
Scope-Tabelle führt Phase 0–4 getrennt auf. Die **Live-Antwort** fällt in keine dieser Phasen.

Damit ist die Lage präzise: **Der Vertrag existiert, er bindet nur das Falsche.** Alle drei
Fehlschläge traten in Live-Antworten auf — der Index existiert noch gar nicht. Ein Konzept ist
nötig, aber es ist ein **Amendment**, kein Neubau (§8, §12).

---

## 4 Steelman

Die stärkste Fassung des Vorschlags argumentiert nicht mit Ordnung, sondern mit **Haftung**.

Wer als Datenschutzbeauftragter, Betreuer oder Vertragspartner eine Auskunft gibt, haftet für
ihre Richtigkeit. Eine Auskunft aus unvollständigem Material ist falsch, auch wenn jeder einzelne
Satz darin zutrifft. Das ist der Unterschied zwischen einem Irrtum und einem Fehler: Der Irrtum
ist eine falsche Aussage, der Fehler ein Verfahren, das falsche Aussagen erzeugt, ohne dass es
auffällt.

Der Deckungsausweis verwandelt eine **unprüfbare Zusicherung** („ich habe alles angesehen") in
eine **nachrechenbare Angabe** („110 Ordner, 46.065 Nachrichten, Kriterium Betreff, 11 Treffer,
Papierkorb eingeschlossen"). Zwei Dinge folgen daraus, die keine Sorgfaltsermahnung leisten kann:

Erstens wird eine **Lücke sichtbar, ohne dass jemand sie sucht**. Wer liest, dass 346 von 846
Nachrichten nicht angesehen wurden, weiß es — ohne den Verdacht gehabt zu haben.

Zweitens wird die Aussage **fremdprüfbar**. Ein Dritter — Aufsichtsbehörde, Mandant, Kollege —
kann den Deckungsbereich beurteilen, ohne die Arbeit zu wiederholen. Das ist genau der Schritt,
den ADR-284 für den Index bereits gegangen ist: Verträge statt Adjektive.

Und es ist wohlfeil: Die Werkzeuge messen die Zahlen ohnehin. Heute werfen sie sie weg.

---

## 5 Konzeptdefinition

### 5.1 Die vier Lücken

Der Kern des Vorschlags ist eine **Taxonomie**, weil „unvollständig" vier verschiedene Dinge
heißt, die vier verschiedene Gegenmittel brauchen. Alle vier sind an einem Tag real aufgetreten.

| # | Lücke | Was schiefgeht | Realfall 2026-07-27 | Mechanisch lösbar? |
|---|---|---|---|---|
| **L1** | **Quellen-Lücke** | Der Suchraum ist enger als der Sachverhalt | Darlegung aus INBOX allein — 3 von 11 Nachrichten; drei der fehlenden lagen im **Papierkorb** (C7) | **ja** — Scope ausweisen und erzwingen |
| **L2** | **Kriterien-Lücke** | Die Abfrage kann nicht treffen, was existiert | Platzhalter `--from "@"` verwarf 21 von 34 (Exchange-X.500-DN ohne `@`) (C4) | **ja** — mehrere Kriterien + Kalibrierung |
| **L3** | **Sichtbarkeits-Lücke** | Das Ergebnis wirkt vollständig, weil der Nenner fehlt | `--list N` gab N Zeilen und sonst nichts (C3) | **ja** — Nenner ist Pflicht |
| **L4** | **Relevanz-Lücke** | Gefunden, aber nicht als zugehörig erkannt | dieselbe Nachricht gehört zu zwei Vorgängen (ADR-286 §4.9) | **nein** — s. §7.2 |

L1–L3 sind **Verfahrensfehler** und vollständig mechanisierbar. L4 ist ein **Urteilsproblem** und
bleibt beim Menschen. Ein Konzept, das alle vier zu lösen verspricht, verspricht zu viel; eines,
das L1–L3 löst und L4 sichtbar ausweist, ist ehrlich und ausreichend.

### 5.2 Der Deckungsausweis

Ein maschinell erzeugter Block, der **vor** der Trefferliste steht — nicht als Fußnote, weil
Fußnoten nach dreimal Lesen unsichtbar werden.

| Feld | Warum |
|---|---|
| **Frage** | Vollständigkeit ist ohne Frage undefiniert (§7.1). Der Ausweis nennt sie, damit später prüfbar ist, wonach gesucht wurde |
| **Konten** | „alle" ist ohne Aufzählung eine Behauptung |
| **Ordner: durchsucht / vorhanden** | die Quellen-Lücke wird zur Zahl |
| **Zeitfenster** | ein Fenster ist ein Ausschluss und gehört benannt |
| **Kriterien, je mit eigener Trefferzahl** | ein Kriterium, das **0** liefert, ist ein Befund — im Gesamtergebnis wäre es unsichtbar |
| **geprüft / vorhanden** | Trunkierung wird sichtbar |
| **Nicht gedeckt** | die eigentliche Aussage: was ausgeschlossen war und warum |
| **Erzeugt von** | maschinell oder von Hand — beides erlaubt, aber unterscheidbar |

### 5.3 Die fünf Regeln

**R-1 — Pflicht-Scope ist alles.** Alle Ordner aller benannten Konten, **einschließlich Gesendet
und Papierkorb**. Ausschlüsse sind zu **benennen**, nicht zu unterstellen. Belegt durch L1: drei
der elf Nachrichten lagen im Papierkorb, und gelöscht heißt dort nicht irrelevant, sondern
meistens *erledigt* — also gerade die Information über den Stand.

**R-2 — Mehrere unabhängige Kriterien.** Thread-Header · Betreff · Beteiligte · zitierter Text ·
Anhangs-Prüfsumme. Jedes mit eigener Trefferzahl. Der Wert liegt nicht in der größeren Treffermenge,
sondern in der **Divergenz**: Findet ein Kriterium nichts, wo ein anderes trifft, ist das ein
Befund über die Abfrage.

**R-3 — Kalibrierung vor Vertrauen.** Vor einer Vollständigkeitsaussage muss die Abfrage ein
Element zurückgeben, von dem feststeht, dass es enthalten ist. Erscheint es nicht, ist **nicht die
Menge leer, sondern die Abfrage kaputt**. Genau dieser eine Test hätte L2 verhindert.

**R-4 — Über-Einschluss vor Unter-Einschluss.** Die Kosten sind asymmetrisch (§7.3): eine
überflüssige Nachricht kostet Aufmerksamkeit, eine fehlende eine falsche Auskunft. Im Zweifel
aufnehmen und als unsicher kennzeichnen.

**R-5 — Maschinell erzeugt.** Ein handgeschriebener Ausweis ist eine Behauptung über eine
Behauptung. Handbetrieb bleibt erlaubt, wird aber als solcher ausgewiesen.

---

## 6 Adversariale Analyse

### 6.1 Advocatus Diabolus

**Wo entsteht eine Doppelquelle?** Nirgends — der Ausweis beschreibt eine Abfrage und speichert
nichts. Er ist so flüchtig wie die Antwort, zu der er gehört. *Aber:* Sobald jemand ihn
archiviert („Beleg für die Aufsicht"), entsteht ein Artefakt mit Aussagekraft über einen
Zeitpunkt — und damit ein Kandidat für Drift. → §12 REC-6.

**Wo wird SSoT nur behauptet?** Beim Wort „alle". Es gilt nur für Konten, auf die Zugriff
besteht. Der HNU-Kanal läuft nach Owner-Entscheid vom 2026-07-27 bei Variante C — durchsuchbar,
aber nicht zuordenbar. Wer „alle Ordner" liest und „alle Mails der Welt" versteht, irrt. → Der
Ausweis nennt die Konten **namentlich**, nicht als Menge.

**Wo wird ein Werkzeug faktisch zur Boundary?** Wird der Ausweis Voraussetzung, ist das erzeugende
Werkzeug kritischer Pfad: Fällt es aus, gibt es keine Darlegung mehr. → R-5 lässt Handbetrieb zu,
gekennzeichnet. Die Alternative — Ausfall bedeutet Stillstand — wäre schlechter als das Problem.

**Wo manuelle Pflicht ohne Enforcement?** **Hier ist die härteste Stelle.** „Ich lege keinen
Sachverhalt ohne Ausweis vor" ist eine Zusage. Ein Hook kann erkennen, *dass* ein Ausweis dasteht;
seine **Richtigkeit** kann er nicht prüfen. Damit ist dies ein **Review-Gate, kein Exit-Code** —
und das steht hier, statt es als geschlossen zu verkaufen.

**Wo ist „sichtbar machen" schwächer als „verhindern"?** Beim Scope. Sichtbar zu machen, dass der
Papierkorb fehlte, hilft nur, wenn jemand hinsieht. Deshalb ist R-1 als **Pflicht** formuliert und
das Weglassen als begründungspflichtige Abweichung — nicht umgekehrt.

**Wo kann man formal erfüllen und praktisch umgehen?** Indem man den Scope eng wählt und korrekt
ausweist: formal sauber, praktisch nutzlos. Dagegen hilft **nur**, dass das Kill-Kriterium an
**Auslassungen** misst und nicht am Vorhandensein des Ausweises (§13).

**Wo wird ein bestehendes Problem verschlimmert?** Bei der Laufzeit (R2 in §11) und beim
Datenschutz: Ein Pflicht-Scope über alle Ordner **berührt mehr personenbezogene Daten** als der
heutige Zuschnitt. Datenschutzfreundlich ist nicht automatisch, was weniger anfasst — aber diese
Abwägung gehört ausgesprochen, nicht unterschlagen. → §7.4.

### 6.2 Maintainer-2028

Wer das in zwei Jahren liest, muss zwei Dinge erkennen.

Erstens: Der Ausweis dokumentiert **nicht Arbeit**, sondern macht **eine Fehlerklasse unmöglich** —
die stille Teilmenge, die wie eine Vollmenge aussieht. Wird er zur Pflichtübung ohne Bezug zur
Frage, ist er zu **streichen**, nicht zu erweitern. Die Frage an ihn lautet nie „ist er da",
sondern „hätte er den Fehler gefangen".

Zweitens: Die vier Lücken aus §5.1 sind der eigentliche Beitrag. Wer später etwas verbessern
will, sollte prüfen, **welche der vier** er adressiert. Ein Vorschlag, der keiner zuzuordnen ist,
löst vermutlich ein anderes Problem.

---

## 7 Deep-Dive

### 7.1 Vollständigkeit ist relativ zu einer Frage

„Alle relevanten Mails" ist ohne Frage nicht definiert. Dieselbe Nachricht ist relevant für
*„was habe ich diesem Gegenüber zugesagt"* und irrelevant für *„wer wartet auf Rückmeldung"*.
Relevanz ist keine Eigenschaft der Nachricht, sondern eine **Relation zwischen Nachricht und
Frage**.

Daraus folgt unmittelbar der Aufbau des Ausweises: Er muss die **Frage mitführen**. Ein Ausweis
ohne Frage ist so leer wie ein Messergebnis ohne Einheit. Und es folgt, dass dieselbe Mailmenge
für zwei Fragen **unterschiedlich vollständig** sein kann — was nicht paradox ist, sondern der
Normalfall.

### 7.2 Warum L4 unentscheidbar bleibt — und warum das kein Defekt ist

Um zu wissen, ob eine Nachricht zu einem Sachverhalt gehört, muss man sie **lesen und verstehen**.
Alle zu lesen wäre die systematische Inhaltsauswertung, die im Art.-14-Nachtrag zur DSFA
ausdrücklich ausgeschlossen ist — sie würde die Rechtfertigung entwerten, auf der die Verarbeitung
ruht.

Damit steht das Konzept vor einer **echten Unmöglichkeit**, nicht vor einer Bequemlichkeit:

> Vollständige Relevanz erforderte vollständige Inhaltskenntnis. Vollständige Inhaltskenntnis ist
> ausgeschlossen. Also ist vollständige Relevanz nicht erreichbar.

Die einzig redliche Konsequenz ist, **Deckung von Relevanz zu trennen** und nur erstere zu
garantieren. Der Ausweis sagt: „In diesem Bereich wurde vollständig gesucht; ob alles Gefundene
gehört und ob außerhalb noch etwas liegt, ist Urteilssache." Das ist weniger, als der Wunsch
hergibt — und mehr, als heute jemand belegen kann.

Ein Nebeneffekt verdient Beachtung: Weil L4 beim Menschen bleibt, wird der Deckungsausweis
**gerade dadurch belastbar**. Er verspricht nichts, was von einer Maschinenbewertung abhängt.

### 7.3 Die Kostenasymmetrie, beziffert

| Fehler | Kosten | Realfall |
|---|---|---|
| Eine Nachricht **zu viel** | Aufmerksamkeit für einige Sekunden | — |
| Eine Nachricht **zu wenig** | falsche Auskunft, verschenkte Frist, doppelte Handlung gegenüber Dritten | Am 2026-07-27 erhielt eine betroffene Person eine **zweite** Authentifizierungsanfrage in einem laufenden Art.-17-Verfahren, weil eine gesendete Mail unsichtbar geblieben war |

Das Verhältnis ist nicht knapp, sondern um Größenordnungen asymmetrisch. Jede Abwägung zwischen
Präzision und Vollständigkeit ist deshalb zugunsten der Vollständigkeit zu entscheiden — R-4 ist
keine Vorsichtsregel, sondern die Konsequenz aus dieser Tabelle.

### 7.4 Der Datenschutz-Einwand gegen den eigenen Vorschlag

Ein Pflicht-Scope über alle Ordner **liest mehr** als ein enger. Wer Datenminimierung ernst nimmt,
muss diesen Vorschlag unbequem finden.

Drei Punkte zur Entkräftung, und ein verbleibender Rest:

1. **Anlassbezogen, nicht systematisch.** Es läuft nur auf eine konkrete Frage und danach nie
   wieder. Der Art.-14-Nachtrag schließt „gezielte und systematische Anreicherung oder Auswertung"
   aus — beides trifft nicht zu.
2. **Nichts wird gespeichert.** Es entsteht kein abgeleitetes Artefakt, das nach ADR-286 §4.4
   einer Löschkaskade unterläge.
3. **Der Zugriff bestand ohnehin.** Es werden keine Daten erschlossen, die vorher unzugänglich
   waren; es wird nur vollständiger gelesen, was der Verantwortliche in seinem eigenen Postfach
   liegen hat.

**Verbleibender Rest, ehrlich:** Häufigkeit bleibt ein Faktor. Wird die Vollsuche zur Gewohnheit
für jede Kleinigkeit, nähert sie sich in ihrer Wirkung dem systematischen Lesen an — auch wenn
jeder Einzellauf begründet ist. Dagegen gibt es keine technische Schranke, nur Maß. → §11 R3.

### 7.5 Warum ein Index das Problem nicht erledigt

Der naheliegende Einwand lautet: Baut Phase 1 aus ADR-284, dann erübrigt sich das.

Er trägt nicht. Ein Index deckt, **was er indexiert hat** — die Frage „war der Scope vollständig"
stellt sich dort **identisch**, nur eine Ebene früher und mit dem Zusatzrisiko, dass eine
veraltete Deckung wie eine aktuelle aussieht. ADR-284 §9 nennt das selbst: *„Ein still veralteter
Index (falsche 100 %-Sicherheit) ist schlimmer als keiner."*

Der Deckungsausweis ist deshalb **kein Provisorium bis zum Index**, sondern das, was ein Index
ohnehin bräuchte. Wird Phase 1 gebaut, wandert der Ausweis mit — und wird dort um den
Watermark-Zeitpunkt reicher.

---

## 8 Alternativen

| # | Alternative | Bewertung |
|---|---|---|
| 1 | **Freitext-Vorbehalt** an jede Antwort („nicht abschließend geprüft") | Nicht prüfbar, deshalb wirkungslos — die Sorte Disclaimer, die man nach dreimal Lesen überliest. Die heutigen Fehlschläge hätten ihn getragen und wären trotzdem falsch gewesen: Sie hatten keine fehlende Warnung, sie hatten falsche Zahlen. |
| 2 | **Erst den Index bauen** (ADR-284 Phase 1) | Löst es nicht (§7.5) und verschiebt es um Monate. Bis dahin bleibt jede Antwort ungeregelt — in genau dem Zeitraum, in dem die Fehler auftreten. |
| 3 | **Nur Werkzeuge härten, keine Konvention** | Wurde heute gemacht (#1485/#1487/#1490) und **reicht nicht**: Das dritte Versagen (L1) geschah *nach* den ersten beiden Härtungen, mit gehärteten Werkzeugen, weil niemand verpflichtet war, sie vollständig einzusetzen. Der Beleg gegen diese Alternative ist derselbe Tag. |
| 4 | **Vier-Augen-Prinzip** statt Ausweis | Verdoppelt Aufwand und Fehlerquelle: Ein zweiter Mensch mit derselben Abfrage sieht dieselbe Teilmenge. Gegen L2 wirkungslos. |

---

## 9 Out-of-the-Box

**9.1 — Negativ-Nachweis statt Positiv-Behauptung.** Der Ausweis könnte seinen Schwerpunkt
umkehren: nicht „das habe ich gefunden", sondern **„das habe ich nicht durchsucht"** als erste
Zeile. Psychologisch wirksamer, weil eine Aufzählung von Lücken sich nicht überlesen lässt wie
eine Zahl. Kostet nichts und ist wahrscheinlich die bessere Darstellung — sollte im Pilot gegen
die Standardform gemessen werden.

**9.2 — Divergenz zweier Wege als eigenständiges Signal.** Dieselbe Frage über zwei unabhängige
Kriterien laufen lassen und **nur die Differenz** melden. Stimmen beide überein, ist das ein
starkes Deckungsindiz; weichen sie ab, ist die Abweichung der interessanteste Teil des Ergebnisses.
Das ist billiger als eine perfekte Einzelabfrage und aussagekräftiger.

**9.3 — Der Ausweis als Artefakt am Vorgang.** Statt im Chat zu verpuffen, könnte er als Notiz am
Vorgang landen — dann ist Monate später prüfbar, auf welcher Grundlage entschieden wurde. Das ist
für regulierte Vorgänge (Art. 17, Fristen) erheblich, erzeugt aber ein persistentes Artefakt mit
Personenbezug und wäre eine eigene Entscheidung (§6.1, REC-6).

**9.4 — Die Lückenliste als Arbeitsvorrat.** Was keine Zuordnung fand, ist nicht Abfall, sondern
die Liste der ungeklärten Fälle. `vorgang.py --suggest` weist sie bereits aus (164 von 200 im
Livelauf). Sie ist der natürliche Einstieg in die nächste Aufräumrunde — der Ausweis erzeugt
damit als Nebenprodukt eine Aufgabenliste.

**9.5 — Kalibrierung als stehender Kanarienvogel.** Eine je Datenquelle hinterlegte, bekannte
Nachrichten-ID, die jede Vollerhebung zurückgeben **muss**. Fehlt sie, bricht der Lauf ab, statt
ein plausibles Teilergebnis zu liefern. Das verwandelt R-3 von einer Gewohnheit in einen
Mechanismus — und ist der einzige Vorschlag hier, der L2 **verhindert** statt sie sichtbar zu
machen.

---

## 10 Befunde

| ID | Befund | Evidenz |
|---|---|---|
| B1 | Der Coverage-Contract aus ADR-284 §2 bindet nur Phase 1 (Index); die Live-Antwort ist ungeregelt | E1 (C1) |
| B2 | Alle drei Fehlschläge traten in Live-Antworten auf — der Index existiert nicht | E3 (C3/C4/C7) |
| B3 | Ein Platzhalter-Filter verwarf 21 von 34 gesendeten Nachrichten still (X.500-DN ohne `@`) | E3 (C4) |
| B4 | Eine Trefferliste ohne Nenner ist von einer Vollerhebung nicht unterscheidbar | E3 (C3) |
| B5 | Ein Sachverhalt verteilte sich über **fünf** Ordner inkl. Papierkorb; die Darlegung aus INBOX zeigte 3 von 11 | E3 (C7) |
| B6 | Die Feldwahl entscheidet mehr als der Suchbegriff: 0 / 327 / 678 Treffer für denselben Term | E3 (C5) |
| B7 | Gehärtete Werkzeuge allein genügen nicht — B5 geschah **nach** der Härtung, mit den gehärteten Werkzeugen | E3 (C3/C4 vs. C7, zeitliche Abfolge) |
| B8 | Eine ordnerübergreifende Suche über 110 Ordner / 46.065 Nachrichten dauert 10–77 s je nach Feld | E3 (C5, Live-Messung) |

---

## 11 Top-5-Risiken

| # | Risiko | Gegenmaßnahme |
|---|---|---|
| R1 | Der Ausweis wird Formalie: vorhanden, ungelesen, mit falschen Zahlen | R-5 (maschinell) + Kill-Gate misst **Auslassungen**, nicht Ausweis-Präsenz |
| R2 | Laufzeit macht den Pflicht-Scope unattraktiv, er wird faktisch umgangen | Kosten **ausweisen** statt Scope kürzen; Kürzung ist eine benannte, begründete Ausnahme — nie ein stiller Default |
| R3 | Häufige Vollsuchen nähern sich in der Wirkung dem systematischen Lesen an | Anlassbezogenheit ist Bedingung, nicht Empfehlung; kein Hintergrundlauf, keine Persistenz (§7.4) |
| R4 | Das erzeugende Werkzeug wird kritischer Pfad; sein Ausfall blockiert jede Darlegung | Handbetrieb bleibt zulässig, wird als solcher gekennzeichnet (R-5) |
| R5 | Scheinsicherheit: Der Ausweis suggeriert Vollständigkeit, obwohl er nur Deckung belegt | §7.2 ist Pflichtbestandteil jeder Einführung; der Ausweis nennt die Relevanzgrenze im Text, nicht nur in diesem Konzept |

---

## 12 Empfehlungen

| # | Empfehlung | Konkret |
|---|---|---|
| REC-1 | Ausweis-Erzeugung als reine Funktion | `deckungsausweis(frage, konten, ordner_gesamt, ordner_durchsucht, kriterien: dict[str,int], fenster, nicht_gedeckt: list[str], erzeuger) -> str` in `tools/mail_agent/vorgang.py` — ohne IMAP, damit ohne Postfach testbar |
| REC-2 | Ausgabe **vor** der Trefferliste | in `cmd_topic` und `cmd_show`; nicht als Fußnote (§5.2) |
| REC-3 | Zweites Kriterium ergänzen | `cmd_topic` zusätzlich über Beteiligte, mit **getrennter** Trefferzahl — Divergenz ist das Signal (§9.2) |
| REC-4 | Kalibrierung als Kommando | `vorgang.py --calibrate <message-id>`: prüft, ob eine bekannt vorhandene Nachricht von der Abfrage zurückgegeben wird; scheitert laut statt still (§9.5) |
| REC-5 | Skill-Pflicht verankern | Abschnitt in `mailcheck.md`, `briefing.md`, `iil-mail.md`: Sachverhalts-Darlegung ohne Deckungsausweis gilt als unvollständig |
| REC-6 | Persistenz **nicht** im MVC | Der Ausweis als Vorgangs-Notiz (§9.3) ist ein eigenständiger Entscheid mit Personenbezug — bewusst vertagt, nicht vergessen |
| REC-7 | ADR-284 amendieren | §2 Nr. 1 um den Satz erweitern, dass der Coverage-Contract auch für Live-Antworten gilt, nicht nur für den Index |

---

## 13 Entscheidung + Kill-Gate

**Entscheidung:** Konzept **annehmen und pilotieren** — REC-1 bis REC-5 umsetzen, REC-6 vertagen,
REC-7 als Amendment nachziehen. Der Pilot läuft auf den eigenen Postfächern, ohne
Fremdbeteiligung, und kostet keine Infrastruktur.

**Kill-Gate (messbar):** Legt eine Sachverhalts-Darlegung bis **2026-09-30** eine relevante Mail
nicht vor, die **innerhalb des ausgewiesenen Deckungsbereichs** lag, hat das Konzept seinen Zweck
verfehlt und wird **verworfen, nicht geflickt**.

**Ausdrücklich kein Fehlschlag:** eine fehlende Mail **außerhalb** des ausgewiesenen Bereichs.
Dann hat der Ausweis funktioniert und der Scope war zu eng — das ist eine Entscheidung, kein
Defekt. Diese Unterscheidung ist der Kern der Messbarkeit; ohne sie misst das Gate Zufall.

**Exception-Budget:** einmalige Verlängerung bis **2026-10-31**, danach ohne weitere.

| Kriterium | Status | Beleg |
|---|---|---|
| K1 Ausweis wird maschinell erzeugt und erscheint vor der Trefferliste | offen | — |
| K2 Pflicht-Scope schließt Gesendet und Papierkorb ein | offen | — |
| K3 Mindestens zwei unabhängige Kriterien mit getrennter Trefferzahl | offen | — |
| K4 Kalibrierung existiert und wird vor Vollständigkeitsaussagen benutzt | offen | — |
| K5 Keine Auslassung innerhalb des ausgewiesenen Bereichs bis 2026-09-30 | offen | — |
| K6 Relevanzgrenze (§7.2) steht im Ausweis-Text, nicht nur im Konzept | offen | — |

### 30/60/90

**Bis Tag 30:** REC-1 bis REC-3 gebaut, Ausweis erscheint in `--topic` und `--show`. Erste zehn
realen Darlegungen mit Ausweis; K1–K3 erfüllt oder begründet offen.

**Bis Tag 60:** REC-4 (Kalibrierung) und REC-5 (Skill-Pflicht) live. Messung: Wie oft wich der
Deckungsbereich vom Pflicht-Scope ab, und war die Abweichung jedes Mal benannt? K4, K6.

**Bis Tag 90:** Entscheid über REC-6 (Persistenz) und über die Darstellungsform aus §9.1
(Negativ-Nachweis vs. Standardform) anhand der Pilot-Erfahrung. K5 abschließend — oder Sunset
nach Kill-Gate.

---

## Threshold

**Amendment an ADR-284**, kein neuer org-weiter ADR. Der Coverage-Contract existiert bereits als
Entscheidung (§2 Nr. 1); ihn auf Live-Antworten auszudehnen ist eine Erweiterung nach bestehendem
Muster. Ein eigener ADR wäre Überbau — die Architekturentscheidung ist getroffen, nur ihr
Geltungsbereich war zu eng.
