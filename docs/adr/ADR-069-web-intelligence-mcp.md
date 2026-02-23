# ADR-069: Web Intelligence MCP — Plattformweiter Web-Zugriff

```yaml
status: proposed
date: 2026-02-23
amended: 2026-02-23
decision-makers: [achim.dehnert]
tags: [mcp-hub, web-scraping, web-intelligence, httpx, trafilatura, crawl4ai, playwright, redis, coach-hub, weltenhub, travel-beat, bfagent]
drift-detector: paths=[mcp-hub/web_intelligence_mcp/], adr=ADR-069
```

---

## Kontext und Problemstellung

Die Plattform hat keinen zentralen Web-Zugriff-Mechanismus. Fünf aktive Hubs
(research/bfagent, coach-hub, weltenhub, travel-beat, trading-hub) benötigen
unabhängig voneinander Zugriff auf Webinhalte — Regulierungstexte, Wikipedia,
Nachrichtenartikel, POI-Daten, Finanznachrichten. Jede App löst das Problem
aktuell ad-hoc oder gar nicht.

**Kernfrage:** Wie stellen wir plattformweit einen einheitlichen, compliance-konformen,
gecachten Web-Zugriff für KI-Agenten bereit — ohne Code-Duplikation, ohne
IP-Sperren durch inkonsistentes Rate-Limiting, und mit klarer DSGVO-Hoheit?

**Nicht-Ziel (dieses ADR):** Authentifiziertes Scraping (Login-Sessions) → ADR-070.
URL-Discovery / Spider-Logik → separates ADR. Dieses MCP empfängt immer
**konkrete URLs** von aufrufenden Agenten.

---

## Decision Drivers

- Kein Code-Duplikat in 5+ Repos (DRY-Prinzip)
- Einheitliches Rate-Limiting → keine IP-Sperren
- Gemeinsame Redis-Cache-Schicht → keine redundanten Requests
- robots.txt-Compliance → rechtliche Absicherung
- DSGVO-Hoheit: Inhalte bleiben auf eigenem Server
- Konsistenz mit bestehendem MCP-Pattern (travel-mcp, deployment-mcp)
- JS-Rendering für moderne Portale (trading-hub, Finanznachrichten)
- Erweiterbarkeit ohne Breaking Changes (Provider-Pattern)

---

## Considered Options

1. **httpx + trafilatura** — Async HTTP-Client + wissenschaftlich evaluiertes Extraktionstool
2. **Playwright (Browser-basiert)** — Vollständiges JS-Rendering via headless Chromium
3. **Hybrid Provider-Pattern** — httpx+trafilatura als Default, Playwright lazy, Wikipedia-API strukturiert
4. **Crawl4AI als Core-Engine** — Single-Dependency für Fetch+JS-Rendering+Extraktion (58k Stars, Apache 2.0)
5. **Externer Dienst** — Jina AI Reader / Firecrawl als SaaS

---

## Decision Outcome

**Gewählte Option: Option 3 (Hybrid Provider-Pattern) — nach Crawl4AI-Spike ggf. Option 4**

Das Provider-Pattern ist konsistent mit `travel-mcp` (bereits bewährt) und erlaubt
maximale Flexibilität. Vor Phase 1a wird ein **1-Tages-Spike** durchgeführt: Crawl4AI
als Single-URL-Fetcher gegen httpx+trafilatura auf 5 repräsentativen URLs benchmarken.
Ergebnis des Spikes bestimmt den primären Provider.

**Entscheidungsmatrix:**

| Frage | Entscheidung | Begründung |
|-------|-------------|------------|
| Build vs. Buy | **Build** (eigener MCP) | DSGVO-Hoheit, kein Vendor-Lock-in |
| Cache-Backend | **Redis** | Bereits im Platform-Stack |
| Playwright-Strategie | **Lazy** (opt-in, separates Image) | ~1.2GB — nur bei Bedarf |
| Jina AI Reader | **Opt-in Fallback** | DSGVO-Prüfung erforderlich |
| Modulname | **`web_intelligence_mcp`** | Beschreibt Wert, nicht Mechanismus |
| Wikipedia | **Direkte API** | Strukturiert, stabil, kein Scraping nötig |
| Auth-Scope | **ADR-070** | Separates Konzept, eigene Entscheidung |

### Consequences

**Good:**
- Einmaliger Aufwand, plattformweiter Nutzen (5+ Repos)
- Provider-Pattern erlaubt Austausch ohne Breaking Changes
- Redis-Cache reduziert externe Requests drastisch
- robots.txt-Compliance out-of-the-box
- Crawl4AI-Option offen gehalten (Spike entscheidet)

**Bad:**
- Initialer Implementierungsaufwand (~3 Wochen gesamt)
- Playwright-Image (~1.2GB) erhöht Docker-Footprint wenn aktiviert
- Drittpaket-Abhängigkeit wenn Crawl4AI gewählt wird

**Neutral:**
- Auth-Scraping explizit OUT OF SCOPE → ADR-070

---

## Architektur

### Modulstruktur

```
mcp-hub/
└── web_intelligence_mcp/
    ├── src/web_intelligence_mcp/
    │   ├── server.py           # FastMCP Server
    │   ├── settings.py         # Pydantic Settings (SecretStr für Credentials)
    │   ├── cache.py            # Redis TTL-Cache + URL-Normalisierung
    │   ├── rate_limiter.py     # Token-Bucket per Domain (aiolimiter)
    │   ├── robots.py           # robots.txt async + Redis-Cache
    │   ├── extractor.py        # HTML → Markdown (trafilatura + markdownify)
    │   └── providers/
    │       ├── base.py         # AbstractProvider
    │       ├── httpx_provider.py      # Statisch (Default)
    │       ├── crawl4ai_provider.py   # JS-fähig (nach Spike-Entscheidung)
    │       ├── playwright_provider.py # JS-fähig (Alternative)
    │       ├── wikipedia_provider.py  # Wikipedia API (strukturiert)
    │       └── jina_provider.py       # Extern (opt-in Fallback)
    ├── tests/
    └── pyproject.toml
```

### Provider-Fallback-Kette

```
fetch_page(url, provider="auto")
    │
    ├─ robots.txt check → BLOCK if disallowed
    ├─ Cache check → HIT: return cached result
    │
    ├─ Wikipedia URL? → wikipedia_provider
    ├─ Domain-Config Override? → konfigurierter Provider
    ├─ Default → httpx_provider + trafilatura
    ├─ Bei leerem Content / Fehler → crawl4ai_provider (JS-Fallback)
    └─ Letzter Fallback → jina_provider (extern, opt-in)
```

### Domain-Konfiguration (statt fragiler Heuristik)

```python
PROVIDER_OVERRIDES: dict[str, str] = {
    "finanzen.net": "playwright",
    "handelsblatt.com": "playwright",
    "wikipedia.org": "wikipedia",
    "eur-lex.europa.eu": "httpx",
    "bafin.de": "httpx",
}
DEFAULT_PROVIDER: str = "httpx"
JS_FALLBACK_PROVIDER: str = "crawl4ai"  # oder "playwright" nach Spike
```

### MCP Tools

```python
fetch_page(url, output_format, provider, timeout_ms) -> FetchResult
extract_content(url, selectors, output_format) -> ExtractResult
wikipedia_search(query, language, sections, max_length) -> WikipediaResult
extract_links(url, filter_pattern, internal_only) -> LinksResult
fetch_multiple(urls, output_format, max_concurrent) -> BatchFetchResult
screenshot_page(url, full_page, element_selector) -> ScreenshotResult  # Playwright only
```

### Fehlermodell

```python
class FetchErrorType(str, Enum):
    ROBOTS_BLOCKED = "robots_blocked"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    PROVIDER_UNAVAILABLE = "provider_unavailable"

class FetchResult(BaseModel):
    success: bool
    url: str
    content: str | None = None
    provider_used: str | None = None
    cached: bool = False
    error: FetchErrorType | None = None
    error_detail: str | None = None
    elapsed_ms: int | None = None

class BatchFetchResult(BaseModel):
    results: list[FetchResult]  # Immer alle — auch Fehler
    total: int
    succeeded: int
    failed: int
```

### Caching

```python
CACHE_TTL = {
    "wikipedia": 86400,   # 24h
    "regulation": 3600,   # 1h (EU AI Act etc.)
    "news": 1800,         # 30min
    "default": 3600,      # 1h
}
# Cache-Key: SHA256(normalize_url(url) + output_format + selectors)
# URL-Normalisierung: www-Strip, HTTPS, Tracking-Params entfernen, Query sortieren
```

### User-Agent-Policy

```python
# httpx-Provider: Transparent (ethisch + rechtlich korrekt)
HTTPX_USER_AGENT = "WebIntelligenceMCP/1.0 (+https://iil.gmbh)"

# Playwright-Provider: Realistisch (technisch notwendig —
# headless Browser werden mit transparentem UA blockiert)
PLAYWRIGHT_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36..."
```

---

## Dependency-Stack

```toml
# Basis (P0+P1) — ~15MB
dependencies = [
    "mcp>=1.0.0", "fastmcp>=2.0.0",
    "pydantic>=2.0.0", "pydantic-settings>=2.0.0",
    "httpx[http2]>=0.27.0",       # bereits im Stack
    "trafilatura>=1.9.0",          # Boilerplate-Removal + Markdown
    "beautifulsoup4>=4.12.0", "lxml>=5.1.0",
    "markdownify>=0.13.0",
    "redis[asyncio]>=5.0.0",       # bereits im Stack
    "aiolimiter>=1.1.0",
    "tenacity>=8.2.0",
    "wikipedia-api>=0.7.0",
]

[project.optional-dependencies]
crawl4ai = ["crawl4ai>=0.4.0"]    # Nach Spike-Entscheidung
browser = [                        # ~1.2GB
    "playwright>=1.41.0",
    "playwright-stealth>=1.0.6",
]
```

---

## Implementierungsplan

### Phase 0 — Crawl4AI Spike (1 Tag)

- Crawl4AI Single-URL-Modus vs. httpx+trafilatura auf 5 URLs benchmarken
- Entscheidung: Crawl4AI als JS-Provider oder Playwright
- Output: Spike-Ergebnis dokumentiert

### Phase 1a — Minimal Viable MCP (3–4 Tage)

- `fetch_page` (httpx + trafilatura)
- FastMCP Server (analog travel-mcp)
- Basis-Tests (pytest + respx)
- Windsurf MCP-Konfiguration

### Phase 1b — Cache + Wikipedia (3–4 Tage)

- Redis-Cache mit URL-Normalisierung
- `wikipedia_search`
- Rate-Limiter (aiolimiter, per Domain)
- `extract_links`

### Phase 1c — Extraktion + Compliance (3–4 Tage)

- `extract_content` (CSS-Selektoren)
- robots.txt-Compliance (async, Redis-gecacht)
- CI-Pipeline + Release v0.1.0

### Phase 2 — Erweiterung (~1 Woche)

- `fetch_multiple` (parallel, BatchFetchResult)
- Jina-Provider (opt-in)
- Domain-Config für Provider-Overrides
- structlog Observability

### Phase 3 — Browser-Rendering (bei Bedarf)

- Crawl4AI-Provider ODER Playwright-Provider (nach Phase-0-Entscheidung)
- `screenshot_page`
- Separates Docker-Image

---

## Compliance und Sicherheit

- **robots.txt**: Automatisch gecacht (24h Redis), Crawl-delay respektiert
- **Rate-Limiting**: Token-Bucket per Domain, konfigurierbar
- **DSGVO**: Nur öffentliche Inhalte gecacht, kein Login-Scraping
- **Urheberrecht**: §44b UrhG (Text & Data Mining) — Nutzung für Forschung/nicht-kommerziell
- **Credentials**: Nie in Cache, nie in Logs — Scope von ADR-070
- **CAPTCHA-Solving**: Explizit nicht implementiert

---

## Verweise

- Konzeptpapier v2: `docs/adr/inputs/concept-web-scraping-mcp.md`
- Critical Review: `docs/adr/inputs/review-web-intelligence-mcp.md`
- ADR-070: Authentifiziertes Web-Scraping (geplant)
- Referenz-Implementierung: `mcp-hub/travel_mcp/` (Provider-Pattern)
- ADR-021: Unified Deployment Pattern
