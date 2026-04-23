# -*- coding: utf-8 -*-
"""
C3: Climate Engine Algorithm.

physis-charter-v2.md 핵심 루프:
  궤도(LUT) → 일사량 → 기압차 → 바람 → 수분 이류 → 기온 → 날씨 확정

Lv.1~2 경량 구현. CPU only, ≤10ms/틱, 3권역 셀 모델.
simplex noise로 날씨 변동성 부여 (인과성 유지).
"""
from __future__ import annotations
import hashlib
import math
import numpy as np
from .planet import NovaPlanet
from .regions import RegionSheet, REGIONS


def _stable_int(*keys) -> int:
    """Same contract as multi_tick_engine._stable_int. Duplicated
    to keep physis package free of core dependency.
    """
    h = hashlib.blake2b(digest_size=8)
    for k in keys:
        h.update(str(k).encode("utf-8"))
        h.update(b"\x00")
    return int.from_bytes(h.digest(), "big")


class ClimateEngine:
    """Physis 기후 엔진. 매 틱 3권역 날씨를 생성한다."""

    def __init__(self, planet: NovaPlanet | None = None, seed: int = 20260406):
        self.planet = planet or NovaPlanet()
        self._seed: int = seed
        self.regions = REGIONS

        # 누적 버퍼 (C5) — 권역별
        self.cumulative: dict[str, dict] = {}
        for rid in self.regions:
            self.cumulative[rid] = {
                "precip_30d": [],   # 30일 강수 이력
                "temp_30d": [],     # 30일 기온 이력
                "drought_days": 0,  # 연속 무강수 일수
                "heatwave_days": 0, # 연속 고온 일수
                "coldsnap_days": 0, # 연속 한파 일수
            }

        # 이전 틱 상태 (LOD 강등 시 재사용)
        self.prev_weather: dict[str, dict] = {}

    def tick(self, day_of_year: int, hour: int) -> dict[str, dict]:
        """
        1틱 기후 계산. 3권역 날씨를 동시에 반환.

        Returns:
            { "claude": {...weather...}, "codex": {...}, "gemini": {...} }
        """
        result = {}
        for rid, region in self.regions.items():
            weather = self._compute_region_weather(region, day_of_year, hour)
            result[rid] = weather

            # 누적 버퍼 갱신 (매 정오에 일 단위 기록)
            if hour == 12:
                self._update_cumulative(rid, weather)

        self.prev_weather = result
        return result

    def _compute_region_weather(self, region: RegionSheet, day: int, hour: int) -> dict:
        """단일 권역 날씨 계산. Charter 인과 체인 구현."""
        planet = self.planet

        # ── Stage 1: 일사량 ──
        insolation = planet.insolation_factor(region.latitude_deg, day)
        day_length = planet.day_length_hours(region.latitude_deg, day)

        # ── Stage 2: 계절 기온 ──
        season_idx = (day // planet.season_length_d) % 4
        season_offset = region.season_temp_offset[season_idx]

        # 기본 기온 = 해수면 기온 + 계절 보정 - 고도 감률
        base_temp = (
            planet.sea_level_temp_c
            + season_offset
            - region.altitude_m / 1000.0 * planet.lapse_rate_per_km
        )

        # 일교차 (내륙=큰 진폭, 해안=작은 진폭)
        diurnal_amp = 8.0 if not region.coastal else 4.0
        # 시간에 따른 기온 변화 (정오 최고, 새벽 최저)
        hour_factor = math.cos(2 * math.pi * (hour - 14) / 24.0)  # 14시 최고
        temp = base_temp + diurnal_amp * hour_factor

        # ── Stage 3: 기압 (기온 역비례, 고도 보정) ──
        pressure = 1013.25 - region.altitude_m * 0.12 - (temp - 15.0) * 0.5

        # ── Stage 4: 바람 (기온 구배 + 노이즈) ──
        # 풍속: 기온 변화율 + 해안 해풍 + 노이즈
        wind_base = 2.0 + abs(temp - planet.sea_level_temp_c) * 0.08
        if region.coastal:
            wind_base += 1.5  # 해풍
        wind_noise = self._noise(day, hour, region.id, "wind_spd") * 3.0
        wind_speed = max(0.5, wind_base + wind_noise)
        # 코리올리: 북반구 시계 편향, 남반구 반시계
        wind_dir_base = 270.0 if region.latitude_deg > 0 else 90.0
        wind_dir = wind_dir_base + self._noise(day, hour, region.id, "wind") * 60.0

        # ── Stage 5: 습도 + 강수 ──
        # 기본 습도 + 해양 영향 + 계절
        humidity = region.base_humidity
        if region.coastal:
            humidity += 0.1  # 해양 수분 공급
        if region.ocean_current_warm:
            humidity += 0.05 * insolation  # 난류 + 일사 → 증발↑

        # 계절별 강수 패턴
        season_precip_mult = [0.8, 1.0, 0.9, 0.6][season_idx]  # 여름 최다
        if region.id == "gemini":
            season_precip_mult = [1.2, 0.8, 1.0, 1.0][season_idx]  # 열대: 봄 우기

        # 강수 확률 (습도 + 노이즈)
        precip_noise = self._noise(day, hour, region.id, "precip")
        precip_threshold = 0.6 - humidity * 0.3  # 습도 높으면 비 쉬움
        is_raining = precip_noise > precip_threshold
        precip_mm = 0.0
        if is_raining:
            # 강수량 = 기본 × 계절 × 노이즈 강도
            intensity = (precip_noise - precip_threshold) * 3.0
            precip_mm = region.base_precip_mm / 30.0 * intensity * season_precip_mult

        # 습도 보정 (비 오면 습도↑)
        if precip_mm > 0:
            humidity = min(1.0, humidity + 0.15)

        # ── Stage 6: 운량 ──
        cloud_cover = min(1.0, humidity * 0.8 + (0.3 if precip_mm > 0 else 0.0))

        # ── Stage 7: 체감 온도 ──
        # 풍속 체감 (wind chill) + 습도 체감 (heat index)
        if temp < 10:
            feels_like = temp - wind_speed * 0.5
        elif temp > 25:
            feels_like = temp + humidity * 5.0
        else:
            feels_like = temp

        # ── Stage 8: 재난 신호 ──
        disaster_signal = 0.0
        cum = self.cumulative.get(region.id, {})
        if cum.get("drought_days", 0) > 20:
            disaster_signal = min(1.0, cum["drought_days"] / 40.0)
        if cum.get("heatwave_days", 0) > 5:
            disaster_signal = max(disaster_signal, min(1.0, cum["heatwave_days"] / 10.0))
        if cum.get("coldsnap_days", 0) > 7:
            disaster_signal = max(disaster_signal, min(1.0, cum["coldsnap_days"] / 14.0))

        # ── Stage 9: 서사 태그 ──
        narrative_tag = self._narrative_tag(temp, precip_mm, wind_speed, humidity, feels_like)

        return {
            "temperature_c": round(temp, 1),
            "feels_like_c": round(feels_like, 1),
            "precipitation_mm": round(precip_mm, 1),
            "humidity_pct": round(humidity * 100, 1),
            "wind_speed_ms": round(wind_speed, 1),
            "wind_dir_deg": round(wind_dir % 360, 1),
            "cloud_cover_pct": round(cloud_cover, 2),
            "pressure_hpa": round(pressure, 1),
            "insolation": round(insolation, 4),
            "day_length_h": round(day_length, 1),
            "disaster_signal": round(disaster_signal, 3),
            "season": self.planet.season_name(day),
            "narrative_tag": narrative_tag,
        }

    def _noise(self, day: int, hour: int, region_id: str, channel: str) -> float:
        """결정론적 노이즈. 시드+일+시+권역+채널로 재현 가능."""
        # 날짜 기반 해시 시드 (Charter: simplex noise 대체)
        seed_val = _stable_int(self._seed, day, hour, region_id, channel) & 0xFFFFFFFF
        rng = np.random.default_rng(seed_val)
        return float(rng.random())

    def _update_cumulative(self, rid: str, weather: dict):
        """누적 버퍼 갱신 (C5). 매일 정오에 호출."""
        cum = self.cumulative[rid]
        temp = weather["temperature_c"]
        precip = weather["precipitation_mm"]

        cum["temp_30d"].append(temp)
        cum["precip_30d"].append(precip)
        if len(cum["temp_30d"]) > 30:
            cum["temp_30d"].pop(0)
        if len(cum["precip_30d"]) > 30:
            cum["precip_30d"].pop(0)

        # 가뭄: 연속 무강수
        if precip < 0.1:
            cum["drought_days"] += 1
        else:
            cum["drought_days"] = 0

        # 폭염: 연속 고온 (>35°C)
        if temp > 35:
            cum["heatwave_days"] += 1
        else:
            cum["heatwave_days"] = 0

        # 한파: 연속 한파 (<-10°C)
        if temp < -10:
            cum["coldsnap_days"] += 1
        else:
            cum["coldsnap_days"] = 0

    def _narrative_tag(self, temp: float, precip: float, wind: float,
                       humidity: float, feels: float) -> str:
        """서사 태그 생성 (C4). 페르소나가 느끼는 날씨."""
        tags = []
        if feels < -5:
            tags.append("bone-chilling cold")
        elif feels < 5:
            tags.append("biting cold")
        elif feels > 35:
            tags.append("suffocating heat")
        elif feels > 28:
            tags.append("sweltering")

        if precip > 10:
            tags.append("downpour")
        elif precip > 3:
            tags.append("steady rain")
        elif precip > 0:
            tags.append("drizzle")

        if wind > 15:
            tags.append("howling wind")
        elif wind > 8:
            tags.append("gusty")

        if humidity > 0.85 and temp > 25:
            tags.append("muggy")

        if not tags:
            if 15 < temp < 25 and precip == 0:
                tags.append("pleasant")
            elif temp > 20 and precip == 0:
                tags.append("clear and warm")
            else:
                tags.append("mild")

        return ", ".join(tags)

    def to_climate_vec(self, weather: dict) -> np.ndarray:
        """날씨 → PersonaBrain 입력 벡터 float16[8]."""
        return np.array([
            (weather["temperature_c"] + 30) / 80,
            min(weather["precipitation_mm"] / 50, 1.0),
            min(weather["wind_speed_ms"] / 30, 1.0),
            weather["humidity_pct"] / 100,
            weather["cloud_cover_pct"],
            (weather["pressure_hpa"] - 950) / 100,
            0.0,  # sea_surface_temp (확장용)
            weather["disaster_signal"],
        ], dtype=np.float16)
