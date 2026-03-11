---
status: accepted
date: 2026-02-21
amended: 2026-02-24
decision-makers: Achim Dehnert
consulted: –
informed: –
implementation_status: implemented
implementation_evidence:
  - "testkit: iil-testkit v0.1.0 on PyPI with tenant fixtures"
  - "platform/docs/adr/ADR-074: testing strategy defined and usable"
---

# ADR-074: Multi-Tenancy Testing Strategy — Isolation, Propagation & CI Gates

| Attribut       | Wert                                                                 |
|----------------|----------------------------------------------------------------------|
| **Status**     | Accepted                                                             |
| **Scope**      | platform                                                             |
| **Repo**       | platform                                                             |
| **Erstellt**   | 2026-02-21                                                           |
| **Autor**      | Achim Dehnert                                                        |
| **Reviewer**   | –                                                                    |
| **Supersedes** | –                                                                    |
| **Relates to** | ADR-056 (Multi-Tenancy Schema Isolation), ADR-035 (Shared Django Tenancy), ADR-021 (Unified Deployment) |

---

## Decision Drivers

- **DSGVO-Kritikalität**: Ein Datenleck zwischen Mandanten ist ein regulatorischer Vorfall — Tests müssen das strukturell verhindern, nicht nur dokumentieren
- **CI-Gate**: Tenant-Isolation-Tests müssen Merges blockieren, nicht nur warnen
- **Multi-Repo**: Jeder Service hat eigene Tests — gemeinsame Fixtures und Patterns müssen in `platform_context` liegen
- **1 Entwickler**: Minimaler Test-Overhead; Fixtures einmal schreiben, überall nutzen
- **`django-tenants` Eigenheiten**: `TenantTestCase` vs. `TestCase` — falsche Basisklasse führt zu Silent Failures
- **3 Kommunikationskanäle**: REST, Celery, DB-Views müssen alle separat auf Tenant-Context-Propagation getestet werden

---

## 1. Kontext

### 1.1 Was Multi-Tenancy-Tests von normalen Tests unterscheidet

Normale Django-Tests laufen in einer einzigen DB-Transaktion die am Ende zurückgerollt wird. Bei Schema-Isolation via `django-tenants` gibt es zwei fundamentale Unterschiede:

1. **Schema-Wechsel erfordert `transaction=True`**: `search_path`-Änderungen sind Connection-Properties, keine Transaktions-Properties. `pytest-django`'s Standard-Rollback funktioniert nicht über Schema-Grenzen.

2. **Silent Failure-Risiko**: Ein Test der vergisst `schema_context` zu setzen, läuft im `public`-Schema — er schlägt nicht fehl, er testet einfach das Falsche.

```python
# FALSCH — läuft im public-Schema, testet nichts Sinnvolles
def test_assessment_isolation(db):
    Assessment.objects.create(title="Geheim")
    assert Assessment.objects.count() == 1  # Grün, aber im falschen Schema!

# RICHTIG — expliziter Schema-Context
@pytest.mark.django_db(transaction=True)
def test_assessment_isolation(tenant_a, tenant_b):
    with schema_context(tenant_a.schema_name):
        Assessment.objects.create(title="Geheim")
    with schema_context(tenant_b.schema_name):
        assert Assessment.objects.count() == 0  # Echte Isolation
```

### 1.2 Bestehende Teststrategie (Ist-Zustand)

Aktuell haben die Services keine Tenant-Isolation-Tests. ADR-035 hat Tenancy-Infrastruktur konsolidiert, aber keine Test-Standards definiert. Die Folge: Jeder Service testet Tenancy anders (oder gar nicht).

### 1.3 Constraints

- **`django-tenants>=3.6`** — `TenantTestCase` und `TenantClient` verfügbar
- **`pytest-django`** — Standard in allen Services (ADR-056 §6)
- **Self-Hosted Runner** auf VPS — keine parallelen DB-Connections über Limits
- **`platform_context`** als vendored Shared Library — Fixtures gehören hierhin
- **PostgreSQL** in CI via GitHub Actions Service Container

---

## 2. Entscheidung

**Drei-Schichten-Teststrategie** für Multi-Tenancy:

1. **Layer 1 — Isolation Tests** (Pflicht, CI-Gate): Daten aus Mandant A sind in Mandant B nicht sichtbar
2. **Layer 2 — Propagation Tests** (Pflicht, CI-Gate): Tenant-Context wird über alle 3 Kanäle korrekt weitergegeben
3. **Layer 3 — Provisioning Tests** (Pflicht vor Produktion): Neuer Mandant wird korrekt in allen Service-DBs angelegt

Alle Fixtures und Basisklassen leben in `platform_context/tenant_utils/testing.py` — einmal schreiben, in jedem Service nutzen.

---

## 3. Betrachtete Alternativen

### Option A: Drei-Schichten-Strategie mit Shared Fixtures (gewählt)

Zentrale Fixtures in `platform_context`, Service-spezifische Tests nutzen sie. Klare Schichtentrennung.

### Option B: Jeder Service definiert eigene Fixtures

**Abgelehnt.** Führt zu Drift (ADR-035-Problem wiederholt sich). Fehler in Fixtures werden nicht plattformweit behoben.

### Option C: Nur Smoke-Tests (2 Mandanten, kein strukturierter Layer-Ansatz)

**Abgelehnt.** Nicht ausreichend für DSGVO-Compliance. Propagation-Tests fehlen — der häufigste Fehlerfall (Context geht bei Cross-Service-Call verloren) wird nicht abgedeckt.

---

## 4. Test-Architektur im Detail

### 4.1 Shared Fixtures in `platform_context`

```python
# vendor/platform_context/src/platform_context/tenant_utils/testing.py

import pytest
from django_tenants.test.cases import TenantTestCase
from django_tenants.test.client import TenantClient
from django_tenants.utils import schema_context


@pytest.fixture(scope="function")
def tenant_a(db):
    """Erstellt Mandant A für Isolation-Tests."""
    from tenants.models import Client, Domain
    tenant = Client(schema_name="test_tenant_a", name="Test Tenant A")
    tenant.save(verbosity=0)
    Domain.objects.create(
        domain="tenant-a.test.local",
        tenant=tenant,
        is_primary=True,
    )
    yield tenant
    # Cleanup: Schema droppen
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_tenant_a CASCADE")


@pytest.fixture(scope="function")
def tenant_b(db):
    """Erstellt Mandant B für Isolation-Tests."""
    from tenants.models import Client, Domain
    tenant = Client(schema_name="test_tenant_b", name="Test Tenant B")
    tenant.save(verbosity=0)
    Domain.objects.create(
        domain="tenant-b.test.local",
        tenant=tenant,
        is_primary=True,
    )
    yield tenant
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_tenant_b CASCADE")


@pytest.fixture
def tenant_a_client(tenant_a):
    """Django Test Client im Context von Mandant A."""
    return TenantClient(tenant_a)


@pytest.fixture
def tenant_b_client(tenant_b):
    """Django Test Client im Context von Mandant B."""
    return TenantClient(tenant_b)
```

### 4.2 Layer 1: Isolation Tests (Pflicht-Gate)

**Wo:** `apps/<app>/tests/test_tenant_isolation.py` in jedem SaaS-Service

**Muster:**

```python
# apps/assessments/tests/test_tenant_isolation.py
import pytest
from django_tenants.utils import schema_context
from platform_context.tenant_utils.testing import tenant_a, tenant_b  # noqa: F401


@pytest.mark.django_db(transaction=True)
def test_model_data_is_isolated(tenant_a, tenant_b):
    """KRITISCH: Daten aus Mandant A dürfen in Mandant B nicht sichtbar sein."""
    from apps.assessments.models import Assessment

    # Daten in Mandant A anlegen
    with schema_context(tenant_a.schema_name):
        Assessment.objects.create(title="Vertraulich — nur Mandant A")
        assert Assessment.objects.count() == 1

    # In Mandant B: nichts davon sichtbar
    with schema_context(tenant_b.schema_name):
        assert Assessment.objects.count() == 0
        assert not Assessment.objects.filter(title__contains="Mandant A").exists()


@pytest.mark.django_db(transaction=True)
def test_api_endpoint_does_not_leak(tenant_a_client, tenant_b, tenant_a):
    """API-Endpoint liefert keine Daten eines fremden Mandanten."""
    from django_tenants.utils import schema_context
    from apps.assessments.models import Assessment

    with schema_context(tenant_a.schema_name):
        Assessment.objects.create(title="Geheim A")

    # Client von Mandant A kann nicht auf Mandant-B-Endpoint zugreifen
    # (tenant_a_client ist bereits im Context von tenant_a)
    response = tenant_a_client.get("/api/assessments/")
    assert response.status_code == 200
    titles = [a["title"] for a in response.json()]
    assert "Geheim A" in titles

    # Mandant B sieht nichts
    from django_tenants.test.client import TenantClient
    client_b = TenantClient(tenant_b)
    response_b = client_b.get("/api/assessments/")
    assert response_b.status_code == 200
    assert response_b.json() == []


@pytest.mark.django_db(transaction=True)
def test_public_schema_is_shared(tenant_a, tenant_b):
    """Public-Schema-Daten (z.B. Tenant-Registry) sind für alle sichtbar."""
    from tenants.models import Client
    # Beide Tenants sind im public-Schema sichtbar
    with schema_context("public"):
        assert Client.objects.filter(schema_name="test_tenant_a").exists()
        assert Client.objects.filter(schema_name="test_tenant_b").exists()
```

### 4.3 Layer 2: Propagation Tests (Pflicht-Gate)

#### 2a: REST-API Tenant-Header-Propagation

```python
# apps/core/tests/test_tenant_propagation.py
import pytest
from unittest.mock import patch, MagicMock
from platform_context.tenant_utils.http_client import TenantAwareHttpClient
from django_tenants.utils import schema_context


@pytest.mark.django_db(transaction=True)
def test_http_client_sends_tenant_header(tenant_a):
    """TenantAwareHttpClient fügt X-Tenant-Schema-Header hinzu."""
    with schema_context(tenant_a.schema_name):
        client = TenantAwareHttpClient("http://other-service:8000")
        headers = client._headers()
        assert headers["X-Tenant-Schema"] == tenant_a.schema_name


@pytest.mark.django_db(transaction=True)
def test_incoming_tenant_header_sets_schema(tenant_a, client):
    """Eingehender X-Tenant-Schema-Header setzt search_path korrekt."""
    from django.db import connection
    response = client.get(
        "/api/internal/ping/",
        HTTP_X_TENANT_SCHEMA=tenant_a.schema_name,
    )
    assert response.status_code == 200
    # Nach dem Request muss der search_path wieder auf public stehen
    # (Middleware-Cleanup verifizieren)
    assert connection.schema_name == "public"


def test_missing_tenant_header_falls_back_to_public(client):
    """Kein Tenant-Header → public-Schema (kein 500)."""
    response = client.get("/api/internal/ping/")
    assert response.status_code in (200, 404)  # Kein 500
```

#### 2b: Celery Tenant-Context-Propagation

```python
# apps/core/tests/test_celery_tenant_propagation.py
import pytest
from unittest.mock import patch
from django_tenants.utils import schema_context


@pytest.mark.django_db(transaction=True)
def test_celery_task_runs_in_correct_schema(tenant_a):
    """Celery-Task wird im richtigen Tenant-Schema ausgeführt."""
    from apps.core.tasks import sample_tenant_task
    from django.db import connection

    executed_in_schema = []

    def mock_task_body():
        executed_in_schema.append(connection.schema_name)

    with schema_context(tenant_a.schema_name):
        # tenant-schemas-celery serialisiert Schema automatisch
        with patch.object(sample_tenant_task, "run", side_effect=mock_task_body):
            sample_tenant_task.apply()  # Synchron via CELERY_TASK_ALWAYS_EAGER

    assert executed_in_schema == [tenant_a.schema_name]


@pytest.mark.django_db(transaction=True)
def test_cross_service_task_propagates_schema(tenant_a):
    """Cross-Service-Task übergibt _tenant_schema im Payload."""
    from platform_context.tenant_utils.celery import send_cross_service_task

    with schema_context(tenant_a.schema_name):
        with patch("celery.current_app.send_task") as mock_send:
            send_cross_service_task("other_service.tasks.do_work", data="test")
            call_kwargs = mock_send.call_args[1]["kwargs"]
            assert call_kwargs["_tenant_schema"] == tenant_a.schema_name
```

#### 2c: Health-Endpoint läuft im public-Schema

```python
# apps/core/tests/test_health_endpoints.py
import pytest


def test_livez_runs_in_public_schema(client):
    """/livez/ antwortet unabhängig vom Tenant-Context."""
    response = client.get("/livez/")
    assert response.status_code == 200


def test_healthz_runs_in_public_schema(client):
    """/healthz/ antwortet unabhängig vom Tenant-Context."""
    response = client.get("/healthz/")
    assert response.status_code == 200


def test_livez_with_tenant_subdomain(tenant_a_client):
    """/livez/ antwortet auch bei Tenant-Subdomain-Request."""
    response = tenant_a_client.get("/livez/")
    assert response.status_code == 200
```

### 4.4 Layer 3: Provisioning Tests

```python
# apps/tenants/tests/test_provisioning.py
import pytest
from django_tenants.utils import schema_context


@pytest.mark.django_db(transaction=True)
def test_new_tenant_schema_is_created():
    """Neuer Mandant erstellt automatisch ein DB-Schema."""
    from tenants.models import Client, Domain
    from django.db import connection

    tenant = Client(schema_name="test_new_corp", name="New Corp")
    tenant.save(verbosity=0)

    # Schema muss existieren
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
            ["test_new_corp"],
        )
        assert cursor.fetchone() is not None

    # Cleanup
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_new_corp CASCADE")


@pytest.mark.django_db(transaction=True)
def test_tenant_deletion_removes_all_data(tenant_a):
    """DROP SCHEMA entfernt alle Mandantendaten vollständig."""
    from apps.assessments.models import Assessment
    from django.db import connection

    with schema_context(tenant_a.schema_name):
        Assessment.objects.create(title="Wird gelöscht")
        assert Assessment.objects.count() == 1

    # Schema droppen (Art. 17 DSGVO)
    with connection.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA {tenant_a.schema_name} CASCADE")

    # Schema existiert nicht mehr
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name = %s",
            [tenant_a.schema_name],
        )
        assert cursor.fetchone() is None


@pytest.mark.django_db(transaction=True)
def test_tenant_provisioning_is_idempotent():
    """Doppelte Provisionierung desselben Mandanten schlägt sauber fehl."""
    from tenants.models import Client
    from django.db import IntegrityError

    Client(schema_name="test_idempotent", name="Idempotent Corp").save(verbosity=0)

    with pytest.raises((IntegrityError, Exception)):
        Client(schema_name="test_idempotent", name="Duplicate").save(verbosity=0)

    # Cleanup
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS test_idempotent CASCADE")
```

### 4.5 CI-Gate-Konfiguration

```yaml
# .github/workflows/ci.yml (Ergänzung für jeden SaaS-Service)
- name: Run Tenant Isolation Tests (CI Gate)
  run: |
    pytest apps/*/tests/test_tenant_isolation.py \
           apps/*/tests/test_tenant_propagation.py \
           apps/tenants/tests/test_provisioning.py \
           --tb=short -q
  env:
    DJANGO_SETTINGS_MODULE: config.settings.test
  # Schlägt fehl → Merge blockiert (branch protection rule)
```

```python
# pyproject.toml — Tenant-Tests als eigene Marker-Gruppe
[tool.pytest.ini_options]
markers = [
    "tenant_isolation: Kritische Isolation-Tests — CI-Gate",
    "tenant_propagation: Context-Propagation über REST/Celery/DB",
    "tenant_provisioning: Mandant-Anlage und -Löschung",
]
```

### 4.6 Anti-Patterns und Linter-Checks

**Verbotene Patterns nach Migration** (werden per `ruff`/`grep` im CI geprüft):

```python
# VERBOTEN in TENANT_APPS nach Migration:
Model.objects.filter(tenant_id=...)      # Row-Level-Filter obsolet
Model.objects.filter(organization=...)   # ADR-035-Pattern obsolet
connection.set_schema_to_public()        # Direkter Schema-Wechsel außerhalb von schema_context()

# ERLAUBT:
Model.objects.all()                      # Automatisch im richtigen Schema
Model.objects.filter(status="active")   # Fachliche Filter ohne Tenant-Bezug
with schema_context("public"): ...      # Expliziter public-Schema-Zugriff
```

```yaml
# .github/workflows/ci.yml — Anti-Pattern-Check
- name: Check for forbidden tenant patterns
  run: |
    # Schlägt fehl wenn verbotene Patterns in TENANT_APPS gefunden werden
    ! grep -rn "filter(tenant_id=" apps/ --include="*.py" \
      --exclude-dir=migrations --exclude-dir=tests \
      | grep -v "# legacy"
```

---

## 5. Migration Tracking — Test-Abdeckung pro Service

| Item | Status | Datum | Notizen |
|------|--------|-------|--------|
| `platform_context/tenant_utils/testing.py` — Fixtures (tenant_a/b, clients) | ✅ done | 2026-02-24 | Schema-Teardown ergänzt (ADR-074) |
| `platform_context/tenant_utils/testing.py` — Import-Fix (Any oben) | ✅ done | 2026-02-24 | War am Ende der Datei |

### Service-Tests

| Service | Layer 1 (Isolation) | Layer 2 (Propagation) | Layer 3 (Provisioning) | CI-Gate |
|---------|--------------------|-----------------------|------------------------|---------|
| `cad-hub` | ✅ done 2026-02-24 | ✅ done 2026-02-24 | ⬜ Ausstehend | ⬜ |
| `travel-beat` | ✅ done (existiert) | ✅ done (existiert) | ⬜ Ausstehend | ⬜ |
| `risk-hub` | ✅ done 2026-02-24 | ✅ done 2026-02-24 | ⬜ Ausstehend | ⬜ |
| `bfagent` | ✅ done 2026-02-24 | ✅ done 2026-02-24 | ⬜ Ausstehend | ⬜ |

**Test-Dateien:**
- `cad-hub/tests/test_tenant_isolation.py` — ConstructionProject isolation via TenantAwareManager
- `travel-beat/apps/tenants/tests/test_tenant_isolation.py` — bereits vorhanden (django-tenants Schema-Isolation)
- `risk-hub/src/tests/test_tenant_isolation.py` — Organization/Site/ApiKey isolation via tenant_id
- `bfagent/apps/core/tests/test_tenant_isolation.py` — TenantPromptOverride isolation via tenant_id

---

## 6. Risiken

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|-----------|
| `transaction=True` verlangsamt CI erheblich | Mittel | Mittel | Isolation-Tests in eigene Stage auslagern; parallelisieren mit `pytest-xdist -n 2` |
| Silent Failure: Test läuft im falschen Schema | Hoch | Kritisch | Pflicht-Assertion: `assert connection.schema_name == expected_schema` am Anfang jedes Isolation-Tests |
| Fixture-Cleanup schlägt fehl → Schema-Leak zwischen Tests | Mittel | Mittel | `yield`-Fixtures mit explizitem `DROP SCHEMA IF EXISTS` im Teardown |
| `django-tenants` `TenantTestCase` inkompatibel mit `pytest-django` | Niedrig | Hoch | `schema_context()` + `@pytest.mark.django_db(transaction=True)` statt `TenantTestCase` |
| Cross-Service-Propagation-Tests brauchen laufende Services | Mittel | Mittel | Mock-basierte Tests für Unit-Level; Integration-Tests als separater Stage |

---

## 7. Konsequenzen

### 7.1 Good

- **DSGVO-Compliance verifizierbar**: Isolation-Tests sind maschinenlesbare Evidenz für Datenschutz-Audits
- **CI-Gate blockiert Regressions**: Datenleck-Bugs werden vor Merge erkannt
- **Shared Fixtures**: Einmal in `platform_context` schreiben, in allen Services nutzen
- **Klare Anti-Pattern-Erkennung**: Linter-Check verhindert Rückfall auf Row-Level-Filter

### 7.2 Bad

- **`transaction=True` ist langsamer**: Isolation-Tests dauern 3–5× länger als normale Tests
- **Schema-Cleanup-Overhead**: Jeder Test-Run erstellt und droppt Schemas — DB-Overhead
- **Komplexere Fixtures**: `schema_context` muss explizit gesetzt werden — kein automatisches Django-Test-Rollback

### 7.3 Nicht in Scope

- Performance-Tests / Load-Tests (ADR-056 §6, Phase 4)
- End-to-End-Tests mit echten Subdomains (Selenium/Playwright) — separates ADR
- Contract-Tests zwischen Services — separates ADR

---

## 8. Confirmation

Compliance wird wie folgt verifiziert:

1. **Pflicht-Datei**: Jeder SaaS-Service muss `apps/*/tests/test_tenant_isolation.py` enthalten — CI schlägt fehl wenn Datei fehlt
2. **CI-Gate**: `pytest -m tenant_isolation` läuft in eigenem Step, blockiert Merge bei Fehler
3. **Anti-Pattern-Check**: `grep`-basierter Linter-Check auf verbotene `filter(tenant_id=...)` in `TENANT_APPS`
4. **Migration-Tracking-Tabelle** (§5) wird bei jedem Service-Rollout aktualisiert

---

## 9. More Information

- [django-tenants Test-Dokumentation](https://django-tenants.readthedocs.io/en/latest/test.html)
- [pytest-django `transaction=True`](https://pytest-django.readthedocs.io/en/latest/database.html#transaction-tests)
- ADR-056: Adopt PostgreSQL Schema Isolation for SaaS Multi-Tenancy
- ADR-035: Shared Django Tenancy Package

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-21 | Achim Dehnert | Initial: Status Proposed |
