# ADR-400: Hybrid-Architektur für Market Scanner Module

| Attribut       | Wert                                      |
|----------------|-------------------------------------------|
| **Status**     | Proposed                                  |
| **Scope**      | trading-hub (400-449)                     |
| **Erstellt**   | 2026-02-12                                |
| **Autor**      | Achim Dehnert                             |
| **Reviewer**   | –                                         |
| **Supersedes** | –                                         |
| **Relates to** | ADR-014 (AI-Native Development Teams), ADR-015 (Platform Governance) |

---

## 1. Kontext

### 1.1 Ausgangslage

Der Trading-Hub (`trading-hub.iil.pet` / `ai-trades.de`) ist eine Django-basierte Multi-Asset-Trading-Plattform, die Crypto (CCXT/Binance/Kraken), Aktien (Alpaca) und Forex (OANDA) unterstützt. Die bestehende Infrastruktur umfasst:

- **Django 5.x** mit Celery-Worker, Redis, WebSocket-Channels
- **Bestehende Models**: `TradingPair`, `ExchangeAccount`, `Strategy`, `Signal`, `Trade`, `Portfolio`
- **Docker-Compose-Stack**: Web, Channels, Worker, Beat, Nginx, PostgreSQL, Redis
- **Deployment**: Hetzner-Server (88.198.191.108) via etabliertem Deploy-Workflow

### 1.2 Anforderung

Es wird ein **Market Scanner** Modul benötigt, das periodisch alle verfügbaren Trading-Paare analysiert und nach ihrer Eignung für Daytrading / kurzfristiges Trading rankt. Das Modul soll:

1. **Multi-Asset-Scanning**: Crypto (100+ Paare via CCXT), Aktien (US-Markt via Alpaca), Forex (Majors/Minors via OANDA) abdecken
2. **Composite-Score berechnen** aus vier Metrik-Kategorien:
   - Volatilität (ATR, Standardabweichung, Bollinger-Bandbreite)
   - Volumen & Liquidität (24h-Volume, Volume-Change, Bid-Ask-Spread)
   - Momentum & Trend (RSI, MACD, Price-Change %)
   - Tradability (Spread-Kosten, Slippage-Schätzung, Handelszeiten)
3. **Periodisch laufen** (konfigurierbar, z.B. alle 5 Minuten) via Celery Beat
4. **Ergebnisse persistieren** für Dashboard-Anzeige und Strategy-Engine-Nutzung
5. **Konfigurierbare Gewichtung** der Score-Komponenten pro Nutzer/Strategie

### 1.3 Constraints

- Die Lösung muss sich in die bestehende Trading-Hub-Architektur integrieren (Django, Celery, Redis, PostgreSQL)
- Kein neuer Service/Container – das Modul läuft im bestehenden Worker-Container
- API-Rate-Limits der Exchanges müssen respektiert werden (Binance: 1200 req/min, Alpaca: 200 req/min, OANDA: 120 req/s)
- Die Scoring-Logik muss unabhängig testbar sein (CI/CD ohne Exchange-Zugang)
- Onboarding neuer Entwickler soll durch klare Trennung erleichtert werden

---

## 2. Entscheidung

**Wir verwenden eine Hybrid-Architektur**: Die Core-Scoring-Logik wird als reines Python-Package (`lib/market_scanner/`) ohne Django-Abhängigkeiten implementiert. Eine dünne Django-App (`apps/scanner/`) integriert das Package in den Trading-Hub für Persistenz, Scheduling und Frontend-Anbindung.

### 2.1 Zielarchitektur

```
trading-hub/
├── lib/
│   └── market_scanner/                  # Reines Python-Package (KEIN Django)
│       ├── __init__.py                  # Public API: ScanEngine, ScanResult
│       ├── py.typed                     # PEP 561 Marker
│       ├── engine.py                    # ScanEngine – Orchestriert den Scan
│       ├── scoring.py                   # CompositeScorer – Gewichtete Score-Berechnung
│       ├── models.py                    # Pydantic-Dataclasses: PairScore, ScanResult, ScanConfig
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base.py                  # MarketDataProvider (Protocol)
│       │   ├── crypto.py                # CryptoProvider (CCXT)
│       │   ├── stocks.py                # StockProvider (Alpaca)
│       │   └── forex.py                 # ForexProvider (OANDA)
│       ├── metrics/
│       │   ├── __init__.py
│       │   ├── base.py                  # MetricCalculator (Protocol)
│       │   ├── volatility.py            # ATR, StdDev, BollingerWidth
│       │   ├── volume.py                # Volume24h, VolumeChange, VWAP
│       │   ├── momentum.py              # RSI, MACD, PriceChange
│       │   └── tradability.py           # SpreadCost, Slippage, MarketHours
│       └── tests/
│           ├── __init__.py
│           ├── conftest.py              # Fixtures mit Mock-OHLCV-Daten
│           ├── test_engine.py
│           ├── test_scoring.py
│           ├── test_metrics_volatility.py
│           ├── test_metrics_volume.py
│           ├── test_metrics_momentum.py
│           └── test_providers.py
│
├── apps/
│   └── scanner/                         # Dünne Django-App (Integration Only)
│       ├── __init__.py
│       ├── apps.py                      # ScannerConfig
│       ├── models.py                    # ScanRun, PairRanking (DB-Persistenz)
│       ├── tasks.py                     # Celery-Tasks: run_scan, cleanup_old_scans
│       ├── views.py                     # HTMX-Partials: Top-Pairs, Scanner-Dashboard
│       ├── urls.py
│       ├── admin.py                     # ScanRun/PairRanking Admin
│       ├── serializers.py               # DRF-Serializer (optional, für API)
│       └── templates/
│           └── scanner/
│               └── partials/
│                   ├── _top_pairs.html  # HTMX-Partial: Top-10-Ranking-Tabelle
│                   ├── _scan_status.html
│                   └── _pair_detail.html
│
├── pyproject.toml                       # market_scanner als lokales Package
└── ...
```

### 2.2 Abhängigkeitsgraph

```
apps/scanner/ ──depends on──▶ lib/market_scanner/
                              │
                              ├── ccxt (>=4.0)
                              ├── pandas (>=2.0)
                              ├── pandas-ta (>=0.3.14b)
                              ├── pydantic (>=2.0)
                              └── alpaca-py / oandapyV20 (optional)
```

Die Django-App importiert **nur** die Public API des Packages:

```python
# apps/scanner/tasks.py
from market_scanner import ScanEngine, ScanConfig, ScanResult
from market_scanner.providers import CryptoProvider, StockProvider, ForexProvider
```

Das Package importiert **niemals** Django-Module. Diese Grenze ist unverhandelbar und wird per CI-Check (`import-linter`) enforced.

---

## 3. Betrachtete Alternativen

### Option A: Standalone Django-App (Monolith)

Gesamte Logik (Scoring, Provider, Metriken) direkt in einer Django-App (`apps/scanner/`).

| Aspekt | Bewertung |
|--------|-----------|
| Setup-Aufwand | ⭐⭐⭐⭐⭐ Minimal – alles in einem Ort |
| Testbarkeit | ⭐⭐ Unit-Tests brauchen Django-Setup (`pytest-django`), langsam |
| Wiederverwendbarkeit | ⭐ Nur innerhalb Django nutzbar |
| Onboarding | ⭐⭐ Neue Entwickler müssen Django kennen, um Scoring-Logik zu verstehen |
| Separation of Concerns | ⭐ Business-Logik und Framework vermischt |
| Refactoring-Aufwand | ⭐⭐ Spätere Extraktion erfordert signifikantes Refactoring |

**Verworfen**, weil die Scoring-Logik (ATR berechnen, Composite-Scores, Provider-Abstraktion) **null mit Django zu tun hat**. Bei 3 Asset-Klassen × 4 Metrik-Kategorien × dutzenden Edge Cases würde die App zu monolithisch. Unit-Tests bräuchten Django-Testrunner, was den Feedback-Loop verlangsamt.

### Option B: Reines Python-Package (Standalone)

Komplette Lösung als eigenständiges `pip install`-fähiges Package ohne Django-Integration.

| Aspekt | Bewertung |
|--------|-----------|
| Setup-Aufwand | ⭐⭐⭐⭐ Package-Struktur aufsetzen |
| Testbarkeit | ⭐⭐⭐⭐⭐ Perfekt isoliert, schnelle Tests |
| Wiederverwendbarkeit | ⭐⭐⭐⭐⭐ Notebook, CLI, andere Apps |
| Onboarding | ⭐⭐⭐⭐ Klare Package-API |
| Integration in Trading-Hub | ⭐ Celery-Tasks, DB-Persistenz, HTMX-Partials fehlen komplett |
| Time-to-Value | ⭐⭐ Muss separat integriert werden |

**Verworfen**, weil kritische Features fehlen: Celery-Beat für periodische Scans, DB-Persistenz für Scan-Ergebnisse (Dashboard, Strategy-Engine), WebSocket-Push bei neuen Top-Pairs. Man landet zwangsläufig beim Hybrid, weil die Integrationsschicht ohnehin gebaut werden muss.

### Option C: Hybrid – Core-Package + dünne Django-App ✅ (Gewählt)

| Aspekt | Bewertung |
|--------|-----------|
| Setup-Aufwand | ⭐⭐⭐ Etwas mehr initial (~15% mehr Code als Option A) |
| Testbarkeit | ⭐⭐⭐⭐⭐ Core-Tests ohne Django in <2s, Integration-Tests separat |
| Wiederverwendbarkeit | ⭐⭐⭐⭐⭐ Notebook, CLI, andere Apps möglich |
| Onboarding | ⭐⭐⭐⭐⭐ Klare Trennung, jede Schicht separat verständlich |
| Separation of Concerns | ⭐⭐⭐⭐⭐ Business-Logik ≠ Framework-Integration |
| Konsistenz mit Plattform | ⭐⭐⭐⭐⭐ Folgt `bfagent-llm` Pattern |
| Skalierbarkeit | ⭐⭐⭐⭐ Core kann in separatem Worker-Container laufen |

---

## 4. Begründung im Detail

### 4.1 Konsistenz mit Plattform-Patterns

Das `bfagent-llm` Package folgt exakt dieses Muster: Reines Python-Package mit Django-Integration als separate Schicht. `cad-services` separiert ebenfalls Core-Logik (Extractor, Parser, Calculator) von der FastAPI-Schicht. ADR-400 führt kein neues Pattern ein, sondern wendet ein bewährtes an.

### 4.2 Testbarkeit als Kernargument

Der Market Scanner hat eine hohe Kombinatorik:

- **3 Provider** × **4 Metrik-Kategorien** × **Edge Cases** (leere Daten, API-Timeouts, Börse geschlossen, ungewöhnliche Spreads) = **50+ Unit-Tests** allein für die Scoring-Logik

Diese Tests müssen schnell laufen (<5s) und dürfen keine Django-Datenbank, Redis oder Exchange-API benötigen. Mit dem Hybrid-Ansatz:

```bash
# Core-Tests: ~1.5s, kein Django
pytest lib/market_scanner/tests/ -x

# Integration-Tests: ~8s, mit Django
pytest apps/scanner/tests/ -x --ds=config.settings.test
```

### 4.3 Onboarding-Optimierung

Ein neuer Entwickler, der an der Scoring-Logik arbeiten soll, braucht kein Django-Wissen:

1. `cd lib/market_scanner/`
2. `pip install -e ".[dev]"` 
3. `pytest` → alle Tests grün
4. Ändere `metrics/volatility.py`, schreibe Test, fertig

Ein Entwickler, der das Frontend/Dashboard erweitern soll:

1. Versteht `apps/scanner/views.py` (HTMX-Partials)
2. Nutzt `ScanEngine` als Black Box über die Public API
3. Braucht kein Wissen über ATR-Berechnung oder CCXT-API

### 4.4 Skalierungspfad

Aktuell läuft alles im bestehenden Worker-Container. Wenn die Scan-Last steigt (alle CCXT-Pairs = 200+ API-Calls pro Scan), kann die Engine in einen dedizierten Container verschoben werden:

```yaml
# docker-compose.prod.yml (Zukunft)
scanner-worker:
  build: .
  command: celery -A config worker -Q scanner -c 4
  environment:
    - CELERY_QUEUES=scanner
```

Diese Skalierung erfordert **null Refactoring** am Core-Package.

---

## 5. Konsequenzen

### 5.1 Positive Konsequenzen

- **Schneller Feedback-Loop**: Core-Tests in <2s ohne externe Abhängigkeiten
- **Klare Ownership**: Scoring-Logik und Framework-Integration haben unterschiedliche Änderungszyklen
- **Wiederverwendbarkeit**: `market_scanner` kann in Jupyter-Notebooks für Strategy-Research, als CLI-Tool für Ad-hoc-Analysen und potenziell in anderen Apps genutzt werden
- **Dokumentation per Design**: Die Package-API (`ScanEngine`, `ScanConfig`, `PairScore`) ist selbstdokumentierend
- **CI/CD-Effizienz**: Core-Tests laufen in der CI parallel und unabhängig von Django-Migrations

### 5.2 Negative Konsequenzen / Trade-offs

- **Initialer Mehraufwand**: ~15% mehr Code gegenüber Option A durch Package-Setup, `pyproject.toml`, Interface-Design
- **Zwei Test-Suiten**: Core-Tests und Django-Integration-Tests müssen separat gepflegt werden
- **Import-Disziplin**: Die Grenze "Package importiert kein Django" muss aktiv enforced werden (→ `import-linter` in CI)
- **Daten-Mapping**: Pydantic-Models im Package müssen auf Django-Models in der App gemappt werden (1x Setup, danach stabil)

### 5.3 Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| API-Rate-Limits bei großen Scans | Hoch | Mittel | Async-Batching mit Backoff, konfigurierbare Scan-Subsets |
| Stale Scores bei Exchange-Ausfällen | Mittel | Niedrig | TTL auf Scan-Ergebnisse, Fallback auf letzten gültigen Scan |
| Over-Engineering für MVP | Niedrig | Niedrig | Phase 1 nur Crypto, Phase 2 Stocks+Forex |
| Import-Grenze wird verletzt | Niedrig | Mittel | `import-linter` in CI, Code-Review-Checkliste |

---

## 6. Implementation Plan

### Phase 1: Core-Package (Crypto Only) — ~3 Tage

1. Package-Struktur erstellen (`lib/market_scanner/`)
2. `MarketDataProvider` Protocol + `CryptoProvider` (CCXT) implementieren
3. Metriken implementieren: `volatility.py`, `volume.py`, `momentum.py`, `tradability.py`
4. `CompositeScorer` mit konfigurierbaren Gewichtungen
5. `ScanEngine` als Orchestrator
6. Unit-Tests mit Mock-OHLCV-Daten (kein Live-API-Zugang nötig)

### Phase 2: Django-Integration — ~2 Tage

7. `apps/scanner/` Django-App erstellen
8. Models: `ScanRun`, `PairRanking`
9. Celery-Tasks: `run_crypto_scan` (periodic), `cleanup_old_scans`
10. HTMX-Partials: Top-Pairs-Tabelle, Scan-Status, Pair-Detail
11. Integration-Tests mit `pytest-django`

### Phase 3: Multi-Asset-Erweiterung — ~3 Tage

12. `StockProvider` (Alpaca) mit Market-Hours-Logik
13. `ForexProvider` (OANDA) mit Session-Awareness (London/NY/Tokyo)
14. Marktzeiten-Awareness im Scoring (nur offene Märkte scannen)
15. Provider-spezifische Metriken (z.B. Open Interest für Crypto-Futures)

### Phase 4: Advanced Features — ~2 Tage

16. WebSocket-Push bei signifikanten Ranking-Änderungen
17. Historische Scan-Vergleiche (Score-Trends über Zeit)
18. Benutzer-spezifische Gewichtungsprofile
19. Export-Funktionen (CSV, API-Endpoint)

---

## 7. Onboarding Guide

### 7.1 Für neue Entwickler: "Wo fange ich an?"

```
Ich will...                         → Starte hier
─────────────────────────────────────────────────────────────
Scoring-Logik verstehen/ändern      → lib/market_scanner/README.md
Neue Metrik hinzufügen              → lib/market_scanner/metrics/base.py (Protocol lesen)
Neuen Provider (Exchange) anbinden  → lib/market_scanner/providers/base.py (Protocol lesen)
Dashboard/Frontend ändern           → apps/scanner/views.py + templates/
Scan-Schedule anpassen              → apps/scanner/tasks.py + config/celery.py
Datenbank-Schema ändern             → apps/scanner/models.py + makemigrations
```

### 7.2 Architektur-Regeln (MUST)

1. **`lib/market_scanner/` importiert NIEMALS `django.*`** — Enforced via `import-linter` in CI
2. **Alle Datenstrukturen im Package sind Pydantic-Models**, keine Django-Models
3. **Provider sind austauschbar** — jeder Provider implementiert das `MarketDataProvider` Protocol
4. **Metriken sind austauschbar** — jede Metrik implementiert das `MetricCalculator` Protocol
5. **Die Django-App ist dünn** — sie mappt Package-Ergebnisse auf Django-Models und stellt HTMX-Partials bereit

### 7.3 Lokale Entwicklung

```bash
# 1. Core-Package entwickeln (kein Docker nötig)
cd lib/market_scanner/
pip install -e ".[dev]"
pytest                              # ~1.5s, alles grün

# 2. Mit Live-Daten testen (optional)
python -m market_scanner --exchange binance --top 20

# 3. Django-Integration testen
cd /path/to/trading-hub
docker compose up db redis -d
pytest apps/scanner/tests/ --ds=config.settings.test

# 4. Vollständiger Stack
docker compose -f docker-compose.prod.yml up
```

### 7.4 Dependency-Matrix

| Komponente | Python | Django | Celery | Redis | PostgreSQL | CCXT |
|-----------|--------|--------|--------|-------|------------|------|
| `lib/market_scanner/` | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ |
| `lib/market_scanner/tests/` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ (Mock) |
| `apps/scanner/` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ (via lib) |

---

## 8. Validation Criteria

Das ADR gilt als erfolgreich implementiert, wenn:

- [ ] `pytest lib/market_scanner/tests/` läuft in <5s ohne externe Abhängigkeiten
- [ ] `import-linter` bestätigt: kein Django-Import in `lib/market_scanner/`
- [ ] Celery-Task `run_crypto_scan` liefert Top-20 Paare mit Composite-Score
- [ ] HTMX-Partial `/scanner/partials/top-pairs/` rendert Ranking-Tabelle
- [ ] Scoring-Gewichtung ist zur Laufzeit konfigurierbar (kein Code-Change nötig)
- [ ] Ein neuer Provider kann durch Implementierung des `MarketDataProvider` Protocol hinzugefügt werden, ohne bestehenden Code zu ändern

---

## 9. Referenzen

- **Internes Precedent**: `bfagent-llm` Package (reines Python + Django-Integration)
- **Internes Precedent**: `cad-services` (Core-Logik + FastAPI-Schicht)
- **ADR-014**: AI-Native Development Teams (Team-Struktur und Gate-System)
- **Libraries**: [CCXT](https://github.com/ccxt/ccxt) (108+ Exchanges), [pandas-ta](https://github.com/twopirllc/pandas-ta) (130+ Indikatoren), [Alpaca-py](https://github.com/alpacahq/alpaca-py), [import-linter](https://github.com/seddonym/import-linter)
- **Pattern**: Ports & Adapters / Hexagonal Architecture (Provider = Adapter, Engine = Port)
