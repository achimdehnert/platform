---
status: proposed
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-052: Trading Hub — Broker-Adapter-Architektur

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-052 |
| **Titel** | Trading Hub — Broker-Adapter-Architektur |
| **Status** | Proposed |
| **Datum** | 2026-02-19 |
| **Betrifft** | trading-hub |
| **Related ADRs** | ADR-022, ADR-027, ADR-043 |

---

## 1. Problem

Der aktuelle `OrderManager` (`services/order_manager.py`) verletzt mehrere Platform-Prinzipien:

- **Kein Interface-Vertrag:** Broker sind `if/elif`-Zweige, keine austauschbaren Objekte
- **Business Logic im Adapter:** P&L-Berechnung und Trade-Status-Mutation vermischen sich mit Broker-API-Calls
- **Silent Fallbacks:** `filled_price=0` bei fehlgeschlagenem Fill, keine Exception-Propagation
- **Keine Idempotenz:** Kein `client_order_id`, kein Replay-Schutz
- **`dict`-Übergaben:** `trade_params: dict` statt typsicherer DTOs
- **`import` in Funktionskörpern:** Lazy Imports erschweren Testbarkeit
- **IBKR fehlt:** Interactive Brokers nicht integriert

---

## 2. Kontext

- Trading-Hub ist ein Multi-Tenant-System mit RLS via `TenantModel`
- Broker-Anbindung erfolgt aktuell direkt im `OrderManager` (monolithisch, nicht austauschbar)
- Strategien und Signale sollen broker-unabhängig bleiben
- IBKR-Integration ist neu; bestehende Adapter (CCXT, Alpaca, OANDA) müssen erhalten bleiben
- Celery-Worker führen Orders asynchron aus — Reconnect-Szenarien sind produktionsrelevant

---

## 3. Optionen

| Option | Beschreibung | Bewertung |
| --- | --- | --- |
| **A: Status quo** | `if/elif` im `OrderManager` erweitern | ❌ Nicht skalierbar, nicht testbar |
| **B: Strategy-Pattern** | Broker-Logik als austauschbare Strategie-Objekte | ⚠️ Kein klares Interface, kein Idempotenz-Konzept |
| **C: Port-Adapter-Pattern** | `BrokerPort` (ABC) als Interface-Vertrag, Adapter pro Broker | ✅ Testbar, austauschbar, erweiterbar |
| **D: Externe Message Queue** | Orders via Queue an separaten Broker-Service | ⚠️ Overengineering für aktuelle Projektgröße |

**Entscheidung: Option C** — Port-Adapter-Pattern bietet klare Schichtentrennung, ist mit `PaperBrokerAdapter` sofort testbar und erlaubt schrittweise Migration.

---

## 4. Entscheidung: Port-Adapter-Pattern

```
ExecutionService (broker-blind)
    └── BrokerPort (ABC)
            ├── IBKRAdapter       (ib_insync, TWS/IB Gateway)
            ├── AlpacaAdapter     (alpaca-py)
            ├── CCXTAdapter       (ccxt, Crypto)
            ├── OANDAAdapter      (oandapyV20)
            └── PaperBrokerAdapter (Simulation)
```

**Prinzipien:**
- Kein Silent Fallback — explizite Exception-Hierarchie
- Idempotenz via `client_order_id` (UUID, DB-unique)
- UTC-intern für alle Timestamps
- Paper/Live-Trennung im Adapter, nicht im Service
- `ExecutionService` kennt keine Broker-spezifischen Typen

---

## 5. Verzeichnisstruktur

```
trading_hub/
├── django/
│   └── models.py            # BESTEHEND — Trade, TradingPair, Portfolio, ExchangeAccount …
├── domain/
│   ├── dtos.py              # Instrument, OrderIntent, OrderState, Fill, Position, AccountSnapshot
│   └── exceptions.py        # BrokerError-Hierarchie
├── brokers/
│   ├── port.py              # BrokerPort (ABC)
│   ├── registry.py          # get_broker() Factory
│   └── adapters/
│       ├── ibkr.py
│       ├── alpaca.py
│       ├── ccxt.py
│       ├── oanda.py
│       └── paper.py
└── services/
    ├── execution_service.py # Einziger Einstiegspunkt
    ├── signal_service.py    # Signal-Lifecycle (executed-Flag) — NICHT im ExecutionService
    └── order_manager.py     # DEPRECATED (entfernt in 2 Releases)
```

**Einbettung in bestehende Struktur:** `domain/` und `brokers/` sind neue Untermodule neben dem bestehenden `django/`, `services/`, `tasks/`. Kein Umbenennen bestehender Pfade.

---

## 6. Domain-DTOs (`domain/dtos.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class TimeInForce(str, Enum):
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass(frozen=True)
class Instrument:
    symbol: str           # "AAPL", "BTC/USDT", "EUR/USD"
    exchange: str         # "SMART", "NASDAQ", "binance"
    currency: str         # "USD", "USDT"
    asset_class: str      # "stock", "crypto", "forex"
    broker_symbol: str = ""  # nach resolve_instrument() — wird in TradingPair.broker_symbol persistiert


@dataclass(frozen=True)
class OrderIntent:
    instrument: Instrument
    side: OrderSide
    quantity: Decimal
    order_type: OrderType
    client_order_id: str          # UUID — Idempotenz-Schlüssel
    limit_price: Decimal | None = None
    stop_price: Decimal | None = None
    time_in_force: TimeInForce = TimeInForce.DAY
    metadata: dict = field(default_factory=dict)


@dataclass
class OrderState:
    client_order_id: str
    broker_order_id: str
    status: OrderStatus
    filled_qty: Decimal
    avg_fill_price: Decimal | None
    submitted_at: datetime        # UTC
    last_updated: datetime        # UTC
    broker_raw: dict = field(default_factory=dict)


@dataclass
class Position:
    instrument: Instrument
    qty: Decimal
    avg_cost: Decimal
    unrealized_pnl: Decimal | None = None


@dataclass
class AccountSnapshot:
    cash: Decimal
    equity: Decimal
    margin_used: Decimal
    currency: str
    timestamp: datetime           # UTC
```

---

## 7. Exception-Hierarchie (`domain/exceptions.py`)

```python
class BrokerError(Exception):
    """Basis."""

class BrokerConnectionError(BrokerError):
    """Verbindung unterbrochen. Retryable."""

class BrokerAuthError(BrokerError):
    """API-Key ungültig. Fatal."""

class InsufficientFundsError(BrokerError):
    """Nicht genug Kapital. Fatal."""

class MarketClosedError(BrokerError):
    """Markt geschlossen. Fatal."""

class RateLimitError(BrokerError):
    """Rate-Limit. Retryable mit Backoff."""

class OrderRejectedError(BrokerError):
    """Order abgelehnt. Fatal."""

class SymbolNotFoundError(BrokerError):
    """Symbol nicht auflösbar. Fatal."""

class DuplicateOrderError(BrokerError):
    """client_order_id bereits verwendet. Idempotenz-Schutz."""
```

---

## 8. BrokerPort (`brokers/port.py`)

```python
from abc import ABC, abstractmethod
from trading_hub.domain.dtos import AccountSnapshot, Instrument, OrderIntent, OrderState, Position


class BrokerPort(ABC):

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    @abstractmethod
    def resolve_instrument(self, instrument: Instrument) -> Instrument:
        """Broker-Symbol auflösen. Raises SymbolNotFoundError."""

    @abstractmethod
    def place_order(self, intent: OrderIntent) -> OrderState:
        """Raises DuplicateOrderError, OrderRejectedError."""

    @abstractmethod
    def cancel_order(self, client_order_id: str) -> OrderState: ...

    @abstractmethod
    def get_order_state(self, client_order_id: str) -> OrderState: ...

    @abstractmethod
    def get_open_orders(self) -> list[OrderState]:
        """Für Reconciliation nach Reconnect."""

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    @abstractmethod
    def get_account_snapshot(self, currency: str = "USD") -> AccountSnapshot: ...
```

---

## 9. IBKRAdapter (`brokers/adapters/ibkr.py`)

```python
import logging
from datetime import datetime, timezone
from decimal import Decimal

from ib_insync import IB, Forex, LimitOrder, MarketOrder, Stock

from trading_hub.brokers.port import BrokerPort
from trading_hub.domain.dtos import (
    AccountSnapshot, Instrument, OrderIntent, OrderState, OrderStatus, Position
)
from trading_hub.domain.exceptions import (
    BrokerConnectionError, BrokerError,
    OrderRejectedError, SymbolNotFoundError,
)

logger = logging.getLogger("trading_hub.brokers.ibkr")


class IBKRAdapter(BrokerPort):
    """IBKR via ib_insync. Paper: Port 7497 | Live: Port 7496"""

    def __init__(self, host="127.0.0.1", port=7497, client_id=1):
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib = IB()

    def connect(self) -> None:
        try:
            self._ib.connect(self._host, self._port, clientId=self._client_id)
        except Exception as exc:
            raise BrokerConnectionError(f"IBKR connect failed: {exc}") from exc

    def disconnect(self) -> None:
        self._ib.disconnect()

    def is_connected(self) -> bool:
        return self._ib.isConnected()

    def resolve_instrument(self, instrument: Instrument) -> Instrument:
        details = self._ib.reqContractDetails(self._to_contract(instrument))
        if not details:
            raise SymbolNotFoundError(f"IBKR: no contract for {instrument.symbol}")
        c = details[0].contract
        return Instrument(
            symbol=instrument.symbol,
            exchange=c.exchange or instrument.exchange,
            currency=c.currency,
            asset_class=instrument.asset_class,
            broker_symbol=c.localSymbol,
        )

    def place_order(self, intent: OrderIntent) -> OrderState:
        # Hinweis: Idempotenz-Prüfung erfolgt im ExecutionService (DB-unique constraint).
        # Der Adapter vertraut darauf, dass client_order_id einmalig ist.
        ib_order = self._to_ib_order(intent)
        ib_order.orderRef = intent.client_order_id
        trade = self._ib.placeOrder(self._to_contract(intent.instrument), ib_order)
        self._ib.sleep(0.5)
        if trade.orderStatus.status in ("Inactive", "ApiCancelled"):
            raise OrderRejectedError(f"{intent.client_order_id}: {trade.orderStatus.status}")
        return self._to_order_state(intent.client_order_id, trade)

    def cancel_order(self, client_order_id: str) -> OrderState:
        for trade in self._ib.trades():
            if trade.order.orderRef == client_order_id:
                self._ib.cancelOrder(trade.order)
                self._ib.sleep(0.5)
                return self._to_order_state(client_order_id, trade)
        raise BrokerError(f"IBKR: order not found: {client_order_id}")

    def get_order_state(self, client_order_id: str) -> OrderState:
        for trade in self._ib.trades():
            if trade.order.orderRef == client_order_id:
                return self._to_order_state(client_order_id, trade)
        raise BrokerError(f"IBKR: order not found: {client_order_id}")

    def get_open_orders(self) -> list[OrderState]:
        self._ib.reqOpenOrders()
        closed = {"Filled", "Cancelled", "Inactive", "ApiCancelled"}
        return [
            self._to_order_state(t.order.orderRef or str(t.order.orderId), t)
            for t in self._ib.trades() if t.orderStatus.status not in closed
        ]

    def get_positions(self) -> list[Position]:
        return [
            Position(
                instrument=Instrument(
                    symbol=p.contract.symbol, exchange=p.contract.exchange,
                    currency=p.contract.currency, asset_class=p.contract.secType.lower(),
                ),
                qty=Decimal(str(p.position)),
                avg_cost=Decimal(str(p.avgCost)),
            )
            for p in self._ib.positions()
        ]

    def get_account_snapshot(self, currency: str = "USD") -> AccountSnapshot:
        vals = {v.tag: v.value for v in self._ib.accountValues() if v.currency == currency}
        return AccountSnapshot(
            cash=Decimal(vals.get("CashBalance", "0")),
            equity=Decimal(vals.get("NetLiquidation", "0")),
            margin_used=Decimal(vals.get("MaintMarginReq", "0")),
            currency=currency,
            timestamp=datetime.now(timezone.utc),
        )

    def _to_contract(self, instrument: Instrument):
        if instrument.asset_class == "stock":
            return Stock(instrument.symbol, instrument.exchange or "SMART", instrument.currency)
        if instrument.asset_class == "forex":
            base, quote = instrument.symbol.split("/")
            return Forex(base + quote)
        raise BrokerError(f"IBKR: unsupported asset_class: {instrument.asset_class}")

    def _to_ib_order(self, intent: OrderIntent):
        action = intent.side.value.upper()
        qty = float(intent.quantity)
        if intent.order_type.value == "market":
            return MarketOrder(action, qty)
        if intent.order_type.value == "limit":
            return LimitOrder(action, qty, float(intent.limit_price))
        raise BrokerError(f"IBKR: unsupported order_type: {intent.order_type}")

    @staticmethod
    def _to_order_state(client_order_id: str, trade) -> OrderState:
        status_map = {
            "Submitted": OrderStatus.SUBMITTED, "PreSubmitted": OrderStatus.SUBMITTED,
            "Filled": OrderStatus.FILLED, "PartiallyFilled": OrderStatus.PARTIAL,
            "Cancelled": OrderStatus.CANCELLED, "ApiCancelled": OrderStatus.CANCELLED,
            "Inactive": OrderStatus.REJECTED,
        }
        fills = trade.fills
        avg_price = None
        if fills:
            total = sum(f.execution.shares for f in fills)
            avg_price = Decimal(str(
                sum(f.execution.price * f.execution.shares for f in fills) / total
            ))
        # submitted_at aus Trade-Log (erster Eintrag) — nicht aus Abruf-Zeitpunkt
        submitted_at = (
            trade.log[0].time.replace(tzinfo=timezone.utc)
            if trade.log else datetime.now(timezone.utc)
        )
        return OrderState(
            client_order_id=client_order_id,
            broker_order_id=str(trade.order.orderId),
            status=status_map.get(trade.orderStatus.status, OrderStatus.PENDING),
            filled_qty=Decimal(str(trade.orderStatus.filled)),
            avg_fill_price=avg_price,
            submitted_at=submitted_at,
            last_updated=datetime.now(timezone.utc),
            broker_raw={"status": trade.orderStatus.status},
        )
```

---

## 10. PaperBrokerAdapter (`brokers/adapters/paper.py`)

Explizit getrennt von Live-Adaptern — kein `mode`-Flag im Service.

```python
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from trading_hub.brokers.port import BrokerPort
from trading_hub.domain.dtos import (
    AccountSnapshot, Instrument, OrderIntent, OrderState, OrderStatus, Position
)
from trading_hub.domain.exceptions import DuplicateOrderError


class PaperBrokerAdapter(BrokerPort):
    """Simulation ohne echten Broker. Für Tests und Paper-Trading."""

    def __init__(self):
        self._orders: dict[str, OrderState] = {}
        self._connected = False

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def resolve_instrument(self, instrument: Instrument) -> Instrument:
        return instrument  # Paper: kein Contract-Lookup nötig

    def place_order(self, intent: OrderIntent) -> OrderState:
        if intent.client_order_id in self._orders:
            raise DuplicateOrderError(intent.client_order_id)
        now = datetime.now(timezone.utc)
        state = OrderState(
            client_order_id=intent.client_order_id,
            broker_order_id=str(uuid.uuid4()),
            status=OrderStatus.FILLED,          # Paper: sofort filled
            filled_qty=intent.quantity,
            avg_fill_price=intent.limit_price,  # None bei Market-Order — Aufrufer nutzt price_at_signal
            submitted_at=now,
            last_updated=now,
        )
        self._orders[intent.client_order_id] = state
        return state

    def cancel_order(self, client_order_id: str) -> OrderState:
        state = self._orders[client_order_id]
        cancelled = OrderState(
            client_order_id=state.client_order_id,
            broker_order_id=state.broker_order_id,
            status=OrderStatus.CANCELLED,
            filled_qty=state.filled_qty,
            avg_fill_price=state.avg_fill_price,
            submitted_at=state.submitted_at,
            last_updated=datetime.now(timezone.utc),
        )
        self._orders[client_order_id] = cancelled
        return cancelled

    def get_order_state(self, client_order_id: str) -> OrderState:
        return self._orders[client_order_id]

    def get_open_orders(self) -> list[OrderState]:
        return [
            s for s in self._orders.values()
            if s.status not in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED)
        ]

    def get_positions(self) -> list[Position]:
        return []  # Paper: Positionen werden aus Trade-Aggregation berechnet

    def get_account_snapshot(self, currency: str = "USD") -> AccountSnapshot:
        return AccountSnapshot(
            cash=Decimal("100000"),
            equity=Decimal("100000"),
            margin_used=Decimal("0"),
            currency=currency,
            timestamp=datetime.now(timezone.utc),
        )
```

---

## 11. ExecutionService (`services/execution_service.py`)

`ExecutionService` ist **ausschließlich** für Order-Lifecycle zuständig. Signal-Lifecycle (`executed`-Flag) liegt im `SignalService`.

```python
import logging
import uuid
from decimal import Decimal

from django.db import transaction

from trading_hub.brokers.port import BrokerPort
from trading_hub.domain.dtos import Instrument, OrderIntent, OrderSide, OrderType
from trading_hub.domain.exceptions import BrokerError, DuplicateOrderError
from trading_hub.django.models import Trade, TradeStatus

logger = logging.getLogger("trading_hub.execution")


class ExecutionService:
    """Einziger Einstiegspunkt für Order-Execution. Broker-blind — kennt nur BrokerPort."""

    def __init__(self, broker: BrokerPort, tenant_id):
        self._broker = broker
        self._tenant_id = tenant_id

    def execute_signal(self, signal, quantity: Decimal) -> Trade | None:
        """Führt Signal aus. Signal-Lifecycle (executed-Flag) obliegt dem Aufrufer (SignalService)."""
        if signal.signal_type == "hold":
            return None

        pair = signal.trading_pair
        instrument = self._broker.resolve_instrument(Instrument(
            symbol=pair.symbol,
            exchange=pair.exchange_account.exchange,
            currency=pair.exchange_account.currency,
            asset_class=pair.asset_class,
        ))
        client_order_id = str(uuid.uuid4())
        intent = OrderIntent(
            instrument=instrument,
            side=OrderSide.BUY if signal.signal_type == "buy" else OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType.MARKET,
            client_order_id=client_order_id,
        )

        # Trade wird VOR dem Broker-Call persistiert (Idempotenz via unique constraint).
        # place_order() liegt bewusst AUßERHALB des atomic()-Blocks:
        # Broker-Calls dürfen keine DB-Transaction offen halten.
        with transaction.atomic():
            trade = Trade.objects.create(
                tenant_id=self._tenant_id,
                signal=signal,
                strategy=signal.strategy,
                trading_pair=pair,
                exchange_account=pair.exchange_account,
                side=intent.side.value,
                status=TradeStatus.OPEN,
                mode=pair.exchange_account.mode,
                quantity=quantity,
                entry_price=signal.price_at_signal,
                client_order_id=client_order_id,
            )

        try:
            order_state = self._broker.place_order(intent)
        except DuplicateOrderError:
            logger.error("Duplicate order prevented: %s", client_order_id)
            raise
        except BrokerError as exc:
            trade.status = TradeStatus.CANCELLED
            trade.metadata = {"error": str(exc)}
            trade.save(update_fields=["status", "metadata"])
            raise

        trade.broker_order_id = order_state.broker_order_id
        trade.entry_price = order_state.avg_fill_price or signal.price_at_signal
        trade.save(update_fields=["broker_order_id", "entry_price"])
        return trade

    def reconcile_open_orders(self) -> None:
        """Nach Reconnect: offene Orders dieses Tenants mit Broker abgleichen."""
        broker_orders = {o.client_order_id: o for o in self._broker.get_open_orders()}
        open_trades = Trade.objects.filter(
            tenant_id=self._tenant_id,          # Tenant-Scope — kein Cross-Tenant-Zugriff
            status=TradeStatus.OPEN,
            client_order_id__isnull=False,
        )
        for trade in open_trades:
            broker_state = broker_orders.get(trade.client_order_id)
            if broker_state is None:
                trade.status = TradeStatus.CANCELLED
                trade.save(update_fields=["status"])
            elif broker_state.status.value == "filled" and broker_state.avg_fill_price:
                trade.entry_price = broker_state.avg_fill_price
                trade.save(update_fields=["entry_price"])
```

## 11b. SignalService (`services/signal_service.py`)

Signal-Lifecycle ist **getrennt** vom ExecutionService:

```python
from trading_hub.django.models import Signal


class SignalService:
    """Verwaltet Signal-Lifecycle. Unabhängig von Broker-Execution."""

    @staticmethod
    def mark_executed(signal: Signal) -> None:
        signal.executed = True
        signal.save(update_fields=["executed"])
```

---

## 12. Adapter-Registry (`brokers/registry.py`)

```python
from django.conf import settings

from trading_hub.brokers.adapters.alpaca import AlpacaAdapter
from trading_hub.brokers.adapters.ccxt import CCXTAdapter
from trading_hub.brokers.adapters.ibkr import IBKRAdapter
from trading_hub.brokers.adapters.oanda import OANDAAdapter
from trading_hub.brokers.adapters.paper import PaperBrokerAdapter
from trading_hub.brokers.port import BrokerPort
from trading_hub.django.models import ExchangeAccount, TradingMode

_CCXT_EXCHANGES = frozenset({"binance", "coinbase", "kraken"})


def get_broker(account: ExchangeAccount) -> BrokerPort:
    if account.mode == TradingMode.PAPER:
        return PaperBrokerAdapter()

    exchange = account.exchange.lower()
    if exchange == "ibkr":
        return IBKRAdapter(
            host=getattr(settings, "IBKR_HOST", "127.0.0.1"),
            port=getattr(settings, "IBKR_PORT", 7497),
            client_id=getattr(settings, "IBKR_CLIENT_ID", 1),
        )
    if exchange in _CCXT_EXCHANGES:
        return CCXTAdapter(account)
    if exchange == "alpaca":
        return AlpacaAdapter(account)
    if exchange == "oanda":
        return OANDAAdapter(account)

    raise ValueError(f"Kein Adapter für Exchange: {account.exchange}")
```

---

## 13. Model-Erweiterungen (Migration)

Additive Migrationen — kein Breaking Change:

### 13.1 Trade-Model

```python
# Zwei neue Felder — ersetzen exchange_order_id
client_order_id = models.CharField(
    max_length=36,
    null=True, blank=True,
    unique=True,                    # DB-seitiger Idempotenz-Schutz (impliziert Index)
    help_text="UUID — Idempotenz-Schlüssel (einmalig pro Order)"
)
broker_order_id = models.CharField(
    max_length=100, blank=True,
    help_text="Broker-seitige Order-ID"
)
```

`exchange_order_id` → **depreciert**, entfernt in 2 Releases (ADR-022 Zero-Breaking-Changes).

`null=True` statt `default=""` — semantisch klar: `None` = noch nicht gesetzt, leerer String ist kein valider Sentinel.
`unique=True` — DB-Constraint verhindert Duplicate-Orders auch bei Race Conditions.

### 13.2 TradingPair-Model

```python
# broker_symbol cachen — verhindert wiederholte IBKR-Contract-Abfragen
broker_symbol = models.CharField(
    max_length=50, blank=True,
    help_text="Broker-spezifisches Symbol nach resolve_instrument() — gecacht"
)
broker_symbol_updated_at = models.DateTimeField(
    null=True, blank=True,
    help_text="Zeitpunkt der letzten broker_symbol-Auflösung (UTC)"
)
```

`resolve_instrument()` schreibt `broker_symbol` zurück auf `TradingPair` (TTL: 24h). Kein erneuter IBKR-Contract-Lookup bei jedem Neustart.

### 13.3 Portfolio-Model — AccountSnapshot-Persistenz

Das bestehende `Portfolio`-Model (`cash_balance`, `total_value`, `unrealized_pnl`) wird als Persistenzschicht für `AccountSnapshot` genutzt:

```python
# Zwei neue Felder auf Portfolio
margin_used = models.DecimalField(
    max_digits=14, decimal_places=2, default=Decimal("0"),
    help_text="Aktuell gebundene Margin (vom Broker)"
)
last_synced_at = models.DateTimeField(
    null=True, blank=True,
    help_text="Zeitpunkt des letzten AccountSnapshot-Syncs (UTC)"
)
```

`PortfolioSyncService.sync(account)` ruft `get_account_snapshot()` auf und schreibt Ergebnisse in `Portfolio` — **nicht** der `ExecutionService`.

### 13.4 Position-Persistenz

Positionen werden **nicht** als separates Model eingeführt (bereits in `Trade`-Aggregation ableitbar). `get_positions()` dient ausschließlich der Reconciliation — kein eigenes Persistenzmodell nötig.

---

## 14. IBKR-Fallen und Lösungen

| Problem | Lösung |
| --- | --- |
| Reconnect / Session Drops | `connect()` idempotent; `reconcile_open_orders()` nach Reconnect |
| Market Data Limits | Separater `MarketDataService` mit Caching — nicht im Adapter |
| Contract-Auflösung komplex | `resolve_instrument()` im Adapter, `broker_symbol` in DB cachen |
| Order-Status asynchron | Event-getrieben via `ib_insync` Callbacks; kein "sende und vergiss" |
| Rate Limits | `RateLimitError` im Adapter, Retry-Logik im Celery-Task |
| Partial Fills | `OrderStatus.PARTIAL` explizit, `filled_qty` in `OrderState` |
| Duplicate Orders bei Reconnect | `client_order_id` als `orderRef` — IBKR erkennt Duplikate |

---

## 15. Phasenplan

### Phase A — Spike (experimentell, ~2 Tage)

| Schritt | Aufgabe |
| --- | --- |
| A.1 | IB Gateway (Paper) aufsetzen, Port 7497 |
| A.2 | `scripts/ibkr_spike.py`: connect → resolve → market data → limit order → cancel |
| A.3 | IBKR-Fallen dokumentieren (Reconnect, Rate Limits, Contract-Details) |

Deliverable: Spike-Script, wegwerfbar. Nicht produktionsreif.

### Phase B — Produktionskritisch (~4 Tage)

| Schritt | Aufgabe | Aufwand |
| --- | --- | --- |
| B.1 | `domain/dtos.py` + `domain/exceptions.py` | 1h |
| B.2 | `brokers/port.py` (BrokerPort ABC) | 0.5h |
| B.3 | `brokers/adapters/paper.py` + Tests | 1h |
| B.4 | `brokers/adapters/ibkr.py` + Tests (Paper Trading) | 4h |
| B.5 | `services/execution_service.py` + Tests | 3h |
| B.6 | `brokers/registry.py` + Migration (client_order_id) | 1h |
| B.7 | `order_manager.py` deprecieren, Deprecation-Warning hinzufügen | 0.5h |
| B.8 | CCXT/Alpaca/OANDA in eigene Adapter-Klassen extrahieren | 3h |
| **Gesamt** | | **~14h (~2 Tage)** |

---

## 16. Risiken

| ID | Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-1 | IB Gateway Reconnect-Loops | Mittel | Hoch | Exponential Backoff + Circuit Breaker im Celery-Task |
| R-2 | `ib_insync` async/sync Konflikte mit Django | Mittel | Mittel | Adapter in eigenem Thread/Prozess (Celery Worker) |
| R-3 | IBKR Contract-Details-Caching veraltet | Niedrig | Mittel | TTL-Cache mit täglichem Refresh |
| R-4 | Partial Fill nicht erkannt | Niedrig | Hoch | `OrderStatus.PARTIAL` explizit, Polling via Celery Beat |

---

## 17. Konsequenzen

### Positiv
- `ExecutionService` ist vollständig broker-blind und unit-testbar via `PaperBrokerAdapter`
- Neuer Broker = neue Adapter-Klasse, kein Eingriff in bestehenden Code
- Idempotenz via DB-`unique=True` auf `client_order_id` — Race Conditions ausgeschlossen
- Signal-Lifecycle und Order-Lifecycle sind sauber getrennt
- `broker_symbol`-Caching auf `TradingPair` eliminiert wiederholte IBKR-Contract-Lookups

### Negativ / Trade-offs
- `IBKRAdapter` läuft synchron via `ib_insync` — muss in Celery-Worker isoliert werden (kein Django-Request-Kontext)
- `PaperBrokerAdapter` hält Orders In-Memory — kein Persistenz-Audit für Paper-Trades (bewusste Vereinfachung)
- Migration auf `client_order_id unique=True` erfordert Datenmigration für bestehende `Trade`-Rows (NULL setzen)

### Nicht entschieden
- WebSocket-basiertes Order-Status-Streaming (Phase C)
- Multi-Account-Support pro Tenant (Phase C)
