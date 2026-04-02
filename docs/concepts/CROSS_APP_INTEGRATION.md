# Cross-App Integration Pattern — Shared DB via weltenfw Storage Backend

**Version:** 1.0 (2026-03-10)
**ADR:** [ADR-117](../adr/ADR-117-shared-world-layer-worldfw.md)
**Status:** Aktiv — verwendet in bfagent + travel-beat

---

## Problem

Mehrere Apps (bfagent, travel-beat, …) arbeiten mit denselben Domänen-Entitäten
(Welten, Charaktere, Orte). Ohne gemeinsame Infrastruktur entsteht:

- **Datenduplizierung**: dieselbe Welt in 3 DBs
- **Sync-Loops**: Push-Sync → Inkonsistenz → mehr Sync
- **Divergenz**: Änderung in App A sichtbar, in App B nicht

## Lösung: Shared DB via Storage Backend

Eine App ist **Datenbankinhaber** (hier: Weltenhub).
Alle anderen Apps sind **Konsumenten** — sie schreiben via Package-API
direkt in die Ziel-DB und speichern lokal nur die UUID-Referenz.

```
Consumer App (bfagent / travel-beat)
         │
         │  from weltenfw import WeltenhubBackend
         │  result = backend.create_world(name=...)
         ▼
    iil-weltenfw Package (Schreibkanal)
         │  POST /api/v1/worlds/worlds/
         ▼
    Weltenhub-DB (PostgreSQL) ← einzige persistente Schicht
         │  gibt UUID zurück
         ▼
    consumer_app.local_model.weltenhub_world_id = UUID
    (nur Referenz — keine Kopie der Daten)
```

---

## Zwei Szenarien

### Szenario A — User ist bereits registriert

```
User legt Entität in Consumer-App an
    → Consumer-App hat user.weltenhub_token
    → WeltenhubBackend(token=user_token).create_world()
    → UUID sofort in Weltenhub-DB
    → Ziel-App UI zeigt Entität sofort
    → Erweiterte Features verfügbar
```

### Szenario B — User noch nicht registriert ("Data ohne UI")

```
User legt Entität in Consumer-App an
    → Kein user.weltenhub_token vorhanden
    → WeltenhubBackend(token=service_token).create_world()
    → UUID in Weltenhub-DB (unter System-Tenant)
    → Consumer-App arbeitet normal weiter mit UUID
    → Ziel-App UI: noch nicht sichtbar (kein User-Account)

Später: User verknüpft Account
    → provision_user() → per-user Token
    → Entitäten werden User-Tenant zugeordnet
    → Ziel-App UI: alle Daten sofort sichtbar
    → Erweiterte Features freigeschaltet
```

**Kernprinzip:** Die UUID existiert ab dem ersten Anlegen — immer.
Der Unterschied ist nur, welche Features des Ziel-Systems verfügbar sind.

---

## Implementierungs-Checkliste

### 1. Consumer-App: Modell-Felder

```python
# models.py — nur UUID-Referenz, keine inhaltlichen Felder
class MyEntity(models.Model):
    # ... eigene Felder ...
    weltenhub_world_id = models.CharField(
        max_length=50, blank=True, null=True, db_index=True,
        help_text="Weltenhub World UUID (ADR-117)",
    )
    weltenhub_synced_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Zeitpunkt der letzten Weltenhub-Registrierung",
    )
```

Migration erstellen:
```bash
python manage.py makemigrations myapp --name weltenhub_refs
```

### 2. Consumer-App: Settings

```python
# config/settings/base.py
WELTENHUB_API_URL = os.environ.get("WELTENHUB_API_URL", "https://weltenforger.com/api/v1")
WELTENHUB_API_KEY = os.environ.get("WELTENHUB_API_KEY", "")   # Service-Token
WELTENHUB_TIMEOUT = float(os.environ.get("WELTENHUB_TIMEOUT", "30"))
```

`.env.prod` / `.env.example`:
```
WELTENHUB_API_URL=https://weltenforger.com/api/v1
WELTENHUB_API_KEY=<service-token-from-weltenhub-admin>
WELTENHUB_TIMEOUT=30
```

### 3. Consumer-App: Dependency

```
# requirements.txt
iil-weltenfw>=0.2.0,<1
```

### 4. Consumer-App: Service

```python
# apps/<myapp>/services/weltenhub_service.py

from __future__ import annotations
import logging
from dataclasses import dataclass
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


def _api_url() -> str:
    return getattr(settings, "WELTENHUB_API_URL", "https://weltenforger.com/api/v1").rstrip("/")

def _service_token() -> str:
    return getattr(settings, "WELTENHUB_API_KEY", "")

def _timeout() -> float:
    return float(getattr(settings, "WELTENHUB_TIMEOUT", 30))


@dataclass(frozen=True)
class RegistrationResult:
    world_id: str
    world_name: str
    created: bool = False
    ui_available: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return bool(self.world_id) and self.error is None


class WeltenhubIntegrationService:
    """Weltenhub-Integration für <APP_NAME> (ADR-117)."""

    def __init__(self, user):
        self._user = user

    def _user_token(self) -> str | None:
        return getattr(self._user, "weltenhub_token", None) or None

    def _backend(self, token: str):
        from weltenfw.backends.weltenhub import WeltenhubBackend
        return WeltenhubBackend(base_url=_api_url(), token=token, timeout=_timeout())

    def is_ui_available(self) -> bool:
        """True wenn User Weltenhub-Account verknüpft hat."""
        return bool(self._user_token())

    def ensure_registered(self, entity, *, name: str, description: str = "") -> RegistrationResult:
        """Registriert entity in Weltenhub. Idempotent."""
        world_id = getattr(entity, "weltenhub_world_id", None)
        if world_id:
            return RegistrationResult(
                world_id=world_id,
                world_name=name,
                ui_available=self.is_ui_available(),
            )

        token = self._user_token() or _service_token()
        if not token:
            return RegistrationResult(world_id="", world_name=name,
                                      error="WELTENHUB_API_KEY nicht konfiguriert")

        backend = self._backend(token)
        result = backend.create_world(name=name, description=description)
        if not result.ok:
            return RegistrationResult(world_id="", world_name=name, error=result.error)

        # UUID lokal speichern — nur Referenz
        entity.weltenhub_world_id = result.id
        entity.weltenhub_synced_at = timezone.now()
        entity.save(update_fields=["weltenhub_world_id", "weltenhub_synced_at"])

        logger.info("weltenhub_entity_registered",
                    extra={"entity_id": entity.pk, "world_id": result.id,
                           "scenario": "A" if self._user_token() else "B"})

        return RegistrationResult(
            world_id=result.id, world_name=result.name,
            created=True, ui_available=self.is_ui_available(),
        )

    def provision_user_account(self) -> bool:
        """Szenario A: User-Account in Weltenhub anlegen/verknüpfen."""
        try:
            from weltenfw.backends.weltenhub import WeltenhubBackend
            token = WeltenhubBackend.provision_user(
                username=self._user.username,
                email=self._user.email,
                base_url=_api_url(),
                service_token=_service_token(),
                timeout=_timeout(),
            )
            if not token:
                return False
            if hasattr(self._user, "weltenhub_token"):
                self._user.weltenhub_token = token
                self._user.save(update_fields=["weltenhub_token"])
            return True
        except Exception as exc:
            logger.warning("weltenhub_provision_failed", extra={"error": str(exc)})
            return False
```

### 5. Weltenhub: ExternalProject registrieren (optional aber empfohlen)

Nach `create_world()` die Consumer-App als `ExternalProject` in Weltenhub eintragen:

```python
# POST /api/v1/worlds/worlds/{world_id}/link-project/
{
    "source_app": "my_app",          # z.B. "bfagent", "travel_beat"
    "external_id": str(entity.pk),
    "project_name": entity.title,
    "project_type": "book",          # oder "trip", "series", …
    "external_slug": entity.slug,
}
```

So weiß Weltenhub, welche Consumer-App-Entität mit welcher Welt verknüpft ist
(bidirektionale Referenz).

---

## Muster-Zusammenfassung

| Schritt | Consumer-App macht | Weltenhub macht |
|---------|-------------------|-----------------|
| Entität anlegen | `backend.create_world(name=…)` | INSERT in wh_world, UUID vergeben |
| UUID speichern | `entity.weltenhub_world_id = uuid` | — |
| Projekt verknüpfen | POST link-project | ExternalProject erstellen |
| User verknüpfen | `provision_user()` → Token speichern | User + Tenant anlegen (idempotent) |
| Daten lesen | `backend.get_world(uuid)` / `list_characters(uuid)` | Daten aus wh_world liefern |
| Features prüfen | `is_ui_available()` | — |

---

## Was NICHT gemacht wird

- ❌ **Keine Datenkopien** — Consumer-App speichert keine Welt-/Charakter-Felder lokal
- ❌ **Kein Sync-Loop** — kein Webhook, kein Event-Bus, kein Celery-Beat-Sync
- ❌ **Kein Push-Sync** — kein periodisches Hochladen von Änderungen
- ❌ **Keine doppelte UUID-Vergabe** — UUID kommt immer aus Weltenhub

---

## Erweiterbarkeit

Das Pattern ist nicht auf Weltenhub beschränkt. Für ein anderes Ziel-System:

1. Neues Backend implementieren (implementiert `AbstractWorldBackend` Protocol)
2. Settings anpassen (`MY_SERVICE_URL`, `MY_SERVICE_KEY`)
3. Service-Klasse instanziiert neues Backend

Kein Code in der Consumer-App muss geändert werden.

---

## Bestehende Implementierungen

| Consumer-App | Service | Modell-Felder | Migration |
|---|---|---|---|
| bfagent | `apps/writing_hub/services/weltenhub_sync.py` | `World.weltenhub_world_id` | `0050_weltenhub_refs` |
| travel-beat | `apps/stories/services/weltenfw_adapter.py` | `Trip.weltenhub_world_id` | — |

---

## Verwandte Dokumente

- [ADR-117](../adr/ADR-117-shared-world-layer-worldfw.md) — Architektur-Entscheidung
- [weltenfw backends/ README](https://github.com/achimdehnert/weltenfw/blob/main/src/weltenfw/backends/README.md)
- [weltenfw README](https://github.com/achimdehnert/weltenfw/blob/main/README.md)
