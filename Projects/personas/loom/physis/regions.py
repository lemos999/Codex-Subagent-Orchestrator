# -*- coding: utf-8 -*-
"""
C2: 3-Region Terrain Sheet.

physis-charter-v2.md Phase 2 확정값.
각 권역의 지형·기후 특성을 정적 데이터로 정의.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionSheet:
    """권역 지형 시트."""
    id: str               # "claude", "codex", "gemini"
    name: str
    latitude_deg: float    # 대표 위도
    altitude_m: float      # 대표 고도
    coastal: bool          # 해안 여부
    albedo: float          # 반사율
    land_cover: str        # 토지 피복
    ocean_current_warm: bool  # 난류 영향
    base_humidity: float   # 기본 습도 (0~1)
    base_precip_mm: float  # 기본 월 강수량

    # 계절별 기온 보정 (봄/여름/가을/겨울)
    season_temp_offset: tuple[float, float, float, float] = (0, 0, 0, 0)


# Charter v2.4 확정값
REGIONS: dict[str, RegionSheet] = {
    "claude": RegionSheet(
        id="claude",
        name="Claude Dominion",
        latitude_deg=45.0,
        altitude_m=1500.0,
        coastal=False,
        albedo=0.25,
        land_cover="steppe/conifer",
        ocean_current_warm=False,
        base_humidity=0.35,
        base_precip_mm=40.0,
        # 대륙성: 여름 25°C, 겨울 -15°C → 큰 진폭
        season_temp_offset=(5.0, 15.0, 3.0, -20.0),
    ),
    "codex": RegionSheet(
        id="codex",
        name="Codex Republic",
        latitude_deg=30.0,
        altitude_m=50.0,
        coastal=True,
        albedo=0.15,
        land_cover="farmland/broadleaf",
        ocean_current_warm=True,
        base_humidity=0.65,
        base_precip_mm=90.0,
        # 온대 해양: 여름 28°C, 겨울 5°C → 중간 진폭
        season_temp_offset=(5.0, 12.0, 4.0, -8.0),
    ),
    "gemini": RegionSheet(
        id="gemini",
        name="Gemini Federation",
        latitude_deg=-5.0,
        altitude_m=10.0,
        coastal=True,
        albedo=0.12,
        land_cover="tropical/mangrove",
        ocean_current_warm=True,
        base_humidity=0.80,
        base_precip_mm=180.0,
        # 열대: 연중 30°C 전후 → 작은 진폭 (기본 +14로 해수면 16+14=30°C 기준)
        season_temp_offset=(14.0, 16.0, 14.0, 13.0),
    ),
}
