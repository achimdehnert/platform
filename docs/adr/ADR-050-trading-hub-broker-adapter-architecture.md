# ADR-050: Trading Hub — Broker-Adapter-Architektur

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-050 |
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

## 2. Entscheidung: Port-Adapter-Pattern

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

## 3. Verzeichnisstruktur

```
trading_hub/
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
    └── order_manager.py     # DEPRECATED (entfernt in 2 Releases)
```

---

## 4. Domain-DTOs (`domain/dtos.py`)

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
    broker_symbol: str = ""  # nach resolve_instrument()


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

## 5. Exception-Hierarchie (`domain/exceptions.py`)

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

## 6. BrokerPort (`brokers/port.py`)

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
    def get_account_snapshot(self) -> AccountSnapshot: ...
```

---

## 7. IBKRAdapter (`brokers/adapters/ibkr.py`)

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
    BrokerConnectionError, BrokerError, DuplicateOrderError,
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
        self._known_order_ids: set[str] = set()

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
        if intent.client_order_id in self._known_order_ids:
            raise DuplicateOrderError(intent.client_order_id)
        ib_order = self._to_ib_order(intent)
        ib_order.orderRef = intent.client_order_id
        trade = self._ib.placeOrder(self._to_contract(intent.instrument), ib_order)
        self._ib.sleep(0.5)
        if trade.orderStatus.status in ("Inactive", "ApiCancelled"):
            raise OrderRejectedError(f"{intent.client_order_id}: {trade.orderStatus.status}")
        self._known_order_ids.add(intent.client_order_id)
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

    def get_account_snapshot(self) -> AccountSnapshot:
        vals = {v.tag: v.value for v in self._ib.accountValues() if v.currency == "USD"}
        return AccountSnapshot(
            cash=Decimal(vals.get("CashBalance", "0")),
            equity=Decimal(vals.get("NetLiquidation", "0")),
            margin_used=Decimal(vals.get("MaintMarginReq", "0")),
            currency="USD",
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
        return OrderState(
            client_order_id=client_order_id,
            broker_order_id=str(trade.order.orderId),
            status=status_map.get(trade.orderStatus.status, OrderStatus.PENDING),
            filled_qty=Decimal(str(trade.orderStatus.filled)),
            avg_fill_price=avg_price,
            submitted_at=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            broker_raw={"status": trade.orderStatus.status},
        )
```

---

## 8. ExecutionService (`services/execution_service.py`)

```python
import logging
import uuid
from decimal import Decimal

from django.db import transaction

from trading_hub.brokers.port import BrokerPort
from trading_hub.domain.dtos import Instrument, OrderIntent, OrderSide, OrderType
from trading_hub.domain.exceptions import BrokerError, DuplicateOrderError
from trading_hub.django.models import Signal, Trade, TradeStatus

logger = logging.getLogger("trading_hub.execution")


class ExecutionService:
    """Einziger Einstiegspunkt. Broker-blind — kennt nur BrokerPort."""

    def __init__(self, broker: BrokerPort):
        self._broker = broker

    def execute_signal(self, signal: Signal, quantity: Decimal) -> Trade | None:
        if signal.signal_type == "hold":
            return None

        instrument = self._broker.resolve_instrument(Instrument(
            symbol=signal.trading_pair.symbol,
            exchange=signal.trading_pair.exchange_account.exchange,
            currency=signal.trading_pair.exchange_account.currency,
            asset_class=signal.trading_pair.asset_class,
        ))
        client_order_id = str(uuid.uuid4())
        intent = OrderIntent(
            instrument=instrument,
            side=OrderSide.BUY if signal.signal_type == "buy" else OrderSide.SELL,
            quantity=quantity,
            order_type=OrderType.MARKET,
            client_order_id=client_order_id,
        )

        with transaction.atomic():
            trade = Trade.objects.create(
                tenant_id=signal.tenant_id,
                signal=signal,
                strategy=signal.strategy,
                trading_pair=signal.trading_pair,
                exchange_account=signal.trading_pair.exchange_account,
                side=intent.side.value,
                status=TradeStatus.OPEN,
                mode=signal.trading_pair.exchange_account.mode,
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
        signal.executed = True
        signal.save(update_fields=["executed"])
        return trade

    def reconcile_open_orders(self) -> None:
        """Nach Reconnect: offene Orders mit Broker abgleichen."""
        broker_orders = {o.client_order_id: o for o in self._broker.get_open_orders()}
        for trade in Trade.objects.filter(status=TradeStatus.OPEN).exclude(client_order_id=""):
            broker_state = broker_orders.get(trade.client_order_id)
            if broker_state is None:
                trade.status = TradeStatus.CANCELLED
                trade.save(update_fields=["status"])
            elif broker_state.status.value == "filled" and broker_state.avg_fill_price:
                trade.entry_price = broker_state.avg_fill_price
                trade.save(update_fields=["entry_price"])
```

---

## 9. Adapter-Registry (`brokers/registry.py`)

```python
from trading_hub.brokers.port import BrokerPort
from trading_hub.django.models import ExchangeAccount, TradingMode


def get_broker(account: ExchangeAccount) -> BrokerPort:
    if account.mode == TradingMode.PAPER:
        from trading_hub.brokers.adapters.paper import PaperBrokerAdapter
        return PaperBrokerAdapter()

    exchange = account.exchange.lower()
    if exchange == "ibkr":
        from django.conf import settings
        from trading_hub.brokers.adapters.ibkr import IBKRAdapter
        return IBKRAdapter(
            host=getattr(settings, "IBKR_HOST", "127.0.0.1"),
            port=getattr(settings, "IBKR_PORT", 7497),
            client_id=getattr(settings, "IBKR_CLIENT_ID", 1),
        )
    if exchange in ("binance", "coinbase", "kraken"):
        from trading_hub.brokers.adapters.ccxt import CCXTAdapter
        return CCXTAdapter(account)
    if exchange == "alpaca":
        from trading_hub.brokers.adapters.alpaca import AlpacaAdapter
        return AlpacaAdapter(account)
    if exchange == "oanda":
        from trading_hub.brokers.adapters.oanda import OANDAAdapter
        return OANDAAdapter(account)

    raise ValueError(f"Kein Adapter für Exchange: {account.exchange}")
```

---

## 10. Model-Erweiterung (Migration)

Additive Migration — kein Breaking Change:

```python
# Trade-Model: zwei neue Felder
client_order_id = models.CharField(
    max_length=36, db_index=True, blank=True, default="",
    help_text="UUID für Idempotenz-Schutz"
)
broker_order_id = models.CharField(
    max_length=100, blank=True,
    help_text="Broker-seitige Order-ID"
)
```

`exchange_order_id` → **depreciert**, entfernt in 2 Releases (ADR-022 Zero-Breaking-Changes).

---

## 11. IBKR-Fallen und Lösungen

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

## 12. Phasenplan

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

## 13. Risiken

| ID | Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-1 | IB Gateway Reconnect-Loops | Mittel | Hoch | Exponential Backoff + Circuit Breaker im Celery-Task |
| R-2 | `ib_insync` async/sync Konflikte mit Django | Mittel | Mittel | Adapter in eigenem Thread/Prozess (Celery Worker) |
| R-3 | IBKR Contract-Details-Caching veraltet | Niedrig | Mittel | TTL-Cache mit täglichem Refresh |
| R-4 | Partial Fill nicht erkannt | Niedrig | Hoch | `OrderStatus.PARTIAL` explizit, Polling via Celery Beat |
