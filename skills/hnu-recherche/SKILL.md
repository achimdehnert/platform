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
zwanzig Titeln für eine Vorlesung waren am 2026-09-10 **fünf** sicher nicht verfügbar und einer blieb ungeklärt.
Ohne die Prüfung fällt das erst auf, wenn ein Teilnehmender den Titel öffnen will.

**Ein Datensatz führt oft mehrere Volltext-Wege** — bis zu neun, als `ezproxy.hnu.de/login?qurl=<Ziel>`. Ein einziger
funktionierender genügt. Deshalb immer alle ansehen, nie nur den ersten.

**Das sichere Nein:** Führen *alle* Wege auf `ebookcentral.proquest.com/lib/<kürzel>/` mit einem fremden Kürzel —
`hwr`, `fhws`, `th-wildau`, `ub-bayreuth`, `uni-passau`, `erlangen`, `fuberlin-ebooks` —, gehört der Titel anderen
Häusern. Das ist der eine Test, der ohne Nachsehen trägt.

**Das Ja muss man sich auf der Zielseite holen, und die sieht überall anders aus.** Den Weg über den Proxy aufrufen
und dort lesen, was die Plattform selbst sagt:

| Plattform | Woran man das Ja erkennt |
|---|---|
| Springer (`doi.org/10.1007…`) | Zeile „Access provided by Hochschule für angewandte Wissenschaften Neu-Ulm" |
| De Gruyter (`doi.org/10.1515…`) | der Block mit „Licensed" ist sichtbar, `itemNotAuthorized` trägt `d-none` |
| wiso-net, Kohlhammer, Beck-Online, Haufe (`doi.org/10.34157…`) | die Seite baut den Inhalt auf, keine Kaufaufforderung |
| **EBSCO** (`search.ebscohost.com`) | **statisch nicht entscheidbar** — siehe unten |

**Zwei Fehlschlüsse, beide selbst gemacht:** Der Pfad allein verurteilt zu Unrecht — Baines, *Servitization Strategy*,
führt einen fremden ProQuest-Pfad **und** einen Springer-Weg, über den die HNU-Kennung durchkommt. Und der
Springer-Satz taugt nicht als allgemeiner Maßstab: De Gruyter kennt ihn nicht, ein Titel dort fiel deshalb erst
fälschlich durch. **Je Plattform den passenden Hinweis lesen, nicht einen Hinweis über alle Plattformen legen.**

**Zwei Prüfungen tragen über alle Plattformen.** Sie kosten je einen Aufruf und sind mehr wert als jeder Marker-Text:

1. **Schreibt der Proxy die Adresse um?** Endet der Aufruf auf einer Adresse mit `.ezproxy.hnu.de`, kennt die
   Hochschule diese Plattform. Landet er auf der nackten Verlagsadresse — `direct.mit.edu`,
   `elibrary.duncker-humblot.com` —, gibt es dort keinen Zugang. Adner, *Winning the Right Game*, fällt genau so durch.
2. **Kommt eine PDF-Datei zurück?** Den Volltext direkt anfordern und auf den Inhaltstyp sehen. Bei Springer etwa
   `link-springer-com.ezproxy.hnu.de/content/pdf/<DOI>.pdf`: Baines liefert `application/pdf`, 6,7 MB — Voigt,
   *Handbuch KI-Verordnung*, liefert `text/html`, also die Bezahlschranke. **Das ist der schärfste Test**, denn er
   fragt nach dem, was der Studierende am Ende braucht.

Hilfsweise verrät sich die Zielseite auch selbst: sichtbare Schlosssymbole an den Kapiteln heißen gesperrt (Lingens,
*Business-Ökosysteme*, zeigt achtzehn davon).

**EBSCO bleibt offen.** Der Aufruf landet auf einer Seite, die die Hochschule im Kopf nennt, ihren Inhalt aber
nachlädt; im Quelltext steht nichts über die Freischaltung, und einen Datenzugang dahinter gibt es nicht. Solche
Titel sind **ungeklärt**, nicht bestätigt — einmal im Browser öffnen oder einen Titel nehmen, der eindeutig durchgeht.

## 6 — Weitere Fallen

- **Die Verfügbarkeitsangabe im Katalog sagt nichts.** „Verfügbar", „Online-Ressource", „Zugang" stehen wörtlich
  gleich auf dem Datensatz eines lizenzierten Titels und auf dem eines fremden. Gemessen am 2026-09-10 an vier
  Datensätzen: identische Zählung, entgegengesetzte Wirklichkeit. Nur die Zielseite entscheidet (§ 5).
- **Fremdlizenzen sind kein Randfall.** In zwei unabhängigen Stichproben zu Strategie- und KI-Themen gehörte
  jeweils rund ein Drittel bis die Hälfte der E-Book-Treffer anderen bayerischen Hochschulen. Wer ohne Prüfung
  auswählt, baut eine Liste, die zum guten Teil nicht aufgeht.
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
