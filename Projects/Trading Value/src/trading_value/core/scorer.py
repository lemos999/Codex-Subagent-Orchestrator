"""Entry quality scorer for Track A.

Instead of binary enter/don't enter, scores each setup 0-100.
Only enters when score >= threshold (default 65).

Each factor contributes points:
- Regime alignment:     0-20
- Cloud prediction:     0-20
- Donchian position:    0-15
- Momentum:             0-15
- Volume:               0-10
- Zone quality:         0-10
- Recent performance:   -10 to +10
"""
from __future__ import annotations

from dataclasses import dataclass

from .models import Timeframe, TimeframeSnapshot


@dataclass(frozen=True)
class EntryScore:
    """Detailed entry quality score."""
    total: int  # 0-100
    regime_score: int
    cloud_score: int
    donchian_score: int
    momentum_score: int
    volume_score: int
    zone_score: int
    performance_adj: int
    details: str  # human-readable breakdown


def score_entry(
    strategy: str,
    side: int,  # 1=long, -1=short
    current_price: float,
    snapshots: dict[Timeframe, TimeframeSnapshot],
    cloud_analysis=None,
    dc_upper: float = 0,
    dc_lower: float = 0,
    dc_middle: float = 0,
    zone_touched: bool = False,
    recent_wins: int = 0,
    recent_losses: int = 0,
) -> EntryScore:
    """Score an entry setup from 0-100.

    Higher score = higher confidence = better entry.
    """
    snap_30m = snapshots.get(Timeframe.M30)
    snap_1h = snapshots.get(Timeframe.H1)
    snap_4h = snapshots.get(Timeframe.H4)
    if not snap_30m:
        return EntryScore(0, 0, 0, 0, 0, 0, 0, 0, "no 30m data")

    details = []
    atr = snap_30m.atr or 1

    # === 1. Regime alignment (0-20) ===
    regime_score = 0
    if side == 1:  # LONG
        if snap_4h and str(snap_4h.cloud_position) == "above":
            regime_score += 10
            details.append("4h above cloud +10")
        if snap_1h and str(snap_1h.cloud_position) == "above":
            regime_score += 5
            details.append("1h above +5")
        if str(snap_30m.cloud_position) == "above":
            regime_score += 5
            details.append("30m above +5")
    else:  # SHORT
        if snap_4h and str(snap_4h.cloud_position) == "below":
            regime_score += 10
            details.append("4h below cloud +10")
        if snap_1h and str(snap_1h.cloud_position) == "below":
            regime_score += 5
            details.append("1h below +5")
        if str(snap_30m.cloud_position) == "below":
            regime_score += 5
            details.append("30m below +5")

    # === 2. Cloud prediction (0-20) ===
    cloud_score = 0
    if cloud_analysis:
        # Cloud direction agrees with trade
        if side == 1 and cloud_analysis.cloud_rising:
            cloud_score += 8
            details.append("cloud rising +8")
        elif side == -1 and cloud_analysis.cloud_falling:
            cloud_score += 8
            details.append("cloud falling +8")

        # Cloud twist in our direction
        if cloud_analysis.twist_detected:
            if (side == 1 and cloud_analysis.twist_direction == "bullish") or \
               (side == -1 and cloud_analysis.twist_direction == "bearish"):
                cloud_score += 7
                details.append(f"cloud twist {cloud_analysis.twist_direction} +7")
            else:
                cloud_score -= 5
                details.append(f"cloud twist AGAINST -{5}")

        # Thin cloud = easy breakout
        if cloud_analysis.future_cloud_thickness_pct < 0.3:
            cloud_score += 5
            details.append("thin cloud +5")
        elif cloud_analysis.future_cloud_thickness_pct > 1.5:
            # Thick cloud blocks movement
            if side == 1 and current_price < cloud_analysis.future_resistance:
                cloud_score -= 3
                details.append("thick cloud resistance -3")
            elif side == -1 and current_price > cloud_analysis.future_support:
                cloud_score -= 3
                details.append("thick cloud support -3")

    # === 3. Donchian position (0-15) ===
    donchian_score = 0
    if dc_upper > 0 and dc_lower > 0:
        dc_range = dc_upper - dc_lower
        if dc_range > 0:
            position_pct = (current_price - dc_lower) / dc_range  # 0=lower, 1=upper

            if side == 1:
                # Long: breakout above upper is strong
                if current_price >= dc_upper:
                    donchian_score += 12
                    details.append("DC breakout +12")
                # Pullback to middle in uptrend
                elif position_pct > 0.4 and position_pct < 0.6:
                    donchian_score += 8
                    details.append("DC middle pullback +8")
                # Near lower = against trend for long
                elif position_pct < 0.2:
                    donchian_score += 3
                    details.append("DC near lower +3")
            else:
                # Short: breakdown below lower is strong
                if current_price <= dc_lower:
                    donchian_score += 12
                    details.append("DC breakdown +12")
                elif position_pct > 0.4 and position_pct < 0.6:
                    donchian_score += 8
                    details.append("DC middle pullback +8")
                elif position_pct > 0.8:
                    donchian_score += 3
                    details.append("DC near upper +3")

            # Squeeze (narrow range) = breakout imminent
            squeeze_pct = dc_range / current_price * 100
            if squeeze_pct < 3.0:
                donchian_score += 3
                details.append(f"DC squeeze {squeeze_pct:.1f}% +3")

    # === 4. Momentum (0-15) ===
    momentum_score = 0
    # TK cross alignment
    if side == 1:
        tk_aligned = 0
        if snap_30m and str(snap_30m.tk_state) == "bullish":
            tk_aligned += 1
        if snap_1h and str(snap_1h.tk_state) == "bullish":
            tk_aligned += 1
        if snap_4h and str(snap_4h.tk_state) == "bullish":
            tk_aligned += 1
        momentum_score = tk_aligned * 5
        if tk_aligned > 0:
            details.append(f"TK bullish x{tk_aligned} +{tk_aligned * 5}")
    else:
        tk_aligned = 0
        if snap_30m and str(snap_30m.tk_state) == "bearish":
            tk_aligned += 1
        if snap_1h and str(snap_1h.tk_state) == "bearish":
            tk_aligned += 1
        if snap_4h and str(snap_4h.tk_state) == "bearish":
            tk_aligned += 1
        momentum_score = tk_aligned * 5
        if tk_aligned > 0:
            details.append(f"TK bearish x{tk_aligned} +{tk_aligned * 5}")

    # === 5. Volume (0-10) ===
    volume_score = 0
    if snap_30m.volume_sma_20 > 0:
        vol_ratio = snap_30m.volume / snap_30m.volume_sma_20
        if vol_ratio >= 2.0:
            volume_score = 10
            details.append(f"volume surge {vol_ratio:.1f}x +10")
        elif vol_ratio >= 1.5:
            volume_score = 7
            details.append(f"high volume {vol_ratio:.1f}x +7")
        elif vol_ratio >= 1.0:
            volume_score = 4
            details.append(f"normal volume +4")
        else:
            volume_score = 0
            details.append(f"low volume {vol_ratio:.1f}x +0")

    # === 6. Zone quality (0-10) ===
    zone_score = 0
    if zone_touched:
        zone_score = 10
        details.append("zone touched +10")
    elif dc_upper > 0:
        # Near a donchian level
        dist_upper = abs(current_price - dc_upper) / atr
        dist_lower = abs(current_price - dc_lower) / atr
        if (side == 1 and dist_lower < 1.0) or (side == -1 and dist_upper < 1.0):
            zone_score = 6
            details.append("near DC level +6")

    # === 7. Recent performance adjustment (-10 to +10) ===
    perf_adj = 0
    if recent_losses >= 3:
        perf_adj = -10
        details.append(f"losing streak {recent_losses} -10")
    elif recent_losses >= 2:
        perf_adj = -5
        details.append(f"recent losses -5")
    elif recent_wins >= 3:
        perf_adj = 5
        details.append(f"winning streak +5")

    total = max(0, min(100,
        regime_score + cloud_score + donchian_score +
        momentum_score + volume_score + zone_score + perf_adj
    ))

    return EntryScore(
        total=total,
        regime_score=regime_score,
        cloud_score=cloud_score,
        donchian_score=donchian_score,
        momentum_score=momentum_score,
        volume_score=volume_score,
        zone_score=zone_score,
        performance_adj=perf_adj,
        details=" | ".join(details),
    )
