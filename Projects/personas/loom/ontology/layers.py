"""
Layer 0~4: 페르소나 국가 온톨로지 데이터 구조 (Phase 0)

world-ontology.md의 코드 실현.
Phase 0에서 필요한 Layer만 구현. 나머지는 Phase별 점진 추가.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
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


# ─── Layer 1a: Territory + Facility ───────────────────────────

@dataclass
class Facility:
    """시설 1개. life-simulation-design.md §1.2."""
    type: str           # "housing", "tavern", "market", "academy", "workshop", "clinic", "office", "temple"
    name: str = ""
    capacity: int = 10
    cost_gold: float = 0.0
    # 기후 보호 속성
    shelter_warmth: float = 0.0   # 0~1, 1=완벽 방한 (housing=0.9, tavern=0.7, outdoor=0)
    shelter_rain: float = 0.0     # 0~1, 1=완벽 방수
    energy_recovery: float = 0.0  # 시설 이용 시 에너지 회복량


# 시설 유형별 기본값
FACILITY_DEFAULTS: dict[str, dict] = {
    "housing":  {"shelter_warmth": 0.9, "shelter_rain": 0.95, "energy_recovery": 0.02, "cost_gold": 0},
    "tavern":   {"shelter_warmth": 0.7, "shelter_rain": 0.8,  "energy_recovery": 0.01, "cost_gold": 5},
    "market":   {"shelter_warmth": 0.3, "shelter_rain": 0.5,  "energy_recovery": 0.0,  "cost_gold": 0},
    "academy":  {"shelter_warmth": 0.8, "shelter_rain": 0.9,  "energy_recovery": 0.0,  "cost_gold": 20},
    "workshop": {"shelter_warmth": 0.6, "shelter_rain": 0.7,  "energy_recovery": 0.0,  "cost_gold": 10},
    "clinic":   {"shelter_warmth": 0.85,"shelter_rain": 0.9,  "energy_recovery": 0.05, "cost_gold": 15},
    "office":   {"shelter_warmth": 0.8, "shelter_rain": 0.9,  "energy_recovery": 0.0,  "cost_gold": 0},
    "temple":   {"shelter_warmth": 0.7, "shelter_rain": 0.8,  "energy_recovery": 0.01, "cost_gold": 0},
}


@dataclass
class GovernancePolicy:
    """영주의 현재 통치 정책. SNN 신호에서 도출되어 매 48틱마다 갱신."""
    tax_rate: float = 0.10
    food_priority: float = 0.5
    stockpile_target: float = 0.5
    treasury_spending_cap: float = 0.3
    market_openness: float = 0.5          # Phase 15-A: 외부 교역 개방도 [0.0, 1.0]
    public_works_rate: float = 0.0        # Phase 16: SNN-driven public works rate [0.0, 0.8]
    last_updated_tick: int = 0


@dataclass
class CommunityMetrics:
    """Phase 15 trust-density metrics for one territory."""
    territory_id: str
    node_count: int
    edge_count: int
    density_ratio: float
    intra_edges: int
    inter_edges: int
    intra_inter_ratio: float


@dataclass
class Territory:
    """영지. 페르소나가 살아가는 물리적 공간."""
    id: str
    name: str
    region: str              # "claude", "codex", "gemini"
    population: int = 0
    facilities: list = field(default_factory=list)  # Facility 리스트
    infra_level: int = 1     # 인프라 레벨 1~5
    gdp: float = 0.0

    # ── 영주 + 금고 ──────────────────────────────────────
    lord_id: Optional[str] = None      # 영주 페르소나 ID (None = 무주공산)
    treasury_gold: float = 0.0         # 영지 금고 (gold 단위)
    treasury_will: float = 0.0         # 영지 WILL 금고
    tax_rate: float = 0.1              # 소득세율 (기본 10%)
    factionRef: Optional[str] = None   # faction.id 투영값
    # ── 통치 정책 (Phase 13) ────────────────────────
    policy: GovernancePolicy = field(default_factory=GovernancePolicy)
    tax_collected_total: float = 0.0   # 누적 징수액
    food_reserve: float = 0.0          # 영지 식량 비축량
    # 분기 통계
    gdp_this_quarter: float = 0.0      # 이번 분기 GDP (WILL)
    chronicle: list = field(default_factory=list)  # {"tick": int, "type": str, "summary": str}
    last_snn_signals: dict = field(default_factory=dict)  # Phase 16: latest policy SNN readout
    last_snn_signals_tick: int = -1
    inventory: dict = field(default_factory=lambda: {
        "food": 0.0, "material": 0.0, "tool": 0.0, "medicine": 0.0, "knowledge": 0.0,
    })
    quarter_tax_income: float = 0.0
    quarter_public_spend: float = 0.0
    internal_food_procured_total: float = 0.0
    last_npc_food_purchase_tick: int = -9999
    communal_farms: int = 1
    food_crisis_counter: float = 0.0

    def get_facility(self, ftype: str) -> Optional['Facility']:
        """시설 유형으로 검색."""
        for f in self.facilities:
            if f.type == ftype:
                return f
        return None

    def best_shelter(self) -> float:
        """영지 내 최고 shelter_warmth 값."""
        if not self.facilities:
            return 0.0
        return max(f.shelter_warmth for f in self.facilities)


@dataclass(slots=True)
class Faction:
    """Phase 17 faction registry entry."""
    id: str
    name: str
    founder_pid: str
    charter: tuple[str, ...]
    created_tick: int
    grace_until_tick: int = 0

    def __post_init__(self) -> None:
        charter = tuple(self.charter)
        if not (3 <= len(charter) <= 5):
            raise ValueError(f"charter length {len(charter)} out of [3, 5]")
        if len(set(charter)) != len(charter):
            raise ValueError(f"charter has duplicates: {charter!r}")
        self.charter = charter


def create_default_territory(tid: str, name: str, region: str) -> 'Territory':
    """기본 시설이 포함된 영지 생성."""
    facilities = []
    for ftype, defaults in FACILITY_DEFAULTS.items():
        f = Facility(type=ftype, name=f"{name} {ftype}", **defaults)
        facilities.append(f)
    return Territory(id=tid, name=name, region=region, facilities=facilities)

MAX_TRACKED_FACTIONS_PER_PERSONA = 8

# ── Phase 17 affiliation_score (v6: Stage 5 Anti-Collapse 가중치 재균형 2026-04-25) ──
# trust 누적 우위와 territory 동시성 비대칭을 0.5 동률로 재균형.
W_TERRITORY_SAME = 0.5   # 같은 territory 거주 시 (v5: 0.3 → v6: 0.5, trust와 동률)
W_TERRITORY_DIFF = 0.1   # 다른 territory 거주 시 (v4: 0.0 → v5: 0.1, 완전 차단 제거)
W_TRUST = 0.5            # (v3~v5: 0.8 → v6: 0.5, 누적 우위 비대칭 해소)
W_GRIEVANCE = 0.6
W_PROXIMITY = 0.4
DECAY = 0.92
GRIEVANCE_MIN_SHARED = 0.3
PROXIMITY_DECAY_SCALE = 10.0

FACTION_COOLDOWN_TICKS = 48
FACTION_COMMIT_EVERY = 48
THETA_JOIN = 2.5

# DRIFT_MARGIN: v4까지 고정 1.2 → v5 동적 계산의 하한으로 재해석
# actual_margin = max(DRIFT_MARGIN_MIN, gap × DRIFT_MARGIN_RATIO)
DRIFT_MARGIN_MIN = 0.3
DRIFT_MARGIN_RATIO = 0.15

# ── Phase 17 v6: collapse 완화 (size tax + homeostasis, 2026-04-24) ──
# 근거: v5 probe 3 seed 전원 active_end=1 붕괴 (PHASE-17-FACTION-COLLAPSE-MITIGATION-SPEC.md)
# 1. Faction 규모 tax: size_ratio가 START를 넘기면 선형 감쇠, MIN이 하한
FACTION_SIZE_TAX_START = 0.3     # 전체 활성 인구 대비 30% 초과분부터 tax 적용
FACTION_SIZE_TAX_MIN = 0.3       # tax 하한 (점유 100%여도 30%는 남아 신규 가입 경로 보존)
# 2. Homeostasis: active faction 수에 따라 drift margin_floor 조절
HOMEOSTASIS_LOW_THRESHOLD = 2    # active 수 2 이하일 때 완화 모드 진입
HOMEOSTASIS_DRIFT_MARGIN_SCALE = 0.5   # 완화 모드에서의 DRIFT_MARGIN_MIN 배수

# ── Phase 17 Stage 3: anti-collapse (minority persistence + founder respawn, 2026-04-24) ──
# 근거: v6 probe 3 seed 전원 active_end=1 붕괴 (absorbing state). B+C 조합으로 예방+치료.
# B. Minority persistence: 소규모 faction의 territory 동거 가산을 줘서 멸종 직전 유지
MINORITY_PERSISTENCE_MAX_MEMBERS = 2      # members <= 2일 때 boost 적용
MINORITY_PERSISTENCE_BOOST = 0.15         # score 가산값 (= DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE 와 동일 규모)
# C. Founder respawn: active < target이면 K틱 주기로 territory lord 기반 신규 faction 생성
FOUNDER_RESPAWN_EVERY = 480               # FACTION_COMMIT_EVERY * 10 (48 * 10). commit 주기와 정합
FOUNDER_RESPAWN_TARGET_ACTIVE = 2         # active 가 2 미만일 때만 발동 (overspawn 방지)

# ── Phase 17 Stage 5: Respawn grace period (G, 2026-04-25) ──
# 신생 faction이 trust 누적 우위에 즉시 재흡수되는 second-collapse pattern을 완화.
# faction_cooldown(재가입 락)과 분리된 drift 면역 채널.
RESPAWN_GRACE_TICKS = 200

# 하위 호환 (기존 import 유지용, 실제 경로는 동적 계산이 우선)
DRIFT_MARGIN = DRIFT_MARGIN_MIN  # deprecated: 동적 계산 사용
W_TERRITORY = W_TERRITORY_SAME   # deprecated: same territory weight alias

NORM_PRIMITIVE_CATALOG: tuple[str, ...] = (
    # 자원·경제 (3)
    "토지_공유", "무역_개방", "재산_개인",
    # 권위·계층 (3)
    "장자_상속", "능력주의", "원로회의",
    # 대외 관계 (3)
    "외세_배척", "이방인_환대", "중립_유지",
    # 종교·문화 (3)
    "선조_숭배", "자연_경외", "지식_추구",
)
CHARTER_PRIMITIVE_COUNT = (3, 5)

FACTION_PROJECT_EVERY = 24
FACTION_HYSTERESIS = 2

FACTION_TELEMETRY_BIAS_OWN = 0.05
FACTION_TELEMETRY_BIAS_NEIGHBOR = 0.03


# ─── Layer 6: Economy ─────────────────────────────────────────


class Goods(str, Enum):
    """교환 가능한 재화 유형."""
    FOOD = "food"
    MATERIAL = "material"
    TOOL = "tool"
    MEDICINE = "medicine"
    KNOWLEDGE = "knowledge"


# ── goods 경제 상수 (Phase 11) ───────────────────────────────
FOOD_CONSUME_PER_TICK: int = 1              # 매 틱 식량 소비량
TOOL_MAX_DURABILITY: int = 100              # 신규 도구 내구도
TOOL_WEAR_PER_TICK: int = 1                 # 작업 1틱당 마모
TOOL_PRODUCTIVITY_BONUS: float = 0.5        # 도구 보유 시 산출 +50%
TOOL_BROKEN_PENALTY: float = 0.3            # 도구 없으면 산출 -30%
TOOL_REPAIR_COST_GOLD: float = 5.0          # 수리 gold 비용 (싱크)
TOOL_REPAIR_MATERIAL: int = 2               # 수리 자재 비용

# 직업 → 산출 재화
JOB_OUTPUT_MAP: dict[str, str] = {
    "farmer": "food", "laborer": "material", "craftsman": "tool",
    "healer": "medicine", "scholar": "knowledge", "guard": "material",
}
# 직업별 기본 산출량 (1틱, 보정 전)
JOB_BASE_OUTPUT: dict[str, float] = {
    "farmer": 3.0, "laborer": 1.5, "craftsman": 0.5,
    "healer": 0.3, "scholar": 0.2, "guard": 0.5,
}

# NPC 상점 (외부 상단 — 비싸고 제한적)
NPC_PRICES: dict[str, dict] = {
    "food":      {"buy": 10, "sell": 5,  "daily_stock": 50},
    "material":  {"buy": 15, "sell": 7,  "daily_stock": 30},
    "tool":      {"buy": 60, "sell": 20, "daily_stock": 5},
    "medicine":  {"buy": 30, "sell": 10, "daily_stock": 10},
    "knowledge": {"buy": 45, "sell": 15, "daily_stock": 3},
}

# 시설 이용료 (gold 싱크 — 50% 소멸)
FACILITY_FEES: dict[str, float] = {
    "market": 2.0, "academy": 10.0, "workshop": 5.0, "clinic": 8.0,
}

MARKET_ORDER_EXPIRY_TICKS: int = 48         # 주문서 만료
MARKET_FEE_SINK_RATIO: float = 0.5          # 수수료 중 소멸 비율
GOLD_DIRECT_PAY_RATIO: float = 0.0          # 자영 노동 gold 제거 — 모든 gold는 거래(NPC/P2P)로만 획득 Phase 15-F
PUBLIC_WORKS_WAGE_PER_TICK: float = 5.0
PUBLIC_WORKS_DURATION: int = 24
PUBLIC_WORKS_INTERVAL: int = 24
PUBLIC_WORKS_MIN_TREASURY: float = 500.0
PUBLIC_WORKS_MAX_TREASURY_RATIO: float = 0.5
PUBLIC_WORKS_IN_KIND_RATIO: float = 0.5
STALE_SIGNAL_TICKS: int = 72
FOOD_STOCKPILE_RESERVE_THRESHOLD: float = 30.0
QUARTER_TAX_BUDGET_MULTIPLIER: float = 1.2
INTERNAL_FOOD_PRICE_RATIO: float = 0.75
PERSONA_FOOD_SAFE_STOCK: float = 12.0
PUBLIC_WORKS_RATE_MIN: float = 0.03
HUNGER_PRESSURE_WEIGHT: float = 0.2
PUBLIC_WORKS_FARMER_BIAS: float = 2.0
HUNGER_TRIGGER_THRESHOLD: float = 0.3
PUBLIC_WORKS_BASE_ACTIVATION: float = 0.04
NPC_FOOD_PURCHASE_COOLDOWN_TICKS: int = 48
FOOD_STOCKPILE_RESERVE_PER_PERSONA: float = 14.0
NPC_FOOD_TRIGGER_RESERVE_RATIO: float = 0.5
PUBLIC_WORKS_LOW_GOLD_THRESHOLD: float = 300.0
"""怨듦났洹쇰줈 ?꾩떆 ?꾨낫 ?몄엯 ??wallet.gold 媛 ??媛?誘몃쭔??????뚮뱷?쇰줈 媛꾩＜."""

PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO: float = 0.2
"""Phase 16-F: 怨듦났洹쇰줈 ?덉궛??treasury 湲곕컲 ?섑븳??鍮꾩쑉.
?몄닔(qincome)媛 ??븘??湲덇퀬媛 異⑸텇?섎㈃ 怨듦났洹쇰줈 吏묓뻾 媛?ν븯?꾨줉 ?쒗솚 李몄“瑜??뚭눼.
洹쇰낯: persona gold ??쓬 ???뚮퉬/?몄닔 ?????cap_income ?????public_works 遺덈컻
     ???섎Ⅴ?뚮굹 gold ?좎엯 ?놁쓬 (?먭린媛뺥솕 ?낆닚??.
Treasury??20%瑜??덉궛 floor濡??ъ슜?섏뿬 cycle ???딆쓬. 
cap_treasury(=0.5 횞 treasury) 濡?overspending? 怨꾩냽 諛⑹???"""

PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD: float = 0.5
"""Phase 16-G: ??媛??댁긽??tension ?먮뒗 food_crisis ?쒖꽦 ??part-time ?꾨낫 ? 媛쒕갑.
employed persona 瑜?異붽? ?꾨낫濡??ы븿?섎릺 employment_id ??遺덈?."""

PUBLIC_WORKS_PARTTIME_WAGE_RATIO: float = 0.5
"""Phase 16-G: part-time ?꾧툑 鍮꾩쑉 (full-time ?鍮?.
employed persona ???대? 怨좎슜 ?뚮뱷???덉쑝誘濡??덈컲 ?꾧툑留?吏湲?"""

PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO: float = 0.5
"""Phase 16-G: part-time ?앹궛 鍮꾩쑉 (full-time ?鍮?.
蹂몄뾽怨?遺꾪븷 ?몃룞?대?濡?怨듦났洹쇰줈 ?곗텧???덈컲."""

PUBLIC_WORKS_BOOTSTRAP_GROWTH: float = 0.3
"""Phase 16-G: 珥덇린 72??STALE_SIGNAL_TICKS) ?숈븞 SNN ?좏샇 ?놁쓣 ???ъ슜??湲곕낯 growth.
媛?0.3: ?꾨쭔??湲띿젙 ?좏샇. economy ?쒖옉 吏??"""

PUBLIC_WORKS_BOOTSTRAP_TENSION: float = 0.2
"""Phase 16-G: 珥덇린 72???숈븞 湲곕낯 tension. part-time ?쒖꽦??寃쎄퀎 ?꾨옒,
怨듦났洹쇰줈 吏묓뻾? 媛?ν븳 ??? ?섏?."""

PUBLIC_WORKS_STALE_DECAY_WINDOW: float = 168.0
"""Phase 16-H: stale signal linear decay window (ticks).
When sig_age exceeds STALE_SIGNAL_TICKS(72), decay linearly over this window.
72 + 168 = 240 reaches the decay floor."""

PUBLIC_WORKS_STALE_DECAY_FLOOR: float = 0.3
"""Phase 16-H: minimum stale signal strength.
Keep stale signals partially useful instead of collapsing to a hard zero."""

PUBLIC_WORKS_STALE_MAX_AGE: int = 480
"""Phase 16-H: maximum usable stale signal age (ticks).
Signals older than this are skipped completely."""

PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD: int = 12
"""怨듦났洹쇰줈 ?꾩떆 ?꾨낫 ?몄엯 ??consecutive_hunger_ticks 媛 ??媛??댁긽????援띠＜由쇱쑝濡?媛꾩＜."""

FOOD_LABOR_NON_FARMER_RATIO: float = 0.7
"""Food crisis mode ?먯꽌 鍮꼎armer ??food ?앹궛 怨꾩닔 (farmer ?鍮?70%)."""

COMMUNAL_FARM_BOOST: float = 0.3
"""Communal farm 1媛쒕떦 food ?앹궛 利앺룺 鍮꾩쑉. produced *= (1 + farms 횞 0.3)."""

FOOD_CRISIS_FARM_THRESHOLD: float = 3.0
"""food_crisis_counter 媛 ??媛??댁긽?????곸＜媛 ?먮룞?쇰줈 farm ?뺤옣 嫄댁꽕???쒕룄 (float ??counter 媛 鍮꾨?移?媛먯냼)."""

FARM_EXPANSION_COST_GOLD: float = 500.0
"""Farm 1媛??뺤옣 鍮꾩슜 ??treasury_gold ?먯꽌 李④컧."""

FOOD_CRISIS_RESERVE_RATIO: float = 0.4
"""Food crisis mode 諛쒕룞 threshold ??reserve < reserve_target 횞 ??媛?+ hunger 議곌굔."""

FOOD_CRISIS_COUNTER_DECAY: float = 0.5
"""NPC 臾대ℓ???ъ씠?대떦 food_crisis_counter 媛먯냼????+1/-0.5 鍮꾨?移??ㅺ퀎."""

MOVE_CANDIDATE_K = 5
MOVE_SOFTMAX_T = 0.5
MIGRATION_COOLDOWN_DEFAULT = 6
MOVE_DISALLOWED_BIOMES = frozenset({"water", "mountain"})
MOVE_WEIGHTS: dict[str, float] = {
    "food": 2.0,
    "material": 1.0,
    "path_cost": -1.5,
    "dist": -0.5,
}


def score_move(cell, persona) -> float:
    """Score a movement candidate tile for Phase 17."""
    dx = abs(persona.pos[0] - cell.x)
    dy = abs(persona.pos[1] - cell.y)
    dist = dx if dx > dy else dy
    return (
        MOVE_WEIGHTS["food"] * cell.resources.get("food", 0.0)
        + MOVE_WEIGHTS["material"] * cell.resources.get("material", 0.0)
        + MOVE_WEIGHTS["path_cost"] * cell.path_cost
        + MOVE_WEIGHTS["dist"] * dist
    )


@dataclass
class Wallet:
    """페르소나의 지갑. WILL(대형 거래) + gold(일상 소비)."""
    persona_id: str
    will: float = 0.0    # 1 WILL = 1,000 gold
    gold: float = 0.0    # 일상 소비 단위

    def total_in_gold(self) -> float:
        return self.will * 1000 + self.gold

    def pay(self, amount_gold: float) -> bool:
        """gold 지불. 부족하면 WILL 환전. 실패 시 False."""
        if self.gold >= amount_gold:
            self.gold -= amount_gold
            return True
        # WILL 환전 시도
        needed = amount_gold - self.gold
        will_needed = needed / 1000
        if self.will >= will_needed:
            self.will -= will_needed
            self.gold = 0
            return True
        return False  # 잔액 부족

    def receive(self, amount_gold: float):
        """gold 수령."""
        self.gold += amount_gold


# ─── Layer 6 확장: 숙달 & 집중 시스템 ────────────────────────

# 직업별 (천장, 복잡도, base_lr)
# 천장: 숙달 최대치. 복잡도: 집중/적성 의존도. base_lr: 기본 학습률.
SKILL_CEILINGS: dict[str, tuple[float, float, float]] = {
    "laborer":    (0.3, 0.2, 0.010),   # 낮은 천장, 빠른 학습
    "farmer":     (0.5, 0.4, 0.006),   # 중간 천장
    "guard":      (0.5, 0.4, 0.005),   # 중간 천장
    "craftsman":  (0.8, 0.7, 0.003),   # 높은 천장, 장인의 길
    "healer":     (0.9, 0.8, 0.002),   # 매우 높은 천장
    "scholar":    (1.0, 0.9, 0.001),   # 무한에 가까운 천장
}

# ─── Layer 0.5: 자연법 응징 등급 ─────────────────────────────
# Nomos는 전지적으로 위반을 탐지 (증거 불필요).
# 누적 위반이 에스컬레이션을 결정.
NOMOS_SEVERITY = {
    "경미": {  # 사소한 규칙 일탈
        "threshold": 1,           # violation_count >= 1
        "class_penalty": 0,       # 클래스 강등 없음
        "blocked_ticks": 0,       # 행동 제한 없음
        "stress_delta": 0.01,     # chronic_stress 증가
        "emotion_delta": 0.05,    # anger/fear 증가
    },
    "중대": {  # 의도적 법 위반 (반복 착취, 지속적 미이행)
        "threshold": 5,           # violation_count >= 5
        "class_penalty": 1,       # 1 클래스 강등
        "blocked_ticks": 48,      # 2일간 행동 제한 (work 불가)
        "stress_delta": 0.05,
        "emotion_delta": 0.2,
    },
    "금기": {  # 세계 근본 규칙 도전 (생명 침해, 극단 착취)
        "threshold": 10,          # violation_count >= 10 또는 제1조 위반
        "class_penalty": 3,       # 3 클래스 강등
        "blocked_ticks": 200,     # 장기 행동 제한
        "stress_delta": 0.15,
        "emotion_delta": 0.5,
        "physis_penalty": True,   # 영지 기후 이상 트리거
    },
}
NOMOS_DECAY_INTERVAL: int = 100   # 무위반 100틱마다 violation_count -1

# ─── Layer 7: 클래스 승급 규칙 ──────────────────────────────
# class → {trigger 임계, gate 임계}
# 하이브리드 2단계: STDP 안정화(trigger) + 사회적 검증(gate)
CLASS_RULES: dict[int, dict] = {
    # flow_thr: 몰입 비율은 3중 조건(집중>0.6, 적성>0.5, 0.2<숙달비<0.8)으로 발생하므로
    # 실제 달성 가능 범위(0.05~0.35)에 맞게 보정. 핵심은 절대값이 아닌 "안정적 STDP 패턴".
    # contribution: 최근 500틱 moving window raw sum 기준
    2: {"base_obs_ticks": 200, "flow_thr": 0.05, "drive_var_max": 0.15,
        "gate": {"mastery_ratio": 0.3, "contribution": 0.05, "peer": 0.05, "stability": 0.5}},
    3: {"base_obs_ticks": 400, "flow_thr": 0.10, "drive_var_max": 0.12,
        "gate": {"mastery_ratio": 0.5, "contribution": 0.15, "peer": 0.15, "stability": 0.6}},
    4: {"base_obs_ticks": 700, "flow_thr": 0.18, "drive_var_max": 0.10,
        "gate": {"mastery_ratio": 0.7, "contribution": 0.30, "peer": 0.3, "stability": 0.7}},
    5: {"base_obs_ticks": 1000, "flow_thr": 0.25, "drive_var_max": 0.08,
        "gate": {"mastery_ratio": 0.85, "contribution": 0.50, "peer": 0.45, "stability": 0.75}},
}

CLASS_TITLES: dict[int, str] = {
    1: "초심자", 2: "견습생", 3: "장인", 4: "숙련가", 5: "대가",
}


@dataclass
class SkillProfile:
    """한 페르소나의 한 직업에 대한 숙달 추적."""
    persona_id: str
    skill_id: str           # Job.title과 매칭
    mastery: float = 0.0    # 0 ~ ceiling
    total_ticks: int = 0    # 이 직업에 투자한 총 틱
    consecutive_ticks: int = 0  # 현재 연속 작업 틱
    last_tick: int = 0      # 마지막 작업 틱
    peak_concentration: float = 0.0  # 달성한 최고 집중도
    flow_ticks: int = 0     # 몰입 상태 총 틱
    burnout_accumulator: float = 0.0  # 번아웃 누적 (0~1)


def compute_concentration(tone: np.ndarray, energy_pool: float) -> float:
    """7개 화학물질의 동시 조건 → 집중도 (0~1).

    모든 조건이 충족되어야 집중할 수 있다 (곱셈 구조).
    A(NE)와 T(CORT)는 역U자 곡선 (Yerkes-Dodson).
    """
    def norm(val: float) -> float:
        """tone 값(0.5~2.0 범위)을 0~1로 정규화."""
        return max(0.0, min(1.0, (val - 0.5) / 1.0))

    def inverted_u(val: float, optimal: float = 1.1, width: float = 0.5) -> float:
        """역U자 곡선: optimal에서 최대, 양쪽으로 감소."""
        deviation = (val - optimal) / width
        return max(0.0, min(1.0, 1.0 - deviation * deviation))

    c_ach  = norm(float(tone[6]))   # C: 시냅스 가소성
    v_da   = norm(float(tone[0]))   # V: 동기 유지
    s_5ht  = norm(float(tone[2]))   # S: 충동 억제
    i_gaba = norm(float(tone[9]))   # I: 잡음 차단

    a_optimal = inverted_u(float(tone[4]), optimal=1.1, width=0.5)  # A: 각성
    t_optimal = inverted_u(float(tone[5]), optimal=1.05, width=0.4) # T: 스트레스

    fatigue_factor = max(0.0, 1.0 - norm(float(tone[8])))  # F: 피로 역수

    energy_gate = min(1.0, energy_pool / 0.5)  # 에너지 < 0.5이면 급감

    # 기하평균 기반 집중도 (순수 곱셈은 7인자에서 너무 가혹)
    # 하나가 0이면 전체 0은 유지 (최소값 게이트), 나머지는 기하평균
    factors = [c_ach, v_da, a_optimal, s_5ht, t_optimal, fatigue_factor, i_gaba]
    min_factor = min(factors)
    if min_factor < 0.01:
        return 0.0  # 하나라도 완전히 0이면 집중 불가

    # 기하평균: (f1 × f2 × ... × f7)^(1/7) — 곱셈보다 관대, 산술평균보다 엄격
    product = 1.0
    for f in factors:
        product *= f
    geo_mean = product ** (1.0 / len(factors))

    return max(0.0, min(1.0, geo_mean * energy_gate))


def compute_aptitude_map(personality: np.ndarray, seed: int) -> dict[str, float]:
    """성격 5축 + seed → 직업별 적성 (0.3~1.0). 생성 시 1회 계산."""
    rng = np.random.default_rng(seed + 7777)
    p = personality  # [-1, +1] 5축

    aptitudes = {}

    # laborer: 편차 거의 없음
    aptitudes["laborer"] = 0.7 + rng.uniform(-0.1, 0.1)

    # farmer: 엄격(p[4]) + 이성(-p[2]) + 독립(-p[3])
    aptitudes["farmer"] = 0.5 + 0.1 * p[4] + 0.05 * (-p[2]) + 0.05 * (-p[3])

    # guard: 대담(p[1]) + 외향(p[0]) + 엄격(p[4])
    aptitudes["guard"] = 0.5 + 0.1 * p[1] + 0.05 * p[0] + 0.1 * p[4]

    # craftsman: 내향(-p[0]) + 이성(-p[2]) + 엄격(p[4]) + 독립(-p[3])
    aptitudes["craftsman"] = 0.5 + 0.1*(-p[0]) + 0.1*(-p[2]) + 0.1*p[4] + 0.05*(-p[3])

    # healer: 감성(p[2]) + 협조(p[3]) + 관대(-p[4]) + 외향(p[0])
    aptitudes["healer"] = 0.5 + 0.1*p[2] + 0.1*p[3] + 0.1*(-p[4]) + 0.05*p[0]

    # scholar: 이성(-p[2]) + 내향(-p[0]) + 독립(-p[3]) + 신중(-p[1])
    aptitudes["scholar"] = 0.5 + 0.15*(-p[2]) + 0.1*(-p[0]) + 0.05*(-p[3]) + 0.05*(-p[1])

    for k in aptitudes:
        aptitudes[k] += rng.uniform(-0.05, 0.05)
        aptitudes[k] = float(max(0.3, min(1.0, aptitudes[k])))

    return aptitudes


def compute_mastery_gain(
    skill_profile: 'SkillProfile',
    concentration: float,
    aptitude: float,
    skill_id: str,
) -> float:
    """1틱 숙달 성장량. 천장 근처에서 감쇠, 복잡한 직업은 집중 의존."""
    ceiling, complexity, base_lr = SKILL_CEILINGS.get(skill_id, (0.5, 0.5, 0.005))

    headroom = max(0.0, ceiling - skill_profile.mastery)
    headroom_ratio = headroom / ceiling if ceiling > 0 else 0
    diminishing = headroom_ratio ** 0.5

    # 복잡도에 따른 집중 의존도
    concentration_effect = (1.0 - complexity) + complexity * concentration

    # 적성 효과 (복잡도에 비례하여 중요)
    aptitude_effect = (1.0 - complexity * 0.5) + complexity * 0.5 * aptitude

    # 연속 작업 보너스 (최대 1.5x, 10틱 연속)
    streak_bonus = min(1.5, 1.0 + skill_profile.consecutive_ticks * 0.05)

    # 번아웃 페널티
    burnout_penalty = 1.0
    if skill_profile.burnout_accumulator > 0.5:
        burnout_penalty = 0.5
    elif skill_profile.burnout_accumulator > 0.3:
        burnout_penalty = 1.0 - skill_profile.burnout_accumulator * 0.5

    return max(0.0, base_lr * diminishing * concentration_effect
               * aptitude_effect * streak_bonus * burnout_penalty)


def compute_output_multiplier(mastery: float, skill_id: str) -> float:
    """숙달도 → 경제 산출 배율 (0.5x ~ 2.0x)."""
    ceiling = SKILL_CEILINGS.get(skill_id, (0.5, 0.5, 0.005))[0]
    mastery_ratio = mastery / ceiling if ceiling > 0 else 0
    return 0.5 + 1.5 * mastery_ratio


@dataclass
class Job:
    """페르소나가 만든 일자리. 고용주가 WILL을 내고 만든다."""
    id: str
    employer_id: str          # 일자리를 만든 페르소나
    title: str                # "farmer", "guard", "craftsman" 등 (자유 설정)
    description: str = ""     # 무엇을 하는 일인가
    wage_per_tick: float = 5.0   # gold/틱 (고용주가 결정)
    max_employees: int = 1
    created_tick: int = 0
    is_open: bool = True      # 구인 중

    # 노동 가치 이론
    snlt_hours: float = 3.0   # 사회적 필요 노동시간 (market norm)
    output_type: str = "labor"  # "food", "tool", "service", "knowledge" 등


@dataclass
class Employment:
    """고용 계약. 고용주 ↔ 피고용인."""
    job_id: str
    employer_id: str
    employee_id: str
    start_tick: int
    wage_per_tick: float      # 계약 임금 (gold/틱)

    # 추적
    ticks_worked: int = 0
    total_earned: float = 0.0   # 벌었어야 할 금액
    total_paid: float = 0.0     # 실제로 받은 금액
    grievances: int = 0         # 미지급 횟수

    @property
    def unpaid(self) -> float:
        return max(0, self.total_earned - self.total_paid)

    @property
    def exploitation_score(self) -> float:
        """착취도 0~1. 1 = 완전 착취. 0 = 완전 이행."""
        if self.total_earned == 0:
            return 0.0
        return self.unpaid / self.total_earned


@dataclass
class MarketOrder:
    """P2P 시장 주문서."""
    id: str
    seller_id: str
    goods_type: str             # "food", "material" 등
    quantity: float
    price_per_unit: float       # gold 단위
    created_tick: int
    territory_id: str


# ─── Layer 1a 확장: 자연 자원 ─────────────────────────────────

@dataclass
class WildFood:
    """자연에서 채집 가능한 식재료. 외형과 실체가 다를 수 있다."""
    id: str           # 실제 ID (독버섯, 산나물 등)
    name: str         # 실제 이름
    region: str
    discovery_prob: float = 0.1

    # ── 외형 (겉으로 보이는 것) ──────────────────────────
    # 외형이 같아도 실제 식물이 다를 수 있음 (독버섯 ≈ 식용버섯)
    apparent_name: str = ""     # 외형상 보이는 이름 ("갈색 버섯", "빨간 열매" 등)
    lookalike_id: Optional[str] = None  # 혼동 가능한 다른 식물 ID

    # ── 식별 난이도 ──────────────────────────────────────
    # 0 = 누구나 즉시 구분 (색이 선명, 냄새가 강함)
    # 1 = 전문가도 헷갈림
    identification_difficulty: float = 0.3

    # ── 효과 (랜덤 범위) ──────────────────────────────────
    energy_delta_min: float = -0.1
    energy_delta_max: float = 0.3
    hunger_delta: float = -0.5
    vitality_delta_min: float = -0.05
    vitality_delta_max: float = 0.02
    chronic_stress_delta: float = 0.0
    fear_delta: float = 0.0
    joy_delta: float = 0.0

    # ── 효과 발현 지연 ──────────────────────────────────
    # 0 = 즉각, 1.0 = 한 주기 후 (수면 후 나타남)
    effect_delay: float = 0.0


# 권역별 자연 식재료 정의
WILD_FOODS: list[WildFood] = [
    # ── Claude (내륙 고원) ──────────────────────────────
    WildFood("pine_nut", "소나무 열매", "claude",
             apparent_name="솔방울 열매",         # 외형: 쉽게 구분
             identification_difficulty=0.1,
             discovery_prob=0.12,
             energy_delta_min=0.05, energy_delta_max=0.15,
             vitality_delta_min=0.0, vitality_delta_max=0.01,
             joy_delta=0.05),

    WildFood("mountain_herb", "산나물", "claude",
             apparent_name="녹색 잎채소",          # 외형: 비슷한 잡초와 혼동
             lookalike_id="toxic_herb",
             identification_difficulty=0.5,
             discovery_prob=0.10,
             energy_delta_min=0.02, energy_delta_max=0.12,
             chronic_stress_delta=-0.003,
             joy_delta=0.02),

    WildFood("toxic_herb", "독초(나물형)", "claude",  # 산나물과 비슷하게 생김
             apparent_name="녹색 잎채소",            # ← 같은 외형!
             lookalike_id="mountain_herb",
             identification_difficulty=0.7,
             discovery_prob=0.04,
             energy_delta_min=-0.25, energy_delta_max=-0.05,
             vitality_delta_min=-0.10, vitality_delta_max=-0.02,
             fear_delta=0.1, effect_delay=0.5),     # 효과가 늦게 나타남

    WildFood("toxic_mushroom", "독버섯", "claude",
             apparent_name="갈색 버섯",             # 외형: 식용버섯과 혼동
             lookalike_id="edible_mushroom",
             identification_difficulty=0.8,         # 매우 구별 어려움
             discovery_prob=0.04,
             energy_delta_min=-0.35, energy_delta_max=-0.15,
             vitality_delta_min=-0.20, vitality_delta_max=-0.08,
             fear_delta=0.25),

    WildFood("edible_mushroom", "식용버섯", "claude",
             apparent_name="갈색 버섯",             # ← 같은 외형!
             lookalike_id="toxic_mushroom",
             identification_difficulty=0.8,
             discovery_prob=0.06,
             energy_delta_min=0.08, energy_delta_max=0.20,
             vitality_delta_min=0.0, vitality_delta_max=0.02,
             joy_delta=0.08),

    # ── Codex (해안 평야) ──────────────────────────────
    WildFood("wild_grain", "야생 곡식", "codex",
             apparent_name="황금색 풀씨",
             identification_difficulty=0.2,
             discovery_prob=0.15,
             energy_delta_min=0.08, energy_delta_max=0.20,
             vitality_delta_min=0.0, vitality_delta_max=0.02,
             joy_delta=0.03),

    WildFood("shellfish", "조개류", "codex",
             apparent_name="해안 조개",
             identification_difficulty=0.3,         # 신선도가 문제
             discovery_prob=0.08,
             energy_delta_min=-0.05, energy_delta_max=0.25,
             vitality_delta_min=-0.08, vitality_delta_max=0.03),

    WildFood("poisonous_weed", "독초(풀형)", "codex",
             apparent_name="평범한 풀",
             lookalike_id="edible_weed",
             identification_difficulty=0.6,
             discovery_prob=0.05,
             energy_delta_min=-0.2, energy_delta_max=-0.05,
             vitality_delta_min=-0.10, vitality_delta_max=-0.02,
             fear_delta=0.15, effect_delay=0.3),

    WildFood("edible_weed", "식용 잡초", "codex",
             apparent_name="평범한 풀",             # ← 같은 외형!
             lookalike_id="poisonous_weed",
             identification_difficulty=0.6,
             discovery_prob=0.10,
             energy_delta_min=0.03, energy_delta_max=0.12,
             joy_delta=0.01),

    # ── Gemini (열대 군도) ──────────────────────────────
    WildFood("tropical_fruit", "열대 과일", "gemini",
             apparent_name="붉은 열매",
             identification_difficulty=0.2,
             discovery_prob=0.20,
             energy_delta_min=0.10, energy_delta_max=0.35,
             vitality_delta_min=0.0, vitality_delta_max=0.03,
             joy_delta=0.15),

    WildFood("medicinal_herb", "약초", "gemini",
             apparent_name="향기로운 잎",
             lookalike_id="bitter_leaf",
             identification_difficulty=0.4,
             discovery_prob=0.06,
             energy_delta_min=0.05, energy_delta_max=0.15,
             vitality_delta_min=0.01, vitality_delta_max=0.05,
             chronic_stress_delta=-0.008,
             joy_delta=0.05),

    WildFood("bitter_leaf", "쓴잎(무해)", "gemini",
             apparent_name="향기로운 잎",           # ← 같은 외형, 효과 애매
             lookalike_id="medicinal_herb",
             identification_difficulty=0.5,
             discovery_prob=0.08,
             energy_delta_min=-0.02, energy_delta_max=0.03,  # 거의 무효과
             joy_delta=-0.02),                               # 쓴맛 불쾌

    WildFood("poison_berry", "독열매", "gemini",
             apparent_name="붉은 열매",             # ← 열대과일과 같은 외형!
             lookalike_id="tropical_fruit",
             identification_difficulty=0.7,
             discovery_prob=0.04,
             energy_delta_min=-0.4, energy_delta_max=-0.15,
             vitality_delta_min=-0.25, vitality_delta_max=-0.08,
             fear_delta=0.3, effect_delay=0.2),
]

WILD_FOODS_BY_REGION: dict[str, list[WildFood]] = {}
for _wf in WILD_FOODS:
    WILD_FOODS_BY_REGION.setdefault(_wf.region, []).append(_wf)


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

    # 위치 상태 (Layer 1a 연결)
    current_facility: Optional[str] = None  # 현재 시설 type (None=야외)

    # 경제 상태 (Layer 6)
    employment_id: Optional[str] = None   # 현재 고용 계약 ID (None=자영)

    # 생애 이력 — SNN 학습의 원천
    birth_region: str = ""        # 태생 권역 (환경 노출의 근거)
    age_ticks: int = 0            # 살아온 틱 수 (경험 총량)

    # 적성 맵 (생성 시 1회 계산, compute_aptitude_map 사용)
    aptitude_map: dict = field(default_factory=dict)  # {skill_id: float 0.3~1.0}

    # ── 성격 5축 (Layer 3: Personality) ──────────────────────
    # 각 축: -1.0 ~ +1.0 (음수=왼쪽 극, 양수=오른쪽 극)
    # 내향(-1) ↔ 외향(+1)
    # 신중(-1) ↔ 대담(+1)
    # 이성(-1) ↔ 감성(+1)
    # 독립(-1) ↔ 협조(+1)
    # 관대(-1) ↔ 엄격(+1)
    personality: np.ndarray = field(
        default_factory=lambda: np.zeros(5, dtype=np.float32)
    )
    pos: tuple[int, int] = (0, 0)
    offset: tuple[float, float] = (0.0, 0.0)
    outfit_id: Optional[str] = None
    faction: Optional[str] = None
    faction_cooldown: int = 0


# ─── Layer 3: Inner World ─────────────────────────────────────

@dataclass
class InnerWorld:
    """페르소나의 내면 상태."""
    persona_id: str
    affiliation_scores: dict[str, float] = field(default_factory=dict)
    residence_ticks: dict[str, int] = field(default_factory=dict)

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

    # ─── 만성 상태 (Chronic State) ───────────────────────
    # 급성 감정(chiljeong)과 달리 매우 느리게 쌓이고 매우 느리게 사라진다.
    # 개구리 효과: 만성 스트레스 > 0.7이면 오히려 새 위협에 둔감해진다.
    chronic_stress: float = 0.0     # 0~1, 누적 고통/위협 (0.998/틱 자연 감쇠)
    chronic_comfort: float = 0.0    # 0~1, 누적 안락/충족 (회복력 원천)

    # ─── 습관화 (Habituation) ─────────────────────────────
    # 반복 자극에 대한 뇌의 적응. 같은 자극이 계속되면 반응이 줄어든다.
    # 몸(만성 스트레스)은 손상되지만 뇌(습관화)는 그걸 모른다 → 개구리 효과.
    #
    # 키: "cold", "heat", "hunger", "isolation", "danger"
    # 값: 0~1 (0=완전 민감, 1=완전 무감각)
    # 증가: 해당 자극에 지속 노출 시
    # 감소: 자극이 사라지면 천천히 역습관화
    habituation: dict = field(default_factory=lambda: {
        "cold": 0.0,
        "heat": 0.0,
        "hunger": 0.0,
        "isolation": 0.0,
        "danger": 0.0,
    })

    # ─── 생명력 + 망각 (Vitality + Mortality Forgetting) ────
    # vitality: 생명의 실질적 잔량. chronic_stress가 쌓이면 서서히 소모된다.
    #           0이 되면 사망.
    vitality: float = 1.0

    # mortality_awareness: 죽음에 대한 인식 (0=완전 망각, 1=생생한 인식)
    # 편안한 삶이 지속되면 죽음을 잊는다.
    # 위협이 오면 다시 깨닫지만, 망각 상태면 대응이 느려진다.
    mortality_awareness: float = 0.5

    # 생존 모드 활성화 여부
    survival_mode: bool = False

    # 감정 연속성: 수면 중 감쇠율 (성격 기반, init 시 계산)
    # 신중(-), 감성(+) → 감쇠 느림 (감정이 오래 남음)
    # 대담(+), 이성(-) → 감쇠 빠름 (빨리 털어냄)
    sleep_emotion_decay: float = 0.95   # 수면 중 감정 감쇠 (기본값, 성격으로 조정)

    # 행동 연속 카운터 (감정 트리거용)
    last_action: str = "idle"
    action_streak: int = 0
    idle_streak: int = 0

    # ─── 숙달 & 집중 ─────────────────────────────────────
    skill_profiles: dict = field(default_factory=dict)  # {skill_id: SkillProfile}
    concentration_cache: float = 0.0  # 마지막 계산된 집중도 (로깅용)

    # ─── 자기 인식 (적성 발견) ────────────────────────────
    # discovered_aptitudes: 경험으로 발견한 적성 {skill_id: perceived_aptitude}
    # aptitude_map(진짜 재능)과 다를 수 있음. 일해보거나 배워야 정확해짐.
    # 업데이트 경로: (1) 직접 work → joy/frustration 반응으로 추정
    #              (2) 숙련자에게 배움 → 체험 기회 → 추정
    discovered_aptitudes: dict = field(default_factory=dict)

    # ─── Nomos 위반 추적 (Phase 10) ─────────────────────
    nomos_violation_count: int = 0           # 누적 위반 횟수 (에스컬레이션 기준)
    nomos_blocked_until: int = 0             # 이 틱까지 work 행동 차단
    nomos_last_severity: str = ""            # 마지막 응징 등급
    nomos_last_violation_tick: int = 0       # 마지막 위반 발생 틱 (갱생 decay 기준)

    # ─── 승급 추적 (Phase 9) ────────────────────────────
    promotion_stable_ticks: int = 0          # 연속 안정 틱
    promotion_drive_history: list = field(default_factory=list)  # drive ring buffer (max 20)
    promotion_contrib_window: list = field(default_factory=list)  # 최근 500틱 기여 ring buffer
    dest: Optional[tuple[int, int]] = None
    migration_cooldown: int = 0
    effective_class: int = 1                 # 단계적 강등용 (persona_class와 분리)
    demotion_warning_ticks: int = 0          # 강등 경고 틱

    # ─── Phase 1: 에피소드 기억 ─────────────────────────
    episodes: list = field(default_factory=list)  # EpisodeTrace 리스트 (ring buffer, 최대 50개)
    episode_max: int = 50

    # ─── 기억 억압 시스템 ─────────────────────────────────
    # 억압된 기억은 episodes에 남지만 state="SUPPRESSED"
    # 극한 스트레스 시 재출현 (try_resurface)
    # 억압 기준: 부정적 salience 높은 + 두려움/분노 강한 기억
    suppression_threshold: float = 0.85  # 이 이상의 부정적 salience → 억압 후보

    # 캐시 (무의식 고속도로 — 상황→행동 매핑)
    habit_cache: dict = field(default_factory=dict)  # {context_hash: action}

    # ── 자연 식품 시스템 ────────────────────────────────
    # 인벤토리: 채집한 식재료 {food_id: count}
    foraged_foods: dict = field(default_factory=dict)
    # 지식: 먹어본 식재료 경험 {food_id: {"tries": n, "avg_delta": x, "is_good": bool}}
    food_knowledge: dict = field(default_factory=dict)

    # ── goods 인벤토리 (Phase 11) ────────────────────────
    inventory: dict = field(default_factory=lambda: {
        "food": 10, "material": 0, "tool": 0, "medicine": 0, "knowledge": 0,
    })
    equipped_tool_durability: Optional[int] = None  # 0~TOOL_MAX_DURABILITY, None=없음
    consecutive_hunger_ticks: int = 0                # 생존 소비 미스 연속 횟수
    # Phase 14-B: economic_state exposes grievance, tax_burden, trust_to_lord to SNN.
    grievance: float = 0.0
    grievance_lord_id: Optional[str] = None
    grievance_announced: bool = False
    strike_until_tick: int = 0
    exodus_cooldown_until_tick: int = 0

    CLUSTER_NAMES = ["V", "L", "S", "B", "A", "T", "C", "G", "F", "I", "D", "P"]
    CHILJEONG_NAMES = ["joy", "anger", "sadness", "fear", "love", "disgust", "desire"]
    OYOK_NAMES = ["hunger", "sleepiness", "lust", "greed", "honor"]

    def tone_dict(self) -> dict:
        return {name: float(val) for name, val in zip(self.CLUSTER_NAMES, self.tone)}

    def emotion_dict(self) -> dict:
        return {name: float(val) for name, val in zip(self.CHILJEONG_NAMES, self.chiljeong)}

    def add_episode(self, episode: 'EpisodeTrace'):
        """에피소드 기억 추가 (ring buffer).

        새 기억은 FRESH 상태로 들어온다.
        ring buffer 초과 시 EXTINCT/SUPPRESSED 우선 제거, 그 다음 salience 낮은 것.
        """
        self.episodes.append(episode)
        if len(self.episodes) > self.episode_max:
            # 제거 우선순위: EXTINCT > SUPPRESSED(약한) > 낮은 salience
            self.episodes.sort(
                key=lambda e: (
                    0 if e.state == "EXTINCT" else
                    1 if e.state == "SUPPRESSED" and e.suppression_strength < 0.3 else
                    2,
                    e.salience
                )
            )
            self.episodes = self.episodes[-self.episode_max:]  # 뒤쪽이 보존 대상

    def try_suppress_traumatic(self):
        """트라우마 기억 자동 억압.

        부정적 감정이 강한 기억(fear/anger/sadness가 높은)을 의식에서 밀어낸다.
        성격 영향: 감성적(+) → 억압 어려움, 이성적(-) → 억압 잘함.
        """
        for ep in self.episodes:
            if ep.state in ("SUPPRESSED", "EXTINCT"):
                continue
            # 부정적 감정 강도 (anger + sadness + fear + disgust)
            neg_intensity = float(
                ep.emotion_snapshot[1] + ep.emotion_snapshot[2]
                + ep.emotion_snapshot[3] + ep.emotion_snapshot[5]
            )
            # salience 높고 + 부정적 감정 강한 → 억압 후보
            if ep.salience > self.suppression_threshold and neg_intensity > 1.5:
                ep.suppress(strength=min(0.9, neg_intensity * 0.3))

    def try_resurface_memories(self):
        """극한 스트레스 시 억압된 기억 재출현 판정."""
        resurfaced = []
        for ep in self.episodes:
            if ep.try_resurface(self.chronic_stress, float(self.chiljeong[3])):
                resurfaced.append(ep)
        return resurfaced

    def get_recallable_episodes(self) -> list:
        """정상 인출 가능한 기억만 반환 (SUPPRESSED/EXTINCT 제외)."""
        return [ep for ep in self.episodes
                if ep.state not in ("SUPPRESSED", "EXTINCT")]

    def check_memory_extinction(self, current_tick: int):
        """LABILE 상태에서 재통합 없이 시간 지난 기억 소멸 판정."""
        for ep in self.episodes:
            ep.check_extinction(current_tick)

    def update_chronic(self, energy: float, weather_feels: float, has_social: bool,
                       personality: np.ndarray | None = None):
        """만성 상태 갱신. 매 틱 호출.

        - chronic_stress: 에너지 부족, 추위, 고립이 쌓임
        - chronic_comfort: 따뜻함, 배부름, 사교가 쌓임
        개구리 효과: chronic_stress가 극도로 높으면 새 위협에 둔감해짐
        """
        # 스트레스 원인
        stress_delta = 0.0
        if energy < 0.2:       stress_delta += 0.006  # 에너지 위기
        elif energy < 0.35:    stress_delta += 0.003
        if weather_feels < -5: stress_delta += 0.005  # 극한 추위
        elif weather_feels < 5: stress_delta += 0.002
        if float(self.oyok[0]) > 0.7: stress_delta += 0.003  # 극심한 배고픔
        if not has_social and self.action_streak > 50: stress_delta += 0.002  # 장기 고립

        # 안락 원인
        comfort_delta = 0.0
        if energy > 0.6:        comfort_delta += 0.003
        if 15 < weather_feels < 28: comfort_delta += 0.002  # 쾌적한 기후
        if has_social:          comfort_delta += 0.002
        if float(self.oyok[0]) < 0.3: comfort_delta += 0.002  # 충분히 먹음

        # 만성 안락이 회복력 제공 → 스트레스 증가 완화
        resilience = self.chronic_comfort * 0.4
        stress_delta = max(0, stress_delta - resilience * stress_delta)

        # 갱신 (매우 느린 감쇠)
        self.chronic_stress = min(1.0, self.chronic_stress * 0.998 + stress_delta)
        self.chronic_comfort = min(1.0, self.chronic_comfort * 0.998 + comfort_delta)

        # ── Vitality 감소 ─────────────────────────────────
        # 만성 스트레스가 누적되면 생명력이 서서히 소진된다.
        # 회복: 충분한 안락 + 낮은 스트레스 시 vitality 천천히 회복
        if self.chronic_stress > 0.6:
            vitality_drain = (self.chronic_stress - 0.6) * 0.002  # 더 빠르게
            self.vitality = max(0.0, self.vitality - vitality_drain)
        elif self.chronic_stress < 0.3 and self.chronic_comfort > 0.4:
            # 안정된 삶 → vitality 회복 (매우 느림)
            self.vitality = min(1.0, self.vitality + 0.00005)

        # ── 망각 (Mortality Forgetting) ────────────────────
        # 편안한 삶이 지속 → 죽음을 잊는다
        # 위협이 오면 → 다시 인식하지만, 망각 상태면 대응 지연
        fear = float(self.chiljeong[3])
        if self.chronic_comfort > 0.5 and self.chronic_stress < 0.3 and fear < 0.2:
            # 안락한 삶 → 망각 진행
            self.mortality_awareness = max(0.0, self.mortality_awareness - 0.0003)
        elif self.chronic_stress > 0.5 or fear > 0.5 or self.vitality < 0.5:
            # 위협 → 망각에서 깨어남 (망각 정도에 따라 속도 다름)
            awakening_speed = 0.005 * (1.0 - self.mortality_awareness * 0.5)
            self.mortality_awareness = min(1.0, self.mortality_awareness + awakening_speed)

        # ── 생존 모드 판정 ─────────────────────────────────
        # vitality 위험 OR (급성 공포 + 에너지 위기) → 생존 모드
        survival_threat = (
            self.vitality < 0.3
            or (fear > 0.7 and energy < 0.2)
            or (self.chronic_stress > 0.85 and energy < 0.3)
        )
        # 망각 상태면 생존 모드 진입이 지연됨
        if survival_threat:
            if self.mortality_awareness > 0.3:
                self.survival_mode = True
            # else: 위협이 있지만 망각 상태 → 모르고 있음
        else:
            self.survival_mode = False

        # ── 습관화 갱신 ──────────────────────────────────
        # 자극이 있으면 천천히 습관화, 없으면 천천히 역습관화
        # 습관화 속도는 성격(대담/이성)에 따라 다름 — 여기서는 기본값으로 통일
        h = self.habituation

        # 성격 기반 습관화 속도 조정
        # 신중(caution↑) + 감성(emotionality↑) → 느린 습관화 (항상 예민)
        # 대담(bold↑) + 이성(rational↑) → 빠른 습관화 (금방 적응)
        if personality is not None:
            caution      = max(0.0, -float(personality[1]))   # 신중도 (신중이면 양수)
            emotionality =  max(0.0, float(personality[2]))   # 감성도
            boldness     =  max(0.0, float(personality[1]))   # 대담도
            rationality  =  max(0.0, -float(personality[2]))  # 이성도
            hab_mult  = (1.0 - caution * 0.5) * (1.0 - emotionality * 0.3)
            hab_mult  = max(0.3, hab_mult)   # 최소 30% 속도 보장
            dehab_mult = (1.0 + boldness * 0.4) * (1.0 + rationality * 0.3)
        else:
            hab_mult  = 1.0
            dehab_mult = 1.0

        HAB_RATE   = 0.0008 * hab_mult    # 습관화: 성격별 속도
        DEHAB_RATE = 0.0004 * dehab_mult  # 역습관화: 대담/이성이면 더 빠르게 해제

        # 추위 습관화
        if weather_feels < 0:
            h["cold"] = min(1.0, h["cold"] + HAB_RATE * abs(weather_feels) / 20)
        else:
            h["cold"] = max(0.0, h["cold"] - DEHAB_RATE)

        # 더위 습관화
        if weather_feels > 35:
            h["heat"] = min(1.0, h["heat"] + HAB_RATE * (weather_feels - 35) / 15)
        else:
            h["heat"] = max(0.0, h["heat"] - DEHAB_RATE)

        # 배고픔 습관화
        hunger = float(self.oyok[0])
        if hunger > 0.6:
            h["hunger"] = min(1.0, h["hunger"] + HAB_RATE * hunger)
        else:
            h["hunger"] = max(0.0, h["hunger"] - DEHAB_RATE)

        # 고립 습관화
        if not has_social:
            h["isolation"] = min(1.0, h["isolation"] + HAB_RATE * 0.5)
        else:
            h["isolation"] = max(0.0, h["isolation"] - DEHAB_RATE * 2)  # 사교하면 고립감 빠르게 해소

        # 위험 습관화 (에너지 저하 반복)
        if energy < 0.25:
            h["danger"] = min(1.0, h["danger"] + HAB_RATE * 1.5)
        else:
            h["danger"] = max(0.0, h["danger"] - DEHAB_RATE)

    def update_emotion(self, action: str, energy: float, prev_energy: float):
        """행동과 상태 변화에 따른 감정 갱신.

        만성 상태가 급성 감정과 상호작용한다:
        - chronic_stress 높음 → 두려움/분노 증폭
        - chronic_stress 극도(>0.7) → 개구리 효과: 오히려 fear 둔화
        - chronic_comfort 높음 → 긍정 감정 회복력
        """
        decay = 0.9  # 감정 자연 감쇠 (매 틱 10% 회귀)

        # 만성 상태에 따른 감쇠 조정
        # 만성 스트레스가 높으면 기쁨이 더 빠르게 사라짐
        joy_decay = decay - self.chronic_stress * 0.05
        fear_decay = decay + self.chronic_comfort * 0.03  # 안락하면 두려움 빨리 사라짐
        self.chiljeong[0] *= max(0.8, joy_decay)   # joy
        self.chiljeong[3] *= max(0.85, fear_decay)  # fear
        self.chiljeong[1] *= decay  # anger
        self.chiljeong[2] *= decay  # sadness
        self.chiljeong[4] *= decay  # love
        self.chiljeong[5] *= decay  # disgust
        self.chiljeong[6] *= decay  # desire

        # 행동 연속 카운터 갱신
        if action == self.last_action:
            self.action_streak += 1
        else:
            self.action_streak = 1
            self.last_action = action
        self.idle_streak = self.action_streak if action == "idle" else 0

        # 식사 → 기쁨
        if action == "eat":
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.3)  # joy

        # 에너지 급락 → 두려움
        # 만성 스트레스 상호작용:
        #   0.3 미만: 정상 반응
        #   0.3~0.7: 증폭 (이미 지쳐서 더 겁남)
        #   0.7 초과: 둔화 (개구리 효과 — 이미 익숙해짐)
        if energy < 0.2:
            cs = self.chronic_stress
            if cs < 0.3:
                fear_boost = 0.2
            elif cs < 0.7:
                fear_boost = 0.2 * (1.0 + cs)   # 최대 0.34
            else:
                fear_boost = 0.2 * (1.0 - (cs - 0.7) * 1.5)  # 개구리: 점점 무감각
                fear_boost = max(0.05, fear_boost)  # 완전히 0이 되진 않음
            self.chiljeong[3] = min(1.0, self.chiljeong[3] + fear_boost)

        # 에너지 회복 → 기쁨
        if energy > prev_energy + 0.1:
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.1)  # joy

        # 배고픔 높으면 → 짜증(분노) + 갈망
        if self.oyok[0] > 0.7:
            self.chiljeong[1] = min(1.0, self.chiljeong[1] + 0.1)  # anger
            self.chiljeong[6] = min(1.0, self.chiljeong[6] + 0.2)  # desire

        # idle 연속 → 좌절(분노)
        if self.idle_streak >= 2:
            self.chiljeong[1] = min(1.0, self.chiljeong[1] + 0.1)  # anger (좌절)

        # 에너지 부족 → 짜증
        if energy < 0.3:
            self.chiljeong[1] = min(1.0, self.chiljeong[1] + 0.05)  # anger

        # 일한 후 → 성취욕(갈망)
        if action == "work":
            self.chiljeong[6] = min(1.0, self.chiljeong[6] + 0.05)  # desire (성취욕)

        # 탐험 → 기쁨 약간
        if action == "explore":
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.1)  # joy

        # 사교 → 사랑(유대) + 기쁨
        if action == "socialize":
            self.chiljeong[4] = min(1.0, self.chiljeong[4] + 0.15)  # love
            self.chiljeong[0] = min(1.0, self.chiljeong[0] + 0.1)   # joy

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

        # 사랑/유대 → B(Bonding/OXT)↑, S(Stability)↑
        self.tone[3] = np.float16(1.0 + float(self.chiljeong[4]) * 0.3)   # B
        self.tone[2] = np.float16(min(2.0, float(self.tone[2]) + float(self.chiljeong[4]) * 0.1))  # S

        # 갈망 → V↑, F(Fatigue) 약간↑
        self.tone[0] = np.float16(min(2.0, float(self.tone[0]) + float(self.chiljeong[6]) * 0.15))  # V
        self.tone[8] = np.float16(1.0 + float(self.chiljeong[6]) * 0.1)  # F

        # ── 집중 관련 클러스터 ──
        # C(Cognition/ACh): 기쁨+낮은 분노+낮은 두려움 → 인지 활성
        # "평온하고 기분 좋을 때 머리가 잘 돌아간다"
        joy = float(self.chiljeong[0])
        anger = float(self.chiljeong[1])
        fear = float(self.chiljeong[3])
        c_boost = joy * 0.3 - anger * 0.15 - fear * 0.2
        self.tone[6] = np.float16(max(0.5, min(2.0, 1.0 + c_boost)))  # C

        # T(Tension/CORT): 만성 스트레스 + 급성 분노/두려움
        t_stress = self.chronic_stress * 0.4 + anger * 0.2 + fear * 0.15
        self.tone[5] = np.float16(max(0.5, min(2.0, 1.0 + t_stress)))  # T

        # G(Growth/Glu): 에너지 충만 + 기쁨 → 성장 촉진
        self.tone[7] = np.float16(1.0 + max(0, self.energy_pool - 0.5) * 0.3 + joy * 0.1)  # G


# ─── L3d: Episode Trace (기억) ────────────────────────────────

@dataclass
class EpisodeTrace:
    """에피소드 기억 1건.

    기억 상태기계:
      FRESH → CONSOLIDATED (NREM 수면 중 안정화)
      CONSOLIDATED → LABILE (인출 시 불안정해짐)
      LABILE → RECONSOLIDATED (재수면 시 변형된 채로 재안정화)
      LABILE → EXTINCT (인출 후 보강 없으면 소멸)
      Any → SUPPRESSED (트라우마: 의식적 억압, 가역적)
      SUPPRESSED → LABILE (극한 스트레스 시 재출현)
    """
    tick: int
    action: str
    emotion_snapshot: np.ndarray  # chiljeong 복사본
    energy_at_time: float
    salience: float = 0.5        # 중요도 (감정 강도에 비례)
    recall_count: int = 0        # 인출 횟수

    # ── 기억 상태기계 ──────────────────────────────────────
    # FRESH: 방금 형성. 아직 수면 안정화 안 됨.
    # CONSOLIDATED: NREM 수면으로 안정화. 장기 보존.
    # LABILE: 인출됨. 현재 감정에 의해 변형 가능.
    # RECONSOLIDATED: 변형된 채로 재안정화. 원본과 다를 수 있음.
    # EXTINCT: 인출 후 보강 없이 소멸 경로. salience 급감.
    # SUPPRESSED: 의식적 억압. 정상 인출 불가. 극한 스트레스 시 재출현.
    state: str = "FRESH"

    # 인출 시각 (LABILE 전환 시점). 재통합 타이밍 판정용.
    last_recalled_tick: int = 0

    # 억압 강도 (SUPPRESSED 상태에서만 사용). 0~1, 높을수록 재출현 어려움.
    suppression_strength: float = 0.0

    # 원본 감정 (재통합으로 변형되기 전 최초 감정)
    _original_emotion: Optional[np.ndarray] = field(default=None, repr=False)

    def compute_salience(self, emotion: np.ndarray) -> float:
        """감정 강도로 salience 계산."""
        self.salience = float(np.abs(emotion).max()) * 0.7 + 0.3
        return self.salience

    def recall(self, current_tick: int, current_emotion: np.ndarray) -> None:
        """기억 인출: CONSOLIDATED/RECONSOLIDATED → LABILE.

        인출 시 기억은 불안정해지며, 현재 감정에 의해 변형될 수 있다.
        "기억은 매번 다시 쓰인다" — Karim Nader (2000).

        FRESH: 아직 안정화 안 됨 → 인출 가능하지만 LABILE 전환 없음 (단기 기억)
        SUPPRESSED: 정상 인출 불가
        EXTINCT: 이미 소멸 경로 → 인출 불가
        """
        if self.state in ("SUPPRESSED", "EXTINCT"):
            return  # 억압/소멸 기억은 정상 인출 불가
        if self.state == "FRESH":
            # FRESH는 아직 단기 기억 → recall_count만 증가, 상태 전환 없음
            self.recall_count += 1
            return

        if self._original_emotion is None:
            self._original_emotion = self.emotion_snapshot.copy()

        self.state = "LABILE"
        self.last_recalled_tick = current_tick
        self.recall_count += 1

        # ── 기억 재통합: 현재 감정이 과거 기억을 오염시킨다 ──
        # 비율: 원본 80% + 현재 감정 20% (인출할 때마다 조금씩 변형)
        blend = min(0.3, 0.1 + self.recall_count * 0.03)  # 횟수↑ → 변형↑ (최대 30%)
        self.emotion_snapshot = (
            self.emotion_snapshot * (1 - blend) + current_emotion * blend
        ).astype(np.float16)

    def consolidate(self) -> None:
        """NREM 수면 중 안정화."""
        if self.state == "FRESH":
            self.state = "CONSOLIDATED"
        elif self.state == "LABILE":
            self.state = "RECONSOLIDATED"
            # 재통합 시 salience 약간 변동 (기억이 달라졌으므로)
            # tick 기반 시드로 재현 가능성 확보
            rng = np.random.default_rng(self.tick + self.recall_count)
            self.salience *= 0.95 + rng.random() * 0.1

    def suppress(self, strength: float = 0.7) -> None:
        """의도적 억압. 트라우마 기억을 의식에서 밀어낸다."""
        if self.state == "SUPPRESSED":
            self.suppression_strength = min(1.0, self.suppression_strength + 0.1)
        else:
            self.state = "SUPPRESSED"
            self.suppression_strength = strength

    def try_resurface(self, chronic_stress: float, fear: float) -> bool:
        """극한 스트레스 시 억압된 기억이 재출현하는지 판정.

        Returns: True면 재출현 (SUPPRESSED → LABILE)
        """
        if self.state != "SUPPRESSED":
            return False

        # 재출현 확률: 스트레스와 공포가 억압 강도를 넘어야
        resurface_pressure = chronic_stress * 0.6 + fear * 0.4
        threshold = self.suppression_strength * 0.8
        if resurface_pressure > threshold:
            self.state = "LABILE"
            self.suppression_strength *= 0.5  # 재출현 후 억압력 약화
            return True
        return False

    def check_extinction(self, current_tick: int) -> bool:
        """LABILE 상태에서 재통합 없이 시간이 지나면 EXTINCT.

        Returns: True면 소멸 경로 진입
        """
        if self.state != "LABILE":
            return False
        # LABILE 후 72틱(3일) 동안 수면(재통합) 없으면 → EXTINCT
        if current_tick - self.last_recalled_tick > 72:
            self.state = "EXTINCT"
            self.salience *= 0.3  # salience 급감
            return True
        return False


# ─── L5: Social (관계/비밀/소문) ─────────────────────────────

@dataclass
class Relationship:
    """두 페르소나 간 관계."""
    persona_a: str
    persona_b: str
    familiarity: float = 0.0   # 0~1 (모르는 사이 → 절친)
    trust: float = 0.5         # 0~1 (불신 → 신뢰)
    last_interaction_tick: int = 0
    interaction_count: int = 0

    def key(self) -> tuple:
        return tuple(sorted([self.persona_a, self.persona_b]))


@dataclass
class Secret:
    """비밀 1건. 비밀 = 알려지면 감당할 수 없는 결과가 오는 정보."""
    owner_id: str
    content_tag: str           # "weakness", "ambition", "past", "skill" 등
    salience: float = 0.5      # 중요도
    known_by: set = field(default_factory=set)  # 아는 사람 ID 집합
    revealed_tick: Optional[int] = None


@dataclass
class KnowledgeRecord:
    """기록된 지식. 소문보다 신뢰도 높고 영구 보존된다.

    누군가 food_knowledge certainty >= 0.8인 식물에 대해 작성.
    Academy/Library 시설에 보관 → 방문한 페르소나가 열람 가능.
    직접 경험의 70~90% 수준의 certainty를 제공.
    """
    id: str
    author_id: str
    topic: str           # "food", "medicine", "territory", "history" 등
    subject_id: str      # 대상 (food_id, territory_id 등)
    content: str         # 내용 요약
    reliability: float   # 저자의 확신도 기반 (0~1)
    created_tick: int = 0
    territory_id: str = ""   # 어느 영지 아카데미/도서관에 보관


@dataclass
class Rumor:
    """소문 1건. 비밀에서 파생되거나 관찰에서 추론된 정보."""
    source_secret_owner: Optional[str] = None  # 원본 비밀 주인 (없으면 관찰 추론)
    content_tag: str = ""                       # "weakness", "ambition" 등
    accuracy: float = 1.0                       # 1.0=원본, 전파마다 감쇠
    spread_count: int = 0                       # 전파 횟수
    origin_tick: int = 0                        # 최초 발생 틱
    known_by: set = field(default_factory=set)   # 들은 사람 ID 집합
    about_id: str = ""                          # 소문 대상 페르소나

    def distort(self) -> float:
        """전화기 효과: 전파 시 정확도 감쇠. 반환값 = 새 정확도."""
        self.spread_count += 1
        # 1차: 0.85, 2차: 0.72, 3차: 0.61 ...
        self.accuracy *= 0.85
        return self.accuracy


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
