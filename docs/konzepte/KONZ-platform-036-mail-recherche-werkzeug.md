---
concept_id: KONZ-platform-036
title: Mail-Recherche-Werkzeug — Vorgangs-Dossier statt Trefferliste
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []            # kein Klickdummy; CLI-Werkzeug + Datenmodell
adr_threshold: "Amendment zu ADR-286 — kein eigener ADR: Speicher (Postgres), Service-Grenze und Transporte sind dort entschieden; dieses Konzept kehrt nur den Zuschnitt um (Suche live, Index für Aggregate) und ist über den Stufenplan reversibel."
review_by: 2026-10-29
kill_criteria: "Drei Gates aus dem Stufenplan, das erste greifende beendet die jeweilige Stufe. S2: Vollaufbau des Index > 30 min. S3: Threading-Genauigkeit < 90 % auf der Regressionsmenge. S4 entfällt ersatzlos, wenn S3 die Fragen aus §13 bereits beantwortet. Zusätzlich global: fällt die Kalibriersonde eines Kontos dauerhaft durch, wird der betroffene Suchpfad gesperrt statt korrigiert."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: tools/mail_agent/read_mail.py, commit_or_pr: "#1519, #1520", opened_in_session: true}
  - {claim_id: C2, source_path: docs/adr/ADR-286-mail-agent-crypto-shredding-derived-index.md, commit_or_pr: "#1522", opened_in_session: true}
  - {claim_id: C3, source_path: docs/konzepte/KONZ-platform-035.md, commit_or_pr: "main", opened_in_session: true}
  - {claim_id: C4, source_path: "Messreihe Durchsatz/Live-Suche (Postfach B, 300 Nachrichten, 119 Ordner)", commit_or_pr: "session 2026-07-28/29", opened_in_session: true}
created: 2026-07-29
---

# KONZ-platform-036 — Mail-Recherche-Werkzeug

**Tier T3** — Datenmodell, Strang-Rekonstruktion, Ingestion-Verfahren und Ausgabeobjekt eines
Werkzeugs über 90.967 Nachrichten in drei Postfächern und zwei Transportarten.

> **Dieses Dokument ist bewusst portabel geschrieben.** Es setzt kein Repo-Wissen voraus und
> trägt am Ende einen vollständigen Review-Auftrag — es kann unverändert einem externen
> Gutachter vorgelegt werden. Die Kopie unter `~/shared/` ist der ephemere Transport, dieses
> Dokument ist der Stand.

## 0. Scope-Grenze — bitte zuerst lesen

**Datenschutz, DSGVO, Aufbewahrung und Löschbarkeit sind NICHT Gegenstand dieser Begutachtung.**
Sie werden getrennt und organisatorisch behandelt und sind dort entschieden. Ein Review, das
darauf einschwenkt, verfehlt den Auftrag — auch dann, wenn der Gegenstand (E-Mail-Korpus einer
Organisation) es nahelegt.

**Gegenstand sind ausschließlich:**

| Dimension | Frage |
|---|---|
| **Datenmodell** | Trägt das Schema die Fragen, die gestellt werden? |
| **Graph** | Ist die Strang-/Vorgangs-Rekonstruktion robust genug für reale Postfächer? |
| **Wirksamkeit** | Löst der Entwurf das Problem messbar — und sind die Messgrößen die richtigen? |
| **Bedienung** | Ist das Ausgabeobjekt das richtige? Ist die Bedienung für einen Einzelnutzer tragfähig? |
| **Betrieb** | Halten Verbesserungsschleife und vorausschauende Wartung, oder sind sie Dekoration? |

---

## 1. Umgebung

- **Ein Nutzer**, technisch versiert, betreibt das Werkzeug für sich selbst. Kein Team, kein
  Bereitschaftsdienst. Jede Komponente, die dauerhaft läuft, muss ohne Betreuung auskommen.
- **Drei Postfächer, zwei Transportarten:**

| Postfach | Transport | Ordner | Nachrichten | Besonderheit |
|---|---|---|---|---|
| A (geschäftlich) | Microsoft Graph (M365) | 90 | 44.878 | `delta`-Abfrage verfügbar, stabile IDs |
| B (Hochschule) | IMAP, Exchange 2010 | 110 | 46.077 | alt; `UIDVALIDITY`/`UID`, keine modernen Erweiterungen |
| C (Referenz) | IMAP | 9 | 12 | kleine Kontrollmenge mit bekanntem Inhalt |
| **Summe** | | **209** | **90.967** | |

- Stack: Python, PostgreSQL verfügbar, Container-Hosting vorhanden. Kein Kubernetes, keine
  Suchmaschine (Elastic o. ä.) im Betrieb, kein Budget für zusätzliche laufende Dienste.
- Ordner sind fachlich sortiert (Kunden, Partner, Projekte, Jahresarchive). Nachrichten liegen
  **nicht** im Posteingang, sondern einsortiert — das ist für den Entwurf wesentlich.

---

## 2. Der Job — am realen Fall

Ein Vorgang der letzten Wochen, an dem sich alles zeigt. Beteiligt: eine Fachauskunft einer
Partnerorganisation (nachfolgend **P**), deren Leitung (**L**), ein Dienstleister (**D**).

Was tatsächlich gebraucht wurde:

1. **23.06.** — ich schicke P drei Fachfragen zu einem Ablauf. *Keine Antwort per Mail.*
2. **20.07.** — Termin mit L, P, D; ich sende vorab ein Kurzpapier.
3. **21.07.** — P antwortet mit einem **Anhang**, der die gesuchte Datenstruktur definiert.
   Ihre Mail hat drei Sätze; die Substanz steckt vollständig im Anhang.
4. Meine Antwort darauf liegt im **Gesendet-Ordner**, ihre im **Projektordner** —
   zwei Ordner, ein Vorgang.

Die drei Erkenntnisse, die zählten, waren:

- *drei Fragen seit vier Wochen ohne schriftliche Antwort*
- *der Anhang, nicht die Mail, definiert das Schema*
- *zwei Ordner gehören zu einem Strang*

**Keine dieser drei ist eine Suchanfrage.** Alle drei sind Zustandsaussagen über einen Vorgang.

Der Weg dorthin dauerte mit dem damaligen Werkzeug **rund ein Dutzend Postfach-Abfragen über
drei Konten**, weil ohne Index nicht auffindbar war, in welchem Postfach und Ordner die Person
überhaupt vorkommt.

> **These, die du angreifen sollst:** Ein Werkzeug, das darauf optimiert, Nachrichten schneller
> zu *finden*, optimiert die falsche Größe.

---

## 3. Gemessener Ausgangsstand

Alle Zahlen sind gemessen, nicht geschätzt; Messdatum 2026-07-28/29.

**Durchsatz Ingestion (Postfach B, Stichprobe 300 Nachrichten):**

| Verfahren | Durchsatz | Hochrechnung 90.967 Nachrichten |
|---|---|---|
| Ein `FETCH` je Nachricht (bisheriger Code) | 10,1/s | **150 min** |
| Ein `FETCH <von>:<bis>` für den Bereich | 106,3/s | **14 min** |

Faktor **10,6**. Der Engpass ist der Round-Trip, nicht der Server. Für Graph gilt dasselbe
Muster: dort wurden **~12/s** bei Einzelabfragen gemessen; `$batch` (20 Anfragen je Aufruf) und
`$select` sind das Gegenstück, aber noch nicht gemessen.

**Live-Suche ohne Index (Postfach B, 119 Ordner):**

| Abfrage | Dauer |
|---|---|
| Absender-Teilstring über alle Ordner | 6,8 s |
| Empfänger-Teilstring (To **oder** Cc) über alle Ordner | 12,6 s |
| Ordner-Auflistung allein | 5,0 s (IMAP) / 2,8 s (Graph) |

**Nutzbarer Textanteil (Postfach B, 210 Nachrichten):**

| | roh | nach Vorverarbeitung | Faktor |
|---|---|---|---|
| Median | 29.764 B | 838 B | 36× |
| Mittelwert | 320.517 B | 1.757 B | **182×** |

Der Mittelwert liegt beim Elffachen des Medians — Anhänge und HTML dominieren die Masse, nicht
der geschriebene Text. Hochgerechnet: Korpus roh ≈ 4,5 Mrd. Token, nach Vorverarbeitung
≈ 34–40 Mio. (~439 nutzbare Token je Nachricht).

**Rauschanteil:** ≥ 13–16 % (Stichprobe in kuratierten Ordnern, also eine **Untergrenze**).

**Verhalten der server-seitigen Suche (Exchange 2010):**

- Bei ASCII-Suchbegriffen **deckungsgleich** mit einem vollständigen lokalen Kopfzeilen-Scan in
  4 von 4 kalibrierten Fällen, u. a. 353 von 353 Treffern in einem Ordner mit 354 Nachrichten.
- Bei Nicht-ASCII-Begriffen bricht die Client-Bibliothek ab (kein Ergebnis, kein stiller Fehler).
- **Aber:** `SEARCH TO "…"` und `SEARCH CC "…"` lieferten in einem Kalender-Ordner **7 Nachrichten,
  von denen keine** den Begriff in irgendeinem Kopffeld trug — der Server sucht dort über den
  Header hinaus.
- Folge im Betrieb: eine ungeprüfte Übernahme der Server-Antwort meldete **28 statt 21** Treffern.
  Die Zahl sah aus wie ein Ergebnis.

---

## 4. Zielbild und Wirksamkeitsmaße

| Größe | heute (gemessen) | Ziel |
|---|---|---|
| Zeit bis zur Antwort auf „was schickte Person X?" | ~12 Abfragen, Minuten | < 5 s, ein Befehl |
| Kopfzeilen-Durchsatz IMAP | 10,1/s | ≥ 100/s |
| Vollaufbau des Index | 150 min | ≤ 15 min |
| Recall auf einer Referenzmenge mit bekannter Antwort | unkalibriert | 100 %, sonst Ausfall |
| Fragen vom Typ „was ist offen?" beantwortbar | 0 % | vollständig aus dem Index |
| Dauerhaft laufende Dienste | 0 | ≤ 1 (nächtlicher Lauf) |

---

## 5. Tragende Architektur-Entscheidung (und der Grund, sie anzugreifen)

Der naheliegende Entwurf ist: alles in eine Datenbank spiegeln, dann darauf suchen.
**Dieser Entwurf tut das ausdrücklich nicht.**

Rechnung: Die Live-Suche über alle Ordner dauert 6,8 s. Eine Datenbankabfrage dauert ~5 ms. Bei
fünf Suchen am Tag spart der Index **34 Sekunden täglich** und kostet dafür einen
Synchronisations-Dienst, Cursor-Verwaltung, Abweichungserkennung und einen Wiederaufbau-Pfad.
Das amortisiert sich nicht.

Der Index rechnet sich nur für Fragen, die das Postfach **überhaupt nicht** beantworten kann:

- Was ist offen?
- Wo habe ich etwas zugesagt?
- Welcher Strang ist verstummt?
- Was hat sich seit dem letzten Termin bewegt?

Das sind Aggregationen über Zeit und Beteiligte, keine Suchen.

> **Entscheidung: Die Suche bleibt live gegen das Postfach. Der Index existiert ausschließlich
> für Aggregate.**
>
> Zweite Folge, die den Betrieb stark vereinfacht: Der Index **darf lückenhaft sein**, solange er
> sagt, wo er lückenhaft ist. Damit entfällt die Anforderung „vollständig und aktuell", und mit
> ihr die halbe Fehlerklasse inkrementeller Synchronisation.
>
> Dritte Folge: Wenn der vollständige Neuaufbau 14 Minuten dauert, braucht die Kaltmenge
> **gar keine** inkrementelle Synchronisation. Nächtlicher Neuaufbau schlägt korrekte Deltas.

**Das ist die These, an der dieses Review am meisten hängt.** Wenn sie falsch ist, ist der ganze
Entwurf falsch zugeschnitten.

---

## 6. Datenmodell

```sql
account(id, kind∈{graph,imap}, label)

folder(id, account_id, path ltree, kind∈{sent,inbox,archive,noise},
       hot bool, msg_count int, uidvalidity bigint, seen_at timestamptz)

message(id, account_id, folder_id,
        transport_key text,              -- graph_id | 'uidvalidity:uid'
        internet_message_id text,        -- nullable, NICHT eindeutig
        in_reply_to text, refs text[],
        sent_at timestamptz, subject text, subject_norm text,
        has_attachments bool, size_bytes int)

participant(message_id, address_norm citext, address_domain citext,
            display_name text, role∈{from,to,cc,bcc,reply_to})

attachment(message_id, filename, mime, sha256, text_extract text, version_of uuid)

thread(id, method∈{refs,subject,quote,manual}, confidence numeric)
thread_member(thread_id, message_id, confidence numeric)

vorgang(id, label, opened_at, closed_at, status)
vorgang_member(vorgang_id, thread_id, message_id, source∈{auto,manual})

signal(id, message_id, kind∈{frage,zusage,frist,anhang,stille},
       due_at, resolved_by, evidence jsonb)

query_log(id, at, filter jsonb, hits int, folders_scanned int, opened_message_id)
```

**Vier Indizes tragen alle relevanten Abfragen:**

| Index | Deckt ab | Warum nicht anders |
|---|---|---|
| `participant(address_norm)` | „wer war beteiligt" — From/To/Cc in **einer** Abfrage | ohne diese Relation sind es drei getrennte Suchen, deren Vereinigung der Aufrufer bildet — genau dort entstand der 28-statt-21-Fehler |
| `GIN pg_trgm (display_name, subject_norm)` | Teilstring, Groß-/Kleinschreibung egal | die reale Suchsemantik ist Teilstring; ein B-Tree trägt das nicht |
| `message(sent_at DESC)` | Zeitachse, „seit wann still" | |
| `folder USING gist(path)` | „alles unter `Kunden/`" als Präfix-Scan | Pfad als Text mit `LIKE` wäre ein Tabellenscan |

**Zwei Entwurfsentscheidungen, die begründet werden müssen:**

1. **`internet_message_id` ist nullable und nicht eindeutig.** In realen Postfächern fehlt sie,
   kollidiert (Blindkopie an sich selbst, Verteiler) oder existiert mehrfach (dieselbe Nachricht
   in Gesendet und Posteingang, Archivkopien). Eindeutigkeit gilt **pro Transport**:
   `(account_id, graph_id)` bzw. `(account_id, mailbox, uidvalidity, uid)`.
2. **`signal` wird berechnet, nie fortgeschrieben.** Ein direkt editierter Zustand macht die
   Datenbank zu einer zweiten Wahrheit, die vom Postfach abweicht, ohne dass entscheidbar wäre,
   welche stimmt. „Aktualisieren" heißt: neu ableiten und protokollieren, auf welche Nachricht
   hin sich der Zustand geändert hat.

---

## 7. Graph — Strang-Rekonstruktion mit drei Signalen

Reine `References`-Verkettung reicht in Outlook-geprägten Postfächern nicht: Weiterleitungen
verlieren die Kette, `WG:`/`AW:`-Ketten reißen, Termin-Einladungen tragen eigene Identitäten.

| Signal | Konfidenz | Deckt ab | Bricht bei |
|---|---|---|---|
| `References` / `In-Reply-To` | 0,95 | saubere Antwortketten | Weiterleitung, Client-Rewrites |
| Betreff-Normalisierung + Beteiligten-Überlappung + Zeitfenster | 0,70 | `WG:`-Ketten, Ordnerwechsel | generische Betreffs („Rückfrage", „Termin") |
| Zitat-Fingerabdruck (erste 200 Zeichen des zitierten Blocks, normalisiert) | 0,50 | Weiterleitungen ohne Header-Kette | HTML-Umbau, gekürzte Zitate |
| *(geplant)* Kalendereintrag zwischen zwei Nachrichten | 0,60 | löst „wie gestern besprochen" auf | Termin ohne Bezug |

Der Strang ist **berechnet, nicht gespeichert** — bei besserem Verfahren wird neu abgeleitet.
Die Konfidenz wandert in die Ausgabe: ein Strang mit 0,5 wird als *vermutet* angezeigt, nicht
als Tatsache gerechnet.

**Offene Schwäche, die wir selbst sehen:** Für die Signale 2 und 3 gibt es noch keine gemessene
Genauigkeit. Der Stufenplan (§11) macht daraus ein Abbruchkriterium.

---

## 8. Ingestion

1. **Bulk statt Einzelabruf.** Ein `FETCH`-Kommando je Bereich statt je Nachricht (Faktor 10,6
   gemessen). Graph-Gegenstück: `$batch` + `$select`.
2. **Gesendet zuerst.** Verpflichtungen entstehen im Gesendet-Ordner, nicht im Posteingang.
   Wer zuletzt indexiert, was er selbst zugesagt hat, findet die eigenen offenen Punkte zuletzt.
3. **Zwei Geschwindigkeiten.** Heißmenge (aktive Vorgänge, Gesendet, letzte N Monate)
   kontinuierlich; Kaltmenge einmalig, danach nur auf Abruf. **Welche Ordner heiß sind, wird
   nicht geraten, sondern aus `query_log` gemessen.**
4. **Neuaufbau schlägt Delta.** Für die Kaltmenge nächtlicher Vollaufbau (14 min) statt korrekter
   inkrementeller Synchronisation. Delta nur dort, wo Latenz zählt.
5. **Fortschreitend nützlich.** Reihenfolge: neueste zuerst, heiße Ordner zuerst. Der Index ist
   nach ~1 Minute brauchbar, nicht nach 14.
6. **Kein Sprachmodell im heißen Pfad.** Fragezeichen, Datumsangaben, Formulierungen wie „ich
   melde mich" / „anbei", Anhang vorhanden, Antwort ausgeblieben — das sind deterministische
   Signale. Billig, erklärbar, ohne Recall-Problem. Ein Modell kommt erst, wenn diese nicht reichen.

**Zur Frage „wann extrahieren":** Ein früherer Entwurf verlangte, jede Nachricht beim Einlesen
durch ein Sprachmodell zu schicken („beim Einlesen oder nie"), weil Inhalte nicht dauerhaft
gespeichert werden. Das ist falsch — **das Postfach hält den Inhalt, solange die Nachricht
existiert, und er ist jederzeit nachladbar.** Daraus:

| | Extraktion beim Einlesen | Extraktion bei Vorgangs-Eintritt |
|---|---|---|
| Nachrichten | 90.967 | die im aktiven Vorgang |
| Token (à ~439) | ~40 Mio. | ~1 Mio. bei 2 % Trefferquote |
| Ingestion-Dauer | modellgebunden | 14 min, modellfrei |
| Schema-Fehler rückwirkend heilbar | **nein** | **ja** |

---

## 9. Bedienung

**Das Ausgabeobjekt ist der Vorgang, nicht die Nachricht.** Eine Trefferliste erzeugt keine der
drei Erkenntnisse aus §2.

```
VORGANG  Postkorb-Klassifikation (offen, 27 Tage)
Beteiligte  P (Fachauskunft) · L (Leitung) · D (Dienstleister)
Zeitachse   23.06. Frage zum Ablauf (3 Punkte)   ⚠ ohne Antwort, 27 Tage
            20.07. Termin · Kurzpapier gesendet
            21.07. Datenstruktur erhalten        📎 .docx
Offen       ① 3 Fragen unbeantwortet   ② Wertelisten unvollständig
Anhänge     Struktur.docx (v1, 21.07.)
Deckung     3 Konten · 134/134 Ordner · Stand 22:14
```

**Verben statt Flags:** `mail wer <name>` · `mail vorgang <id>` · `mail offen` ·
`mail still --seit 14d`. Jede Ausgabe trägt ihre **Deckungszeile** (geprüfte Konten und Ordner,
Stand). `--json` für alles, damit Zahlen nicht aus Fließtext gezählt werden — genau so entstand
der 28-statt-21-Fehler.

**Anhänge sind erstklassig:** extrahierter Text, Typ, und **Versionierung** — dasselbe Dokument
wandert mehrfach durch einen Strang, und nur die letzte Fassung gilt. Ein Werkzeug, das Anhänge
nur als Dateinamen führt, verfehlt in Fällen wie §2 den gesamten Inhalt.

---

## 10. Verbesserungsschleife und vorausschauende Wartung

| Signal | Quelle | Automatische Reaktion |
|---|---|---|
| `UIDVALIDITY` gewechselt | IMAP `SELECT` | Ordner vollständig neu einlesen |
| Ordner-Zahl weicht vom letzten Stand ab | `folder.msg_count` | Delta-Lauf nur für diesen Ordner |
| Kalibriersonde fällt durch | nächtlicher Lauf je Konto | Suchpfad sperren, auf Vollscan zurückfallen, melden |
| Durchsatz bricht > 50 % ein | Ingest-Metrik | Serveränderung vermuten, Batchgröße halbieren |
| Abfrage liefert 0 Treffer auf bekanntem Muster | `query_log` | als kaputte Abfrage melden, **nicht** als Leermenge werten |
| Ordner 90 Tage in keinem geöffneten Treffer | `query_log` | in die Kaltmenge demoten |
| Strang seit N Tagen ohne Nachricht bei offenem Signal | `signal` | Befund „verstummt" erzeugen |

**Kalibriersonde:** Vor jedem Lauf wird der tatsächlich genutzte Suchpfad an einer Menge mit
**bekannter Antwort** geprüft — im Gesendet-Ordner trägt per Konstruktion jede Nachricht den
eigenen Absender. Geprüft wird die Eigenschaft, auf die es ankommt: *verschweigt der
server-seitige Vorfilter etwas, das der lokale Scan sieht?* Kriterium ist `Client ⊆ Server`,
nicht Gleichheit — zu viele Treffer sind harmlos (lokale Gegenprobe entfernt sie), zu wenige
sehen aus wie ein Ergebnis.

**Recall-Regressionsmenge:** Der Fall aus §2 ist der erste Eintrag (erwartet: genau 1 Nachricht
von P, 20 an P, Strang über zwei Ordner). Jede Änderung am Suchpfad läuft dagegen. Das ist der
Unterschied zwischen „getestet" und „kalibriert".

**Zugrundeliegende Regel:** Falsch-negativ und falsch-positiv kosten nicht gleich viel. Ein
überzähliger Treffer fällt beim Lesen auf; ein fehlender fällt nie auf, weil er wie ein Ergebnis
aussieht. Deshalb: **jede Optimierung, die Kandidaten verwirft, muss gegen eine Menge mit
bekannter Antwort kalibriert sein** — jede, die zu viele liefert, darf ungeprüft bleiben, sofern
nachgelagert gegengeprüft wird. Das trifft ausdrücklich auch Näherungs-Vektorsuche
(`ivfflat`/`hnsw` sind Recall-Regler), falls sie je gebaut wird.

---

## 11. Stufenplan mit Abbruchkriterien

| Stufe | Inhalt | Aufwand | Abbruch, wenn |
|---|---|---|---|
| **S1** | Bulk-Abruf, Gesendet-zuerst, Dossier-Ausgabe, `--json` | Stunden | — reine Verbesserung des Bestands |
| **S2** | Cache-Tabellen + Beteiligten-Index, nächtlicher Vollaufbau | 1–2 Tage | Vollaufbau > 30 min |
| **S3** | Threading (3 Signale) + `signal` + `mail offen` | 2–3 Tage | Threading-Genauigkeit < 90 % auf der Regressionsmenge |
| **S4** | Anhangs-Extraktion, Kalender als vierte Kante, **erst dann** ggf. Semantik/Vektoren | offen | S3 beantwortet die realen Fragen bereits |

**Bestand heute:** Ein Kommandozeilen-Werkzeug für Live-Suche über alle Ordner existiert und ist
im Einsatz (Ordner-Walk mit ausgewiesenem Nenner, Kalibriersonde, Deckungsausweis, `--json`).
Alles ab S2 ist Entwurf.

---

## 12. Bereits entschieden — bitte nicht neu aufrollen

- **Postgres als Speicher** (vorhanden, betrieben, kein zusätzlicher Dienst).
- **Kein zusätzlicher Suchdienst** (Elastic o. ä.) — ein weiterer Dauerdienst ist für einen
  Einzelnutzer nicht tragbar.
- **Postfach bleibt Quelle der Wahrheit**, der Index ist abgeleitet und wiederaufbaubar.
- **Transport-spezifische Identität** statt Vertrauen auf `Message-ID`.
- **Deterministische Signale vor Sprachmodell.**
- **Datenschutz ist ausgelagert** (§0).

Wenn dein Befund einen dieser Punkte *unterläuft*, sag das ausdrücklich — aber greife sie nicht
als eigenständige Empfehlung an.

---

## 13. Fragen, zu denen wir ausdrücklich deine Meinung wollen

1. **Die Umkehrung aus §5** — Suche live, Index nur für Aggregate. Tragfähig, oder ist das eine
   Rationalisierung dafür, den schwierigeren Teil (korrekte Synchronisation) nicht zu bauen?
2. **„Neuaufbau schlägt Delta"** bei 14 Minuten Vollaufbau — bis zu welcher Korpusgröße hält das,
   und woran merkt man, dass es kippt?
3. **Threading mit Konfidenzwerten**: Ist ein dreistufiges Signalmodell die richtige Antwort auf
   kaputte `References`-Ketten, oder gibt es ein robusteres Verfahren, das wir übersehen?
4. **`signal` als berechnete Schicht** — reicht das, oder braucht es einen expliziten Zustand mit
   Übergängen (Zustandsautomat je Vorgang)?
5. **Das Dossier als Ausgabeobjekt** — richtig geschnitten? Was fehlt, was ist Zierrat?
6. **Vorausschauende Wartung (§10)** — welche der sieben Signale sind tragend, welche erzeugen
   nur Rauschen? Welches fehlt?

---

## 14. Schwächen, die wir selbst sehen

Damit du sie nicht als Fund verkaufen musst, sondern vertiefen kannst:

- **Threading-Genauigkeit ist ungemessen.** Die Konfidenzwerte 0,95/0,70/0,50 sind gesetzt, nicht
  belegt.
- **Graph-`$batch` ist ungemessen.** Der Faktor 10,6 stammt von IMAP; für Graph ist er
  angenommen.
- **Die Heißmengen-Definition ist zirkulär**, solange `query_log` leer ist — anfangs muss geraten
  werden, welche Ordner heiß sind.
- **`signal`-Extraktion über Muster** („ich melde mich") ist sprachabhängig und spröde; die
  Trefferquote ist ungemessen.
- **Ein Einzelnutzer ist ein Bus-Faktor von 1.** Der Entwurf optimiert bewusst auf wenig
  laufende Teile — das kann in dem Moment zur Fessel werden, in dem doch mehrere Nutzer dazukommen.
- **Der Nutzen von S3 ist eine Hypothese.** Dass „was ist offen" die wirklich wertvolle Frage
  ist, stützt sich auf **einen** durchgearbeiteten Realfall (§2), nicht auf eine Erhebung.

---

## Review-Auftrag

Arbeite in dieser Reihenfolge:

1. **Steelman zuerst** — formuliere die stärkstmögliche Fassung dieses Entwurfs, bevor du ihn
   angreifst (3–5 Sätze).
2. **Drei Rollen nacheinander:**
   - 🟢 **Befürworter** — warum ist das der richtige Zuschnitt?
   - 😈 **Advocatus Diabolus** — greife maximal hart an: wo bricht der Entwurf, welche Annahme ist
     fragil, welche verworfene Alternative war in Wahrheit besser?
   - 🔮 **Betreiber 2028** — du erbst das in zwei Jahren: was bereust du?
3. **Out-of-the-Box** — mindestens ein Ansatz, den dieses Dokument gar nicht erwägt (anderes
   Paradigma, kaufen statt bauen, ganz weglassen). Auch wenn du ihn am Ende verwirfst.
4. **Befund & Empfehlung** — annehmen / überarbeiten (konkrete Punkte) / verwerfen.

**Nicht annehmen:** Dein trainiertes „Best Practice" gilt hier nicht automatisch. Wo es den
Randbedingungen aus §1 und §12 widerspricht, **gewinnen die Randbedingungen** — benenne den
Konflikt, statt die Wahl als Fehler zu werten. Trenne Beobachtung von Vermutung und markiere
Unsicheres als unsicher, statt zu raten.

**Antwortformat** — die gesamte Antwort als **ein** Markdown-Codeblock, damit sie direkt
gespeichert werden kann:

1. `## Steelman` — 3–5 Sätze
2. `## Befunde` — Tabelle mit stabilen IDs:
   `| ID | Rolle | Befund (1 Satz) | Schwere (hoch/mittel/niedrig) | betroffener Abschnitt |`
   Präfixe: `PRO-1…`, `AD-1…`, `B28-1…`
3. `## Out-of-the-Box` — je Ansatz: Idee · Vorteil · Nachteil · verworfen? (ja/nein + 1 Satz)
4. `## Antworten auf §13` — je Frage 1–3 Sätze, mit Bezug auf eine Befund-ID wo passend
5. `## Empfehlung` — annehmen / überarbeiten / verwerfen + die **eine** wichtigste Begründung
6. `## Vorgeschlagene Änderungen` — nummeriert `REC-1…`, jede mit Bezug auf eine Befund-ID
