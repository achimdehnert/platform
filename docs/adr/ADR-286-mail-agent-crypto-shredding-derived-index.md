---
status: proposed
decision_date: 2026-07-24
deciders: Achim Dehnert
consulted: –
informed: –
---

# ADR-286: Adopt a crypto-shredded derived-index architecture for the Postgres mail agent

## Metadaten

| Attribut        | Wert                                                                 |
|-----------------|----------------------------------------------------------------------|
| **Status**      | Proposed                                                             |
| **Scope**       | platform                                                             |
| **Erstellt**    | 2026-07-24                                                           |
| **Autor**       | Achim Dehnert                                                        |
| **Reviewer**    | –                                                                    |
| **Supersedes**  | –                                                                    |
| **Superseded by** | –                                                                  |
| **Relates to**  | KONZ-platform-034 (Postgres-Mailagent), KONZ-033 (Rollen-Mail-Identität) |

## Repo-Zugehörigkeit

| Repo           | Rolle      | Betroffene Pfade / Komponenten                        |
|----------------|------------|-------------------------------------------------------|
| `platform`     | Referenz   | `docs/adr/`, `tools/mail_agent/` (Transport-Layer)    |
| `dev-hub`      | Primär     | `apps/mail_agent/` (Django-App, Postgres, celery)     |
| `risk-hub`     | Sekundär   | `create_deletion_request` (Löschpfad, Crypto-Shredding-Trigger) |

---

## Decision Drivers

- **Datenhoheit/DSGVO**: Der Mailagent (KONZ-034) soll Mails persistieren, die Personendaten
  enthalten (IIL-Kunden, DSGVO-Mandanten). Ein persistenter Speicher **ohne** tragfähigen
  Löschpfad ist rechtlich nicht betreibbar (Art. 17 Recht auf Vergessen).
- **Widerspruch append-only × Löschpflicht**: Der naive Entwurf (append-only Voll-Store mit
  Klartext-Bodies) macht Löschung technisch unmöglich — der zentrale Kill-Punkt aus dem
  3-Agenten-Adversariat in KONZ-034.
- **Ehrlichkeit des „100%"-Anspruchs**: Ein Absolut-Vollständigkeitszähler lügt (toter Kanal =
  „0 neue = grün"); es braucht Drift-Messung + Heartbeat statt Behauptung.
- **Zweckbindung/Auftragsverarbeitung**: MEiKI-Daten laufen über HNU (Auftragsverarbeiter) —
  dürfen nicht als personenbezogene kritische Daten in den IIL-Store; Scope-Grenze nötig.
- **Neue Service-Boundary**: Neue Postgres-DB + Ingestion-Automatismus über 3 Auth-Modelle =
  echte Architektur-Entscheidung mit Betriebs- und Sicherheits-Perimeter-Folgen.

---

## 1. Context and Problem Statement

KONZ-platform-034 empfiehlt einen Postgres-gestützten Mailagenten (lückenlose Erfassung + Historie +
verlaufsbewusste Assistenz). Der wirtschaftliche Nutzen ist belegt, aber die **Datenarchitektur** ist
rechtlich gating: Ein Speicher, der Personendaten hält, muss löschbar sein, darf die Zweckbindung
nicht verletzen und darf Vollständigkeit nicht bloß behaupten. Dieses ADR entscheidet **wie** die
Daten liegen, gelöscht werden und klassifiziert sind — **bevor** echte Personendaten fließen.

### 1.1 Ist-Zustand

| Komponente | Stand |
|---|---|
| `platform/tools/mail_agent/` | stdlib IMAP/SMTP/Graph, **kein** DB-Store |
| `~/.claude/mail-vorgaenge.json` | leichter JSON-Vorgangs-Store (kein Volltext, keine Historie) |
| dev-hub | Postgres/Redis/celery/aifw vorhanden, 17 Apps, **kein** Mail-App |
| Löschpfad | risk-hub `create_deletion_request` existiert (DSGVO-Prozess) |

### 1.2 Warum jetzt

Owner-Entscheid 2026-07-24: KONZ-034 (Option 1) umsetzen, **erster Kanal dehnert.team**, aifw erst
Phase 3. Damit rückt echter Bau näher — die DSGVO-/Datenarchitektur muss vor dem ersten Prod-Datensatz
entschieden sein, nicht nachgerüstet (Maintainer-2028: nachträgliches Redaction-Layer war „schmerzhaft").

---

## 2. Considered Options

### Option A: Crypto-shredded derived index + metadata-only event-log ✅

Postfach = Source of Truth. Postgres = strikt abgeleiteter, neu aufbaubarer Index. **Nur** das
Ereignis-Log über **Metadaten** (ingested/seen/moved/replied/deleted/redacted) ist append-only.
**Mail-Bodies + Anhänge** liegen verschlüsselt mit **per-Mail-Schlüssel** außerhalb der Zeilen;
Löschung = **Key-Delete (Crypto-Shredding)** → Inhalt unlesbar, Nachweis-Metadaten bleiben.

**Pros:**
- DSGVO-Art.-17-tauglich: Löschung ist ein Key-Delete, kein Bruch der Event-Immutabilität.
- Auditierbar: Event-Log belegt „wann was", ohne Inhalte unlöschbar zu machen.
- Index jederzeit aus der SoT rebuildbar → keine Datenverlust-Klasse, nur Rebuild-Kosten.

**Cons:**
- Schlüsselverwaltung (per-Mail-Key + Key-Store) ist zusätzliche Komplexität.

### Option B: Naiver append-only Voll-Store mit Klartext-Bodies

**Pros:**
- Einfachstes Schema, keine Krypto-Schicht.

**Cons:**
- append-only × Art. 17 unvereinbar → **Abgelehnt weil:** Löschung technisch unmöglich; MEiKI/HNU-
  Zweckbindungsverstoß bei gemeinsamem Klartext-See (KONZ-034 Kill-Befund B1/B2).

### Option C: Kein zentraler Store — TTL-Kontext-Cache pro Vorgang (ALT-2)

**Pros:**
- Keine DSGVO-Landmine, minimaler Betrieb.

**Cons:**
- Kein beweisbarer Vollständigkeits-/Historie-Anker → **Abgelehnt als Primär**, aber **als
  Kill-Rückfall behalten**, falls Option A am Löschmodell/Hosting scheitert.

---

## 3. Decision Outcome

**Gewählte Option: Option A — Crypto-shredded derived index + metadata-only event-log.**

Option A ist die einzige, die beide KONZ-034-Ziele trägt *und* DSGVO-Art. 17 erfüllt: Bodies sind über
Key-Delete löschbar, während das Metadaten-Event-Log den Nachweis behält. B ist rechtlich nicht
betreibbar; C verliert den beweisbaren Vollständigkeits-/Historie-Kern und bleibt daher nur als
Kill-Rückfall. Der Rollout ist gestaffelt: **ein Kanal (dehnert.team)** zuerst, **ohne** aifw.

---

## 4. Implementation Details

### 4.1 Datenmodell (dev-hub `apps/mail_agent`)

```text
Message(internet_message_id UNIQUE, account, folder, uid, thread_key,
        from, to, subject, sent_at, received_at,
        body_ref, body_key_id, has_attachments, deleted_at, redacted_at)
MailEvent(message_id, kind ∈ {ingested,seen,moved,replied,deleted,redacted}, at, meta)  # append-only
```

- **Keine Klartext-Body-Spalte.** Bodies/Anhänge verschlüsselt im Objekt-Store; `body_ref` +
  `body_key_id` in der DB. `internet_message_id` = kanonischer Cross-Postfach-Schlüssel (stabil über
  Graph *und* IMAP, überlebt UID-/UIDVALIDITY-Wechsel); UID nur sekundär.

### 4.2 Löschpfad (Crypto-Shredding, DSGVO-Art. 17)

- Löschantrag/Frist → risk-hub `create_deletion_request` → Trigger `Key-Delete(body_key_id)` +
  `MailEvent(kind=redacted)`. Backups: Schlüssel-Rotation/-Löschung erfasst die Backups mit
  (kein Klartext-Backup ohne Schlüssel).

### 4.3 Konsistenz & „100%" (ehrlich)

- Reconciliation (celery-beat) difft je Ordner DB↔Postfach per `internet_message_id`; Move = **ein**
  Event (kein Delete+Neu). Postfach-Löschungen werden in die DB propagiert.
- **Ingestion-Heartbeat** je Kanal (`last_successful_poll_at` + Soll-Intervall) → Alarm bei Stille.
  „100%" wird als **Abdeckung(aktueller Ordnerzustand) + Drift-Metrik** ausgewiesen, nie als Absolut-Zähler.

### 4.4 Datenklassifikation & Scope

- **Kanal 1: dehnert.team** (geringste Sensibilität, voller Zugriff).
- **MEiKI: nur Projektkommunikation** — **keine Verwaltung personenbezogener kritischer Daten**
  (Owner-Setzung 2026-07-24). MEiKI-Personendaten bleiben bei HNU (Auftragsverarbeiter), nicht im IIL-Store.
- DSGVO-Mandanten/IIL-Kundendaten: nur unter Option-A-Crypto-Shredding + Zweckbindung; erst nach §8-Gates.

### 4.5 Assistenz (Phase 3)

- aifw-Verlaufsantwort erst Phase 3, **draft-first**, kein Personendaten-Voll-Prompt.

---

## 5. Migration Tracking

| Repo / Service | Phase | Status | Datum | Notizen |
|----------------|-------|--------|-------|---------|
| `dev-hub`      | 1 (Modell + Ingestion dehnert.team) | ⬜ Ausstehend | – | ohne aifw |
| `dev-hub`      | 2 (Reconciliation + Heartbeat)      | ⬜ Ausstehend | – | Drift-Alarm |
| `risk-hub`     | 1 (Crypto-Shredding-Löschpfad)      | ⬜ Ausstehend | – | Key-Delete-Trigger |
| `dev-hub`      | 3 (aifw-Verlaufsantwort, Opt-in)    | ➖ Out of Scope (später) | – | draft-first |

---

## 6. Consequences

### 6.1 Good

- Persistente Historie + beweisbare Reconciliation **mit** DSGVO-Löschbarkeit.
- Index verwerfbar/rebuildbar aus SoT; keine „zweite Wahrheit", die eine Postfach-Löschung überlebt.

### 6.2 Bad

- Schlüsselverwaltung + Objekt-Store sind zusätzliche bewegliche Teile.
- Reconciliation über heterogene Backends bleibt Rest-Heuristik (kein mathematischer Absolut-Beweis).

### 6.3 Nicht in Scope

- MEiKI-Personendaten (bleiben bei HNU), aifw-Verlaufsantwort (Phase 3), weitere Kanäle (nach Kanal 1).

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| Schlüssel-Store kompromittiert → alle Bodies lesbar | Niedrig | Kritisch | Getrennter Key-Store, Rotation, Zugriffs-Audit |
| Stiller Drift DB↔Postfach | Mittel | Mittel | Reconciliation per internet_message_id + Drift-Alarm |
| Toter Kanal unbemerkt | Mittel | Mittel | Ingestion-Heartbeat je Kanal |
| Serverstandort/AVV ungeklärt vor Prod-Daten | Mittel | Hoch | §8-Gate: TOM/VVT/Standort vor erstem Prod-Datensatz |

---

## 8. Confirmation

1. **Schema-Gate (kein Klartext-Body)**: CI-Test/`grep` über die Migration belegt, dass `Message`
   **keine** Klartext-Body-Spalte hat (nur `body_ref`/`body_key_id`) — prüfbar bei jedem PR.
2. **Löschtest (Crypto-Shredding)**: Ein Test erzeugt eine Nachricht, löst `create_deletion_request`
   aus und verifiziert, dass der Body danach **unlesbar** ist und ein `MailEvent(kind=redacted)` existiert.
3. **MEiKI-Scope-Gate**: Die Ingestion-Konfiguration schließt MEiKI-Personendaten aus; ein Check
   verifiziert, dass kein HNU/MEiKI-Personendaten-Kanal aktiv ist, bevor Prod-Daten fließen.
4. **Hosting-Gate**: Kein Prod-Datensatz vor dokumentiertem Serverstandort + TOM/VVT (Review-Nachweis).
5. **Drift-Detector**: Dieses ADR wird von ADR-059 auf Aktualität geprüft — Staleness-Schwelle: 12 Monate.

---

## Glossar

| Abkürzung / Begriff | Bedeutung |
|-----------|-----------|
| **DSGVO** | Datenschutz-Grundverordnung; Art. 17 = Recht auf Löschung/„Vergessen" |
| **Crypto-Shredding** | Datenlöschung durch Vernichten des Schlüssels — verschlüsselte Daten werden unlesbar, ohne die Zeile physisch zu löschen |
| **SoT** | Source of Truth — die maßgebliche Quelle (hier: das Postfach) |
| **append-only** | Ein Log, an das nur angehängt, nie überschrieben/gelöscht wird |
| **AVV / Auftragsverarbeitung** | Vertrag/Verhältnis, in dem ein Dienstleister (HNU) Personendaten im Auftrag verarbeitet |
| **TOM / VVT** | Technisch-organisatorische Maßnahmen / Verzeichnis der Verarbeitungstätigkeiten |
| **aifw** | LLM-Routing-Framework in dev-hub |
| **Reconciliation** | Abgleich DB-Zustand ↔ Postfach-Zustand zur Drift-Erkennung |

---

## 9. More Information

- KONZ-platform-034: Postgres-Mailagent (Konzept, `idea`) — Quelle dieser Entscheidung
- KONZ-platform-033: Rollen-Mail-Identität — Transport-/Absender-Schicht
- risk-hub `create_deletion_request` — DSGVO-Löschprozess (Crypto-Shredding-Trigger)
- `platform-agents`-Policy — Host-Wahl dev-hub

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-07-24 | Achim Dehnert | Initial: Status Proposed |
