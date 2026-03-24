"""Persistent trading memory for the AI trader.

Remembers everything across sessions so the AI trader gets progressively better.

Stored in .tq-journal/memory/

Files:
- best-params.json: Best parameter set per strategy (cumulative best)
- tried-params.json: All parameter combinations tried + their results
- mistakes.json: Patterns that led to losses (never repeat)
- insights.json: Patterns that led to profits (reinforce)
- history.json: Full history of all auto-improve sessions
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TradingMemory:
    """Persistent memory for the AI trader. Remembers everything.

    Uses an in-memory cache to avoid repeated disk I/O during a session.
    Data is loaded lazily on first access and written through on every mutation.
    """

    MEMORY_DIR = Path(".tq-journal/memory")

    def __init__(self, memory_dir: Path | str | None = None):
        if memory_dir is not None:
            self.MEMORY_DIR = Path(memory_dir)
        self.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, Any] = {}
        self._dirty: set[str] = set()  # files modified since last flush
        self._write_count = 0
        self._flush_interval = 50  # flush to disk every N writes

    # ── File I/O helpers ──

    def _load_json(self, filename: str) -> Any:
        """Load JSON from cache, falling back to disk on first access."""
        if filename in self._cache:
            return self._cache[filename]
        path = self.MEMORY_DIR / filename
        if not path.exists():
            data: Any = {}
        else:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load %s: %s", path, exc)
                data = {}
        self._cache[filename] = data
        return data

    def _save_json(self, filename: str, data: Any) -> None:
        """Save to cache immediately, flush to disk periodically."""
        self._cache[filename] = data
        self._dirty.add(filename)
        self._write_count += 1
        if self._write_count >= self._flush_interval:
            self.flush()

    def flush(self) -> None:
        """Write all dirty cache entries to disk."""
        for filename in self._dirty:
            if filename in self._cache:
                path = self.MEMORY_DIR / filename
                path.write_text(
                    json.dumps(self._cache[filename], indent=2,
                               ensure_ascii=False, default=str),
                    encoding="utf-8",
                )
        self._dirty.clear()
        self._write_count = 0

    def _invalidate_cache(self, filename: str | None = None) -> None:
        """Clear cache for a file or all files."""
        if filename:
            self._cache.pop(filename, None)
        else:
            self._cache.clear()

    def compact(self) -> None:
        """Trim oversized files to prevent unbounded growth.

        - mistakes: keep only last 500 entries
        - insights: keep only last 500 entries
        - tried-params: keep only last 200 per strategy
        """
        # Trim mistakes
        data = self._load_json("mistakes.json")
        ml = data.get("mistakes", [])
        if len(ml) > 500:
            data["mistakes"] = ml[-500:]
            self._save_json("mistakes.json", data)
            logger.info("Compacted mistakes: %d -> 500", len(ml))

        # Trim insights
        data = self._load_json("insights.json")
        il = data.get("insights", [])
        if len(il) > 500:
            data["insights"] = il[-500:]
            self._save_json("insights.json", data)
            logger.info("Compacted insights: %d -> 500", len(il))

        # Trim tried-params (keep highest-scoring 200 per strategy)
        data = self._load_json("tried-params.json")
        for strat, trials in data.items():
            if isinstance(trials, dict) and len(trials) > 200:
                sorted_trials = sorted(
                    trials.items(),
                    key=lambda kv: kv[1].get("score", 0),
                    reverse=True,
                )
                data[strat] = dict(sorted_trials[:200])
        self._save_json("tried-params.json", data)

        # Trim history (keep last 1000 sessions)
        data = self._load_json("history.json")
        sessions = data.get("sessions", [])
        if len(sessions) > 1000:
            data["sessions"] = sessions[-1000:]
            self._save_json("history.json", data)
            logger.info("Compacted history: %d -> 1000", len(sessions))

        self.flush()

    @staticmethod
    def _params_hash(params: dict) -> str:
        """Deterministic hash of a parameter dict for deduplication."""
        canonical = json.dumps(params, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    # ── Best Parameters ──

    def get_best_params(self, strategy: str) -> dict:
        """Get the best known parameters for a strategy.

        Returns empty dict if no data (use defaults).
        """
        data = self._load_json("best-params.json")
        entry = data.get(strategy)
        if entry and isinstance(entry, dict):
            return entry.get("params", {})
        return {}

    def save_best_params(
        self,
        strategy: str,
        params: dict,
        score: float,
        win_rate: float,
        trades: int,
        context: dict | None = None,
    ) -> None:
        """Save new best parameters. Only overwrites if score > current best,
        or same score but higher win_rate, or same score+wr but more trades."""
        data = self._load_json("best-params.json")
        current = data.get(strategy)
        if current and isinstance(current, dict):
            cur_score = current.get("score", float("-inf"))
            if cur_score > score:
                return  # current is strictly better, skip
            if cur_score == score:
                cur_wr = current.get("win_rate", 0)
                if cur_wr > win_rate:
                    return  # same score but current win_rate is better
                if cur_wr == win_rate and current.get("trades", 0) >= trades:
                    return  # same score+wr, prefer more trades

        data[strategy] = {
            "params": params,
            "score": score,
            "win_rate": win_rate,
            "trades": trades,
            "context": context or {},
            "updated_at": datetime.now().isoformat(),
        }
        self._save_json("best-params.json", data)

    # ── Tried Parameters ──

    def has_tried(self, strategy: str, params: dict) -> bool:
        """Check if this exact parameter combo was tried before."""
        data = self._load_json("tried-params.json")
        strategy_trials = data.get(strategy, {})
        h = self._params_hash(params)
        return h in strategy_trials

    def record_trial(self, strategy: str, params: dict, result: dict) -> None:
        """Record a parameter trial and its result."""
        data = self._load_json("tried-params.json")
        if strategy not in data:
            data[strategy] = {}
        h = self._params_hash(params)
        data[strategy][h] = {
            "params": params,
            "score": result.get("score", 0),
            "win_rate": result.get("win_rate", 0),
            "trades": result.get("trades", 0),
            "timestamp": datetime.now().isoformat(),
        }
        self._save_json("tried-params.json", data)

    def get_untried_variations(
        self, strategy: str, base_params: dict
    ) -> list[dict]:
        """Generate parameter variations that haven't been tried yet."""
        # Define possible deltas for common param keys
        _DELTAS: dict[str, list] = {
            "fast": [-2, +2, -4, +4, -1, +1],
            "slow": [-3, +3, -6, +6, -1, +1],
            "signal": [-2, +2, +4, -1, +1],
            "period": [-3, +3, -5, +5, -1, +1, -7, +7],
            "oversold": [-5, +5, -10, +10, -3, +3],
            "overbought": [-5, +5, -10, +10, -3, +3],
            "std_dev": [-0.3, +0.3, -0.5, +0.5, -0.1, +0.1],
            "window": [-3, +3, -5, +5, -1, +1, -7, +7],
            "entry_period": [-5, +5, -3, +3, -1, +1],
            "multiplier": [-0.5, +0.5, -0.3, +0.3, -0.1, +0.1],
            # Additional common param keys
            "k": [-2, +2, -4, +4, -1, +1],
            "d": [-1, +1, -2, +2],
            "lookback": [-3, +3, -5, +5, -10, +10],
            "threshold": [-0.5, +0.5, -0.3, +0.3, -0.1, +0.1],
            "atr": [-3, +3, -5, +5],
            "tenkan": [-2, +2, -3, +3],
            "kijun": [-3, +3, -5, +5],
            "senkou_b": [-5, +5, -10, +10],
            "trend": [-5, +5, -10, +10],
            "rsi": [-2, +2, -4, +4],
            "ema": [-3, +3, -5, +5],
            "mult": [-0.3, +0.3, -0.5, +0.5],
            "tolerance": [-0.001, +0.001, -0.002, +0.002],
            "volume_mult": [-0.3, +0.3, -0.5, +0.5],
            "trend_period": [-3, +3, -5, +5],
            "don_period": [-3, +3, -5, +5],
            "wr_period": [-2, +2, -4, +4],
            "abs": [-20, +20, -40, +40],
            "rel": [-5, +5, -10, +10],
            "sma": [-5, +5, -10, +10],
        }
        _BOUNDS: dict[str, tuple[float, float]] = {
            "fast": (3, 20),
            "slow": (15, 50),
            "signal": (3, 20),
            "period": (5, 50),
            "oversold": (10, 45),
            "overbought": (55, 90),
            "std_dev": (1.0, 4.0),
            "window": (5, 50),
            "entry_period": (5, 40),
            "multiplier": (1.0, 5.0),
            "k": (5, 30),
            "d": (2, 10),
            "lookback": (5, 50),
            "threshold": (0.001, 5.0),
            "atr": (5, 40),
            "tenkan": (5, 20),
            "kijun": (15, 40),
            "senkou_b": (30, 80),
            "trend": (20, 100),
            "rsi": (7, 30),
            "ema": (10, 40),
            "mult": (1.0, 4.0),
            "tolerance": (0.0005, 0.01),
            "volume_mult": (1.0, 4.0),
            "trend_period": (10, 40),
            "don_period": (10, 40),
            "wr_period": (7, 30),
            "abs": (100, 400),
            "rel": (20, 120),
            "sma": (20, 100),
        }

        variations: list[dict] = []
        for key, val in base_params.items():
            if key not in _DELTAS:
                continue
            lo, hi = _BOUNDS.get(key, (0, 1000))
            for delta in _DELTAS[key]:
                new_val = val + delta
                if isinstance(val, float):
                    new_val = round(new_val, 4)
                else:
                    new_val = int(new_val)
                new_val = max(lo, min(hi, new_val))
                if new_val == val:
                    continue
                candidate = dict(base_params)
                candidate[key] = new_val
                if not self.has_tried(strategy, candidate):
                    variations.append(candidate)

        return variations

    # ── Mistakes & Insights ──

    def record_mistake(self, mistake: dict) -> None:
        """Record a pattern that led to loss. Deduplicates by strategy+params hash."""
        data = self._load_json("mistakes.json")
        mistakes_list: list = data.get("mistakes", [])

        # Deduplicate: skip if same strategy+params already recorded
        strategy = mistake.get("strategy", "")
        params = mistake.get("params")
        if strategy and params:
            h = self._params_hash(params)
            for existing in mistakes_list:
                if (existing.get("strategy") == strategy
                        and existing.get("_params_hash") == h):
                    return  # already recorded

        mistake.setdefault("timestamp", datetime.now().isoformat())
        mistake.setdefault("avoid", True)
        # Store pre-computed hash for fast dedup lookups
        if params:
            mistake["_params_hash"] = self._params_hash(params)
        mistakes_list.append(mistake)
        data["mistakes"] = mistakes_list
        self._save_json("mistakes.json", data)

    def record_insight(self, insight: dict) -> None:
        """Record a pattern that led to profit."""
        data = self._load_json("insights.json")
        insights_list: list = data.get("insights", [])
        insight.setdefault("timestamp", datetime.now().isoformat())
        insight.setdefault("reinforce", True)
        insights_list.append(insight)
        data["insights"] = insights_list
        self._save_json("insights.json", data)

    def get_mistakes(self, strategy: str | None = None) -> list[dict]:
        """Get all recorded mistakes, optionally filtered by strategy."""
        data = self._load_json("mistakes.json")
        mistakes: list[dict] = data.get("mistakes", [])
        if strategy:
            mistakes = [m for m in mistakes if m.get("strategy") == strategy]
        return mistakes

    def get_insights(self, strategy: str | None = None) -> list[dict]:
        """Get all recorded insights, optionally filtered by strategy."""
        data = self._load_json("insights.json")
        insights: list[dict] = data.get("insights", [])
        if strategy:
            insights = [i for i in insights if i.get("strategy") == strategy]
        return insights

    def should_avoid(self, strategy: str, params: dict) -> tuple[bool, str]:
        """Check if this param combo is known to be bad.

        Returns (should_avoid, reason).
        """
        h = self._params_hash(params)
        mistakes = self.get_mistakes(strategy)
        for m in mistakes:
            if not m.get("avoid"):
                continue
            # Use pre-computed hash if available, else compute
            m_hash = m.get("_params_hash")
            if not m_hash:
                m_params = m.get("params")
                if m_params:
                    m_hash = self._params_hash(m_params)
            if m_hash == h:
                reason = m.get("reason", "이전에 손실 발생")
                return True, reason
        return False, ""

    # ── Session History ──

    def record_session(self, session: dict) -> None:
        """Record a complete auto-improve session with all rounds."""
        data = self._load_json("history.json")
        sessions: list = data.get("sessions", [])
        session.setdefault("timestamp", datetime.now().isoformat())
        sessions.append(session)
        data["sessions"] = sessions
        self._save_json("history.json", data)

    def get_session_count(self) -> int:
        """How many auto-improve sessions have been run total."""
        data = self._load_json("history.json")
        return len(data.get("sessions", []))

    def get_cumulative_improvement(self, strategy: str) -> dict:
        """Track improvement over all sessions.

        Returns: {first_score, best_score, improvement_pct, sessions_count,
                  total_trials, unique_params_tried}
        """
        data = self._load_json("history.json")
        sessions: list[dict] = data.get("sessions", [])
        strategy_sessions = [
            s for s in sessions if s.get("strategy") == strategy
        ]

        if not strategy_sessions:
            return {
                "first_score": 0,
                "best_score": 0,
                "improvement_pct": 0,
                "sessions_count": 0,
                "total_trials": 0,
                "unique_params_tried": 0,
            }

        first_score = strategy_sessions[0].get("best_score", 0)
        best_score = max(s.get("best_score", 0) for s in strategy_sessions)
        total_trials = sum(s.get("rounds", 0) for s in strategy_sessions)

        # Count unique params from tried-params
        tried_data = self._load_json("tried-params.json")
        unique_params = len(tried_data.get(strategy, {}))

        improvement_pct = 0
        if first_score != 0:
            improvement_pct = round(
                (best_score - first_score) / abs(first_score) * 100, 1
            )
        elif best_score > 0:
            improvement_pct = 100.0

        return {
            "first_score": first_score,
            "best_score": best_score,
            "improvement_pct": improvement_pct,
            "sessions_count": len(strategy_sessions),
            "total_trials": total_trials,
            "unique_params_tried": unique_params,
        }

    # ── Summary ──

    def get_summary(self) -> dict:
        """Overall memory summary for display."""
        history = self._load_json("history.json")
        tried = self._load_json("tried-params.json")
        best = self._load_json("best-params.json")
        mistakes_data = self._load_json("mistakes.json")
        insights_data = self._load_json("insights.json")

        sessions_count = len(history.get("sessions", []))
        total_tried = sum(len(v) for v in tried.values() if isinstance(v, dict))
        strategies_with_best = list(best.keys())
        mistakes_count = len(mistakes_data.get("mistakes", []))
        insights_count = len(insights_data.get("insights", []))

        # Find overall first and best scores
        all_sessions = history.get("sessions", [])
        first_score = all_sessions[0].get("best_score", 0) if all_sessions else 0
        best_score = (
            max(s.get("best_score", 0) for s in all_sessions)
            if all_sessions
            else 0
        )

        return {
            "sessions_count": sessions_count,
            "total_tried": total_tried,
            "strategies_with_best": strategies_with_best,
            "mistakes_count": mistakes_count,
            "insights_count": insights_count,
            "first_score": first_score,
            "best_score": best_score,
        }

    # ── Reset ──

    def forget(self, strategy: str | None = None) -> None:
        """Reset memory for a strategy or all."""
        if strategy is None:
            # Delete all memory files
            for fname in [
                "best-params.json",
                "tried-params.json",
                "mistakes.json",
                "insights.json",
                "history.json",
            ]:
                path = self.MEMORY_DIR / fname
                if path.exists():
                    path.unlink()
            self._cache.clear()
            return

        # Remove strategy-specific data
        for fname in ["best-params.json", "tried-params.json"]:
            data = self._load_json(fname)
            if strategy in data:
                del data[strategy]
                self._save_json(fname, data)

        # Filter mistakes/insights
        for fname, key in [
            ("mistakes.json", "mistakes"),
            ("insights.json", "insights"),
        ]:
            data = self._load_json(fname)
            items = data.get(key, [])
            data[key] = [i for i in items if i.get("strategy") != strategy]
            self._save_json(fname, data)

        # Filter sessions
        data = self._load_json("history.json")
        sessions = data.get("sessions", [])
        data["sessions"] = [
            s for s in sessions if s.get("strategy") != strategy
        ]
        self._save_json("history.json", data)
