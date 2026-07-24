---
concept_id: KONZ-platform-034
title: Postgres-gestützter Mailagent (Erfassung + Historie + verlaufsbewusste Assistenz)
pipeline_status: idea
tier: T3
owner: Achim Dehnert
spec_refs: []            # kein Klickdummy-Spec; Backend-/Daten-Architektur
adr_threshold: org-weiter ADR (neue DB + neue Service-Boundary + Datenhoheit/Personendaten + AV-MEiKI)
review_by: 2026-10-24
kill_criteria: "Wenn bis review_by kein DSGVO-tragfähiges Lösch-/Redaction-Modell steht (append-only × Art. 17 ungelöst) ODER die Reconciliation über >1 Kanal keinen ehrlichen Vollständigkeits-/Drift-Beweis liefert (nur einen grünen Zähler), wird das Konzept auf den TTL-Kontext-Cache (ALT-2) zurückgestuft — kein zentraler Voll-Mail-See."
superseded_by_spec: null
evidence_manifest:
  - {claim_id: C1, source_path: platform/tools/mail_agent/, commit_or_pr: "session 2026-07-24", opened_in_session: true}
  - {claim_id: C2, source_path: "~/.claude/{mail.env,mail-hnu.env,graph-mail-tokens,mail-vorgaenge.json}", commit_or_pr: "n/a", opened_in_session: true}
  - {claim_id: C3, source_path: dev-hub/config/settings/, commit_or_pr: "session 2026-07-24", opened_in_session: true}
  - {claim_id: C4, source_path: dev-hub/apps/, commit_or_pr: "session 2026-07-24", opened_in_session: true}
created: 2026-07-24
---

# KONZ-platform-034 — Postgres-gestützter Mailagent

**Tier T3** — neue Postgres-DB (neue Dependency + Service-Boundary), **cross-repo** (platform-Transport
+ dev-hub-App + risk-hub-Löschung), **Datenhoheit/Security-Perimeter** (Personendaten: IIL-Kunden,
DSGVO-Mandanten, MEiKI-über-HNU), neuer Betriebs-Lifecycle. Auto-Eskalation greift auf vier Achsen.

## 1 Executive Summary

Achim will (1) **100 % seiner Mails über alle Postfächer lückenlos erfasst** und (2) **Assistenz, die
sich auf den gesamten Mailverlauf bezieht**, mit **konsistenter DB/Postfach-Beziehung und Historie**.
Der tragfähige Kern ist ein **abgeleiteter Postgres-Index + Ereignis-Log** in dev-hub, gespeist vom
bestehenden stdlib-Transport (`platform/tools/mail_agent`). **Aber** der naive Entwurf („append-only
Voll-Mail-See mit Klartext-Bodies aller Rollen") ist in zwei Punkten **tödlich** und wird hier
bewusst *nicht* empfohlen: (a) **append-only × DSGVO Art. 17** (Recht auf Vergessen) ist ein
Widerspruch; (b) **MEiKI/HNU-Daten** unterliegen der Auftragsverarbeitung und dürfen nicht in einen
gemeinsamen iil.gmbh-Store. Empfehlung: **kleiner schneiden** — ein Kanal zuerst, **Metadaten +
verschlüsselte Body-Referenz** statt Klartext, **Crypto-Shredding/Redaction** statt dogmatisch
append-only, **Ingestion-Heartbeat** statt „100 %"-Zähler-Lüge, aifw-Verlaufsantwort als späteres
Opt-in. Und: **ehrliche Neufassung von „100 %"** als *verifizierte Reconciliation-Abdeckung des
aktuellen Ordnerzustands + Drift-Alarm*, nicht als unfälschbarer Absolut-Anspruch.

## 2 Scope & Evidenzbasis

**In Scope:** Ingestion-/Index-/Historie-Architektur, Konsistenzmodell, DSGVO-Löschpfad, Host-Wahl,
schrittweiser Rollout. **Out of Scope:** UI-Details, konkrete aifw-Prompts, HNU/DSB-Signaturinhalte.

Evidenzbasis (in dieser Session geöffnet): `platform/tools/mail_agent/` = stdlib IMAP/SMTP/Graph,
**kein DB-Store** (C1). Transport-Configs `mail.env`/`mail-hnu.env`/`graph-mail-tokens` + heutiger
Vorgangs-Store `mail-vorgaenge.json` (C2). dev-hub-Settings mit Celery/Redis (C3), 17 Apps ohne
Mail-App (C4). Nicht verifiziert: konkrete Graph-vs-IMAP-ID-Semantik im *geplanten* Code (existiert
noch nicht) — als Design/Hypothese behandelt.

## 3 Infrastruktur-Fit

dev-hub bringt Postgres, Redis, django-celery-beat (periodische Reconciliation) und aifw (LLM-Routing)
bereits mit (C3/C4) — ein `dev-hub/apps/mail_agent` ist die **18. App im bestehenden Muster**, kein
neuer Backup-/Monitoring-Fußabdruck. Laut `platform-agents`-Policy gehört ein plattformweiter,
nicht-domänen-Agent nach dev-hub. Der **Transport bleibt** in `platform/tools/mail_agent` (dünn,
zustandslos); die DB-Semantik lebt in dev-hub. Das ist die richtige Schichtung: Adapter unten,
Normalisierung/Historie oben.

## 4 Steelman (stärkster Fall FÜR)

- **Symmetrie über heterogene Transporte:** Graph, HNU-IMAP, dehnert.team-IMAP liefern inkompatible
  IDs/Flags/Zeitstempel. Ein DB-Index normalisiert auf ein einheitliches Schema (kanonische
  `internetMessageId`, Postfach-Herkunft, Thread-Key). Transport bleibt dünn.
- **Idempotenz + Vollständigkeit sind nur mit Persistenz *beweisbar*:** „erfasst" ist eine
  Mengengleichheit (Ordner-UID-Set == DB-Set); Live-IMAP allein hat keinen Vergleichsanker. Ein
  UNIQUE-Constraint auf `(account, folder, uid_or_msgid)` macht Doppel-Ingestion strukturell unmöglich.
- **Reproduzierbarkeit & Nebenläufigkeit:** Postgres-MVCC + Transaktionen lösen Lost-Update über
  mehrere Sessions; JSON korrumpiert bei Abbruch und liefert je nach Postfach-Zustand andere Historie.
- **Auditierbarkeit:** Ein Ereignis-Log (gesehen/verschoben/beantwortet/gelöscht) belegt „wann wurde
  was getan" — ein DSGVO-*Nachweis*, den flüchtige Live-Abfragen nicht liefern.
- **Konkreter Nutzen:** Thread-Kontext über *alle* Postfächer (IIL↔HNU-Kreuzbezüge); Fristen/Vorgänge
  verlässlich, weil keine Mail unbemerkt fehlt (Realfall Zinser/Azure-Übersehen wäre strukturell
  schwerer); reproduzierbare Auskunft „welche Mandanten-Mail wann beantwortet/gelöscht".

## 5 Konzeptdefinition (synthetisierter Entwurf)

**Kernthese:** Postfach = **Source of Truth**; Postgres = **strikt abgeleiteter, jederzeit neu
aufbaubarer Index** + **Ereignis-Log über Metadaten**. **Mail-Bodies liegen NICHT append-only im
Klartext**, sondern als **verschlüsselte Body-Referenz mit per-Mail-Schlüssel** (Löschung =
Key-Delete → Crypto-Shredding, DSGVO-Art.-17-tauglich). Das append-only-Prinzip gilt nur für das
**Ereignis-Log der Aktionen** (Fakten über Beobachtungen), nie für schützenswerte Inhalte.

**Konsistenz:** Ein Reconciliation-Loop (celery-beat) difft je Ordner DB-Set gegen aktuellen
Postfach-Zustand; **Postfach-Löschungen/-Moves werden in die DB propagiert** (DB überlebt eine
Postfach-Löschung nicht). „100 %" wird ehrlich definiert als **Abdeckung des aktuellen
Ordnerzustands + gemessene Drift**, plus ein **Ingestion-Heartbeat** (Durchsatz/Frische je Kanal),
damit ein toter Kanal *laut* auffällt statt als „0 neue Mails" grün zu lügen.

**Trennung MEiKI/HNU:** MEiKI-/HNU-Auftragsverarbeitungs-Daten werden **ausgeschlossen oder strikt
getrennt** (eigener Store/Schema mit eigener Zweckbindung) — nie im gemeinsamen IIL-See.

**Assistenz (Ziel 2):** Verlaufsbewusste Antwort ist ein **Opt-in-Retrieval** (relevanten Thread
für Achim sichtbar machen), **draft-first**, kein Auto-Versand — passend zur „kein-KI-Vorrede"- und
Draft-first-Kultur. Kein Personendaten-Voll-Dump in LLM-Prompts.

## 6 Adversariale Analyse

**Advocatus Diabolus (Kill-/Schwachpunkte):**
1. **append-only × Art. 17 = tödlich** in der Naiv-Form → gelöst durch Crypto-Shredding (§5/§7).
2. **MEiKI/HNU-Zweckbindung** → gelöst durch Ausschluss/Trennung (§5).
3. **„100,00 %" unfälschbar** (UIDVALIDITY-Bruch, Änderungen zwischen Cron-Läufen, kein stabiler
   Cross-Backend-Key) → entschärft durch ehrliche Neudefinition + `internetMessageId` als
   primärer Cross-Backend-Anker (UID nur sekundär).
4. **Zweite Wahrheit driftet still** → Propagation von Postfach-Löschungen + Drift-Alarm.
5. **Over-Engineering für einen Nutzer** → Rollout ein Kanal, ALT-2 als Rückfallebene.
6. **Betriebslast/Fehlalarm über 3 Auth-Modelle** → Heartbeat je Kanal statt Gesamt-Zähler.
7. **Konzentrationsrisiko** (Single-Point-of-Breach) → Serverstandort/VVT/AVV vor Prod-Daten.

**Maintainer-2028 (Rückblick-Befunde):** (i) Auth-/Token-Rotation über 3 Kanäle = größter Schmerz,
Graph-Secret lief still ab; (ii) DB vs. Postfach lief bei Server-Side-Moves/Archiv-Konvention
auseinander; (iii) Art-17 × append-only teuer nachgerüstet; (iv) **totes Feature:** aifw-Voll-Verlauf
kaum genutzt (draft-first-Kultur); (v) DB-Wachstum/Attachment-Sog ohne TTL; (vi) halb-tot unbemerkt
(nur „conclusion grün"). **Jeder dieser Befunde ist im Entwurf §5/§7 vorweggenommen.**

**Konfliktmatrix (belegte Dissense):**

| Thema | Steelman | Diabolus / Maintainer | Auflösung |
|---|---|---|---|
| append-only Historie | Audit-Asset | tödlich (Art. 17) | append-only nur fürs **Event-Log (Metadaten)**; Bodies crypto-shred-bar |
| „100 %" | via Mengengleichheit beweisbar | unfälschbar/Heuristik | Neudefinition: Abdeckung *aktueller* Zustand + Drift + Heartbeat |
| DB-Autorität | rebuildbarer Index | wird de-facto autoritativ, driftet | Löschungen propagieren; DB nie länger als Postfach |
| aifw-Verlaufsantwort | Kernnutzen | totes/teures Feature | späteres Opt-in-Retrieval, nicht Fundament |
| Umfang | Voll-See lohnt | Over-Engineering | 1 Kanal zuerst; MEiKI aus; ALT-2 als Kill-Rückfall |

## 7 Deep-Dive

**Datenmodell:** `Message(internet_message_id UNIQUE, account, folder, uid, thread_key, from, to,
subject, sent_at, received_at, body_ref, body_key_id, has_attachments, deleted_at)` +
`MailEvent(message_id, kind ∈ {ingested,seen,moved,replied,deleted,redacted}, at, meta)` (append-only).
**Bodies/Anhänge:** verschlüsselt in Objekt-Store, `body_ref`+`body_key_id` in der DB; **Löschung =
Key-Delete** (Inhalt unlesbar, Metadaten/Event-Log bleiben als Nachweis). **Ingestion:** celery-beat
pro Kanal, Cursor = höchste UID/`internetMessageId`; idempotent per UNIQUE-Constraint. **Reconciliation:**
Ordner-Diff DB↔Postfach; Move = ein Event, kein Delete+Neu (Match per `internetMessageId`, nicht UID).
**Heartbeat:** je Kanal `last_successful_poll_at` + erwartetes Intervall → Alarm bei Stille
(nicht „0 neue = grün"). **DSGVO:** Löschanträge laufen über risk-hub (`create_deletion_request`),
der einen Key-Delete + `redacted`-Event auslöst; MEiKI/HNU nicht im Store.

## 8 Alternativen

| Alt | Beschreibung | Bewertung |
|---|---|---|
| **ALT-1 (empfohlen)** | Abgeleiteter Index + Event-Log (Metadaten append-only, Bodies crypto-shred-bar), 1 Kanal zuerst | Trägt beide Ziele, DSGVO-tragfähig, rückbaubar |
| **ALT-2 (Kill-Rückfall)** | Kein zentraler See — **TTL-Kontext-Cache pro Vorgang** + `mail-vorgaenge.json` + Live-IMAP bei Bedarf | 90 % Nutzen ohne DSGVO-Landmine; Fallback wenn ALT-1 am Löschmodell scheitert |
| ALT-3 | Naiver append-only Voll-See mit Klartext | **Verworfen** — Art. 17 × append-only, MEiKI-Verstoß |

## 9 Out-of-the-Box

- **`internetMessageId` als kanonischer Cross-Postfach-Schlüssel** (stabil über Graph *und* IMAP,
  überlebt UID-Wechsel) statt UID-Abhängigkeit.
- **Crypto-Shredding** entkoppelt „Nachweis behalten" von „Inhalt vergessen" — löst den Kernkonflikt.
- **Heartbeat-statt-Zähler** dreht die 100 %-Frage von „behaupte Vollständigkeit" zu „beweise
  Erreichbarkeit + miss Drift".

## 10 Befunde

- **B1 (kritisch):** Naiver append-only-Voll-See ist DSGVO-inkompatibel (Art. 17). Beleg: Diabolus+Maintainer unabhängig. → §5/§7.
- **B2 (kritisch):** MEiKI/HNU im gemeinsamen Store = AV-/Zweckbindungsverstoß. → Ausschluss/Trennung.
- **B3 (hoch):** „100,00 %" ist ohne Neudefinition + Heartbeat eine Lebenslüge. → §5.
- **B4 (mittel):** aifw-Voll-Verlaufsantwort droht totes/teures Feature zu werden. → Opt-in, nicht Fundament.
- **B5 (mittel):** Auth-Rotation über 3 Kanäle ist der Haupt-Wartungstreiber. → 1 Kanal zuerst + Heartbeat.

## 11 Top-5-Risiken

1. **DSGVO-Löschmodell scheitert** → Kill-Rückfall ALT-2. (Mitig.: Crypto-Shredding + risk-hub-Verzahnung)
2. **Stiller Drift DB↔Postfach** → Reconciliation per `internetMessageId` + Drift-Alarm + Lösch-Propagation.
3. **Toter Kanal unbemerkt** → Ingestion-Heartbeat je Kanal.
4. **Personendaten-Konzentration/Breach** → Serverstandort/TOM/VVT/AVV vor Prod-Daten; Bodies verschlüsselt.
5. **Scope-Explosion (Konzern-Muster für 1 Nutzer)** → strikt gestaffelter Rollout, ALT-2 verfügbar.

## 12 Empfehlungen

1. **ALT-1, gestaffelt.** Start mit **einem** Kanal (Vorschlag: `dehnert.team`/AD — geringste
   Sensibilität, voller Zugriff), Modelle `Message`+`MailEvent`, Bodies verschlüsselt+Key-Delete.
2. **DSGVO zuerst entscheiden (ADR):** Crypto-Shredding-Löschpfad + MEiKI-Ausschluss + Serverstandort/VVT
   — **bevor** echte Personendaten fließen. Ohne diesen ADR keine Prod-Daten.
3. **„100 %" ehrlich fassen:** Reconciliation-Abdeckung(aktueller Zustand) + Drift-Metrik + Heartbeat;
   keinen Absolut-Zähler bauen, der lügt.
4. **aifw-Verlaufsantwort als Phase 3 Opt-in**, draft-first, kein Personendaten-Voll-Prompt.
5. **`mail-vorgaenge.json` migrieren**, nicht doppeln (SSoT: der JSON-Store wird von der DB abgelöst,
   nicht parallel geführt).

## 13 Entscheidung + Kill-Gate

**Entscheidung:** ALT-1 gestaffelt weiterverfolgen, **gegated durch einen DSGVO-ADR** (Crypto-Shredding
+ MEiKI-Trennung + Hosting). Nächster Schritt: ADR entwerfen; parallel MVC ein Kanal (Ingestion +
Reconciliation + Heartbeat, **ohne** aifw-Antwort). 30/60/90: **30** ADR + Datenmodell-Migration
`mail-vorgaenge.json`; **60** MVC ein Kanal grün inkl. Drift-Alarm; **90** Entscheidung über 2. Kanal +
aifw-Opt-in.

**Kill-Gate (messbar):**

| Kriterium | Status (offen/erfüllt/verworfen) | Beleg |
|---|---|---|
| DSGVO-tragfähiges Lösch-/Redaction-Modell (Crypto-Shredding) im ADR akzeptiert | offen | — |
| MEiKI/HNU nachweislich aus dem IIL-Store ausgeschlossen/getrennt | offen | — |
| Reconciliation über ≥1 Kanal liefert Drift-Metrik + Heartbeat (kein reiner „100 %"-Zähler) | offen | — |
| `mail-vorgaenge.json` migriert (nicht dupliziert) | offen | — |

**Exception-Budget:** 1× Verlängerung um 30 Tage (bis 2026-11-23). Reißt Kriterium 1 oder 2 dauerhaft →
Rückstufung auf **ALT-2** (TTL-Kontext-Cache), kein zentraler Voll-Mail-See.

**Ehrliche Enforcement-Grenze:** Dieses Konzept *schreibt* die Lifecycle-/Kill-Felder, *erzwingt* sie
nicht — sie wirken erst über ein Konzept-Lifecycle-Gate bzw. den begleitenden ADR. Bis dahin
Review-Gate, kein Exit-Code.
