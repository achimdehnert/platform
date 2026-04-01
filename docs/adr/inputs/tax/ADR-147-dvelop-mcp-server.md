---
status: "proposed"
date: 2026-03-25
decision-makers: [Achim Dehnert]
consulted: []
informed: []
supersedes: []
amends: []
related:
  - ADR-044  # MCP-Hub Architecture Consolidation (FastMCP-Standard)
  - ADR-146  # risk-hub → DMS Audit Trail (DvelopDmsClient Quelle)
  - ADR-149  # Inbound Scan (Phase 1 — Gate für dieses ADR)
  - ADR-150  # DMS Rollout-Plan (Phase 2)
staleness_months: 6
drift_check_paths:
  - mcp-hub/dvelop_mcp/
---

# ADR-147: Adopt FastMCP dvelop_mcp Server als agentic DMS-Zugriffsschicht

## Metadaten

| Attribut       | Wert                                                              |
|----------------|-------------------------------------------------------------------|
| **Status**     | Proposed                                                          |
| **Scope**      | mcp-hub                                                           |
| **Erstellt**   | 2026-03-25                                                        |
| **Autor**      | Achim Dehnert                                                     |
| **Relates to** | ADR-044, ADR-146, ADR-149, ADR-150                                |

## Repo-Zugehörigkeit

| Repo      | Rolle    | Betroffene Pfade                            |
|-----------|----------|---------------------------------------------|
| `mcp-hub` | Primär   | `dvelop_mcp/` (neu)                         |
| `dms-hub` | Sekundär | `dms_hub/client/dvelop_client.py` (Quelle)  |
| `platform`| Referenz | `docs/adr/`                                 |

---

## Decision Drivers

- **ADR-150 Phase 2**: Sobald Phase 1 (Inbound Scan) produktiv ist, braucht
  Cascade/Windsurf Lesezugriff auf die archivierten Dokumente.
- **DvelopDmsClient existiert**: Der HTTP-Client aus ADR-146 implementiert bereits
  `search`, `upload`, `download`, `list_repositories` — der MCP-Server ist ein
  dünner Wrapper, kein neuer Client.
- **FastMCP-Standard**: ADR-044 schreibt FastMCP als einzigen MCP-Protokollstack vor.
  Kein Raw MCP SDK, kein eigener Main-Loop.
- **Aufwand < 1 Tag**: Vier Tools, synchrone Wrapper, keine neue Infrastruktur.

---

## 1. Context and Problem Statement

### 1.1 Ist-Zustand nach Phase 1

Nach Abschluss von ADR-149 (Inbound Scan) liegen Behördendokumente in
`https://iil.d-velop.cloud`. Cascade kann darauf nur über manuelle REST-Calls
zugreifen — kein strukturierter Tool-Zugriff, keine Tool-Beschreibungen,
kein Fehlerhandling für den Agenten.

### 1.2 Ziel

Ein FastMCP-Server `dvelop_mcp` in `mcp-hub`, der Cascade vier Tools bereitstellt:
Suche, Dokument-Abruf, Upload und Kategorie-Listing. Der Server läuft lokal in
Windsurf (stdio) und leitet Calls an `https://iil.d-velop.cloud` weiter.

```
Windsurf/Cascade
    │  MCP stdio
    ▼
dvelop_mcp (FastMCP, lokal)
    │  httpx REST
    ▼
d.velop Cloud
https://iil.d-velop.cloud
```

---

## 2. Considered Options

### Option A — FastMCP-Server in mcp-hub (gewählt) ✅

Neuer Server `dvelop_mcp/` nach ADR-044-Template. Nutzt
`DvelopDmsClient` direkt (via `pip install -e` oder Copy).

**Pro:**
- Konsistent mit ADR-044-Template (`travel_mcp`, `illustration_mcp`)
- DvelopDmsClient bereits vollständig getestet (ADR-146)
- Kein neuer HTTP-Client nötig

**Con:**
- `DvelopDmsClient` muss aus `dms-hub` extrahiert oder kopiert werden

### Option B — dms-hub API-Endpunkt + MCP-Proxy

MCP-Server ruft internen dms-hub REST-Endpunkt auf statt direkt d.velop.

**Abgelehnt**: Zusätzlicher Netzwerkhop ohne Mehrwert. dms-hub läuft auf
Hetzner, MCP-Server läuft lokal in Windsurf — unnötige Latenz und
Abhängigkeit vom Hetzner-Netz bei lokaler Entwicklung.

### Option C — Raw MCP SDK

Direkte Implementierung ohne FastMCP.

**Abgelehnt**: Verstößt gegen ADR-044. ~100 Zeilen Boilerplate ohne Nutzen.

---

## 3. Decision Outcome

**Gewählt: Option A.**

`DvelopDmsClient` wird als `dvelop_mcp/client.py` kopiert und leicht
vereinfacht (nur die 4 benötigten Methoden). Kein Package-Import aus
`dms-hub` — die beiden Repos sind unabhängig deploybar.

---

## 4. Implementation — Schritte

### Schritt 1 — Verzeichnisstruktur anlegen

```
mcp-hub/dvelop_mcp/
├── src/dvelop_mcp/
│   ├── __init__.py          # __version__ = "0.1.0"
│   ├── __main__.py          # mcp.run() Einstiegspunkt
│   ├── server.py            # FastMCP-Instanz + 4 Tools
│   ├── client.py            # DvelopDmsClient (vereinfacht aus ADR-146)
│   └── settings.py          # pydantic-settings
├── tests/
│   ├── conftest.py
│   └── test_tools.py        # respx-gemockte Tests
└── pyproject.toml
```

---

### Schritt 2 — `settings.py`

```python
# src/dvelop_mcp/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DVELOP_")

    base_url: str = "https://iil.d-velop.cloud"
    api_key: str                    # DVELOP_API_KEY — Pflicht
    default_repo_id: str = ""       # DVELOP_DEFAULT_REPO_ID
    timeout: float = 30.0


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

---

### Schritt 3 — `client.py` (vereinfacht aus ADR-146)

Nur die vier benötigten Methoden — kein Upload-Blob-Split, kein Retry
(FastMCP-Layer übernimmt Error-Handling):

```python
# src/dvelop_mcp/client.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import httpx


@dataclass
class DmsDoc:
    id: str
    category: str
    filename: str
    properties: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_hal(cls, data: dict) -> "DmsDoc":
        props = {p["key"]: p["value"] for p in data.get("sourceProperties", [])}
        return cls(
            id=data.get("id", ""),
            category=data.get("sourceCategory", ""),
            filename=data.get("displayName", ""),
            properties=props,
        )


class DvelopClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 30.0):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/hal+json",
                "Origin": base_url.rstrip("/"),  # CSRF-Pflicht
            },
            timeout=timeout,
            follow_redirects=True,
        )

    # ── 1. Repositories ──────────────────────────────────────────
    def list_repositories(self) -> list[dict]:
        r = self._client.get("/dms/r")
        r.raise_for_status()
        return r.json().get("repositories", [])

    # ── 2. Suche ─────────────────────────────────────────────────
    def search(
        self,
        repo_id: str,
        fulltext: str | None = None,
        category_ids: list[str] | None = None,
        page_size: int = 20,
    ) -> list[DmsDoc]:
        import json
        params: dict[str, Any] = {"pagesize": page_size}
        if fulltext:
            params["fulltext"] = fulltext
        if category_ids:
            params["objectdefinitionids"] = json.dumps(category_ids)
        r = self._client.get(f"/dms/r/{repo_id}/o2m", params=params)
        r.raise_for_status()
        return [DmsDoc.from_hal(i) for i in r.json().get("items", [])]

    # ── 3. Dokument-Metadaten ─────────────────────────────────────
    def get_document(self, repo_id: str, doc_id: str) -> DmsDoc:
        r = self._client.get(f"/dms/r/{repo_id}/o/{doc_id}")
        r.raise_for_status()
        return DmsDoc.from_hal(r.json())

    # ── 4. Upload (2-Step: Blob → Object) ────────────────────────
    def upload(
        self,
        repo_id: str,
        filename: str,
        content: bytes,
        category: str,
        properties: dict[str, str],
        content_type: str = "application/pdf",
    ) -> str:
        # Step 1: Blob
        r1 = self._client.post(
            f"/dms/r/{repo_id}/b",
            content=content,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
        r1.raise_for_status()
        blob_id = r1.headers["Location"].split("/")[-1]

        # Step 2: DMS-Objekt
        r2 = self._client.post(
            f"/dms/r/{repo_id}/o",
            json={
                "sourceCategory": category,
                "sourceProperties": [
                    {"key": k, "value": v} for k, v in properties.items()
                ],
                "contentLocationUri": f"/dms/r/{repo_id}/b/{blob_id}",
            },
        )
        r2.raise_for_status()
        return r2.headers["Location"].split("/")[-1]

    def close(self) -> None:
        self._client.close()
```

---

### Schritt 4 — `server.py` — 4 Tools

```python
# src/dvelop_mcp/server.py
from __future__ import annotations
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP
from asgiref.sync import async_to_sync   # ADR-Plattformregel: kein asyncio.run()

from .client import DvelopClient
from .settings import get_settings

logger = logging.getLogger(__name__)


# ── Lifespan: Client einmal initialisieren, sauber schließen ─────

@asynccontextmanager
async def lifespan(server: FastMCP):
    cfg = get_settings()
    server.state["client"] = DvelopClient(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=cfg.timeout,
    )
    try:
        yield
    finally:
        server.state["client"].close()


mcp = FastMCP(name="dvelop-mcp", lifespan=lifespan)


def _client() -> DvelopClient:
    return mcp.state["client"]


def _repo(repo_id: str | None) -> str:
    rid = repo_id or get_settings().default_repo_id
    if not rid:
        raise ValueError(
            "repo_id fehlt. Entweder als Parameter übergeben "
            "oder DVELOP_DEFAULT_REPO_ID setzen."
        )
    return rid


# ── Tool 1: Suche ─────────────────────────────────────────────────

@mcp.tool()
def dvelop_search(
    query: str,
    repo_id: str | None = None,
    category: str | None = None,
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """
    Volltext-Suche im d.velop DMS.

    Args:
        query:       Suchbegriff (z.B. "Bebauungsplan 2024")
        repo_id:     Repository-ID (optional, nutzt Default aus Settings)
        category:    d.velop Kategorie-ID zum Einschränken (optional)
        max_results: Maximale Trefferzahl (Standard 20)

    Returns:
        Liste von Dokumenten mit id, category, filename, properties
    """
    try:
        docs = _client().search(
            _repo(repo_id),
            fulltext=query,
            category_ids=[category] if category else None,
            page_size=min(max_results, 50),
        )
        return [
            {"id": d.id, "category": d.category,
             "filename": d.filename, "properties": d.properties}
            for d in docs
        ]
    except Exception as e:
        logger.exception("dvelop_search failed")
        return [{"error": "Suche fehlgeschlagen", "detail": str(e)}]


# ── Tool 2: Dokument-Metadaten abrufen ────────────────────────────

@mcp.tool()
def dvelop_get_document(
    doc_id: str,
    repo_id: str | None = None,
) -> dict[str, Any]:
    """
    Metadaten eines einzelnen DMS-Dokuments abrufen.

    Args:
        doc_id:  d.velop Dokument-ID (aus dvelop_search)
        repo_id: Repository-ID (optional)

    Returns:
        Dokument-Metadaten: id, category, filename, properties
    """
    try:
        doc = _client().get_document(_repo(repo_id), doc_id)
        return {
            "id": doc.id,
            "category": doc.category,
            "filename": doc.filename,
            "properties": doc.properties,
        }
    except Exception as e:
        logger.exception("dvelop_get_document failed")
        return {"error": "Dokument nicht gefunden", "detail": str(e)}


# ── Tool 3: Dokument hochladen ────────────────────────────────────

@mcp.tool()
def dvelop_upload(
    filename: str,
    content_base64: str,
    category: str,
    properties: dict[str, str],
    repo_id: str | None = None,
) -> dict[str, str]:
    """
    Dokument ins d.velop DMS hochladen.

    Args:
        filename:       Dateiname inkl. Endung (z.B. "bescheid_2024.pdf")
        content_base64: Dateiinhalt als Base64-kodierter String
        category:       d.velop Kategorie-ID (z.B. "INBOUND_BESCHEID")
        properties:     Metadaten als Dict (z.B. {"Aktenzeichen": "2024-001"})
        repo_id:        Repository-ID (optional)

    Returns:
        {"doc_id": "<d.velop Dokument-ID>"} bei Erfolg
        {"error": "...", "detail": "..."} bei Fehler
    """
    import base64
    try:
        content = base64.b64decode(content_base64)
        doc_id = _client().upload(
            _repo(repo_id),
            filename=filename,
            content=content,
            category=category,
            properties=properties,
        )
        return {"doc_id": doc_id}
    except Exception as e:
        logger.exception("dvelop_upload failed")
        return {"error": "Upload fehlgeschlagen", "detail": str(e)}


# ── Tool 4: Verfügbare Repositories auflisten ─────────────────────

@mcp.tool()
def dvelop_list_repositories() -> list[dict[str, str]]:
    """
    Alle verfügbaren d.velop-Repositories auflisten.
    Nützlich um die repo_id für andere Tools zu ermitteln.

    Returns:
        Liste mit {"id": "...", "name": "..."} pro Repository
    """
    try:
        repos = _client().list_repositories()
        return [{"id": r.get("id", ""), "name": r.get("name", "")} for r in repos]
    except Exception as e:
        logger.exception("dvelop_list_repositories failed")
        return [{"error": "Repositories nicht abrufbar", "detail": str(e)}]
```

---

### Schritt 5 — `__main__.py` und `pyproject.toml`

```python
# src/dvelop_mcp/__main__.py
from .server import mcp

if __name__ == "__main__":
    mcp.run()
```

```toml
# pyproject.toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "dvelop-mcp"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.27",
    "pydantic-settings>=2.0",
    "asgiref>=3.8",
]

[project.scripts]
dvelop-mcp = "dvelop_mcp.__main__:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

### Schritt 6 — Tests (`tests/test_tools.py`)

```python
# tests/test_tools.py
import pytest
import respx
import httpx
from dvelop_mcp.server import dvelop_search, dvelop_list_repositories, mcp
from dvelop_mcp.client import DvelopClient
from dvelop_mcp.settings import Settings


BASE = "https://iil.d-velop.cloud"
REPO = "test-repo-id"


@pytest.fixture(autouse=True)
def inject_client(monkeypatch):
    """Inject Mock-Client in server.state."""
    cfg = Settings(base_url=BASE, api_key="test-key", default_repo_id=REPO)
    monkeypatch.setattr("dvelop_mcp.server.get_settings", lambda: cfg)
    client = DvelopClient(base_url=BASE, api_key="test-key")
    mcp.state["client"] = client
    yield
    client.close()


@respx.mock
def test_dvelop_search_returns_documents():
    respx.get(f"{BASE}/dms/r/{REPO}/o2m").mock(
        return_value=httpx.Response(200, json={
            "items": [
                {
                    "id": "doc-001",
                    "sourceCategory": "INBOUND_BESCHEID",
                    "displayName": "bescheid_2024.pdf",
                    "sourceProperties": [{"key": "Aktenzeichen", "value": "2024-001"}],
                }
            ],
            "itemsCount": 1,
        })
    )
    result = dvelop_search(query="Bescheid", repo_id=REPO)
    assert len(result) == 1
    assert result[0]["id"] == "doc-001"
    assert result[0]["filename"] == "bescheid_2024.pdf"


@respx.mock
def test_dvelop_search_returns_error_on_failure():
    respx.get(f"{BASE}/dms/r/{REPO}/o2m").mock(
        return_value=httpx.Response(500)
    )
    result = dvelop_search(query="anything", repo_id=REPO)
    assert result[0].get("error") is not None


@respx.mock
def test_dvelop_list_repositories():
    respx.get(f"{BASE}/dms/r").mock(
        return_value=httpx.Response(200, json={
            "repositories": [{"id": REPO, "name": "Landratsamt DMS"}]
        })
    )
    result = dvelop_list_repositories()
    assert result[0]["id"] == REPO
    assert result[0]["name"] == "Landratsamt DMS"
```

---

### Schritt 7 — Windsurf `mcp_servers.json` Eintrag

```json
{
  "mcpServers": {
    "dvelop": {
      "command": "python",
      "args": ["-m", "dvelop_mcp"],
      "cwd": "/path/to/mcp-hub/dvelop_mcp",
      "env": {
        "DVELOP_API_KEY": "<key-aus-read_secret>",
        "DVELOP_DEFAULT_REPO_ID": "<repo-id-aus-dvelop_list_repositories>"
      }
    }
  }
}
```

**Reihenfolge beim Einrichten**:

```bash
# 1. Installieren
cd mcp-hub/dvelop_mcp && pip install -e .

# 2. Repo-ID ermitteln (einmalig)
DVELOP_API_KEY=<key> python -c "
from dvelop_mcp.client import DvelopClient
c = DvelopClient('https://iil.d-velop.cloud', '<key>')
print(c.list_repositories())
c.close()
"
# → [{'id': 'dee1f3d3-...', 'name': 'Landratsamt'}]

# 3. Repo-ID in mcp_servers.json eintragen
# 4. Windsurf neu starten → dvelop-Tools in Cascade verfügbar
```

---

## 5. Migration Tracking

| Schritt | Status | Datum | Notiz |
|---------|--------|-------|-------|
| ADR-147 erstellt | ✅ Done | 2026-03-25 | |
| ADR-147 Review | ⬜ Pending | – | Gate: Phase 1 (ADR-149) Done |
| Verzeichnis + pyproject.toml | ⬜ Pending | – | Schritt 1 |
| settings.py + client.py | ⬜ Pending | – | Schritte 2–3 |
| server.py (4 Tools) | ⬜ Pending | – | Schritt 4 |
| Tests grün | ⬜ Pending | – | Schritt 6 |
| Windsurf verbunden | ⬜ Pending | – | Schritt 7 |
| Cascade findet Phase-1-Dokument via `dvelop_search` | ⬜ Pending | – | **Done-Kriterium** |

---

## 6. Consequences

### 6.1 Good

- Cascade kann DMS-Dokumente suchen, abrufen und ablegen ohne manuelle REST-Calls
- Konform mit ADR-044 (FastMCP, Lifespan, Error-Sanitisierung)
- `DvelopDmsClient`-Logik wird nicht dupliziert — gleiche Implementierung
  wie in `dms-hub`, nur vereinfacht auf 4 Methoden
- Kein `asyncio.run()` (Tools sind synchron, kein ASGI-Kontext-Problem)

### 6.2 Bad

- `client.py` ist eine Kopie aus ADR-146, kein gemeinsames Package.
  Bei API-Änderungen müssen zwei Stellen gepflegt werden.
- Upload via Base64 ist für große Dateien (> 10 MB) unhandlich —
  Cascade-Uploads sind aber typischerweise kleine PDFs.

### 6.3 Nicht in Scope

- Download von Datei-Inhalten (nur Metadaten via `dvelop_get_document`)
- Webhook-Empfang im MCP-Server
- Authentifizierung per OAuth2 (bleibt Bearer-Token)

---

## 7. Risks

| Risiko | W'keit | Impact | Mitigation |
|--------|--------|--------|------------|
| API-Key im Klartext in `mcp_servers.json` | Mittel | Hoch | Key via Env-Var, niemals in versionierten Dateien |
| d.velop-Ausfall blockiert Cascade | Niedrig | Mittel | Error-Return statt Exception — Cascade bekommt strukturierte Fehlermeldung |
| `client.py`-Drift zu `dms-hub` | Niedrig | Niedrig | Bei Breaking Change: Update in beiden Repos, ADR-Drift-Detector meldet |

---

## 8. Confirmation

1. `pytest tests/ -v` — alle Tests grün, kein echter Netzwerkaufruf
2. `dvelop_list_repositories()` gibt Landratsamt-Repository zurück
3. `dvelop_search("Bebauungsplan")` findet ≥ 1 Dokument aus Phase 1
4. Cascade-Prompt `"Suche im DMS nach Bebauungsplänen"` → Tool-Call sichtbar in Windsurf
5. `DVELOP_API_KEY` nur via Env-Var — kein Klartext in `mcp_servers.json` im Repo
6. Drift-Detector: dieses ADR wird alle 6 Monate geprüft

---

## 9. More Information

| Referenz | Inhalt |
|----------|--------|
| ADR-044 | FastMCP-Template, Lifespan-Pattern, Error-Sanitisierung |
| ADR-146 | `DvelopDmsClient` — Quell-Implementierung (vollständig, mit Retry) |
| ADR-149 | Phase 1 Gate — muss done sein bevor dieser ADR implementiert wird |
| ADR-150 | Roadmap-Kontext: Phase 2 von 5 |

---

*Erstellt: 2026-03-25 · Autor: Achim Dehnert · Review: ausstehend*
