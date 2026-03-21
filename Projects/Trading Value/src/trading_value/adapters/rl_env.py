"""Gymnasium-compatible reinforcement learning environment for Trading Value.

Wraps the Trading Value indicator/regime pipeline into a standard Gymnasium
interface so that RL agents (PPO, DQN, etc. via stable-baselines3) can learn
trading policies on historical OHLCV data.

Episode = one pass through ``episode_bars`` 30-minute bars.
"""
from __future__ import annotations

import bisect
from datetime import datetime
from enum import IntEnum

import gymnasium
import numpy as np
import pandas as pd

from ..core.indicators import build_all_snapshots
from ..core.models import (
    CloudPosition,
    ProfileBias,
    Timeframe,
    TimeframeSnapshot,
    TkState,
)
from ..core.regime import (
    H1Bias,
    M30Bias,
    RegimeSnapshot,
    classify_regime,
)


# ---------------------------------------------------------------------------
# Action enum (for readability; the space itself is Discrete(5))
# ---------------------------------------------------------------------------

class Action(IntEnum):
    HOLD = 0
    OPEN_LONG = 1
    OPEN_SHORT = 2
    CLOSE = 3
    REVERSE = 4


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------

_CLOUD_MAP: dict[str, float] = {
    CloudPosition.ABOVE: 1.0,
    CloudPosition.IN: 0.0,
    CloudPosition.BELOW: -1.0,
}

_TK_MAP: dict[str, float] = {
    TkState.BULLISH: 1.0,
    TkState.BEARISH: -1.0,
}

_PROFILE_MAP: dict[str, float] = {
    ProfileBias.ABOVE_VA: 1.0,
    ProfileBias.INSIDE_VA: 0.0,
    ProfileBias.BELOW_VA: -1.0,
}

_HTF_MAP: dict[str, float] = {
    "HTF_BULLISH": 1.0,
    "HTF_NEUTRAL": 0.0,
    "HTF_BEARISH": -1.0,
}

_H1_MAP: dict[str, float] = {
    "H1_BULLISH": 1.0,
    "H1_NEUTRAL": 0.0,
    "H1_BEARISH": -1.0,
}

_M30_MAP: dict[str, float] = {
    "M30_BULLISH": 1.0,
    "M30_NEUTRAL": 0.0,
    "M30_BEARISH": -1.0,
}

# Mode encoding: normalized to [-1, 1] range
_MODE_MAP: dict[str, float] = {
    "MODE_TREND_LONG": 1.0,
    "MODE_PULLBACK_LONG": 0.33,
    "MODE_REBOUND_SHORT": -0.33,
    "MODE_NO_TRADE": -1.0,
}

# Profile window defaults (same as backtest adapter)
_PROFILE_WINDOWS: dict[Timeframe, int | None] = {
    Timeframe.H4: 90,
    Timeframe.H1: 120,
    Timeframe.M30: 96,
}


# ---------------------------------------------------------------------------
# TradingEnv
# ---------------------------------------------------------------------------

class TradingEnv(gymnasium.Env):
    """Gymnasium environment for crypto futures trading.

    The agent observes market state (indicators, regime, position) and
    takes discrete actions (hold, long, short, close).

    Episode = one pass through the data (e.g., 30 days of 30m bars).
    """

    metadata = {"render_modes": ["human"]}

    # -----------------------------------------------------------------
    # Init
    # -----------------------------------------------------------------

    def __init__(
        self,
        data: dict[Timeframe, pd.DataFrame],
        symbol: str = "ETHUSDT",
        initial_balance: float = 10000.0,
        commission_rate: float = 0.0002,
        risk_pct: float = 0.0035,
        episode_bars: int = 1440,  # 30 days of 30m bars
        random_start: bool = True,
        min_rr: float = 1.5,
        max_hold_bars: int = 48,
        render_mode: str | None = None,
    ):
        super().__init__()

        self.symbol = symbol
        self.initial_balance = initial_balance
        self.commission_rate = commission_rate
        self.risk_pct = risk_pct
        self.episode_bars = episode_bars
        self.random_start = random_start
        self.min_rr = min_rr
        self.max_hold_bars = max_hold_bars
        self.render_mode = render_mode

        # --- Spaces ---
        # 25-dimensional continuous observation vector
        self.observation_space = gymnasium.spaces.Box(
            low=-5.0, high=5.0, shape=(25,), dtype=np.float32,
        )
        # 5 discrete actions
        self.action_space = gymnasium.spaces.Discrete(5)

        # --- Store raw data & pre-compute ---
        self._raw_data = data
        self._precompute_snapshots()

        # --- Episode state (set properly in reset) ---
        self._step_idx: int = 0
        self._start_idx: int = 0
        self._balance: float = initial_balance
        self._peak_balance: float = initial_balance
        self._position: int = 0  # -1 short, 0 flat, 1 long
        self._entry_price: float = 0.0
        self._stop_price: float = 0.0
        self._position_qty: float = 0.0
        self._bars_held: int = 0
        self._consecutive_losses: int = 0
        self._total_commission: float = 0.0

    # -----------------------------------------------------------------
    # Pre-compute snapshots (O(N) per timeframe)
    # -----------------------------------------------------------------

    def _precompute_snapshots(self) -> None:
        """Use build_all_snapshots for each timeframe. Store as dict[timestamp, snapshot]."""
        self._snapshot_cache: dict[Timeframe, dict[datetime, TimeframeSnapshot]] = {}
        self._sorted_keys: dict[Timeframe, list[datetime]] = {}

        for tf, df in self._raw_data.items():
            if df.empty:
                continue
            pw = _PROFILE_WINDOWS.get(tf)
            cache = build_all_snapshots(df, tf, profile_window=pw)
            self._snapshot_cache[tf] = cache
            self._sorted_keys[tf] = sorted(cache.keys())

        # Build the primary (30m) bar timeline — this drives step()
        m30_df = self._raw_data.get(Timeframe.M30)
        if m30_df is None or m30_df.empty:
            raise ValueError("30m data is required for the RL environment")

        # Ensure timestamp column exists
        if "timestamp" not in m30_df.columns:
            if m30_df.index.name == "timestamp":
                m30_df = m30_df.reset_index()
            else:
                raise ValueError("30m DataFrame must have a 'timestamp' column or index")

        self._m30_df: pd.DataFrame = m30_df.reset_index(drop=True)
        self._m30_timestamps: list[datetime] = self._m30_df["timestamp"].tolist()
        self._m30_closes: np.ndarray = self._m30_df["close"].values.astype(np.float64)
        self._m30_highs: np.ndarray = self._m30_df["high"].values.astype(np.float64)
        self._m30_lows: np.ndarray = self._m30_df["low"].values.astype(np.float64)
        self._m30_volumes: np.ndarray = self._m30_df["volume"].values.astype(np.float64)

        # Determine the earliest M30 index where ALL timeframe snapshots exist
        self._min_valid_idx = self._compute_min_valid_idx()

    def _compute_min_valid_idx(self) -> int:
        """Find the first M30 bar index where snapshots for ALL 3 TFs are available."""
        required_tfs = [Timeframe.H4, Timeframe.H1, Timeframe.M30]
        for i, ts in enumerate(self._m30_timestamps):
            all_present = True
            for tf in required_tfs:
                snap = self._get_snapshot_at(tf, ts)
                if snap is None:
                    all_present = False
                    break
            if all_present:
                return i
        # Fallback: if no valid index found, use conservative default
        return min(60, len(self._m30_timestamps) - 1)

    # -----------------------------------------------------------------
    # Reset
    # -----------------------------------------------------------------

    def reset(
        self, seed: int | None = None, options: dict | None = None,
    ) -> tuple[np.ndarray, dict]:
        """Reset environment to a new episode.

        If random_start: pick a random start point in the data.
        Otherwise: start from the beginning.
        """
        super().reset(seed=seed)

        max_start = len(self._m30_df) - self.episode_bars
        if max_start < self._min_valid_idx:
            max_start = self._min_valid_idx

        if self.random_start and max_start > self._min_valid_idx:
            self._start_idx = self.np_random.integers(
                self._min_valid_idx, max_start,
            )
        else:
            self._start_idx = self._min_valid_idx

        self._step_idx = self._start_idx
        self._balance = self.initial_balance
        self._peak_balance = self.initial_balance
        self._position = 0
        self._entry_price = 0.0
        self._stop_price = 0.0
        self._position_qty = 0.0
        self._bars_held = 0
        self._consecutive_losses = 0
        self._total_commission = 0.0

        obs = self._build_observation()
        info = self._build_info()
        return obs, info

    # -----------------------------------------------------------------
    # Step
    # -----------------------------------------------------------------

    def step(self, action: int) -> tuple[np.ndarray, float, bool, bool, dict]:
        """Execute one step (one 30m bar).

        1. Apply action (open/close position)
        2. Advance to next bar
        3. Update position PnL
        4. Compute reward
        5. Check if episode is done

        Returns (observation, reward, terminated, truncated, info)
        """
        reward = 0.0
        current_close = float(self._m30_closes[self._step_idx])
        current_atr = self._get_atr_at_step()

        # ---- 1. Apply action ----
        reward += self._apply_action(action, current_close, current_atr)

        # ---- 2. Advance to next bar ----
        self._step_idx += 1
        if self._position != 0:
            self._bars_held += 1

        # ---- 3. Check episode boundaries ----
        terminated = False
        truncated = False

        if self._step_idx >= len(self._m30_df):
            truncated = True
        elif self._step_idx >= self._start_idx + self.episode_bars:
            truncated = True

        if truncated and self._position != 0:
            # Force-close at end of episode
            new_close = float(self._m30_closes[min(self._step_idx, len(self._m30_df) - 1)])
            reward += self._close_position(new_close)

        # ---- 4. Check stop loss (1R) ----
        if not truncated and self._position != 0:
            new_close = float(self._m30_closes[self._step_idx])
            new_high = float(self._m30_highs[self._step_idx])
            new_low = float(self._m30_lows[self._step_idx])

            stopped = False
            if self._position == 1 and new_low <= self._stop_price:
                # Long stopped out at stop price
                reward += self._close_position(self._stop_price, stopped_out=True)
                stopped = True
            elif self._position == -1 and new_high >= self._stop_price:
                # Short stopped out at stop price
                reward += self._close_position(self._stop_price, stopped_out=True)
                stopped = True

            # Max hold exit
            if not stopped and self._bars_held >= self.max_hold_bars:
                reward += self._close_position(new_close)

        # ---- 5. Holding cost ----
        if self._position != 0:
            reward -= 0.001 * self._bars_held

        # ---- 6. Drawdown penalty ----
        if self._balance < self._peak_balance:
            dd_pct = (self._peak_balance - self._balance) / self._peak_balance
            reward -= 0.5 * dd_pct

        # ---- 7. Build observation ----
        if truncated:
            obs = np.zeros(25, dtype=np.float32)
        else:
            obs = self._build_observation()

        info = self._build_info()
        return obs, float(reward), terminated, truncated, info

    # -----------------------------------------------------------------
    # Action application
    # -----------------------------------------------------------------

    def _apply_action(
        self, action: int, current_close: float, current_atr: float,
    ) -> float:
        """Apply the agent's action and return immediate reward component.

        Commission is accounted for in _close_position (in R units, round-trip).
        No separate commission_r penalty here to avoid double-counting.
        """
        reward = 0.0

        if action == Action.HOLD:
            pass

        elif action == Action.OPEN_LONG:
            if self._position == 0:
                self._open_position(1, current_close, current_atr)

        elif action == Action.OPEN_SHORT:
            if self._position == 0:
                self._open_position(-1, current_close, current_atr)

        elif action == Action.CLOSE:
            if self._position != 0:
                reward += self._close_position(current_close)

        elif action == Action.REVERSE:
            if self._position != 0:
                old_side = self._position
                reward += self._close_position(current_close)
                new_side = -old_side
                self._open_position(new_side, current_close, current_atr)

        return reward

    def _open_position(
        self, side: int, price: float, atr: float,
    ) -> None:
        """Open a new position (side: 1=long, -1=short)."""
        self._position = side
        self._entry_price = price
        self._bars_held = 0

        # Stop loss at 1R = 1 ATR distance
        risk_distance = max(atr, price * 0.001)  # floor at 0.1% of price
        if side == 1:
            self._stop_price = price - risk_distance
        else:
            self._stop_price = price + risk_distance

        # Position sizing: risk_pct of balance
        risk_amount = self._balance * self.risk_pct
        self._position_qty = risk_amount / risk_distance if risk_distance > 0 else 0.0

        # Charge commission
        comm = price * self._position_qty * self.commission_rate
        self._balance -= comm
        self._total_commission += comm

    def _close_position(
        self, price: float, stopped_out: bool = False,
    ) -> float:
        """Close the current position and return reward in R units.

        Commission is computed as actual round-trip cost in R units and
        applied once here (not at open time in reward, only in balance).
        """
        if self._position == 0:
            return 0.0

        # PnL calculation
        if self._position == 1:
            raw_pnl = (price - self._entry_price) * self._position_qty
        else:
            raw_pnl = (self._entry_price - price) * self._position_qty

        # Commission on close (balance tracking only)
        close_comm = price * self._position_qty * self.commission_rate
        self._balance -= close_comm
        self._total_commission += close_comm

        # Risk amount for R-unit conversion
        risk_distance = abs(self._entry_price - self._stop_price)
        risk_amount = risk_distance * self._position_qty

        # Actual round-trip commission in R units
        round_trip_comm = (
            self._entry_price * self._position_qty * self.commission_rate
            + price * self._position_qty * self.commission_rate
        )
        commission_r = round_trip_comm / risk_amount if risk_amount > 0 else 0.0

        # PnL in R units (raw, before commission)
        raw_pnl_r = raw_pnl / risk_amount if risk_amount > 0 else 0.0

        # Net reward in R units = raw PnL_R - commission_R (applied once)
        pnl_r = raw_pnl_r - commission_r

        # Update balance (raw PnL; open+close commissions already deducted from balance)
        self._balance += raw_pnl
        if self._balance > self._peak_balance:
            self._peak_balance = self._balance

        # Track consecutive losses
        net_pnl = raw_pnl - round_trip_comm
        if net_pnl < 0:
            self._consecutive_losses = min(self._consecutive_losses + 1, 5)
        else:
            self._consecutive_losses = 0

        # Reward = realized PnL in R units (commission included) + bonus
        reward = pnl_r
        if pnl_r > 0:
            reward += 0.2  # bonus for profitable close

        # Reset position
        self._position = 0
        self._entry_price = 0.0
        self._stop_price = 0.0
        self._position_qty = 0.0
        self._bars_held = 0

        return reward

    # -----------------------------------------------------------------
    # Observation builder
    # -----------------------------------------------------------------

    def _build_observation(self) -> np.ndarray:
        """Build the 25-dim observation vector from current state."""
        _SENTINEL = -1.0  # distinct from any valid encoding {-1, 0, 1}
        obs = np.full(25, _SENTINEL, dtype=np.float32)
        ts = self._m30_timestamps[self._step_idx]
        current_close = float(self._m30_closes[self._step_idx])

        # Get snapshots for each timeframe at current timestamp
        snap_4h = self._get_snapshot_at(Timeframe.H4, ts)
        snap_1h = self._get_snapshot_at(Timeframe.H1, ts)
        snap_30m = self._get_snapshot_at(Timeframe.M30, ts)

        # [0-2] 4h: cloud_position, tk_state, profile_bias
        if snap_4h is not None:
            obs[0] = _CLOUD_MAP.get(snap_4h.cloud_position, 0.0)
            obs[1] = _TK_MAP.get(snap_4h.tk_state, 0.0)
            obs[2] = _PROFILE_MAP.get(snap_4h.profile_bias, 0.0)

        # [3-5] 1h: same 3 features
        if snap_1h is not None:
            obs[3] = _CLOUD_MAP.get(snap_1h.cloud_position, 0.0)
            obs[4] = _TK_MAP.get(snap_1h.tk_state, 0.0)
            obs[5] = _PROFILE_MAP.get(snap_1h.profile_bias, 0.0)

        # [6-8] 30m: same 3 features
        if snap_30m is not None:
            obs[6] = _CLOUD_MAP.get(snap_30m.cloud_position, 0.0)
            obs[7] = _TK_MAP.get(snap_30m.tk_state, 0.0)
            obs[8] = _PROFILE_MAP.get(snap_30m.profile_bias, 0.0)

        # [9] position: -1(short), 0(flat), 1(long)
        obs[9] = float(self._position)

        # [10] unrealized_pnl_r: normalized unrealized PnL in R units
        if self._position != 0:
            risk_dist = abs(self._entry_price - self._stop_price)
            if risk_dist > 0:
                if self._position == 1:
                    unrealized = (current_close - self._entry_price) / risk_dist
                else:
                    unrealized = (self._entry_price - current_close) / risk_dist
                obs[10] = np.clip(unrealized, -5.0, 5.0)

        # [11] atr_normalized: ATR / close (volatility proxy)
        atr = self._get_atr_at_step()
        obs[11] = np.clip(atr / current_close, 0.0, 5.0) if current_close > 0 else 0.0

        # [12-16] last 5 bar returns (close_change / ATR)
        for j in range(5):
            idx = self._step_idx - j
            if idx > 0 and atr > 0:
                ret = (
                    float(self._m30_closes[idx])
                    - float(self._m30_closes[idx - 1])
                ) / atr
                obs[12 + j] = np.clip(ret, -5.0, 5.0)

        # [17] distance_to_nearest_zone / ATR
        if snap_30m is not None and atr > 0:
            # Use VAH, VAL, POC as proxy zones
            zone_levels = []
            for s in (snap_4h, snap_1h, snap_30m):
                if s is not None:
                    if s.vah > 0:
                        zone_levels.append(s.vah)
                    if s.val > 0:
                        zone_levels.append(s.val)
                    if s.poc > 0:
                        zone_levels.append(s.poc)
            if zone_levels:
                min_dist = min(abs(current_close - z) for z in zone_levels)
                obs[17] = np.clip(min_dist / atr, 0.0, 5.0)

        # [18] volume_ratio: current_volume / sma_20
        if snap_30m is not None and snap_30m.volume_sma_20 > 0:
            obs[18] = np.clip(
                snap_30m.volume / snap_30m.volume_sma_20, 0.0, 5.0,
            )

        # [19] consecutive_losses: normalized to [0, 1] (max 5 -> 1.0)
        obs[19] = float(self._consecutive_losses) / 5.0

        # [20] time_in_position: bars since entry (normalized to 0-1)
        if self._position != 0 and self.max_hold_bars > 0:
            obs[20] = min(float(self._bars_held) / self.max_hold_bars, 1.0)

        # [21-24] regime encoding
        regime = self._get_regime_at_step()
        if regime is not None:
            obs[21] = _HTF_MAP.get(regime.htf.value, 0.0)
            obs[22] = _H1_MAP.get(regime.h1.value, 0.0)
            obs[23] = _M30_MAP.get(regime.m30.value, 0.0)
            # Mode: derive from regime combination
            mode = self._infer_mode(regime)
            obs[24] = _MODE_MAP.get(mode, -1.0)

        return obs

    # -----------------------------------------------------------------
    # Snapshot / regime helpers
    # -----------------------------------------------------------------

    def _get_snapshot_at(
        self, tf: Timeframe, ts: datetime,
    ) -> TimeframeSnapshot | None:
        """Get the most recent snapshot at or before timestamp for a timeframe."""
        keys = self._sorted_keys.get(tf)
        cache = self._snapshot_cache.get(tf)
        if not keys or not cache:
            return None
        idx = bisect.bisect_right(keys, ts) - 1
        if idx < 0:
            return None
        return cache[keys[idx]]

    def _get_atr_at_step(self) -> float:
        """Get ATR from the 30m snapshot at the current step."""
        ts = self._m30_timestamps[self._step_idx]
        snap = self._get_snapshot_at(Timeframe.M30, ts)
        if snap is not None and snap.atr > 0:
            return snap.atr
        # Fallback: simple range estimate
        close = float(self._m30_closes[self._step_idx])
        return close * 0.005  # 0.5% as rough fallback

    def _get_regime_at_step(self) -> RegimeSnapshot | None:
        """Classify regime at the current step."""
        ts = self._m30_timestamps[self._step_idx]
        snap_4h = self._get_snapshot_at(Timeframe.H4, ts)
        snap_1h = self._get_snapshot_at(Timeframe.H1, ts)
        snap_30m = self._get_snapshot_at(Timeframe.M30, ts)
        if snap_4h is None or snap_1h is None or snap_30m is None:
            return None
        snapshots = {
            Timeframe.H4: snap_4h,
            Timeframe.H1: snap_1h,
            Timeframe.M30: snap_30m,
        }
        return classify_regime(snapshots)

    @staticmethod
    def _infer_mode(regime: RegimeSnapshot) -> str:
        """Infer trading mode from regime snapshot (simplified)."""
        htf = regime.htf.value
        h1 = regime.h1.value
        m30 = regime.m30.value

        if htf == "HTF_BULLISH" and h1 == "H1_BULLISH" and m30 == "M30_BULLISH":
            return "MODE_TREND_LONG"
        if htf == "HTF_BULLISH" and h1 != "H1_BEARISH":
            return "MODE_PULLBACK_LONG"
        if htf == "HTF_BEARISH" and m30 == "M30_BEARISH":
            return "MODE_REBOUND_SHORT"
        return "MODE_NO_TRADE"

    # -----------------------------------------------------------------
    # Render
    # -----------------------------------------------------------------

    def render(self) -> None:
        """Print current state: bar, position, PnL, regime."""
        if self._step_idx >= len(self._m30_df):
            print("[TradingEnv] Episode ended.")
            return

        ts = self._m30_timestamps[self._step_idx]
        close = float(self._m30_closes[self._step_idx])
        regime = self._get_regime_at_step()
        regime_str = (
            f"HTF={regime.htf.value} H1={regime.h1.value} M30={regime.m30.value}"
            if regime else "N/A"
        )
        pos_str = {1: "LONG", -1: "SHORT", 0: "FLAT"}[self._position]
        pnl = self._balance - self.initial_balance

        print(
            f"[{ts}] close={close:.2f} | pos={pos_str} "
            f"| balance={self._balance:.2f} (PnL={pnl:+.2f}) "
            f"| bars_held={self._bars_held} | {regime_str}"
        )

    # -----------------------------------------------------------------
    # Info dict
    # -----------------------------------------------------------------

    def _build_info(self) -> dict:
        """Build the info dict returned by step/reset."""
        return {
            "balance": self._balance,
            "peak_balance": self._peak_balance,
            "position": self._position,
            "bars_held": self._bars_held,
            "consecutive_losses": self._consecutive_losses,
            "total_commission": self._total_commission,
            "step_idx": self._step_idx,
        }
