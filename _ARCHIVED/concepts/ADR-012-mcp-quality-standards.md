# ADR-012: MCP Server Quality Standards

| Metadata | Value |
|----------|-------|
| **Status** | Proposed |
| **Date** | 2026-02-03 |
| **Author** | Achim Dehnert |
| **Scope** | core |
| **Reviewers** | — |
| **Supersedes** | — |
| **Related** | ADR-009 (Deployment Architecture), ADR-011 (Centralized ADR Management) |

---

## 1. Executive Summary

Dieses ADR etabliert **verbindliche Qualitätsstandards** für alle MCP Server im MCP-Hub. Es definiert eine Scorecard-Methodik zur objektiven Bewertung, automatisierte CI/CD-Checks, und eine gemeinsame Base Library (`mcp-core`) zur Reduzierung von Boilerplate und Sicherstellung konsistenter Qualität.

**Kernprinzip:** *"Jeder MCP Server muss production-ready sein, bevor er deployed wird."*

---

## 2. Context

### 2.1 Aktuelle Situation

Der MCP-Hub enthält 14+ MCP Server mit unterschiedlichen Reifegraden:

| Server | Status | Maintainer | Letzte Änderung |
|--------|--------|------------|-----------------|
| `llm_mcp` | ✅ Production | Team | Aktiv |
| `bfagent_mcp` | ✅ Production | Team | Aktiv |
| `deployment_mcp` | ✅ Production | Team | Aktiv |
| `research_mcp` | ✅ Production | Team | Aktiv |
| `travel_mcp` | ✅ Production | Team | Aktiv |
| `illustration_mcp` | ✅ Production | Team | Aktiv |
| `book_writing_mcp` | ✅ Production | Team | Aktiv |
| `bfagent_sqlite_mcp` | ✅ Production | Team | Aktiv |
| `german_tax_mcp` | 🔧 Beta | Team | Sporadisch |
| `ifc_mcp` | 🔧 Beta | Team | Sporadisch |
| `cad_mcp` | 🔧 Beta | Team | Sporadisch |
| `dlm_mcp` | 🔧 Beta | Team | Sporadisch |
| `physicals_mcp` | 🔧 Beta | Team | Sporadisch |

### 2.2 Identifizierte Probleme

| Problem | Impact | Häufigkeit |
|---------|--------|------------|
| **Inkonsistente Error Handling** | Unvorhersehbare Fehler für AI-Clients | Hoch |
| **Fehlende Input-Validierung** | Security-Risiken, Crashes | Hoch |
| **Unzureichende Dokumentation** | Schwere Nutzbarkeit | Mittel |
| **Keine Test-Coverage** | Regressions unbemerkt | Hoch |
| **Duplizierter Boilerplate** | Wartungsaufwand | Mittel |
| **Inkonsistente Logging** | Schweres Debugging | Mittel |
| **Keine Metrics** | Blind für Performance-Issues | Niedrig |

### 2.3 MCP Best Practices (Stand 2025/2026)

Basierend auf der offiziellen MCP-Spezifikation und Community-Best-Practices:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER QUALITY PYRAMID                            │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                           ┌─────────────┐                                │
│                           │  Excellent  │  Observability, Auto-Healing   │
│                           │   (90+)     │  Performance Optimization      │
│                         ┌─┴─────────────┴─┐                              │
│                         │      Good       │  Comprehensive Tests         │
│                         │    (75-89)      │  Full Documentation          │
│                       ┌─┴─────────────────┴─┐                            │
│                       │     Acceptable      │  Basic Tests               │
│                       │      (60-74)        │  Error Handling            │
│                     ┌─┴─────────────────────┴─┐                          │
│                     │       Minimum           │  Type Hints, Docstrings  │
│                     │       (50-59)           │  Input Validation        │
│                   ┌─┴─────────────────────────┴─┐                        │
│                   │          Below Standard      │  ❌ NOT DEPLOYABLE    │
│                   │            (<50)             │                        │
│                   └─────────────────────────────┘                        │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 2.4 Anforderungen

| ID | Anforderung | Priorität | Quelle |
|----|-------------|-----------|--------|
| R1 | Einheitliche Qualitätsbewertung | CRITICAL | Ops |
| R2 | Automatisierte Quality Gates | CRITICAL | DevOps |
| R3 | Reduzierung von Boilerplate | HIGH | Dev |
| R4 | Klare Mindeststandards | HIGH | Team |
| R5 | Einfache Compliance-Prüfung | MEDIUM | QA |
| R6 | Messbare Verbesserung | MEDIUM | Management |

---

## 3. Decision

### 3.1 Drei-Säulen-Architektur

Wir führen ein **Drei-Säulen-Qualitätssystem** ein:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    MCP QUALITY FRAMEWORK                                 │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────┐ │
│  │                    │  │                    │  │                    │ │
│  │   📊 SCORECARD     │  │   🤖 AUTOMATION    │  │   📦 MCP-CORE      │ │
│  │                    │  │                    │  │                    │ │
│  │  Objektive         │  │  CI/CD Quality     │  │  Shared Base       │ │
│  │  Bewertung         │  │  Gates             │  │  Library           │ │
│  │                    │  │                    │  │                    │ │
│  │  • 7 Kategorien    │  │  • Pre-Commit      │  │  • Error Handling  │ │
│  │  • Gewichtung      │  │  • PR Checks       │  │  • Validation      │ │
│  │  • Grade A-F       │  │  • Release Gates   │  │  • Logging         │ │
│  │  • Action Items    │  │  • Scheduled Scan  │  │  • Retry Logic     │ │
│  │                    │  │                    │  │  • Metrics         │ │
│  └────────────────────┘  └────────────────────┘  └────────────────────┘ │
│           │                       │                       │              │
│           └───────────────────────┴───────────────────────┘              │
│                                   │                                      │
│                                   ▼                                      │
│                    ┌──────────────────────────┐                          │
│                    │   PRODUCTION-READY MCP   │                          │
│                    │        SERVERS           │                          │
│                    └──────────────────────────┘                          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Säule 1: Quality Scorecard

### 4.1 Bewertungskategorien

| Kategorie | Gewicht | Beschreibung |
|-----------|---------|--------------|
| 🔧 **Tool Design** | 20% | Naming, Parameter, Docstrings, Semantik |
| 🛡️ **Error Handling** | 15% | Exception Handling, Graceful Degradation |
| 📝 **Documentation** | 15% | README, API-Docs, Beispiele, Changelog |
| 🧪 **Test Coverage** | 20% | Unit Tests, Integration Tests, E2E |
| 🔒 **Security** | 15% | Input Validation, Secrets, Rate Limiting |
| 📊 **Observability** | 10% | Logging, Metrics, Tracing |
| 🏗️ **Architecture** | 5% | Modularity, Dependencies, Code Quality |

### 4.2 Detaillierte Kriterien

#### 🔧 Tool Design (20%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Naming Convention** | 0-2 | `snake_case`, beschreibend, konsistent |
| **Parameter Design** | 0-2 | Sinnvolle Defaults, optionale Parameter |
| **Type Hints** | 0-2 | Vollständige Typisierung aller Parameter |
| **Docstrings** | 0-2 | Args, Returns, Raises dokumentiert |
| **Semantic Clarity** | 0-2 | Tool macht genau eine Sache |

```python
# ❌ Schlecht
@app.tool()
async def do_stuff(x, y=None):
    """Does stuff."""
    pass

# ✅ Gut
@app.tool()
async def search_documents(
    query: str,
    limit: int = 10,
    include_metadata: bool = False,
) -> str:
    """
    Search documents matching the query.
    
    Args:
        query: Search query string (min 3 chars)
        limit: Maximum results to return (1-100, default: 10)
        include_metadata: Include document metadata in results
    
    Returns:
        JSON string with search results:
        {
            "success": true,
            "results": [...],
            "total": 42
        }
    
    Raises:
        ValidationError: If query is too short or limit out of range
        ServiceError: If search backend is unavailable
    """
    pass
```

#### 🛡️ Error Handling (15%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Try/Catch Coverage** | 0-2 | Alle externen Calls abgesichert |
| **Error Classification** | 0-2 | Client vs Server vs External Errors |
| **Structured Responses** | 0-2 | Konsistentes Error-Format |
| **Graceful Degradation** | 0-2 | Fallbacks bei Partial Failures |
| **Error Logging** | 0-2 | Ausreichend Context für Debugging |

```python
# ✅ Strukturierte Error Response
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class ErrorCategory(Enum):
    CLIENT_ERROR = "client_error"      # 4xx - Benutzer-Fehler
    SERVER_ERROR = "server_error"      # 5xx - Unser Fehler
    EXTERNAL_ERROR = "external_error"  # Abhängigkeit nicht verfügbar

@dataclass
class MCPError:
    category: ErrorCategory
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None  # Sekunden bis Retry sinnvoll

@app.tool()
async def safe_tool(param: str) -> str:
    """Tool with proper error handling."""
    try:
        # Input validation
        if not param or len(param) < 3:
            return json.dumps({
                "success": False,
                "error": {
                    "category": "client_error",
                    "code": "INVALID_INPUT",
                    "message": "Parameter must be at least 3 characters",
                }
            })
        
        result = await external_service.call(param)
        return json.dumps({"success": True, "data": result})
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return json.dumps({
            "success": False,
            "error": {
                "category": "client_error",
                "code": "VALIDATION_ERROR",
                "message": str(e),
            }
        })
    except ExternalServiceError as e:
        logger.error(f"External service failed: {e}")
        return json.dumps({
            "success": False,
            "error": {
                "category": "external_error",
                "code": "SERVICE_UNAVAILABLE",
                "message": "External service temporarily unavailable",
                "retry_after": 60,
            }
        })
    except Exception as e:
        logger.exception(f"Unexpected error in safe_tool")
        return json.dumps({
            "success": False,
            "error": {
                "category": "server_error",
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
            }
        })
```

#### 📝 Documentation (15%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **README.md** | 0-2 | Installation, Config, Quick Start |
| **Tool Documentation** | 0-2 | Alle Tools mit Beispielen |
| **Configuration Guide** | 0-2 | Env Vars, Config Files erklärt |
| **Changelog** | 0-2 | CHANGELOG.md gepflegt |
| **Troubleshooting** | 0-2 | Common Issues dokumentiert |

```markdown
# ✅ Gute README Struktur

# Server Name MCP

Brief description of what this server does.

## Installation

```bash
pip install server-name-mcp
```

## Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | Yes | — | API key for service |
| `TIMEOUT` | No | 30 | Request timeout in seconds |

## Tools

### tool_name

Description of the tool.

**Parameters:**
- `param1` (str, required): Description
- `param2` (int, optional): Description (default: 10)

**Example:**
```python
result = await tool_name(param1="test", param2=5)
```

**Response:**
```json
{"success": true, "data": {...}}
```

## Troubleshooting

### Error: API_KEY not set
Solution: Set the API_KEY environment variable...
```

#### 🧪 Test Coverage (20%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Unit Tests** | 0-3 | Isolierte Tool-Tests |
| **Integration Tests** | 0-3 | MCP Protocol Tests |
| **Coverage %** | 0-2 | ≥80% = 2, ≥60% = 1, <60% = 0 |
| **Edge Cases** | 0-2 | Error Paths, Boundary Values |

```python
# ✅ Test-Struktur
# tests/
# ├── conftest.py          # Shared Fixtures
# ├── unit/
# │   ├── test_tools.py    # Tool Logic Tests
# │   └── test_utils.py    # Utility Tests
# ├── integration/
# │   └── test_mcp.py      # MCP Protocol Tests
# └── e2e/
#     └── test_client.py   # End-to-End Tests

# tests/unit/test_tools.py
import pytest
from my_mcp.server import search_documents

@pytest.mark.asyncio
async def test_search_documents_success():
    """Test successful search."""
    result = await search_documents(query="test", limit=5)
    data = json.loads(result)
    
    assert data["success"] is True
    assert "results" in data
    assert len(data["results"]) <= 5

@pytest.mark.asyncio
async def test_search_documents_invalid_query():
    """Test validation error for short query."""
    result = await search_documents(query="ab")  # Too short
    data = json.loads(result)
    
    assert data["success"] is False
    assert data["error"]["category"] == "client_error"
    assert data["error"]["code"] == "INVALID_INPUT"

@pytest.mark.asyncio
async def test_search_documents_service_unavailable(mocker):
    """Test graceful handling of service failure."""
    mocker.patch('my_mcp.service.search', side_effect=ServiceUnavailable())
    
    result = await search_documents(query="test")
    data = json.loads(result)
    
    assert data["success"] is False
    assert data["error"]["category"] == "external_error"
    assert "retry_after" in data["error"]

# tests/integration/test_mcp.py
@pytest.mark.asyncio
async def test_mcp_list_tools():
    """Test MCP protocol: list tools."""
    async with mcp_client("my-mcp") as client:
        tools = await client.list_tools()
        
        tool_names = [t.name for t in tools]
        assert "search_documents" in tool_names

@pytest.mark.asyncio
async def test_mcp_call_tool():
    """Test MCP protocol: call tool."""
    async with mcp_client("my-mcp") as client:
        result = await client.call_tool(
            "search_documents",
            {"query": "test"}
        )
        
        assert result is not None
        data = json.loads(result)
        assert data["success"] is True
```

#### 🔒 Security (15%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Input Validation** | 0-3 | Alle Inputs validiert |
| **Secrets Management** | 0-3 | Keine hardcoded Secrets |
| **Rate Limiting** | 0-2 | Schutz vor Abuse |
| **Output Sanitization** | 0-2 | Keine Sensitive Data in Responses |

```python
# ✅ Security Best Practices

from pydantic import BaseModel, Field, validator
import os

# 1. Input Validation mit Pydantic
class SearchParams(BaseModel):
    query: str = Field(..., min_length=3, max_length=200)
    limit: int = Field(default=10, ge=1, le=100)
    
    @validator('query')
    def sanitize_query(cls, v):
        # Remove potential injection patterns
        return v.strip().replace('\x00', '')

# 2. Secrets aus Environment
class Config:
    api_key: str = os.environ.get("API_KEY")  # ✅ Aus ENV
    # api_key: str = "sk-123..."  # ❌ NIEMALS hardcoded

# 3. Rate Limiting
from functools import wraps
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, calls_per_minute: int = 60):
        self.calls_per_minute = calls_per_minute
        self.calls = defaultdict(list)
    
    def check(self, key: str) -> bool:
        now = time.time()
        minute_ago = now - 60
        
        # Clean old calls
        self.calls[key] = [t for t in self.calls[key] if t > minute_ago]
        
        if len(self.calls[key]) >= self.calls_per_minute:
            return False
        
        self.calls[key].append(now)
        return True

rate_limiter = RateLimiter(calls_per_minute=100)

@app.tool()
async def rate_limited_tool(param: str) -> str:
    """Tool with rate limiting."""
    client_id = get_client_id()  # From MCP context
    
    if not rate_limiter.check(client_id):
        return json.dumps({
            "success": False,
            "error": {
                "category": "client_error",
                "code": "RATE_LIMITED",
                "message": "Too many requests",
                "retry_after": 60,
            }
        })
    
    # Proceed with tool logic
    pass
```

#### 📊 Observability (10%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Structured Logging** | 0-3 | JSON-Format, Context, Levels |
| **Metrics** | 0-3 | Counters, Histograms, Gauges |
| **Request Tracing** | 0-2 | Request IDs, Correlation |
| **Health Endpoint** | 0-2 | Readiness, Liveness |

```python
# ✅ Observability Setup

import logging
import json
from datetime import datetime
from contextvars import ContextVar

# Request ID für Tracing
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(''),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("my-mcp")
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)

# Metrics (Optional: Prometheus)
from prometheus_client import Counter, Histogram

tool_calls = Counter(
    'mcp_tool_calls_total',
    'Total tool calls',
    ['tool_name', 'status']
)

tool_duration = Histogram(
    'mcp_tool_duration_seconds',
    'Tool execution duration',
    ['tool_name']
)

# Health Check Resource
@app.resource("health://status")
async def health_status() -> str:
    """Health check for readiness probes."""
    return json.dumps({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    })
```

#### 🏗️ Architecture (5%)

| Kriterium | Punkte | Beschreibung |
|-----------|--------|--------------|
| **Single Responsibility** | 0-2 | Ein Server, ein Zweck |
| **Dependency Management** | 0-2 | Pinned Versions, minimal |
| **Code Organization** | 0-2 | Klare Struktur, Module |
| **Configuration** | 0-2 | Externalisiert, validiert |
| **Async Best Practices** | 0-2 | Keine blocking Calls |

```
# ✅ Empfohlene Struktur

my_mcp/
├── __init__.py
├── server.py           # MCP Server Entry Point
├── tools/              # Tool Implementations
│   ├── __init__.py
│   ├── search.py
│   └── analyze.py
├── services/           # External Service Clients
│   ├── __init__.py
│   └── api_client.py
├── models/             # Pydantic Models
│   ├── __init__.py
│   ├── requests.py
│   └── responses.py
├── config.py           # Configuration
├── exceptions.py       # Custom Exceptions
└── utils.py            # Utilities

tests/
├── conftest.py
├── unit/
├── integration/
└── e2e/

pyproject.toml
README.md
CHANGELOG.md
```

### 4.3 Scoring & Grades

| Score | Grade | Status | Deployment |
|-------|-------|--------|------------|
| 90-100 | A | Excellent | ✅ Production + Featured |
| 80-89 | B | Good | ✅ Production |
| 70-79 | C | Acceptable | ✅ Production (mit Auflagen) |
| 60-69 | D | Needs Work | ⚠️ Nur Staging |
| 50-59 | E | Minimum | ⚠️ Nur Development |
| <50 | F | Failing | ❌ Nicht deploybar |

### 4.4 Scorecard Template

```
┌──────────────────────────────────────────────────────────────────────────┐
│                    MCP SERVER QUALITY SCORECARD                          │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Server: llm_mcp                                 Date: 2026-02-03        │
│  Version: 1.2.0                                  Reviewer: AI + Human    │
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📊 OVERALL SCORE: 76/100                        Grade: C               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ CATEGORY              │ RAW  │ WEIGHT │ WEIGHTED │ NOTES            ││
│  ├───────────────────────┼──────┼────────┼──────────┼──────────────────┤│
│  │ 🔧 Tool Design        │ 8/10 │  20%   │  16/20   │ Good naming      ││
│  │ 🛡️ Error Handling     │ 6/10 │  15%   │   9/15   │ Needs work       ││
│  │ 📝 Documentation      │ 7/10 │  15%   │ 10.5/15  │ Missing examples ││
│  │ 🧪 Test Coverage      │ 5/10 │  20%   │  10/20   │ 45% coverage     ││
│  │ 🔒 Security           │ 8/10 │  15%   │  12/15   │ Good validation  ││
│  │ 📊 Observability      │ 6/10 │  10%   │   6/10   │ Basic logging    ││
│  │ 🏗️ Architecture       │ 9/10 │   5%   │  4.5/5   │ Clean structure  ││
│  ├───────────────────────┼──────┼────────┼──────────┼──────────────────┤│
│  │ TOTAL                 │      │ 100%   │  68/100  │                  ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  🚨 CRITICAL ISSUES (Must Fix for Production):                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • [SEC-001] No input length validation on `prompt` parameter        ││
│  │ • [ERR-001] Unhandled exception in `generate_text` on API timeout   ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ⚠️ WARNINGS (Should Fix):                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • [TST-001] Test coverage at 45%, target is 80%                     ││
│  │ • [DOC-001] Missing usage examples in README                        ││
│  │ • [OBS-001] No structured logging, using print statements           ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  💡 SUGGESTIONS (Nice to Have):                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ • Add Prometheus metrics for tool call latency                      ││
│  │ • Implement response caching for repeated queries                   ││
│  │ • Add OpenTelemetry tracing for distributed debugging               ││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  ════════════════════════════════════════════════════════════════════   │
│                                                                          │
│  📋 ACTION ITEMS:                                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Priority │ Item                                    │ Owner │ Due    ││
│  ├──────────┼─────────────────────────────────────────┼───────┼────────┤│
│  │ P0       │ Fix SEC-001: Add input validation       │ Dev   │ 1 day  ││
│  │ P0       │ Fix ERR-001: Handle API timeouts        │ Dev   │ 1 day  ││
│  │ P1       │ Increase test coverage to 80%           │ Dev   │ 1 week ││
│  │ P2       │ Add structured logging                  │ Dev   │ 2 weeks││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Säule 2: Automatisierte Quality Gates

### 5.1 CI/CD Pipeline

```yaml
# .github/workflows/mcp-quality.yml
name: "🔍 MCP Quality Gate"

on:
  push:
    paths:
      - '*_mcp/**'
  pull_request:
    paths:
      - '*_mcp/**'

jobs:
  # ═══════════════════════════════════════════════════════════════════
  # Job 1: Static Analysis
  # ═══════════════════════════════════════════════════════════════════
  static-analysis:
    name: "📊 Static Analysis"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Tools
        run: pip install ruff mypy bandit
      
      - name: Ruff (Lint + Format)
        run: ruff check . --output-format=github
      
      - name: MyPy (Type Check)
        run: mypy . --ignore-missing-imports
      
      - name: Bandit (Security)
        run: bandit -r . -f json -o bandit-report.json || true
      
      - name: Upload Security Report
        uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: bandit-report.json

  # ═══════════════════════════════════════════════════════════════════
  # Job 2: MCP-Specific Checks
  # ═══════════════════════════════════════════════════════════════════
  mcp-checks:
    name: "🔧 MCP Quality Checks"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Dependencies
        run: pip install ast-grep pydantic
      
      - name: Check Tool Docstrings
        run: |
          python scripts/check_tool_docstrings.py
      
      - name: Check Error Handling
        run: |
          python scripts/check_error_handling.py
      
      - name: Check Input Validation
        run: |
          python scripts/check_input_validation.py

  # ═══════════════════════════════════════════════════════════════════
  # Job 3: Tests
  # ═══════════════════════════════════════════════════════════════════
  tests:
    name: "🧪 Tests"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install Dependencies
        run: |
          pip install pytest pytest-asyncio pytest-cov
          pip install -e .
      
      - name: Run Tests with Coverage
        run: |
          pytest --cov=. --cov-report=xml --cov-report=html
      
      - name: Check Coverage Threshold
        run: |
          coverage report --fail-under=60
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4

  # ═══════════════════════════════════════════════════════════════════
  # Job 4: Documentation Check
  # ═══════════════════════════════════════════════════════════════════
  docs-check:
    name: "📝 Documentation Check"
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check README exists
        run: |
          if [ ! -f README.md ]; then
            echo "❌ README.md missing"
            exit 1
          fi
      
      - name: Check required sections
        run: |
          python scripts/check_readme_sections.py

  # ═══════════════════════════════════════════════════════════════════
  # Job 5: Generate Scorecard
  # ═══════════════════════════════════════════════════════════════════
  scorecard:
    name: "📊 Generate Scorecard"
    needs: [static-analysis, mcp-checks, tests, docs-check]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate Scorecard
        run: |
          python scripts/generate_scorecard.py \
            --output scorecard.md
      
      - name: Comment on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const fs = require('fs');
            const scorecard = fs.readFileSync('scorecard.md', 'utf8');
            
            await github.rest.issues.createComment({
              owner: context.repo.owner,
              repo: context.repo.repo,
              issue_number: context.issue.number,
              body: scorecard
            });

  # ═══════════════════════════════════════════════════════════════════
  # Job 6: Quality Gate Decision
  # ═══════════════════════════════════════════════════════════════════
  quality-gate:
    name: "🚦 Quality Gate"
    needs: [static-analysis, mcp-checks, tests, docs-check]
    runs-on: ubuntu-latest
    steps:
      - name: Evaluate Results
        run: |
          # Fail if any critical checks failed
          echo "✅ All quality checks passed"
```

### 5.2 Quality Check Scripts

```python
# scripts/check_tool_docstrings.py
"""Check that all MCP tools have proper docstrings."""

import ast
import sys
from pathlib import Path

def check_docstrings(file_path: Path) -> list[str]:
    """Check tool docstrings in a Python file."""
    issues = []
    
    with open(file_path) as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            # Check if decorated with @app.tool() or similar
            is_tool = any(
                isinstance(d, ast.Call) and 
                hasattr(d.func, 'attr') and 
                d.func.attr == 'tool'
                for d in node.decorator_list
            )
            
            if is_tool:
                docstring = ast.get_docstring(node)
                
                if not docstring:
                    issues.append(f"❌ {node.name}: Missing docstring")
                elif "Args:" not in docstring:
                    issues.append(f"⚠️ {node.name}: Missing 'Args:' section")
                elif "Returns:" not in docstring:
                    issues.append(f"⚠️ {node.name}: Missing 'Returns:' section")
    
    return issues

def main():
    all_issues = []
    
    for py_file in Path(".").rglob("*.py"):
        if "test" in str(py_file):
            continue
        issues = check_docstrings(py_file)
        all_issues.extend(issues)
    
    if all_issues:
        print("Docstring Issues Found:")
        for issue in all_issues:
            print(f"  {issue}")
        
        # Fail only on missing docstrings (not missing sections)
        critical = [i for i in all_issues if i.startswith("❌")]
        if critical:
            sys.exit(1)
    else:
        print("✅ All tools have proper docstrings")

if __name__ == "__main__":
    main()
```

---

## 6. Säule 3: MCP-Core Shared Library

### 6.1 Package Struktur

```
mcp-core/
├── pyproject.toml
├── src/
│   └── mcp_core/
│       ├── __init__.py
│       ├── server.py          # Enhanced MCPServer base class
│       ├── decorators.py      # @tool, @resource decorators
│       ├── errors.py          # Structured error handling
│       ├── validation.py      # Input validation utilities
│       ├── logging.py         # Structured logging setup
│       ├── metrics.py         # Prometheus metrics
│       ├── retry.py           # Retry logic
│       ├── config.py          # Configuration management
│       └── testing/
│           ├── __init__.py
│           ├── fixtures.py    # pytest fixtures
│           └── mocks.py       # Common mocks
└── tests/
```

### 6.2 Core Components

```python
# mcp_core/server.py
"""Enhanced MCP Server base class with quality features built-in."""

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp_core.logging import setup_logging
from mcp_core.metrics import MetricsCollector
from mcp_core.config import MCPConfig
from mcp_core.errors import MCPError, ErrorCategory

class MCPServer:
    """
    Enhanced MCP Server with built-in quality features.
    
    Features:
    - Structured logging
    - Prometheus metrics
    - Health checks
    - Configuration management
    - Error handling
    """
    
    def __init__(
        self,
        name: str,
        version: str = "0.1.0",
        config: MCPConfig = None,
    ):
        self.name = name
        self.version = version
        self.config = config or MCPConfig()
        
        # Setup logging
        self.logger = setup_logging(name)
        
        # Setup metrics
        self.metrics = MetricsCollector(name)
        
        # Create underlying MCP server
        self._server = Server(name)
        
        # Register health resource
        self._register_health()
    
    def _register_health(self):
        """Register health check resource."""
        @self._server.resource("health://status")
        async def health_status() -> str:
            return json.dumps({
                "status": "healthy",
                "name": self.name,
                "version": self.version,
                "timestamp": datetime.utcnow().isoformat(),
            })
    
    def tool(
        self,
        *,
        validate: bool = True,
        timeout: int = None,
        retry: int = 0,
        cache_ttl: int = None,
    ):
        """
        Enhanced tool decorator with quality features.
        
        Args:
            validate: Auto-validate parameters using type hints
            timeout: Timeout in seconds (None = use config default)
            retry: Number of retries on transient failures
            cache_ttl: Cache TTL in seconds (None = no caching)
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                tool_name = func.__name__
                
                # Start metrics
                with self.metrics.tool_call(tool_name):
                    try:
                        # Validation
                        if validate:
                            kwargs = self._validate_params(func, kwargs)
                        
                        # Timeout
                        actual_timeout = timeout or self.config.default_timeout
                        
                        # Retry logic
                        last_error = None
                        for attempt in range(retry + 1):
                            try:
                                result = await asyncio.wait_for(
                                    func(*args, **kwargs),
                                    timeout=actual_timeout
                                )
                                
                                self.metrics.tool_success(tool_name)
                                return result
                                
                            except asyncio.TimeoutError:
                                last_error = MCPError(
                                    category=ErrorCategory.SERVER_ERROR,
                                    code="TIMEOUT",
                                    message=f"Tool {tool_name} timed out after {actual_timeout}s"
                                )
                            except TransientError as e:
                                last_error = e
                                if attempt < retry:
                                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                        
                        # All retries failed
                        self.metrics.tool_error(tool_name, last_error.code)
                        return last_error.to_json()
                        
                    except ValidationError as e:
                        self.metrics.tool_error(tool_name, "VALIDATION_ERROR")
                        return MCPError(
                            category=ErrorCategory.CLIENT_ERROR,
                            code="VALIDATION_ERROR",
                            message=str(e),
                        ).to_json()
                        
                    except Exception as e:
                        self.logger.exception(f"Unexpected error in {tool_name}")
                        self.metrics.tool_error(tool_name, "INTERNAL_ERROR")
                        return MCPError(
                            category=ErrorCategory.SERVER_ERROR,
                            code="INTERNAL_ERROR",
                            message="An internal error occurred",
                        ).to_json()
            
            # Register with underlying server
            self._server.tool()(wrapper)
            return wrapper
        
        return decorator
    
    async def run(self):
        """Run the MCP server."""
        self.logger.info(f"Starting {self.name} v{self.version}")
        
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(read_stream, write_stream)


# mcp_core/errors.py
"""Structured error handling for MCP servers."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any
import json

class ErrorCategory(Enum):
    CLIENT_ERROR = "client_error"      # 4xx - User's fault
    SERVER_ERROR = "server_error"      # 5xx - Our fault
    EXTERNAL_ERROR = "external_error"  # Dependency failure

@dataclass
class MCPError(Exception):
    """Structured MCP error."""
    category: ErrorCategory
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None
    
    def to_dict(self) -> dict:
        result = {
            "success": False,
            "error": {
                "category": self.category.value,
                "code": self.code,
                "message": self.message,
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.retry_after:
            result["error"]["retry_after"] = self.retry_after
        return result
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


# mcp_core/validation.py
"""Input validation utilities."""

from pydantic import BaseModel, ValidationError
from typing import get_type_hints, Type
import inspect

def validate_tool_params(func, kwargs: dict) -> dict:
    """
    Validate tool parameters using type hints.
    
    Automatically creates a Pydantic model from function signature.
    """
    hints = get_type_hints(func)
    sig = inspect.signature(func)
    
    # Build Pydantic model dynamically
    fields = {}
    for name, param in sig.parameters.items():
        if name == 'self':
            continue
        
        hint = hints.get(name, str)
        default = param.default if param.default != inspect.Parameter.empty else ...
        fields[name] = (hint, default)
    
    # Create model
    Model = type('ParamsModel', (BaseModel,), {'__annotations__': hints})
    
    # Validate
    try:
        validated = Model(**kwargs)
        return validated.dict()
    except ValidationError as e:
        raise ValidationError(e.errors())
```

### 6.3 Migration Guide

```python
# VORHER: Standalone MCP Server
from mcp.server import Server
from mcp.server.stdio import stdio_server

app = Server("my-mcp")

@app.tool()
async def my_tool(query: str) -> str:
    """Search for items."""
    try:
        result = await search(query)
        return json.dumps({"success": True, "data": result})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e)})

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream)


# NACHHER: Mit mcp-core
from mcp_core import MCPServer

server = MCPServer("my-mcp", version="1.0.0")

@server.tool(validate=True, retry=3, timeout=30)
async def my_tool(query: str, limit: int = 10) -> str:
    """
    Search for items matching the query.
    
    Args:
        query: Search query (min 3 chars)
        limit: Max results (1-100)
    
    Returns:
        JSON with search results
    """
    # Validation, error handling, retries, metrics - all automatic!
    result = await search(query, limit)
    return json.dumps({"success": True, "data": result})

if __name__ == "__main__":
    import asyncio
    asyncio.run(server.run())
```

---

## 7. Implementation Plan

### Phase 1: Foundation (Woche 1-2)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Scorecard Template finalisieren | Achim | `docs/mcp-scorecard-template.md` |
| Check Scripts erstellen | Dev | `scripts/check_*.py` |
| CI Pipeline einrichten | DevOps | `.github/workflows/mcp-quality.yml` |
| Erste 3 Server reviewen | Team | Scorecards für llm, bfagent, deployment |

### Phase 2: MCP-Core (Woche 3-4)

| Task | Owner | Deliverable |
|------|-------|-------------|
| mcp-core Package erstellen | Dev | `mcp-core/` Package |
| Base Classes implementieren | Dev | MCPServer, Decorators |
| Error Handling | Dev | MCPError, Validation |
| Unit Tests für mcp-core | Dev | >90% Coverage |

### Phase 3: Migration (Woche 5-8)

| Task | Owner | Deliverable |
|------|-------|-------------|
| Production Server migrieren | Dev | 7 Server auf mcp-core |
| Beta Server upgraden | Dev | 6 Server quality-compliant |
| Documentation Update | Dev | Alle READMEs aktualisiert |
| Final Review | Team | Alle Server ≥ Grade C |

### Phase 4: Continuous Improvement (Ongoing)

| Task | Owner | Frequency |
|------|-------|-----------|
| Monthly Quality Review | Team | Monatlich |
| Scorecard Updates | Auto | Bei jedem PR |
| Dependency Updates | Bot | Wöchentlich |
| Security Scans | CI | Bei jedem Push |

---

## 8. Consequences

### 8.1 Positive

| Benefit | Impact |
|---------|--------|
| **Konsistente Qualität** | Alle Server erfüllen Mindeststandards |
| **Frühe Fehlererkennung** | CI fängt Issues vor Production |
| **Reduzierter Boilerplate** | ~60% weniger Code pro Server |
| **Bessere Wartbarkeit** | Einheitliche Struktur |
| **Transparenz** | Objektive Qualitätsmessung |
| **Schnelleres Onboarding** | Klare Standards, gute Docs |

### 8.2 Negative

| Drawback | Mitigation |
|----------|------------|
| Initialer Aufwand | Phasenweise Migration |
| Learning Curve | Gute Dokumentation, Examples |
| CI-Zeit erhöht | Parallelisierung, Caching |
| Breaking Changes | Deprecation Warnings, Migration Guide |

### 8.3 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Zu strenge Standards | Medium | Medium | Grade C als Minimum für Production |
| Migration unterbricht Development | Medium | High | Feature Freeze während Migration vermeiden |
| mcp-core wird zum Bottleneck | Low | High | Minimal Dependencies, Good Docs |

---

## 9. Success Metrics

| Metric | Current | Target (3M) | Target (6M) |
|--------|---------|-------------|-------------|
| Avg Server Score | ~60? | ≥75 | ≥80 |
| Servers Grade C+ | ~50%? | ≥90% | 100% |
| Test Coverage Avg | ~40%? | ≥70% | ≥80% |
| Critical Issues Open | Unknown | 0 | 0 |
| Time to Add New Tool | ~2h | ~30min | ~15min |

---

## 10. References

- [MCP Specification 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18)
- [MCP Best Practices Guide](https://modelcontextprotocol.info/docs/best-practices/)
- [Anthropic MCP Blog](https://www.anthropic.com/news/model-context-protocol)
- [MCP Server Development Guide](https://github.com/cyanheads/model-context-protocol-resources)

---

## Changelog

| Date | Author | Change |
|------|--------|--------|
| 2026-02-03 | Achim Dehnert | Initial version |
