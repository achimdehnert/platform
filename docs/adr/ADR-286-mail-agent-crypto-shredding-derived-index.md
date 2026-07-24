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
Quellmailbox (oder dokumentierte Ausnahme), Metadaten-Projektion, Body-Blob + Schlüssel, Anhänge,
Events, Such-/tsvector-/Trigram-Index, Embeddings/Zusammenfassungen, LLM-Prompt/Response-Logs,
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

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `risk-hub`     | 0 (Erasure-Ledger + Reingestion-Sperrliste) | ⬜ | – | vor Prod-Daten |
| `dev-hub`      | 1 (Metadaten-Index + Delta-Ingestion dehnert.team) | ⬜ | – | ohne Body-Store |
| `dev-hub`      | 2 (Reconciliation + Heartbeat + Restore-Gate) | ⬜ | – | Drift-Alarm |
| `dev-hub`      | 3 (zweckgebundene Body-Persistenz + aifw Opt-in) | ➖ später | – | draft-first, Delete-Cascade |

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
5. **MEiKI-Scope-Test**: Fehlklassifikation landet in Quarantäne, nicht im Store; kein LLM-Zugriff.
6. **DSGVO-Gate**: **DSFA** + Rechtsgrundlage je Kanal + Serverstandort/TOM/VVT **vor** Prod-Daten
   (Zusammenführung mehrerer Quellen + KI-Auswertung ab Phase 3 → DSFA-Prüfpflicht).
7. **Art. 14**: Informationspflicht ggü. Dritten dokumentiert (oder Ausnahme Art. 14 Abs. 5 lit. b begründet).
8. **Drift-Detector** (ADR-059): Staleness 12 Monate.

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

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-24 | Achim Dehnert | Initial: Status Proposed (crypto-geschredderter Voll-Index) |
| 2026-07-24 | Achim Dehnert | v2 nach 2× externer KI-Zweitmeinung: Option D (Metadaten-first) primär, Erasure-Ledger, Envelope-Encryption, transport-spezifische Identität, Löschumfang-Matrix, MEiKI-deny-by-default, DSFA-Gate, Delta-Sync; Tag-Tabelle §11 |
| 2026-07-24 | Achim Dehnert | §4.8 ergänzt (Owner-Frage): Darstellung komplexer Sachverhalte unter Option D — Metadaten-Skelett / JIT-Inhalt / Vorgang-Promotion + ehrliche Grenzen |
| 2026-07-24 | Achim Dehnert | Status **Proposed → Accepted** (Owner reviewed + approved) |
