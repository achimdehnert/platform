# ADR-401: Autonomer Trading Bot — Execution-Loop & Bot-Architektur

| Attribut       | Wert                                                                                                      |
|----------------|-----------------------------------------------------------------------------------------------------------|
| **Status**     | Proposed                                                                                                  |
| **Scope**      | trading-hub (400-449)                                                                                     |
| **Erstellt**   | 2026-02-19                                                                                                |
| **Autor**      | Achim Dehnert                                                                                             |
| **Reviewer**   | –                                                                                                         |
| **Supersedes** | –                                                                                                         |
| **Relates to** | ADR-400 (Market Scanner), ADR-045 (Secrets Management), ADR-022 (Platform Consistency), ADR-041 (Django Component Pattern), ADR-014 (AI-Native Development Teams) |

---

## 1. Kontext

### 1.1 Ausgangslage

Der Trading-Hub (`trading-hub.iil.pet` / `ai-trades.de`) verfügt bereits über alle strukturellen Bausteine für einen autonomen Trading Bot:

- **`SignalEngine`**: XGBoost/LightGBM Feature-Engineering (RSI, MACD, ATR, Bollinger, ADX, Volume-Ratio)
- **`EnsembleEngine`**: Gewichtete Fusion von ML + RL + Sentiment-Signalen
- **`OrderManager`**: Paper- und Live-Execution für Crypto (CCXT), Stocks (Alpaca), Forex (OANDA)
- **`RiskManager`**: Daily-Loss-Limit, Max-Open-Trades, Position-Sizing, Drawdown-Circuit-Breaker
- **`DataCollector`**: OHLCV-Daten von allen 3 Asset-Klassen
- **`Backtester`**: vectorbt + QuantStats
- **Celery-Tasks**: `collect_prices_task`, `run_signals_task`, `run_backtest_task`
- **Domain-Modelle**: `Strategy`, `Signal`, `Trade`, `Portfolio`, `ExchangeAccount`, `TradingPair`

### 1.2 Kritische Lücken

**Lücke A — Fehlender Execution-Loop**: Die bestehenden Services existieren isoliert. Es gibt keinen Task, der ausführbare Signale (`Signal.executed=False`, Confidence ≥ Threshold) abholt, Risk-Checks durchführt, Orders platziert, `Trade`-Objekte anlegt und offene Positionen auf Stop-Loss / Take-Profit überwacht.

**Lücke B — Kein Audit-Trail für Bot-Läufe**: Die Platform-Philosophie ist datenbankgetrieben — jeder relevante Zustand wird persistiert. Bot-Ausführungen, Skips, Circuit-Breaker-Auslösungen und Fehler sind aktuell nicht nachvollziehbar. Es fehlen die Models `BotRun` und `ExecutionLog`.

**Lücke C — Separation-of-Concerns-Verstoß**: `RiskManager` importiert `Trade` und `TradeStatus` direkt aus `trading_hub.django.models`. Services dürfen gemäß ADR-400 Hybrid-Pattern kein Django importieren. Dieser Verstoß wird mit dem Execution-Loop behoben: Risk-Checks erhalten typisierte Datenklassen statt Django-Model-Instanzen.

**Lücke D — Bekannte Stubs im Code**:

| Stub | Datei | Schweregrad |
|------|-------|-------------|
| `feature_cols=[]` in `run_signals_task` | `tasks/run_signals.py` | � Kritisch |
| `api_key_ref` ohne Secret-Auflösung | `services/order_manager.py` | � Kritisch |
| `TradingEnvironment` ist leer (`pass`) | `services/rl_agent.py` | � Hoch |
| `SentimentAnalyzer` ist Keyword-Matching | `services/sentiment.py` | � Hoch |
| RL-Confidence hardcoded `0.75` | `services/rl_agent.py` | 🟡 Mittel |
| `MarketData` kein TimescaleDB-Hypertable | `django/models.py` | 🟡 Mittel |

### 1.3 Constraints

- Kein neuer Service/Container für den Bot-Core — läuft im bestehenden Celery-Worker
- Paper-Trading-Modus muss vollständig funktionieren, bevor Live-Trading aktiviert wird
- Idempotenz aller Order-Tasks ist Pflicht (Celery-Retry darf keine Doppelorders erzeugen)
- Secret-Management für API-Keys muss ADR-045 folgen
- ML-Baseline muss im Backtest profitabel sein, bevor RL-Agent in Produktion geht

---

## 2. Entscheidung

**Wir implementieren den autonomen Trading Bot in drei Phasen** (Crawl → Walk → Run), beginnend mit einem vollständigen Paper-Trading-Bot für Crypto (ML-only), bevor Live-Trading oder Multi-Asset aktiviert wird.

### 2.1 Zielarchitektur — Execution-Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                        Celery Beat Schedule                      │
│                                                                  │
│  collect_prices_task (1min)  ──▶  MarketData (TimescaleDB)      │
│         │                                                        │
│         ▼                                                        │
│  run_signals_task (5min)     ──▶  Signal (executed=False)       │
│         │                                                        │
│         ▼                                                        │
│  execute_signals_task (5min) ──▶  RiskManager.check_can_trade() │
│         │                    ──▶  OrderManager.place_order()    │
│         │                    ──▶  Trade.create()                │
│         │                    ──▶  Signal.executed = True        │
│         │                                                        │
│  monitor_trades_task (1min)  ──▶  Preis vs. SL/TP prüfen       │
│                               ──▶  OrderManager.close_trade()   │
│                               ──▶  Portfolio.update()           │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Neue Tasks (Zielstruktur)

```
trading-hub/src/trading_hub/tasks/
├── __init__.py
├── collect_prices.py          # ✅ Vorhanden
├── run_signals.py             # ✅ Vorhanden (fix: feature_cols)
├── execute_signals.py         # 🆕 Neu — Kern des Execution-Loop
├── monitor_trades.py          # 🆕 Neu — SL/TP Monitoring
├── update_portfolio.py        # 🆕 Neu — Portfolio-Aggregation
└── run_backtest.py            # ✅ Vorhanden
```

### 2.3 Neue DB-Models — Datenbankgetriebener Audit-Trail

Gemäß Platform-Philosophie wird jeder relevante Bot-Zustand persistiert:

```python
# django/models.py — Ergänzungen

class BotRunStatus(models.TextChoices):
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CIRCUIT_BREAK = "circuit_break", "Circuit Breaker Ausgelöst"


class BotRun(TenantModel):
    """Protokolliert jeden Execution-Loop-Durchlauf."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE, related_name="bot_runs")
    status = models.CharField(max_length=15, choices=BotRunStatus.choices)
    signals_evaluated = models.IntegerField(default=0)
    signals_executed = models.IntegerField(default=0)
    signals_skipped = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "trading_bot_run"
        ordering = ["-started_at"]


class ExecutionLog(TenantModel):
    """Detailliertes Log pro Signal-Ausführung oder Skip."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bot_run = models.ForeignKey(BotRun, on_delete=models.CASCADE, related_name="logs")
    signal = models.ForeignKey(Signal, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20)  # executed, skipped, risk_rejected, error
    reason = models.TextField(blank=True)
    trade = models.ForeignKey("Trade", on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = "trading_execution_log"
        ordering = ["-created_at"]
```

### 2.4 Trade-State-Machine

Das bestehende `TradeStatus`-Enum wird um `PENDING` und `PARTIAL_FILL` erweitert. Da `TradeStatus` ein `TextChoices`-Enum ist, erfordert die Erweiterung eine Django-Migration (`makemigrations` + `migrate`). Bestehende Datensätze sind nicht betroffen — neue Werte sind additiv.

```
PENDING ──▶ OPEN ──▶ CLOSED
              │
              ├──▶ CANCELLED  (Risk-Check fehlgeschlagen)
              │
              └──▶ PARTIAL_FILL  (nur Live-Trading, Limit-Orders)
```

### 2.5 Idempotenz-Pattern (Pflicht für alle Order-Tasks)

```python
# tasks/execute_signals.py — Idempotenz-Guard
@shared_task(name="trading.execute_signals_task", bind=True, max_retries=3)
def execute_signals_task(self, tenant_id: str | None = None):
    signals = Signal.objects.select_for_update().filter(
        executed=False,
        confidence__gte=F("strategy__confidence_threshold"),
    )
    for signal in signals:
        with transaction.atomic():
            # Re-check inside transaction to prevent race conditions
            if Signal.objects.filter(id=signal.id, executed=True).exists():
                continue
            signal.executed = True
            signal.save(update_fields=["executed"])
            # ... place order
```

### 2.6 Secret-Management (ADR-045-konform)

`api_key_ref` im `ExchangeAccount`-Model referenziert einen Secret-Key. Der `OrderManager` löst diesen über den in ADR-045 definierten `read_secret()`-Helper auf — **kein eigenes Secret-Schema**, kein `env:`-Prefix:

```python
# config/secrets.py — bereits durch ADR-045 definiert, hier nur Nutzung
from config.secrets import read_secret

# In services/order_manager.py:
api_key = read_secret(account.api_key_ref, required=True)
api_secret = read_secret(account.api_secret_ref, required=True)
```

Das `api_key_ref`-Feld im `ExchangeAccount`-Model enthält den **Key-Namen** (z.B. `BINANCE_API_KEY`), nicht den Wert. `read_secret()` sucht in `/run/secrets/<key_lower>`, dann in `os.environ` — ADR-045 Section 2.4 Pattern A.

### 2.7 Separation of Concerns — RiskManager-Fix

`RiskManager` importiert aktuell Django-Models direkt (Verstoß gegen ADR-400 Hybrid-Pattern). Der Fix: Risk-Checks erhalten eine typisierte Datenklasse `PortfolioSnapshot` statt einer Django-Model-Instanz:

```python
# services/risk_manager.py — nach Fix
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class PortfolioSnapshot:
    tenant_id: str
    exchange_account_id: str
    total_value: Decimal
    cash_balance: Decimal
    daily_pnl: Decimal
    max_drawdown: Decimal
    open_trade_count: int

# check_can_trade() erhält PortfolioSnapshot statt Portfolio-Django-Model
def check_can_trade(self, snapshot: PortfolioSnapshot, trade_params: dict) -> tuple[bool, str]:
    ...
```

Die Django-App (`tasks/execute_signals.py`) baut den `PortfolioSnapshot` aus dem DB-Model und übergibt ihn an den Service — kein Django-Import im Service.

### 2.8 Sentiment-Upgrade (realistisch, ohne LLM-Latenz)

Für Intraday-Trading (1m–1h) wird LLM-Sentiment durch strukturierte Marktdaten ersetzt:

| Quelle | Frequenz | Verwendung |
|--------|----------|------------|
| Binance Funding Rate | 8h | Crypto-Regime-Filter (Contrarian) |
| Alternative.me Fear & Greed | 1x täglich | Tages-Bias |
| LLM-Sentiment (Claude/FinGPT) | 1x täglich | Weekly-Bias, nicht Intraday |

### 2.9 Dashboard-Komponenten (ADR-041-konform)

Das Bot-Monitoring-Dashboard wird als HTMX-Komponenten nach ADR-041 Component Pattern implementiert. Alle Elemente tragen `data-testid`-Attribute:

```
data-testid="bot-run-status"          — Aktueller BotRun-Status
data-testid="bot-run-signals-count"   — Ausgeführte / Übersprungene Signale
data-testid="execution-log-table"     — ExecutionLog-Tabelle
data-testid="circuit-breaker-alert"   — Circuit-Breaker-Warnung
data-testid="portfolio-pnl-daily"     — Tages-PnL
```

---

## 3. Betrachtete Alternativen

### Option A: Vollständiger Bot auf einmal (Big Bang)

Alle Komponenten (Execution-Loop, RL-Agent, Multi-Asset, LLM-Sentiment) gleichzeitig implementieren.

| Aspekt | Bewertung |
|--------|-----------|
| Time-to-Value | ⭐ Monate bis erster lauffähiger Bot |
| Risiko | ⭐ Fehler in RL-Training blockieren gesamten Bot |
| Testbarkeit | ⭐⭐ Schwer isoliert testbar |
| Kapitalrisiko | ⭐ Unvalidierte Komponenten in Produktion |

**Verworfen.** Zu hohes Risiko, zu langer Feedback-Loop.

### Option B: Regelbasierter Bot (kein ML)

Einfache Regeln (RSI < 30 → Buy, RSI > 70 → Sell) ohne ML/RL.

| Aspekt | Bewertung |
|--------|-----------|
| Implementierungsaufwand | ⭐⭐⭐⭐⭐ Minimal |
| Erklärbarkeit | ⭐⭐⭐⭐⭐ Vollständig transparent |
| Performance | ⭐⭐ Bekannt schwach in Trending-Märkten |
| Nutzung vorhandener Infrastruktur | ⭐⭐ SignalEngine/EnsembleEngine ungenutzt |

**Teilweise übernommen** als Baseline für Backtesting-Vergleich, nicht als Produktions-Bot.

### Option C: Phasenweise (Crawl → Walk → Run) ✅ (Gewählt)

| Aspekt | Bewertung |
|--------|-----------|
| Time-to-Value | ⭐⭐⭐⭐⭐ Paper-Bot in 2-3 Wochen |
| Risiko | ⭐⭐⭐⭐⭐ Jede Phase validiert die nächste |
| Nutzung vorhandener Infrastruktur | ⭐⭐⭐⭐⭐ Alle Services werden verbunden |
| Kapitalschutz | ⭐⭐⭐⭐⭐ Live-Trading erst nach Paper-Validierung |
| Erweiterbarkeit | ⭐⭐⭐⭐ RL/Multi-Asset als optionale Phase 3 |

---

## 4. Begründung im Detail

### 4.1 Warum Crypto-only als MVP

- 24/7-Markt — kein Marktzeiten-Management nötig
- CCXT bereits vollständig integriert
- Paper-Trading via CCXT-Sandbox verfügbar
- Binance Funding Rate als kostenloser Regime-Filter
- Höchste Datenverfügbarkeit für Backtesting

### 4.2 Warum ML vor RL

Der RL-Agent (`TradingEnvironment`) ist ein leerer Stub. Ein stabiles Gymnasium-Environment zu bauen, zu trainieren und zu validieren erfordert:
- Sorgfältiges Reward-Engineering (Sharpe-basiert, nicht nur PnL)
- Vermeidung von Look-Ahead-Bias im Environment
- Mindestens 50.000–200.000 Trainings-Steps
- Separate Validierungs-Perioden (Walk-Forward)

XGBoost/LightGBM hingegen sind mit den vorhandenen Features (`compute_features()` in `SignalEngine`) sofort trainierbar und interpretierbar.

### 4.3 Warum Idempotenz kritisch ist

Celery-Tasks können bei Broker-Timeouts oder Worker-Neustarts mehrfach ausgeführt werden. Ohne Idempotenz-Guard entstehen Doppelorders — bei Live-Trading mit realem Kapital ein nicht akzeptables Risiko. `select_for_update()` + `transaction.atomic()` ist das Standardmuster für diesen Fall.

### 4.4 Skalierungspfad

```yaml
# docker-compose.prod.yml (Zukunft) — ADR-022-konform: env_file statt environment:
bot-worker:
  image: ${IMAGE_NAME}:${IMAGE_TAG:-latest}
  command: celery -A config worker -Q bot_execution -c 2
  env_file: .env.prod
  deploy:
    resources:
      limits:
        memory: 512M
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
  restart: unless-stopped
```

Die Queue-Trennung (`bot_execution` vs. `default`) ermöglicht separate Skalierung und Monitoring des Bot-Workers. App-Konfiguration (`TRADING_MODE`, `CELERY_QUEUES`) kommt ausschließlich aus `.env.prod` — kein `environment:`-Block mit App-Variablen (ADR-022 Regel A8).

---

## 5. Implementation Plan

### Phase 1: Paper-Bot, Crypto only, ML-only — ~2-3 Wochen

**Woche 1: DB-Schema + Execution-Loop**

1. `django/models.py` — `BotRun`, `ExecutionLog` Models ergänzen + Migration
2. `django/models.py` — `TradeStatus` um `PENDING`, `PARTIAL_FILL` erweitern + Migration
3. `services/risk_manager.py` — `PortfolioSnapshot` Dataclass, Django-Import entfernen (SoC-Fix)
4. `tasks/execute_signals.py` — Idempotenter Execution-Task mit `select_for_update`
5. `tasks/monitor_trades.py` — SL/TP-Monitoring für offene Trades
6. `tasks/update_portfolio.py` — Portfolio-Aggregation nach Trade-Close

**Woche 2: Signal-Pipeline + Secret-Management**

7. `services/order_manager.py` — `api_key_ref` via `read_secret()` auflösen (ADR-045)
8. `tasks/run_signals.py` — `feature_cols` aus `strategy.parameters` laden
9. `tasks/run_signals.py` — Strategy-Type-Routing (trend_following → Modell-Pfad)
10. Celery-Beat-Schedule für alle 5 Tasks konfigurieren
11. Unit-Tests für `execute_signals_task` (Mock-OrderManager, Mock-PortfolioSnapshot)
12. Integration-Test: End-to-End Paper-Trade (Signal → BotRun → Trade → Close → ExecutionLog)

**Woche 3: Dashboard + Validierung**

13. Backtesting auf 6 Monate BTC/USDT, ETH/USDT historische Daten
14. Paper-Trading-Monitoring-Dashboard (ADR-041 Component Pattern, `data-testid`-Attribute)
15. Alerting bei Circuit-Breaker-Auslösung (E-Mail / Webhook)
16. Dokumentation: Paper-Trading-Playbook

### Phase 2: Live-Bot, Crypto, ML + Market Scanner — ~4-6 Wochen

17. ADR-400 Market Scanner implementieren (Scanner-Score als Signal-Filter)
18. Secret-Management vollständig via SOPS (ADR-045 Phase 5 — CI/CD-Deploy nach `/run/secrets/`)
19. Order-Fill-Confirmation via CCXT-WebSocket (für Limit-Orders)
20. TimescaleDB Hypertable Migration für `MarketData` (separates ADR-403 empfohlen)
21. Funding-Rate-Collector (Binance) als Regime-Filter
22. Fear & Greed Index Integration (täglicher Bias)
23. 30 Tage Paper-Trading-Validierung: Sharpe ≥ 1.0, Max-DD < 10%
24. Live-Trading-Aktivierung (schrittweise: 10% → 25% → 50% des Kapitals)

### Phase 3: Multi-Asset + Ensemble + RL (optional) — ~3+ Monate

25. `StockProvider` (Alpaca) mit Market-Hours-Awareness
26. `ForexProvider` (OANDA) mit Session-Awareness (London/NY/Tokyo)
27. `TradingEnvironment` (Gymnasium) vollständig implementieren
28. RL-Agent Training (PPO) auf historischen Daten
29. RL-Agent Walk-Forward-Validierung (Out-of-Sample)
30. LLM-Sentiment (Claude/FinGPT) als Weekly-Bias-Signal
31. Ensemble-Gewichtung per Strategie konfigurierbar (DB-gesteuert via `Strategy.parameters`)
32. RL-Agent in Produktion (nur wenn Phase 2 Sharpe ≥ 1.5 über 90 Tage)

---

## 6. Risiken

| Risiko | Wahrscheinlichkeit | Auswirkung | Mitigation |
|--------|-------------------|------------|------------|
| Doppelorder durch Celery-Retry | Hoch (ohne Guard) | 🔴 Kritisch | `select_for_update` + Idempotenz-Guard (Phase 1) |
| ML-Modell nicht vorhanden beim Start | Hoch | 🔴 Kritisch | Fallback: kein Signal wenn Modell fehlt (kein Crash) |
| API-Key-Leak durch plaintext `api_key_ref` | Mittel | 🔴 Kritisch | `config/secrets.py` `read_secret()` gemäß ADR-045 (Phase 1) |
| Overfitting des ML-Modells | Hoch | 🟠 Hoch | Walk-Forward-Backtest, Out-of-Sample-Validierung |
| Exchange-Ausfall während offener Position | Mittel | 🟠 Hoch | Circuit-Breaker, manuelle Override-Möglichkeit |
| RL-Agent instabil in Produktion | Hoch | 🟠 Hoch | RL erst nach ML-Baseline profitabel (Phase 3) |
| Sentiment-Signal zu langsam (LLM-Latenz) | Hoch | 🟡 Mittel | LLM nur für Daily-Bias, nicht Intraday (Phase 2) |
| TimescaleDB-Migration Downtime | Niedrig | 🟡 Mittel | Migration in Maintenance-Window, Backup vorher |

---

## 7. Konsequenzen

### 7.1 Positive Konsequenzen

- **Sofortiger Wert**: Paper-Bot in 2-3 Wochen lauffähig — alle vorhandenen Services werden verbunden
- **Kapitalschutz**: Phasenweise Validierung verhindert Live-Trading mit unvalidierten Komponenten
- **Erweiterbarkeit**: Jede Phase baut auf der vorherigen auf — kein Refactoring nötig
- **Testbarkeit**: Idempotenz-Pattern ermöglicht Unit-Tests ohne Exchange-Zugang
- **Monitoring**: Circuit-Breaker und Alerting von Anfang an

### 7.2 Negative Konsequenzen / Trade-offs

- **Kein RL im MVP**: RL-Agent ist der ambitionierteste Teil — bewusst auf Phase 3 verschoben
- **Crypto-only Phase 1**: Multi-Asset erfordert Marktzeiten-Management (nicht trivial)
- **Modell-Training extern**: XGBoost/LightGBM-Modelle müssen separat trainiert und deployed werden (Jupyter Notebook / MLflow)
- **Paper-Trading-Pflicht**: Mindestens 30 Tage Paper-Trading vor Live-Aktivierung — kein Shortcut

### 7.3 Nicht in Scope dieses ADR

- ML-Modell-Training-Pipeline (separates ADR empfohlen: ADR-402)
- TimescaleDB-Migrations-Strategie (separates ADR empfohlen: ADR-403)
- Multi-Tenant-Isolation für Bot-Execution (folgt bestehenden `TenantModel`-Patterns)

---

## 8. Validation Criteria

### Phase 1 — Gate: Paper-Bot lauffähig

- [ ] `BotRun` und `ExecutionLog` werden pro Execution-Loop-Durchlauf persistiert
- [ ] `execute_signals_task` läuft idempotent — kein Doppelorder bei Celery-Retry
- [ ] Paper-Trade End-to-End: Signal → BotRun → Risk-Check → Order → Trade → ExecutionLog → Portfolio-Update
- [ ] `monitor_trades_task` schließt Trades bei SL/TP-Erreichen korrekt
- [ ] `RiskManager` importiert kein `django.*` — `PortfolioSnapshot` Dataclass in Verwendung
- [ ] `read_secret()` (ADR-045) löst `api_key_ref` auf — kein Plaintext-Key im Code
- [ ] `feature_cols` wird aus `strategy.parameters` geladen — kein leeres Array
- [ ] Circuit-Breaker (Daily-Loss, Max-Drawdown) stoppt neue Orders und schreibt `BotRun.status = circuit_break`
- [ ] Dashboard-Komponenten tragen `data-testid`-Attribute gemäß ADR-041

### Phase 2 — Gate: Live-Trading freigegeben

- [ ] 30 Tage Paper-Trading ohne Circuit-Breaker-Auslösung
- [ ] Sharpe Ratio ≥ 1.0 über 30-Tage-Zeitraum
- [ ] Max Drawdown < 10% über 30-Tage-Zeitraum
- [ ] ADR-400 Market Scanner aktiv als Signal-Filter
- [ ] SOPS-verschlüsselte API-Keys via CI/CD deployed (ADR-045 vollständig)
- [ ] `bot-worker` Compose-Service ADR-022-konform (env_file, memory limit, logging)

### Phase 3 — Gate: RL-Agent in Produktion

- [ ] ML-Baseline (Phase 2) Sharpe Ratio ≥ 1.5 über 90 Tage
- [ ] RL-Agent Walk-Forward-Validierung: Out-of-Sample Sharpe ≥ ML-Baseline
- [ ] `TradingEnvironment` vollständig implementiert und getestet (kein `pass`)
- [ ] RL-Confidence aus Aktions-Wahrscheinlichkeiten abgeleitet (kein Hardcode)

---

## 9. Referenzen

- **ADR-400**: Market Scanner Hybrid-Architektur (Signal-Filter für Phase 2; definiert Hybrid-Pattern und SoC-Regeln)
- **ADR-045**: Secrets Management — `config/secrets.py` + `read_secret()` Pattern (Section 2.4 Pattern A)
- **ADR-022**: Platform Consistency Standard — `env_file`-Regel, Compose-Template, Memory-Limits
- **ADR-041**: Django Component Pattern — `data-testid`-Konvention für Dashboard-Komponenten
- **ADR-014**: AI-Native Development Teams
- **Codebase**: `trading_hub/services/` — `SignalEngine`, `EnsembleEngine`, `OrderManager`, `RiskManager`
- **Libraries**: [CCXT](https://github.com/ccxt/ccxt), [vectorbt](https://vectorbt.dev/), [Stable-Baselines3](https://stable-baselines3.readthedocs.io/), [pandas-ta](https://github.com/twopirllc/pandas-ta)
- **Muster**: Idempotente Celery-Tasks via `select_for_update` + `transaction.atomic()`

---

## 10. Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| 2026-02-19 | Achim Dehnert | Initial Draft — Execution-Loop, BotRun/ExecutionLog Models, ADR-045/022/041-Konformität |
