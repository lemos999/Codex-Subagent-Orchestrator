from __future__ import annotations

import argparse
from bisect import bisect_right
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import pandas as pd  # type: ignore[import-untyped]

from strategy import (
    ENTRY_PROFILE_LOOKBACK,
    EVASION_PEAK_ATR_RATIO,
    EVASION_WINDOW_HOURS,
    STATE_1_TIMEOUT_BARS,
    AppConfig,
    Candle,
    EntrySignalBar,
    OrderIntent,
    RunnerInputs,
    StateCode,
    StateMachine,
    StrategyStateSnapshot,
    TakeProfitInputs,
    TradeSide,
    atr,
    base_layer_fraction,
    btc_ema_4h,
    cvd_abs_sma,
    cvd_proxy_series,
    fibo_anchor_temporally_valid,
    fibo_extension,
    fibo_retracement,
    ichimoku,
    latest_fibo_anchor,
    load_config,
    parse_symbol_override,
    reverse_spike,
    rsi,
    volume_profile,
    volume_sma,
)


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = ROOT_DIR.parent / "predictive_runner_paper" / "cache_180d"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "logs" / "trades_mtsv1_offline_90d.jsonl"
STATE2_EXIT_MODES = {"all", "adverse-only", "off"}
STATE2_SIGNAL_MODES = {"any", "both", "reverse-only", "htf-only"}
CVD_ENTRY_MODES = {"pine-ltf", "spec-30m"}
REPLAY_STOP_TOUCH_EPSILON = 0.1
REPLAY_STATE_1_TIMEOUT = timedelta(hours=48)


def pandas_timeframe(raw: str) -> str:
    normalized = raw.strip().lower()
    aliases = {
        "15": "15min",
        "15m": "15min",
        "15min": "15min",
        "30": "30min",
        "30m": "30min",
        "30min": "30min",
        "60": "1h",
        "1h": "1h",
        "240": "4h",
        "4h": "4h",
    }
    if normalized in aliases:
        return aliases[normalized]
    raise ValueError(f"Unsupported timeframe for offline replay: {raw}")


def timeframe_delta(raw: str) -> timedelta:
    normalized = pandas_timeframe(raw)
    if normalized == "15min":
        return timedelta(minutes=15)
    if normalized == "30min":
        return timedelta(minutes=30)
    if normalized == "1h":
        return timedelta(hours=1)
    if normalized == "4h":
        return timedelta(hours=4)
    raise ValueError(f"Unsupported timeframe for offline replay: {raw}")


@dataclass(slots=True)
class ReplayClock:
    ts: datetime

    def now(self) -> datetime:
        return self.ts


@dataclass(slots=True)
class ReplayPosition:
    machine: StateMachine
    side: TradeSide
    entry_ts: datetime
    entry_index: int
    entry_cvd_sign: int
    clock: ReplayClock | None = None
    realized_r: float = 0.0
    pending_l3_fraction: float = base_layer_fraction("L3")
    avg_entry_for_r: float = 0.0
    risk_for_r: float = 0.0
    remaining_fraction_for_r: float = 1.0
    peak_mfe: float = 0.0
    pending_l2_fill_price: float | None = None
    pending_l2_fill_ts: datetime | None = None
    pending_l2_fill_reason: str = "L2_FILL"
    pending_l2_promo_fraction: float = 0.0
    pending_l2_promo_price: float | None = None
    refresh_child_layers_on_next_bar: bool = False
    last_fill_event: str = ""
    last_fill_reason: str = ""
    last_fill_ts: datetime | None = None


@dataclass(slots=True, frozen=True)
class ExitContext:
    avg_entry: float
    hard_sl: float
    risk: float
    remaining_fraction: float


@dataclass(slots=True, frozen=True)
class ReplayResult:
    output_path: Path
    events: int
    exits: int
    symbols: list[str]


def parse_timestamp(raw: Any) -> datetime:
    parsed = cast(datetime, pd.Timestamp(raw).to_pydatetime())
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def symbol_asset(symbol: str) -> str:
    return symbol.split("/", 1)[0].split(":", 1)[0].upper()


def parse_symbol_float_map(raw: str) -> dict[str, float]:
    if not raw.strip():
        return {}
    result: dict[str, float] = {}
    for item in raw.split(","):
        key, separator, value = item.partition("=")
        if not separator:
            raise ValueError(f"Expected SYMBOL=value item, got {item!r}")
        result[key.strip().upper()] = float(value)
    return result


def load_15m_cache(cache_dir: Path, asset: str) -> pd.DataFrame:
    path = cache_dir / f"{asset}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing cache file: {path}")
    frame = pd.read_csv(path, parse_dates=["timestamp"])
    missing_columns = {"open", "high", "low", "close", "volume", "timestamp"} - set(
        frame.columns
    )
    if missing_columns:
        raise ValueError(f"{path} missing columns={sorted(missing_columns)}")
    frame = frame.rename(columns={"timestamp": "ts"})
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    frame = frame.sort_values("ts").reset_index(drop=True)
    if frame.empty:
        raise ValueError(f"{path} has no rows")
    gaps = frame["ts"].diff().dropna()
    if not gaps.empty and not (gaps == pd.Timedelta(minutes=15)).all():
        raise ValueError(f"{path} has non-15m timestamp gaps")
    return frame


def resample_ohlcv(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    indexed = frame.set_index("ts")
    result = indexed.resample(timeframe).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum",
        }
    )
    return result.dropna().reset_index()


def align_security_frame_to_base_close(
    frame: pd.DataFrame,
    security_timeframe: str,
    base_timeframe: str = "15min",
) -> pd.DataFrame:
    offset = timeframe_delta(security_timeframe) - timeframe_delta(base_timeframe)
    if offset <= timedelta(0):
        return frame

    aligned = frame.copy()
    aligned["ts"] = aligned["ts"] + offset
    return aligned


def candles_from_frame(frame: pd.DataFrame) -> list[Candle]:
    return [
        Candle(
            timestamp=parse_timestamp(row.ts),
            open=float(row.open),
            high=float(row.high),
            low=float(row.low),
            close=float(row.close),
            volume=float(row.volume),
        )
        for row in frame.itertuples(index=False)
    ]


def touched(candle: Candle, price: float) -> bool:
    return candle.low <= price <= candle.high


def pine_contract_qty(equity_fraction: float, order_price: float) -> float:
    if order_price <= 0.0:
        raise ValueError("order_price must be positive.")
    return equity_fraction / order_price


def marketable_limit_fill_price(
    side: TradeSide,
    limit_price: float,
    close_price: float,
) -> float | None:
    if side == TradeSide.LONG and limit_price >= close_price:
        return close_price
    if side == TradeSide.SHORT and limit_price <= close_price:
        return close_price
    return None


def intrabar_limit_fill_price(
    side: TradeSide,
    limit_price: float,
    candle: Candle,
) -> float | None:
    """TradingView-style active limit fill for a bar without bar magnifier."""
    if side == TradeSide.LONG:
        if candle.open <= limit_price:
            return candle.open
        if candle.low <= limit_price:
            return limit_price
        return None

    if candle.open >= limit_price:
        return candle.open
    if candle.high >= limit_price:
        return limit_price
    return None


def cvd_sign(candle: Candle) -> int:
    delta = (candle.close - candle.open) * candle.volume
    if delta > 0.0:
        return 1
    if delta < 0.0:
        return -1
    return 0


def side_r(price: float, avg_entry: float, risk: float, side: TradeSide) -> float:
    if risk <= 0.0:
        return 0.0
    if side == TradeSide.LONG:
        return (price - avg_entry) / risk
    return (avg_entry - price) / risk


def event_row(
    *,
    ts: datetime,
    symbol: str,
    event: str,
    side: TradeSide,
    price: float,
    reason: str,
    rr: float | None = None,
    win: bool | None = None,
    cvd: int | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "ts": ts.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "symbol": symbol,
        "event": event,
        "side": side.value,
        "price": round(price, 8),
        "reason": reason,
    }
    if rr is not None:
        row["rr"] = round(rr, 6)
        row["pnl_r"] = round(rr, 6)
        row["r_multiple"] = round(rr, 6)
    if win is not None:
        row["win"] = win
    if cvd is not None:
        row["cvd_sign"] = cvd
    if extra:
        row.update(extra)
    return row


def state2_trigger_source(*, reverse: bool, htf_cross: bool) -> str:
    if reverse and htf_cross:
        return "both"
    if reverse:
        return "reverse_spike"
    if htf_cross:
        return "htf_cross"
    return "unknown"


def reverse_spike_ratio(
    *,
    side: TradeSide,
    cvd_delta: float,
    threshold: float,
) -> float:
    if threshold <= 0.0:
        return 0.0
    adverse_delta = -cvd_delta if side == TradeSide.LONG else cvd_delta
    return adverse_delta / threshold


def mark_fill(active: ReplayPosition, *, event: str, reason: str, ts: datetime) -> None:
    active.last_fill_event = event
    active.last_fill_reason = reason
    active.last_fill_ts = ts


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


class OfflineReplay:
    def __init__(
        self,
        *,
        config: AppConfig,
        cache_dir: Path,
        days: int,
        output_path: Path,
        entry_timeframe: str | None = None,
        execution_timeframe: str | None = None,
        htf_timeframe: str | None = None,
        state2_exit_mode: str = "all",
        state2_signal_mode: str = "any",
        state2_profit_hold_r: float | None = None,
        l3_max_distance_atr: float | None = None,
        reverse_spike_multiplier: float = 3.0,
        symbol_reverse_spike_multipliers: dict[str, float] | None = None,
        reverse_spike_min_ratio: float = 1.0,
        reverse_spike_confirm_bars: int = 1,
        state2_reverse_min_minutes_since_l2: float = 0.0,
        tp_intrabar_touch: bool = False,
        cvd_entry_mode: str = "pine-ltf",
    ) -> None:
        if state2_exit_mode not in STATE2_EXIT_MODES:
            raise ValueError(f"Unsupported state2_exit_mode: {state2_exit_mode}")
        if state2_signal_mode not in STATE2_SIGNAL_MODES:
            raise ValueError(f"Unsupported state2_signal_mode: {state2_signal_mode}")
        if cvd_entry_mode not in CVD_ENTRY_MODES:
            raise ValueError(f"Unsupported cvd_entry_mode: {cvd_entry_mode}")
        if reverse_spike_min_ratio < 1.0:
            raise ValueError("reverse_spike_min_ratio must be >= 1.0")
        if reverse_spike_confirm_bars not in {1, 2}:
            raise ValueError("reverse_spike_confirm_bars must be 1 or 2")
        if state2_reverse_min_minutes_since_l2 < 0.0:
            raise ValueError("state2_reverse_min_minutes_since_l2 must be >= 0")
        self.config = config
        self.cache_dir = cache_dir
        self.days = days
        self.output_path = output_path
        self.entry_timeframe = pandas_timeframe(entry_timeframe or config.timeframes.entry_tf)
        self.execution_timeframe = pandas_timeframe(
            execution_timeframe or self.entry_timeframe,
        )
        self.htf_timeframe = pandas_timeframe(htf_timeframe or config.timeframes.htf)
        self.state2_exit_mode = state2_exit_mode
        self.state2_signal_mode = state2_signal_mode
        self.state2_profit_hold_r = state2_profit_hold_r
        self.l3_max_distance_atr = l3_max_distance_atr
        self.reverse_spike_multiplier = reverse_spike_multiplier
        self.symbol_reverse_spike_multipliers = symbol_reverse_spike_multipliers or {}
        self.reverse_spike_min_ratio = reverse_spike_min_ratio
        self.reverse_spike_confirm_bars = reverse_spike_confirm_bars
        self.state2_reverse_min_minutes_since_l2 = state2_reverse_min_minutes_since_l2
        self.tp_intrabar_touch = tp_intrabar_touch
        self.cvd_entry_mode = cvd_entry_mode
        self.events: list[dict[str, Any]] = []
        self.symbol_cooldowns: dict[str, datetime] = {}
        self.coverage_start: datetime | None = None
        self.coverage_end: datetime | None = None
        btc_15m = load_15m_cache(cache_dir, "BTC")
        self.btc_4h = candles_from_frame(
            align_security_frame_to_base_close(
                resample_ohlcv(btc_15m, self.htf_timeframe),
                self.htf_timeframe,
            ),
        )
        self.btc_context_cache = self._precompute_btc_context(self.btc_4h)
        self.btc_context_timestamps = [item[0] for item in self.btc_context_cache]

    def run(self, symbols: list[str]) -> ReplayResult:
        for symbol in symbols:
            self._run_symbol(symbol)
        self.events.sort(key=lambda row: str(row["ts"]))
        output_rows = self._metadata_rows(symbols) + self.events
        write_jsonl(self.output_path, output_rows)
        exits = sum(1 for row in self.events if row.get("event") == "EXIT")
        return ReplayResult(
            output_path=self.output_path,
            events=len(self.events),
            exits=exits,
            symbols=symbols,
        )

    def _run_symbol(self, symbol: str) -> None:
        asset = symbol_asset(symbol)
        raw_15m = load_15m_cache(self.cache_dir, asset)
        entry_frame = resample_ohlcv(raw_15m, self.entry_timeframe)
        entry_candles = candles_from_frame(entry_frame)
        execution_candles = candles_from_frame(
            resample_ohlcv(raw_15m, self.execution_timeframe),
        )
        htf_candles = candles_from_frame(
            align_security_frame_to_base_close(
                resample_ohlcv(raw_15m, self.htf_timeframe),
                self.htf_timeframe,
            ),
        )
        htf_cross_cache = self._precompute_htf_crosses(htf_candles)
        if len(entry_candles) < ENTRY_PROFILE_LOOKBACK + 3:
            return

        end_ts = entry_candles[-1].timestamp
        start_ts = end_ts - timedelta(days=self.days)
        self._update_coverage(start_ts=start_ts, end_ts=end_ts)
        active: ReplayPosition | None = None
        execution_index = 0
        entry_delta = timeframe_delta(self.entry_timeframe)

        for index in range(ENTRY_PROFILE_LOOKBACK + 3, len(entry_candles)):
            candle = entry_candles[index]
            if candle.timestamp < start_ts:
                continue
            next_entry_ts = (
                entry_candles[index + 1].timestamp
                if index + 1 < len(entry_candles)
                else candle.timestamp + entry_delta
            )
            execution_span, execution_index = self._execution_span(
                execution_candles,
                execution_index,
                candle.timestamp,
                next_entry_ts,
            )
            window = entry_candles[: index + 1]
            prev_window = entry_candles[:index]
            try:
                indicators = self._indicators(window, symbol)
                htf_cross_long, htf_cross_short = htf_cross_cache.get(
                    candle.timestamp,
                    (False, False),
                )
                indicators["htf_cross_long"] = float(htf_cross_long)
                indicators["htf_cross_short"] = float(htf_cross_short)
                prev_ichi = ichimoku(prev_window)
                kijun_series = [
                    ichimoku(entry_candles[: index - 1]).kijun,
                    prev_ichi.kijun,
                    indicators["kijun"],
                ]
            except ValueError:
                continue

            if active is None:
                active = self._maybe_enter(
                    symbol=symbol,
                    candle=candle,
                    prev_candle=entry_candles[index - 1],
                    index=index,
                    indicators=indicators,
                    prev_kijun=prev_ichi.kijun,
                )
                continue

            active = self._advance_active_over_execution_span(
                symbol=symbol,
                active=active,
                execution_candles=execution_span or [candle],
                signal_candle=candle,
                prev_signal_candle=entry_candles[index - 1],
                signal_index=index,
                indicators=indicators,
                kijun_series=kijun_series,
            )

        if active is not None:
            self._force_close(symbol, active, entry_candles[-1], "END_OF_WINDOW")

    def _execution_span(
        self,
        execution_candles: list[Candle],
        start_index: int,
        start_ts: datetime,
        end_ts: datetime,
    ) -> tuple[list[Candle], int]:
        index = start_index
        while index < len(execution_candles) and execution_candles[index].timestamp < start_ts:
            index += 1
        span_start = index
        while index < len(execution_candles) and execution_candles[index].timestamp < end_ts:
            index += 1
        return execution_candles[span_start:index], index

    def _update_coverage(self, *, start_ts: datetime, end_ts: datetime) -> None:
        self.coverage_start = (
            start_ts
            if self.coverage_start is None
            else max(self.coverage_start, start_ts)
        )
        self.coverage_end = (
            end_ts
            if self.coverage_end is None
            else min(self.coverage_end, end_ts)
        )

    def _metadata_rows(self, symbols: list[str]) -> list[dict[str, Any]]:
        if self.coverage_start is None or self.coverage_end is None:
            return []
        return [
            {
                "ts": self.coverage_start.astimezone(UTC).isoformat().replace(
                    "+00:00",
                    "Z",
                ),
                "event": "REPLAY_META",
                "coverage_start": self.coverage_start.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "coverage_end": self.coverage_end.astimezone(UTC)
                .isoformat()
                .replace("+00:00", "Z"),
                "coverage_days": self.days,
                "symbols": symbols,
                "source": str(self.cache_dir),
            }
        ]

    def _indicators(self, window: list[Candle], symbol: str = "") -> dict[str, float]:
        entry_window = window[-ENTRY_PROFILE_LOOKBACK:]
        profile = volume_profile(entry_window)
        anchor = latest_fibo_anchor(window)
        ichi = ichimoku(window)
        delta_bars, _cumulative_cvd = cvd_proxy_series(window)
        reverse_multiplier = self._reverse_spike_multiplier(symbol)
        cvd_delta = self._entry_cvd_delta(delta_bars)
        cvd_delta_prev = delta_bars[-2] if len(delta_bars) >= 2 else 0.0
        reverse_abs_sma = cvd_abs_sma(delta_bars, 20)
        reverse_abs_sma_prev = cvd_abs_sma(delta_bars[:-1], 20) if len(delta_bars) > 20 else 0.0
        reverse_threshold = reverse_abs_sma * reverse_multiplier
        reverse_threshold_prev = reverse_abs_sma_prev * reverse_multiplier
        reverse_spike_long_prev = (
            reverse_spike(delta_bars[:-1], TradeSide.LONG, 20, reverse_multiplier)
            if len(delta_bars) > 20
            else False
        )
        reverse_spike_short_prev = (
            reverse_spike(delta_bars[:-1], TradeSide.SHORT, 20, reverse_multiplier)
            if len(delta_bars) > 20
            else False
        )
        return {
            "atr": atr(window, 14),
            "kijun": ichi.kijun,
            "poc": profile.poc,
            "vah": profile.vah,
            "val": profile.val,
            "fibo_long_0618": fibo_retracement(anchor, 0.618, TradeSide.LONG),
            "fibo_long_0786": fibo_retracement(anchor, 0.786, TradeSide.LONG),
            "fibo_long_1000": fibo_extension(anchor, 1.0, TradeSide.LONG),
            "fibo_long_1500": fibo_extension(anchor, 1.5, TradeSide.LONG),
            "fibo_short_0618": fibo_retracement(anchor, 0.618, TradeSide.SHORT),
            "fibo_short_0786": fibo_retracement(anchor, 0.786, TradeSide.SHORT),
            "fibo_short_1000": fibo_extension(anchor, 1.0, TradeSide.SHORT),
            "fibo_short_1500": fibo_extension(anchor, 1.5, TradeSide.SHORT),
            "fibo_long_temporal_valid": float(
                fibo_anchor_temporally_valid(anchor, TradeSide.LONG),
            ),
            "fibo_short_temporal_valid": float(
                fibo_anchor_temporally_valid(anchor, TradeSide.SHORT),
            ),
            "rsi": rsi(window, 14),
            "volume_sma": volume_sma(window, 20),
            "entry_cvd_delta": cvd_delta,
            "entry_cvd_delta_prev": cvd_delta_prev,
            "reverse_spike_abs_sma_20": reverse_abs_sma,
            "reverse_spike_abs_sma_20_prev": reverse_abs_sma_prev,
            "reverse_spike_threshold": reverse_threshold,
            "reverse_spike_threshold_prev": reverse_threshold_prev,
            "reverse_spike_multiplier": reverse_multiplier,
            "reverse_spike_long": float(
                reverse_spike(
                    delta_bars,
                    TradeSide.LONG,
                    20,
                    reverse_multiplier,
                )
            ),
            "reverse_spike_short": float(
                reverse_spike(
                    delta_bars,
                    TradeSide.SHORT,
                    20,
                    reverse_multiplier,
                )
            ),
            "reverse_spike_long_prev": float(reverse_spike_long_prev),
            "reverse_spike_short_prev": float(reverse_spike_short_prev),
        }

    def _reverse_spike_multiplier(self, symbol: str) -> float:
        if not symbol:
            return self.reverse_spike_multiplier
        asset = symbol_asset(symbol)
        return self.symbol_reverse_spike_multipliers.get(
            asset,
            self.symbol_reverse_spike_multipliers.get(symbol.upper(), self.reverse_spike_multiplier),
        )

    def _symbol_htf_crosses(
        self,
        htf_candles: list[Candle],
        ts: datetime,
    ) -> tuple[bool, bool]:
        candles = [candle for candle in htf_candles if candle.timestamp <= ts]
        if len(candles) < 54:
            return False, False
        # request.security HTF cross should pulse only when the aligned HTF value updates.
        if candles[-1].timestamp != ts:
            return False, False
        previous_close = candles[-2].close
        current_close = candles[-1].close
        previous_kijun = ichimoku(candles[:-1]).kijun
        current_kijun = ichimoku(candles).kijun
        cross_against_long = previous_close >= previous_kijun and current_close < current_kijun
        cross_against_short = previous_close <= previous_kijun and current_close > current_kijun
        return cross_against_long, cross_against_short

    def _precompute_htf_crosses(
        self,
        htf_candles: list[Candle],
    ) -> dict[datetime, tuple[bool, bool]]:
        result: dict[datetime, tuple[bool, bool]] = {}
        for index in range(53, len(htf_candles)):
            candles = htf_candles[: index + 1]
            previous_close = candles[-2].close
            current_close = candles[-1].close
            previous_kijun = ichimoku(candles[:-1]).kijun
            current_kijun = ichimoku(candles).kijun
            result[candles[-1].timestamp] = (
                previous_close >= previous_kijun and current_close < current_kijun,
                previous_close <= previous_kijun and current_close > current_kijun,
            )
        return result

    def _precompute_btc_context(
        self,
        btc_candles: list[Candle],
    ) -> list[tuple[datetime, float, float]]:
        return [
            (
                btc_candles[index].timestamp,
                btc_candles[index].close,
                btc_ema_4h(btc_candles[: index + 1], 50),
            )
            for index in range(49, len(btc_candles))
        ]

    def _btc_context(self, ts: datetime) -> tuple[float, float]:
        index = bisect_right(self.btc_context_timestamps, ts) - 1
        if index < 0:
            raise ValueError("BTC 4h context requires at least 50 candles")
        _timestamp, close, ema_value = self.btc_context_cache[index]
        return close, ema_value

    def _maybe_enter(
        self,
        *,
        symbol: str,
        candle: Candle,
        prev_candle: Candle,
        index: int,
        indicators: dict[str, float],
        prev_kijun: float,
    ) -> ReplayPosition | None:
        if self._symbol_cooldown_active(symbol, candle.timestamp):
            return None

        btc_close, btc_ema = self._btc_context(candle.timestamp)
        for side in (TradeSide.LONG, TradeSide.SHORT):
            def client_order_id(
                layer: str,
                state_from: int,
                state_to: int,
                entry_index: int = index,
            ) -> str:
                return f"offline_{layer}_{state_from}_{state_to}_{entry_index}"

            snapshot = StrategyStateSnapshot(symbol=symbol)
            cooldown_until = self.symbol_cooldowns.get(symbol)
            if cooldown_until is not None:
                snapshot.cooldown_until = cooldown_until.isoformat()
            clock = ReplayClock(candle.timestamp)
            machine = StateMachine(
                snapshot,
                now_fn=clock.now,
                client_order_id_fn=client_order_id,
            )
            signal = machine.evaluate_entry_trigger(
                bar=EntrySignalBar(close=candle.close, kijun=indicators["kijun"]),
                prev_bar=EntrySignalBar(close=prev_candle.close, kijun=prev_kijun),
                htf_bar=EntrySignalBar(close=btc_close, kijun=0.0),
                btc_ema_htf=btc_ema,
                cvd_30m=indicators["entry_cvd_delta"],
                side=side,
            )
            if not signal:
                continue

            if not bool(indicators[f"fibo_{side.value}_temporal_valid"]):
                continue

            fibo_0618 = indicators[f"fibo_{side.value}_0618"]
            fibo_0786 = indicators[f"fibo_{side.value}_0786"]
            orders = machine.place_layers(
                avg_fill_fn=None,
                atr_value=indicators["atr"],
                poc=indicators["poc"],
                kijun=indicators["kijun"],
                fibo_0618=fibo_0618,
                fibo_0786=fibo_0786,
                val=indicators["val"],
                vah=indicators["vah"],
                side=side,
                bar_index=index,
            )
            if not orders:
                continue
            self._cap_l3_distance(machine, side, indicators["atr"])
            self.events.append(
                event_row(
                    ts=candle.timestamp,
                    symbol=symbol,
                    event="ENTRY_SIGNAL",
                    side=side,
                    price=candle.close,
                    reason="ENTRY_TRIGGER",
                    cvd=cvd_sign(candle),
                )
            )
            active = ReplayPosition(
                machine=machine,
                side=side,
                entry_ts=candle.timestamp,
                entry_index=index,
                entry_cvd_sign=cvd_sign(candle),
                clock=clock,
            )
            l1_price = float(machine.snapshot.entry_prices["L1"] or 0.0)
            close_fill = marketable_limit_fill_price(side, l1_price, candle.close)
            if close_fill is not None:
                machine.on_l1_fill(
                    fill_price=close_fill,
                    fill_qty=pine_contract_qty(base_layer_fraction("L1"), l1_price),
                    fill_ts=candle.timestamp,
                )
                active.avg_entry_for_r = close_fill
                active.risk_for_r = max(indicators["atr"] * 2.0, active.risk_for_r)
                mark_fill(
                    active,
                    event="ENTRY_L1",
                    reason="L1_FILL_ON_CLOSE",
                    ts=candle.timestamp,
                )
                self.events.append(
                    event_row(
                        ts=candle.timestamp,
                        symbol=symbol,
                        event="ENTRY_L1",
                        side=active.side,
                        price=close_fill,
                        reason="L1_FILL_ON_CLOSE",
                        cvd=cvd_sign(candle),
                    )
                )
                active.refresh_child_layers_on_next_bar = True
                return active
            return active
        return None

    def _entry_cvd_delta(self, delta_bars: list[float]) -> float:
        if self.cvd_entry_mode == "spec-30m" and self.entry_timeframe == "15min":
            return sum(delta_bars[-2:])
        return delta_bars[-1] if delta_bars else 0.0

    def _cap_l3_distance(
        self,
        machine: StateMachine,
        side: TradeSide,
        atr_value: float,
    ) -> None:
        if self.l3_max_distance_atr is None:
            return
        l2_price = machine.snapshot.entry_prices.get("L2")
        l3_price = machine.snapshot.entry_prices.get("L3")
        if l2_price is None or l3_price is None:
            return
        max_distance = self.l3_max_distance_atr * atr_value
        if side == TradeSide.LONG:
            machine.snapshot.entry_prices["L3"] = max(l3_price, l2_price - max_distance)
        else:
            machine.snapshot.entry_prices["L3"] = min(l3_price, l2_price + max_distance)

    def _refresh_child_layer_prices_once(
        self,
        active: ReplayPosition,
        indicators: dict[str, float],
    ) -> None:
        # Pine creates child L2/L3 orders on the L1 fill recognition pass.
        # After that pass, their limit prices stay fixed until fill/cancel.
        side = active.side
        required = {
            "atr",
            "val",
            "vah",
            f"fibo_{side.value}_0618",
            f"fibo_{side.value}_0786",
        }
        if any(key not in indicators for key in required):
            return
        active.machine.snapshot.entry_prices["L2"] = indicators[
            f"fibo_{side.value}_0618"
        ]
        if side == TradeSide.LONG:
            active.machine.snapshot.entry_prices["L3"] = min(
                indicators[f"fibo_{side.value}_0786"],
                indicators["val"],
            )
        else:
            active.machine.snapshot.entry_prices["L3"] = max(
                indicators[f"fibo_{side.value}_0786"],
                indicators["vah"],
            )
        self._cap_l3_distance(active.machine, side, indicators["atr"])

    def _advance_active(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        prev_candle: Candle,
        index: int,
        indicators: dict[str, float],
        kijun_series: list[float],
        allow_state2_exit: bool = True,
        allow_take_profit: bool = True,
        take_profit_candle: Candle | None = None,
        take_profit_execution_candle: Candle | None = None,
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        machine = active.machine
        state = machine.snapshot.state
        if state == int(StateCode.PENDING):
            if self._state_1_timed_out(active, candle):
                return None
            l1_price = float(machine.snapshot.entry_prices["L1"] or 0.0)
            l1_fill_price = intrabar_limit_fill_price(active.side, l1_price, candle)
            if l1_fill_price is not None:
                self._refresh_child_layer_prices_once(active, indicators)
                machine.on_l1_fill(
                    fill_price=l1_fill_price,
                    fill_qty=pine_contract_qty(base_layer_fraction("L1"), l1_price),
                    fill_ts=candle.timestamp,
                )
                active.avg_entry_for_r = l1_fill_price
                active.risk_for_r = max(indicators["atr"] * 2.0, active.risk_for_r)
                mark_fill(
                    active,
                    event="ENTRY_L1",
                    reason="L1_FILL",
                    ts=candle.timestamp,
                )
                self.events.append(
                    event_row(
                        ts=candle.timestamp,
                        symbol=symbol,
                        event="ENTRY_L1",
                        side=active.side,
                        price=l1_fill_price,
                        reason="L1_FILL",
                        cvd=cvd_sign(candle),
                    )
                )
                self._try_same_bar_l2_fill(
                    symbol=symbol,
                    active=active,
                    candle=candle,
                    indicators=indicators,
                )
                return active
            return active

        if state == int(StateCode.FILLED_PARTIAL):
            created_child_layers_this_bar = False
            if active.refresh_child_layers_on_next_bar:
                self._refresh_child_layer_prices_once(active, indicators)
                active.refresh_child_layers_on_next_bar = False
                created_child_layers_this_bar = True
            if active.pending_l2_fill_price is not None:
                self._update_peak_mfe(active, candle)
                state2_exit_reason = (
                    self._state2_exit_reason(active=active, candle=candle, indicators=indicators)
                    if allow_state2_exit
                    else None
                )
                recognized = self._recognize_deferred_l2_fill(
                    symbol=symbol,
                    active=active,
                    candle=candle,
                    indicators=indicators,
                    check_hard_sl=state2_exit_reason is None,
                )
                if recognized is None:
                    return None
                if state2_exit_reason is not None:
                    self._record_state2_exit(
                        symbol,
                        recognized,
                        candle,
                        state2_exit_reason,
                        candle.close,
                        indicators,
                    )
                    self._apply_state2_exit_reset(
                        symbol=symbol,
                        active=recognized,
                        candle=candle,
                        indicators=indicators,
                        reason=state2_exit_reason,
                    )
                    return None
                return recognized

            if created_child_layers_this_bar:
                return self._try_same_bar_l2_fill(
                    symbol=symbol,
                    active=active,
                    candle=candle,
                    indicators=indicators,
                )

            exit_context = self._capture_exit_context(active)
            if self._check_hard_sl_hit(active, candle):
                self._remember_active_cooldown(symbol, active)
                self._record_exit(
                    symbol,
                    active,
                    candle,
                    "HARD_SL",
                    exit_context.hard_sl or candle.close,
                    exit_context,
                )
                return None
            self._update_peak_mfe(active, candle)
            state2_exit_reason = (
                self._state2_exit_reason(active=active, candle=candle, indicators=indicators)
                if allow_state2_exit
                else None
            )
            l2_qty = machine.snapshot.fill_qtys.get("L2", 0.0)
            l3_qty = machine.snapshot.fill_qtys.get("L3", 0.0)
            if l2_qty <= 0.0:
                l2_price = float(machine.snapshot.entry_prices["L2"] or 0.0)
                l2_fill_price = intrabar_limit_fill_price(active.side, l2_price, candle)
                if l2_fill_price is not None:
                    if state2_exit_reason is None:
                        return self._fill_l2(
                            symbol=symbol,
                            active=active,
                            candle=candle,
                            indicators=indicators,
                            fill_price=l2_fill_price,
                        )
                    active_after_l2 = self._fill_l2(
                        symbol=symbol,
                        active=active,
                        candle=candle,
                        indicators=indicators,
                        fill_price=l2_fill_price,
                        check_hard_sl=state2_exit_reason is None,
                    )
                    if active_after_l2 is None:
                        return None
                    if state2_exit_reason is not None:
                        self._record_state2_exit(
                            symbol,
                            active_after_l2,
                            candle,
                            state2_exit_reason,
                            candle.close,
                            indicators,
                        )
                        self._apply_state2_exit_reset(
                            symbol=symbol,
                            active=active_after_l2,
                            candle=candle,
                            indicators=indicators,
                            reason=state2_exit_reason,
                        )
                        return None
                    return active_after_l2
                if state2_exit_reason is not None:
                    self._record_state2_exit(
                        symbol,
                        active,
                        candle,
                        state2_exit_reason,
                        candle.close,
                        indicators,
                        exit_context,
                    )
                    self._apply_state2_exit_reset(
                        symbol=symbol,
                        active=active,
                        candle=candle,
                        indicators=indicators,
                        reason=state2_exit_reason,
                    )
                    return None
                return active
            if state2_exit_reason is not None:
                self._record_state2_exit(
                    symbol,
                    active,
                    candle,
                    state2_exit_reason,
                    candle.close,
                    indicators,
                    exit_context,
                )
                self._apply_state2_exit_reset(
                    symbol=symbol,
                    active=active,
                    candle=candle,
                    indicators=indicators,
                    reason=state2_exit_reason,
                )
                return None

            self._try_l2_promo_fill(
                symbol=symbol,
                active=active,
                candle=candle,
            )
            if active.pending_l2_promo_fraction > 0.0:
                return active

            if l3_qty <= 0.0:
                l3_price = float(machine.snapshot.entry_prices["L3"] or 0.0)
                if touched(candle, l3_price):
                    machine.on_l3_fill(
                        fill_price=l3_price,
                        fill_qty=pine_contract_qty(active.pending_l3_fraction, l3_price),
                        atr_value=indicators["atr"],
                    )
                    self._sync_exit_context(active)
                    mark_fill(
                        active,
                        event="ENTRY_L3",
                        reason="L3_FILL",
                        ts=candle.timestamp,
                    )
                    self.events.append(
                        event_row(
                            ts=candle.timestamp,
                            symbol=symbol,
                            event="ENTRY_L3",
                            side=active.side,
                            price=l3_price,
                            reason="L3_FILL",
                            cvd=cvd_sign(candle),
                        )
                    )
                    exit_context = self._capture_exit_context(active)
                    if self._check_hard_sl_hit(active, candle):
                        self._remember_active_cooldown(symbol, active)
                        self._record_exit(
                            symbol,
                            active,
                            candle,
                            "HARD_SL",
                            exit_context.hard_sl or l3_price,
                            exit_context,
                        )
                        return None
                return active

        if state == int(StateCode.FILLED_FULL):
            return self._evaluate_full_position(
                symbol=symbol,
                active=active,
                candle=candle,
                indicators=indicators,
                kijun_series=kijun_series,
                allow_take_profit=allow_take_profit,
                take_profit_candle=take_profit_candle,
                take_profit_execution_candle=take_profit_execution_candle,
            )

        if state == int(StateCode.RUNNER):
            runner = RunnerInputs(
                close_prev=prev_candle.close,
                open_cur=candle.open,
                kijun_prev=kijun_series[1],
                kijun_cur=kijun_series[2],
            )
            runner_action = machine.tick(runner=runner)
            if (
                runner_action is not None
                and runner_action.intent == OrderIntent.CLOSE_MARKET
            ):
                self._remember_active_cooldown(symbol, active)
                self._record_exit(
                    symbol,
                    active,
                    candle,
                    runner_action.reason,
                    candle.open,
                )
                return None
            return active

        return active

    def _try_same_bar_l2_fill(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        l2_price = float(active.machine.snapshot.entry_prices["L2"] or 0.0)
        close_fill = marketable_limit_fill_price(active.side, l2_price, candle.close)
        if close_fill is None:
            return active
        return self._fill_l2(
            symbol=symbol,
            active=active,
            candle=candle,
            indicators=indicators,
            fill_price=close_fill,
            reason="L2_FILL_ON_CLOSE",
            defer_recognition=True,
        )

    def _record_deferred_l2_fill(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        fill_price: float,
        reason: str = "L2_FILL",
    ) -> None:
        self._sync_active_clock(active, candle.timestamp)
        active.pending_l2_fill_price = fill_price
        active.pending_l2_fill_ts = candle.timestamp
        active.pending_l2_fill_reason = reason
        self.events.append(
            event_row(
                ts=candle.timestamp,
                symbol=symbol,
                event="ENTRY_L2",
                side=active.side,
                price=fill_price,
                reason=reason,
                cvd=cvd_sign(candle),
            )
        )

    def _recognize_deferred_l2_fill(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
        check_hard_sl: bool = True,
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        fill_price = active.pending_l2_fill_price
        if fill_price is None:
            return active
        fill_ts = active.pending_l2_fill_ts or candle.timestamp
        fill_reason = active.pending_l2_fill_reason
        active.pending_l2_fill_price = None
        active.pending_l2_fill_ts = None
        active.pending_l2_fill_reason = "L2_FILL"
        return self._fill_l2(
            symbol=symbol,
            active=active,
            candle=candle,
            indicators=indicators,
            fill_price=fill_price,
            emit_event=False,
            reason=fill_reason,
            fill_ts=fill_ts,
            check_hard_sl=check_hard_sl,
        )

    def _fill_l2(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
        fill_price: float,
        reason: str = "L2_FILL",
        check_hard_sl: bool = True,
        emit_event: bool = True,
        defer_recognition: bool = False,
        fill_ts: datetime | None = None,
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        if defer_recognition:
            self._record_deferred_l2_fill(
                symbol=symbol,
                active=active,
                candle=candle,
                fill_price=fill_price,
                reason=reason,
            )
            return active

        machine = active.machine
        l2_order_price = float(machine.snapshot.entry_prices["L2"] or fill_price)
        actions = machine.on_l2_fill(
            fill_price=fill_price,
            fill_qty=pine_contract_qty(base_layer_fraction("L2"), l2_order_price),
            atr_value=indicators["atr"],
            poc=indicators["poc"],
            kijun=indicators["kijun"],
            fibo_0618=indicators[f"fibo_{active.side.value}_0618"],
        )
        for state_action in actions:
            if (
                state_action.layer == "L2"
                and state_action.reason == "TRIPLE_CONFLUENCE_RESIZE_L2"
                and state_action.order is not None
            ):
                active.pending_l2_promo_fraction = state_action.order.equity_fraction
                active.pending_l2_promo_price = state_action.order.price
            if state_action.layer == "L3" and state_action.order is not None:
                active.pending_l3_fraction = state_action.order.equity_fraction
        self._sync_exit_context(active)
        mark_fill(
            active,
            event="ENTRY_L2",
            reason=reason,
            ts=fill_ts or candle.timestamp,
        )
        if emit_event:
            self.events.append(
                event_row(
                    ts=candle.timestamp,
                    symbol=symbol,
                    event="ENTRY_L2",
                    side=active.side,
                    price=fill_price,
                    reason=reason,
                    cvd=cvd_sign(candle),
                )
            )
        exit_context = self._capture_exit_context(active)
        if check_hard_sl and self._check_hard_sl_hit(active, candle):
            self._remember_active_cooldown(symbol, active)
            self._record_exit(
                symbol,
                active,
                candle,
                "HARD_SL",
                candle.close,
                exit_context,
            )
            return None
        return active

    def _try_l2_promo_fill(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
    ) -> bool:
        if active.pending_l2_promo_fraction <= 0.0:
            return False
        promo_price = active.pending_l2_promo_price
        if promo_price is None:
            return False
        fill_price = intrabar_limit_fill_price(active.side, promo_price, candle)
        if fill_price is None:
            return False

        active.machine.on_l2_promo_fill(
            fill_price=fill_price,
            fill_qty=pine_contract_qty(active.pending_l2_promo_fraction, promo_price),
        )
        active.pending_l2_promo_fraction = 0.0
        active.pending_l2_promo_price = None
        self._sync_exit_context(active)
        mark_fill(
            active,
            event="ENTRY_L2_PROMO",
            reason="L2_PROMO_FILL",
            ts=candle.timestamp,
        )
        self.events.append(
            event_row(
                ts=candle.timestamp,
                symbol=symbol,
                event="ENTRY_L2_PROMO",
                side=active.side,
                price=fill_price,
                reason="L2_PROMO_FILL",
                cvd=cvd_sign(candle),
            )
        )
        return True

    def _advance_active_over_execution_span(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        execution_candles: list[Candle],
        signal_candle: Candle,
        prev_signal_candle: Candle,
        signal_index: int,
        indicators: dict[str, float],
        kijun_series: list[float],
    ) -> ReplayPosition | None:
        current: ReplayPosition | None = active
        total = len(execution_candles)
        span_candle = self._aggregate_execution_span(execution_candles)
        for offset, execution_candle in enumerate(execution_candles):
            if current is None:
                return None
            is_last_execution = offset == total - 1
            state = current.machine.snapshot.state
            if state == int(StateCode.RUNNER):
                continue
            current = self._advance_active(
                symbol=symbol,
                active=current,
                candle=execution_candle,
                prev_candle=prev_signal_candle,
                index=signal_index,
                indicators=indicators,
                kijun_series=kijun_series,
                allow_state2_exit=is_last_execution,
                allow_take_profit=is_last_execution,
                take_profit_candle=signal_candle,
                take_profit_execution_candle=span_candle,
            )

        if current is None:
            return None
        if current.machine.snapshot.state != int(StateCode.RUNNER):
            return current
        return self._advance_active(
            symbol=symbol,
            active=current,
            candle=signal_candle,
            prev_candle=prev_signal_candle,
            index=signal_index,
            indicators=indicators,
            kijun_series=kijun_series,
            allow_state2_exit=True,
            allow_take_profit=True,
            take_profit_candle=signal_candle,
            take_profit_execution_candle=span_candle,
        )

    def _aggregate_execution_span(self, candles: list[Candle]) -> Candle | None:
        if not candles:
            return None
        return Candle(
            timestamp=candles[-1].timestamp,
            open=candles[0].open,
            high=max(candle.high for candle in candles),
            low=min(candle.low for candle in candles),
            close=candles[-1].close,
            volume=sum(candle.volume for candle in candles),
        )

    def _try_state2_exit(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        reason = self._state2_exit_reason(
            active=active,
            candle=candle,
            indicators=indicators,
        )
        if reason is None:
            return active
        context = self._capture_exit_context(active)
        self._record_state2_exit(
            symbol,
            active,
            candle,
            reason,
            candle.close,
            indicators,
            context,
        )
        self._apply_state2_exit_reset(
            symbol=symbol,
            active=active,
            candle=candle,
            indicators=indicators,
            reason=reason,
        )
        return None

    def _state2_exit_reason(
        self,
        *,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
    ) -> str | None:
        if self.state2_exit_mode == "off":
            return None

        reverse, htf_cross = self._state2_signal_flags(
            active=active,
            candle=candle,
            indicators=indicators,
        )
        if not self._state2_signal_matches(reverse=reverse, htf_cross=htf_cross):
            return None

        context = self._capture_exit_context(active)
        current_r = side_r(candle.close, context.avg_entry, context.risk, active.side)
        if self.state2_profit_hold_r is not None and current_r > self.state2_profit_hold_r:
            return None
        if self.state2_exit_mode == "adverse-only" and current_r > 0.0:
            return None
        hours_since_fill = self._hours_since_first_fill(active, candle.timestamp)
        signal_dead = active.peak_mfe < (EVASION_PEAK_ATR_RATIO * indicators["atr"])
        if hours_since_fill <= EVASION_WINDOW_HOURS and signal_dead:
            return "EVASION"
        if active.machine.snapshot.state == int(StateCode.FILLED_PARTIAL):
            return "STATE_2_ABORT"
        return None

    def _apply_state2_exit_reset(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
        reason: str,
    ) -> None:
        self._sync_active_clock(active, candle.timestamp)
        reverse, htf_cross = self._state2_signal_flags(
            active=active,
            candle=candle,
            indicators=indicators,
        )
        if reason == "EVASION":
            active.machine.check_evasion(
                peak_mfe=active.peak_mfe,
                atr_value=indicators["atr"],
                reverse_spike=reverse,
                htf_cross=htf_cross,
                hours_since_fill=self._hours_since_first_fill(active, candle.timestamp),
            )
            self._remember_active_cooldown(symbol, active)
            return
        if reason == "STATE_2_ABORT":
            active.machine.check_state_2_abort(reverse_spike=reverse, htf_cross=htf_cross)

    def _state2_signal_matches(self, *, reverse: bool, htf_cross: bool) -> bool:
        if self.state2_signal_mode == "any":
            return reverse or htf_cross
        if self.state2_signal_mode == "both":
            return reverse and htf_cross
        if self.state2_signal_mode == "reverse-only":
            return reverse
        if self.state2_signal_mode == "htf-only":
            return htf_cross
        raise ValueError(f"Unsupported state2_signal_mode: {self.state2_signal_mode}")

    def _state2_signal_flags(
        self,
        *,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
    ) -> tuple[bool, bool]:
        reverse = self._reverse_spike_against(active.side, indicators)
        if reverse and self._state2_reverse_l2_hold_blocks(active, candle.timestamp):
            reverse = False
        return reverse, self._htf_cross_against(active.side, indicators)

    def _state2_reverse_l2_hold_blocks(
        self,
        active: ReplayPosition,
        ts: datetime,
    ) -> bool:
        if self.state2_reverse_min_minutes_since_l2 <= 0.0:
            return False
        if active.last_fill_event != "ENTRY_L2" or active.last_fill_ts is None:
            return False
        minutes_since_l2 = (ts - active.last_fill_ts).total_seconds() / 60.0
        return minutes_since_l2 < self.state2_reverse_min_minutes_since_l2

    def _reverse_spike_against(
        self,
        side: TradeSide,
        indicators: dict[str, float],
    ) -> bool:
        key = "reverse_spike_long" if side == TradeSide.LONG else "reverse_spike_short"
        if not bool(indicators.get(key, 0.0)):
            return False
        if self.reverse_spike_min_ratio <= 1.0:
            current_passes = True
        else:
            ratio = reverse_spike_ratio(
                side=side,
                cvd_delta=float(indicators.get("entry_cvd_delta", 0.0)),
                threshold=float(indicators.get("reverse_spike_threshold", 0.0)),
            )
            current_passes = ratio > self.reverse_spike_min_ratio
        if not current_passes:
            return False
        if self.reverse_spike_confirm_bars == 1:
            return True
        prev_key = f"{key}_prev"
        return bool(indicators.get(prev_key, 0.0))

    def _htf_cross_against(
        self,
        side: TradeSide,
        indicators: dict[str, float],
    ) -> bool:
        key = "htf_cross_long" if side == TradeSide.LONG else "htf_cross_short"
        return bool(indicators.get(key, 0.0))

    def _update_peak_mfe(self, active: ReplayPosition, candle: Candle) -> None:
        avg_entry = active.machine.snapshot.avg_entry or active.avg_entry_for_r
        if avg_entry <= 0.0:
            return
        favorable_move = (
            candle.high - avg_entry
            if active.side == TradeSide.LONG
            else avg_entry - candle.low
        )
        active.peak_mfe = max(active.peak_mfe, favorable_move, 0.0)

    def _hours_since_first_fill(self, active: ReplayPosition, ts: datetime) -> float:
        first_fill_raw = active.machine.snapshot.first_fill_ts
        if first_fill_raw is None:
            return max((ts - active.entry_ts).total_seconds() / 3600.0, 0.0)
        first_fill = datetime.fromisoformat(first_fill_raw)
        if first_fill.tzinfo is None:
            first_fill = first_fill.replace(tzinfo=UTC)
        return max((ts - first_fill.astimezone(UTC)).total_seconds() / 3600.0, 0.0)

    def _evaluate_full_position(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
        kijun_series: list[float],
        allow_take_profit: bool = True,
        take_profit_candle: Candle | None = None,
        take_profit_execution_candle: Candle | None = None,
    ) -> ReplayPosition | None:
        self._sync_active_clock(active, candle.timestamp)
        machine = active.machine
        exit_context = self._capture_exit_context(active)
        if self._check_hard_sl_hit(active, candle):
            self._remember_active_cooldown(symbol, active)
            self._record_exit(
                symbol,
                active,
                candle,
                "HARD_SL",
                exit_context.hard_sl or candle.close,
                exit_context,
            )
            return None
        if not allow_take_profit:
            return active

        tp_candle = take_profit_candle or candle
        tp_execution_candle = take_profit_execution_candle or candle
        tp_price = self._take_profit_price(active.side, tp_execution_candle, tp_candle)
        previous_remaining = exit_context.remaining_fraction
        tp = TakeProfitInputs(
            price=tp_price,
            rsi=indicators["rsi"],
            kijun_series=kijun_series,
            fibo_1_0=indicators[f"fibo_{active.side.value}_1000"],
            fibo_1_5=indicators[f"fibo_{active.side.value}_1500"],
            volume=tp_candle.volume,
            volume_sma_20=indicators["volume_sma"],
            use_runner=self.config.use_runner,
            bar_id=int(
                (candle.timestamp if self.tp_intrabar_touch else tp_candle.timestamp)
                .timestamp()
            ),
        )
        action = machine.tick(
            take_profit=tp,
        )
        if action is None:
            return active

        if action.reason in {"TP_A", "TP_B"}:
            fill_price = tp_candle.close if action.reason == "TP_A" else tp_price
            closed_fraction = max(
                previous_remaining
                - max(machine.snapshot.remaining_position_fraction, 0.0),
                0.0,
            )
            active.realized_r += closed_fraction * side_r(
                fill_price,
                exit_context.avg_entry,
                exit_context.risk,
                active.side,
            )
            active.remaining_fraction_for_r = max(
                machine.snapshot.remaining_position_fraction,
                0.0,
            )
            return active

        if action.reason == "TP_C_RUNNER_START":
            active.avg_entry_for_r = exit_context.avg_entry
            active.risk_for_r = exit_context.risk
            active.remaining_fraction_for_r = previous_remaining
            return active

        exit_price = exit_context.hard_sl if action.reason == "HARD_SL" else tp_price
        self._remember_active_cooldown(symbol, active)
        self._record_exit(symbol, active, candle, action.reason, exit_price, exit_context)
        return None

    def _take_profit_price(
        self,
        side: TradeSide,
        execution_candle: Candle,
        signal_candle: Candle,
    ) -> float:
        if not self.tp_intrabar_touch:
            return signal_candle.close
        return execution_candle.high if side == TradeSide.LONG else execution_candle.low

    def _capture_exit_context(self, active: ReplayPosition) -> ExitContext:
        snapshot = active.machine.snapshot
        avg_entry = snapshot.avg_entry or active.avg_entry_for_r
        hard_sl = snapshot.hard_sl
        risk = abs(avg_entry - hard_sl) if hard_sl > 0.0 else active.risk_for_r
        remaining = snapshot.remaining_position_fraction
        if remaining <= 0.0:
            remaining = active.remaining_fraction_for_r
        return ExitContext(
            avg_entry=avg_entry,
            hard_sl=hard_sl,
            risk=risk,
            remaining_fraction=remaining if remaining > 0.0 else 1.0,
        )

    def _sync_exit_context(self, active: ReplayPosition) -> None:
        context = self._capture_exit_context(active)
        if context.avg_entry > 0.0:
            active.avg_entry_for_r = context.avg_entry
        if context.risk > 0.0:
            active.risk_for_r = context.risk
        active.remaining_fraction_for_r = context.remaining_fraction

    def _sync_active_clock(self, active: ReplayPosition, ts: datetime) -> None:
        if active.clock is not None:
            active.clock.ts = ts

    def _check_hard_sl_hit(self, active: ReplayPosition, candle: Candle) -> bool:
        snapshot = active.machine.snapshot
        if snapshot.hard_sl <= 0.0:
            return False
        if active.side == TradeSide.LONG:
            if candle.low > snapshot.hard_sl - REPLAY_STOP_TOUCH_EPSILON:
                return False
        elif candle.high < snapshot.hard_sl + REPLAY_STOP_TOUCH_EPSILON:
            return False
        return active.machine.check_hard_sl_hit(
            bar_low=candle.low,
            bar_high=candle.high,
        )

    def _state_1_timed_out(self, active: ReplayPosition, candle: Candle) -> bool:
        # Pine tracks State 1 timeout in milliseconds, so it stays 48h on any entry TF.
        if candle.timestamp - active.entry_ts < REPLAY_STATE_1_TIMEOUT:
            return False
        return active.machine.check_state_1_timeout(STATE_1_TIMEOUT_BARS)

    def _record_exit(
        self,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        reason: str,
        exit_price: float,
        context: ExitContext | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        context = context or self._capture_exit_context(active)
        rr = active.realized_r + context.remaining_fraction * side_r(
            exit_price,
            context.avg_entry,
            context.risk,
            active.side,
        )
        self.events.append(
            event_row(
                ts=candle.timestamp,
                symbol=symbol,
                event="EXIT",
                side=active.side,
                price=exit_price,
                reason=reason,
                rr=rr,
                win=rr > 0.0,
                cvd=active.entry_cvd_sign,
                extra=metadata,
            )
        )

    def _record_state2_exit(
        self,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        reason: str,
        exit_price: float,
        indicators: dict[str, float],
        context: ExitContext | None = None,
    ) -> None:
        context = context or self._capture_exit_context(active)
        self._record_exit(
            symbol,
            active,
            candle,
            reason,
            exit_price,
            context,
            metadata=self._state2_exit_metadata(
                symbol=symbol,
                active=active,
                candle=candle,
                indicators=indicators,
                context=context,
            ),
        )

    def _state2_exit_metadata(
        self,
        *,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        indicators: dict[str, float],
        context: ExitContext,
    ) -> dict[str, Any]:
        raw_reverse = self._reverse_spike_against(active.side, indicators)
        reverse, htf_cross = self._state2_signal_flags(
            active=active,
            candle=candle,
            indicators=indicators,
        )
        reverse_l2_hold_blocked = raw_reverse and not reverse
        reverse_for_source = reverse or (reverse_l2_hold_blocked and not htf_cross)
        atr_value = float(indicators.get("atr", 0.0))
        current_r = side_r(candle.close, context.avg_entry, context.risk, active.side)
        cvd_delta = float(indicators.get("entry_cvd_delta", 0.0))
        cvd_delta_prev = float(indicators.get("entry_cvd_delta_prev", 0.0))
        reverse_threshold = float(indicators.get("reverse_spike_threshold", 0.0))
        reverse_threshold_prev = float(indicators.get("reverse_spike_threshold_prev", 0.0))
        reverse_ratio = reverse_spike_ratio(
            side=active.side,
            cvd_delta=cvd_delta,
            threshold=reverse_threshold,
        )
        reverse_ratio_prev = reverse_spike_ratio(
            side=active.side,
            cvd_delta=cvd_delta_prev,
            threshold=reverse_threshold_prev,
        )
        reverse_prev_key = (
            "reverse_spike_long_prev" if active.side == TradeSide.LONG else "reverse_spike_short_prev"
        )
        minutes_since_last_fill = (
            (candle.timestamp - active.last_fill_ts).total_seconds() / 60.0
            if active.last_fill_ts is not None
            else None
        )
        fill_qtys = active.machine.snapshot.fill_qtys
        return {
            "state2_trigger_source": state2_trigger_source(
                reverse=reverse_for_source,
                htf_cross=htf_cross,
            ),
            "state2_reverse_spike": reverse_for_source,
            "state2_reverse_spike_effective": reverse,
            "state2_reverse_l2_hold_blocked": reverse_l2_hold_blocked,
            "state2_htf_cross": htf_cross,
            "state2_current_r": round(current_r, 6),
            "state2_peak_mfe": round(active.peak_mfe, 8),
            "state2_atr": round(atr_value, 8),
            "state2_hours_since_fill": round(
                self._hours_since_first_fill(active, candle.timestamp),
                6,
            ),
            "state2_signal_mode": self.state2_signal_mode,
            "state2_active_rsm": self._reverse_spike_multiplier(symbol),
            "state2_reverse_spike_confirm_bars": self.reverse_spike_confirm_bars,
            "state2_reverse_min_minutes_since_l2": round(
                self.state2_reverse_min_minutes_since_l2,
                6,
            ),
            "state2_reverse_spike_prev": bool(indicators.get(reverse_prev_key, 0.0)),
            "state2_last_fill_event": active.last_fill_event,
            "state2_last_fill_reason": active.last_fill_reason,
            "state2_minutes_since_last_fill": round(minutes_since_last_fill, 6)
            if minutes_since_last_fill is not None
            else None,
            "state2_l2_filled": float(fill_qtys.get("L2", 0.0)) > 0.0,
            "state2_l3_filled": float(fill_qtys.get("L3", 0.0)) > 0.0,
            "state2_cvd_delta": round(cvd_delta, 8),
            "state2_cvd_delta_prev": round(cvd_delta_prev, 8),
            "state2_reverse_spike_abs_sma_20": round(
                float(indicators.get("reverse_spike_abs_sma_20", 0.0)),
                8,
            ),
            "state2_reverse_spike_abs_sma_20_prev": round(
                float(indicators.get("reverse_spike_abs_sma_20_prev", 0.0)),
                8,
            ),
            "state2_reverse_spike_threshold": round(reverse_threshold, 8),
            "state2_reverse_spike_threshold_prev": round(reverse_threshold_prev, 8),
            "state2_reverse_spike_ratio": round(reverse_ratio, 8),
            "state2_reverse_spike_ratio_prev": round(reverse_ratio_prev, 8),
            "state2_reverse_spike_margin": round(cvd_delta + reverse_threshold, 8)
            if active.side == TradeSide.LONG
            else round(cvd_delta - reverse_threshold, 8),
        }

    def _symbol_cooldown_active(self, symbol: str, ts: datetime) -> bool:
        cooldown_until = self.symbol_cooldowns.get(symbol)
        if cooldown_until is None:
            return False
        return ts < cooldown_until

    def _remember_active_cooldown(self, symbol: str, active: ReplayPosition) -> None:
        raw = active.machine.snapshot.cooldown_until
        if not raw:
            return
        cooldown_until = datetime.fromisoformat(raw)
        if cooldown_until.tzinfo is None:
            cooldown_until = cooldown_until.replace(tzinfo=UTC)
        cooldown_until = cooldown_until.astimezone(UTC)
        previous = self.symbol_cooldowns.get(symbol)
        if previous is None or cooldown_until > previous:
            self.symbol_cooldowns[symbol] = cooldown_until

    def _force_close(
        self,
        symbol: str,
        active: ReplayPosition,
        candle: Candle,
        reason: str,
    ) -> None:
        if active.machine.snapshot.state in {int(StateCode.PENDING), int(StateCode.IDLE)}:
            return
        self._record_exit(symbol, active, candle, reason, candle.close)


def run_replay(
    *,
    config_path: Path,
    cache_dir: Path,
    days: int,
    output_path: Path,
    symbols: list[str] | None = None,
    entry_timeframe: str | None = None,
    execution_timeframe: str | None = None,
    htf_timeframe: str | None = None,
    state2_exit_mode: str = "all",
    state2_signal_mode: str = "any",
    state2_profit_hold_r: float | None = None,
    l3_max_distance_atr: float | None = None,
    reverse_spike_multiplier: float = 3.0,
    symbol_reverse_spike_multipliers: dict[str, float] | None = None,
    reverse_spike_min_ratio: float = 1.0,
    reverse_spike_confirm_bars: int = 1,
    state2_reverse_min_minutes_since_l2: float = 0.0,
    tp_intrabar_touch: bool = False,
    cvd_entry_mode: str = "pine-ltf",
) -> ReplayResult:
    config = load_config(config_path)
    selected_symbols = symbols or config.symbols
    replay = OfflineReplay(
        config=config,
        cache_dir=cache_dir,
        days=days,
        output_path=output_path,
        entry_timeframe=entry_timeframe,
        execution_timeframe=execution_timeframe,
        htf_timeframe=htf_timeframe,
        state2_exit_mode=state2_exit_mode,
        state2_signal_mode=state2_signal_mode,
        state2_profit_hold_r=state2_profit_hold_r,
        l3_max_distance_atr=l3_max_distance_atr,
        reverse_spike_multiplier=reverse_spike_multiplier,
        symbol_reverse_spike_multipliers=symbol_reverse_spike_multipliers,
        reverse_spike_min_ratio=reverse_spike_min_ratio,
        reverse_spike_confirm_bars=reverse_spike_confirm_bars,
        state2_reverse_min_minutes_since_l2=state2_reverse_min_minutes_since_l2,
        tp_intrabar_touch=tp_intrabar_touch,
        cvd_entry_mode=cvd_entry_mode,
    )
    return replay.run(selected_symbols)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline MTS-V1 replay from local OHLCV cache")
    parser.add_argument("--config", type=Path, default=ROOT_DIR / "config.yaml")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--symbols", default="")
    parser.add_argument("--entry-timeframe", help="Optional replay-only override, e.g. 15m, 30m, 1h.")
    parser.add_argument(
        "--execution-timeframe",
        help="Optional lower-timeframe fill/SL replay while keeping entry indicators on entry-timeframe.",
    )
    parser.add_argument("--htf-timeframe", help="Optional replay-only override, e.g. 4h.")
    parser.add_argument(
        "--state2-exit-mode",
        choices=sorted(STATE2_EXIT_MODES),
        default="all",
        help="Replay experiment mode for State 2 reverse/HTF exits.",
    )
    parser.add_argument(
        "--state2-signal-mode",
        choices=sorted(STATE2_SIGNAL_MODES),
        default="any",
        help="Replay experiment: which State 2 signal family may trigger abort/evasion.",
    )
    parser.add_argument(
        "--state2-profit-hold-r",
        type=float,
        help="Replay experiment: keep State 2 partial positions when current R is above this threshold.",
    )
    parser.add_argument(
        "--l3-max-distance-atr",
        type=float,
        help="Replay experiment: cap L3 distance from L2 in ATR units.",
    )
    parser.add_argument(
        "--reverse-spike-multiplier",
        type=float,
        default=3.0,
        help="Replay experiment: CVD reverse-spike multiplier.",
    )
    parser.add_argument(
        "--symbol-reverse-spike-multipliers",
        default="",
        help="Replay experiment: comma-separated asset overrides, e.g. BTC=6.3,ETH=6.8.",
    )
    parser.add_argument(
        "--reverse-spike-min-ratio",
        type=float,
        default=1.0,
        help=(
            "Replay experiment: require adverse CVD delta / threshold to exceed this ratio; "
            "1.0 preserves strict Pine-style threshold crossing."
        ),
    )
    parser.add_argument(
        "--reverse-spike-confirm-bars",
        type=int,
        default=1,
        choices=(1, 2),
        help="Replay experiment: require this many consecutive reverse-spike bars.",
    )
    parser.add_argument(
        "--state2-reverse-min-minutes-since-l2",
        type=float,
        default=0.0,
        help=(
            "Replay experiment: suppress State2 reverse-spike exits until this many "
            "minutes have passed after the latest L2 fill. 0 preserves default behavior."
        ),
    )
    parser.add_argument(
        "--tp-intrabar-touch",
        action="store_true",
        help="Replay experiment: evaluate TP B/C price hits from execution-timeframe highs/lows.",
    )
    parser.add_argument(
        "--cvd-entry-mode",
        choices=sorted(CVD_ENTRY_MODES),
        default="pine-ltf",
        help="Replay experiment: Pine uses one LTF delta; SPEC text also allows 30m aggregation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_replay(
        config_path=args.config,
        cache_dir=args.cache_dir,
        days=args.days,
        output_path=args.output,
        symbols=parse_symbol_override(args.symbols),
        entry_timeframe=args.entry_timeframe,
        execution_timeframe=args.execution_timeframe,
        htf_timeframe=args.htf_timeframe,
        state2_exit_mode=args.state2_exit_mode,
        state2_signal_mode=args.state2_signal_mode,
        state2_profit_hold_r=args.state2_profit_hold_r,
        l3_max_distance_atr=args.l3_max_distance_atr,
        reverse_spike_multiplier=args.reverse_spike_multiplier,
        symbol_reverse_spike_multipliers=parse_symbol_float_map(
            args.symbol_reverse_spike_multipliers,
        ),
        reverse_spike_min_ratio=args.reverse_spike_min_ratio,
        reverse_spike_confirm_bars=args.reverse_spike_confirm_bars,
        state2_reverse_min_minutes_since_l2=args.state2_reverse_min_minutes_since_l2,
        tp_intrabar_touch=args.tp_intrabar_touch,
        cvd_entry_mode=args.cvd_entry_mode,
    )
    print(
        f"[offline-replay] events={result.events} exits={result.exits} "
        f"symbols={len(result.symbols)} output={result.output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
