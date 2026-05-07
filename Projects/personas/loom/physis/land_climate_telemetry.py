"""Phase 17 Phi-1 Land rev.next §7-1 Land-Climate Closure Probe — read-only telemetry.

Spec authority: ``PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md`` rev.0
[확정] 2026-05-07.

This module is a *read-only observer* of :class:`physis.world.LandCell`. It
derives the eight candidate fields described in paper §5.2 from LandCell state
and stores them in two separate buckets: a rolling current-window bucket
(``measurements_current``) and a full cumulative bucket
(``measurements_cumulative``).

Strict invariants (spec §0.1, §0.2, §1.3, §5.2):
  - LandCell本문 변경 0건. ``observe`` 는 ``World.iter_cells`` 만 호출.
  - climate dict 키 추가 0건 (현재: ``rainfall``, ``temperature``).
  - mechanism 결합 수식 freeze 금지 — 본 모듈은 raw 누적·평균·연속 카운트만
    수행하며 fertility/depletion/recovery/hazard 의 정확한 결합 함수는
    §7-2 이후 별도 spec 의 결정 영역.
  - 분위수 임계값 magic number 0건 — 분위수 산출은 본 모듈 외부의 extractor
    스크립트 역할 (§4.2).
  - 추가 window 길이는 freeze 금지: 30일은 spec §2.2 기본값 (OQ 1) 이며 본
    모듈에서는 ``window_size`` 매개변수로 변수화.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:  # pragma: no cover — import only for type checking
    from .world import LandCell, World


# ---------------------------------------------------------------------------
# Spec §2.2 — LandClimateMeasurement
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LandClimateMeasurement:
    """Single tile × single tick raw measurement (read-only observer of LandCell).

    Eight candidate fields per paper §5.2. All fields are *raw* signals derived
    from LandCell state at observation time. The actual mechanism coupling
    (e.g. fertility = f(biome, soil_moisture, resources)) is reserved for a
    later spec — this measurement object only carries observed quantities.
    """

    tick: int
    x: int
    y: int
    soil_moisture: float
    fertility: float
    rainfall_30d: float
    temperature_30d: float
    drought_days: int
    depletion: float
    recovery_rate: float
    hazard_damage: float


# ---------------------------------------------------------------------------
# Spec §2.2 — LandClimateTelemetry
# ---------------------------------------------------------------------------


# Default rolling current-window length, in observation ticks (paper §8 / OQ 1).
# Marked as a module-level constant so external callers / tests can introspect
# the spec default without hard-coding it. Other window lengths are freeze 금지
# at the spec body level — they may be passed at instance construction time.
DEFAULT_WINDOW_SIZE: int = 30


@dataclass(slots=True)
class LandClimateTelemetry:
    """Read-only observer of LandCell state.

    The telemetry stores observations in two buckets, keyed by ``(x, y)``:

    - ``measurements_current``: rolling current-window bucket. Old entries are
      dropped by :meth:`trim_window` once their tick falls outside the
      ``window_size`` horizon. Used for current-window distribution analysis.
    - ``measurements_cumulative``: full cumulative bucket. Never trimmed. Used
      for cumulative distribution analysis (paper §8 current-vs-cumulative
      separation requirement).

    The observer also maintains internal per-tile rainfall/temperature history
    in order to derive 30-day windowed signals (rainfall_30d / temperature_30d
    / drought_days) without mutating LandCell state.
    """

    seed: int
    window_size: int = DEFAULT_WINDOW_SIZE
    measurements_current: dict[tuple[int, int], list[LandClimateMeasurement]] = field(
        default_factory=dict
    )
    measurements_cumulative: dict[tuple[int, int], list[LandClimateMeasurement]] = field(
        default_factory=dict
    )
    # Internal rolling history of climate dict reads, per tile. Captures
    # (tick, rainfall, temperature) per observed cell. Used to derive the
    # 30-day windowed signals and the drought-days streak without touching
    # LandCell. Trimmed alongside ``measurements_current``.
    _climate_history: dict[tuple[int, int], list[tuple[int, float, float]]] = field(
        default_factory=dict
    )
    # Per-tile starting resource baseline captured on first observation.
    # Subsequent observations compare against this snapshot to derive a raw
    # depletion ratio. The baseline is *captured*, not mutated, on the
    # LandCell. The exact depletion / recovery_rate coupling formulas are
    # spec freeze 금지 — this module only records a raw ratio of the read.
    _resource_baseline: dict[tuple[int, int], dict[str, float]] = field(
        default_factory=dict
    )
    # Last seen depletion per tile, used to derive a raw recovery rate as
    # max(0, prev_depletion - curr_depletion). Stored alongside the tick at
    # which it was recorded so we can normalize per tick gap.
    _last_depletion: dict[tuple[int, int], tuple[int, float]] = field(
        default_factory=dict
    )
    # Per-tile cumulative hazard damage. The hazard mechanism itself is
    # outside this spec; the observer simply accumulates the inverse of
    # path_cost normalization as a raw damage proxy until §7-3 mechanism
    # is decided. Stored as a running value keyed by tile.
    _hazard_accum: dict[tuple[int, int], float] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def observe(self, tick: int, world: "World") -> None:
        """Read current LandCell state and append measurements to both buckets.

        IMPORTANT (spec §1.3 [금지] / §5.2): this method must never mutate any
        LandCell field. It only iterates :meth:`World.iter_cells` and reads
        public attributes (``x``, ``y``, ``biome``, ``resources``, ``climate``,
        ``path_cost``, ``elevation``). All derived state is stored on the
        telemetry object itself, never on LandCell.
        """
        for cell in world.iter_cells():
            key = (int(cell.x), int(cell.y))
            climate = self._read_climate(cell)
            rainfall = climate[0]
            temperature = climate[1]

            # Update rolling per-tile climate history (capped by window_size).
            history = self._climate_history.setdefault(key, [])
            history.append((tick, rainfall, temperature))
            self._trim_history(history, tick)

            # Derived 30-day signals (raw measurements only, no thresholds
            # frozen — drought is counted against the smallest non-zero
            # rainfall observed in the rolling history, with a fall-back to
            # zero strict comparison when no positive rainfall has been seen).
            rainfall_window = sum(entry[1] for entry in history)
            temperature_window = (
                sum(entry[2] for entry in history) / len(history)
                if history
                else float(temperature)
            )
            drought_days = self._derive_drought_days(history)

            # Resource baseline + raw depletion ratio. The baseline is the
            # first read per tile; subsequent reads compute a raw fraction
            # of remaining-vs-baseline. The coupling function is freeze 금지
            # (§7-2), so this is intentionally a simple ratio.
            depletion = self._derive_depletion(key, cell)

            # Raw recovery_rate proxy: positive when current depletion
            # decreased compared to the previous observation. The coupling
            # function is freeze 금지 (§7-2).
            recovery_rate = self._derive_recovery_rate(key, tick, depletion)

            # Raw soil_moisture proxy: window-normalized rainfall fraction.
            # The exact coupling to fertility (§7-2) is reserved.
            soil_moisture = self._derive_soil_moisture(rainfall_window, history)

            # Raw fertility proxy: a clamped product of biome baseline,
            # soil moisture and remaining resource share. The exact formula
            # is freeze 금지 (§7-2); this is a placeholder probe value.
            fertility = self._derive_fertility(cell, soil_moisture, depletion)

            # Raw hazard_damage proxy: running accumulator. The hazard
            # mechanism is outside this spec (§7-3+).
            hazard_damage = self._derive_hazard_damage(key, cell, drought_days)

            measurement = LandClimateMeasurement(
                tick=int(tick),
                x=int(cell.x),
                y=int(cell.y),
                soil_moisture=float(soil_moisture),
                fertility=float(fertility),
                rainfall_30d=float(rainfall_window),
                temperature_30d=float(temperature_window),
                drought_days=int(drought_days),
                depletion=float(depletion),
                recovery_rate=float(recovery_rate),
                hazard_damage=float(hazard_damage),
            )

            self.measurements_current.setdefault(key, []).append(measurement)
            self.measurements_cumulative.setdefault(key, []).append(measurement)

        # After ingesting this tick across all tiles, drop stale current-
        # window measurements. Cumulative bucket is intentionally not
        # trimmed (spec §2.2 / paper §8 separation).
        self.trim_window(tick)

    def trim_window(self, tick: int) -> None:
        """Drop entries from ``measurements_current`` older than the window.

        An entry at ``entry.tick`` is retained if and only if
        ``tick - entry.tick < self.window_size``. The cumulative bucket is
        unaffected (spec §2.2).
        """
        horizon = int(tick) - int(self.window_size) + 1
        for key, entries in self.measurements_current.items():
            if not entries:
                continue
            self.measurements_current[key] = [
                entry for entry in entries if entry.tick >= horizon
            ]
        # Mirror trimming on the per-tile climate history so derived signals
        # for the next observe() call are consistent with the current bucket.
        for key, history in self._climate_history.items():
            if not history:
                continue
            self._climate_history[key] = [
                entry for entry in history if entry[0] >= horizon
            ]

    # ------------------------------------------------------------------
    # Inspection helpers (read-only convenience accessors)
    # ------------------------------------------------------------------

    def iter_current(self) -> Iterable[LandClimateMeasurement]:
        """Yield every measurement currently in the rolling-window bucket."""
        for entries in self.measurements_current.values():
            yield from entries

    def iter_cumulative(self) -> Iterable[LandClimateMeasurement]:
        """Yield every measurement in the cumulative bucket."""
        for entries in self.measurements_cumulative.values():
            yield from entries

    # ------------------------------------------------------------------
    # Internal derivations — kept simple to honor freeze 금지 caveats
    # ------------------------------------------------------------------

    def _read_climate(self, cell: "LandCell") -> tuple[float, float]:
        """Return the (rainfall, temperature) pair from the LandCell read.

        Climate dict keys are restricted to ``rainfall`` and ``temperature``
        (spec §1.3 [금지]: climate dict 키 추가 금지).
        """
        climate = cell.climate
        rainfall = float(climate.get("rainfall", 0.0))
        temperature = float(climate.get("temperature", 20.0))
        return rainfall, temperature

    def _trim_history(
        self,
        history: list[tuple[int, float, float]],
        tick: int,
    ) -> None:
        """Trim per-tile rolling climate history in-place to the window."""
        horizon = int(tick) - int(self.window_size) + 1
        if history and history[0][0] < horizon:
            history[:] = [entry for entry in history if entry[0] >= horizon]

    def _derive_drought_days(
        self, history: list[tuple[int, float, float]]
    ) -> int:
        """Count the longest tail run of zero rainfall in the window.

        We deliberately use a strict-zero threshold here rather than a frozen
        analytic percentile cut. Spec §3 row 5 marks the actual quantile cut
        as freeze 금지; the extractor will derive candidate cuts from the
        raw history. Treating "no rainfall" as the only threshold keeps this
        observer transparent.
        """
        run = 0
        for _, rainfall, _ in reversed(history):
            if rainfall <= 0.0:
                run += 1
            else:
                break
        return int(run)

    def _derive_soil_moisture(
        self,
        rainfall_window: float,
        history: list[tuple[int, float, float]],
    ) -> float:
        """Normalize rolling rainfall by the largest observed entry.

        This is a *raw* normalization — the actual coupling to climate
        physics is freeze 금지 (§7-2). When no positive rainfall has been
        seen, returns 0.0; otherwise returns ``rainfall_window`` rescaled
        by ``window_size × max_rainfall_observed``. Clamped to ``[0, 1]``.
        """
        if not history:
            return 0.0
        max_rainfall = max(entry[1] for entry in history)
        if max_rainfall <= 0.0:
            return 0.0
        denom = float(self.window_size) * max_rainfall
        if denom <= 0.0:
            return 0.0
        value = float(rainfall_window) / denom
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    def _derive_depletion(
        self, key: tuple[int, int], cell: "LandCell"
    ) -> float:
        """Track raw depletion ratio against the per-tile baseline read.

        On first observation we capture a baseline of the cell's resources;
        subsequent reads compute ``1 - sum(curr) / sum(baseline)`` clamped
        to ``[0, 1]``. The exact coupling formula is freeze 금지 (§7-2).
        """
        baseline = self._resource_baseline.get(key)
        current_resources = {
            str(name): float(value)
            for name, value in cell.resources.items()
        }
        if baseline is None:
            self._resource_baseline[key] = dict(current_resources)
            return 0.0
        baseline_total = sum(baseline.values())
        if baseline_total <= 0.0:
            return 0.0
        current_total = sum(current_resources.values())
        ratio = 1.0 - (current_total / baseline_total)
        if ratio < 0.0:
            return 0.0
        if ratio > 1.0:
            return 1.0
        return float(ratio)

    def _derive_recovery_rate(
        self,
        key: tuple[int, int],
        tick: int,
        depletion: float,
    ) -> float:
        """Raw recovery_rate proxy: depletion drop since previous read.

        Returns the per-tick decrease in depletion, clamped to ``[0, 1]``.
        The actual recovery formula is freeze 금지 (§7-2). On first read
        the recovery rate is 0.
        """
        prev = self._last_depletion.get(key)
        self._last_depletion[key] = (int(tick), float(depletion))
        if prev is None:
            return 0.0
        prev_tick, prev_depletion = prev
        gap = int(tick) - int(prev_tick)
        if gap <= 0:
            return 0.0
        delta = prev_depletion - depletion
        if delta <= 0.0:
            return 0.0
        rate = float(delta) / float(gap)
        if rate > 1.0:
            return 1.0
        return rate

    def _derive_fertility(
        self,
        cell: "LandCell",
        soil_moisture: float,
        depletion: float,
    ) -> float:
        """Raw fertility probe: equal-weighted product of biome / moisture / remaining.

        Provides a placeholder probe so downstream extractor analysis can
        observe the field. The exact biome × soil × resource coupling is
        freeze 금지 (§7-2). We deliberately use an equal-weighted product
        of three normalized factors — biome dryness flag, soil moisture and
        remaining resource share — so that no coefficient is frozen at the
        spec body. The coefficients themselves will be derived from the
        extractor's distribution analysis in a later spec.
        """
        remaining = 1.0 - float(depletion)
        if remaining < 0.0:
            remaining = 0.0
        elif remaining > 1.0:
            remaining = 1.0
        moisture = float(soil_moisture)
        if moisture < 0.0:
            moisture = 0.0
        elif moisture > 1.0:
            moisture = 1.0
        # Biome flag: 0 if water (uninhabitable for fertility purposes),
        # otherwise 1. Spec §3 row 2 marks the biome coupling itself as
        # freeze 금지; we therefore avoid biome-specific scalar weights at
        # this layer and only encode the binary "land vs water" distinction.
        biome_flag = 0.0 if str(cell.biome) == "water" else 1.0
        value = moisture * remaining * biome_flag
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    def _derive_hazard_damage(
        self,
        key: tuple[int, int],
        cell: "LandCell",
        drought_days: int,
    ) -> float:
        """Raw hazard_damage proxy: running accumulation per tile.

        Increases monotonically when drought_days are observed; stays
        bounded by ``[0, 1]``. The hazard mechanism itself is outside the
        scope of this spec (§7-3+).
        """
        current = self._hazard_accum.get(key, 0.0)
        if drought_days > 0:
            current = current + float(drought_days) / float(
                max(self.window_size, 1)
            )
        if current < 0.0:
            current = 0.0
        elif current > 1.0:
            current = 1.0
        self._hazard_accum[key] = current
        return current

__all__ = [
    "DEFAULT_WINDOW_SIZE",
    "LandClimateMeasurement",
    "LandClimateTelemetry",
]
