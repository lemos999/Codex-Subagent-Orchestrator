# -*- coding: utf-8 -*-
"""
C1: Nova Planet Parameters.

physis-charter-v2.md Phase 2 확정값.
모든 상수는 전역 변수화 (config 주입 대비).
"""
from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class NovaPlanet:
    """노바 행성 물리 상수."""

    # 궤도
    rotation_period_h: float = 24.0      # 자전 주기 (시간)
    orbital_period_d: int = 360          # 공전 주기 (일) = 4계절 × 90일
    axial_tilt_deg: float = 25.0         # 자축 기울기 (°) — 지구보다 약간 강화
    eccentricity: float = 0.02           # 궤도 이심률

    # 대기
    sea_level_temp_c: float = 16.0       # 해수면 평균 기온 (°C)
    lapse_rate_per_km: float = 6.5       # 고도 감률 (°C/km)

    # 물리
    gravity_ms2: float = 9.81

    # 계절 (90일 단위, day 0 = 봄 시작)
    season_length_d: int = 90

    # 일사량 관련
    solar_constant: float = 1361.0       # W/m² (지구와 동일)

    @property
    def axial_tilt_rad(self) -> float:
        return math.radians(self.axial_tilt_deg)

    def solar_declination(self, day_of_year: int) -> float:
        """태양 적위 (라디안). day 0 = 춘분."""
        # 하지(day 90) 최대, 동지(day 270) 최소
        return self.axial_tilt_rad * math.sin(2 * math.pi * (day_of_year - 0) / self.orbital_period_d)

    def day_length_hours(self, latitude_deg: float, day_of_year: int) -> float:
        """주어진 위도에서의 낮 길이 (시간)."""
        lat = math.radians(latitude_deg)
        decl = self.solar_declination(day_of_year)
        # 시간각
        cos_ha = -math.tan(lat) * math.tan(decl)
        cos_ha = max(-1.0, min(1.0, cos_ha))  # 극지 처리
        ha = math.acos(cos_ha)
        return (2.0 * ha / math.pi) * 12.0

    def insolation_factor(self, latitude_deg: float, day_of_year: int) -> float:
        """상대 일사량 (0~1). 위도+계절 의존."""
        lat = math.radians(latitude_deg)
        decl = self.solar_declination(day_of_year)
        # 정오 태양 고도각
        sin_elev = math.sin(lat) * math.sin(decl) + math.cos(lat) * math.cos(decl)
        # 낮 길이 비율
        day_frac = self.day_length_hours(latitude_deg, day_of_year) / 24.0
        return max(0.0, sin_elev * day_frac)

    def season_name(self, day_of_year: int) -> str:
        """현재 계절."""
        idx = (day_of_year // self.season_length_d) % 4
        return ["spring", "summer", "autumn", "winter"][idx]
