---
status: accepted
date: 2026-03-10
updated: 2026-07-01
decision-makers: Achim Dehnert
consulted: Cascade
implementation_status: implemented
implementation_evidence:
  - "weltenfw v0.2.0: WeltenClient, AbstractWorldBackend, WeltenhubBackend, LocalWorldBackend"
  - "schema/: World, Character, Location, Scene, Story (Pydantic v2 frozen)"
  - "resources/: REST clients für worlds, characters, locations, scenes, stories, tenants"
  - "django/: app_config, cache integration"
  - "auth.py: Token-basierte Authentifizierung (User-Token + Service-Token)"
  - "Error-Contract: WorldResult, CharacterResult mit ok/error_code/backend"
  - "CI: ci.yml + test.yml + publish.yml (Trusted Publishers)"
  - "50 unit tests (all green)"
  - "Noch offen (LOW): bfagent + travel-beat Consumer-Integration"
---

# ADR-117: Shared World Layer — Weltenhub-DB als SSoT, weltenfw als Schreibkanal

## Status

Accepted — v1.1 (2026-03-11, Review-Fixes: Auth-Konzept, Error-Contract)

## Context

bfagent (Buchprojekte), travel-beat (Reisen) und weltenhub (Weltenbau-Plattform)
arbeiten alle mit denselben Konzepten: Welten, Charaktere, Orte, Szenen.

Bisher:
- **bfagent** pflegt eigene `World`/`WorldCharacter`-Modelle (writing_hub)
- **travel-beat** pflegt eigene `Trip`-Welt-Felder + `TravelParty` für Charaktere
- **weltenhub** ist eine eigenständige Multi-Tenant Plattform für Weltenbau

Das führt zu Datenduplizierung, Divergenz und doppeltem Code.

## Decision

**Weltenhub-DB ist die einzige persistente Schicht für Weltenbau-Entitäten.**
Jede neue Welt / jeder neue Charakter bekommt eine UUID aus Weltenhub — ab dem
Zeitpunkt der Erstellung, egal ob der User im bfagent oder in weltenhub arbeitet.

Das bestehende Package **`iil-weltenfw`** (Repo: `achimdehnert/weltenfw`) wird um
ein Backend-Pattern erweitert und übernimmt die Rolle des **Shared Write Channel**.

### Prinzip

```
bfagent / travel-beat
         │
         │  from weltenfw import WeltenhubBackend
         │  backend.create_world(name="Mittelerde")  →  UUID aus Weltenhub
         ▼
    iil-weltenfw (WeltenhubBackend)
         │  schreibt via REST-API nach Weltenhub
         ▼
    ┌─────────────────────────────┐
    │  Weltenhub-DB (PostgreSQL)  │  ← einzige Datenbankschicht für Welten
    │  UUID wird hier vergeben    │
    └─────────────────────────────┘
         │  gibt UUID zurück
         ▼
    bfagent: World.weltenhub_world_id = UUID  ← nur Referenz, keine Kopie
```

### Zwei Szenarien

**Beide Szenarien schreiben IMMER in die Weltenhub-DB.**
Der Unterschied ist nur der Zeitpunkt der Account-Verknüpfung.

---

**Szenario A — User ist bereits Weltenhub-User (Account verknüpft):**

Beim Anlegen eines Buchs/Reise in bfagent/travel-beat ist der Weltenhub-Account
bereits bekannt (`user.weltenhub_token` vorhanden). Welt wird sofort angelegt.

```
bfagent: "Neues Buch" → backend.create_world()
    → Weltenhub-DB: INSERT, UUID vergeben
    → bfagent: writing_worlds.weltenhub_world_id = UUID
    → weltenhub UI: Welt sofort sichtbar
```

---

**Szenario B — User hat noch keinen Weltenhub-Account (Data ohne UI):**

Die Welt wird **trotzdem sofort in der Weltenhub-DB angelegt** — via S2S-Service-Token.
Der User bekommt noch keinen Zugang zur Weltenhub-UI. Die Daten liegen bereit.

```
bfagent: "Neues Buch" → WeltenhubBackend.create_world() mit Service-Token
    → Weltenhub-DB: INSERT (Tenant = System/Shared), UUID vergeben
    → bfagent: writing_worlds.weltenhub_world_id = UUID
    → weltenhub UI: NICHT sichtbar (kein User-Account verknüpft)

Später: User verknüpft Weltenhub-Account ("Sind Sie bereits Nutzer bei
        weltenforger.com?" / SSO-Login / Account-Erstellung)
    → Weltenhub: World wird User-Tenant zugeordnet
    → weltenhub UI: alle Welten/Charaktere sofort sichtbar + erweiterbar
    → Erweiterte Features freigeschaltet: Arcs, Regeln, Locations, Szenen
```

**Kernprinzip:** Die UUID existiert ab dem ersten Anlegen — immer.
Der Unterschied ist nur, ob der User die Weltenhub-UI-Features nutzen kann.

### Auth-Konzept (S2S + User)

Zwei Auth-Modi für WeltenhubBackend:

| Modus | Wann | Token-Typ | Audit |
|-------|------|-----------|-------|
| **User-Token** | Szenario A (Account verknüpft) | OAuth2 / Session-Token | User-ID im Request |
| **Service-Token** | Szenario B (kein Account) | HMAC-signiert (ADR-118) | `source_app` Header |

Service-Token wird pro Consumer-App erstellt und in `WELTENHUB_SERVICE_TOKEN` konfiguriert.
Weltenhub validiert HMAC-Signatur und loggt `source_app` für Audit-Trail.

### Error-Contract

```python
# weltenfw/backends/base.py
from pydantic import BaseModel

class WorldResult(BaseModel):
    ok: bool
    id: str | None = None
    error_code: str | None = None   # "auth_failed", "conflict", "unavailable", "timeout"
    error_message: str | None = None
    backend: str = "weltenhub"

class CharacterResult(BaseModel):
    ok: bool
    id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    world_id: str | None = None
    backend: str = "weltenhub"
```

Bei Netzwerk-Fehlern: Retry mit exponential Backoff (max 3 Versuche).
Bei 503/Timeout nach allen Retries: `WorldResult(ok=False, error_code="unavailable")`
→ Caller fällt auf Szenario B zurück (lokale Erstellung, späterer Upload).

### Gleicher Code für alle Konsumenten

```python
# Identisch in bfagent UND travel-beat:
from weltenfw import WeltenhubBackend

backend = WeltenhubBackend(
    base_url=settings.WELTENHUB_API_URL,
    # Szenario A: User-Token
    token=user.weltenhub_token,
    # Szenario B: Service-Token (HMAC per ADR-118)
    service_token=settings.WELTENHUB_SERVICE_TOKEN,
    source_app="bfagent",  # Audit-Trail
)
result = backend.create_world(name=project.title, description=project.description)
# result.id         → UUID aus Weltenhub
# result.ok         → True wenn erfolgreich
# result.error_code → None oder Fehler-Code
# result.backend    → "weltenhub"
```

### Package-Erweiterung in weltenfw (v0.2.0)

```
weltenfw/src/weltenfw/
├── backends/
│   ├── __init__.py
│   ├── base.py         # AbstractWorldBackend Protocol + WorldResult/CharacterResult
│   └── weltenhub.py    # WeltenhubBackend — wraps WeltenClient
└── ...
```

`LocalWorldBackend` existiert als leerer Stub für Tests / Apps ohne Weltenhub-Verbindung.
Er schreibt nichts — der Caller verwaltet die lokale DB selbst.

### Datenfluss (Szenario A — Weltenhub aktiv)

```
User legt Buch an (bfagent)
    │
    ▼
bfagent service: backend.create_world(name="Drachenwelt")
    │
    ▼  WeltenhubBackend.create_world()
    │  → POST /api/v1/worlds/worlds/  (iil-weltenfw WeltenClient)
    ▼
Weltenhub-DB: INSERT wh_world → UUID vergeben
    │
    ▼  response: {"id": "uuid-xyz", "name": "Drachenwelt"}
    ▼
bfagent: writing_worlds.weltenhub_world_id = "uuid-xyz"  ← nur UUID gespeichert
    │
    ▼
User öffnet Weltenhub → "Drachenwelt" ist sofort da — kein Sync, keine Kopie
```

### Datenfluss (Szenario B — Weltenhub nachträglich)

```
User legt Buch an (bfagent, ohne Weltenhub-Abo)
    │
    ▼
bfagent: World lokal in writing_worlds → weltenhub_world_id = None
    │
    ▼  (später: User bucht Weltenhub)
    ▼
Management Command: upload_worlds_to_weltenhub
    │  iteriert alle lokalen Welten ohne weltenhub_world_id
    │  für jede: WeltenhubBackend.create_world() → UUID
    │  setzt weltenhub_world_id auf lokales Modell
    ▼
Ab sofort: neue Welten direkt via WeltenhubBackend
```

## Consequences

### Positiv
- **Kein Sync-Loop**: UUID wird genau einmal vergeben — beim Create in Weltenhub
- **Keine Datenkopien**: bfagent/travel-beat speichern nur die UUID-Referenz
- **Alle Konsumenten gleich**: identischer weltenfw-Code in bfagent und travel-beat
- **Rückwärtskompatibel**: Szenario B erlaubt späte Aktivierung ohne Breaking Change
- **Erweiterbar**: Neues WeltenhubBackend-Feature ohne Code-Änderung in den Apps
- **Testbar**: WeltenhubBackend ist mockbar (WeltenClient via respx)

### Negativ / Risiken
- **Latenz**: WeltenhubBackend-Calls sind synchron HTTP
  → Mitigation: Celery-Task für nicht-blockierende Erstellung
- **Weltenhub-Ausfall beim Create**: Wenn Weltenhub down → UUID nicht verfügbar
  → Mitigation: Retry + lokaler Fallback mit nachträglichem Upload (Szenario B)
- **Tenant-Provisioning nötig**: User muss zuerst in Weltenhub provisioniert werden
  → bereits implementiert in `weltenfw.backends.weltenhub.WeltenhubBackend.provision_user()`

## Affected Repos

| Repo | Änderung |
|------|----------|
| `weltenfw` | v0.2.0: `backends/` Package hinzufügen |
| `bfagent` | `iil-weltenfw` dependency + `WeltenhubBackend` nutzen — **wird decommissioned (#35), Rolle → writing-hub** |
| `travel-beat` | bestehende weltenfw-Nutzung auf `WeltenhubBackend` umstellen |
| `weltenhub` | S2S-Auth-Endpoint für Service-Token (HMAC, ADR-118) |
| `writing-hub` | **Nachfolge-Konsument für bfagent** (Amendment 2026-07-01); nutzt `iil-weltenfw` bereits |
| `illustration-hub` | **Neuer Konsument** (Amendment 2026-07-01); konsumiert Welt/Ort/Charakter für Illustrationen |

## Related ADRs

- ADR-082: WorldCharacter SSoT in bfagent
- ADR-032 (weltenfw): bestehender Weltenhub-Client für travel-beat
- ADR-109: Multi-Tenancy Platform Standard
- ADR-118: Platform Store / HMAC Auth (S2S-Token-Konzept)

## Amendment 2026-07-01 (v1.2) — writing-hub als Nachfolge-Konsument, illustration-hub, Szenen-Grenze

**Kein neuer Entscheid — Erweiterung des Konsumenten-Kreises.** Die Kern-Entscheidung
(Weltenhub-DB = SSoT für Weltenbau-Entitäten, `iil-weltenfw` = Shared Channel) bleibt unverändert.

1. **writing-hub ersetzt bfagent als Buch-/Autoren-Konsument.** bfagent (dessen Django-App `writing_hub`
   in diesem ADR referenziert ist — **nicht** zu verwechseln mit dem Nachfolge-*Repo* `writing-hub`;
   Altcode/Doku entsprechend disambiguieren) wird decommissioned (#35). **writing-hub** ist der Nachfolger,
   nutzt `iil-weltenfw` bereits (`requirements.txt:48`) und erbt die bfagent-Rolle: es hält nur
   `weltenhub_*_id`-UUID-Referenzen, keine Kopien.
   **Migrations-Invarianten (kein „1:1"-Handwave):** bestehende `consumer_app="bfagent"`-Rows werden
   nach `"writing_hub"` migriert **oder** explizit eingefroren (read-only); alte `wh_authored_uuid`-Links
   werden abgebildet; `BfagentContext` in `CONSUMER_SCHEMAS` bekommt ein **Entfernungsdatum**. Bestehende
   UUIDs bleiben stabil (kein Neu-Create).

2. **writing-hub *definiert* die Story, weltenhub die Welt-Assets.** Präzisierung der Ownership-Grenze:
   - **weltenhub = SSoT** für **Welt, Ort, Charakter** — world-scoped und über Buchreihen wiederverwendbar.
   - **Charakter-Präzisierung (Identität vs. Zustand):** weltenhub besitzt die **stabile Identität**
     (Name, Erscheinung/Visual-Canon, Herkunft); der **Narrativzustand *innerhalb* einer Story**
     (tot/lebendig, Beziehungen@T, Arc-Fortschritt) gehört zu writing-hub. „Wiederverwendbar" gilt für
     die stabile Identität, nicht für den Story-Zustand (sonst bricht der erste Prequel/Parallel-Serie-Fall).
   - **writing-hub = führende Quelle für Story** (Dramaturgie, Serie, Kapitel, Outline via `iil-outlinefw`, ADR-121).
   - **Story-Grenze wird ERZWUNGEN, nicht nur beabsichtigt:** weltenhubs `Story`-Modell ist ab v1.2
     **ausdrücklich nicht-autoritativ** für Buch-Dramaturgie — es darf world-scoped Narrativ-Verknüpfungen
     halten, **nicht** Kapitelstruktur / Serien-Arcs / finale Outline / konkrete Buchdramaturgie.
   - **Follow-up (eigener ADR, nicht in diesem Amendment):** die vollständige Auflösung der Story-Kollision
     (weltenhub-`Story` umbenennen z. B. `WorldNarrativeLink` **oder** deprecaten) ist eine eigene
     Grenz-Entscheidung → **eigener ADR mit „Alternatives Considered"** (Governance: neue Grenze = ADR).

3. **Szenen-Grenze (Sub-Entscheid 2026-07-01) — mit operationalem Contract:** **weltenhub liefert
   Szenen-Bausteine/Templates** (`SceneTemplate`), **writing-hub besitzt den Szenen-Inhalt**
   (`OutlineNode(scene)` + Prosa). Damit die Naht eine Linie und kein Spektrum ist:
   - **`SceneTemplate` DARF:** abstrakte, parametrisierbare, welt-/genre-gebundene Struktur (Beat-Gerüst,
     Stimmung, benötigte Story-Elemente als Slots, typische Dauer).
   - **`SceneTemplate` DARF NICHT:** benannte Story-Ereignisse, konkrete POV-Prosa, finale Beats,
     Kapitelnummer, story-spezifische Figurenzustände.
   - **Instanziierung:** writing-hub referenziert `SceneTemplate.uuid` und erzeugt daraus eine eigene
     `OutlineNode(scene)` mit story-spezifischem Inhalt — nur Referenz, keine Kopie.
   - **Abgrenzung zu `iil-outlinefw`:** SceneTemplate = *Szenen-Vorlage* (Welt-Asset); `iil-outlinefw` =
     *Story-Outline-Framework* (Konsument-seitig). Ein „promote-scene-to-template"-Pfad wird bei Bedarf
     als eigenes Ticket geführt, nicht implizit erlaubt.

4. **illustration-hub als neuer Konsument — mit Visual-Canon-Regel.** Konsumiert Welt/Ort/Charakter aus
   weltenhub (heute kein `iil-weltenfw`-Pin) für die Illustrations-Erzeugung.
   **Erscheinungs-Kanon ist world-scoped SSoT:** Charakter-/Location-**Erscheinung** lebt strukturiert auf
   weltenhubs `Character`/`Location` (analog `systems_data`, ADR-095), **nicht** im konsumenten-scoped
   AuthoredContent-Thread — sonst re-etabliert man im visuellen Kern genau die Divergenz, die ADR-117
   verhindert. illustration-hub komponiert Prompts aus dem Welt-Kanon **+ eigenem Stil-Kontext**.
   (Detail + Exit-Klausel für Prompt-Metadaten → ADR-119-Amendment v1.2.)

5. **Strukturierter Weltenbau (Bezug + Konsum-Regel):** `weltenhub:ADR-095` (`World.systems_data`)
   erweitert den SSoT konsistent; Herleitung `KONZ-weltenhub-001`. Konsumenten (writing-hub/illustration-hub)
   **referenzieren/projizieren** `systems_data` selektiv — **keine Kopie, keine konkurrierende Struktur** im Konsumenten.

**Betroffene Repos (Delta):** `writing-hub` (kanonischer Konsument statt bfagent + bfagent-Daten-Migration),
`illustration-hub` (neue Integration), `weltenhub` (`SceneTemplate` als Konsum-Fläche exponieren;
strukturiertes Visual-Canon-Feld auf `Character`/`Location`; `Story`-Nicht-Autoritativ-Enforcement + Story-ADR-Follow-up).

**Aus externem Review gehärtet (2026-07-01, 2 Reviewer, Step-5-Tagging):** Punkte 1–5 oben tragen die
`[valid]`-Befunde ein (Migrations-Invarianten, Identität-vs-Zustand, erzwungene Story-Grenze + eigener ADR,
SceneTemplate-Contract, Visual-Canon world-scoped). Settled-Kern-Befunde (GFK-vs-FK, Szenario-B-Wording,
CONSUMER_SCHEMAS-Dezentralisierung) sind bewusst **out-of-scope** dieses Konsumenten-Amendments → Hardening-Backlog.
Nachweis: `~/shared/adr-handoff-ADR-117-119-2026-07-01-RUECKFLUSS.md`.

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-11 | v1.0 | Cascade | ❌ 3 BLOCKs (Frontmatter, Auth, Error-Contract) | [Review](../reviews/ADR-117-review-2026-03-11.md) |
| 2026-03-11 | v1.0 → v1.1 | Cascade | Fixes applied | — |
| 2026-07-01 | v1.1 → v1.2 | — | Amendment: writing-hub (Nachfolge bfagent), illustration-hub, Szenen-Grenze | — |
