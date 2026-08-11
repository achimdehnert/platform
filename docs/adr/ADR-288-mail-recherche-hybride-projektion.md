---
status: proposed
decision_date: 2026-07-29
deciders: Achim Dehnert
consulted: –
informed: –
ai_sparring_by:
  - tool: other
    date: 2026-07-29
    role: adversarial-review
    summary: "Externes LLM (Runde 1) auf KONZ-036: Verdikt überarbeiten. Kern: durable Kuration hängt an wegwerfbaren IDs (nächtlicher Neuaufbau zerstört das einzige Produkt), §5-These im eigenen Dokument gebrochen (Köpfe werden längst indexiert), 14-min-Zahl aus einer 300er-Stichprobe eines Ordners hochgerechnet, Kalibriersonde prüft FROM+ASCII statt der real gebrochenen TO/CC- und Unicode-Fälle. Tag-Tabelle §11."
  - tool: other
    date: 2026-07-29
    role: adversarial-review
    summary: "Externes LLM (Runde 2) auf KONZ-036: Verdikt überarbeiten. Kern: ein ausgewiesen lückenhafter Index trägt positive Treffer, aber KEINE Negativaussage — eine fehlende Nachricht kehrt den Zustand um; fehlende Build-Generationen erzeugen zeitlich gemischte Abbilder; message modelliert Ablageposition statt Entität; Personenauflösung fehlt ganz. Tag-Tabelle §11."
  - tool: other
    date: 2026-07-29
    role: adversarial-review
    summary: "Externes LLM (Runde 3, 'konzept-hybrid') auf KONZ-036: eigenständige Gegen-Konzeption statt Review — 16 Architekturklassen mit gewichteter Matrix, Sieger PostgreSQL+Datei-CAS (4,73). Vier übernommene Zugewinne: inhaltsadressierter Rohobjektspeicher, Leitsatz 'Delta an der Quelle, Rebuild in der Projektion', sechs Ausgabezustände statt zwei, sechsstufige Retrieval-Pipeline. Nicht übernommen: die volle Grundausstattung (25 Tabellen) und der unbeschränkte Volltext-CAS. Tag-Tabelle §11.3."
  - tool: other
    date: 2026-07-29
    role: adversarial-review
    summary: "OpenAI o3 (Runde 4) auf DIESEN ADR-Text — erste Runde, die nicht die Vorstufe bewertet. Verdikt überarbeiten. Traf die drei in §11.5 selbst benannten Lücken: die Zahlenkorrektur bleibt Indizienbeweis (AD-1), die Zweckbindung macht eine Ausnahmeklausel von ADR-286 zur Default-Strategie (AD-3), und Gate 8 misst das likely_open-Problem, behebt es aber nicht (AD-4). 7 von 9 Befunden valid, 2 missverstehen den Kontext. Tag-Tabelle §11.6."
  - tool: other
    date: 2026-08-11
    role: adversarial-review
    summary: "Externes LLM (Runde 5, Pre-Mortem) auf ADR-288 v2: Verdikt ueberarbeiten. Kern: ein Accept beglaubigt einen Zustand, den der ADR selbst verbietet — zwei Wahrheitsstaende der Kuration und eine Gate-Entscheidung auf einer als vorlaeufig markierten Zahl. Fuenf Failure-Modes, fuenf Empfehlungen. Tag-Tabelle §11.7."
  - tool: other
    date: 2026-08-11
    role: adversarial-review
    summary: "Externes LLM (Runde 6, Pre-Mortem, anderer Anbieter) auf ADR-288 v2: Verdikt ueberarbeiten. Kern: die zentrale Zusage 'open nur bei vollstaendiger Deckung' ist aus der laufenden Anlage nicht aus einem autoritativen, generationenkonsistenten Zustand ableitbar. Acht Failure-Modes, acht Empfehlungen, darunter ein belegter interner Widerspruch (§1.4.2 vs §4.11). Tag-Tabelle §11.7."
---

# ADR-288: Adopt a purpose-scoped local evidence store with source-side deltas, rebuildable projections and coverage-bound negative statements

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed — v2 nach vier Runden; **sechs** nach dem Pre-Mortem-Paar (§11.7), das den Accept ausdruecklich blockiert |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-29                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | offen · 6× externe KI-Zweitmeinung (non-accountable, §11)             |
| **Supersedes**  | – (**kein** Supersede von ADR-286 — siehe §3.2)                       |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-286 (Persistenz — §4.10.7 wird korrigiert, der Rest bleibt gültig), KONZ-platform-036 (Vorstufe), KONZ-platform-035 (Deckungsausweis) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `tools/mail_agent/` (Transport, Live-Suche, Ausschlussregel) |
| `dev-hub`      | Primär     | `apps/mail_agent/` (Evidenzspeicher, Projektion, Dossier) |

> **Scope-Grenze.** Datenschutz, Aufbewahrung und Löschbarkeit sind **nicht** Gegenstand dieser
> Entscheidung; sie sind organisatorisch geregelt. Hier geht es um Datenmodell, Graph,
> Wirksamkeit, Bedienung und Betrieb.

---

## Decision Drivers

- **Negativaussagen sind das Produkt.** Der Nutzen liegt in „offen", „unbeantwortet",
  „verstummt" — nicht in Trefferlisten. Diese Aussagen kehren sich um, wenn eine Nachricht fehlt.
- **Vier Fünftel des Bestands sind für die Fragestellung irrelevant** — gemessen, §1.4. Der
  billigste Hebel ist, sie gar nicht erst zu verarbeiten.
- **Ein Nutzer, kein Bereitschaftsdienst.** Jede dauerhaft laufende Komponente muss ohne
  Betreuung überleben.
- **Das Produkt des Werkzeugs ist nicht ableitbar.** Vorgänge, Auflösungen und Entscheidungen
  entstehen nicht aus dem Postfach und dürfen nicht mit einer Projektion verworfen werden.
- **Umkehrbarkeit.** Von „wenig lokal" zu „viel lokal" kommt man jederzeit; zurück nicht.

---

## 1. Context and Problem Statement

### 1.1 Der Job

Der motivierende Realfall: Eine Fachauskunft **P** beantwortet drei Fragen vom 23.06. nicht; am
20.07. ein Termin; am 21.07. eine dreisätzige Mail, deren Substanz vollständig in einem **Anhang**
steckt; ihre Nachricht und meine Antwort liegen in **zwei verschiedenen Ordnern**. Alle drei
Erkenntnisse waren **Zustandsaussagen über einen Vorgang**, keine Suchergebnisse. Der Weg dorthin
kostete rund ein Dutzend Postfach-Abfragen über drei Konten.

### 1.2 Umgebung

Drei Postfächer, zwei Transportarten. Python, PostgreSQL und Container-Hosting vorhanden; kein
Budget für zusätzliche dauerhaft laufende Dienste. Die Ordnerstruktur ist fachlich relevant —
Nachrichten liegen einsortiert, nicht im Posteingang.

### 1.3 Gemessener Durchsatz und Suchverhalten (2026-07-28/29)

| Messung | Wert |
|---|---|
| Ingestion Einzel-`FETCH` je Nachricht | 10,1/s |
| Ingestion ein `FETCH` je Bereich | **106,3/s** (Faktor 10,6) |
| Live-Suche über 119 Ordner, Absender | 6,8 s |
| Live-Suche über 119 Ordner, Empfänger (To **oder** Cc) | 12,6 s |
| Vorverarbeitung roh → nutzbar | Faktor 182 im Mittel, ~439 Token je Nachricht |
| Server-`SEARCH`, ASCII | deckungsgleich mit lokalem Vollscan, 4/4 (u.a. 353/353 von 354) |
| Server-`SEARCH`, Nicht-ASCII | Abbruch der Client-Bibliothek |
| Server-`SEARCH` auf `TO`/`CC` | **7 Treffer ohne den Begriff in irgendeinem Kopffeld** |

Der letzte Wert ist der teuerste: ungeprüft übernommen ergab er **28 statt 21** Treffern.

### 1.4 Bestandsgröße und Wirkung der Ausschlussregel (2026-07-29, neu)

Erhoben über `STATUS (MESSAGES)` je Ordner, gegengeprüft gegen `SELECT`/`SEARCH ALL` in vier
Ordnern — **4/4 identisch**, die Methode ist belegt.

| Konto | Ordner | Nachrichten | behalten | ausgeschlossen |
|---|---:|---:|---:|---:|
| A / Graph | 112 | 40.171 | 7.966 | **32.205 (80,2 %)** |
| B / IMAP | 119 | 26.303 | 5.976 | **20.327 (77,3 %)** |
| C / IMAP Referenz | 9 | 12 | 10 | 2 (16,7 %) |
| D / IMAP privat | 6 | 94 | 76 | 18 (19,1 %) |
| **Summe** | **246** | **66.580** | **14.028** | **52.552 (78,9 %)** |

Ausgeschlossen wird nach der bereits implementierten Regel (`tools/mail_agent/indexierung.py`):
Papierkorb/Junk, technische Ordner, redaktionell/werbliche Ordner und Jahresarchive bis
`ARCHIV_BIS`. Die größten Posten sind Jahresarchive (Archiv/2017: 7.459, Archiv/2023: 4.789)
und Newsletter-Ordner.

**Das verändert die Größenordnung der gesamten Entscheidung:**

| | ohne Ausschluss | mit Ausschluss |
|---|---:|---:|
| Zu verarbeitende Nachrichten | 66.580 | **14.028** |
| Vollaufbau bei 106,3/s | 10,4 min | **2,2 min** |
| Rohobjektspeicher (Mittelwert-Hochrechnung) | 21,3 GB | **4,5 GB** |
| Auslastung eines 15-min-Fensters | 70 % | **15 %** |

### 1.4.1 Gate 0 — der Widerspruch zu ADR-286 §4.10.8, aufgelöst

ADR-286 §4.10.8 nennt **90.967** Nachrichten über 209 Ordner (Messung 2026-07-28). Die hiesige
Messung ergibt **66.580** über 246 Ordner — mehr Ordner, weniger Nachrichten. Die Abweichung liegt
bei den beiden großen Konten (B: 26.303 statt 46.077 · A: 40.171 statt 44.878), zusammen −24.483.

**Belegkette:**

1. **Die Methode ist validiert.** `STATUS` stimmt in vier Stichproben-Ordnern exakt mit `SELECT`
   und `SEARCH ALL` überein; im vollständigen Lauf trat **kein einziger** nicht zählbarer Ordner
   auf (Fehler werden ausgewiesen, nie als 0 verrechnet).
2. **Das Kontrollkonto trifft exakt.** Konto C ergibt **9 Ordner / 12 Nachrichten** — identisch
   mit ADR-286. Genau dieses Konto war von der unten genannten Umsortierung nicht betroffen.
3. **Die Ursache steht im eigenen Sitzungsprotokoll.** Am 2026-07-28 lief eine große
   Archiv-Umsortierung (`archiv_einsortieren.py`): elf neue Jahrgänge angelegt, dreizehn
   nachgezogen, **Sammelordner erst nach einem Leer-Guard gelöscht**. Der Session-Retro
   `docs/retros/session-retro-2026-07-28-platform-d5eb5e.md` beziffert **28.158 in zwei
   Produktivpostfächern verschobene Nachrichten** — dieselben zwei Konten, dieselbe
   Größenordnung wie die Differenz von 24.483. Zusätzlich dokumentiert die Sitzung
   Drossel-Wiederholungen („12.311 Falsch-Fehler").

**Schluss:** Die ältere Zahl war zum Messzeitpunkt keine Erfindung, sondern die Ablesung eines
**vorübergehenden Zustands** — Nachrichten lagen zugleich im Sammelordner und im neuen
Jahresarchiv, bevor die Sammelordner gelöscht wurden. Sie beschreibt nicht den heutigen Bestand
und wird nicht weiterverwendet. Maßgeblich ist **66.580**.

**Konsequenz für die drei externen Runden:** Alle argumentierten auf 90.967. Die schärfste
Einzelkritik — „90.967 von theoretisch 95.670 = 95 % des 15-min-Fensters" — liegt mit der
gemessenen Zahl bei 70 % und nach Ausschluss bei **15 %**. Die Kritik bleibt in der Sache richtig
(nicht extrapolieren, sondern messen), ihr konkreter Alarmwert entfällt.

**Restlücke, ehrlich:** Die Umsortierung als Ursache ist aus Datum, betroffenen Konten und
Größenordnung erschlossen, nicht aus einem Lauf-Protokoll der damaligen Zählung rekonstruiert.
Ein Beweis wäre nur über die Rohausgabe jener Messung möglich, die nicht vorliegt.

**Was daraus folgt (Runde 4, AD-1).** Die Gegenlesung hält den Schluss für einen
Indizienbeweis und zieht daraus einen Schluss, den dieser Abschnitt bis dahin nicht gezogen
hatte: solange nur *eine* Zählung vorliegt, ist auch **66.580** eine Momentaufnahme. Die alte
Zahl wurde ja gerade deshalb verworfen, weil sie einen Zwischenzustand traf — dasselbe
Argument gilt gegen die neue. Der Einwand ist berechtigt und billig zu entkräften:

> **Die Bestandszählung gilt erst als belastbar, wenn sie an drei nicht aufeinanderfolgenden
> Tagen wiederholt wurde, die Rohausgabe je Lauf protokolliert ist und die drei Ergebnisse
> innerhalb einer festzulegenden Spanne liegen.** Bis dahin ist 66.580 die *beste verfügbare*
> Zahl, keine bestätigte. Größenrechnungen dürfen darauf aufsetzen, Gate-Entscheidungen nicht.

Das verschiebt Gate 0 von „erfüllt" auf „vorläufig erfüllt" (§8).

### 1.4.2 Gemessener Vollaufbau (2026-07-29) — Beleg zu Gate 5

Der Kopfzeilen-Vollaufbau über die **behaltene** Menge, tatsächlich ausgeführt statt
hochgerechnet — read-only, alle vier Konten, beide Transporte:

| Konto | Transport | Kopfsätze | Ordner | Dauer | Rate |
|---|---|---:|---:|---:|---:|
| A / IIL | Graph | 7.951 | 78 | 86,5 s | 92,0/s |
| B / HNU | IMAP | 5.978 | 92 | 76,1 s | 78,5/s |
| C / Referenz | IMAP | 10 | 7 | 0,4 s | — |
| D / privat | IMAP | 77 | 3 | 0,2 s | — |
| **Gesamt** | | **14.016** | **180** | **163,2 s = 2,7 min** | 86/s |

**Die Mikro-Benchmarks überschätzen systematisch.** Einzelordner-Messungen ergaben 120,7/s
(Graph, Listen-Abruf) und 106,3/s (IMAP, Bulk-`FETCH`); im echten Lauf über 180 Ordner sind es
92,0/s und 78,5/s. Die Differenz ist Ordnerwechsel-Overhead — **genau der Faktor, den die
externen Runden 1 und 2 an den Hochrechnungen dieses Entwurfs kritisiert haben** (§11.1). Ihre
Kritik trifft im Mechanismus zu; die Schwelle hält mit Faktor 3,7 Reserve trotzdem.

Zum Graph-Transport, der bis hierher als „ungemessen" geführt war: der natürliche Weg ist
**nicht** `$batch`, sondern der Listen-Abruf mit `$top` und Paging — 591 Nachrichten kamen in
**einer** Antwort. Gegen den Einzelabruf je Nachricht (10,3/s) ist das Faktor 11,7.

**Zwei Einschränkungen, ausdrücklich:**

- Gate 5 verlangt wörtlich ein **p95**; gemessen ist **ein** Lauf. Bei 2,7 gegen 10 Minuten ist
  der Abstand groß genug, dass daraus kein Streitfall wird — ein p95 ist es nicht.
- Gezählt wurden 14.016 statt der in §1.4 erhobenen 14.028 (−12). Das Postfach lebt zwischen
  zwei Läufen; die Größenordnung bestätigt beide Messungen gegenseitig.

**Noch nicht gemessen** und damit der offene Rest von Gate 5: Datenbankschreiben und
Normalisierung. Beide existieren erst mit P2 — der Wert oben ist die **untere** Schranke des
späteren Vollaufbaus, nicht sein Endwert.

### 1.5 Warum v1 dieses ADR nicht trug

Der Vorgänger dieser Fassung setzte auf „Suche bleibt live, der Index existiert nur für
Aggregate, und er darf lückenhaft sein, solange er sagt wo." Drei unabhängige externe Runden
haben diesen Zuschnitt gebrochen (§11). Der tragende Einwand:

> Ein ausgewiesen lückenhafter Index trägt **positive** Treffer, aber **keine Negativaussage** —
> gerade eine fehlende Nachricht kehrt „offen" in „erledigt" um.

---

## 2. Considered Options

Runde 3 hat 16 Architekturklassen mit gewichteter Passungsmatrix bewertet. Die vier für uns
relevanten:

| Option | Passung | Ergebnis |
|---|---:|---|
| **PostgreSQL + Datei-Rohobjektspeicher** | **4,73** | **gewählt** |
| Maildir + notmuch + PostgreSQL | 4,17 | Benchmark, kein Architekturpfad |
| Reines PostgreSQL ohne Rohobjekte | 4,07 | tragfähig, aber Parserwechsel erzwingt Vollabruf |
| PostgreSQL + externer Suchdienst | 4,05 | funktional stark, betrieblich unpassend (Dauerdienst) |
| Live-Föderation ohne Projektion (= v1) | 2,67 | Verifikation statt Primärpfad |

Verworfen mit Begründung: Graph-, Vektor- und Multi-Model-Datenbanken als *Kern* (lösen
Kantenerzeugung nicht, die eigentliche Schwierigkeit), Kaufprodukte (lösen den Standardteil,
nicht das persönliche Vorgangs- und Zustandsmodell), LLM-Agent über Live-Quellen (Bedienoberfläche,
kein verlässlicher Kern).

---

## 3. Decision Outcome

### 3.1 Die Entscheidung

**Gewählt: zweckgebundener lokaler Evidenzspeicher mit quellenseitigem Delta und vollständig
wiederaufbaubaren Projektionen.**

Sechs Festlegungen:

1. **Ausschluss zuerst.** Die bestehende Regel entfernt 78,9 % des Bestands, bevor irgendetwas
   verarbeitet wird. Ausgeschlossene Ordner erscheinen **namentlich mit Grund** in jeder Deckung —
   Ausschluss verkleinert die Grundgesamtheit sichtbar, nicht still. Drei Auflagen, alle aus
   Runde 4 (AD-2, M28-1):
   - Die Ausschlussregel lebt in einer **versionierten Konfiguration**, nicht als Literal im
     Code. Jede Deckung nennt die Version, mit der sie erzeugt wurde. Ohne das ist in zwei
     Jahren nicht mehr rekonstruierbar, warum ein alter Vorgang eine andere Grundgesamtheit
     sah als ein neuer.
   - Ein Ausschluss ist **nie endgültig**: zeigt ein Vorgang auf einen ausgeschlossenen Ordner,
     wird dieser gezielt nachgeladen und die Deckung neu berechnet. Der Ausschluss spart
     Verarbeitung, er verkleinert nicht den erreichbaren Raum.
   - Bis zum Nachladen ist der Zustand **`unknown`**, nicht `open` und nicht `resolved`. Ein
     ausgeschlossener Ordner ist eine Deckungslücke wie jede andere — genau das war der
     Einwand: sonst verschiebt der Ausschluss das Problem nur an eine Stelle, an der es
     niemand mehr sieht.
2. **Delta an der Quelle, Rebuild in der Projektion.** Die teure Übertragung über das Netz ist
   inkrementell (Graph-Delta je Ordner, IMAP über `UIDVALIDITY`/UID mit periodischer Abstimmung).
   Alles lokal Abgeleitete darf jederzeit vollständig neu entstehen. Das ersetzt die Regel
   „Neuaufbau schlägt Delta" aus v1, die beide Achsen vermengte.
3. **Zweckgebundener Rohobjektspeicher.** Kopfdaten und **Anhänge** für die behaltene Menge;
   **Volltext nur für Nachrichten in einem aktiven Vorgang**. Inhaltsadressiert (Ablage unter dem
   Fingerabdruck des Inhalts), damit identische Anhänge einmal liegen und Parserwechsel ein
   lokaler Neulauf statt eines Vollabrufs sind.
4. **Projektion sucht, Quelle verifiziert.** Die lokale Projektion beantwortet Kopf-Abfragen,
   Volltext und Aggregate; das Postfach dient Synchronisation, Originalabruf und gezielter
   Gegenprüfung.
5. **Sechs Ausgabezustände** statt einer binären Aussage (§4.6).
6. **Zwei Schichten**: wegwerfbare Projektion ↔ durable Kuration (§4.1).

### 3.2 Verhältnis zu ADR-286 — kein Supersede

ADR-286 entschied „Metadaten-Index-first, kein dauerhafter Klartext-Body, Inhalte just-in-time".
Ein **unbeschränkter** Volltextspeicher wäre dessen Gegenteil und bräuchte ein Supersede.

Die hier gewählte Fassung braucht keines: ADR-286 sieht **zweckgebundene Persistenz** selbst vor
(§4.8 Stufe 3, „Vorgang-Promotion"). Punkt 3 oben denkt genau diese Tür konsequent zu Ende —
Volltext existiert lokal nur für das, was in einem aktiven Vorgang steht. Alles andere bleibt
Kopfdaten plus Anhänge.

Zwei Gründe, warum das nicht nur formal, sondern sachlich die bessere Wahl ist:

- **Umkehrbarkeit.** Von der Teilmenge zur Vollmenge kommt man jederzeit — die Quelle steht ja.
  Zurück ist teuer. Wer die Teilmenge wählt und sich irrt, verliert Zeit; umgekehrt verliert man
  Handlungsspielraum.
- **Messbarkeit.** Ob die Teilmenge reicht, beantwortet Phase 3/4 ohnehin — als Messwert statt
  als Vorabannahme.

**Korrigiert wird ADR-286 §4.10.7:** Der Satz „Weil Bodies nicht dauerhaft gespeichert werden,
ist Extraktion beim Einlesen **oder nie**" ist falsch. §4.8 derselben ADR sagt bereits das
Richtige — das Postfach hält den Inhalt, er ist nachladbar. Mit dem Rohobjektspeicher gilt das
erst recht: Extraktion ist wiederholbar, und ein Schema- oder Parserfehler ist rückwirkend heilbar.

| | Extraktion beim Einlesen | Extraktion bei Vorgangs-Eintritt |
|---|---|---|
| Nachrichten | 14.018 (nach Ausschluss) | die im aktiven Vorgang |
| Ingestion | modellgebunden | modellfrei |
| Schema-Fehler rückwirkend heilbar | **nein** | **ja** |

### 3.2.1 Wann ein Supersede doch nötig würde (Runde 4, AD-3)

Die Gegenlesung hält dem entgegen, dass hier eine **Ausnahmeklausel zur Regelstrategie**
gemacht wird: ADR-286 §4.8 sieht Vorgang-Promotion als Sonderfall vor, dieser ADR baut den
Normalbetrieb darauf. Der Einwand trifft. Er widerlegt die Entscheidung nicht — eine Klausel
konsequent zu nutzen ist zulässig —, aber er legt offen, dass die Grenze bisher nirgends
definiert war. Ein Verhältnis, das nur durch Auslegung hält, driftet.

**Die Entscheidung braucht ein Supersede von ADR-286, sobald einer dieser Punkte eintritt:**

1. Volltext wird für Nachrichten **außerhalb** eines aktiven Vorgangs dauerhaft gespeichert —
   gleich mit welcher Begründung (Vorwärmen, Recall-Messung, Bequemlichkeit).
2. Der Anteil der Nachrichten in aktiven Vorgängen überschreitet dauerhaft **ein Viertel** der
   behaltenen Menge. Dann ist „zweckgebunden" nur noch ein Etikett für „fast alles".
3. Ein Vorgang wird geschlossen, ohne dass sein Volltext gelöscht oder in ein definiertes
   Nachleben überführt wird. Zweckbindung ohne Ende der Zweckbindung ist keine.

Trifft einer davon zu, ist die Umdeklaration real und der ehrliche Weg ist ein Supersede,
kein weiter gedehnter §4.8. **Der Anteil aus Punkt 2 wird gemessen** (§8 Gate 10).

---

## 4. Implementation Details

### 4.1 Zwei Schichten — Projektion und Kuration

**Wegwerfbar (drop & rebuild):** `message_entity`, `message_occurrence`, `participant`,
`text_unit`, `attachment_occurrence`, `edge`, `thread_projection`, `observation`.

**Durabel (überlebt jeden Neuaufbau):** `vorgang`, `action_item`, `action_event`, `party`,
`identity`, `query_log`, `regression_case`.

Durable Referenzen hängen an **stabiler Identität**, nie an einem Wert, den ein Neuaufbau neu
vergibt. Ein `UIDVALIDITY`-Wechsel oder ein Postfach-Umzug bekommt eine definierte
Migrationsprozedur.

Ohne diese Trennung zerstört der Neuaufbau auf Dauer das Einzige, was das Werkzeug produziert —
der stärkste Einwand aus Runde 1.

#### Geändert 2026-07-31 — natürlicher Schlüssel statt Umgehung der Datenbank

**Vorher stand hier:** „Durable Referenzen zeigen **nie** auf Surrogat-IDs der Projektion,
sondern auf `(account_id, transport_key)` plus die logische Entität […]; ein Zähler
**verwaister durabler Referenzen** läuft nach jedem Aufbau (§8 Gate 3)."

Die erste Umsetzung befolgte diesen Wortlaut und baute damit **an der Datenbank vorbei**: die
Kennung lag als Textkopie neben einem Fremdschlüssel, der nur noch Cache war, dazu ein
Neuverknüpfungs-Lauf und ein Waisen-Zähler. Drei Mechanismen für eine Beziehung.

Zwei Messungen am 2026-07-31 haben die Änderung ausgelöst:

1. **Kein Code löscht `LogicalMessage`** (nur `demo_data.py` beim Seed-Reset), und einen
   Neuaufbau-Pfad gibt es nicht. Der Test, der die Regel rechtfertigte, bildete ein Szenario
   nach, das das System nicht erzeugen kann.
2. **`ingest_or_skip` korreliert längst** auf `internet_message_id`/`raw_sha256`. Die „stabile
   Kennung" war keine neue Größe, sondern der vorhandene Merge-Schlüssel unter neuem Namen.

**Das Ziel der Regel ist stabile Identität, nicht die Vermeidung von Fremdschlüsseln.** Ein
*natürlicher* Schlüssel — `sha256(Mandant | Message-ID bzw. Inhalts-Hash)`, materialisiert als
eindeutige Spalte — erfüllt das Ziel und taugt als Fremdschlüsselziel. Damit erzwingt die
Datenbank die Beziehung selbst, statt sie hinterher zu beklagen.

**Folgen für §8 Gate 3.** Für diese Referenzklasse ist der Waisen-Zähler kein Monitor mehr,
sondern ein Wächter: `PROTECT` verweigert das Löschen einer kuratierten Nachricht, verwaiste
Zuordnungen sind damit **konstruktiv ausgeschlossen** statt gezählt. Die Prüffunktion bleibt
bestehen — sie deckt den Fall ab, dass jemand am ORM vorbei löscht (roher SQL-Zugriff,
Teil-Restore). Ein Gate, das seine eigene Voraussetzung nicht mehr prüft, ist kein Gate. Für
andere durable Klassen (`action_item`, `party`, …) gilt Gate 3 unverändert, solange sie keinen
Fremdschlüssel auf einen natürlichen Schlüssel tragen.

**Verträglich mit ADR-286 §4.3.** Die DSGVO-Löschung entfernt keine Zeile, sie setzt einen
Grabstein und minimiert die Felder — `PROTECT` steht ihr nicht im Weg. Als Test verankert;
andernfalls wäre der Schutz ein Fehler.

**Restlücke, ehrlich benannt:** Eine Nachricht ohne jede Identität (weder Message-ID noch
Inhalts-Hash) bekommt **keinen** Schlüssel und ist damit nicht kuratierbar. Das ist gewollt —
ein erfundener Schlüssel würde zwei verschiedene Nachrichten zu einer machen. Wie oft dieser
Fall real auftritt, ist **nicht gemessen**; der billigste Check ist
`LogicalMessage.objects.filter(kennung__isnull=True).count()` nach dem Backfill.

Umgesetzt in dev-hub#182 (Migrationen `0008`/`0009`).

### 4.2 Rohobjektspeicher (inhaltsadressiert)

```text
store/objects/<hh>/<hh>/<hash>.<ext>     # Identität ist der Hash, die Endung ist Bedienhilfe
store/manifests/  store/quarantine/  store/tmp/
```

Schreibweg: in eine temporäre Datei streamen, dabei Hash und Größe berechnen, synchronisieren,
atomar an den Zielpfad verschieben, danach Datenbanksatz anlegen. Ein Datenbankverweis zeigt nur
auf ein bestätigtes Objekt; ein Objekt ohne Verweis gilt zunächst als verwaist, nicht als löschbar.

**Umfang nach §3.1 Punkt 3:** Kopfdaten und Anhänge für die behaltene Menge (14.018 Nachrichten,
~4,5 GB Mittelwert-Hochrechnung), Volltext nur für aktive Vorgänge. Der Speicherbedarf ist bei
allen betrachteten Varianten unkritisch und war für die Entscheidung nicht maßgeblich.

### 4.3 Entität und Vorkommen

Dieselbe logische Nachricht existiert in Gesendet und Posteingang, in Archivkopien, und wechselt
beim Verschieben ihre Transportidentität — Zählungen, Signale und Anhänge wirken dadurch doppelt.

```text
message_entity(id, content_fingerprint, sent_at, subject_norm, …)
message_occurrence(entity_id, account_id, folder_id, transport_key, generation)
attachment_occurrence(occurrence_id, filename, mime, sha256, raw_object_ref)
```

`sha256`-Gleichheit belegt **Identität, nicht Versionsnachfolge**. Eine Spalte `version_of`
entfällt ersatzlos; Dokumentversionierung ist ein eigenes Problem und wird nicht in einer
Schemaspalte versteckt.

### 4.4 Build-Generationen

```text
build_generation(id, status∈{building,validating,ready,active,superseded,rejected},
                 derivation_version, parser_version, started_at, finished_at)
folder_scan(generation_id, account_id, folder_path, expected, read, errors, watermark,
            excluded_reason NULL)
```

Ein Lauf baut in eine neue Generation, wird gegen Invarianten validiert und **erst danach atomar
freigegeben**. Der letzte aktive Stand bleibt erhalten. Ein abgebrochener Lauf ist unsichtbar.
`derivation_version` und `parser_version` wandern in die Ausgabe — sonst ist in zwei Jahren nicht
erklärbar, warum ein Vorgang 2026 anders aussah als 2028.

`excluded_reason` steht **an den Daten**, nicht als Filter im Code: nur so kann eine Deckung aus
der Datenbank heraus erklären, was fehlt.

### 4.5 Deckung ist mehrdimensional

Nicht „134 von 134 Ordnern", sondern: Konten · Ordner · **Zeitintervall** · bekannte Vorkommen ·
geladene Rohobjekte · **Parserstatus** · Anhangstypen · Generation · Stand.

```text
Deckung: vollständig für Partei P, 2026-06-01 bis 2026-07-29
Quellen: 3/3 Konten, 134/134 relevante Ordner (52.544 bewusst ausgeschlossen)
Rohobjekte: 62/62 vorhanden · Parser: 59 ok, 2 Format nicht unterstützt, 1 verschlüsselt
Ergebnis: PARTIAL — negative Aussage nicht definitiv
Build: gen_2026-07-29T22:14Z
```

Die technische Zählung bleibt sichtbar, wird aber in eine **fachliche Konsequenz** übersetzt.

### 4.6 Sechs Ausgabezustände

Eine offene Frage wird nur dann definitiv als `open` ausgegeben, wenn gilt: *Anfrage oder Zusage
existiert* **und** *relevanter Scope vollständig* **und** *kein Erledigungsbeleg* **und** *keine
manuelle Erledigung*.

| Status | Bedeutung |
|---|---|
| `open` | relevanter Scope vollständig geprüft, kein Erledigungsbeleg |
| `likely_open` | starke Evidenz, Zuordnung oder Deckung nicht vollständig |
| `unknown` | Quelle, Ordner, Zeitraum oder Parser unvollständig |
| `resolved` | belegte oder manuell bestätigte Erledigung |
| `dismissed` | bewusst nicht als Arbeitsgegenstand behandelt |
| `snoozed` | gültig, bis zu einem Zeitpunkt zurückgestellt |

Das ersetzt die Zweiteilung aus v1, die „starke Evidenz bei unvollständiger Deckung" und „keine
Ahnung" in denselben Topf warf. **`likely_open` braucht eine gemessene Zielquote** — bleibt der
Anteil dauerhaft hoch, ist die Unterscheidung wertlos (§8 Gate 8).

**Der Einwand aus Runde 4 (AD-4) und warum er nur halb übernommen wird.** Die Gegenlesung
hält die Regel für praxisgefährdend: wenn vollständige Deckung selten erreicht wird, landet
alles in `likely_open`, und das Werkzeug beantwortet die eine Frage nicht mehr, für die es
gebaut ist. Der zweite Teil des Einwands sitzt: Gate 8 **misst** das Problem, es **behebt**
nichts — ein Messwert ohne definierte Konsequenz ist ein Beobachtungsposten, keine Absicherung.

Der vorgeschlagene Ausweg — `open` schon ab einer Deckung von etwa neun Zehnteln zulassen —
wird **nicht** übernommen. Er kauft Benutzbarkeit mit genau der Fehlerklasse, gegen die dieser
ADR gebaut ist: bei neun Zehnteln Deckung ist jede zehnte Nachricht ungesehen, und eine
einzige ungesehene Nachricht kehrt „offen" in „erledigt" um. Eine Schwelle unterhalb von
vollständig macht die Negativaussage nicht etwas unsicherer, sondern unzulässig — der
Unterschied ist kategorial, nicht graduell.

**Stattdessen bekommt Gate 8 eine Konsequenz statt nur einer Zahl.** Übersteigt der Anteil
`likely_open` an allen offenen Punkten den Schwellwert dauerhaft, wird genau einer von drei
Hebeln gezogen, und die Wahl wird begründet festgehalten:

1. **Die Deckungsdefinition ist zu breit geschnitten** — der „relevante Scope" einer Frage
   umfasst Quellen, die für sie nachweislich nichts beitragen. Dann wird der Scope enger
   definiert, nicht die Schwelle gesenkt.
2. **Die Ingestion hat eine reale Lücke** — dann ist der hohe Anteil ein korrektes Signal und
   die Lücke wird geschlossen.
3. **Die Frage ist auf diesem Bestand nicht beantwortbar.** Dann sagt das Werkzeug das, statt
   eine Antwort zu erfinden — das ist ein zulässiges Ergebnis, kein Defekt.

Bleibt der Anteil auch nach dem Ziehen eines Hebels hoch, ist das ein Befund gegen den
gesamten Zuschnitt und gehört in eine Nachfolge-Entscheidung — nicht in eine aufgeweichte
Schwelle.

### 4.7 Retrieval in sechs Stufen

| Stufe | Inhalt |
|---|---|
| 1 | **Struktureller Scope** — Konten, Ordner, Zeitraum, Parteien; erzeugt zugleich die Deckung |
| 2 | **Lexikalische Kandidaten** — PostgreSQL-Volltext und `pg_trgm` als Basispfad |
| 3 | **Semantische Erweiterung** — optional, nur additiv, nie als Vollständigkeitsbeleg |
| 4 | **Graph-Erweiterung** — Strang- und Vorgangskanten ziehen Nachbarn hinzu |
| 5 | **Re-Ranking** — Zusammenführung der Kandidatenmengen |
| 6 | **Dossier** — Ausgabe mit Evidenz je Zeile |

v1 hatte Schema und Regeln, aber keinen Antwortpfad — das war eine echte Lücke.

### 4.8 Graph — zwei Ebenen, typisierte Evidenzkanten

```text
edge(from_entity, to_entity,
     type∈{reply,quote,same_subject,shared_participants,temporal_context,calendar_context},
     features jsonb, score numeric, derivation_version)
```

- **Strangebene:** `reply` und belastbare `quote`-Kanten bilden über Union-Find den
  Kommunikationsstrang.
- **Vorgangsebene:** `same_subject`, `shared_participants`, `temporal_context`,
  `calendar_context` erzeugen **Vorgangskandidaten**, nicht Strangzugehörigkeit.
- **Schwache Kanten vereinigen nicht transitiv.** Ohne diese Schranke zieht ein generischer
  Betreff („Rückfrage", „Termin") fremde Stränge zusammen.

Die Skalar-Konfidenzen 0,95/0,70/0,50 aus v1 entfallen — gesetzte Pseudo-Präzision mit genau
einem Konsumenten. Stattdessen ein Dreizustand *sicher / wahrscheinlich / vermutet*, abgeleitet
aus Kantentyp und Clusterkonsistenz.

### 4.9 Beobachtung, Hypothese, Entscheidung

```text
observation(entity_id, kind∈{frage,zusage,frist,anhang,antwortkandidat,termin},
            evidence_span jsonb, parser_version)        -- append-only, abgeleitet
action_item(id, vorgang_id, opened_by_observation, status_projected)
action_event(action_item_id, at, kind∈{bestätigt,erledigt,mündlich_erledigt,
             verworfen,pausiert,wieder_geöffnet}, reason, evidence)   -- append-only
```

Der Zustandsautomat gehört an den **einzelnen offenen Punkt**, nicht an den Vorgang. Nutzerwissen
(mündlich erledigt, nicht relevant, Wiedervorlage) ist ausdrücklich modelliert und **überlebt
jeden Rebuild** — es liegt in der durablen Schicht.

### 4.10 Personen

```text
party(id, label)
identity(party_id, address_norm, display_name, valid_from, valid_to)
identity_link(a, b, kind∈{merge,split}, at, reason)      -- versioniert, umkehrbar
```

`mail wer <name>` löst zuerst eine **Partei** auf und durchsucht danach deren Adressen. Ohne diese
Ebene sind Aliase, Funktionspostfächer und Namensvarianten fachlich unbestimmt — und der zentrale
Befehl hätte keine definierte Semantik.

### 4.11 Ingestion

1. **Ausschluss zuerst** (78,9 %), Grund an den Daten.
2. **Bulk statt Einzelabruf** (Faktor 10,6 gemessen); Graph-Gegenstück `$batch` + `$select`
   — **ungemessen, Messung ist Vorbedingung** (§8 Gate 5).
3. **Gesendet zuerst** — dort entstehen die eigenen Verpflichtungen.
4. **Heißmenge deterministisch starten**: Gesendet, letzte Monate, manuell aktive Vorgänge.
   `query_log` ist **ein** Signal, nicht das einzige; rotierende Stichproben kalter Ordner
   verhindern, dass Nichtbeobachtung sich selbst verstärkt.
5. **Kein Sprachmodell im heißen Pfad.** Zulässige Rollen: Kandidatenerzeugung und
   Dossier-Formulierung. Unzulässig: Identität, Antwortbeziehung oder Erledigung allein bestimmen.

### 4.12 Kalibrierung

| Sonde | Prüft |
|---|---|
| `FROM`, ASCII | Grundfall (bisher einzige Sonde) |
| `TO` / `CC` | die real beobachtete Übermenge |
| Nicht-ASCII (Umlaut-Name) | im deutschsprachigen Korpus der **Normalfall** |
| Ordner außerhalb Gesendet, inkl. Kalenderordner | dort trat die Übermenge auf |

Kriterium `Client ⊆ Server`: zu viele Server-Treffer sind harmlos, zu wenige sehen aus wie ein
Ergebnis. Fällt eine Sonde, wird der Pfad **gesperrt**, nicht nachgebessert.

**Was „gesperrt" genau heißt (Runde 4, M28-3).** Die Gegenlesung weist darauf hin, dass ein
einzelner Parser- oder Sondenfehler bei dieser Formulierung ein ganzes Konto stilllegen kann —
im Ein-Personen-Betrieb ohne Bereitschaft ist das ein Ausfall, kein Schutz. Der Einwand
trifft eine echte Unschärfe: gesperrt wird der **Retrievalpfad**, für den die Sonde steht,
nicht das Konto und nicht der Lauf.

- Fällt die `TO`/`CC`-Sonde, wird die Empfängersuche für dieses Konto auf den lokalen
  Vollscan umgestellt — langsamer, aber vollständig. Absendersuche und Ingestion laufen weiter.
- Fällt eine Sonde für einen Ordner, gilt dieser Ordner als **nicht gedeckt** und erscheint so
  in jeder Deckung. Der Rest des Kontos bleibt nutzbar.
- Nur wenn **kein** Pfad eines Kontos mehr kalibriert ist, gilt das Konto als ungedeckt.

Der Unterschied ist wesentlich: eine gesperrte Abkürzung darf nie zu weniger Treffern führen,
sondern nur zu langsameren. Ein Pfad wird gesperrt, damit die Antwort ehrlich bleibt — nicht,
damit sie ausbleibt.

### 4.13 Dossier

Jede Zeile trägt **Evidenzverweis**, **Ableitungsart** (`beobachtet`/`abgeleitet`),
Dreizustands-Konfidenz, möglichen Gegenbeleg und Deckungszustand. Offene Punkte zeigen Frage,
mutmaßliche Antwort, Grund der Nichtauflösung und nächste Aktion. Aktionen: `resolve` ·
`dismiss` · `snooze` · `split` · `merge` · `show-evidence`.

### 4.14 Werkzeuge der Textgewinnung — der Grundsatz ist „kein Dauerdienst"

**Präzisierung, 2026-08-02.** Runde 3 empfahl Apache Tika für die Anhangs-Extraktion (§11.3,
`[valid]`); die Umsetzung verwarf ihn und hielt fest, die Extraktion komme **ohne
Fremdbibliothek** aus. Das war eine *Auslegung*, keine Anforderung — und sie trug nur so lange,
wie `.docx` das Format war, das die fachliche Substanz trug.

**Was der Grundsatz wirklich verlangt.** Tika wurde verworfen, **weil** es eine JVM und faktisch
einen laufenden Dienst braucht: bei Bus-Faktor 1 und ohne Bereitschaftsdienst ist ein
zusätzlicher Dauerprozess der teuerste Teil der Kette. Der Grundsatz lautet damit **„kein
Dauerdienst"**, nicht „keine Bibliothek". Eine reine Python-Bibliothek verletzt ihn nicht.

**Was die Messung ergab** (HNU, 2026-08-02, Vollerhebung über 119 Ordner, 5.665 Nachrichten):

| Anhangstyp | Anzahl | mit stdlib lesbar |
|---|---|---|
| **PDF** | **1.443** | **nein** |
| `.docx` | 211 | ja |
| `.xlsx` | 64 | ja (ZIP + XML) |
| `.pptx` | 29 | ja (ZIP + XML) |

PDF ist der **Hauptfall**. Eine Auslegung, die ihn ausschließt, macht die Zweckbindung aus §4.5
wertlos: ein aktiver Vorgang bekäme Zugriff auf einen Volltext, der die tragenden Dokumente
gerade nicht enthält.

**Entscheidung.** Für PDF kommt **eine** Bibliothek hinzu: `pdfminer.six` — reines Python, MIT,
kein Dienst, kein Systempaket. Gemessen an 40 echten PDFs liegt sie praktisch gleichauf mit
`pdftotext`/poppler (Median 1.591 gegen 1.697 Zeichen; 28 von 40 gleichauf, 8 zugunsten poppler,
4 zugunsten pdfminer) — der Unterschied rechtfertigt kein Systempaket im Abbild plus
Unterprozess. `PyMuPDF` wäre stärker, steht aber unter **AGPL**; das ist eine Lizenzfrage und
fällt damit unter die ADR-Schwelle, nicht unter Werkzeuggeschmack. `.xlsx` und `.pptx` kommen
ohne weitere Abhängigkeit dazu (ZIP mit XML, wie `.docx`).

**Die Grenze bleibt und wird beziffert: 12,5 % der PDFs haben keine Textebene.** Das sind Scans.
Dafür hilft nur OCR — und OCR *wäre* der Dauerdienst, den dieser ADR verwirft. Sie enden deshalb
als benannter Parserfehler mit gemessener Zeichenzahl, nicht als leerer Erfolg; §4.5 und die
Deckungsbewertung behandeln sie damit korrekt als `partial`. **Ob OCR dazukommt, ist eine eigene
Entscheidung** und braucht einen eigenen ADR — dieser Vermerk trifft sie nicht.

**Was das nicht ändert:** die Zweckbindung (§4.5), die Extraktion bei Vorgangs-Eintritt statt
beim Einlesen (§3.2) und die modellfreie Ingestion. Der Vermerk betrifft ausschließlich die
Frage, mit welchem Werkzeug ein bereits zulässiger Volltext gewonnen wird.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Notizen |
|---|---|---|---|
| `platform` | **P0** Referenzmenge 30–50 Vorgänge + Messskripte | ⬜ | Tor: kein Threading vorher |
| `platform` | **P1a** Bestandszahl klären (§1.4-Widerspruch) | ⬜ | Gate 0, blockiert alle Größenrechnungen |
| `platform` | **P1b** Bulk-Abruf, Gesendet-zuerst, Dossier, `--json` | ⬜ | verbessert den Bestand |
| `dev-hub` | **P2** Rohobjektspeicher, Entität/Vorkommen, Generationen, Deckung | ⬜ | Abbruch bei Vollaufbau > 30 min |
| `dev-hub` | **P3** Volltext, Anhangs-Extraktion, Parteien, Dossier mit Evidenz | ⬜ | Benchmark gegen notmuch/`pg_search` |
| `dev-hub` | **P4** Graph zweistufig, Kantenprovenienz | ⬜ | Falsch-Zusammenführung getrennt gemessen |
| `dev-hub` | **P5** Vorgänge, `action_item`, sechs Zustände | ⬜ | keine Negativaussage ohne volle Deckung |
| `dev-hub` | **P6** Semantik/`pgvector`, nur bei belegtem Zusatz-Recall | ➖ später | entfällt, wenn P5 die Fragen beantwortet |

---

## 6. Consequences

### 6.1 Good
- Negativaussagen sind an Deckung gebunden — die teuerste Fehlerklasse wird strukturell verhindert.
- Der Ausschluss senkt Verarbeitungsmenge, Aufbauzeit und Speicher um rund vier Fünftel.
- Parser- und Algorithmuswechsel sind lokale Neuläufe statt Vollabrufe.
- Kuration überlebt jeden Neuaufbau; abgebrochene Läufe sind unsichtbar.
- Kein Supersede von ADR-286 nötig; der Rückweg zur kleineren Variante bleibt offen.

### 6.2 Bad
- Deutlich mehr Schema als v1: Rohobjekte, Generationen, Entität/Vorkommen, Parteien, drei
  Zustandsschichten.
- Zwei Suchpfade (Projektion und live) können in Normalisierung und Semantik auseinanderlaufen.
- Der Ausschluss macht ältere Korrespondenz unsichtbar — bewusst, aber ein Vorgang kann auf einen
  alten Strang zeigen; dann muss gezielt nachgeladen werden.

### 6.3 Nicht in Scope
- Datenschutz/Aufbewahrung (organisatorisch).
- Mehrbenutzerbetrieb, Web-Oberfläche, Kalender als eigenständiges Zeitsystem.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Bestandszahl veraltet nach einer Umsortierung | Mittel | Mittel | Gate 0 ist erfüllt (§1.4.1), gilt aber als **Wiederholungsauflage** nach jeder Umsortierung |
| Neuaufbau entwertet durable Kuration | Mittel | **Kritisch** | Schichtentrennung §4.1 + Waisen-Zähler |
| Negativaussage auf teilweiser Deckung | Mittel | **Kritisch** | §4.6 sechs Zustände + Gate 1 |
| Falsche Zusammenführung fremder Stränge | Hoch | Hoch | keine transitive Vereinigung schwacher Kanten, Gate 6 |
| `likely_open` wird zum Sammelbecken | Mittel | Hoch | gemessene Zielquote, Gate 8 |
| Überanpassung an einen Realfall | **Hoch** | Hoch | geschichtete Referenzmenge 30–50, Gate 7 |
| Ausgeschlossener Ordner enthält doch Relevantes | Mittel | Mittel | Ausschluss in jeder Deckung namentlich; gezieltes Nachladen möglich |
| Umfang bricht den Ein-Personen-Betrieb | **Hoch** | Hoch | Phasen mit Toren; P6 entfällt bei ausreichendem P5 |
| Parserfehler blockiert Lauf | Mittel | Mittel | Limits, Quarantäne, Generation wird `rejected` |

---

## 8. Confirmation

0. **Bestands-Gate — 🟡 vorläufig erfüllt (§1.4.1, herabgestuft nach Runde 4).** Maßgeblich ist
   **66.580** über 246 Ordner; die ältere Zahl 90.967 war die Ablesung eines vorübergehenden
   Zustands während der Archiv-Umsortierung vom 2026-07-28. Belegt durch: Methodenvalidierung
   (`STATUS` = `SELECT` = `SEARCH`, 4/4, null nicht zählbare Ordner), exakte Übereinstimmung im
   nicht betroffenen Kontrollkonto (9/12) und das Sitzungsprotokoll mit 28.158 verschobenen
   Nachrichten in denselben zwei Konten.
   **Warum nur vorläufig:** Genau das Argument, das die alte Zahl entwertet hat — eine einzelne
   Messung kann einen Zwischenzustand treffen — gilt unverändert gegen die neue. Ein
   Indizienbeweis, der die Vorgängerzahl kippt, trägt seine eigene nicht.
   **Voll erfüllt ist Gate 0 erst,** wenn die Zählung an **drei nicht aufeinanderfolgenden
   Tagen** wiederholt wurde, die **Rohausgabe je Lauf** protokolliert vorliegt und die drei
   Ergebnisse innerhalb einer vorab festgelegten Spanne liegen. Bis dahin dürfen
   Größenrechnungen auf 66.580 aufsetzen, **Gate-Entscheidungen nicht**.
   **Wiederholungsauflage:** Die Zählung wird zusätzlich nach jeder Umsortierung erneut erhoben.
1. **Negativaussage-Gate:** Kein `open` ohne vollständige Deckung. Ein Test mit künstlich
   entferntem Ordner erzeugt `unknown`, **nicht** `open`.
2. **Build-Gate:** Ein mitten im Lauf abgebrochener Aufbau ändert den sichtbaren Stand nicht.
3. **Waisen-Gate:** Nach jedem Neuaufbau **null** verwaiste durable Referenzen; ein simulierter
   `UIDVALIDITY`-Wechsel läuft durch die Migrationsprozedur.
4. **Kalibrier-Gate:** Sonden für `FROM`, `TO`/`CC`, Nicht-ASCII und einen Nicht-Gesendet-Ordner
   laufen je Konto und Transport; eine fallende Sonde sperrt den Pfad.
5. **Benchmark-Gate — 🟡 teilweise erfüllt (§8.5a).** Der Kopfzeilen-Vollaufbau ist **real
   gemessen**: 14.016 Kopfsätze aus 180 behaltenen Ordnern über alle vier Konten und beide
   Transporte in **2,7 min**. Offen bleiben Datenbankschreiben und Normalisierung — die
   existieren erst mit P2. Bei p95 > 10 min: inkrementell für die Heißmenge.
6. **Threading-Gate:** Paarweise Präzision und Recall, **Falsch-Zusammenführungsrate getrennt**,
   Vorgangsabdeckung. Falsche Zusammenführungen werden strenger bestraft als Teilungen; eine
   einzelne „Genauigkeit > 90 %" gilt nicht als bestanden.
7. **Evaluations-Gate:** Vor P4 existiert eine geschichtete Referenzmenge von 30–50 realen
   Vorgängen (Weiterleitungen, generische Betreffs, Ordnerwechsel, Mehrfachkopien, Unicode,
   Anhänge, Termine, parallele Themen). Im selben Zug: einmaliger Benchmark eines fertigen
   lokalen Indexers gegen dieselbe Menge.
8. **`likely_open`-Gate — mit Konsequenz, nicht nur mit Zahl (verschärft nach Runde 4, AD-4).**
   Der Anteil `likely_open` an allen offenen Punkten wird gemessen. Bleibt er dauerhaft über
   dem Schwellwert, **wird einer der drei Hebel aus §4.6 gezogen und die Wahl begründet
   festgehalten** — Scope enger schneiden, Ingestionslücke schließen, oder die Frage als auf
   diesem Bestand nicht beantwortbar ausweisen. Ein reiner Messwert ohne gezogenen Hebel gilt
   als **nicht bestanden**: Gate 8 war bis hierher ein Beobachtungsposten, keine Absicherung.
   Die Schwelle für `open` wird dabei **nicht** gesenkt (Begründung in §4.6).
9. **Dossier-Gate:** Jede Zeile trägt Evidenzverweis und Ableitungsart; eine Zeile ohne beides ist
   ein Fehler.
10. **Zweckbindungs-Gate (neu nach Runde 4, AD-3).** Der Anteil der Nachrichten in aktiven
    Vorgängen an der behaltenen Menge wird gemessen. Überschreitet er dauerhaft **ein Viertel**,
    oder tritt einer der beiden anderen Punkte aus §3.2.1 ein, ist die Zweckbindung nur noch
    ein Etikett — dann ist ein **Supersede von ADR-286** fällig, keine weitere Auslegung von
    dessen §4.8.
11. **Ausschluss-Rückholbarkeits-Gate (neu nach Runde 4, AD-2).** Ein Vorgang, der auf einen
    ausgeschlossenen Ordner zeigt, erzeugt `unknown` und einen Nachlade-Auftrag — **nie** eine
    stille Auslassung. Ein Test mit einem künstlich auf „ausgeschlossen" gesetzten Ordner, der
    nachweislich relevante Nachrichten enthält, muss das zeigen.
12. **Drift-Detector** (ADR-059): Staleness 12 Monate.

---

## 9. More Information

- **Vorstufe:** KONZ-platform-036 — platform#1523
- **Deckungsausweis-Begriffe:** KONZ-platform-035
- **Persistenz darunter:** ADR-286 (§4.10.7 korrigiert, kein Supersede) — platform#1522
- **Werkzeugstand:** `tools/mail_agent/read_mail.py` — platform#1519, platform#1520;
  Ausschlussregel `tools/mail_agent/indexierung.py`
- Externe Runden: `~/shared/review 1.md`, `~/shared/review 2.md`, `~/shared/konzept-hybrid.md`
  (ephemer; Audit hier in §11 + `ai_sparring_by`)

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-08-02 | Claude Code (Opus 5) | **§4.14 neu — Präzisierung des Werkzeug-Grundsatzes.** Die Umsetzung von P3 hatte „Tika verworfen" zu „ohne Fremdbibliothek" verallgemeinert; das war eine Auslegung, keine Anforderung. Der Grundsatz ist **„kein Dauerdienst"** (Tika scheitert an JVM + Hintergrundprozess, nicht an `pip install`). Anlass ist eine Messung, nicht eine Meinung: in der Vollerhebung des Referenzpostfachs stehen **1.443 PDF** gegen 211 `.docx`, 64 `.xlsx`, 29 `.pptx` — PDF ist der Hauptfall, und die stdlib-Auslegung hätte den Volltext eines aktiven Vorgangs gerade um die tragenden Dokumente gekürzt. Aufgenommen: `pdfminer.six` (reines Python, MIT, kein Dienst), an 40 echten PDFs gegen `pdftotext` gemessen und praktisch gleichauf; `PyMuPDF` wegen **AGPL** ausgeschlossen. **Beziffert stehen gelassen: 12,5 % der PDFs haben keine Textebene** — sie enden als benannter Parserfehler und machen die Deckung `partial`, statt als leerer Erfolg durchzugehen. OCR bleibt bewusst draußen und bräuchte einen eigenen ADR. Unverändert: Zweckbindung §4.5, Extraktion bei Vorgangs-Eintritt §3.2, modellfreie Ingestion. |
| 2026-07-29 | Claude Code (Opus 5) | **Runde 4 eingearbeitet (§11.6) — erste externe Gegenlesung dieses Textes statt der Vorstufe.** Sie traf alle drei in §11.5 als ungeprüft benannten Punkte; 7 von 9 Befunden `[valid]`, 2 `[missversteht-Kontext]`. Die folgenreichste Änderung ist eine **Herabstufung**: Gate 0 fällt von ✅ auf 🟡, weil das Argument, mit dem die alte Bestandszahl entwertet wurde (eine Einzelmessung kann einen Zwischenzustand treffen), unverändert gegen die neue gilt — voll erfüllt erst nach drei Wiederholungsmessungen an nicht aufeinanderfolgenden Tagen mit protokollierter Rohausgabe. Neu: **§3.2.1** benennt drei Auslöser, ab denen die Zweckbindung zur Umdeklaration wird und ein Supersede von ADR-286 fällig ist (Gate 10 misst den Anteil); **§3.1 Punkt 1** macht die Ausschlussregel versioniert konfigurierbar und den Ausschluss rückholbar — ein Vorgang auf einem ausgeschlossenen Ordner erzeugt `unknown`, nie eine stille Auslassung (Gate 11); **§4.12** grenzt „gesperrt" auf den Retrievalpfad ein statt auf Konto oder Lauf. **Gate 8** bekommt drei definierte Hebel statt nur eines Messwerts. **Abgelehnt** wurde die Empfehlung, `open` schon ab rund neun Zehnteln Deckung zuzulassen: bei jeder zehnten ungesehenen Nachricht kippt die Negativaussage — der Unterschied zu vollständiger Deckung ist kategorial, nicht graduell (§4.6). Offen und auch nach vier Runden ungegengelesen: die Ausschluss-Messung selbst (§1.4, 52.552 Nachrichten). |
| 2026-07-29 | Claude Code (Opus 5) | **Gate 5 belegt (§1.4.2), P2 damit vorbereitet.** Der Kopfzeilen-Vollaufbau wurde **ausgeführt statt hochgerechnet**: 14.016 Kopfsätze aus 180 behaltenen Ordnern über vier Konten und beide Transporte in **2,7 min** — Schwelle 10 min, Reserve Faktor 3,7. Zwei Erkenntnisse: (a) Der Graph-Transport war als „ungemessen" geführt; der tragende Weg ist nicht `$batch`, sondern der Listen-Abruf mit `$top`+Paging (591 Nachrichten in **einer** Antwort, Faktor 11,7 gegen Einzelabruf). (b) **Mikro-Benchmarks überschätzen systematisch** — 120,7/s bzw. 106,3/s im Einzelordner gegen 92,0/s bzw. 78,5/s im Lauf über 180 Ordner; die Differenz ist Ordnerwechsel-Overhead, also genau der Punkt, an dem die Runden 1 und 2 die Hochrechnungen dieses Entwurfs angegriffen haben. Gate 5 bleibt **teilweise** offen: Datenbankschreiben und Normalisierung existieren erst mit P2, der Messwert ist die untere Schranke. Ebenfalls benannt: es ist ein Lauf, kein p95. |
| 2026-07-29 | Claude Code (Opus 5) | **Gate 0 geschlossen (§1.4.1).** Nachmessung mit ausgewiesenen Fehlern statt stiller Nullen: **66.580** Nachrichten über 246 Ordner in vier Konten, null nicht zählbare Ordner. Der Widerspruch zu ADR-286 §4.10.8 (90.967) ist **ursächlich aufgeklärt**, nicht nur neu gezählt: das nicht betroffene Kontrollkonto trifft die alte Zahl exakt (9 Ordner / 12), während die beiden Konten, in denen am 2026-07-28 laut Session-Retro `d5eb5e` **28.158 Nachrichten verschoben** wurden, zusammen 24.483 weniger zeigen — die alte Messung erfasste einen vorübergehenden Zustand, in dem Nachrichten zugleich im Sammelordner und im neuen Jahresarchiv lagen. Gate 0 wird zur **Wiederholungsauflage** nach jeder Umsortierung. Restlücke benannt: die Ursache ist aus Datum, Konten und Größenordnung erschlossen, nicht aus dem Protokoll der damaligen Zählung. |
| 2026-07-29 | Claude Code (Opus 5) | **v2 nach Runde 3 und einer eigenen Messung.** Neu gemessen: die bestehende Ausschlussregel entfernt **78,9 %** des Bestands (66.562 → 14.018), womit Vollaufbau auf 2,2 min und Rohobjektspeicher auf ~4,5 GB fallen; die Größen-Bedenken der Runden 1–3 entschärfen sich dadurch strukturell. Dabei aufgedeckt: die seit ADR-286 §4.10.8 durchgereichte Zahl **90.967** ist mit der gegengeprüften Methode nicht reproduzierbar (gemessen 66.562) — als **Gate 0** offen geführt statt weggeglättet, weil zwei externe Runden auf der älteren Zahl argumentiert haben. Aus Runde 3 übernommen: inhaltsadressierter Rohobjektspeicher, Leitsatz „Delta an der Quelle, Rebuild in der Projektion" (ersetzt „Neuaufbau schlägt Delta"), **sechs** Ausgabezustände statt zwei, sechsstufige Retrieval-Pipeline, mehrdimensionale Deckung mit fachlicher Konsequenz. **Nicht** übernommen: die volle 25-Tabellen-Grundausstattung und der unbeschränkte Volltextspeicher. Letzteres ist die tragende Abweichung — der Rohobjektspeicher ist **zweckgebunden** (Kopfdaten und Anhänge global, Volltext nur für aktive Vorgänge), wodurch **kein Supersede von ADR-286 nötig** ist und der Rückweg zur kleineren Variante offen bleibt (§3.2). |
| 2026-07-29 | Claude Code (Opus 5) | v1, Status Proposed. Aus KONZ-036 nach zwei externen Runden: §5-These ehrlich umformuliert, Deckungszustand als Bedingung für Negativaussagen, Trennung Cache ↔ Kuration, Build-Generationen, Entität/Vorkommen, Parteien, Graph zweistufig, drei Zustandsschichten, `version_of` gestrichen. Korrigiert ADR-286 §4.10.7. |

---

## 11. Externe Zweitmeinungen — Rückfluss-Tagging

Drei unabhängige Runden auf der Vorstufe KONZ-036 am 2026-07-29. Runden 1 und 2 sind adversariale
Reviews (Verdikt beide „überarbeiten"), Runde 3 ist eine **eigenständige Gegen-Konzeption** mit
16 bewerteten Architekturklassen. Die Einstufung ist Owner-Urteil; nur `[valid]` ist eingeflossen,
als eigene Formulierung, nicht als übernommene Prosa.

### 11.1 Konvergenz Runde 1 + 2

| Befund | R1 | R2 | Wirkung |
|---|---|---|---|
| §5-These im eigenen Dokument gebrochen | AD-2 | AD-1 | §3.1 Punkt 4 |
| 14-Minuten-Zahl unbelegt | AD-1 | AD-3 | Gate 5, §1.4 |
| Durable Kuration hängt an wegwerfbaren IDs | AD-3 | AD-6 | §4.1, Gate 3 |
| Kalibriersonde prüft die falschen Fälle | AD-5 | AD-13 | §4.12, Gate 4 |
| Strang ≠ Vorgang; Skalar-Konfidenzen sind Pseudo-Präzision | AD-6 | AD-8/9 | §4.8 |
| Regressionsmenge n=1 → Überanpassung | B28-2 | AD-14/B28-6 | Gate 7 |
| `signal` braucht Nutzerentscheidungen als eigene Schicht | §13.4 | AD-11 | §4.9 |
| `query_log`-Rückkopplung | B28-4 | AD-12 | §4.11 Punkt 4 |

### 11.2 Einzelbefunde Runde 1 + 2

| Befund | Quelle | Verdikt | Wirkung |
|---|---|---|---|
| Lückenhafter Index trägt keine Negativaussage | R2/AD-4 | `[valid]` — **tiefster Befund** | §4.6, Gate 1 |
| Fehlende Build-Generationen → gemischtes Abbild | R2/AD-5, B28-3 | `[valid]` | §4.4, Gate 2 |
| `message` modelliert Ablageposition | R2/AD-6 | `[valid]` | §4.3 |
| Personenauflösung fehlt | R2/AD-7, B28-5 | `[valid]` | §4.10 |
| Betriebsplan unbestimmt | R2/AD-2 | `[valid]` | §3.1 Punkt 2, §5 |
| Zitat-Entfernung ungemessen | R1/AD-4 | `[valid]` | Gate 7 |
| Exchange EOL, kein Identitäts-Migrationspfad | R1/B28-1 | `[valid]` | §4.1, Gate 3 |
| Zwei Suchpfade driften | R2/B28-1 | `[valid]` | §6.2 |
| Dokumentversionierung nicht per Hash | R1/B28-3, R2/REC-3 | `[valid]` | `version_of` gestrichen |
| notmuch: R1 Spike vs. R2 verwirft — **Runden widersprechen sich** | R1/REC-6, R2/OOB-3 | `[valid, anders]` | Benchmark, kein Architekturpfad (Gate 7) |
| Explizites Tracking | R1/OOB-2, R2/OOB-1 | `[valid, als Ergänzung]` | Kontrollgruppe, kein Ersatz |
| Kalenderkante = Mehrquellen-Zeitsystem | R2/B28-7 | `[out-of-scope]` | in P6, §6.3 |

### 11.3 Runde 3 (Gegen-Konzeption)

| Beitrag | Verdikt | Wirkung |
|---|---|---|
| Inhaltsadressierter Rohobjektspeicher | `[valid]` — **stärkster Einzelbeitrag** | §4.2; macht Parserwechsel zum lokalen Neulauf statt Vollabruf |
| „Delta an der Quelle, Rebuild in der Projektion" | `[valid]` | §3.1 Punkt 2; ersetzt „Neuaufbau schlägt Delta" und löst die Grenzwertrechnung auf |
| Sechs Ausgabezustände | `[valid]` | §4.6; v1 warf „starke Evidenz ohne Deckung" und „keine Ahnung" zusammen |
| Sechsstufige Retrieval-Pipeline | `[valid]` | §4.7; v1 hatte keinen Antwortpfad |
| Mehrdimensionale Deckung mit fachlicher Konsequenz | `[valid]` | §4.5 |
| 16 Architekturklassen mit gewichteter Matrix | `[valid]` | §2 ersetzt die 4-Optionen-Analyse aus v1 |
| Tika für Anhangs-Extraktion | `[valid]` | P3 |
| Parquet/DuckDB für Regressionsauswertung | `[valid, später]` | P6 |
| **Unbeschränkter Volltext im Rohobjektspeicher** | `[valid, anders umgesetzt]` | **zweckgebunden** statt unbeschränkt: Kopfdaten + Anhänge global, Volltext nur für aktive Vorgänge. Grund: Runde 3 kennt ADR-286 nicht (Eingabe war nur KONZ-036) und übersieht daher, dass ein unbeschränkter Volltextspeicher dessen Kern widerspricht. Die zweckgebundene Fassung liefert denselben Nutzen für den Referenzfall ohne Supersede und bleibt umkehrbar (§3.2). |
| **25-Tabellen-Grundausstattung, 7 Phasen** | `[valid, reduziert]` | Bei Bus-Faktor 1 ist Umfang das zentrale Risiko; Runde 3 benennt es selbst (R-10). Übernommen werden die Konzepte, nicht die Grundausstattung auf einmal — die Phasen tragen Tore. |
| Speicherbedarf des Rohobjektspeichers | `[Lücke der Runde]` | nicht beziffert; hier nachgerechnet: ~4,5 GB für die behaltene Menge, ~21,3 GB für den Gesamtbestand — für die Entscheidung unerheblich |

### 11.4 Was keine Runde angegriffen hat

Dossier als Ausgabeobjekt · Bulk-Ingestion · Gesendet-zuerst · kein Sprachmodell im heißen Pfad ·
die Asymmetrie falsch-negativ/falsch-positiv (Runde 1: „das tragfähigste Element des Entwurfs").
Durch drei unabhängige Runden bestätigt.

### 11.5 Was diese Runden nicht leisten konnten

Alle drei bewerteten die **Vorstufe**, nicht diesen Text. Ungeprüft sind damit: die
Ausschluss-Messung aus §1.4 samt des dabei aufgedeckten Zahlen-Widerspruchs, die Zweckbindung des
Rohobjektspeichers (§3.2) und die daraus folgende Entscheidung gegen ein Supersede von ADR-286.
Das sind genau die drei Punkte, an denen eine vierte Runde ansetzen sollte.

### 11.6 Runde 4 — erste Gegenlesung dieses Textes (OpenAI o3, 2026-07-29)

Die erste Runde, die **diesen ADR** bewertet hat statt der Vorstufe. Auftrag war ausdrücklich
die Lückenliste aus §11.5. Verdikt: **überarbeiten**. Sie hat alle drei benannten Lücken
getroffen — der Auftrag hat also funktioniert, was für sich schon eine Aussage über §11.5 ist.

| ID | Befund (verkürzt) | Verdikt | Wirkung |
|---|---|---|---|
| AD-1 | Die Zahlenkorrektur bleibt Indizienbeweis — ohne alte Rohmessung kann auch 66.580 unvollständig sein | `[valid]` — **schärfster Befund** | §1.4.1 + Gate 0 von ✅ auf 🟡 **herabgestuft**; drei Wiederholungsmessungen an nicht aufeinanderfolgenden Tagen mit protokollierter Rohausgabe |
| AD-3 | Die Zweckbindung macht eine Ausnahmeklausel von ADR-286 zur Default-Strategie | `[valid]` | **§3.2.1 neu**: drei benannte Auslöser, ab denen ein Supersede fällig ist; **Gate 10 neu** misst den Anteil |
| AD-4 | Gate 8 misst das `likely_open`-Problem, behebt es aber nicht | `[valid, anders umgesetzt]` | §4.6 + Gate 8: **drei definierte Hebel** statt eines Messwerts. Die vorgeschlagene Schwelle „`open` ab ~90 % Deckung" wird **abgelehnt** — bei jeder zehnten ungesehenen Nachricht kippt die Negativaussage; der Unterschied zu vollständig ist kategorial, nicht graduell |
| AD-2 | Ausschluss verschiebt das Problem nur auf eine manuelle Nachlade-Aktion | `[valid]` | §3.1 Punkt 1: Ausschluss ist nie endgültig, Zustand bis zum Nachladen ist `unknown`; **Gate 11 neu** |
| M28-1 | Ausschlussliste hart kodiert statt versioniert konfigurierbar | `[valid]` | §3.1 Punkt 1: versionierte Konfiguration, Version steht in jeder Deckung |
| M28-3 | Ein Sondenfehler kann ein ganzes Konto stilllegen | `[valid]` | §4.12: „gesperrt" gilt für den **Retrievalpfad**, nicht für Konto oder Lauf; Fallback auf den langsameren Vollscan |
| AD-5 | Ohne dauerhaften Klartext müssen Bodies bei jeder Vorgangs-Revision neu geholt werden | `[missversteht-Kontext]` | Für Nachrichten **in** einem aktiven Vorgang liegt der Volltext lokal (§3.1 Punkt 3) — genau dort, wo wiederholt gearbeitet wird. Anhänge liegen ohnehin inhaltsadressiert (§4.2). Der beschriebene Wiederhol-Abruf tritt im benannten Fall nicht auf |
| M28-2 | Migration bei Schema-Änderungen der durablen Tabellen fehlt | `[missversteht-Kontext]` | §4.4 führt `derivation_version` und `parser_version` je Generation und §4.1 eine definierte Migrationsprozedur samt Waisen-Zähler (Gate 3). Der Befund trifft eine reale Sorge, aber nicht diesen Text |
| PRO-1…4 | Steelman-Seite: Ausschlusshebel, Zweckbindung, Sechs-Zustands-Logik, Schichtentrennung | bestätigend | keine Änderung — deckt sich mit den in §11.4 schon dreifach bestätigten Elementen |

**Nicht übernommene Empfehlungen und warum.** REC-2 (`open` ab ~90 % Deckung) ist abgelehnt,
Begründung in §4.6. REC-4 (Schema-Migration) und REC-6 (Body-Cache mit Verfallszeit) hängen an
den beiden Befunden, die den Kontext missverstehen, und entfallen mit ihnen. Übernommen sind
REC-1, REC-3 und REC-5 — jeweils in eigener Formulierung, nicht als übernommene Prosa.

**Was Runde 4 nicht geleistet hat.** Sie hat die **Ausschluss-Messung selbst** (§1.4, die
78,9 %) nicht angegriffen, sondern nur deren Folgen für ausgeschlossene Jahrgänge (AD-2). Die
Zahl 52.552 und ihre Aufteilung auf die Ordnerklassen bleibt damit auch nach vier Runden
ungeprüft — sie ist gemessen, aber nicht gegengelesen.

---

### 11.7 Runden 5 und 6 — Pre-Mortem auf v2 (2026-08-11)

Zwei unabhängige externe Anbieter, beide im **Pre-Mortem**-Modus („was geht schief, *nachdem*
das akzeptiert und gebaut ist"), beide ohne Sicht auf Repo oder frühere ADRs. Anlass war die
Absicht, diesen ADR auf `accepted` zu heben.

**Beide kommen unabhängig zum selben Verdikt: überarbeiten, nicht akzeptieren.** Nach vier
Runden, die Wortschärfungen erwarten ließen, ist das kein Rauschen — es ist der erste Befund,
den *beide* neuen Runden an dieselbe Stelle setzen: nicht an die Architektur, sondern an den
**Zeitpunkt** des Accept.

Die tragende Aussage, in Runde 1 formuliert: *Ein Accept in der jetzigen Lage beglaubigt einen
Zustand, den der ADR selbst verbietet* — zwei Wahrheitsstände für die Kuration und eine
Gate-Entscheidung auf einer ausdrücklich als vorläufig markierten Zahl (§8 Gate 0 sagt wörtlich,
Gate-Entscheidungen dürften nicht auf 66.580 aufsetzen; der Accept wäre die größte davon).

Volltext beider Runden: `~/shared/adr-handoff-ADR-288-premortem-2026-08-11-response.md`
(ephemer). Dieser Abschnitt ist der durable Nachweis.

#### Konvergenz der beiden Runden

| Sache | R5 | R6 | Wirkung |
|---|---|---|---|
| Accept blockiert, bis Gate 0 wirklich trägt | REC-3 | REC-1 | §8 Gate 0, Status bleibt `proposed` |
| Kuration hat zwei Wahrheitsstände — vor dem Accept auflösen | REC-1 | REC-2 | KONZ-platform-042, neues Gate 13 |
| Dauermess-Gates brauchen mechanische Konsequenz, keine Lesepflicht | REC-4 | REC-7 | §8 Gates 6/8/10 |
| `undated` ist eine eigene Deckungsdimension | REC-5 | REC-6 | §4.5 |

Vier von fünf bzw. acht Empfehlungen decken sich paarweise. Die verbleibenden aus Runde 6 sind
Schema-Befunde, die Runde 5 nicht hatte — darunter ein **im Dokument belegbarer Widerspruch**.

#### Tag-Tabelle (Owner-Urteil vorbehalten)

Eine Zeile je Empfehlungs-ID, 13 von 13 (mechanisch gegengezählt, Skill-Step 5a.2).
**Die Einstufung unten ist ein Vorschlag, keine getroffene Entscheidung** — das Urteil über
externe Befunde bleibt beim Owner.

| ID | Verdikt | Aktion |
|---|---|---|
| R5-REC-1 | `[valid]` | Doppelquelle vor dem Accept auflösen. Deckt sich mit R6-REC-2 und mit einer eigenen Messung vom selben Tag (18 Vorgänge in der Datei, 4 Felder im Modell) → KONZ-platform-042 steigt vom Folge-Thema zum **Accept-Blocker**. Neues Gate 13 „Ein Wahrheitsstand der Kuration". |
| R5-REC-2 | `[valid]` | Neuer Abschnitt „Ist-Anlage": was heute wirklich läuft (11.964 Nachrichten, 145 Ordner, 03:30-Lauf, keine Generationen), und je Gate, ob es dafür gilt. Bis P2 trägt jede Werkzeug-Ausgabe „Vor-ADR-Modus: keine Deckungsgarantie". **Der strukturell wichtigste Punkt beider Runden** — er trennt Zielbild von Ist. |
| R5-REC-3 | `[valid]` | s. R6-REC-1 — die drei Zählungen vor dem Accept ausführen. Aufwand laut eigener Messung Minuten je Lauf. |
| R5-REC-4 | `[valid]` | s. R6-REC-7 — mechanischer Trigger statt Lesepflicht. |
| R5-REC-5 | `[valid]` | s. R6-REC-6 — `undated` als Deckungsdimension. Am 2026-08-11 im Produktivbestand gemessen: **22 Nachrichten ohne Datum**, sie fallen aus jeder Zeitfenster-Abfrage. |
| R6-REC-1 | `[valid]` | Accept blockieren bis Gate 0 abgeschlossen **und** der Ist-Bestand reconciled ist, mit Manifest je Lauf und zeilenweiser Ursachenzuordnung der Differenz zu 11.964/145. „Anderer Scope" als Pauschalerklärung ist ausdrücklich nicht zulässig. |
| R6-REC-2 | `[valid]` | s. R5-REC-1. Zusatz gegenüber R5: JSON nach dem Abgleich **gehasht und read-only** als Migrationsbeleg, plus Regressionstest, der fehlschlägt, sobald ein produktiver Befehl die Datei noch schreibt. |
| R6-REC-3 | `[valid, teilweise vorweggenommen]` | Trennung in durable `message_identity` und generationengebundene `message_projection`. **Vor der Umsetzung gegen die real gebaute Fassung prüfen:** `VorgangsZuordnung` in `dev-hub` weicht laut eigenem Docstring (2026-07-31) bereits bewusst von §4.1 ab und hängt den Fremdschlüssel an `LogicalMessage.kennung`. Ob das die Kritik entkräftet oder bestätigt, ist offen — hier ist der billigste Check ein Rebuild-Test. |
| R6-REC-4 | `[valid]` | `opened_by_observation` durch einen durablen Evidenzanker ersetzen; Test mit geändertem `parser_version` muss zeigen, dass ein Rebuild neue Beobachtungen erzeugen darf, ohne bestehende `action_item` umzudeuten. |
| R6-REC-5 | `[valid]` | Discovery-Probe über ausgeschlossene Ordner vor jeder Negativaussage, plus gemessene Falsch-Ausschlussrate. Trifft **genau die Lücke, die §11.6 selbst benennt**: die 78,9 %/52.552 sind gemessen, aber nach vier Runden nie gegengelesen. Gate 11 deckt nur den bereits verlinkten Fall ab. |
| R6-REC-6 | `[valid]` | Zeitliche Deckung als Vertrag: `coverage_cutoff` und Quell-Watermarks in jeder Ausgabe, Live-Nachzüge als Overlay-Generation, `undated`-Bereich setzt betroffene Aussagen auf `unknown`. |
| R6-REC-7 | `[valid]` | Dreizehn Gates auf drei ausführbare Klassen reduzieren (Accept-Blocker · Laufzeitinvarianten · periodische Review-Metriken), je mit Check, Evidenzartefakt, Auswertungsfenster und fail-closed Konsequenz. |
| R6-REC-8 | `[valid — im Dokument belegt]` | Widerspruch beseitigen: Zeile 194 hält fest, der tragende Graph-Weg sei **nicht** `$batch`, sondern Listen-Abruf mit `$top`+Paging; §4.11 schreibt weiterhin `$batch` + `$select` vor. Gate 5 als End-to-End-p95 mit dem produktiven Commit wiederholen. **Von außen gefunden, ohne Repo-Zugriff — und beim Gegenlesen bestätigt.** |

**Bilanz: 13 Empfehlungen, 13 als `[valid]` vorgeschlagen, 0 als `[missversteht-Kontext]` oder
`[out-of-scope]`.** Das ist ungewöhnlich hoch und selbst ein Befund: Beide Runden zielen fast
ausschließlich auf die Lücke zwischen Dokument und laufender Anlage — eine Lücke, die keine der
vier früheren Runden sehen konnte, weil sie das Konzept vor der Implementierung prüften.

#### Was Runde 5 und 6 nicht geleistet haben

Beide arbeiten am **Zeitpunkt und an der Verankerung**, keine greift die gewählte Architektur an
— was korrekt ist, weil das Briefing sie ausdrücklich als settled ausgewiesen hat. Die
Passungsmatrix aus Runde 3 bleibt damit auch nach sechs Runden ungegengelesen; sie ist begründet,
aber nicht adversarial geprüft.
