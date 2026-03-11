---
status: accepted
date: 2026-03-10
updated: 2026-03-11
decision-makers: Achim Dehnert
---

# ADR-119: AuthoredContent Pipeline — Neutral Lore → Autorenstil Thread

## Status

Accepted — v1.1 (2026-03-11, Review-Fixes aus [platform#24](https://github.com/achimdehnert/platform/issues/24))

**Repos:** weltenhub, bfagent, travel-beat
**Related:** ADR-117 (Shared World Layer), ADR-041 (Component Pattern), ADR-118 (billing-hub HMAC)

## Context

Weltenhub speichert Weltenbau-Daten (Welten, Orte, Szenen, Charaktere) in einem **neutralen, faktischen Lore-Stil** — vergleichbar einem Wiki. Konsumenten wie bfagent (Roman-Autor) oder travel-beat (Reiseblog) benötigen dieselben Inhalte jedoch im **eigenen Autorenstil**, angereichert mit ihrem spezifischen Kontext (z.B. Kapitel-Outline, Story-Arc, Ton).

Bisher gibt es keine systematische Trennung zwischen neutralem Lore und stilistisch aufbereitetem Content. Autoren müssen Weltenhub-Inhalte manuell umformulieren.

## Decision

Wir führen eine **AuthoredContent Pipeline** ein:

```
Weltenhub (neutral)          AuthoredContent Thread        Konsument
──────────────────           ─────────────────────         ─────────
World / Location /    ──►    UUID-identifizierter    ──►   bfagent
Scene / Character            Stil-Thread                   travel-beat
  (Lore, faktisch)           (AI + manuell editierbar)     (etc.)
                             + Konsumenten-Kontext
```

### Datenmodell

`AuthoredContent` ist ein **generischer Thread** auf einem beliebigen Weltenhub-Objekt.
Das Model lebt in **weltenhub** (`apps/enrichment/models.py`). Konsumenten (bfagent,
travel-beat) greifen ausschließlich über die weltenhub-API zu.

```python
# weltenhub: apps/enrichment/models.py
class AuthoredContent(TenantAwareModel):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    # ↑ Sekundärer Identifier für Inter-App-Kommunikation.
    # PK bleibt BigAutoField (Platform-Konvention / ADR-022).

    # Polymorphe Quelle (Scene, Location, World, Character)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id    = models.PositiveBigIntegerField()  # kompatibel mit BigAutoField
    source       = GenericForeignKey("content_type", "object_id")

    # Konsumenten-Kontext (kommt vom Konsumenten beim Request)
    consumer_app     = models.CharField(max_length=50)   # "bfagent", "travel_beat"
    consumer_ref_id  = models.CharField(max_length=100)  # opaker String für den Konsumenten
    consumer_context = models.JSONField(default=dict)    # validiert via Pydantic (s.u.)

    # Autorenstil-Inhalt
    authored_text    = models.TextField(blank=True)
    previous_text    = models.TextField(blank=True)      # Undo bei regenerate
    style_notes      = models.TextField(blank=True)      # Redaktionelle Hinweise
    is_ai_generated  = models.BooleanField(default=False)
    is_approved      = models.BooleanField(default=False)

    # Sync
    last_generated_at = models.DateTimeField(null=True, blank=True)
    created_at        = models.DateTimeField(auto_now_add=True)
```

> **Hinweis `consumer_ref_id`:** Opaker String — weltenhub interpretiert ihn nicht.
> Der Konsument nutzt ihn um den AuthoredContent seinem eigenen Objekt zuzuordnen
> (z.B. `"chapter-123"` in bfagent). Weltenhub speichert ihn nur als Referenz.

> **Hinweis Quell-Löschung:** Wenn ein Quell-Objekt (Scene, Location) gelöscht wird,
> verwaist der `AuthoredContent` (GenericFK hat keinen DB-Constraint). Ein täglicher
> Celery-Job (`cleanup_orphaned_authored_content`) bereinigt verwaiste Einträge.

### Schema-Validierung (`consumer_context`)

Jeder `consumer_app` hat ein definiertes Pydantic-Schema. Validierung erfolgt im
Serializer **vor** der DB-Speicherung:

```python
# weltenhub: apps/enrichment/schemas.py
from pydantic import BaseModel

class BfagentContext(BaseModel):
    outline: str
    tone: str = "neutral"
    pov: str = "third_person_limited"

class TravelBeatContext(BaseModel):
    destination: str
    travel_style: str = "adventure"
    audience: str = "general"

CONSUMER_SCHEMAS: dict[str, type[BaseModel]] = {
    "bfagent": BfagentContext,
    "travel_beat": TravelBeatContext,
}

def validate_consumer_context(consumer_app: str, context: dict) -> dict:
    schema = CONSUMER_SCHEMAS.get(consumer_app)
    if schema is None:
        raise ValueError(f"Unbekannter consumer_app: {consumer_app}")
    return schema(**context).model_dump()
```

Neue Konsumenten registrieren ihr Schema in `CONSUMER_SCHEMAS`.

### API-Flow

**Auth-Konzept:**
- **Intra-App** (weltenhub-intern, z.B. UI): Session-Auth + Tenant-Isolation (TenantAwareModel)
- **Inter-App** (bfagent → weltenhub): HMAC-Signatur analog ADR-118 (`WELTENHUB_HMAC_SECRET`)
  via `decouple.config()`. Rate-Limiting: **10 Requests/Minute** pro Konsument.

**Konsument → Weltenhub (generate):**

```
POST /api/v1/authored-content/generate/
Headers: X-Consumer-Timestamp + X-Consumer-Signature (HMAC)
{
  "source_type": "scene",
  "source_id":   42,
  "consumer_app": "bfagent",
  "consumer_ref_id": "chapter-123",
  "consumer_context": {
    "outline": "Held betritt verlassene Stadt...",
    "tone": "melancholisch",
    "pov": "third_person_limited"
  }
}
→ 202 Accepted { "task_id": "celery-task-uuid", "uuid": "abc-123-..." }
```

> **Async-Pflicht:** LLM-Generierung läuft als Celery-Task (2–30s Dauer).
> Response ist `202 Accepted` mit `task_id`. Konsument pollt auf Status.

**Konsument pollt auf Ergebnis:**
```
GET /api/v1/authored-content/{uuid}/
→ 200 { "uuid": "...", "authored_text": "...", "status": "ready", "is_approved": false }
→ 200 { "uuid": "...", "authored_text": "", "status": "generating" }  # noch nicht fertig
```

**Konsument aktualisiert Kontext (re-generate):**
```
PATCH /api/v1/authored-content/{uuid}/regenerate/
{ "consumer_context": { "outline": "neues Outline..." } }
→ 202 Accepted { "task_id": "...", "previous_text": "... alter Text ..." }
```

> **Versionierung:** Bei `/regenerate/` wird der aktuelle `authored_text` in
> `previous_text` gesichert. Ermöglicht Undo wenn der neue Text schlechter ist.

### AI-Generierung (Celery-Task)

- LLM-Prompt wird aus **neutralem Lore-Text** (Weltenhub-Objekt) + **Konsumenten-Kontext** zusammengesetzt
- Verwendet `iil-aifw` / `weltenfw` Backend
- Läuft als **Celery-Task** (`apps/enrichment/tasks.py`) — niemals synchron im Request
- Ergebnis ist editierbar (`authored_text` direkt überschreibbar)
- `is_approved = True` setzt Autor manuell — signalisiert "fertig für Konsumenten"

### Konsumenten-Integration

**bfagent:**
- `BookChapter` bekommt `wh_authored_uuid` Feld
- Beim Chapter-Öffnen: Authored Text wird geladen und als Schreib-Grundlage angeboten
- Outline (aus `chapter.summary` + `plot_threads`) wird als `consumer_context` übergeben

**travel-beat:**
- `Story` / `Location` bekommt `wh_authored_uuid` Feld
- Autorenstil = Reiseblog-Ton

## Consequences

**Positiv:**
- Klare Trennung: Lore (neutral, stabil) vs. Content (Stil, konsumenten-spezifisch)
- Gleicher Lore kann N Authored Threads haben (bfagent Roman + travel-beat Blog)
- UUID-Identifikation ermöglicht versionsloses Linking
- AI + manuelles Editing kombinierbar

**Negativ / Risiken:**
- `django.contrib.contenttypes` GenericForeignKey erhöht Query-Komplexität (kein `select_related()`)
- AI-Generierung kostet Token — Rate-Limiting (10/min) und Celery-Task sind Pflicht
- `is_approved` Workflow muss in UI abgebildet werden
- Verwaiste AuthoredContent bei Quell-Löschung (Cleanup-Job nötig)

## Implementation Plan

1. `apps/enrichment/` Modul in weltenhub anlegen (models, schemas, serializers, views, tasks)
2. `AuthoredContent` Model + Migration
3. `AuthoredContentSerializer` mit Pydantic-Schema-Validierung
4. `AuthoredContentViewSet` mit HMAC-Auth für Inter-App
5. `/api/v1/authored-content/` + `/generate/` (async) + `/regenerate/` (async)
6. Celery-Task `generate_authored_content` in `apps/enrichment/tasks.py`
7. Cleanup-Job `cleanup_orphaned_authored_content` (täglich)
8. bfagent: `wh_authored_uuid` auf `BookChapter` + Service-Methode
9. travel-beat: analog

## Betroffene Repos

- `weltenhub` — AuthoredContent Model, API, Celery-Tasks, Pydantic-Schemas
- `bfagent` — `wh_authored_uuid` auf BookChapter, Service-Integration
- `travel-beat` — `wh_authored_uuid` auf Story/Location, Service-Integration
- `weltenfw` — nicht betroffen (AuthoredContent lebt in weltenhub, nicht in der Library)

## Review-History

| Datum | Version | Reviewer | Urteil | Link |
|-------|---------|----------|--------|------|
| 2026-03-11 | v1.0 → v1.1 | Cascade | ❌ → Fixes applied | [Review](../reviews/ADR-119-review-2026-03-11.md) · [Issue #24](https://github.com/achimdehnert/platform/issues/24) |
