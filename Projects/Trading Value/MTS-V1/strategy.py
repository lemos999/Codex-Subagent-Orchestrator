from __future__ import annotations

import argparse
import json
import logging
import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Protocol, cast

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on local environment
    yaml = None  # type: ignore[assignment]


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"
DEFAULT_STATE_DIR = ROOT_DIR / "state"
DEFAULT_BACKTEST_CACHE_DIR = ROOT_DIR.parent / "predictive_runner_paper" / "cache_180d"
DEFAULT_BACKTEST_OUTPUT_PATH = ROOT_DIR / "logs" / "trades_mtsv1_offline_90d.jsonl"
DEFAULT_BACKTEST_DAYS = 90
ENTRY_PROFILE_LOOKBACK = 500
ENTRY_PROFILE_BINS = 50
VALUE_AREA_RATIO = 0.70
PIVOT_LENGTH = 2
PIVOT_FALLBACK_WINDOW = 100
BASE_SIZING_FRAME = 0.05
PROMOTED_SIZING_FRAME = 0.10
L1_WEIGHT = 0.33
L2_WEIGHT = 0.33
L3_WEIGHT = 0.34
TRIPLE_CONFLUENCE_ATR_RATIO = 0.20
EVASION_PEAK_ATR_RATIO = 0.10
STATE_1_TIMEOUT_BARS = 48
EVASION_WINDOW_HOURS = 48.0


class StrategyMode(str, Enum):
    BACKTEST = "backtest"
    PAPER = "paper"
    INDICATOR_CHECK = "indicator-check"


class StateCode(IntEnum):
    FLAT = 0
    IDLE = 0
    PENDING = 1
    L1_FILLED = 1
    FILLED_PARTIAL = 2
    L2_FILLED = 2
    FILLED_FULL = 3
    L3_FILLED = 3
    RUNNER = 4
    EVASION = 5


class SubState(str, Enum):
    A = "A"
    AB = "AB"


class TradeSide(str, Enum):
    LONG = "long"
    SHORT = "short"


class OrderIntent(str, Enum):
    TRANSITION = "transition"
    PLACE = "place"
    CANCEL = "cancel"
    CLOSE_MARKET = "close_market"


class MakerOrderRejected(RuntimeError):
    """Raised when a post-only order would cross the book as a taker order."""


class ExchangeReconciliationClient(Protocol):
    def fetch_positions(self, symbols: list[str]) -> list[dict[str, Any]]:
        ...

    def fetch_open_orders(self, symbol: str) -> list[dict[str, Any]]:
        ...


CreateOrderFn = Callable[[dict[str, Any]], dict[str, Any]]


@dataclass(slots=True)
class TimeframeConfig:
    htf: str
    entry_tf: str
    ltf: str


@dataclass(slots=True)
class RiskConfig:
    daily_max_loss_pct: float
    symbol_cooldown_hours: int


@dataclass(slots=True)
class AppConfig:
    strategy: str
    version: str
    exchange: str
    quote_asset: str
    contract_type: str
    symbols: list[str]
    timeframes: TimeframeConfig
    risk: RiskConfig
    user_leverage: int
    use_runner: bool
    mmr: dict[str, float | None]

    @classmethod
    def from_mapping(cls, raw: dict[str, Any]) -> "AppConfig":
        timeframes_raw = _as_mapping(raw.get("timeframes"), field_name="timeframes")
        risk_raw = _as_mapping(raw.get("risk"), field_name="risk")
        mmr_raw = _as_mapping(raw.get("mmr"), field_name="mmr")

        return cls(
            strategy=str(raw.get("strategy", "MTS-V1")),
            version=str(raw.get("version", "v5.2")),
            exchange=str(raw.get("exchange", "binanceusdm")),
            quote_asset=str(raw.get("quote_asset", "USDT")),
            contract_type=str(raw.get("contract_type", "perpetual")),
            symbols=[str(symbol) for symbol in raw.get("symbols", [])],
            timeframes=TimeframeConfig(
                htf=str(timeframes_raw.get("htf", "4h")),
                entry_tf=str(timeframes_raw.get("entry_tf", "1h")),
                ltf=str(timeframes_raw.get("ltf", "15m")),
            ),
            risk=RiskConfig(
                daily_max_loss_pct=float(risk_raw.get("daily_max_loss_pct", 5)),
                symbol_cooldown_hours=int(risk_raw.get("symbol_cooldown_hours", 24)),
            ),
            user_leverage=int(raw.get("user_leverage", 10)),
            use_runner=bool(raw.get("use_runner", True)),
            mmr={
                str(symbol): None if value is None else float(value)
                for symbol, value in mmr_raw.items()
            },
        )


@dataclass(slots=True)
class StrategyStateSnapshot:
    strategy: str = "MTS-V1"
    version: str = "v5.2"
    symbol: str = ""
    state: int = int(StateCode.FLAT)
    sub_state: str | None = None
    side: str | None = None
    avg_entry: float = 0.0
    hard_sl: float = 0.0
    remaining_position_fraction: float = 0.0
    entry_prices: dict[str, float | None] = field(
        default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": None}
    )
    fill_qtys: dict[str, float] = field(
        default_factory=lambda: {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    )
    triple_confluence: bool = False
    triple_confluence_evaluated: bool = False
    sizing_frame: float = BASE_SIZING_FRAME
    entry_started_bar: int | None = None
    first_fill_ts: str | None = None
    last_tp_bar_id: int | None = None
    cooldown_until: str | None = None
    client_order_ids: dict[str, str | None] = field(
        default_factory=lambda: {"L1": None, "L2": None, "L3": None, "HARD_SL": None}
    )
    cvd_daily_start: str = ""
    created_ts: str = ""
    updated_ts: str = ""

    def to_mapping(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(slots=True, frozen=True)
class IchimokuValues:
    tenkan: float
    kijun: float
    senkou_b: float


@dataclass(slots=True, frozen=True)
class VolumeProfile:
    poc: float
    vah: float
    val: float
    window_low: float
    window_high: float
    bin_size: float


@dataclass(slots=True, frozen=True)
class FiboAnchor:
    pivot_low: float
    pivot_high: float
    low_index: int
    high_index: int
    pivot_low_ts: int | None
    pivot_high_ts: int | None


@dataclass(slots=True, frozen=True)
class LayeredEntryPrices:
    l1: float
    l2: float
    l3: float


@dataclass(slots=True, frozen=True)
class EntrySignalBar:
    close: float
    kijun: float


@dataclass(slots=True, frozen=True)
class TakeProfitInputs:
    price: float
    rsi: float
    kijun_series: Sequence[float]
    fibo_1_0: float
    fibo_1_5: float
    volume: float
    volume_sma_20: float
    use_runner: bool
    bar_id: int | None = None


@dataclass(slots=True, frozen=True)
class RunnerInputs:
    close_prev: float
    open_cur: float
    kijun_prev: float
    kijun_cur: float


@dataclass(slots=True, frozen=True)
class LayerOrder:
    layer: str
    side: TradeSide
    price: float
    equity_fraction: float
    client_order_id: str


@dataclass(slots=True, frozen=True)
class HardStopOrder:
    side: TradeSide
    stop_price: float
    client_order_id: str


@dataclass(slots=True, frozen=True)
class StateAction:
    intent: OrderIntent
    reason: str
    state_from: int
    state_to: int
    layer: str | None = None
    order: LayerOrder | None = None
    stop_order: HardStopOrder | None = None
    cancel_order_ids: tuple[str, ...] = ()


def _snapshot_side(snapshot: StrategyStateSnapshot) -> TradeSide:
    if snapshot.side == TradeSide.SHORT.value:
        return TradeSide.SHORT
    return TradeSide.LONG


def _opposite_trade_side(side: TradeSide) -> TradeSide:
    return TradeSide.SHORT if side == TradeSide.LONG else TradeSide.LONG


def _reset_snapshot_flat(snapshot: StrategyStateSnapshot, *, keep_cooldown: bool) -> None:
    cooldown_until = snapshot.cooldown_until if keep_cooldown else None
    snapshot.state = int(StateCode.IDLE)
    snapshot.sub_state = None
    snapshot.side = None
    snapshot.avg_entry = 0.0
    snapshot.hard_sl = 0.0
    snapshot.remaining_position_fraction = 0.0
    snapshot.entry_prices = {"L1": 0.0, "L2": 0.0, "L3": None}
    snapshot.fill_qtys = {"L1": 0.0, "L2": 0.0, "L3": 0.0}
    snapshot.triple_confluence = False
    snapshot.triple_confluence_evaluated = False
    snapshot.sizing_frame = BASE_SIZING_FRAME
    snapshot.entry_started_bar = None
    snapshot.first_fill_ts = None
    snapshot.last_tp_bar_id = None
    snapshot.client_order_ids = {"L1": None, "L2": None, "L3": None, "HARD_SL": None}
    snapshot.cooldown_until = cooldown_until


class TPEvaluator:
    @staticmethod
    def evaluate_a(
        rsi_value: float,
        kijun_series: Sequence[float],
        side: TradeSide = TradeSide.LONG,
    ) -> bool:
        _require_length(kijun_series, 3, "kijun_series")
        recent_slope = kijun_series[-1] - kijun_series[-2]
        previous_slope = kijun_series[-2] - kijun_series[-3]
        if side == TradeSide.LONG:
            return rsi_value < 55.0 and recent_slope <= 0.0 and previous_slope <= 0.0
        return (
            rsi_value > 45.0
            and recent_slope >= 0.0
            and previous_slope >= 0.0
        )

    @staticmethod
    def evaluate_b(price: float, fibo_1_0: float, side: TradeSide = TradeSide.LONG) -> bool:
        if side == TradeSide.LONG:
            return price >= fibo_1_0
        return price <= fibo_1_0

    @staticmethod
    def evaluate_c(
        price: float,
        fibo_1_5: float,
        volume: float,
        volume_sma_20: float,
        side: TradeSide = TradeSide.LONG,
    ) -> bool:
        price_hit = price >= fibo_1_5 if side == TradeSide.LONG else price <= fibo_1_5
        return price_hit and volume > (volume_sma_20 * 1.5)


class RunnerHandler:
    def __init__(
        self,
        snapshot: StrategyStateSnapshot,
        *,
        now_fn: Callable[[], datetime],
        client_order_id_fn: Callable[[str, int, int], str],
    ) -> None:
        self.snapshot = snapshot
        self._now_fn = now_fn
        self._client_order_id_fn = client_order_id_fn

    @staticmethod
    def check_kijun_break(
        close_prev: float,
        open_cur: float,
        kijun_prev: float,
        kijun_cur: float,
        side: TradeSide = TradeSide.LONG,
    ) -> bool:
        if side == TradeSide.LONG:
            return close_prev < kijun_prev and open_cur < kijun_cur
        return close_prev > kijun_prev and open_cur > kijun_cur

    def on_kijun_break(self) -> StateAction | None:
        if self.snapshot.state != int(StateCode.RUNNER):
            return None

        previous_state = self.snapshot.state
        close_fraction = self.snapshot.remaining_position_fraction
        close_side = _opposite_trade_side(_snapshot_side(self.snapshot))
        self.snapshot.cooldown_until = (self._now_fn() + timedelta(hours=24)).isoformat()
        _reset_snapshot_flat(self.snapshot, keep_cooldown=True)
        return StateAction(
            intent=OrderIntent.CLOSE_MARKET,
            reason="RUNNER_KIJUN_BREAK",
            state_from=previous_state,
            state_to=int(StateCode.IDLE),
            layer="RUNNER",
            order=LayerOrder(
                layer="RUNNER_EXIT",
                side=close_side,
                price=0.0,
                equity_fraction=close_fraction,
                client_order_id=self._client_order_id_fn(
                    "RUNNER",
                    previous_state,
                    int(StateCode.IDLE),
                ),
            ),
        )


@dataclass(slots=True, frozen=True)
class Position:
    side: TradeSide
    entry_prices: dict[str, float | None]
    fill_qtys: dict[str, float]

    def compute_avg_entry(self) -> float:
        numerator = 0.0
        denominator = 0.0
        for layer, qty in self.fill_qtys.items():
            price = self.entry_prices.get(layer)
            if price is None or qty <= 0.0:
                continue
            numerator += price * qty
            denominator += qty
        return numerator / denominator if denominator > 0.0 else 0.0

    def compute_hard_sl(self, atr_entry_tf: float) -> float:
        avg_entry = self.compute_avg_entry()
        if self.side == TradeSide.LONG:
            return avg_entry - (2.0 * atr_entry_tf)
        return avg_entry + (2.0 * atr_entry_tf)


@dataclass(slots=True, frozen=True)
class CvdTrade:
    timestamp: datetime
    quantity: float
    is_buyer_maker: bool


@dataclass(slots=True)
class CvdTradeAccumulator:
    current_day: date | None = None
    cumulative_delta: float = 0.0
    current_bar_delta: float = 0.0

    def ingest(self, trade: CvdTrade) -> float:
        trade_day = _utc_day(trade.timestamp)
        if trade_day != self.current_day:
            self.current_day = trade_day
            self.cumulative_delta = 0.0
            self.current_bar_delta = 0.0

        delta = trade.quantity if not trade.is_buyer_maker else -trade.quantity
        self.cumulative_delta += delta
        self.current_bar_delta += delta
        return delta

    def close_bar(self) -> float:
        delta = self.current_bar_delta
        self.current_bar_delta = 0.0
        return delta


@dataclass(slots=True, frozen=True)
class Phase2IndicatorSnapshot:
    atr_14: float
    tenkan_9: float
    kijun_26: float
    senkou_b_52: float
    poc: float
    vah: float
    val: float
    pivot_low: float
    pivot_high: float
    fibo_0618: float
    fibo_0786: float
    fibo_1000: float
    fibo_1500: float
    rsi_14: float
    volume_sma_20: float
    btc_ema_50: float
    cvd_proxy: float
    cvd_trade_delta: float
    cvd_abs_sma_20: float
    cvd_spike: bool
    reverse_spike_long: bool
    reverse_spike_short: bool


@dataclass(slots=True, frozen=True)
class ParityRow:
    indicator: str
    python_value: float
    pine_value: float
    basis: str

    @property
    def match_3dp(self) -> bool:
        return round(self.python_value, 3) == round(self.pine_value, 3)


@dataclass(slots=True, frozen=True)
class Phase2SampleData:
    entry_candles: list[Candle]
    btc_htf_candles: list[Candle]
    cvd_trade_deltas: list[float]


def _as_mapping(value: Any, *, field_name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping.")
    return value


def _require_length(values: Sequence[Any], minimum: int, label: str) -> None:
    if len(values) < minimum:
        raise ValueError(f"{label} requires at least {minimum} values.")


def _utc_day(timestamp: datetime) -> date:
    return timestamp.astimezone(UTC).date()


def _ensure_positive_integer(value: int, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} must be positive.")


def _window_or_tail(candles: Sequence[Candle], limit: int) -> list[Candle]:
    if limit <= 0:
        raise ValueError("limit must be positive.")
    if len(candles) <= limit:
        return list(candles)
    return list(candles[-limit:])


def _float_range(value: float) -> float:
    return value if not math.isclose(value, 0.0) else 1.0


def load_config(path: Path) -> AppConfig:
    if yaml is None:
        raise RuntimeError("PyYAML is required to load config.yaml.")

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise ValueError("config.yaml must contain a top-level mapping.")

    config = AppConfig.from_mapping(raw)
    validate_config(config)
    return config


def validate_config(config: AppConfig) -> None:
    if config.strategy != "MTS-V1":
        raise ValueError("strategy must remain MTS-V1.")
    if not config.symbols:
        raise ValueError("At least one symbol must be configured.")
    missing_mmr = [symbol for symbol in config.symbols if symbol not in config.mmr]
    if missing_mmr:
        raise ValueError(f"Missing mmr entries for symbols: {', '.join(missing_mmr)}")


def symbol_to_state_path(symbol: str, state_dir: Path) -> Path:
    slug = PersistenceManager.symbol_slug(symbol).lower()
    return state_dir / f"state_{slug}.json"


def default_state(symbol: str, now_iso: str) -> StrategyStateSnapshot:
    return StrategyStateSnapshot(
        symbol=symbol,
        cvd_daily_start=now_iso,
        created_ts=now_iso,
        updated_ts=now_iso,
    )


def load_state(path: Path) -> StrategyStateSnapshot | None:
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ValueError(f"State file {path} must contain a JSON object.")

    snapshot = StrategyStateSnapshot()
    for field_name in snapshot.to_mapping():
        if field_name in raw:
            setattr(snapshot, field_name, raw[field_name])
    return snapshot


def save_state(path: Path, snapshot: StrategyStateSnapshot) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(snapshot.to_mapping(), handle, indent=2)
        handle.write("\n")


class PersistenceManager:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir

    @staticmethod
    def symbol_slug(symbol: str) -> str:
        return symbol.replace("/", "_").replace(":", "_").upper()

    def state_path(self, symbol: str) -> Path:
        return self.state_dir / f"state_{self.symbol_slug(symbol)}.json"

    def save_state(self, symbol: str, state_dict: dict[str, Any]) -> Path:
        path = self.state_path(symbol)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(state_dict, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
        return path

    def load_state(self, symbol: str) -> dict[str, Any] | None:
        path = self.state_path(symbol)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, dict):
            raise ValueError(f"State file {path} must contain a JSON object.")
        return cast(dict[str, Any], raw)


class TradeLogger:
    NULLABLE_FIELDS = (
        "runner_exit_price",
        "runner_exit_ts",
        "evasion_reason",
        "hard_sl_price",
    )

    def __init__(
        self,
        logs_dir: Path,
        *,
        now_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.logs_dir = logs_dir
        self._now_fn = now_fn or (lambda: datetime.now(UTC))

    def append(self, event_dict: dict[str, Any]) -> Path:
        event = dict(event_dict)
        for field_name in self.NULLABLE_FIELDS:
            if event.get(field_name, None) == "":
                event[field_name] = None
            else:
                event.setdefault(field_name, None)

        ts = self._event_timestamp(event)
        event.setdefault("ts", ts.isoformat())
        path = self.logs_dir / f"trades_{ts.date().isoformat()}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            json.dump(event, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
        return path

    def _event_timestamp(self, event: dict[str, Any]) -> datetime:
        raw_ts = event.get("ts")
        if isinstance(raw_ts, str) and raw_ts:
            parsed = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        return self._now_fn()


class OrderManager:
    def __init__(self, *, now_fn: Callable[[], datetime] | None = None) -> None:
        self._now_fn = now_fn or (lambda: datetime.now(UTC))

    def client_order_id(
        self,
        *,
        symbol: str,
        state_from: int,
        state_to: int,
        ts_ms: int | None = None,
    ) -> str:
        timestamp_ms = ts_ms if ts_ms is not None else int(self._now_fn().timestamp() * 1000)
        slug = PersistenceManager.symbol_slug(symbol)
        return f"mtsv1_{slug}_{state_from}{state_to}_{timestamp_ms}"

    def place_post_only_with_retry(
        self,
        create_order_fn: CreateOrderFn,
        *,
        symbol: str,
        side: TradeSide,
        amount: float,
        price: float,
        tick_size: float,
        state_from: int,
        state_to: int,
        max_attempts: int = 3,
    ) -> dict[str, Any]:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")
        if amount <= 0.0:
            raise ValueError("amount must be positive.")
        if tick_size <= 0.0:
            raise ValueError("tick_size must be positive.")

        attempt_price = price
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            request = {
                "symbol": symbol,
                "side": side.value,
                "amount": amount,
                "price": attempt_price,
                "params": {
                    "postOnly": True,
                    "clientOrderId": self.client_order_id(
                        symbol=symbol,
                        state_from=state_from,
                        state_to=state_to,
                    ),
                },
                "attempt": attempt + 1,
            }
            try:
                return create_order_fn(request)
            except Exception as exc:
                if not self._is_maker_rejection(exc):
                    raise
                last_error = exc
                attempt_price = self._next_passive_price(
                    side=side,
                    price=attempt_price,
                    tick_size=tick_size,
                )

        raise MakerOrderRejected(
            f"post-only maker order rejected after {max_attempts} attempts"
        ) from last_error

    @staticmethod
    def _next_passive_price(*, side: TradeSide, price: float, tick_size: float) -> float:
        if side == TradeSide.LONG:
            return price - tick_size
        return price + tick_size

    @staticmethod
    def _is_maker_rejection(exc: Exception) -> bool:
        if isinstance(exc, MakerOrderRejected):
            return True
        message = str(exc).lower()
        return any(token in message for token in ("post-only", "post only", "maker", "taker"))


class StartupReconciliation:
    def __init__(
        self,
        persistence: PersistenceManager,
        exchange: ExchangeReconciliationClient,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self.persistence = persistence
        self.exchange = exchange
        self.logger = logger or logging.getLogger(__name__)

    def reconcile_symbol(self, symbol: str) -> int:
        state = self.persistence.load_state(symbol)
        if state is None:
            return 0

        positions = self.exchange.fetch_positions([symbol])
        open_orders = self.exchange.fetch_open_orders(symbol)
        mismatches = self._find_mismatches(state, positions, open_orders)
        if not mismatches:
            return 0

        self.logger.warning(
            "Startup reconciliation mismatch for %s: %s. Manual intervention required.",
            symbol,
            "; ".join(mismatches),
        )
        return 2

    def _find_mismatches(
        self,
        state: dict[str, Any],
        positions: list[dict[str, Any]],
        open_orders: list[dict[str, Any]],
    ) -> list[str]:
        mismatches: list[str] = []
        state_code = int(state.get("state", int(StateCode.IDLE)))
        state_has_position = state_code in {
            int(StateCode.FILLED_PARTIAL),
            int(StateCode.FILLED_FULL),
            int(StateCode.RUNNER),
        }
        exchange_open = any(self._position_is_open(position) for position in positions)
        if state_has_position != exchange_open:
            mismatches.append(
                f"position state_has_position={state_has_position} exchange_open={exchange_open}"
            )

        state_order_ids = self._expected_open_order_ids(state)
        exchange_order_ids = {
            str(order.get("clientOrderId") or order.get("client_order_id"))
            for order in open_orders
            if order.get("clientOrderId") or order.get("client_order_id")
        }
        missing_orders = state_order_ids - exchange_order_ids
        if missing_orders:
            mismatches.append(f"missing open order ids={sorted(missing_orders)}")
        extra_orders = exchange_order_ids - state_order_ids
        if extra_orders:
            mismatches.append(f"extra open order ids={sorted(extra_orders)}")
        return mismatches

    @staticmethod
    def _position_is_open(position: dict[str, Any]) -> bool:
        for field_name in ("contracts", "size", "positionAmt"):
            raw_value = position.get(field_name)
            if raw_value is None:
                continue
            try:
                if not math.isclose(float(raw_value), 0.0):
                    return True
            except (TypeError, ValueError):
                continue
        return False

    @staticmethod
    def _expected_open_order_ids(state: dict[str, Any]) -> set[str]:
        state_code = int(state.get("state", int(StateCode.IDLE)))
        client_order_ids = _as_mapping(
            state.get("client_order_ids"),
            field_name="client_order_ids",
        )
        open_layers_by_state = {
            int(StateCode.PENDING): {"L1"},
            int(StateCode.FILLED_PARTIAL): {"L2", "L3", "HARD_SL"},
            int(StateCode.FILLED_FULL): {"HARD_SL"},
        }
        open_layers = open_layers_by_state.get(state_code, set())
        return {
            str(value)
            for layer, value in client_order_ids.items()
            if layer in open_layers and value
        }


def sma(values: Sequence[float], length: int) -> float:
    _ensure_positive_integer(length, "length")
    _require_length(values, length, "sma")
    window = values[-length:]
    return sum(window) / float(length)


def rma(values: Sequence[float], length: int) -> float:
    _ensure_positive_integer(length, "length")
    _require_length(values, length, "rma")

    average = sum(values[:length]) / float(length)
    for value in values[length:]:
        average = ((average * float(length - 1)) + value) / float(length)
    return average


def ema(values: Sequence[float], length: int) -> float:
    _ensure_positive_integer(length, "length")
    _require_length(values, length, "ema")

    multiplier = 2.0 / float(length + 1)
    ema_value = sum(values[:length]) / float(length)
    for value in values[length:]:
        ema_value = (value * multiplier) + (ema_value * (1.0 - multiplier))
    return ema_value


def true_ranges(candles: Sequence[Candle]) -> list[float]:
    _require_length(candles, 1, "true_ranges")
    ranges: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        if previous_close is None:
            true_range = candle.high - candle.low
        else:
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - previous_close),
                abs(candle.low - previous_close),
            )
        ranges.append(true_range)
        previous_close = candle.close
    return ranges


def atr(candles: Sequence[Candle], length: int) -> float:
    return rma(true_ranges(candles), length)


def ichimoku(
    candles: Sequence[Candle],
    conversion_periods: int = 9,
    base_periods: int = 26,
    span_b_periods: int = 52,
) -> IchimokuValues:
    _require_length(candles, span_b_periods, "ichimoku")
    highs = [candle.high for candle in candles]
    lows = [candle.low for candle in candles]

    tenkan = (max(highs[-conversion_periods:]) + min(lows[-conversion_periods:])) / 2.0
    kijun = (max(highs[-base_periods:]) + min(lows[-base_periods:])) / 2.0
    senkou_b = (max(highs[-span_b_periods:]) + min(lows[-span_b_periods:])) / 2.0
    return IchimokuValues(tenkan=tenkan, kijun=kijun, senkou_b=senkou_b)


def volume_profile(
    candles: Sequence[Candle],
    bins: int = ENTRY_PROFILE_BINS,
    value_area_ratio: float = VALUE_AREA_RATIO,
) -> VolumeProfile:
    _ensure_positive_integer(bins, "bins")
    _require_length(candles, 1, "volume_profile")

    window_low = min(candle.low for candle in candles)
    window_high = max(candle.high for candle in candles)
    price_range = window_high - window_low

    if math.isclose(price_range, 0.0):
        return VolumeProfile(
            poc=window_high,
            vah=window_high,
            val=window_low,
            window_low=window_low,
            window_high=window_high,
            bin_size=1.0,
        )

    bin_size = _float_range(price_range / float(bins))
    histogram = [0.0] * bins

    for candle in candles:
        raw_index = (candle.close - window_low) / bin_size
        clamped_index = min(max(int(math.floor(raw_index)), 0), bins - 1)
        histogram[clamped_index] += candle.volume

    poc_index = 0
    poc_volume = histogram[0]
    for index, bucket_volume in enumerate(histogram[1:], start=1):
        if bucket_volume > poc_volume:
            poc_index = index
            poc_volume = bucket_volume

    total_volume = sum(histogram)
    if math.isclose(total_volume, 0.0):
        poc_price = window_low + (bin_size * (float(poc_index) + 0.5))
        return VolumeProfile(
            poc=poc_price,
            vah=poc_price,
            val=poc_price,
            window_low=window_low,
            window_high=window_high,
            bin_size=bin_size,
        )

    left_index = poc_index
    right_index = poc_index
    accumulated_volume = histogram[poc_index]
    target_volume = total_volume * value_area_ratio

    while accumulated_volume < target_volume and (left_index > 0 or right_index < bins - 1):
        left_candidate = histogram[left_index - 1] if left_index > 0 else -1.0
        right_candidate = histogram[right_index + 1] if right_index < bins - 1 else -1.0

        if left_candidate >= right_candidate and left_index > 0:
            left_index -= 1
            accumulated_volume += histogram[left_index]
        elif right_index < bins - 1:
            right_index += 1
            accumulated_volume += histogram[right_index]
        else:
            break

    poc_price = window_low + (bin_size * (float(poc_index) + 0.5))
    vah_price = window_low + (bin_size * float(right_index + 1))
    val_price = window_low + (bin_size * float(left_index))
    return VolumeProfile(
        poc=poc_price,
        vah=vah_price,
        val=val_price,
        window_low=window_low,
        window_high=window_high,
        bin_size=bin_size,
    )


def _find_latest_pivot_high(
    candles: Sequence[Candle],
    pivot_length: int,
) -> tuple[float, int] | None:
    _require_length(candles, (pivot_length * 2) + 1, "pivot_high")

    for index in range(len(candles) - pivot_length - 1, pivot_length - 1, -1):
        candidate = candles[index].high
        is_pivot = True
        for offset in range(1, pivot_length + 1):
            if candidate <= candles[index - offset].high or candidate <= candles[index + offset].high:
                is_pivot = False
                break
        if is_pivot:
            return candidate, index
    return None


def _find_latest_pivot_low(
    candles: Sequence[Candle],
    pivot_length: int,
) -> tuple[float, int] | None:
    _require_length(candles, (pivot_length * 2) + 1, "pivot_low")

    for index in range(len(candles) - pivot_length - 1, pivot_length - 1, -1):
        candidate = candles[index].low
        is_pivot = True
        for offset in range(1, pivot_length + 1):
            if candidate >= candles[index - offset].low or candidate >= candles[index + offset].low:
                is_pivot = False
                break
        if is_pivot:
            return candidate, index
    return None


def _fallback_high(candles: Sequence[Candle], fallback_window: int) -> tuple[float, int]:
    window = _window_or_tail(candles, fallback_window)
    start_index = len(candles) - len(window)
    highest = window[0].high
    highest_index = start_index
    for offset, candle in enumerate(window[1:], start=1):
        if candle.high > highest:
            highest = candle.high
            highest_index = start_index + offset
    return highest, highest_index


def _fallback_low(candles: Sequence[Candle], fallback_window: int) -> tuple[float, int]:
    window = _window_or_tail(candles, fallback_window)
    start_index = len(candles) - len(window)
    lowest = window[0].low
    lowest_index = start_index
    for offset, candle in enumerate(window[1:], start=1):
        if candle.low < lowest:
            lowest = candle.low
            lowest_index = start_index + offset
    return lowest, lowest_index


def latest_fibo_anchor(
    candles: Sequence[Candle],
    pivot_length: int = PIVOT_LENGTH,
    fallback_window: int = PIVOT_FALLBACK_WINDOW,
) -> FiboAnchor:
    _ensure_positive_integer(pivot_length, "pivot_length")
    _ensure_positive_integer(fallback_window, "fallback_window")
    _require_length(candles, 1, "latest_fibo_anchor")

    pivot_high = _find_latest_pivot_high(candles, pivot_length)
    pivot_low = _find_latest_pivot_low(candles, pivot_length)

    if pivot_high is None:
        high_value, high_index = _fallback_high(candles, fallback_window)
        pivot_high_ts: int | None = None
    else:
        high_value, high_index = pivot_high
        pivot_high_ts = high_index

    if pivot_low is None:
        low_value, low_index = _fallback_low(candles, fallback_window)
        pivot_low_ts: int | None = None
    else:
        low_value, low_index = pivot_low
        pivot_low_ts = low_index

    if high_value <= low_value:
        raise ValueError("Fibo anchor requires pivot_high > pivot_low.")

    return FiboAnchor(
        pivot_low=low_value,
        pivot_high=high_value,
        low_index=low_index,
        high_index=high_index,
        pivot_low_ts=pivot_low_ts,
        pivot_high_ts=pivot_high_ts,
    )


def validate_fibo_anchor_temporal(
    pivot_high_ts: int | None,
    pivot_low_ts: int | None,
    side: TradeSide,
) -> bool:
    """Validate confirmed pivot order; fallback anchors cannot prove time order."""
    if pivot_high_ts is None or pivot_low_ts is None:
        return True
    if side == TradeSide.LONG:
        return pivot_low_ts < pivot_high_ts
    return pivot_high_ts < pivot_low_ts


def fibo_anchor_temporally_valid(anchor: FiboAnchor, side: TradeSide) -> bool:
    return validate_fibo_anchor_temporal(
        pivot_high_ts=anchor.pivot_high_ts,
        pivot_low_ts=anchor.pivot_low_ts,
        side=side,
    )


def fibo_retracement(anchor: FiboAnchor, ratio: float, side: TradeSide) -> float:
    price_range = anchor.pivot_high - anchor.pivot_low
    if side == TradeSide.LONG:
        return anchor.pivot_high - (price_range * ratio)
    return anchor.pivot_low + (price_range * ratio)


def fibo_extension(anchor: FiboAnchor, level: float, side: TradeSide) -> float:
    price_range = anchor.pivot_high - anchor.pivot_low
    if side == TradeSide.LONG:
        return anchor.pivot_low + (price_range * level)
    return anchor.pivot_high - (price_range * level)


def build_layered_entry_prices(
    profile: VolumeProfile,
    anchor: FiboAnchor,
    kijun_value: float,
    atr_value: float,
    side: TradeSide,
) -> LayeredEntryPrices | None:
    if not fibo_anchor_temporally_valid(anchor, side):
        return None

    buffer = 0.05 * atr_value
    if side == TradeSide.LONG:
        return LayeredEntryPrices(
            l1=max(profile.poc, kijun_value) + buffer,
            l2=fibo_retracement(anchor, 0.618, TradeSide.LONG),
            l3=min(fibo_retracement(anchor, 0.786, TradeSide.LONG), profile.val),
        )

    return LayeredEntryPrices(
        l1=min(profile.poc, kijun_value) - buffer,
        l2=fibo_retracement(anchor, 0.618, TradeSide.SHORT),
        l3=max(fibo_retracement(anchor, 0.786, TradeSide.SHORT), profile.vah),
    )


def triple_confluence_active(
    *,
    poc: float,
    kijun: float,
    fibo_0618: float,
    atr_value: float,
) -> bool:
    spread = max(poc, kijun, fibo_0618) - min(poc, kijun, fibo_0618)
    return spread <= (TRIPLE_CONFLUENCE_ATR_RATIO * atr_value)


def base_layer_fraction(layer: str) -> float:
    weights = {"L1": L1_WEIGHT, "L2": L2_WEIGHT, "L3": L3_WEIGHT}
    return BASE_SIZING_FRAME * weights[layer]


def promoted_layer_fraction(layer: str) -> float:
    if layer == "L1":
        return base_layer_fraction("L1")
    remaining_frame = PROMOTED_SIZING_FRAME - base_layer_fraction("L1")
    if layer == "L2":
        return remaining_frame * (L2_WEIGHT / (L2_WEIGHT + L3_WEIGHT))
    if layer == "L3":
        return remaining_frame * (L3_WEIGHT / (L2_WEIGHT + L3_WEIGHT))
    raise ValueError(f"Unknown layer: {layer}")


class StateMachine:
    def __init__(
        self,
        snapshot: StrategyStateSnapshot,
        *,
        now_fn: Callable[[], datetime] | None = None,
        client_order_id_fn: Callable[[str, int, int], str] | None = None,
    ) -> None:
        self.snapshot = snapshot
        self._now_fn = now_fn or (lambda: datetime.now(UTC))
        self._client_order_id_fn = client_order_id_fn or self._default_client_order_id

    def evaluate_entry_trigger(
        self,
        bar: EntrySignalBar,
        prev_bar: EntrySignalBar,
        htf_bar: EntrySignalBar,
        btc_ema_htf: float,
        cvd_30m: float,
        side: TradeSide = TradeSide.LONG,
    ) -> bool:
        if self.snapshot.state != int(StateCode.IDLE) or self._cooldown_active():
            return False

        if side == TradeSide.LONG:
            htf_bias = htf_bar.close > btc_ema_htf
            entry_cross = bar.close > bar.kijun and prev_bar.close <= prev_bar.kijun
            cvd_aligned = cvd_30m > 0.0
        else:
            htf_bias = htf_bar.close < btc_ema_htf
            entry_cross = bar.close < bar.kijun and prev_bar.close >= prev_bar.kijun
            cvd_aligned = cvd_30m < 0.0

        return htf_bias and entry_cross and cvd_aligned

    def place_layers(
        self,
        avg_fill_fn: Callable[[str, float, float], str] | None,
        atr_value: float,
        poc: float,
        kijun: float,
        fibo_0618: float,
        fibo_0786: float,
        val: float,
        side: TradeSide = TradeSide.LONG,
        bar_index: int | None = None,
        fibo_temporal_valid: bool = True,
        vah: float | None = None,
    ) -> list[LayerOrder]:
        if self.snapshot.state != int(StateCode.IDLE) or not fibo_temporal_valid:
            return []

        buffer = 0.05 * atr_value
        if side == TradeSide.LONG:
            layer_prices = {
                "L1": max(poc, kijun) + buffer,
                "L2": fibo_0618,
                "L3": min(fibo_0786, val),
            }
        else:
            layer_prices = {
                "L1": min(poc, kijun) - buffer,
                "L2": fibo_0618,
                "L3": max(fibo_0786, val if vah is None else vah),
            }

        self.snapshot.side = side.value
        self.snapshot.state = int(StateCode.PENDING)
        self.snapshot.entry_started_bar = bar_index
        self.snapshot.entry_prices = dict(layer_prices)
        self.snapshot.sizing_frame = BASE_SIZING_FRAME
        self.snapshot.triple_confluence = False
        self.snapshot.triple_confluence_evaluated = False

        orders = [
            self._make_order("L1", side, layer_prices["L1"], base_layer_fraction("L1")),
        ]
        if avg_fill_fn is not None:
            l1_order = orders[0]
            avg_fill_fn(l1_order.layer, l1_order.price, l1_order.equity_fraction)
        return [orders[0]]

    def on_l1_fill(
        self,
        fill_price: float,
        fill_qty: float,
        *,
        fill_ts: datetime | None = None,
    ) -> list[StateAction]:
        previous_state = self.snapshot.state
        if previous_state != int(StateCode.PENDING):
            return []

        self._record_fill("L1", fill_price, fill_qty)
        self.snapshot.state = int(StateCode.FILLED_PARTIAL)
        self.snapshot.first_fill_ts = (fill_ts or self._now_fn()).isoformat()

        l2_price = self.snapshot.entry_prices.get("L2")
        if l2_price is None:
            return []
        order = self._make_order("L2", self._side(), l2_price, base_layer_fraction("L2"))
        return [
            StateAction(
                intent=OrderIntent.PLACE,
                reason="ENTRY_L2",
                state_from=previous_state,
                state_to=self.snapshot.state,
                layer="L2",
                order=order,
            )
        ]

    def on_l2_fill(
        self,
        fill_price: float,
        fill_qty: float,
        *,
        atr_value: float,
        poc: float,
        kijun: float,
        fibo_0618: float,
        l2_filled_equity_fraction: float = BASE_SIZING_FRAME * L2_WEIGHT,
        l3_filled_equity_fraction: float = 0.0,
    ) -> list[StateAction]:
        previous_state = self.snapshot.state
        if previous_state != int(StateCode.FILLED_PARTIAL):
            return []

        self._record_fill("L2", fill_price, fill_qty)
        actions: list[StateAction] = self._replace_hard_sl(atr_value)
        if not self.snapshot.triple_confluence_evaluated:
            self.snapshot.triple_confluence = triple_confluence_active(
                poc=poc,
                kijun=kijun,
                fibo_0618=fibo_0618,
                atr_value=atr_value,
            )
            self.snapshot.triple_confluence_evaluated = True
            if self.snapshot.triple_confluence:
                self.snapshot.sizing_frame = PROMOTED_SIZING_FRAME

        if self.snapshot.triple_confluence:
            target_l2_fraction = promoted_layer_fraction("L2")
            remaining_l2_fraction = max(target_l2_fraction - l2_filled_equity_fraction, 0.0)
            if not math.isclose(remaining_l2_fraction, 0.0):
                l2_price = self.snapshot.entry_prices.get("L2")
                if l2_price is not None:
                    actions.append(
                        StateAction(
                            intent=OrderIntent.PLACE,
                            reason="TRIPLE_CONFLUENCE_RESIZE_L2",
                            state_from=previous_state,
                            state_to=self.snapshot.state,
                            layer="L2",
                            order=self._make_resize_order(
                                layer="L2",
                                id_layer="L2R",
                                side=self._side(),
                                price=l2_price,
                                equity_fraction=remaining_l2_fraction,
                            ),
                        )
                    )

        target_fraction = (
            promoted_layer_fraction("L3")
            if self.snapshot.triple_confluence
            else base_layer_fraction("L3")
        )
        remaining_l3_fraction = max(target_fraction - l3_filled_equity_fraction, 0.0)
        l3_price = self.snapshot.entry_prices.get("L3")
        if l3_price is None or math.isclose(remaining_l3_fraction, 0.0):
            return actions

        order = self._make_order("L3", self._side(), l3_price, remaining_l3_fraction)
        if self.snapshot.triple_confluence:
            actions.append(
                StateAction(
                    intent=OrderIntent.CANCEL,
                    reason="TRIPLE_CONFLUENCE_RESIZE_L3",
                    state_from=previous_state,
                    state_to=self.snapshot.state,
                    layer="L3",
                )
            )
        actions.append(
            StateAction(
                intent=OrderIntent.PLACE,
                reason="ENTRY_L3",
                state_from=previous_state,
                state_to=self.snapshot.state,
                layer="L3",
                order=order,
            )
        )
        return actions

    def on_l2_promo_fill(self, fill_price: float, fill_qty: float) -> None:
        if self.snapshot.state != int(StateCode.FILLED_PARTIAL):
            return
        self._record_fill("L2", fill_price, fill_qty)

    def on_l3_fill(
        self,
        fill_price: float,
        fill_qty: float,
        *,
        atr_value: float | None = None,
    ) -> list[StateAction]:
        previous_state = self.snapshot.state
        if previous_state != int(StateCode.FILLED_PARTIAL):
            return []

        self._record_fill("L3", fill_price, fill_qty)
        self.snapshot.state = int(StateCode.FILLED_FULL)
        self.snapshot.remaining_position_fraction = 1.0
        actions = [
            StateAction(
                intent=OrderIntent.TRANSITION,
                reason="FILLED_FULL",
                state_from=previous_state,
                state_to=self.snapshot.state,
                layer="L3",
            )
        ]
        if atr_value is not None:
            actions = self._replace_hard_sl(atr_value) + actions
        return actions

    def evaluate_take_profit_bar(self, inputs: TakeProfitInputs) -> StateAction | None:
        if self.snapshot.state == int(StateCode.RUNNER):
            return None
        if inputs.bar_id is not None and self.snapshot.last_tp_bar_id == inputs.bar_id:
            return None

        side = self._side()
        if (
            self.snapshot.sub_state is None
            and TPEvaluator.evaluate_a(inputs.rsi, inputs.kijun_series, side)
        ):
            return self._mark_tp_bar(self.on_tp_a(), inputs.bar_id)
        if self.snapshot.sub_state != SubState.AB.value and TPEvaluator.evaluate_b(
            inputs.price,
            inputs.fibo_1_0,
            side,
        ):
            return self._mark_tp_bar(self.on_tp_b(), inputs.bar_id)
        if TPEvaluator.evaluate_c(
            inputs.price,
            inputs.fibo_1_5,
            inputs.volume,
            inputs.volume_sma_20,
            side,
        ):
            return self._mark_tp_bar(
                self.on_tp_c(use_runner=inputs.use_runner),
                inputs.bar_id,
            )
        return None

    def evaluate_exit_bar(
        self,
        *,
        bar_low: float,
        bar_high: float,
        take_profit: TakeProfitInputs,
    ) -> StateAction | None:
        previous_state = self.snapshot.state
        if self.check_hard_sl_hit(bar_low=bar_low, bar_high=bar_high):
            return StateAction(
                intent=OrderIntent.CLOSE_MARKET,
                reason="HARD_SL",
                state_from=previous_state,
                state_to=int(StateCode.IDLE),
            )
        return self.evaluate_take_profit_bar(take_profit)

    def tick(
        self,
        *,
        runner: RunnerInputs | None = None,
        take_profit: TakeProfitInputs | None = None,
        bar_low: float | None = None,
        bar_high: float | None = None,
    ) -> StateAction | None:
        if self.snapshot.state == int(StateCode.RUNNER):
            if runner is None:
                return None
            runner_handler = RunnerHandler(
                self.snapshot,
                now_fn=self._now_fn,
                client_order_id_fn=self._client_order_id_fn,
            )
            if runner_handler.check_kijun_break(
                runner.close_prev,
                runner.open_cur,
                runner.kijun_prev,
                runner.kijun_cur,
                self._side(),
            ):
                return runner_handler.on_kijun_break()
            return None

        if take_profit is None:
            return None
        if bar_low is not None and bar_high is not None:
            return self.evaluate_exit_bar(
                bar_low=bar_low,
                bar_high=bar_high,
                take_profit=take_profit,
            )
        return self.evaluate_take_profit_bar(take_profit)

    def on_tp_a(self) -> StateAction | None:
        if self.snapshot.state != int(StateCode.FILLED_FULL) or self.snapshot.sub_state is not None:
            return None

        previous_state = self.snapshot.state
        self.snapshot.sub_state = SubState.A.value
        close_fraction = self.snapshot.remaining_position_fraction * 0.50
        self.snapshot.remaining_position_fraction -= close_fraction
        return StateAction(
            intent=OrderIntent.CLOSE_MARKET,
            reason="TP_A",
            state_from=previous_state,
            state_to=self.snapshot.state,
            layer="TP_A",
            order=LayerOrder(
                layer="TP_A",
                side=self._opposite_side(),
                price=0.0,
                equity_fraction=close_fraction,
                client_order_id=self._client_order_id_fn("TPA", previous_state, self.snapshot.state),
            ),
        )

    def on_tp_b(self) -> StateAction | None:
        if self.snapshot.state != int(StateCode.FILLED_FULL):
            return None
        if self.snapshot.sub_state == SubState.AB.value:
            return None

        previous_state = self.snapshot.state
        close_fraction = self.snapshot.remaining_position_fraction * 0.50
        self.snapshot.remaining_position_fraction -= close_fraction
        self.snapshot.sub_state = SubState.AB.value
        return StateAction(
            intent=OrderIntent.CLOSE_MARKET,
            reason="TP_B",
            state_from=previous_state,
            state_to=self.snapshot.state,
            layer="TP_B",
            order=LayerOrder(
                layer="TP_B",
                side=self._opposite_side(),
                price=0.0,
                equity_fraction=close_fraction,
                client_order_id=self._client_order_id_fn("TPB", previous_state, self.snapshot.state),
            ),
        )

    def on_tp_c(self, *, use_runner: bool) -> StateAction | None:
        if self.snapshot.state != int(StateCode.FILLED_FULL):
            return None

        previous_state = self.snapshot.state
        if use_runner:
            hard_sl_client_order_id = self.snapshot.client_order_ids.get("HARD_SL")
            old_hard_sl = self.snapshot.hard_sl
            self.snapshot.state = int(StateCode.RUNNER)
            self.snapshot.hard_sl = 0.0
            self.snapshot.client_order_ids["HARD_SL"] = None
            return StateAction(
                intent=OrderIntent.TRANSITION,
                reason="TP_C_RUNNER_START",
                state_from=previous_state,
                state_to=self.snapshot.state,
                layer="TP_C",
                stop_order=(
                    HardStopOrder(
                        side=self._side(),
                        stop_price=old_hard_sl,
                        client_order_id=hard_sl_client_order_id,
                    )
                    if hard_sl_client_order_id is not None
                    else None
                ),
                cancel_order_ids=(
                    (hard_sl_client_order_id,) if hard_sl_client_order_id is not None else ()
                ),
            )

        close_fraction = self.snapshot.remaining_position_fraction
        close_side = self._opposite_side()
        self._reset_flat(keep_cooldown=False)
        return StateAction(
            intent=OrderIntent.CLOSE_MARKET,
            reason="TP_C_EXIT",
            state_from=previous_state,
            state_to=int(StateCode.IDLE),
            layer="TP_C",
            order=LayerOrder(
                layer="TP_C",
                side=close_side,
                price=0.0,
                equity_fraction=close_fraction,
                client_order_id=self._client_order_id_fn("TPC", previous_state, int(StateCode.IDLE)),
            ),
        )

    def check_hard_sl_hit(self, bar_low: float, bar_high: float) -> bool:
        if self.snapshot.state == int(StateCode.RUNNER):
            return False
        if self.snapshot.state not in {
            int(StateCode.FILLED_PARTIAL),
            int(StateCode.FILLED_FULL),
        }:
            return False
        if math.isclose(self.snapshot.hard_sl, 0.0):
            return False

        side = self._side()
        hit = (
            bar_low <= self.snapshot.hard_sl
            if side == TradeSide.LONG
            else bar_high >= self.snapshot.hard_sl
        )
        if not hit:
            return False

        self._set_cooldown(hours=24)
        self._reset_flat(keep_cooldown=True)
        return True

    def check_state_2_abort(self, reverse_spike: bool, htf_cross: bool) -> bool:
        if self.snapshot.state != int(StateCode.FILLED_PARTIAL):
            return False
        if not (reverse_spike or htf_cross):
            return False

        self._reset_flat(keep_cooldown=False)
        return True

    def check_evasion(
        self,
        peak_mfe: float,
        atr_value: float,
        reverse_spike: bool,
        htf_cross: bool,
        hours_since_fill: float,
    ) -> bool:
        if self.snapshot.state not in {
            int(StateCode.FILLED_PARTIAL),
            int(StateCode.FILLED_FULL),
        }:
            return False
        if hours_since_fill > EVASION_WINDOW_HOURS:
            return False

        signal_dead = peak_mfe < (EVASION_PEAK_ATR_RATIO * atr_value)
        if not ((reverse_spike or htf_cross) and signal_dead):
            return False

        self._set_cooldown(hours=24)
        self.snapshot.state = int(StateCode.EVASION)
        self._reset_flat(keep_cooldown=True)
        return True

    def check_state_1_timeout(self, bars_elapsed: int) -> bool:
        if self.snapshot.state != int(StateCode.PENDING):
            return False
        if bars_elapsed < STATE_1_TIMEOUT_BARS:
            return False

        self._reset_flat(keep_cooldown=False)
        return True

    def _record_fill(self, layer: str, fill_price: float, fill_qty: float) -> None:
        if fill_qty <= 0.0:
            raise ValueError("fill_qty must be positive.")
        self.snapshot.entry_prices[layer] = fill_price
        self.snapshot.fill_qtys[layer] = self.snapshot.fill_qtys.get(layer, 0.0) + fill_qty
        self.snapshot.avg_entry = self._position().compute_avg_entry()

    def _mark_tp_bar(self, action: StateAction | None, bar_id: int | None) -> StateAction | None:
        if action is not None and bar_id is not None:
            self.snapshot.last_tp_bar_id = bar_id
        return action

    def _position(self) -> Position:
        return Position(
            side=self._side(),
            entry_prices=self.snapshot.entry_prices,
            fill_qtys=self.snapshot.fill_qtys,
        )

    def _replace_hard_sl(self, atr_value: float) -> list[StateAction]:
        actions: list[StateAction] = []
        previous_client_order_id = self.snapshot.client_order_ids.get("HARD_SL")
        if previous_client_order_id is not None:
            actions.append(
                StateAction(
                    intent=OrderIntent.CANCEL,
                    reason="HARD_SL_CANCEL_REPLACE",
                    state_from=self.snapshot.state,
                    state_to=self.snapshot.state,
                    layer="HARD_SL",
                    stop_order=HardStopOrder(
                        side=self._side(),
                        stop_price=self.snapshot.hard_sl,
                        client_order_id=previous_client_order_id,
                    ),
                )
            )

        hard_sl = self._position().compute_hard_sl(atr_value)
        self.snapshot.hard_sl = hard_sl
        client_order_id = self._client_order_id_fn("HSL", self.snapshot.state, self.snapshot.state)
        self.snapshot.client_order_ids["HARD_SL"] = client_order_id
        actions.append(
            StateAction(
                intent=OrderIntent.PLACE,
                reason="HARD_SL_REPLACE",
                state_from=self.snapshot.state,
                state_to=self.snapshot.state,
                stop_order=HardStopOrder(
                    side=self._side(),
                    stop_price=hard_sl,
                    client_order_id=client_order_id,
                ),
            )
        )
        return actions

    def _make_order(
        self,
        layer: str,
        side: TradeSide,
        price: float,
        equity_fraction: float,
    ) -> LayerOrder:
        transition_by_layer = {
            "L1": (int(StateCode.IDLE), int(StateCode.PENDING)),
            "L2": (int(StateCode.PENDING), int(StateCode.FILLED_PARTIAL)),
            "L3": (int(StateCode.FILLED_PARTIAL), int(StateCode.FILLED_FULL)),
        }
        state_from, state_to = transition_by_layer[layer]
        client_order_id = self._client_order_id_fn(layer, state_from, state_to)
        self.snapshot.client_order_ids[layer] = client_order_id
        return LayerOrder(
            layer=layer,
            side=side,
            price=price,
            equity_fraction=equity_fraction,
            client_order_id=client_order_id,
        )

    def _make_resize_order(
        self,
        *,
        layer: str,
        id_layer: str,
        side: TradeSide,
        price: float,
        equity_fraction: float,
    ) -> LayerOrder:
        state_from = self.snapshot.state
        state_to = self.snapshot.state
        client_order_id = self._client_order_id_fn(id_layer, state_from, state_to)
        self.snapshot.client_order_ids[layer] = client_order_id
        return LayerOrder(
            layer=layer,
            side=side,
            price=price,
            equity_fraction=equity_fraction,
            client_order_id=client_order_id,
        )

    def _side(self) -> TradeSide:
        return _snapshot_side(self.snapshot)

    def _opposite_side(self) -> TradeSide:
        return _opposite_trade_side(self._side())

    def _cooldown_active(self) -> bool:
        if not self.snapshot.cooldown_until:
            return False
        cooldown_until = datetime.fromisoformat(self.snapshot.cooldown_until)
        if cooldown_until.tzinfo is None:
            cooldown_until = cooldown_until.replace(tzinfo=UTC)
        return self._now_fn() < cooldown_until

    def _set_cooldown(self, *, hours: int) -> None:
        self.snapshot.cooldown_until = (self._now_fn() + timedelta(hours=hours)).isoformat()

    def _reset_flat(self, *, keep_cooldown: bool) -> None:
        _reset_snapshot_flat(self.snapshot, keep_cooldown=keep_cooldown)

    def _default_client_order_id(self, layer: str, state_from: int, state_to: int) -> str:
        _ = layer
        return OrderManager(now_fn=self._now_fn).client_order_id(
            symbol=self.snapshot.symbol,
            state_from=state_from,
            state_to=state_to,
        )


def rsi(candles: Sequence[Candle], length: int) -> float:
    _ensure_positive_integer(length, "length")
    _require_length(candles, length + 1, "rsi")

    closes = [candle.close for candle in candles]
    gains: list[float] = []
    losses: list[float] = []
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    average_gain = rma(gains, length)
    average_loss = rma(losses, length)
    if math.isclose(average_loss, 0.0):
        return 100.0
    if math.isclose(average_gain, 0.0):
        return 0.0

    relative_strength = average_gain / average_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def volume_sma(candles: Sequence[Candle], length: int = 20) -> float:
    return sma([candle.volume for candle in candles], length)


def cvd_proxy_series(candles: Sequence[Candle]) -> tuple[list[float], list[float]]:
    _require_length(candles, 1, "cvd_proxy_series")

    deltas: list[float] = []
    cumulative: list[float] = []
    current_day: date | None = None
    running_cvd = 0.0

    for candle in candles:
        candle_day = _utc_day(candle.timestamp)
        if candle_day != current_day:
            current_day = candle_day
            running_cvd = 0.0

        delta = (candle.close - candle.open) * candle.volume
        running_cvd += delta
        deltas.append(delta)
        cumulative.append(running_cvd)

    return deltas, cumulative


def _floor_to_hour(timestamp: datetime) -> datetime:
    utc_timestamp = timestamp.astimezone(UTC)
    return utc_timestamp.replace(minute=0, second=0, microsecond=0)


def build_cvd_trade_delta_bars(trades: Sequence[CvdTrade]) -> tuple[list[float], list[float]]:
    _require_length(trades, 1, "build_cvd_trade_delta_bars")

    accumulator = CvdTradeAccumulator()
    current_bar = _floor_to_hour(trades[0].timestamp)
    next_bar = current_bar + timedelta(hours=1)
    deltas: list[float] = []
    cumulative: list[float] = []

    for trade in trades:
        trade_timestamp = trade.timestamp.astimezone(UTC)
        while trade_timestamp >= next_bar:
            deltas.append(accumulator.close_bar())
            cumulative.append(accumulator.cumulative_delta)
            current_bar = next_bar
            next_bar = current_bar + timedelta(hours=1)
        accumulator.ingest(trade)

    deltas.append(accumulator.close_bar())
    cumulative.append(accumulator.cumulative_delta)
    return deltas, cumulative


def cvd_abs_sma(delta_bars: Sequence[float], length: int = 20) -> float:
    absolute_deltas = [abs(delta) for delta in delta_bars]
    return sma(absolute_deltas, length)


def cvd_spike(delta_bars: Sequence[float], length: int = 20, multiplier: float = 3.0) -> bool:
    _require_length(delta_bars, length, "cvd_spike")
    threshold = cvd_abs_sma(delta_bars, length) * multiplier
    return abs(delta_bars[-1]) > threshold


def reverse_spike(
    delta_bars: Sequence[float],
    side: TradeSide,
    length: int = 20,
    multiplier: float = 3.0,
) -> bool:
    _require_length(delta_bars, length, "reverse_spike")
    threshold = cvd_abs_sma(delta_bars, length) * multiplier
    if side == TradeSide.LONG:
        return delta_bars[-1] < (-threshold)
    return delta_bars[-1] > threshold


def btc_ema_4h(candles: Sequence[Candle], length: int = 50) -> float:
    closes = [candle.close for candle in candles]
    return ema(closes, length)


def phase2_indicator_snapshot(
    entry_candles: Sequence[Candle],
    btc_htf_candles: Sequence[Candle],
    trade_delta_bars: Sequence[float],
) -> Phase2IndicatorSnapshot:
    entry_window = _window_or_tail(entry_candles, ENTRY_PROFILE_LOOKBACK)
    profile = volume_profile(entry_window, bins=ENTRY_PROFILE_BINS, value_area_ratio=VALUE_AREA_RATIO)
    anchor = latest_fibo_anchor(entry_candles)
    ichimoku_values = ichimoku(entry_candles)
    proxy_deltas, proxy_cvd = cvd_proxy_series(entry_candles)

    return Phase2IndicatorSnapshot(
        atr_14=atr(entry_candles, 14),
        tenkan_9=ichimoku_values.tenkan,
        kijun_26=ichimoku_values.kijun,
        senkou_b_52=ichimoku_values.senkou_b,
        poc=profile.poc,
        vah=profile.vah,
        val=profile.val,
        pivot_low=anchor.pivot_low,
        pivot_high=anchor.pivot_high,
        fibo_0618=fibo_retracement(anchor, 0.618, TradeSide.LONG),
        fibo_0786=fibo_retracement(anchor, 0.786, TradeSide.LONG),
        fibo_1000=fibo_extension(anchor, 1.0, TradeSide.LONG),
        fibo_1500=fibo_extension(anchor, 1.5, TradeSide.LONG),
        rsi_14=rsi(entry_candles, 14),
        volume_sma_20=volume_sma(entry_candles, 20),
        btc_ema_50=btc_ema_4h(btc_htf_candles, 50),
        cvd_proxy=proxy_cvd[-1],
        cvd_trade_delta=trade_delta_bars[-1],
        cvd_abs_sma_20=cvd_abs_sma(trade_delta_bars, 20),
        cvd_spike=cvd_spike(trade_delta_bars, 20),
        reverse_spike_long=reverse_spike(trade_delta_bars, TradeSide.LONG, 20),
        reverse_spike_short=reverse_spike(trade_delta_bars, TradeSide.SHORT, 20),
    )


def build_phase2_sample_candles(
    *,
    count: int,
    start: datetime,
    interval: timedelta,
    base_price: float,
    drift: float,
    wave: float,
    base_volume: float,
) -> list[Candle]:
    candles: list[Candle] = []
    for index in range(count):
        timestamp = start + (interval * index)
        trend = base_price + (drift * float(index))
        swing = math.sin(float(index) / 11.0) * wave
        pullback = math.cos(float(index) / 7.0) * (wave * 0.35)
        open_price = trend + swing + (pullback * 0.20)
        close_price = trend + swing + pullback
        high_price = max(open_price, close_price) + 1.15 + (abs(math.sin(float(index) / 5.0)) * 0.45)
        low_price = min(open_price, close_price) - 1.05 - (abs(math.cos(float(index) / 6.0)) * 0.40)
        volume = base_volume + (float(index % 19) * 23.0) + (abs(math.sin(float(index) / 4.0)) * 140.0)
        candles.append(
            Candle(
                timestamp=timestamp,
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=volume,
            )
        )
    return candles


def build_phase2_sample_trades(entry_candles: Sequence[Candle]) -> list[CvdTrade]:
    trades: list[CvdTrade] = []
    for candle in entry_candles[-24:]:
        base_quantity = candle.volume / 250.0
        trade_time = candle.timestamp.astimezone(UTC)
        for step in range(6):
            quantity = base_quantity * (0.9 + (0.08 * float(step)))
            is_buyer_maker = step % 2 == 1
            trades.append(
                CvdTrade(
                    timestamp=trade_time + timedelta(minutes=step * 10),
                    quantity=quantity,
                    is_buyer_maker=is_buyer_maker,
                )
            )
    return trades


def build_phase2_sample_data() -> Phase2SampleData:
    entry_start = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    btc_start = datetime(2025, 8, 1, 0, 0, tzinfo=UTC)

    entry_candles = build_phase2_sample_candles(
        count=ENTRY_PROFILE_LOOKBACK,
        start=entry_start,
        interval=timedelta(hours=1),
        base_price=98.0,
        drift=0.18,
        wave=5.2,
        base_volume=980.0,
    )
    btc_htf_candles = build_phase2_sample_candles(
        count=60,
        start=btc_start,
        interval=timedelta(hours=4),
        base_price=62000.0,
        drift=21.0,
        wave=880.0,
        base_volume=1800.0,
    )
    sample_trades = build_phase2_sample_trades(entry_candles)
    trade_deltas, _ = build_cvd_trade_delta_bars(sample_trades)
    return Phase2SampleData(
        entry_candles=entry_candles,
        btc_htf_candles=btc_htf_candles,
        cvd_trade_deltas=trade_deltas,
    )


def build_phase2_parity_rows() -> list[ParityRow]:
    sample = build_phase2_sample_data()
    snapshot = phase2_indicator_snapshot(
        sample.entry_candles,
        sample.btc_htf_candles,
        sample.cvd_trade_deltas,
    )
    entry_window = _window_or_tail(sample.entry_candles, ENTRY_PROFILE_LOOKBACK)
    profile = volume_profile(entry_window, bins=ENTRY_PROFILE_BINS, value_area_ratio=VALUE_AREA_RATIO)
    anchor = latest_fibo_anchor(sample.entry_candles)
    ichimoku_values = ichimoku(sample.entry_candles)

    return [
        ParityRow("ATR(14)", snapshot.atr_14, atr(sample.entry_candles, 14), "Wilder RMA of TR"),
        ParityRow("Ichimoku Tenkan(9)", snapshot.tenkan_9, ichimoku_values.tenkan, "HH/LL midpoint over 9 bars"),
        ParityRow("Ichimoku Kijun(26)", snapshot.kijun_26, ichimoku_values.kijun, "HH/LL midpoint over 26 bars"),
        ParityRow("Ichimoku Senkou B(52)", snapshot.senkou_b_52, ichimoku_values.senkou_b, "HH/LL midpoint over 52 bars"),
        ParityRow("POC", snapshot.poc, profile.poc, "500-bar close-bin profile, center price"),
        ParityRow("VAH", snapshot.vah, profile.vah, "70% value area upper bound"),
        ParityRow("VAL", snapshot.val, profile.val, "70% value area lower bound"),
        ParityRow("Pivot Low", snapshot.pivot_low, anchor.pivot_low, "Latest confirmed pivot low, fallback 100-bar low"),
        ParityRow("Pivot High", snapshot.pivot_high, anchor.pivot_high, "Latest confirmed pivot high, fallback 100-bar high"),
        ParityRow("Fibo 0.618", snapshot.fibo_0618, fibo_retracement(anchor, 0.618, TradeSide.LONG), "Pivot-H retracement from long anchor"),
        ParityRow("Fibo 0.786", snapshot.fibo_0786, fibo_retracement(anchor, 0.786, TradeSide.LONG), "Pivot-H retracement from long anchor"),
        ParityRow("Fibo 1.0", snapshot.fibo_1000, fibo_extension(anchor, 1.0, TradeSide.LONG), "Pivot-H extension target"),
        ParityRow("Fibo 1.5", snapshot.fibo_1500, fibo_extension(anchor, 1.5, TradeSide.LONG), "Pivot-H extension target"),
        ParityRow("RSI(14)", snapshot.rsi_14, rsi(sample.entry_candles, 14), "Wilder RMA gain/loss"),
        ParityRow("Volume SMA(20)", snapshot.volume_sma_20, volume_sma(sample.entry_candles, 20), "20-bar simple average"),
        ParityRow("BTC EMA(4H, 50)", snapshot.btc_ema_50, btc_ema_4h(sample.btc_htf_candles, 50), "50-bar EMA on BTC 4H"),
    ]


def format_phase2_parity_markdown(rows: Sequence[ParityRow]) -> str:
    lines = [
        "### Phase 2 Parity Check (CVD 제외)",
        "",
        "- 데이터셋: synthetic entry_tf 500 bars + BTC 4H 60 bars",
        "- Pine 값은 `strategy.pine` 수식 기준 수동 계산값으로 기록",
        "- POC/VAH/VAL은 close-price single-bin volume allocation 가정으로 Pine/Python 통일",
        "",
        "| Indicator | Python | Pine | 3dp Match | Basis |",
        "|---|---:|---:|:---:|---|",
    ]

    for row in rows:
        lines.append(
            f"| {row.indicator} | {row.python_value:.6f} | {row.pine_value:.6f} | "
            f"{'yes' if row.match_3dp else 'no'} | {row.basis} |"
        )

    return "\n".join(lines)


def collect_market_snapshot(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "entry_trigger_ready": False,
        "triple_confluence": False,
        "runner_triggered": False,
    }


def evaluate_entry_trigger(market_snapshot: dict[str, Any]) -> bool:
    return bool(market_snapshot.get("entry_trigger_ready", False))


def advance_state_machine(
    snapshot: StrategyStateSnapshot,
    event_name: str,
) -> StrategyStateSnapshot:
    logging.debug("State machine placeholder received event=%s for %s", event_name, snapshot.symbol)
    return snapshot


def evaluate_exit_logic(
    snapshot: StrategyStateSnapshot,
    market_snapshot: dict[str, Any],
) -> str | None:
    _ = snapshot
    _ = market_snapshot
    return None


def enforce_ops_guards(config: AppConfig, symbol: str) -> list[str]:
    warnings: list[str] = []
    if config.mmr.get(symbol) is None:
        warnings.append(
            f"{symbol}: mmr is unset. Fill exchange-published values before paper/live execution."
        )
    return warnings


def run_backtest(
    config: AppConfig,
    symbols: list[str],
    state_dir: Path,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    cache_dir: Path = DEFAULT_BACKTEST_CACHE_DIR,
    days: int = DEFAULT_BACKTEST_DAYS,
    output_path: Path = DEFAULT_BACKTEST_OUTPUT_PATH,
) -> int:
    _ = state_dir
    from mts_profile import accepted_replay_kwargs
    from offline_replay import run_replay

    logging.info(
        "Running offline OHLCV replay: symbols=%s days=%s cache_dir=%s output=%s",
        ",".join(symbols),
        days,
        cache_dir,
        output_path,
    )
    result = run_replay(
        config_path=config_path,
        cache_dir=cache_dir,
        days=days,
        output_path=output_path,
        symbols=symbols,
        **accepted_replay_kwargs(),
    )
    logging.info(
        "Configured TFs: htf=%s entry_tf=%s ltf=%s; emitted events=%s exits=%s",
        config.timeframes.htf,
        config.timeframes.entry_tf,
        config.timeframes.ltf,
        result.events,
        result.exits,
    )
    return 0


def run_paper(
    config: AppConfig,
    symbols: list[str],
    state_dir: Path,
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    cache_dir: Path = DEFAULT_BACKTEST_CACHE_DIR,
    days: int = DEFAULT_BACKTEST_DAYS,
) -> int:
    _ = config
    from mts_paper_runner import MtsPaperRunner

    runner = MtsPaperRunner(
        config_path=config_path,
        cache_dir=cache_dir,
        paper_dir=state_dir.parent / "paper_logs",
        symbols=symbols,
    )
    payload = runner.run_once(days=days)
    logging.info(
        "MTS-V1 paper-only replay generated symbols=%s events=%s exits=%s summary=%s",
        len(payload["symbols"]),
        payload["events"],
        payload["exits"],
        payload["artifacts"]["summary_json"],
    )
    return 0


def run_indicator_check() -> int:
    rows = build_phase2_parity_rows()
    print(format_phase2_parity_markdown(rows))
    return 0


def parse_symbol_override(raw: str | None) -> list[str] | None:
    if raw is None or not raw.strip():
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MTS-V1 strategy scaffold")
    parser.add_argument(
        "--mode",
        choices=[mode.value for mode in StrategyMode],
        default=StrategyMode.PAPER.value,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--state-dir", type=Path, default=DEFAULT_STATE_DIR)
    parser.add_argument("--symbols", help="Comma-separated symbol override.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_BACKTEST_CACHE_DIR)
    parser.add_argument("--days", type=int, default=DEFAULT_BACKTEST_DAYS)
    parser.add_argument("--output", type=Path, default=DEFAULT_BACKTEST_OUTPUT_PATH)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(levelname)s %(message)s",
    )

    if args.mode == StrategyMode.INDICATOR_CHECK.value:
        return run_indicator_check()

    config = load_config(args.config)
    symbol_override = parse_symbol_override(args.symbols)
    if symbol_override is None and args.mode in {
        StrategyMode.BACKTEST.value,
        StrategyMode.PAPER.value,
    }:
        from mts_profile import ACCEPTED_SYMBOLS

        symbols = list(ACCEPTED_SYMBOLS)
    else:
        symbols = symbol_override or config.symbols

    for symbol in symbols:
        for warning in enforce_ops_guards(config, symbol):
            logging.warning(warning)

    if args.mode == StrategyMode.BACKTEST.value:
        return run_backtest(
            config,
            symbols,
            args.state_dir,
            config_path=args.config,
            cache_dir=args.cache_dir,
            days=args.days,
            output_path=args.output,
        )
    return run_paper(
        config,
        symbols,
        args.state_dir,
        config_path=args.config,
        cache_dir=args.cache_dir,
        days=args.days,
    )


if __name__ == "__main__":
    raise SystemExit(main())
