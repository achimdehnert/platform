---
status: accepted
decision_date: 2026-07-24
deciders: Achim Dehnert
consulted: –
informed: –
ai_sparring_by:
  - tool: other
    date: 2026-07-24
    role: adversarial-review
    summary: "Externes LLM (Review 1): Verdikt überarbeiten; kritisch: Metadaten sind PII (append-only ≠ Art.17), Key-Store = neue Klartext-DB, UNIQUE(internet_message_id) falsch, abgeleitete Artefakte = zweiter Klartext. Tag-Tabelle im Body §11."
  - tool: other
    date: 2026-07-24
    role: adversarial-review
    summary: "Externes LLM (Review 2): Verdikt überarbeiten; Kern: keine monotone Löschung (Quellmailbox/alte Schlüssel/Restore), Identität in LogicalMessage/MailCopy trennen, Erasure-Ledger + Restore-Gate. Beide Reviews schlugen unabhängig Option D (Metadaten-Index + JIT-Bodies) vor. Tag-Tabelle im Body §11."
---

# ADR-286: Adopt a metadata-index-first mail agent with purpose-bound crypto-shredded body persistence

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Accepted                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-24                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | Achim Dehnert (approved 2026-07-24) · 2× externe KI-Zweitmeinung (non-accountable, §11)             |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | KONZ-platform-034 (Postgres-Mailagent), KONZ-033 (Rollen-Mail-Identität) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `tools/mail_agent/` (Transport-Layer)    |
| `dev-hub`      | Primär     | `apps/mail_agent/` (Django-App, Postgres, celery)     |
| `risk-hub`     | Sekundär   | `create_deletion_request` → Erasure-Ledger-Eintrag    |

---

## Decision Drivers

- **Datenhoheit/DSGVO**: Persistente Mail-Daten enthalten Personendaten (IIL-Kunden, DSGVO-Mandanten).
  Ohne monotonen, restore-festen Löschpfad nicht betreibbar (Art. 17).
- **Metadaten sind Personendaten**: `from`/`to`/`subject`/`thread_key` tragen Klarnamen/Sachverhalte —
  eine reine Body-Löschung erfüllt Art. 17 *nicht* (externe Reviews, §11).
- **Datenminimierung**: Der billigste Weg, Art. 17 für Inhalte zu erfüllen, ist, Inhalte gar nicht
  dauerhaft zu speichern, außer wenn ein Vorgang es rechtfertigt.
- **Zweckbindung/AVV**: MEiKI läuft über einen HNU-Auftragsverarbeiter — eine private Zweitkopie
  personenbezogener kritischer Daten ist potenziell weisungswidrig; braucht technische *und*
  vertragliche Grenze.
- **Neue Service-Boundary**: Neue Postgres-DB + Ingestion über heterogene Transporte = echte
  Architektur-Entscheidung mit Sicherheits-/Datenschutz-Perimeter.

---

## 1. Context and Problem Statement

KONZ-platform-034 empfiehlt einen Mailagenten (Erfassung + Historie + Assistenz). Zwei externe
adversariale Zweitmeinungen (§11) haben die erste ADR-Fassung („crypto-geschredderter Voll-Index mit
Metadaten-append-only") als **überarbeitungsbedürftig** befunden: der Löschanspruch war **nicht
monoton** (Quellmailbox, alte Schlüsselstände, Restore, abgeleitete Artefakte konnten gelöschte
Inhalte wieder verfügbar machen), das Identitätsmodell (`UNIQUE(internet_message_id)`) war falsch, und
Metadaten wurden als nicht-personenbezogen behandelt. Diese Fassung integriert die validen Befunde.

### 1.1 Ist-Zustand

| Komponente | Stand |
|---|---|
| `platform/tools/mail_agent/` | stdlib IMAP/SMTP/Graph, **kein** DB-Store |
| `~/.claude/mail-vorgaenge.json` | leichter JSON-Vorgangs-Store |
| dev-hub | Postgres/Redis/celery/aifw vorhanden, kein Mail-App |
| Löschpfad | risk-hub `create_deletion_request` (wird zum Erasure-Ledger-Eintritt) |

### 1.2 Warum jetzt

Owner-Entscheid 2026-07-24: KONZ-034 bauen, Kanal 1 dehnert.team, aifw Phase 3. Die Datenarchitektur
muss vor dem ersten Prod-Datensatz stehen — nachträgliche Redaction ist teuer (Maintainer-Befunde §11).

---

## 2. Considered Options

### Option D: Metadaten-Index-first, Bodies nur just-in-time / zweckgebunden persistiert ✅

Postgres hält **standardmäßig nur minimierte Metadaten + Compliance-Zustand**. Mail-Bodies/Anhänge
werden bei Bedarf **live aus dem Postfach** geholt und höchstens in einem **kurzlebigen verschlüsselten
TTL-Cache** gehalten. **Dauerhafte** Body-Persistenz nur, wenn ein Vorgang sie ausdrücklich markiert —
dann mit Envelope-Encryption + Crypto-Shredding (die frühere „Option A" als *zweckgebundener
Untermodus*).

**Pros:**
- Art. 17 für Bodies **per Konstruktion** erfüllt (kein Default-Body-Store → nichts zu löschen).
- Backups enthalten standardmäßig keinen Mailinhalt; Key-Lifecycle klein.
- Mehr als „kein Store": Metadaten-Projektion, Drift-Messung, Erasure-Ledger bleiben dauerhaft.

**Cons:**
- Such-/Assistenz-Latenz, Postfach-Verfügbarkeits-Abhängigkeit; kein Body-Volltext ohne Zweckbindung.
- Zwei Persistenz-Pfade (Metadaten immer, Bodies zweckgebunden) — mehr Produktlogik.

### Option A: Crypto-geschredderter Voll-Index (Bodies immer persistiert)

**Pros:** Voller Body-Volltext offline.
**Cons:** Großer Key-/Backup-/Restore-Angriffs- und Löschumfang → **abgelehnt als Default**, überlebt
nur als **zweckgebundener Untermodus** von D.

### Option B: Naiver append-only Voll-Store mit Klartext-Bodies

**Cons:** append-only × Art. 17 unvereinbar, Zweckbindungsverstoß → **abgelehnt**.

### Option C: Kein Store, nur TTL-Kontext-Cache

**Cons:** kein Vollständigkeits-/Historie-Anker → **Kill-Rückfall** (mit Trigger, §4.7), nicht Primär.

---

## 3. Decision Outcome

**Gewählte Option: Option D — Metadaten-Index-first mit zweckgebundener, crypto-geschredderter
Body-Persistenz.** Beide externen Reviews schlugen D unabhängig vor; es löst den härtesten
DSGVO-Konflikt (Body-Löschbarkeit) durch Nicht-Speicherung statt durch Schlüsselverwaltung und
verkleinert Key-Store, Backup- und Restore-Risiko drastisch. Der volle crypto-geschredderte Store (A)
bleibt als zweckgebundener Untermodus für markierte Vorgänge. Rollout gestaffelt, Kanal 1 dehnert.team,
ohne aifw.

---

## 4. Implementation Details

### 4.1 Identitätsmodell (transport-spezifisch — kein `UNIQUE(internet_message_id)`)

`internet_message_id` ist **nullable, nicht eindeutig** (nur Korrelationshinweis; fehlt/kollidiert bei
Bcc-an-sich, Listen, Sent+Inbox, Archiv-Kopien). Eindeutigkeit **pro Transport**:

```text
LogicalMessage(id, internet_message_id NULL, thread_key, raw_sha256)   # 1 fachliche Nachricht
MailCopy(logical_message_id, account_id, mailbox_id, transport,
         graph_immutable_id NULL, uidvalidity NULL, uid NULL,
         seen, flags, present)                                          # je Postfach-Kopie
Attachment(logical_message_id, part_id, blob_ref, blob_key_id, sha256)  # einzeln referenzier-/shredder-bar
```

- UNIQUE Graph: `(account_id, graph_immutable_id)`; UNIQUE IMAP: `(account_id, mailbox_id, uidvalidity, uid)`.
- `raw_sha256` als Fallback-Identität, wenn keine Message-ID vorhanden.

### 4.2 Metadaten sind Personendaten

Metadaten werden **minimiert** (nur was ein Vorgang braucht), erhalten eine **Retention-Regel je
Klasse** und eine **Rechtsgrundlage je Kanal**; das Event-`meta` ist **typisiert (Allowlist-Schema)**,
kein Freitext-Sammelbecken. Metadaten unterliegen demselben Erasure-Ledger wie Bodies.

### 4.3 Erasure-Ledger (monoton, restore-fest) — statt `deleted_at`/`redacted_at`-Spalten

Ein **autoritativer, append-only ErasureLedger** (Tombstones) lebt **außerhalb** des rücksetzbaren
Index-Backups. Er wird **vor jeder Ingestion** geprüft (Reingestion-Sperrliste) und **bei jedem
Restore vollständig replayt, bevor** Reads/Jobs/Ingestion freigegeben werden. Die früheren
denormalisierten Spalten `deleted_at`/`redacted_at` entfallen (SSoT-Konflikt mit `MailEvent`).

### 4.4 Löschumfang-Matrix (Pflicht, Art. 17)

Eine Löschung erfasst **alle** Kategorien mit Aktion/Frist/Ausnahme/Rechtsgrundlage/Nachweis:
Quellmailbox (oder dokumentierte Ausnahme), Metadaten-Projektion, **Teilnehmer-Zeilen (§4.11.1)**,
Body-Blob + Schlüssel, Anhänge, Events, Such-/tsvector-/Trigram-Index,
Embeddings/Zusammenfassungen/extrahierte Aussagen (§4.11.3), LLM-Prompt/Response-Logs,
Queue-Payloads (Redis), Traces/Crash-Dumps, Backups. Ciphertext-Blobs werden zusätzlich **physisch
mit Retention gelöscht** (Ciphertext ohne Schlüssel gilt aufsichtsseitig als *pseudonym*, nicht anonym).

### 4.5 Schlüssel-Architektur (Envelope-Encryption, keine abgeleiteten Schlüssel)

Pro persistiertem Inhalt ein **zufälliger DEK** (AEAD, an Objektkontext gebunden), gewrappt unter
**versionierten, nicht-exportierbaren KEKs**. **Kein** `HKDF(Master, message_id)` (Schlüssel wäre
rekonstruierbar → Shredding wertlos). Inventar aller Schlüsselkopien/Caches/Replicas; Rotation nur
lebender DEKs; sichere Cache-Invalidierung; Schlüsselvernichtungs-Nachweis.

### 4.6 Konsistenz, Delta-Sync & ehrliche Grenzen

- **Delta-Sync statt Voll-Diff**: Graph `delta`/Immutable-IDs, IMAP `UIDVALIDITY`+`UID` (+ `QRESYNC`/
  `OBJECTID` wo verfügbar). Der **Cursor-Zustand** (deltaLink/MODSEQ/UIDVALIDITY) wird **im App-Host
  modelliert** — der stdlib-Transport bleibt dünn, ist aber **nicht** zustandslos bzgl. Cursor.
- **Move-Semantik**: nur bei stabiler transportnativer Identität ein `moved`-Event; sonst
  `disappeared`+`appeared` mit Korrelationskandidat (kein wahrheitswidriges Move).
- **Ehrlichkeit**: Polling sieht Ereignisse zwischen zwei Läufen nicht — „Abdeckung" misst den
  **überlebenden** Zustand, nicht alles, was je existierte. Der Index ist rebuildbar; das
  **Event-Log ist beobachteter Zustand** (nicht aus dem aktuellen Postfach rekonstruierbar) und damit
  bewusst ein separater, unter SSoT begründeter Wahrheitsstand.

### 4.7 MEiKI-Gate (deny-by-default), Kill-Rückfall, JSON-Migration

- **MEiKI**: eigener Account-/Folder-Scope, **explizite Allowlist**, **In-Memory-Klassifikation vor
  Persistenz**, Quarantäne unbekannter/verbotener Inhalte, Attachment-Policy, **kein LLM-Zugriff**,
  periodische Stichproben, Incident-Prozess. **Zusätzlich vertraglich (AVV) prüfen** (Rolle
  Verantwortlicher/Auftragsverarbeiter — *rechtlich zu klären*).
- **Kill-Rückfall C**: Trigger = Löschmodell/Hosting-Gate reißt bis review_by; Migration = Body-Store
  stilllegen, Metadaten-Index behalten.
- **JSON-Migration**: `mail-vorgaenge.json` bekommt **Cutover-Datum + Migrationsschritt**; danach
  read-only, kein Parallelbetrieb (SSoT).

### 4.8 Darstellung komplexer Sachverhalte (drei Ebenen)

Option D verbietet **nicht** die inhaltliche Analyse komplexer, mailübergreifender Sachverhalte —
sie staffelt sie nach Zweck:

1. **Metadaten-Skelett (immer):** `thread_key`, Beteiligte, Zeitachse, Betreffe, Cross-Postfach-
   Verknüpfungen bilden die *Struktur* eines Sachverhalts ab (Timeline-/Thread-/Beteiligten-Ansicht)
   ohne Body-Persistenz.
2. **Just-in-time-Inhalt (ad hoc):** Der Index bestimmt, welche Mails den Sachverhalt bilden; deren
   Bodies werden **live aus dem Postfach** geholt, im Speicher/TTL-Cache zum Sachverhalt montiert,
   dargestellt und verworfen. Volle inhaltliche Darstellung ohne Dauer-Store.
3. **Vorgang-Promotion (tiefe/lange Sachverhalte):** Wird ein Sachverhalt zum **Vorgang** erklärt,
   werden seine Thread-Bodies zweckgebunden persistiert (Envelope-Encryption, Crypto-Shredding,
   Retention + Delete-Cascade) → Offline-Analyse, reproduzierbar, aifw-Reasoning (Phase 3, draft-first).

**Ehrliche Grenzen:** Ad-hoc-Volltextsuche über *nicht* persistierte Bodies existiert nicht (→ Vorgang
promoten); JIT bringt Latenz + Postfach-Verfügbarkeits-Abhängigkeit; eine vor dem Fetch gelöschte Mail
ist inhaltlich weg (korrektes SoT-Verhalten). Der Vorteil ggü. Option B: ein erklärter Vorgang trägt
Zweck, Frist und Löschpfad, statt jeden Inhalt unbefristet vorzuhalten.

### 4.9 Vorgangs-Graph — Struktur *zwischen* Sachverhalten (Amendment 2026-07-27)

§4.8 strukturiert **einen** Sachverhalt: `thread_key`, Beteiligte, Zeitachse. Was fehlt, ist die
Beziehung **zwischen** Sachverhalten. Realfall, der das Amendment ausgelöst hat: Die Antwort in
Thread A beantwortet zugleich einen Punkt aus Thread B mit einem **anderen** Gegenüber. Header-
Threading (`References`/`In-Reply-To`) kann das nicht sehen — es kennt nur die Antwortkette. Ordner
können es nicht abbilden, weil eine Nachricht dort nur **einem** Vorgang zugeordnet werden kann;
der Regelfall ist aber die Mehrfachzugehörigkeit.

**Ziel:** die korrekte und verbindliche Wiedergabe eines Sachverhalts — einschließlich der daraus
folgenden Empfehlungen und Schlüsse.

**Ausdrückliches Nicht-Ziel:** die Profilierung von Personen. Das ist keine Absichtserklärung,
sondern wird unten im Schema erzwungen.

#### Zwei Knotentypen, unterschiedliche Regeln

Ein früherer Entwurf verbot Personen-Knoten vollständig. Das war zu grob: Es hätte genau die
Vorgänge unmöglich gemacht, um die es im Datenschutz-Alltag geht — ein Betroffener mit einem
Löschbegehren **ist** der Vorgang, und seine Frist zu verfolgen ist Pflicht, nicht Profilbildung.

| | **Sachvorgang** | **Anspruchsvorgang** |
|---|---|---|
| Beispiele | technische Klärung, Angebot, Ausschreibung | Löschbegehren, Auskunftsersuchen, Fristanfrage |
| Personenbezug | keiner | Betroffener **verlinkt**, nicht kopiert |
| Rechtsgrundlage | Art. 6 Abs. 1 lit. f | **Art. 6 Abs. 1 lit. c** |
| Frist | fachlich | gesetzlich, überwachungspflichtig |
| Aggregation über die Person | ausgeschlossen | **ebenfalls ausgeschlossen** |
| Löschung | nach Aufbewahrungsklasse | erst nach Nachweiszeitraum (Art. 5 Abs. 2) |

Die vorletzte Zeile hält beides zusammen: Auch beim Anspruchsvorgang wird **nicht über die Person
ausgewertet**. Verfolgt wird ein Anspruch mit einer Frist, nicht ein Mensch mit einer Historie —
der Unterschied zwischen Fristenkalender und Personenakte.

#### Regeln

1. **Knoten tragen Sachstand, keinen Personenbezug.** Die Grenze ist *kein Personenbezug*, nicht
   *kein Inhalt* — „die Rechenlogik braucht eine Entscheidung zur Zurechnung" ist zulässig,
   „Frau X antwortet nicht" nicht. Ein rein zeigerbasierter Knoten wäre korrekt und unbrauchbar.
2. **Keine Kante zwischen zwei Anspruchsvorgängen derselben Person.** Sonst entsteht die
   Personenakte durch die Hintertür. Diese Regel ist im Schema durchsetzbar und gehört dorthin.
3. **Keine Aggregation und kein Zähler je Person** — in keiner Ansicht, keinem Export.
4. **Kanten tragen Herkunft und Status:** vom Menschen gesetzt / Zitat-Übereinstimmung / gleicher
   Anhangs-Hash / gemeinsame Beteiligung — und *bestätigt* vs. *vermutet*. Eine vermutete Zuordnung
   ist eine Behauptung und wird als solche ausgewiesen (§7-Prinzip „nie stumm weg").
5. **Stufe 1 nutzt ausschließlich deterministische Signale.** Semantische Verknüpfung durch
   Modelle bleibt außen vor — sie verknüpft still falsch und wäre die systematische
   Inhaltsauswertung, die die Art.-14-Ausnahme der DSFA ausdrücklich **nicht** deckt.
6. **Zeiger statt Kopien.** Der Graph hält keine Bodies. Löschung im Postfach ist damit Löschung
   im Graphen: Der Zeiger löst nicht mehr auf, ein knotenloser Rest verschwindet. Die Löschkaskade
   nach §4.4 ist damit **by design** erfüllt, nicht nachgebaut.
7. **Toter Zeiger ist nicht gleich toter Zeiger.** Mit `ErasureTombstone` (§4.3) ist es eine
   korrekte Löschung — erwartbar, dokumentiert. Ohne Tombstone ist es ungeklärt und ein **Befund,
   der gemeldet wird**. Ein System, das beides gleich behandelt, meldet entweder überall Alarm
   oder nirgends.
8. **Aufbewahrung über den vorhandenen Katalog.** Ein Knoten verweist auf `RetentionRule` /
   `StandardRetentionPeriod` (risk-hub) statt eine eigene Frist zu führen — zwei Fristenwerke
   driften auseinander.
9. **Der Graph schlägt Löschung vor, er vollzieht sie nicht.** Löschen ist irreversibel und wirkt
   nach außen; der Vollzug bleibt beim Menschen. Geliefert wird die begründete Liste: welche
   Nachrichten, zu welchem Vorgang, seit wann abgeschlossen, nach welcher Regel fällig.
10. **Anspruchsvorgänge werden dort geführt, wo der jeweilige Verantwortliche sitzt.** Für
    DSGVO-Löschbegehren ist das `DeletionRequest` in risk-hub; der Graph verlinkt und dupliziert
    nicht. **Fehlt ein solches System — heute für HNU und MEiKI — ist das ein benannter Mangel und
    keine stillschweigende Übernahme durch IIL.** Eine Fristenverfolgung für Studierende oder
    Bürger im IIL-Graphen wäre eine Verarbeitung im Namen eines fremden Verantwortlichen ohne
    Grundlage.

#### Zwei Annahmen, die nicht tragen und hier korrigiert werden

**„Anonymisiert" trifft nicht zu.** Ein Knoten, der auf eine Postfach-Nachricht verweist, erlaubt
die Re-Identifikation per Konstruktion — dem Zeiger zu folgen *ist* der Zweck. Nach Erwägungsgrund
26 ist der Graph damit **pseudonym** und weiterhin personenbezogen (Art. 4 Nr. 5). Das ist kein
K.-o., aber die Konstruktion darf nicht auf der Anonymitäts-Annahme aufsetzen. Ergänzend gilt:
Struktur re-identifiziert auch ohne Namen — bei kleinen Grundgesamtheiten genügt die Form.

**„Vergessen ausgeschlossen" heißt nicht „Löschen unmöglich".** Die Garantie ist die
**Vollständigkeit der Sicht zum Zeitpunkt der Frage** — dass kein offener Vorgang aus dem Blick
fällt. Löschen muss möglich sein und ist spätestens nach Fortfall des Zwecks Pflicht
(Art. 5 Abs. 1 lit. e). Der Graph ist dafür das **Instrument**, nicht das Hindernis: Er weiß als
einziger, welche Nachrichten zu einem abgeschlossenen Vorgang gehören — und genau dieses Wissen
fehlt heute, weshalb Löschkonzepte in Postfächern regelmäßig unvollzogen bleiben.

#### Benannte Nicht-Ziele mit Kompensation

**Art.-15-Auskunft ist strukturell nicht möglich.** „Alle Daten zu Person X" ist personenzentriert
— genau das, was Regel 2 und 3 verhindern. Die Auskunft ist trotzdem gedeckt, aber durch das
**Postfach** (Suche nach Adresse), nicht durch den Graphen. Wer den Graphen später für ein
Auskunftsinstrument hält, irrt; das steht hier, damit niemand darauf baut.

**Kein Erstlauf über den Altbestand.** Ein initialer Durchlauf über Jahre Postfach wäre selbst die
systematische Inhaltsauswertung, die vermieden werden soll. Der Graph wächst **vorwärts**, aus
laufender Zuordnung.

#### Stufen

**Stufe 1 — Zuordnung (klein, sofort umsetzbar).** Vorgänge als **Kategorien** im Postfach
(Graph-`categories`, mehrfach je Nachricht möglich — Ordner können das nicht) plus eine flache
Vorgangsliste mit Zustand, Abschlussdatum und Aufbewahrungsklasse. Werkzeugseitig fehlt dafür
heute alles: `graph_mail` kennt weder `categories` noch `conversationId` noch `References`.

**Stufe 2 — Struktur.** Der Graph entsteht aus Stufe 1, wenn die flache Liste die Querbezüge nicht
mehr trägt. Ob und wann das eintritt, ist eine Messfrage, keine Entwurfsfrage — bei einer
zweistelligen Zahl offener Vorgänge ist ein Graph Überbau.

#### Prüffälle (Falsifikation, nicht Illustration)

Beide Fälle sind real und **genericisiert** — ein ADR über Personenbezug trägt keine Namen ins
Repository (vgl. Changelog-Eintrag Rev 0).

**Prüffall A — wiederkehrendes Gegenüber über Monate.** Eine Person schreibt über einen längeren
Zeitraum mehrfach zum selben Anliegen, teils mit geändertem Betreff, teils in neuen Threads.
*Erwartung:* vollständiger Stand des Vorgangs inklusive noch offener eigener Zusagen — ohne dass
über die Person aggregiert oder ihr Verhalten bewertet wird. *Der Fall existiert, weil eine
Antwort ohne Kenntnis des Verlaufs bereits zu einer doppelten Anfrage an einen Betroffenen
geführt hat.*

**Prüffall B — Antwort quer zum Thread.** Eine Antwort in Thread A beantwortet zugleich einen
Punkt aus Thread B mit einem anderen Gegenüber. *Erwartung:* beide Vorgänge werden erkannt, die
Verbindung wird mit ihrer Herkunft ausgewiesen (Zitat-Übereinstimmung, gemeinsame Beteiligung),
und sie ist als bestätigt oder vermutet unterscheidbar.

**Kill-Kriterium:** Lässt sich Prüffall A oder B **nur** über systematische Inhaltsauswertung
lösen, ist dieser Entwurf gescheitert. Dann wird er **verworfen, nicht geflickt** — denn die
Inhaltsauswertung ist genau die Grenze, deren Einhaltung ihn rechtfertigt.

> **Überholt durch §4.10 (Amendment 2026-07-28).** Regel 1 (kein Personenbezug im Knoten),
> Regel 5 (nur deterministische Signale) und das Kill-Kriterium oben sind aufgehoben. Der
> Zwecktest in §4.10.1 tritt an ihre Stelle. Die Prüffälle A und B bleiben als Prüffälle
> gültig — nur ohne die Auflage, sie ohne Inhaltsauswertung lösen zu müssen.

---

### 4.10 Inhaltliche Auswertung, Aussagengewicht und Sachstand (Amendment 2026-07-28)

**Anlass.** Der Owner hat am 2026-07-28 den Zuschnitt korrigiert: Personendaten und Termine
sind *erwünscht*, weil sie Situationen aufklären; logische Verkettung dient der Verbesserung
der Lage, nicht der Bewertung von Menschen. Damit fällt die Begründung mehrerer Klauseln weg,
die als Datenschutz-Auflage formuliert waren und faktisch die Funktion begrenzt haben.

#### 4.10.1 Ein Zwecktest ersetzt drei Verbote

§8.9 trug drei starre Klauseln: kein Personen-Knoten im Sachvorgang, keine Kante zwischen
Anspruchsvorgängen derselben Person, keine Aggregation je Person. Sie werden ersetzt durch:

> Verbessert die Verkettung das Verständnis der **Situation** — oder erzeugt sie ein Urteil
> über einen **Menschen**?

Das ist zugleich freizügiger und präziser als die Verbotsliste. „Diese Organisation hat vier
offene Zusagen uns gegenüber" ist eine Situationsaussage und war unter dem alten Verbot
gesperrt, obwohl sie genau das leistet, wofür das System gebaut wird. „Diese Person antwortet
unzuverlässig" ist ein Personenurteil und bleibt außerhalb des Zwecks — obwohl beide
technisch dieselbe Aggregation sind. Der Unterschied liegt im **Subjekt des Ergebnisses**,
nicht in der Abfrage.

**Ausgaberegel als Durchsetzung:** Ergebnisse sprechen über Sachverhalte, Zusagen, Fristen und
Organisationen. Ein Befund, der sich **nur** als Aussage über einen Menschen formulieren ließe,
ist per Konstruktion außerhalb des Zwecks und wird nicht ausgegeben.

#### 4.10.2 Aufgehobene Klauseln

| Fundstelle | Klausel | Status |
|---|---|---|
| §4.7 | MEiKI: Allowlist, In-Memory-Klassifikation, Stichproben | aufgehoben |
| §4.7 | MEiKI: **kein LLM-Zugriff** | aufgehoben |
| §4.7 | MEiKI: Quarantäne, Attachment-Policy, Incident-Prozess | **bleibt** (§4.10.3) |
| §4.9 Regel 1 | Knoten tragen keinen Personenbezug | aufgehoben |
| §4.9 Regel 5 | nur deterministische Signale, keine Semantik | aufgehoben |
| §8.9 | Graph-Schema-Gate, drei Klauseln | ersetzt durch §4.10.1 |

**MEiKI wird nicht mehr gesondert behandelt.** Der Pilot arbeitet mit synthetischen Daten;
der Übergang auf echte Daten wird ausdrücklich kommuniziert und ist eine Owner-Entscheidung,
kein Dauerzustand, gegen den vorsorglich gegatet wird. Bis dahin gilt für MEiKI derselbe
Funktionsumfang wie für IIL, HNU und dehnert.team — ein Kanal, eine Codebasis.

#### 4.10.3 Was bleibt, und warum es kein Datenschutz-Grund ist

Quarantäne unbekannter Inhalte und die Attachment-Policy bleiben — mit **geänderter
Begründung**. Mailinhalt ist von außen geschriebener Text, der in ein Modell läuft; das ist
ein Injection-Vektor. ADR-284 hat das bereits festgehalten („nl2sql über angreifer-
kontrollierte Betreffs"). Bei MEiKI ist die Angriffsfläche größer, weil beliebige Absender
hineinschreiben können. Fremder Inhalt bleibt **Daten, nie Anweisung** — das ist Härtung der
Funktion, nicht ihre Begrenzung.

#### 4.10.4 Akteurs-Registry statt Personen-Knoten

Aussagen werden gewichtet, dafür braucht es Identität und Stand des Sprechenden. Beides gehört
**nicht in den Vorgangs-Knoten**, sondern in eine eigene Registry, auf die die Aussage zeigt.
Drei Gründe, alle funktional:

1. **Rollen ändern sich.** Wer im Mai Mitarbeiter war und im Juli Teamleitung ist, muss für
   eine Mai-Aussage mit Mai-Stand bewertet werden. Ein Rang im Knoten schreibt bei jeder
   Beförderung still die Vergangenheit um oder friert einen veralteten Stand ein.
2. **Eine Person, mehrere Hüte.** Dieselbe Person unter zwei Adressen ist derselbe Akteur mit
   unterschiedlichem Stand je nach Organisationskontext. Pro Mail ein Knoten erzeugt daraus
   zwei unverbundene Akteure.
3. **Rangordnung ist Organisationswissen, nicht Vorgangswissen.** In jeden Vorgang kopiert
   driftet sie auseinander.

```
Akteur          stabile ID, Anzeigename
  Adresse[]       Adresse, gültig_von/bis
  Zugehörigkeit[] Organisation, Rolle, Rang, gültig_von/bis
Aussage         Zeiger auf Nachricht, Akteur-Ref, Typ, Kern, Wortlaut,
                Bezugsaussage, gesagt_am, gilt_ab/gilt_bis, bestätigt|vermutet
Konflikt        Aussage A, Aussage B, gelöst_durch, Begründung
```

Die vorhandene Rollen-Registry (`tools/mail_agent/roles.py`) beschreibt dieselbe Struktur von
der anderen Seite — die eigene Absender-Identität. Beide werden zusammengeführt; wir selbst
sind Akteure wie andere auch. Das schließt zugleich platform#1481 (Rollen-Registry kennt keine
Kanal-Grenze), weil Organisationszugehörigkeit dann im Modell steht statt in einer Konvention.

#### 4.10.5 Gewichtung — Rang gilt für Entscheidungen, Sachnähe für Fakten

Geordnete Regeln, die erste greifende entscheidet:

1. **Weisungsbefugnis** — höherer Rang in derselben Organisation überstimmt, **aber nur bei
   Weisungen und Entscheidungen**.
2. **Sachnähe** — bei Tatsachenaussagen entscheidet, wer den Sachverhalt verantwortet. Wer die
   Messung gemacht hat, weiß den Messwert besser als die Leitung. Ebenso hat über *seine*
   Anforderung der Kunde das letzte Wort, über *unseren* Liefertermin wir.
3. **Aktualität** — jüngere Aussage desselben Akteurs überstimmt die ältere, gemessen an
   `gilt_ab`, nicht an `gesagt_am`.
4. **Verbindlichkeit** — ausdrückliche Zusage schlägt Meinung oder Vermutung.
5. **Ungelöst bleibt ungelöst** — greift keine Regel, wird der Konflikt gemeldet, nicht still
   entschieden.

Regel 1 ohne die Einschränkung auf Entscheidungen wäre ein Korrektheitsfehler: Ein System, das
Rang auf Tatsachenaussagen anwendet, glaubt die Schätzung der Leitung und verwirft die Messung
der Bearbeitung — es wird mit jeder Hierarchiestufe dümmer.

#### 4.10.6 Beobachtung und Sachstand sind zwei Schichten

Der Graph nach §4.9 ist statisch: Er sagt, welche Nachrichten zusammengehören, nicht was daraus
gerade gilt. Darüber kommt eine Schicht, die bei neuen Fakten revidiert wird.

| | **Beobachtung** | **Sachstand** |
|---|---|---|
| Inhalt | was eine Nachricht gesagt hat | was daraus gerade gilt |
| Änderbar | nein, append-only | ja, wird revidiert |
| Herkunft | Zeiger auf die Nachricht | abgeleitet, mit Begründung |
| Bei Zweifel | Postfach ist Wahrheit | neu ableiten |

**Der Sachstand muss aus den Beobachtungen neu berechenbar sein — nicht von Hand
fortgeschrieben.** Ein direkt editierter Stand macht die Datenbank zu einer zweiten Wahrheit,
die vom Postfach abweicht, ohne dass entscheidbar wäre, welche stimmt. „Aktualisieren" heißt
deshalb: neu ableiten und protokollieren, auf welche Nachricht hin sich der Stand geändert hat.

Das Muster ist nicht neu — §4.6 zieht dieselbe Trennung eine Ebene tiefer für die
Postfach-Mechanik („Der Index ist rebuildbar; das Event-Log ist beobachteter Zustand").

**Verstärkungsrisiko, ausdrücklich benannt:** Ein falsch extrahierter Fakt revidiert den Stand
auf eine Aussage, die nie gefallen ist — gefährlicher als eine übersehene Nachricht, weil er
sich richtig anfühlt. Gegenmittel ist die Kennzeichnung *bestätigt* vs. *vermutet* aus §4.9
Regel 4: Eine vermutete Zusage wird angezeigt, nicht gerechnet.

#### 4.10.7 Vorverarbeitung ist Vorbedingung, nicht Optimierung

Gemessen am 2026-07-28 über 210 Nachrichten des HNU-Kontos:

| | roh | nutzbar | Faktor |
|---|---|---|---|
| Median | 29.764 B | 838 B | 36× |
| Mittelwert | 320.517 B | 1.757 B | **182×** |

Der Mittelwert liegt beim Elffachen des Medians — Anhänge und HTML dominieren die Masse, nicht
der geschriebene Text. Roh gerechnet ergäbe der Gesamtkorpus von ~~90.967~~ **66.580 Nachrichten**
(korrigiert, §4.10.8a) rund **3,3 Mrd. Token**; nach Vorverarbeitung sind es **~29 Mio.**
(≈439 Token je Nachricht). Nach der Ausschlussregel dieses Abschnitts bleiben davon **14.028
Nachrichten** und damit **~6 Mio. Token** — der Faktor, der die Verhältnisse tatsächlich bestimmt,
ist nicht die Vorverarbeitung allein, sondern Ausschluss **mal** Vorverarbeitung.

Verbindlich ist deshalb die Kette vor jeder Extraktion: `text/plain` bevorzugen, sonst HTML zu
Text reduzieren · Anhänge ausschließen · Zitat-Historie abschneiden. Ein Entwurf, der die
Nachricht an ein Modell reicht, ist um zwei Größenordnungen daneben.

**Einmal extrahieren, oft abfragen.** Der Modell-Lauf erfolgt **einmal je Nachricht beim
Einlesen**; Ergebnis ist die strukturierte Aussage. Jede spätere Frage ist eine Abfrage darauf
und kostet null Token. Das ist keine Bequemlichkeit: Weil Bodies nach Option D nicht dauerhaft
gespeichert werden, ist Extraktion beim Einlesen **oder nie**. Kleines Modell extrahiert,
großes synthetisiert — und zwar auf der extrahierten Struktur, nicht auf Rohtext.

#### 4.10.8 Gemessener Ausgangsstand (2026-07-28) — ⚠ überholt, siehe §4.10.8a

| Konto | Transport | Ordner | Nachrichten | Rauschen (Stichprobe) |
|---|---|---|---|---|
| IIL | Graph | 90 | 44.878 | 13% |
| HNU | IMAP | 110 | 46.077 | 16% |
| Referenz | IMAP | 9 | 12 | — |

Rauschquote ist eine **Untergrenze** — gemessen in kuratierten Archiv- und Gesendet-Ordnern.
Ordner-Sweep 2,8 s (Graph) bzw. 5,0 s (IMAP); Kopfzeilen-Durchsatz ~64/s (IMAP) und ~12/s
(Graph) ⇒ einmaliger Kopfzeilen-Vollscan ≈ 75 Minuten. Das private dehnert.team-Postfach ist
**nicht** als lesbares Konto konfiguriert und damit ungemessen.

#### 4.10.8a Korrektur der Bestandszahl (2026-07-29)

**Die Zahlen in §4.10.8 beschreiben einen vorübergehenden Zustand und dürfen nicht
weiterverwendet werden.** Nachmessung am 2026-07-29:

| Konto | Transport | Ordner | Nachrichten | Δ zu §4.10.8 |
|---|---|---:|---:|---:|
| IIL | Graph | 112 | 40.171 | −4.707 |
| HNU | IMAP | 119 | 26.303 | **−19.774** |
| Referenz | IMAP | 9 | 12 | ±0 |
| privat (neu erfasst) | IMAP | 6 | 94 | — |
| **Summe** | | **246** | **66.580** | **−24.387** |

**Warum die alte Zahl zustande kam.** Am 2026-07-28 lief in genau den beiden großen Konten eine
Archiv-Umsortierung (`archiv_einsortieren.py`): elf neue Jahrgänge angelegt, dreizehn nachgezogen,
Sammelordner **erst nach einem Leer-Guard gelöscht**. Der Session-Retro
`docs/retros/session-retro-2026-07-28-platform-d5eb5e.md` beziffert **28.158 verschobene
Nachrichten** — dieselbe Größenordnung wie die Differenz von 24.387. Die damalige Zählung erfasste
Nachrichten, die zugleich im Sammelordner und im neuen Jahresarchiv lagen.

**Warum die neue Zahl trägt.** `STATUS` stimmt in vier Stichproben exakt mit `SELECT` und
`SEARCH ALL` überein; im Volllauf trat kein nicht zählbarer Ordner auf (Fehler werden ausgewiesen,
nie als 0 verrechnet); und das von der Umsortierung **nicht** betroffene Referenzkonto trifft die
alte Zahl exakt (9 Ordner / 12 Nachrichten) — die Methode ist also gegen einen Datenpunkt dieser
ADR selbst validiert.

**Regel daraus:** Eine Bestandszählung wird nach jeder Umsortierung erneut erhoben, bevor
Größen-, Zeit- oder Speicherrechnungen darauf aufsetzen. Die Folgeentscheidung ADR-288 führt das
als Gate 0.

**Restlücke:** Die Umsortierung als Ursache ist aus Datum, betroffenen Konten und Größenordnung
erschlossen; ein Protokoll der damaligen Zählung liegt nicht vor.

#### 4.10.9 Benannte Grenzen

- **Nicht-Mail-Fakten.** Telefonate und Flurgespräche bleiben unsichtbar. Der Deckungsausweis
  misst Abdeckung über das Postfach, nicht über die Wirklichkeit, und muss das aussprechen.
  Termine schließen einen Teil dieser Lücke (§4.10.10).
- **Nicht-Ereignisse.** Eine verstrichene Frist ohne Reaktion ist ein Fakt, aber nur
  feststellbar, wenn eine Erwartung hinterlegt ist. Zusagen und Termine erzeugen sie.
- **Textgröße nach Vorverarbeitung** ist an einem Konto gemessen; IIL kann abweichen.

#### 4.10.10 Termine als zweite Quelle

Kalendereinträge lösen eine Klasse toter Zeiger auf: „wie besprochen", „im Termin geklärt",
„laut Abstimmung" sind ohne sie nicht auflösbar. Zusätzlich liefern sie die Erwartungen für die
Nicht-Ereignisse oben — ein Termin ohne nachfolgende Nachricht ist ein Befund. Der Zugang
besteht bereits (`~/.claude/calendar.env`, Graph).

### 4.11 Beteiligung, Nenner und abgeleitete Repräsentationen (Amendment 2026-07-28, zweites)

Anlass ist kein Entwurf, sondern ein Fehlschlag im Betrieb ohne Index. Die Frage „was hat
Person X geschickt?" kostete am 2026-07-28 rund ein Dutzend Postfach-Abfragen über drei Konten,
weil ohne Index nicht auffindbar ist, in welchem Postfach und Ordner eine Person überhaupt
vorkommt. Drei Lücken, die dabei sichtbar wurden, betreffen das Modell, nicht das Werkzeug.

#### 4.11.1 Beteiligung ist eine Relation, keine Spalte

§4.8 nennt „Beteiligte" als Teil des Metadaten-Skeletts, §4.10.4 modelliert Akteure und
Aussagen — aber im physischen Modell aus §4.1 gibt es **keine Relation zwischen Nachricht und
Adresse**. Damit ist „wer war beteiligt?" keine Abfrage, sondern drei getrennte Suchen über
`from`, `to` und `cc`, deren Vereinigung der Aufrufer selbst bilden muss. Genau dort entstand am
2026-07-28 eine falsche Trefferzahl (28 statt 21).

```text
MessageParticipant(logical_message_id, address_norm, address_domain,
                   display_name, role ∈ {from,to,cc,bcc,reply_to},
                   akteur_id NULL)                    # Brücke zur Registry §4.10.4
```

- **`address_norm` und `address_domain` werden beim Schreiben normalisiert, nicht beim Lesen.**
  Die Kunden-/Mandanten-Zuordnung lebt heute als Domain-Substrings in einer lokalen Textdatei
  (`~/.claude/mail-folders.env`); als indizierte Spalte wird daraus ein Join — und erst dadurch
  prüfbar, ob eine Domain in zwei Ordner zeigt.
- **Trigram-Index (`pg_trgm`, GIN) auf `display_name` und normalisierten Betreff.** Die
  Suchsemantik ist Teilstring, Groß-/Kleinschreibung egal; ein B-Tree trägt dafür nicht.
- **`akteur_id` ist nullable und die einzige Brücke** von der Umschlag-Ebene zur Akteurs-Registry.
  Ohne sie hat §4.10.4 keinen Anker im physischen Index: Adressen stehen dann in Aussagen, aber
  nirgends in den Nachrichten, aus denen sie stammen.

Teilnehmer-Zeilen sind Personendaten nach §4.2 und gehören damit in die Löschumfang-Matrix
(§4.4) — sie sind dort ergänzt.

#### 4.11.2 Der Nenner gehört in die Daten, nicht in den Lauf

§4.10.7 schließt Ordner von der Indexierung aus; die Regel lebt als Laufzeit-Filter in
`tools/mail_agent/indexierung.py`. Solange sie das tut, kann ein Deckungsausweis **nicht aus der
Datenbank heraus** erklären, was fehlt — er kennt nur die Restmenge. Die Zahl „92 von 119
Ordnern geprüft" aus dem Lauf vom 2026-07-28 ist genau so eine Laufzeit-Behauptung: nachträglich
nicht reproduzierbar, weil nirgends steht, wie viele Ordner es zu diesem Zeitpunkt gab.

Deshalb:

```text
MailCopy.excluded_reason NULL        # Grund am Objekt, nicht als Filter im Code
FolderSnapshot(account_id, folder_path, message_count, seen_at)   # je Sync-Lauf
```

Der Ordnerpfad bekommt einen präfixfähigen Typ (`ltree` oder indizierter Text), damit „alles
unter `IIL.Kunden/`" ein Präfix-Scan wird statt eines Table-Scans mit `LIKE`.

Das ist dieselbe Regel wie in §4.10.7, eine Ebene tiefer: Ausschluss verkleinert die
Grundgesamtheit **sichtbar**, Löschung unsichtbar. Ein Ausschluss, der nur im Code steht, ist
für den Ausweis eine Löschung.

#### 4.11.3 Abgeleitete Repräsentationen: die Löschung ist geregelt, das Schutzniveau nicht

**Zuerst die Korrektur einer naheliegenden Fehlannahme:** Embeddings und Zusammenfassungen sind
in dieser ADR **nicht** vergessen worden. §4.4 führt sie ausdrücklich in der Löschumfang-Matrix,
§7 nennt „Abgeleitete Artefakte offenbaren Gelöschtes" als Risiko, §8.4 verlangt den
Delete-Cascade-Test. Art. 17 ist für sie abgedeckt.

Offen ist etwas anderes: **§4.5 bindet Envelope-Encryption an „jeden persistierten Inhalt".**
Ob ein Embedding eines Bodys als *Inhalt* in diesem Sinne gilt, steht nirgends. Eine
Vektor-Spalte im Klartext, die sauber mitgelöscht wird, erfüllt §4.4 vollständig und §4.5 gar
nicht.

Die Entscheidung folgt dem Vorbild, das diese ADR bereits gefällt hat: §4.4 behandelt
Ciphertext ohne Schlüssel als **pseudonym, nicht anonym**, und §4.9 zieht dieselbe Linie für den
Vorgangs-Graphen. Ein Text-Embedding ist kein Zufallsvektor, sondern eine verlustbehaftete
Repräsentation genau des Textes, dessen dauerhafte Speicherung Option D vermeiden soll; dass ein
Rückschluss ausgeschlossen sei, ist unbelegt und wäre die einzige Annahme, die eine
Klartext-Ablage rechtfertigen würde.

> **Regel.** Eine aus einem Body abgeleitete Repräsentation — Embedding, Zusammenfassung,
> extrahierte Aussage — erbt **Zweckbindung und Schutzniveau des Bodys**: DEK-Klasse nach §4.5,
> Zweck nach §4.10.1. Wo das nicht geleistet wird, wird sie **nicht persistiert**.

Das ist keine Randnotiz, sondern trifft den Kern von §4.10.7: Weil Bodies nach Option D nicht
dauerhaft gespeichert werden, ist die extrahierte Aussage „einmal extrahieren, oft abfragen"
**der überlebende Inhalt**. Sie ungeschützt abzulegen, während der Body geschützt verworfen
wird, kehrt Option D in ihr Gegenteil um — der Store enthielte dann dauerhaft genau das, was er
nicht enthalten sollte, nur in anderer Form.

#### 4.11.4 Falsch-negativ und falsch-positiv sind nicht gleich teuer

Gemessen am 2026-07-28 gegen Exchange 2010: eine server-seitige `IMAP SEARCH` auf `TO`/`CC`
lieferte im Ordner `Kalender` sieben Nachrichten, von denen **keine** den Suchbegriff in
irgendeinem Kopffeld trug. Umgekehrt war dieselbe Suche bei ASCII-Begriffen in vier von vier
kalibrierten Fällen deckungsgleich mit dem vollständigen lokalen Scan (u.a. 353 von 353 Treffern
in einem Ordner mit 354 Nachrichten).

Beide Fehlerarten sind nicht symmetrisch:

- Ein **falsch-positiver** Treffer fällt beim Lesen auf und wird von einer lokalen Gegenprobe
  entfernt. Kosten: Rechenzeit.
- Ein **falsch-negativer** fällt nie auf. Er sieht aus wie ein Ergebnis. Kosten: eine falsche
  Aussage über den Bestand.

> **Regel.** Jede Optimierung, die Kandidaten **verwirft**, muss gegen eine Menge mit bekannter
> Antwort kalibriert sein; jede, die zu viele liefert, darf ungeprüft bleiben, sofern nachgelagert
> gegengeprüft wird.

Für den Index betrifft das mehr als IMAP: **Approximate-Nearest-Neighbour-Suche gehört per
Definition in die verwerfende Klasse** (`ivfflat`/`hnsw` mit `probes`/`ef_search` sind ein
Recall-Regler). Eine ANN-Konfiguration ohne gemessenen Recall gegen exakte Suche ist derselbe
Fehler wie ein unkalibrierter Server-Vorfilter, nur schwerer zu bemerken. Dasselbe gilt für
Retention-Filter und für jede Query, die auf einem Teilindex arbeitet.

Umgesetzt ist die Regel bereits auf Werkzeugebene: `read_mail.py --abwesenheitsbeweis`
(platform#1520) belegt den genutzten Suchpfad je Konto gegen den Gesendet-Ordner, in dem die
Antwort bekannt ist, und verweigert die Vollständigkeitsaussage, wenn die Sonde nicht durchläuft.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `risk-hub`     | 0 (Erasure-Ledger + Reingestion-Sperrliste) | ⬜ | – | vor Prod-Daten |
| `dev-hub`      | 1 (Metadaten-Index + Delta-Ingestion dehnert.team) | ⬜ | – | ohne Body-Store |
| `dev-hub`      | 2 (Reconciliation + Heartbeat + Restore-Gate) | ⬜ | – | Drift-Alarm |
| `dev-hub`      | 3 (zweckgebundene Body-Persistenz + aifw Opt-in) | ➖ später | – | draft-first, Delete-Cascade |
| `dev-hub`      | 1a (§4.11: `MessageParticipant`, `FolderSnapshot`, `excluded_reason`) | ⬜ | – | Teil von Phase 1, Tracking platform#1521 |
| `dev-hub`      | 3a (§4.11.3: DEK-Bindung abgeleiteter Repräsentationen) | ➖ später | – | Vorbedingung für Embeddings/Extraktion |

---

## 6. Consequences

### 6.1 Good
- Art. 17 für Bodies per Konstruktion; kleiner Key-/Backup-Angriffsumfang; monotone Löschung via Ledger.
- Ehrliche Konsistenz-Semantik; transport-korrekte Identität; Metadaten als PII behandelt.

### 6.2 Bad
- Zwei Persistenz-Pfade + Erasure-Ledger + Envelope-Encryption = mehr bewegliche Teile.
- Such-/Assistenz-Latenz bei nicht-persistierten Bodies.

### 6.3 Nicht in Scope
- MEiKI-Personendaten (bleiben bei HNU), aifw-Verlaufsantwort (Phase 3), weitere Kanäle.

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Restore bringt gelöschten Inhalt/alten Compliance-Stand zurück | Mittel | Kritisch | Erasure-Ledger außerhalb Backup + Restore-Gate-Replay (§4.3/4.6) |
| Metadaten-PII bleibt unlöschbar | Mittel | Hoch | Metadaten unter Erasure-Ledger + Retention (§4.2) |
| Identitäts-Kollision bricht Ingestion | Mittel | Hoch | LogicalMessage/MailCopy, transport-spezifisch (§4.1) |
| Abgeleitete Artefakte offenbaren Gelöschtes | Mittel | Hoch | Löschumfang-Matrix (§4.4) + Phase-0-Register |
| Ungeschützte Ableitung ersetzt faktisch den geschützten Body | Mittel | Hoch | Ableitung erbt DEK-Klasse + Zweck (§4.11.3), CI-Gate §8.17 |
| Verwerfender Suchpfad meldet Leermenge als Ergebnis | Hoch | Mittel | Recall gegen exakte Suche messen (§4.11.4), Gate §8.18 |
| MEiKI-Fehlklassifikation | Mittel | Hoch | deny-by-default + Quarantäne (§4.7) |
| Basic-Auth-Abschaltung (Exchange/HNU) | Hoch | Mittel | Kanal 1 = dehnert.team (nicht Exchange); HNU-Kanal später mit OAuth |

---

## 8. Confirmation

1. **Schema-Gate**: CI belegt kein Klartext-Body-/Freitext-`meta`-Feld; Identität transport-spezifisch.
2. **Löschtest monoton**: nach `create_deletion_request` ist Body unlesbar, ErasureLedger-Tombstone
   gesetzt, Reingestion gesperrt, Metadaten redigiert.
3. **Restore-Gate-Test**: ältesten Backup-Stand wiederherstellen → Ledger/Key-Sperren replayen →
   abgeleitete Artefakte prüfen → erst dann Freigabe.
4. **Abgeleitete-Artefakte-Test**: Such-Index/Embedding/Summary/Prompt-Log respektieren dieselbe
   Löschung (Delete-Cascade).
5. **Injection-Test** (§4.10.3, ersetzt den MEiKI-Scope-Test): Eine Nachricht mit
   Anweisungstext im Betreff oder Body verändert weder Abfrage noch Ausgabe — fremder Inhalt
   wirkt als Daten, nie als Anweisung. Gilt für alle Kanäle, nicht nur MEiKI.
6. **DSGVO-Gate**: **DSFA** + Rechtsgrundlage je Kanal + Serverstandort/TOM/VVT **vor** Prod-Daten
   (Zusammenführung mehrerer Quellen + KI-Auswertung ab Phase 3 → DSFA-Prüfpflicht).
7. **Art. 14**: Informationspflicht ggü. Dritten dokumentiert (oder Ausnahme Art. 14 Abs. 5 lit. b begründet).
8. **Drift-Detector** (ADR-059): Staleness 12 Monate.
9. **Zwecktest-Gate** (§4.10.1, ersetzt das Graph-Schema-Gate): Kein Ergebnis-Objekt hat einen
   Menschen als Subjekt. Geprüft wird an der Ausgabe, nicht am Schema — Aggregation über eine
   Person ist zulässig, solange das Ergebnis eine Situation beschreibt.
10. **Toter-Zeiger-Test** (§4.9): ein aufgelöster Zeiger OHNE `ErasureTombstone` erzeugt einen
    gemeldeten Befund, kein stilles Beschneiden.
11. **Prüffälle A und B** (§4.9) werden gelöst — die frühere Auflage, sie *ohne*
    Inhaltsauswertung zu lösen, ist mit §4.10 aufgehoben.
12. **Vorverarbeitungs-Gate** (§4.10.7): Kein Modell-Aufruf auf Roh-MIME. Der Test belegt für
    eine Stichprobe, dass Anhänge ausgeschlossen und Zitat-Historie abgeschnitten sind.
13. **Konten-Nenner-Gate** (§4.10.8): Die Konten-Aufzählung des Deckungsausweises enthält
    **jedes** lesbare Postfach — auch Graph-Konten aus `calendar.env` — und **keine**
    Nicht-Postfächer. Gegenprobe gegen die Konfigurationsquellen, nicht gegen einen Glob.
14. **Aussagen-Gewichtungstest** (§4.10.5): Ein Faktum einer sachnahen Quelle wird **nicht**
    von einer ranghöheren Meinung überstimmt; eine Weisung dagegen schon.
15. **Beteiligungs-Gate** (§4.11.1): „Alle Nachrichten mit Adresse X" ist **eine** Abfrage über
    `MessageParticipant` und liefert From-, To- **und** Cc-Beteiligung; der Test vergleicht das
    Ergebnis gegen die Vereinigung dreier Einzelsuchen über dieselbe Menge.
16. **Nenner-aus-der-Datenbank-Gate** (§4.11.2): Der Deckungsausweis eines vergangenen Laufs
    lässt sich **ohne Postfachzugriff** aus `FolderSnapshot` + `excluded_reason` rekonstruieren.
    Ein Ausschluss, der nur im Code steht, lässt diesen Test scheitern.
17. **Schutzniveau-Gate abgeleiteter Repräsentationen** (§4.11.3): Für jede persistierte
    Ableitung eines Bodys — Embedding, Zusammenfassung, extrahierte Aussage — belegt CI eine
    DEK-Referenz nach §4.5. Eine Ableitung ohne Schlüsselbindung ist ein Schema-Verstoß, nicht
    nur ein Löschproblem.
18. **Recall-Gate verwerfender Pfade** (§4.11.4): Jeder Pfad, der Kandidaten verwirft — ANN-Suche
    (`probes`/`ef_search`), Vorfilter, Teilindex — trägt einen **gemessenen Recall gegen die
    exakte Suche** auf einer Menge mit bekannter Antwort. Ohne Messwert wird der Pfad nicht
    verwendet; ein Pfad ohne Kalibrierung darf keine Vollständigkeitsaussage tragen.

---

## 11. Externe KI-Zweitmeinung — Rückfluss-Tagging (Step-5-Gate)

Zwei externe adversariale Reviews (non-accountable, ersetzen keine Owner-Review). Verdikt beider:
**überarbeiten**. Tag-Bilanz (nur `[valid]` eingearbeitet, mit eigener Begründung, nicht 1:1):

| Befund-Cluster (Review-IDs) | Verdikt | Aktion in dieser Fassung |
|---|---|---|
| Metadaten sind PII, append-only ≠ Art.17 (R1-AD1, R2-AD5) | [valid] | §4.2 Metadaten minimiert + Retention + Erasure-Ledger |
| Key-Store/Backups/Restore untspezifiziert (R1-AD2, R2-AD3, R2-M28-2) | [valid] | §4.5 Envelope-Encryption + §4.3 Restore-festes Ledger |
| `UNIQUE(internet_message_id)` falsch (R1-AD3, R2-AD1, R2-AD12) | [valid] | §4.1 LogicalMessage/MailCopy, transport-spezifisch |
| Abgeleitete Artefakte = zweiter Klartext (R1-AD4, R2-AD10) | [valid] | §4.4 Löschumfang-Matrix + §8.4 |
| Löschung ohne Quellmailbox/Rebuild reingestiert (R2-AD2, R2-AD4) | [valid] | §4.3 Reingestion-Sperrliste + §4.4 Quellmailbox |
| MEiKI inhaltsbasiert nicht durchsetzbar (R1-AD5, R2-AD7) | [valid] | §4.7 deny-by-default technisches Gate |
| MEiKI AVV/Vertrag (R1-AD6) | [valid, unsicher] | §4.7 „rechtlich zu klären"-Gate |
| Polling misst Überlebende (R1-AD7, R2-AD8) | [valid] | §4.6 Ehrlichkeit + Delta-Sync |
| Move-Semantik cross-transport (R2-AD9, R2-REC10) | [valid] | §4.6 disappeared/appeared statt Fake-Move |
| DSFA fehlt in Gates (R1-AD9) | [valid] | §8.6 DSFA-Prüfpflicht |
| Art. 14 Info-Pflicht (R1-AD10) | [valid, niedrig] | §8.7 |
| Schema: uidvalidity/raw_sha256/Anhänge einzeln (R1-AD11) | [valid] | §4.1 Attachment-Tabelle + raw_sha256 |
| Ciphertext = Pseudonym, nicht anonym (R2/R1-AD12) | [valid] | §4.4 physische Ciphertext-Löschung |
| Abgeleiteter per-Mail-Key zerstört Shredding (R1-AD13) | [valid, präventiv] | §4.5 zufälliger DEK, kein HKDF |
| Basic-Auth-Abschaltung (R1-M28-1) | [valid] | §7 Kanal 1 nicht Exchange; HNU später OAuth |
| SSoT-Konflikt `deleted_at`/`redacted_at` (R1-AD8) | [valid] | §4.3 Spalten entfernt, Ledger/Events |
| „rebuildbarer Index" vs. append-only Log (R2-AD6) | [valid] | §4.6 Ehrlichkeits-Korrektur |
| Reconciliation-Voll-Diff-Kost + Cursor-State (R2-M28, R1-AD14) | [valid] | §4.6 Delta-Sync + Cursor im App-Host |
| Kill-Rückfall ohne Trigger/Migration (R1-M28-3) | [valid] | §4.7 Trigger + Migration |
| JSON-Migration ohne Cutover (R1-M28-4) | [valid] | §4.7 Cutover-Datum |
| **Option D (Metadaten-Index + JIT-Bodies)** (R1-OOTB1, R2-OOTB1/2) | [valid] | **§2/§3 als Primär gewählt** |
| „Wie viel Architektur für 1 Nutzer" (R1-M28-5) | [noted] | Owner hat Weiterbau entschieden; Rollout minimal (Kanal 1, ohne aifw) |
| Retention-Epochen-Sharing (R2-OOTB3) | [out-of-scope] | Reviewer selbst verworfen als Primär; ggf. nur für TTL-Cache |

---

## Glossar

| Begriff | Bedeutung |
|-----------|-----------|
| **DSGVO / Art. 17 / Art. 14** | Datenschutz-Grundverordnung; Recht auf Löschung / Informationspflicht ggü. Betroffenen |
| **DSFA** | Datenschutz-Folgenabschätzung (Art. 35) — Pflicht bei hohem Risiko |
| **Crypto-Shredding** | Löschung durch Schlüsselvernichtung |
| **Envelope-Encryption / DEK / KEK** | Datenschlüssel (je Inhalt) unter Schlüssel-Schlüssel (versioniert) gewrappt |
| **Erasure-Ledger / Tombstone** | Autoritatives, restore-festes Register erfolgter Löschungen |
| **SoT / SSoT** | (Single) Source of Truth |
| **AVV** | Auftragsverarbeitungsvertrag |
| **Delta-Sync / QRESYNC / UIDVALIDITY** | Inkrementeller Postfach-Abgleich; IMAP-Resync-Mechanismen |
| **aifw** | LLM-Routing-Framework in dev-hub |

---

## 9. More Information

- KONZ-platform-034 (Konzept), KONZ-platform-033 (Rollen-Mail-Identität)
- risk-hub `create_deletion_request` → Erasure-Ledger
- Externe Zweitmeinungen: `~/shared/adr-handoff-ADR-286-2026-07-24*.md` (ephemer; Audit hier in §11 + `ai_sparring_by`)
- **§4.11 Umsetzung getrackt**: platform#1521 (Phase 1a + 3a) — entschieden ≠ umgesetzt
- Werkzeugseitige Vorläufer der Regeln aus §4.11.2/§4.11.4: platform#1519 (`--all-folders`
  mit sichtbarem Ordner-Nenner) und platform#1520 (`--abwesenheitsbeweis` mit Kalibriersonde
  je Konto und Deckungsausweis nach KONZ-platform-035)

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-28 | Claude Code (Opus 5) | **Amendment §4.11 — Beteiligung, Nenner, abgeleitete Repräsentationen.** Anlass war kein Entwurf, sondern ein Betriebsfehlschlag ohne Index: „was hat Person X geschickt?" kostete ein Dutzend Postfach-Abfragen über drei Konten, weil ohne Index nicht auffindbar ist, in welchem Postfach und Ordner eine Person vorkommt. **§4.11.1** schließt eine Lücke im physischen Modell: §4.8 nennt „Beteiligte", §4.10.4 modelliert Akteure — aber §4.1 hat keine Relation Nachricht↔Adresse, sodass „wer war beteiligt?" drei getrennte Suchen sind, deren Vereinigung der Aufrufer bildet (genau dort entstand am 2026-07-28 die Trefferzahl 28 statt 21). Neu `MessageParticipant` mit beim Schreiben normalisierter Adresse/Domain, Trigram-Index für die tatsächliche Teilstring-Semantik und `akteur_id` als einziger Brücke zur Registry aus §4.10.4. **§4.11.2** verlagert Ausschlussgrund und Ordner-Nenner aus dem Laufzeit-Filter (`indexierung.py`) in die Daten (`excluded_reason`, `FolderSnapshot`) — sonst kann ein Deckungsausweis nicht aus der Datenbank erklären, was fehlt, und eine Zahl wie „92 von 119 Ordnern" bleibt nachträglich unbelegbar. **§4.11.3 korrigiert eine naheliegende Fehlannahme ausdrücklich**: Embeddings sind **nicht** vergessen — §4.4/§7/§8.4 decken ihre Löschung ab. Offen war das **Schutzniveau**: §4.5 bindet Envelope-Encryption an „persistierten Inhalt", ohne zu sagen, ob eine Ableitung dazuzählt; eine Klartext-Vektorspalte erfüllt §4.4 vollständig und §4.5 gar nicht. Entschieden analog zur bereits gefällten Linie (Ciphertext ohne Schlüssel = pseudonym, nicht anonym): Ableitungen erben Zweckbindung und DEK-Klasse des Bodys oder werden nicht persistiert — zwingend, weil nach §4.10.7 die extrahierte Aussage der **überlebende** Inhalt ist und eine ungeschützte Ablage Option D in ihr Gegenteil kehrte. **§4.11.4** hält die Asymmetrie fest, die beim Bau der Werkzeuge gemessen wurde: server-seitige `SEARCH` auf `TO`/`CC` lieferte 7 Nachrichten ohne den Begriff in irgendeinem Kopffeld (harmlos, lokale Gegenprobe entfernt sie), während ein falsch-negativer Treffer wie ein Ergebnis aussieht. Regel: was Kandidaten **verwirft**, muss gegen eine Menge mit bekannter Antwort kalibriert sein — das trifft ausdrücklich **ANN-Suche** (`ivfflat`/`hnsw` sind Recall-Regler), nicht nur IMAP. Gates neu: §8.15–§8.18 (Beteiligung, Nenner-aus-DB, Schutzniveau, Recall). Migration: Phase 1a + 3a. Umsetzung getrackt in platform#1521 — die ADR ist damit entschieden, **nicht** umgesetzt. |
| 2026-07-28 | Claude Code (Opus 5) | **Amendment §4.10 — inhaltliche Auswertung, Aussagengewicht, Sachstand.** Anlass: Owner-Korrektur des Zuschnitts — Personendaten und Termine sind erwünscht, weil sie Situationen aufklären; Verkettung dient der Verbesserung der Lage, nicht der Bewertung von Menschen; Datenschutz wird nachgeschärft, wenn die Funktionalität steht. Aufgehoben: §4.7 MEiKI-Sonderweg inkl. „kein LLM-Zugriff" (der Pilot arbeitet mit synthetischen Daten, der Umschaltpunkt ist eine kommunizierte Owner-Entscheidung), §4.9 Regel 1 (kein Personenbezug im Knoten), §4.9 Regel 5 (nur deterministische Signale) und das Kill-Kriterium der Prüffälle. Ersetzt durch **einen Zwecktest** (Situation vs. Personenurteil), durchgesetzt an der Ausgabe statt im Schema — freizügiger *und* präziser, weil „Organisation hat vier offene Zusagen" und „Person antwortet unzuverlässig" technisch dieselbe Aggregation sind und sich nur im Subjekt des Ergebnisses unterscheiden. Bleibt mit **geänderter Begründung**: Quarantäne + Attachment-Policy als Injection-Härtung (fremder Inhalt = Daten, nie Anweisung), jetzt für alle Kanäle statt nur MEiKI. Neu: Akteurs-Registry mit Gültigkeitszeiträumen statt Personen-Knoten (Rollen ändern sich, eine Person hat mehrere Hüte, Rangordnung ist Organisations- nicht Vorgangswissen) — führt `roles.py` zusammen und schließt platform#1481; Gewichtung mit der tragenden Unterscheidung **Rang für Entscheidungen, Sachnähe für Fakten** (andernfalls glaubt das System die Schätzung der Leitung und verwirft die Messung der Bearbeitung); Trennung **Beobachtung** (append-only) von **Sachstand** (revidierbar, neu ableitbar, nie handeditiert) analog zur bestehenden §4.6-Trennung Index/Event-Log; zwei Zeitachsen (`gesagt_am` vs. `gilt_ab`), Bezugsaussage, Wortlaut neben Normalisierung. **Gemessen statt geschätzt** (2026-07-28): Korpus 90.967 Nachrichten über 209 Ordner (IIL 44.878 / HNU 46.077 / Referenz 12), Rauschanteil ≥13–16 %, Vorverarbeitung reduziert um Faktor 182 im Mittel — roh 4,5 Mrd. Token, nutzbar ~34–40 Mio. Daraus §4.10.7: Vorverarbeitung ist Vorbedingung, nicht Optimierung, und Extraktion erfolgt beim Einlesen oder nie (Bodies sind nach Option D nicht persistiert). Gates: §8.5 → Injection-Test, §8.9 → Zwecktest-Gate, §8.11 entschärft, neu §8.12–§8.14 (Vorverarbeitung, Konten-Nenner, Gewichtung). |
| 2026-07-27 | Claude Code (Opus 5) | **Amendment §4.9 Vorgangs-Graph** + §8.9–§8.11. Anlass: Header-Threading erkennt Querbezüge nicht (eine Antwort beantwortet zugleich einen Punkt aus einem anderen Thread mit anderem Gegenüber), Ordner können Mehrfachzugehörigkeit nicht abbilden. Kernpunkte: zwei Knotentypen (Sachvorgang / Anspruchsvorgang) mit unterschiedlicher Rechtsgrundlage — ein früherer Entwurf verbot Personen-Knoten vollständig und hätte damit die Fristenverfolgung nach Art. 6 Abs. 1 lit. c unmöglich gemacht; keine Kante zwischen Anspruchsvorgängen derselben Person (Personenakte durch die Hintertür); Grenze ist *kein Personenbezug*, nicht *kein Inhalt*; Zeiger statt Kopien, damit die Löschkaskade §4.4 by design greift; toter Zeiger mit Tombstone = korrekte Löschung, ohne = gemeldeter Befund; Aufbewahrung über den vorhandenen Katalog (`RetentionRule`/`StandardRetentionPeriod`) statt zweitem Fristenwerk. Zwei Annahmen korrigiert: der Graph ist **pseudonym, nicht anonym** (EG 26), und „Vergessen ausgeschlossen" heißt Vollständigkeit der Sicht, **nicht** Löschverbot — Löschen ist spätestens nach Fortfall des Zwecks Pflicht (Art. 5 Abs. 1 lit. e), und der Graph ist dafür das Instrument. Benannte Nicht-Ziele: Art.-15-Auskunft (kompensiert durch die Postfach-Suche), kein Erstlauf über den Altbestand. Zwei genericisierte Prüffälle mit Kill-Kriterium: nur über systematische Inhaltsauswertung lösbar → verwerfen, nicht flicken. |
| 2026-07-24 | Achim Dehnert | Initial: Status Proposed (crypto-geschredderter Voll-Index) |
| 2026-07-24 | Achim Dehnert | v2 nach 2× externer KI-Zweitmeinung: Option D (Metadaten-first) primär, Erasure-Ledger, Envelope-Encryption, transport-spezifische Identität, Löschumfang-Matrix, MEiKI-deny-by-default, DSFA-Gate, Delta-Sync; Tag-Tabelle §11 |
| 2026-07-24 | Achim Dehnert | §4.8 ergänzt (Owner-Frage): Darstellung komplexer Sachverhalte unter Option D — Metadaten-Skelett / JIT-Inhalt / Vorgang-Promotion + ehrliche Grenzen |
| 2026-07-24 | Achim Dehnert | Status **Proposed → Accepted** (Owner reviewed + approved) |
