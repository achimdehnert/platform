---
name: hnu-recherche
description: "Literatur an der Hochschule Neu-Ulm recherchieren — Bücher und E-Books im Bibliothekskatalog, begutachtete Aufsätze im Verbundindex. Anmeldung über den Hochschul-Proxy, die Filter, die aus 13 000 Treffern 200 brauchbare machen, und die Fallen, die eine leere Trefferliste vortäuschen. Nutze diesen Skill, sobald Literatur für Lehre, Gutachten, Konzepte oder Angebote gesucht wird und sie an der HNU verfügbar sein soll."
metadata:
  version: v1.0
  stand: 2026-09-10
---

# HNU-Recherche

*v1.0 · Stand 2026-09-10*

**Zweck.** Literatur finden, die Studierende und Mitarbeitende der Hochschule Neu-Ulm **tatsächlich öffnen können** —
nicht Titel, die es irgendwo gibt. Der Weg dahin ist nicht offensichtlich: Es gibt zwei getrennte Suchräume, die
Anmeldung läuft über einen Proxy mit Einmal-Sitzung, und ohne die richtigen Filter liefert jede Anfrage tausende
Treffer aus Medizin, Tourismus und Pädagogik.

## 1 — Zwei Suchräume, zwei Zwecke

| | Katalog | Verbundindex (Primo) |
|---|---|---|
| Pfad | `/vufind/Search/Results` | `/vufind/Primo/Search` |
| Inhalt | Bestand der HNU: Bücher, E-Books, Zeitschriften | Aufsätze aus den lizenzierten Datenbanken, dazu Bücher anderer bayerischer Hochschulen |
| Größenordnung | Dutzende bis Hunderte je Thema | Tausende bis Zehntausende |
| Wofür | **Lehrbücher, Standardwerke, E-Books** | **Begutachtete Aufsätze**, aktuelle Forschung |
| Format-Filter | `filter[]=~format:"eBook"` | `filter[]=rtype:"articles"` |

Wer Lehrliteratur sucht, braucht **beides**: das Buch aus dem Katalog, den Aufsatz aus dem Verbundindex.

## 2 — Anmeldung

Alles läuft über den Proxy: `https://bibkat-hnu-de.ezproxy.hnu.de/…` statt `https://bibkat.hnu.de/…`.
Die Anmeldung ist eine SAML-Kette (Proxy → Anmeldedienst der Hochschule → zurück), die ein Skript in drei Schritten
durchläuft; Zugangsdaten stehen in `~/.secrets/hnu.env` als `user:` und `password:` — **im Format Doppelpunkt, nicht
als Shell-Variablen.** Ein `source` dieser Datei schlägt fehl; lies sie mit `sed -n 's/^user: *//p'`.

Vorlage: `hnu_login.sh` (liegt neben diesem Skill). Es legt die Sitzung in einer Cookie-Datei ab; alle weiteren
Anfragen laufen mit `curl -b <cookies>`.

**Die Sitzung hält etwa eine Stunde.** Danach antwortet jede Suche mit **302** statt 200. Das ist kein leeres Ergebnis,
sondern eine abgelaufene Anmeldung — neu anmelden und weitermachen.

**Automatik-Browser kommen nicht durch.** Der Katalog steht hinter einem Bot-Schutz (Anubis); ein Playwright-Aufruf
endet mit „Zugriff verweigert" und einem Fehlercode. `curl` mit gültiger Sitzung geht durch. Wer eine Seite ansehen
will, holt sie mit `curl` und öffnet die lokale Datei.

## 3 — Die Filter, die den Unterschied machen

An die Such-Adresse angehängt, mehrfach kombinierbar:

| Filter | Wirkung |
|---|---|
| `filter[]=tlevel:"online_resources"` | nur online verfügbar — **der wichtigste Filter** |
| `filter[]=tlevel:"peer_reviewed"` | nur begutachtet |
| `filter[]=rtype:"articles"` | Aufsätze; weitere Werte: `books`, `book_chapters`, `reviews`, `dissertations`, `conference_proceedings`, `magazinearticle`, `reports`, `datasets` |
| `daterange[]=creationdate&creationdatefrom=2023&creationdateto=2026` | Jahresbereich, beide Grenzen nötig |
| `filter[]=lang:"ger"` / `"eng"` | Sprache |
| `filter[]=domain:"EBSCOhost Business Source Premier"` | **Fachfilter über die Datenbank** — für BWL zusätzlich `ABI/INFORM Global`, `Emerald Journals Perpetual Access`, `Springer Nature - Complete Springer Journals` |
| `filter[]=topic:"Strategy"` | Schlagwort aus der Facette |
| `filter[]=jtitle:"…"` | Zeitschrift |
| `filter[]=~format:"eBook"` | **nur im Katalog**: E-Books |

Suchfelder im Verbundindex: `type0[]=Subject` (Schlagwort, eng), `Title`, `Author`, `AllFields` (breit);
`op0[]=contains` oder `exact`; mehrere Felder über `bool0[]=AND|OR|NOT` verknüpfen.

**Der Fachfilter ist der Hebel.** Gemessen am 2026-09-10 für das Schlagwort „Digital strategy":

| Einschränkung | Treffer |
|---|---|
| ohne Filter | 13 700 |
| nur online | 7 942 |
| online + begutachtet | 7 791 |
| online + begutachtet + ab 2023 | 3 895 |
| dazu Business Source Premier | **268** |

Erst die letzte Zahl ist eine Liste, die man lesen kann.

## 4 — Rezept für Lehrliteratur

1. **Bücher zuerst, im Katalog.** Suche mit `~format:"eBook"`, gezielt nach den Standardwerken des Fachs mit Titel und
   Autor. Ein Standardwerk, das als E-Book vorliegt, schlägt eine neuere, schwächere Alternative.
2. **Dann Aufsätze, im Verbundindex.** `online_resources` + `peer_reviewed` + Jahresbereich + eine Wirtschaftsdatenbank.
   Für ein Seminar reichen zwei bis drei Aufsätze je Sitzung.
3. **Je Titel die Datensatzseite öffnen** (`/vufind/Record/<ID>`) und Verlag, Auflage, Schlagworte lesen. Der Satz,
   warum ein Titel passt, kommt von dort — nicht aus dem Titel geraten.
4. **Die Katalognummer mitnehmen** (`DE-604.BV…`). Der Link `https://bibkat.hnu.de/vufind/Record/<ID>` führt nach
   Anmeldung direkt zum Volltext und ist die stabile Referenz für Literaturlisten.

## 5 — Die wichtigste Prüfung: gehört die Lizenz uns?

**Der Katalog zeigt auch E-Books anderer bayerischer Hochschulen.** Sie sehen aus wie jeder andere Treffer, tragen
dieselbe Formatangabe und dieselbe Katalognummer — aber Angehörige der HNU kommen nicht hinein. Bei einer Auswahl von
zwanzig Titeln für eine Vorlesung waren am 2026-09-10 **fünf** davon betroffen, darunter drei bekannte Standardwerke.
Ohne die Prüfung fällt das erst auf, wenn ein Teilnehmender den Titel öffnen will.

**Der Beleg ist die Zielseite, nicht der Link.** Auf der Datensatzseite stehen die Volltext-Wege als
`ezproxy.hnu.de/login?qurl=<Ziel>` — oft **mehrere, bis zu neun**, und die meisten davon gehören anderen Häusern.
Ein Titel ist verfügbar, sobald **ein einziges** Ziel durchgeht. Also jedes Ziel über den Proxy aufrufen und auf der
geladenen Seite nach dem Satz **„Access provided by Hochschule für angewandte Wissenschaften Neu-Ulm"** suchen.
Steht er da, gehört die Lizenz uns.

**Am Pfad allein darf man es nicht entscheiden.** Ein Pfad `ebookcentral.proquest.com/lib/<kürzel>/` mit fremdem
Kürzel — `hwr`, `fhws`, `th-wildau`, `erlangen`, `fuberlin-ebooks` — ist ein Warnzeichen, aber kein Urteil: Baines,
*Servitization Strategy*, trägt genau so einen fremden Pfad **und** einen Springer-Weg, über den die HNU-Kennung
sauber durchkommt. Wer nur den Pfad liest, wirft das Buch zu Unrecht raus.

**Umgekehrt ist auch eine Verlagsadresse kein Freibrief.** Bei EBSCO (`search.ebscohost.com`) landet man nach dem
Proxy auf einer Seite, die die Hochschule nennt, ihren Inhalt aber erst per Nachladen aufbaut — ob der Volltext
freigeschaltet ist, steht dort nicht im Quelltext. Solche Fälle sind **ungeklärt**, nicht bestätigt: entweder von
Hand im Browser ansehen oder einen Titel nehmen, der eindeutig durchgeht.

Eindeutig unsere sind erfahrungsgemäß `doi.org` (Springer, Haufe), `www.wiso-net.de`, `link.springer.com`,
`beck-online.beck.de` und `elibrary.kohlhammer.de`.

**Prüfe jeden Titel einzeln, bevor er in eine Liste kommt.** Ein Aufruf je Ziel, ein Blick auf den Zugangssatz —
Sekunden, und der Unterschied zwischen einer Leseliste und einer Enttäuschung.

## 6 — Weitere Fallen

- **302 ist keine Null.** Eine Suche ohne Treffer ist erst dann ein Ergebnis, wenn dieselbe Suche ohne Filter Treffer
  liefert. Sonst ist die abgelaufene Sitzung der Filter, nicht die Welt.
- **`rtype:"books"` im Verbundindex bringt fast nichts** — er ist ein Aufsatzindex. Bücher gehören in den Katalog.
- **Ohne Fachfilter dominiert das Fremde.** Bei „digital" kommen Medizin, Tourismus, Pädagogik und Sportwissenschaft
  zuerst; die Formatfacette trennt nach Art, nicht nach Fach.
- **Die Facettenliste ist zweispaltig aufgebaut** (Wert und Anzeigename in getrennten Stellen des Quelltexts). Wer
  beide mit einem Suchmuster einsammelt, bekommt sie gegeneinander verschoben. Getrennt auslesen und über die
  Reihenfolge zuordnen, oder gleich den Wert nehmen.
- **Kein Titel ohne Katalognummer** in eine Literaturliste. Ohne sie ist später nicht prüfbar, ob es ihn noch gibt.
- **Zugangsdaten nie ausgeben.** Kein `env`-Dump, kein `cat` der Geheimnisdatei; die Werte gehören über die
  Standardeingabe ins Kommando, nie in die Kommandozeile.

## 7 — Urheberrecht bei Folien und Skripten

Abbildungen aus Büchern und Aufsätzen dürfen in Lehrmaterial, wenn der Teilnehmerkreis abgegrenzt ist und die Quelle
genannt wird. Liegt das Material auf einer offen erreichbaren Webseite, trägt diese Schranke nicht. Vor dem Übernehmen
einer fremden Abbildung also prüfen, wo das fertige Deck landet — und im Zweifel eine eigene Grafik zeichnen.

## 8 — Werkzeuge

Neben diesem Skill liegen drei Skripte, die zusammenarbeiten:

- `hnu_login.sh` — Anmeldung, legt die Cookie-Datei an
- `bibkat_suche.py` — Ergebnisliste des Katalogs auswerten (Titel, Autoren, Jahr, Format, Katalognummer)
- `bibkat_ebooks.py` — dieselbe Suche mit E-Book-Filter und Jahresgrenze über mehrere Themen

Für den Verbundindex genügt dieselbe Auswertung; die Ergebnisliste ist gleich aufgebaut.
