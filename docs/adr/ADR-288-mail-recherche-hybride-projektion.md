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
    summary: "Externes LLM (Review 1) auf KONZ-036: Verdikt überarbeiten. Kern: durable Kuration hängt an wegwerfbaren IDs (nächtlicher Neuaufbau zerstört das einzige Produkt), §5-These im eigenen Dokument gebrochen (Köpfe werden längst indexiert), 14-min-Zahl aus einer 300er-Stichprobe eines Ordners hochgerechnet, Kalibriersonde prüft FROM+ASCII statt der real gebrochenen TO/CC- und Unicode-Fälle. Tag-Tabelle §11."
  - tool: other
    date: 2026-07-29
    role: adversarial-review
    summary: "Externes LLM (Review 2) auf KONZ-036: Verdikt überarbeiten. Kern: ein ausgewiesen lückenhafter Index trägt positive Treffer, aber KEINE Negativaussage ('offen', 'unbeantwortet') — eine fehlende Nachricht kehrt den Zustand um; fehlende Build-Generationen erzeugen zeitlich gemischte Abbilder; message modelliert Ablageposition statt Entität; Personenauflösung fehlt ganz. Nachrechnung: 90.967 von theoretisch 95.670 Nachrichten = 95 % des 15-min-Ziels vor jeder Zusatzarbeit. Tag-Tabelle §11."
---

# ADR-288: Adopt a hybrid mail-research projection with build generations, coverage states and a curation layer separated from the rebuildable cache

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed — zur externen Zweitmeinung freigegeben                     |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-29                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | offen · 2× externe KI-Zweitmeinung auf der Vorstufe KONZ-036 (non-accountable, §11) |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | ADR-286 (Mailagent-Persistenz — **§4.10.7 wird hier korrigiert**), KONZ-platform-036 (Vorstufe), KONZ-platform-035 (Deckungsausweis) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `tools/mail_agent/` (Transport, Live-Suche) |
| `dev-hub`      | Primär     | `apps/mail_agent/` (Projektion, Build-Generationen, Dossier) |

> **Scope-Grenze.** Datenschutz, Aufbewahrung und Löschbarkeit sind **nicht** Gegenstand dieser
> Entscheidung; sie sind in ADR-286 und organisatorisch geregelt. Hier geht es ausschließlich um
> Datenmodell, Graph, Wirksamkeit, Bedienung und Betrieb.

---

## Decision Drivers

- **Negativaussagen sind das Produkt.** Der Nutzen des Werkzeugs liegt in „offen", „unbeantwortet",
  „verstummt" — nicht in Trefferlisten. Diese Aussagen kehren sich um, wenn eine Nachricht fehlt.
- **Ein Nutzer, kein Bereitschaftsdienst.** Jede dauerhaft laufende Komponente muss ohne Betreuung
  überleben; komplizierte Synchronisationskorrektheit ist kein tragbarer Dauerposten.
- **Das Postfach bleibt Quelle der Wahrheit**, die Projektion ist abgeleitet — aber das *Produkt*
  des Werkzeugs (Vorgänge, Auflösungen, Entscheidungen) ist es **nicht** und darf nicht mit der
  Projektion verworfen werden.
- **Messbarkeit vor Eleganz.** Jede Stufe braucht ein Abbruchkriterium, das an einer Menge mit
  bekannter Antwort geprüft wird.
- **Reversal**: ADR-286 §4.10.7 („Extraktion beim Einlesen **oder nie**") ist falsch und wird
  hier korrigiert — das begründet den ADR-Rang gegenüber der Vorstufe KONZ-036.

---

## 1. Context and Problem Statement

### 1.1 Der Job

Drei Postfächer, zwei Transportarten, 90.967 Nachrichten in 209 Ordnern:

| Postfach | Transport | Ordner | Nachrichten |
|---|---|---|---|
| A (geschäftlich) | Microsoft Graph, `delta` verfügbar | 90 | 44.878 |
| B (Hochschule) | IMAP, Exchange 2010 | 110 | 46.077 |
| C (Referenz) | IMAP, bekannter Inhalt | 9 | 12 |

Der motivierende Realfall: Eine Fachauskunft **P** beantwortet drei Fragen vom 23.06. nicht; am
20.07. ein Termin; am 21.07. eine dreisätzige Mail, deren Substanz vollständig in einem **Anhang**
steckt; ihre Nachricht und meine Antwort liegen in **zwei verschiedenen Ordnern**. Die drei
Erkenntnisse, die zählten, waren allesamt **Zustandsaussagen über einen Vorgang**, keine
Suchergebnisse. Der Weg dorthin kostete rund ein Dutzend Postfach-Abfragen über drei Konten.

### 1.2 Gemessener Ausgangsstand (2026-07-28/29)

| Messung | Wert |
|---|---|
| Ingestion Einzel-`FETCH` je Nachricht | 10,1/s |
| Ingestion ein `FETCH` je Bereich | **106,3/s** (Faktor 10,6) |
| Live-Suche über 119 Ordner, Absender | 6,8 s |
| Live-Suche über 119 Ordner, Empfänger (To **oder** Cc) | 12,6 s |
| Vorverarbeitung roh → nutzbar | Faktor 182 im Mittel, ~439 Token je Nachricht |
| Rauschanteil (Stichprobe, Untergrenze) | 13–16 % |
| Server-`SEARCH`, ASCII | deckungsgleich mit lokalem Vollscan, 4/4 (u.a. 353/353 von 354) |
| Server-`SEARCH`, Nicht-ASCII | Abbruch der Client-Bibliothek |
| Server-`SEARCH` auf `TO`/`CC` | **7 Treffer ohne den Begriff in irgendeinem Kopffeld** |

Der letzte Wert ist der teuerste: ungeprüft übernommen ergab er **28 statt 21** Treffern — eine
Zahl, die aussah wie ein Ergebnis.

### 1.3 Warum jetzt eine Entscheidung nötig ist

Die Vorstufe (KONZ-036) schlug vor: *Suche bleibt live, der Index existiert nur für Aggregate,
und er darf lückenhaft sein, solange er sagt wo.* Zwei unabhängige externe Reviews haben diesen
Zuschnitt an derselben Stelle gebrochen (§11). Der tragende Einwand:

> Ein ausgewiesen lückenhafter Index trägt **positive** Treffer, aber **keine Negativaussage** —
> gerade eine fehlende Nachricht kehrt „offen" in „erledigt" um und umgekehrt.

Da Negativaussagen das eigentliche Produkt sind, ist das kein Detail, sondern ein
Zuschnittsfehler. Zusätzlich rechnete Review 2 nach: 106,3/s × 15 min = 95.670 Nachrichten; der
Bestand von 90.967 nutzt bereits **95 %** dieser theoretischen Grenze, bevor Ordnerwechsel,
Datenbankschreiben, Parser und Anhänge berücksichtigt sind. Die 14-Minuten-Zahl war aus **einer**
300er-Stichprobe **eines** Ordners hochgerechnet und trug nur Kopfzeilen.

---

## 2. Considered Options

### Option C: Hybride Projektion mit Build-Generationen und Deckungszuständen ✅

Der Index beantwortet **Kopf-Abfragen und Aggregate**; Inhalte werden live nachgeladen; **jede
Antwort trägt einen Deckungszustand** (`vollständig` / `teilweise` / `unbekannt`). Der Aufbau
läuft in Generationen, die validiert und erst dann atomar freigegeben werden; der letzte gültige
Stand bleibt erhalten. Das Schema trennt **wegwerfbaren Cache** von **durabler Kuration**.

- **Gut:** Negativaussagen werden erst dann getroffen, wenn die Deckung sie trägt. Ein
  abgebrochener Lauf ändert nichts Sichtbares. Kuration überlebt jeden Neuaufbau.
- **Schlecht:** Mehr Schema und ein Generationen-Begriff, den ein Ein-Personen-Betrieb pflegen muss.

### Option A: Voll-Spiegel mit eigener Suchschicht

Alles in die Datenbank, dort auch Volltextsuche.

- Verworfen: erfordert dauerhafte Synchronisationskorrektheit über zwei Transporte und beantwortet
  die eigentlich wertvollen Fragen nicht besser. Der gemessene Gewinn gegen Live-Suche liegt bei
  ~34 Sekunden pro Tag.

### Option B: Reine Live-Suche ohne Projektion (die Vorstufe KONZ-036)

- Verworfen aus zwei gemessenen Gründen: die Live-Suche verfehlt mit 6,8–12,6 s bereits das
  eigene „< 5 s"-Ziel, und Aggregate über Zeit („was ist offen") sind live gar nicht bildbar.
  Beide Reviews stellten unabhängig fest, dass der Entwurf Köpfe ohnehin indexiert
  (`participant`, Trigram) — die Selbstbeschreibung war schlicht unehrlich.

### Option D: Fertiger lokaler Indexer (`mbsync` + `notmuch`) als Primärarchitektur

- Verworfen als Architektur: verlagert Identität in eine zweite Schicht, löst weder Vorgangs-
  zuschnitt noch Zustände, und die M365-Anbindung ist unelegant. **Nicht verworfen als Messlatte:**
  ein zeitlich begrenzter Benchmark seiner Threading-Güte gegen die eigene Referenzmenge ist
  billiger als jede Diskussion darüber (§8 Gate 7).

---

## 3. Decision Outcome

**Gewählt: Option C.**

Der Zuschnitt der Vorstufe bleibt bestehen — Vorgang statt Trefferliste, Aggregate statt Suche,
Kalibrierung statt Vertrauen. Die Mechanik wird an fünf Stellen korrigiert:

1. **§5-These ehrlich**: Kopf-Abfragen und Aggregate aus der Projektion, Inhalte live, jede Antwort
   mit Deckungszustand.
2. **Zwei Schichten**: wegwerfbarer Cache ↔ durable Kuration, mit transportstabilen Referenzen.
3. **Build-Generationen** mit Validierung, atomarer Freigabe und letztem gültigem Stand.
4. **Graph in zwei Ebenen**: Kommunikationsstrang ≠ Vorgang; schwache Kanten vereinigen nicht
   transitiv.
5. **Drei Schichten für Zustand**: Beobachtung (append-only) → Hypothese (projiziert) →
   Nutzerentscheidung (append-only Ereignisse, je offenem Punkt).

**Korrektur an ADR-286 §4.10.7:** Der Satz „Weil Bodies nicht dauerhaft gespeichert werden, ist
Extraktion beim Einlesen **oder nie**" ist falsch. ADR-286 §4.8 sagt bereits das Richtige — das
Postfach hält den Inhalt, er ist nachladbar. Damit wird Extraktion **wiederholbar**:

| | Extraktion beim Einlesen | Extraktion bei Vorgangs-Eintritt |
|---|---|---|
| Nachrichten | 90.967 | die im aktiven Vorgang |
| Token (à ~439) | ~40 Mio. | ~1 Mio. bei 2 % |
| Ingestion | modellgebunden | modellfrei |
| Schema-Fehler rückwirkend heilbar | **nein** | **ja** |

---

## 4. Implementation Details

### 4.1 Zwei Schichten — Cache und Kuration

**Wegwerfbar (drop & rebuild):** `message_entity`, `message_occurrence`, `participant`,
`attachment_occurrence`, `edge`, `thread`, abgeleitete `observation`.

**Durabel (überlebt jeden Neuaufbau):** `vorgang`, `open_point`, `decision_event`, `party`,
`identity_link`, `query_log`, `regression_case`.

Durable Referenzen zeigen **nie** auf Surrogat-IDs des Cache, sondern auf
`(account_id, transport_key)` plus die logische Entität. Ein `UIDVALIDITY`-Wechsel oder ein
Postfach-Umzug bekommt eine definierte Migrationsprozedur; ein Zähler **verwaister durabler
Referenzen** läuft nach jedem Aufbau (§8 Gate 3).

Ohne diese Trennung zerstört der nächtliche Lauf auf Dauer das Einzige, was das Werkzeug
produziert — der stärkste Einwand aus Review 1.

### 4.2 Entität und Vorkommen

`message` in der Vorstufe modellierte eine **Ablageposition**, nicht eine Nachricht. Dieselbe
logische Nachricht existiert in Gesendet und Posteingang, in Archivkopien, und wechselt beim
Verschieben ihre Transportidentität — Zählungen, Signale und Anhänge wirken dadurch doppelt.

```text
message_entity(id, content_fingerprint, sent_at, subject_norm, …)
message_occurrence(entity_id, account_id, folder_id, transport_key, seen_in_generation)
attachment_occurrence(occurrence_id, filename, mime, sha256, text_extract)
```

`sha256`-Gleichheit belegt **Identität, nicht Versionsnachfolge**. Die Spalte `version_of` aus der
Vorstufe entfällt ersatzlos; Dokumentversionierung ist ein eigenes Problem und wird nicht in einer
Schemaspalte versteckt (beide Reviews, unabhängig).

### 4.3 Build-Generationen

```text
build_generation(id, started_at, finished_at, status∈{building,valid,published,failed},
                 derivation_version, parser_version)
folder_scan(generation_id, account_id, folder_path, expected, read, errors, watermark)
```

Ein Lauf baut in eine neue Generation, wird gegen Invarianten validiert und **erst danach atomar
freigegeben**. Der letzte veröffentlichte Stand bleibt erhalten. Ein abgebrochener Lauf ist
unsichtbar; ohne dieses Modell entsteht während eines mehrminütigen Scans ein zeitlich gemischtes
Abbild, und ein Teilergebnis kann trotz plausibler Ordnerzähler ausgeliefert werden.

`derivation_version` und `parser_version` wandern in die Ausgabe — sonst ist in zwei Jahren nicht
mehr erklärbar, warum ein Vorgang 2026 anders aussah als 2028.

### 4.4 Deckungszustand statt „darf lückenhaft sein"

Jede Antwort trägt `vollständig` / `teilweise` / `unbekannt`.

> **Harte Regel: Eine Negativaussage („offen", „unbeantwortet", „verstummt") wird nur bei
> Deckungszustand `vollständig` getroffen.** Bei `teilweise` wird der offene Punkt als
> *unbestimmt* geführt, nicht als offen. Eine partielle Abfrage darf niemals wie eine gewöhnliche
> Leermenge aussehen.

Die Deckungszeile weist Scanintervall, fehlgeschlagene Ordner, Parserfehler und die verwendete
Generation aus — Ordnerzähler und ein Zeitstempel allein sind keine semantische Deckung.

### 4.5 Graph — zwei Ebenen, typisierte Evidenzkanten

```text
edge(from_entity, to_entity, type∈{reply,quote,same_subject,shared_participants,
                                    temporal_context,calendar_context},
     features jsonb, score numeric, derivation_version)
```

- **Strangebene:** `reply` und belastbare `quote`-Kanten bilden über Union-Find den
  Kommunikationsstrang (JWZ-artig, Strang = Zusammenhangskomponente).
- **Vorgangsebene:** `same_subject`, `shared_participants`, `temporal_context`,
  `calendar_context` erzeugen **Vorgangskandidaten**, nicht Strangzugehörigkeit.
- **Schwache Kanten vereinigen nicht transitiv.** Ohne diese Schranke zieht ein generischer
  Betreff („Rückfrage", „Termin") fremde Stränge zusammen.

Die Skalar-Konfidenzen 0,95/0,70/0,50 der Vorstufe entfallen — sie waren gesetzte Pseudo-Präzision
mit genau einem Konsumenten. An ihre Stelle tritt ein Dreizustand *sicher / wahrscheinlich /
vermutet*, abgeleitet aus Kantentyp und Clusterkonsistenz.

### 4.6 Beobachtung, Hypothese, Entscheidung

```text
observation(entity_id, kind∈{frage,zusage,frist,anhang,antwortkandidat,termin},
            evidence_span jsonb, parser_version)          -- append-only, abgeleitet
open_point(id, vorgang_id, opened_by_observation, status_projected)
decision_event(open_point_id, at, kind∈{bestätigt,erledigt,mündlich_erledigt,
               verworfen,pausiert,wieder_geöffnet}, reason, evidence)   -- append-only
```

Der Zustandsautomat gehört an den **einzelnen offenen Punkt**, nicht an den Vorgang: ein Vorgang
hat mehrere offene Punkte mit unterschiedlichem Schicksal. Beobachtungen sind unveränderlich und
neu ableitbar; Nutzerwissen (mündlich erledigt, nicht relevant, Wiedervorlage) ist ausdrücklich
modelliert statt in eine berechnete Schicht gezwungen.

### 4.7 Personen — `address_norm` ist keine Person

```text
party(id, label)
identity(party_id, address_norm, display_name, valid_from, valid_to)
identity_link(a, b, kind∈{merge,split}, at, reason)      -- versioniert, umkehrbar
```

`mail wer <name>` löst zuerst eine **Partei** auf und durchsucht danach deren Adressen. Ohne diese
Ebene sind Aliase, Funktionspostfächer, mehrere Adressen derselben Person und Namensvarianten
fachlich unbestimmt — und der zentrale Befehl des Werkzeugs hat keine definierte Semantik.

### 4.8 Ingestion

1. **Bulk statt Einzelabruf** (Faktor 10,6 gemessen); Graph-Gegenstück `$batch` + `$select`
   — **ungemessen, Messung ist Vorbedingung** (§8 Gate 5).
2. **Gesendet zuerst** — dort entstehen die eigenen Verpflichtungen.
3. **Heißmenge deterministisch starten**: Gesendet, letzte Monate, manuell aktive Vorgänge.
   `query_log` ist **ein** Signal, nicht das einzige; rotierende Stichproben kalter Ordner
   verhindern, dass Nichtbeobachtung sich selbst verstärkt.
4. **Fortschreitend nützlich**: neueste zuerst, heiße Ordner zuerst.
5. **Kein Sprachmodell im heißen Pfad** — deterministische Merkmale zuerst.

### 4.9 Kalibrierung

Mehrere Sonden statt einer, je Transport und je Operation:

| Sonde | Prüft |
|---|---|
| `FROM`, ASCII | Grundfall (bisher einzige Sonde) |
| `TO` / `CC` | die real beobachtete Übermenge |
| Nicht-ASCII (Umlaut-Name) | im deutschsprachigen Korpus der **Normalfall**, nicht der Randfall |
| Ordner außerhalb Gesendet, inkl. Kalenderordner | dort trat die Übermenge auf |

Kriterium bleibt `Client ⊆ Server`: zu viele Server-Treffer sind harmlos, zu wenige sehen aus wie
ein Ergebnis. Fällt eine Sonde, wird der betroffene Pfad **gesperrt**, nicht nachgebessert.

### 4.10 Dossier

Jede Zeile trägt **Evidenzverweis**, **Ableitungsart** (`beobachtet` / `abgeleitet`),
Dreizustands-Konfidenz, möglichen Gegenbeleg und Deckungszustand. Offene Punkte zeigen zugehörige
Frage, mutmaßliche Antwort, Grund der Nichtauflösung und nächste Aktion. Aktionen:
`resolve` · `dismiss` · `snooze` · `split` · `merge` · `show-evidence`.

Ohne Bestätigen/Verwerfen/Pausieren wird eine Liste, die gelegentlich bereits Erledigtes meldet,
binnen Wochen ignoriert.

---

## 5. Migration Tracking

| Repo / Service | Stufe | Status | Datum | Notizen |
|---|---|---|---|---|
| `platform` | S1 (Bulk-Abruf, Gesendet-zuerst, Dossier-Ausgabe, `--json`) | ⬜ | – | verbessert den Bestand |
| `dev-hub` | S2 (Cache-Schema, Build-Generationen, Deckungszustand) | ⬜ | – | Abbruch bei Vollaufbau > 30 min |
| `dev-hub` | **S2a** (Entität/Vorkommen, Personenauflösung, Evaluationswerkzeug) | ⬜ | – | neu aus §11 |
| `dev-hub` | **S2b** (Dossier-on-demand, explizites Tracking als Kontrollgruppe) | ⬜ | – | neu aus §11; kann S3 verkleinern |
| `dev-hub` | S3 (Graph zweistufig, `observation`/`open_point`, `mail offen`) | ⬜ | – | erst nach S2a/S2b |
| `dev-hub` | S4 (Anhangs-Extraktion, Kalenderkante, ggf. Semantik) | ➖ später | – | entfällt, wenn S3 die Fragen beantwortet |

---

## 6. Consequences

### 6.1 Good
- Negativaussagen sind an Deckung gebunden — die teuerste Fehlerklasse wird strukturell verhindert.
- Kuration überlebt jeden Neuaufbau; der Cache bleibt wegwerfbar.
- Abgebrochene Läufe sind unsichtbar; es gibt immer einen letzten gültigen Stand.
- Falsche Zusammenführungen werden getrennt gemessen statt in einer Gesamtquote versteckt.

### 6.2 Bad
- Deutlich mehr Schema als die Vorstufe: Generationen, Entität/Vorkommen, Parteien, drei
  Zustandsschichten.
- S3 rückt nach hinten; der eigentliche Nutzen kommt später.
- Zwei Suchpfade (Projektion und live) können in Normalisierung und Semantik auseinanderlaufen —
  jeder fachliche Suchfehler ist an zwei Stellen zu reparieren.

### 6.3 Nicht in Scope
- Datenschutz/Aufbewahrung (ADR-286 + organisatorisch).
- Mehrbenutzerbetrieb, Web-Oberfläche, Kalender als eigenständiges Zeitsystem.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|---|---|---|---|
| Vollaufbau sprengt das nächtliche Fenster (95 % der theoretischen Grenze bereits genutzt) | **Hoch** | Hoch | Produktions-Benchmark vor S2 (§8 Gate 5); bei p95 > 10 min auf inkrementell für die Heißmenge |
| Neuaufbau entwertet durable Kuration | Mittel | **Kritisch** | Schichtentrennung §4.1 + Waisen-Zähler (§8 Gate 3) |
| Negativaussage auf teilweiser Deckung | Mittel | **Kritisch** | Harte Regel §4.4 + Gate 1 |
| Falsche Zusammenführung fremder Stränge | Hoch | Hoch | keine transitive Vereinigung schwacher Kanten (§4.5), getrennte Messung (§8 Gate 6) |
| Überanpassung an einen Realfall | **Hoch** | Hoch | geschichtete Referenzmenge 30–50 Vorgänge vor S3 (§8 Gate 7) |
| Zwei Suchpfade driften semantisch | Mittel | Mittel | gemeinsame Normalisierungsbibliothek, Sonden gegen beide Pfade |
| Signal-Muster sprachabhängig und spröde | Hoch | Mittel | explizites Tracking als Kontrollgruppe (S2b), Präzision gegen Referenzmenge gemessen |

---

## 8. Confirmation

1. **Negativaussage-Gate:** Kein `mail offen`-Eintrag ohne Deckungszustand `vollständig`. Ein Test
   mit künstlich entferntem Ordner erzeugt `unbestimmt`, **nicht** „offen".
2. **Build-Gate:** Ein mitten im Lauf abgebrochener Aufbau ändert den sichtbaren Stand nicht; der
   letzte veröffentlichte Stand bleibt abfragbar.
3. **Waisen-Gate:** Nach jedem Neuaufbau **null** verwaiste durable Referenzen; ein simulierter
   `UIDVALIDITY`-Wechsel läuft durch die Migrationsprozedur.
4. **Kalibrier-Gate:** Sonden für `FROM`, `TO`/`CC`, Nicht-ASCII und einen Nicht-Gesendet-Ordner
   laufen je Konto und Transport; eine fallende Sonde sperrt den Pfad.
5. **Produktions-Benchmark-Gate:** Vor S2 wird der **tatsächliche** Vollaufbau gemessen — alle drei
   Konten, alle 209 Ordner, inklusive `SELECT`-Overhead, Graph-`$batch`, Datenbankschreiben,
   Normalisierung und Fehlerwiederholung. Die 14-Minuten-Zeile wird durch den Messwert ersetzt.
   Bei p95 > 10 min oder wiederkehrender Serverdrosselung: inkrementell für die Heißmenge.
6. **Threading-Gate:** Gemessen werden paarweise Präzision und Recall, **Falsch-Zusammenführungs-
   rate getrennt** und Vorgangsabdeckung. Falsche Zusammenführungen werden strenger bestraft als
   Teilungen; eine einzelne „Genauigkeit > 90 %" gilt nicht als bestanden.
7. **Evaluations-Gate:** Vor S3 existiert eine geschichtete Referenzmenge von 30–50 realen
   Vorgängen (Weiterleitungen, generische Betreffs, Ordnerwechsel, Mehrfachkopien, Unicode,
   Anhänge, Termine, parallele Themen). Im selben Zug: einmaliger Benchmark eines fertigen
   lokalen Indexers gegen dieselbe Menge, als Messlatte für die eigene Threading-Güte.
8. **Dossier-Gate:** Jede Zeile trägt Evidenzverweis und Ableitungsart; eine Zeile ohne beides ist
   ein Fehler, keine Anzeige.
9. **Drift-Detector** (ADR-059): Staleness 12 Monate.

---

## 9. More Information

- **Vorstufe:** KONZ-platform-036 (portables Entwurfsdokument, Stand v1) — platform#1523
- **Deckungsausweis-Begriffe:** KONZ-platform-035
- **Persistenz-Entscheidung darunter:** ADR-286 (§4.10.7 wird hier korrigiert) — platform#1522
- **Werkzeugstand:** `tools/mail_agent/read_mail.py` — platform#1519 (Ordner-Walk mit
  ausgewiesenem Nenner), platform#1520 (Kalibriersonde, Deckungsausweis, `--json`)
- Externe Zweitmeinungen zur Vorstufe: `~/shared/review 1.md`, `~/shared/review 2.md`
  (ephemer; Audit hier in §11 + `ai_sparring_by`)

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-29 | Claude Code (Opus 5) | Initial, Status **Proposed**. Entstanden aus KONZ-036 nach zwei unabhängigen externen adversarialen Reviews, die den Zuschnitt der Vorstufe an derselben Stelle brachen. Kernänderungen gegenüber KONZ-036: §5-These ehrlich umformuliert (Kopf-Abfragen und Aggregate aus der Projektion statt „Suche bleibt live"), Deckungszustand als harte Bedingung für Negativaussagen, Trennung wegwerfbarer Cache ↔ durable Kuration mit transportstabilen Referenzen, Build-Generationen mit atomarer Freigabe und letztem gültigem Stand, Entität/Vorkommen statt Ablageposition, Parteien-/Identitätsauflösung als eigene Ebene, Graph zweistufig mit typisierten Evidenzkanten ohne transitive Vereinigung schwacher Kanten, drei Zustandsschichten (Beobachtung/Hypothese/Entscheidung) mit Automat je offenem Punkt, erweiterte Kalibriersonden (TO/CC, Nicht-ASCII, Nicht-Gesendet-Ordner), `version_of` ersatzlos gestrichen. Neue Stufen S2a/S2b vor S3. Korrigiert **ADR-286 §4.10.7** („Extraktion beim Einlesen oder nie") als falsch — §4.8 derselben ADR sagt bereits das Richtige. |

---

## 11. Externe KI-Zweitmeinung — Rückfluss-Tagging

Zwei unabhängige Runden auf der Vorstufe KONZ-036 am 2026-07-29, beide Verdikt **„überarbeiten"**,
keine „verwerfen". 43 Befunde, 21 Änderungsvorschläge. Die Einstufung ist Owner-Urteil; nur
`[valid]` ist eingeflossen, und zwar als eigene Formulierung, nicht als übernommene Prosa.

### 11.1 Konvergenz — von beiden Runden unabhängig gefunden

| Befund | R1 | R2 | Verdikt | Wirkung |
|---|---|---|---|---|
| §5-These im eigenen Dokument gebrochen (Köpfe werden längst indexiert) | AD-2 | AD-1 | `[valid]` | §3 Punkt 1, §2 Option B verworfen |
| 14-Minuten-Zahl unbelegt (eine Stichprobe, ein Ordner, nur Kopfzeilen) | AD-1 | AD-3 | `[valid]` | §8 Gate 5 |
| Durable Kuration hängt an wegwerfbaren IDs | AD-3 | AD-6 | `[valid]` | §4.1, §8 Gate 3 |
| Kalibriersonde prüft die falschen Fälle | AD-5 | AD-13 | `[valid]` | §4.9, §8 Gate 4 |
| Strang ≠ Vorgang; Skalar-Konfidenzen sind Pseudo-Präzision | AD-6 | AD-8/9 | `[valid]` | §4.5 |
| Regressionsmenge n=1 führt zur Überanpassung | B28-2 | AD-14/B28-6 | `[valid]` | §8 Gate 7 |
| `signal` braucht Nutzerentscheidungen als eigene Schicht | §13.4 | AD-11 | `[valid]` | §4.6 |
| `query_log`-Rückkopplung (unerschlossene Ordner werden nie heiß) | B28-4 | AD-12 | `[valid]` | §4.8 Punkt 3 |

### 11.2 Einzelbefunde mit Wirkung

| Befund | Quelle | Verdikt | Wirkung |
|---|---|---|---|
| Lückenhafter Index trägt keine Negativaussage | R2/AD-4 | `[valid]` — **der tiefste Befund beider Runden** | §4.4 harte Regel, §8 Gate 1 |
| Fehlende Build-Generationen → zeitlich gemischtes Abbild, Teilergebnisse sichtbar | R2/AD-5, B28-3 | `[valid]` | §4.3, §8 Gate 2 |
| `message` modelliert Ablageposition statt Entität | R2/AD-6 | `[valid]` | §4.2 |
| Personenauflösung fehlt vollständig | R2/AD-7, B28-5 | `[valid]` | §4.7 |
| Betriebsplan unbestimmt (Heiß kontinuierlich + Kalt nächtlich + „≤ 1 Dienst") | R2/AD-2 | `[valid]` | §4.8, §5 Stufenplan |
| Zitat-Entfernung ungemessen → falsche `frage`-Signale | R1/AD-4 | `[valid]` | §8 Gate 7, S2b Kontrollgruppe |
| Exchange 2010 ist EOL; kein Identitäts-Migrationspfad | R1/B28-1 | `[valid]` | §4.1 Migrationsprozedur, §8 Gate 3 |
| Zwei Suchpfade driften semantisch auseinander | R2/B28-1 | `[valid]` | §6.2, §7 |
| S3-Schätzung scheitert an der Referenzmenge, nicht am Code | R2/B28-6 | `[valid]` | S2a als eigene Stufe |
| Durchsatz-50 %-Signal und 90-Tage-Demotion verfrüht | R1/B28-4, R2/§13.6 | `[valid]` | erst nach gefülltem `query_log` |

### 11.3 Abweichend übernommen oder abgelehnt

| Befund / Vorschlag | Quelle | Verdikt | Begründung |
|---|---|---|---|
| Vier-Tabellen-Split inkl. `document`/`document_version` | R2/REC-3 | `[valid, anders umgesetzt]` | Entität/Vorkommen übernommen; Dokumentversionierung **nicht** — beide Runden sagen unabhängig, dass Hashgleichheit nur Identität belegt (R1/B28-3 fordert `version_of` zu streichen). Die Spalte entfällt statt ausgebaut zu werden. |
| `mbsync`+`notmuch` | R1/REC-6 (Spike vor S2) vs. R2/OOB-3 (als Architektur verworfen) | `[valid, anders umgesetzt]` | **Die Runden widersprechen sich.** Beide wollen es messen, keine will es übernehmen → einmaliger Benchmark gegen die Referenzmenge (§8 Gate 7), kein Architekturpfad. |
| Explizites Verpflichtungsjournal / `mail track` | R1/OOB-2, R2/OOB-1 | `[valid, als Ergänzung]` | Nicht als Ersatz für automatische Erkennung — als **Kontrollgruppe** in S2b, damit der Zusatznutzen der Automatik messbar wird. |
| Kalenderkante macht daraus ein Mehrquellen-Zeitsystem | R2/B28-7 | `[out-of-scope]` | Inhaltlich richtig, aber die Kante liegt in S4 hinter einem Abbruchkriterium. Als benannte Grenze in §6.3, keine Änderung. |

### 11.4 Was keine Runde angegriffen hat

Dossier als Ausgabeobjekt · Bulk-Ingestion · Gesendet-zuerst · kein Sprachmodell im heißen Pfad ·
die Asymmetrie falsch-negativ/falsch-positiv (Review 1: „das tragfähigste Element des Entwurfs").
Diese Elemente gelten als durch zwei unabhängige Runden bestätigt.

### 11.5 Was diese Runde nicht leisten konnte

Beide Runden bewerteten die **Vorstufe**, nicht diesen Text. Die hier getroffenen Entscheidungen —
insbesondere die Schichtentrennung §4.1, die Generationen §4.3 und die harte Negativaussage-Regel
§4.4 — sind **ungeprüft**. Genau dafür geht dieser ADR in eine dritte Runde.
