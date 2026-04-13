"""
Layer 0~4: 페르소나 국가 온톨로지 데이터 구조 (Phase 0)

world-ontology.md의 코드 실현.
Phase 0에서 필요한 Layer만 구현. 나머지는 Phase별 점진 추가.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


# ─── Layer 0: Origin ───────────────────────────────────────────

@dataclass
class Creator:
    """창조자 = 살아있는 헌법. 규칙 자체."""
    name: str = "Creator"


# ─── Layer 1b: Substrate (동적 기반) ──────────────────────────

@dataclass
class Weather:
    """Physis C4 출력 — Phase 0에서는 정적 값."""
    temperature_c: float = 15.0
    precipitation_mm: float = 0.0
    wind_speed_ms: float = 3.0
    humidity_pct: float = 50.0
    cloud_cover_pct: float = 0.3
    pressure_hpa: float = 1013.0
    sea_surface_temp: float = 0.0  # 내륙 = 0
    disaster_signal: float = 0.0   # 0~1

    def to_climate_vec(self) -> np.ndarray:
        """정규화된 float16 climate_vec[8] — PersonaBrain 입력."""
        return np.array([
            (self.temperature_c + 30) / 80,       # [0] temp
            min(self.precipitation_mm / 50, 1.0),  # [1] precip
            min(self.wind_speed_ms / 30, 1.0),     # [2] wind
            self.humidity_pct / 100,                # [3] humidity
            self.cloud_cover_pct,                   # [4] cloud
            (self.pressure_hpa - 950) / 100,        # [5] pressure
            (self.sea_surface_temp + 5) / 45,       # [6] sst
            self.disaster_signal,                   # [7] disaster
        ], dtype=np.float16)


@dataclass
class GameTime:
    """Lachesis 관리 — 게임 시간."""
    tick: int = 0
    game_hour: int = 0   # 0~23
    game_day: int = 1
    season: int = 0       # 0=봄, 1=여름, 2=가을, 3=겨울

    def advance(self):
        self.tick += 1
        self.game_hour = self.tick % 24
        self.game_day = self.tick // 24 + 1
        self.season = (self.tick // 90) % 4  # 90일/계절 (360일/년)


# ─── Layer 2: Entity ──────────────────────────────────────────

@dataclass
class Persona:
    """페르소나 엔티티 — 존재의 기본 정보."""
    id: str
    name: str
    full_name: str
    region: str = "claude"     # claude / codex / gemini
    territory: str = "seorim"  # 서림
    persona_class: int = 1     # 1~9, 10=EX
    title: str = "초심자"

    # PersonaBrain 관련 (Phase 0 최소)
    neuron_count: int = 1_000  # Phase 0: 1K 뉴런
    brain_weights_path: Optional[str] = None

    # Mitotype (Phase 0: 기본값)
    mitotype_id: int = 0  # Beta(균형)


# ─── Layer 3: Inner World ─────────────────────────────────────

@dataclass
class InnerWorld:
    """페르소나의 내면 상태."""
    persona_id: str

    # 12클러스터 neuromodulator_tone (Phase 0: 기본값 1.0)
    # V  L  S  B  A  T  C  G  F  I  D  P
    tone: np.ndarray = field(default_factory=lambda: np.ones(12, dtype=np.float16))

    # 에너지 (미토콘드리아)
    energy_pool: float = 1.0       # 0.0 ~ 1.0
    max_capacity: float = 1.0

    # 감정 (Phase 0: 중립)
    # 칠정: 희(기쁨) 노(분노) 애(슬픔) 구(두려움) 애(사랑) 오(싫음) 욕(갈망)
    chiljeong: np.ndarray = field(default_factory=lambda: np.zeros(7, dtype=np.float16))

    # 오욕: 식욕 수면욕 색욕 재욕 명예욕
    oyok: np.ndarray = field(default_factory=lambda: np.array([0.3, 0.0, 0.0, 0.1, 0.1], dtype=np.float16))

    # 수면 상태
    is_sleeping: bool = False
    sleep_ticks_remaining: int = 0

    # ─── Phase 1: 에피소드 기억 ─────────────────────────
    episodes: list = field(default_factory=list)  # EpisodeTrace 리스트 (ring buffer, 최대 50개)
    episode_max: int = 50

    # 캐시 (무의식 고속도로 — 상황→행동 매핑)
    habit_cache: dict = field(default_factory=dict)  # {context_hash: action}

    CLUSTER_NAMES = ["V", "L", "S", "B", "A", "T", "C", "G", "F", "I", "D", "P"]
    CHILJEONG_NAMES = ["joy", "anger", "sadness", "fear", "love", "disgust", "desire"]
    OYOK_NAMES = ["hunger", "sleepiness", "lust", "greed", "honor"]

    def tone_dict(self) -> dict:
        return {name: float(val) for name, val in zip(self.CLUSTER_NAMES, self.tone)}

    def emotion_dict(self) -> dict:
        return {name: float(val) for name, val in zip(self.CHILJEONG_NAMES, self.chiljeong)}

    def add_episode(self, episode: 'EpisodeTrace'):
        """에피소드 기억 추가 (ring buffer)."""
        self.episodes.append(episode)
        if len(self.episodes) > self.episode_max:
            # salience 가장 낮은 것 제거 (망각)
            self.episodes.sort(key=lambda e: e.salience, reverse=True)
            self.episodes = self.episodes[:self.episode_max]

    def update_emotion(self, action: str, energy: float, prev_energy: float):
        """행동과 상태 변화에 따른 감정 갱신."""
        decay = 0.9  # 감정 자연 감쇠 (매 틱 10% 회귀)
        self.chiljeong *= decay

        # 식사 → 기쁨
        if action == "eat":
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.3)  # joy

        # 에너지 급락 → 두려움
        if energy < 0.2:
            self.chiljeong[3] = min(1.0, self.chiljeong[3] + 0.2)  # fear

        # 에너지 회복 → 기쁨
        if energy > prev_energy + 0.1:
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.1)  # joy

        # 배고픔 높으면 → 짜증(분노) + 갈망
        if self.oyok[0] > 0.7:
            self.chiljeong[1] = min(1.0, self.chiljeong[1] + 0.1)  # anger
            self.chiljeong[6] = min(1.0, self.chiljeong[6] + 0.2)  # desire

        # 탐험 → 기쁨 약간
        if action == "explore":
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.1)  # joy

        # 클리핑
        self.chiljeong = np.clip(self.chiljeong, -1.0, 1.0)

    def update_tone_from_emotion(self):
        """감정 → 12클러스터 tone 영향."""
        # 기쁨 → V(Drive)↑, L(Liking)↑
        self.tone[0] = np.float16(1.0 + float(self.chiljeong[0]) * 0.2)  # V
        self.tone[1] = np.float16(1.0 + float(self.chiljeong[0]) * 0.15)  # L

        # 분노 → A(Acute)↑, S(Stability)↓, D(Dominance)↑
        self.tone[4] = np.float16(1.0 + float(self.chiljeong[1]) * 0.3)  # A
        self.tone[2] = np.float16(1.0 - float(self.chiljeong[1]) * 0.2)  # S
        self.tone[10] = np.float16(1.0 + float(self.chiljeong[1]) * 0.2)  # D

        # 두려움 → A↑, I(Inhibition)↑, P(Protection)↑
        self.tone[4] = np.float16(min(2.0, float(self.tone[4]) + float(self.chiljeong[3]) * 0.2))  # A
        self.tone[9] = np.float16(1.0 + float(self.chiljeong[3]) * 0.2)  # I
        self.tone[11] = np.float16(1.0 + float(self.chiljeong[3]) * 0.3)  # P

        # 갈망 → V↑, F(Fatigue) 약간↑
        self.tone[0] = np.float16(min(2.0, float(self.tone[0]) + float(self.chiljeong[6]) * 0.15))  # V
        self.tone[8] = np.float16(1.0 + float(self.chiljeong[6]) * 0.1)  # F


# ─── L3d: Episode Trace (기억) ────────────────────────────────

@dataclass
class EpisodeTrace:
    """에피소드 기억 1건."""
    tick: int
    action: str
    emotion_snapshot: np.ndarray  # chiljeong 복사본
    energy_at_time: float
    salience: float = 0.5        # 중요도 (감정 강도에 비례)
    recall_count: int = 0        # 인출 횟수

    def compute_salience(self, emotion: np.ndarray) -> float:
        """감정 강도로 salience 계산."""
        self.salience = float(np.abs(emotion).max()) * 0.7 + 0.3
        return self.salience


# ─── Layer 4: Agency ──────────────────────────────────────────

@dataclass
class ActionProposal:
    """Anima가 제안하는 행동."""
    persona_id: str
    tick: int
    action_type: str       # "idle", "work", "eat", "sleep", "explore", "socialize"
    target_id: Optional[str] = None
    confidence: float = 0.5
    energy_cost: float = 0.01
    intensity: int = 1      # 1~4
    fallback_flag: int = 0  # 0=정상, 1=캐시폴백, 2=직전반복, 3=no-op
