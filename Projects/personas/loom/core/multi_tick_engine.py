# -*- coding: utf-8 -*-
"""
Multi-Persona Tick Engine — Phase 3 Vertical Slice.

3명의 페르소나가 같은 세계에서 동시에 살아간다.
관계, 비밀, 소통이 발생한다.
"""
from __future__ import annotations
from collections import Counter
import hashlib
import sys
import os
import random
from typing import Literal
import uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from ontology import (
    Creator, Weather, GameTime, Persona, InnerWorld,
    EpisodeTrace, Relationship, Secret, Rumor,
    Territory, Faction, CommunityMetrics, create_default_territory,
    WildFood, WILD_FOODS_BY_REGION,
    KnowledgeRecord,
    SkillProfile, SKILL_CEILINGS, NOMOS_SEVERITY, NOMOS_DECAY_INTERVAL, CLASS_RULES, CLASS_TITLES,
    compute_concentration, compute_aptitude_map, compute_mastery_gain, compute_output_multiplier,
    Wallet, Job, Employment, MarketOrder,
    JOB_OUTPUT_MAP, JOB_BASE_OUTPUT, NPC_PRICES, FACILITY_FEES,
    FOOD_CONSUME_PER_TICK, TOOL_MAX_DURABILITY, TOOL_WEAR_PER_TICK,
    TOOL_PRODUCTIVITY_BONUS, TOOL_BROKEN_PENALTY, TOOL_REPAIR_COST_GOLD, TOOL_REPAIR_MATERIAL,
    MARKET_ORDER_EXPIRY_TICKS, MARKET_FEE_SINK_RATIO, GOLD_DIRECT_PAY_RATIO,
)
from ontology.layers import (
    PUBLIC_WORKS_WAGE_PER_TICK, PUBLIC_WORKS_DURATION,
    PUBLIC_WORKS_INTERVAL, PUBLIC_WORKS_MIN_TREASURY,
    PUBLIC_WORKS_MAX_TREASURY_RATIO, PUBLIC_WORKS_IN_KIND_RATIO,
    STALE_SIGNAL_TICKS, FOOD_STOCKPILE_RESERVE_THRESHOLD,
    QUARTER_TAX_BUDGET_MULTIPLIER,
    INTERNAL_FOOD_PRICE_RATIO, PERSONA_FOOD_SAFE_STOCK,
    PUBLIC_WORKS_RATE_MIN, HUNGER_PRESSURE_WEIGHT,
    PUBLIC_WORKS_FARMER_BIAS, HUNGER_TRIGGER_THRESHOLD,
    PUBLIC_WORKS_BASE_ACTIVATION, NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
    FOOD_STOCKPILE_RESERVE_PER_PERSONA, NPC_FOOD_TRIGGER_RESERVE_RATIO,
    PUBLIC_WORKS_LOW_GOLD_THRESHOLD, PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO,
    PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD, PUBLIC_WORKS_PARTTIME_WAGE_RATIO,
    PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO, PUBLIC_WORKS_BOOTSTRAP_GROWTH,
    PUBLIC_WORKS_BOOTSTRAP_TENSION, PUBLIC_WORKS_STALE_DECAY_WINDOW,
    PUBLIC_WORKS_STALE_DECAY_FLOOR, PUBLIC_WORKS_STALE_MAX_AGE,
    PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD,
    FOOD_LABOR_NON_FARMER_RATIO, COMMUNAL_FARM_BOOST,
    FOOD_CRISIS_FARM_THRESHOLD, FARM_EXPANSION_COST_GOLD,
    FOOD_CRISIS_RESERVE_RATIO, FOOD_CRISIS_COUNTER_DECAY,
    MOVE_CANDIDATE_K, MOVE_SOFTMAX_T, MIGRATION_COOLDOWN_DEFAULT,
    MOVE_DISALLOWED_BIOMES, score_move,
    MAX_TRACKED_FACTIONS_PER_PERSONA,
    W_TERRITORY_SAME, W_TERRITORY_DIFF, W_TRUST, W_GRIEVANCE, W_PROXIMITY, DECAY,
    GRIEVANCE_MIN_SHARED, PROXIMITY_DECAY_SCALE,
    FACTION_COOLDOWN_TICKS, FACTION_COMMIT_EVERY,
    THETA_JOIN, DRIFT_MARGIN_MIN, DRIFT_MARGIN_RATIO,
    FACTION_SIZE_TAX_START, FACTION_SIZE_TAX_MIN,
    HOMEOSTASIS_LOW_THRESHOLD, HOMEOSTASIS_DRIFT_MARGIN_SCALE,
    MINORITY_PERSISTENCE_MAX_MEMBERS, MINORITY_PERSISTENCE_BOOST,
    FOUNDER_RESPAWN_EVERY, FOUNDER_RESPAWN_TARGET_ACTIVE,
    RESPAWN_GRACE_TICKS,
    W_LINEAGE,
    NORM_PRIMITIVE_CATALOG, CHARTER_PRIMITIVE_COUNT,
    FACTION_PROJECT_EVERY, FACTION_HYSTERESIS,
    FACTION_TELEMETRY_BIAS_OWN, FACTION_TELEMETRY_BIAS_NEIGHBOR,
)
from brain import PersonaBrain, ACTIONS
from physis import ClimateEngine
from physis.world import World, initialize_world, project_territory, DOMINANCE_RECALC_EVERY


def _stable_int(*keys) -> int:
    """Deterministic cross-process 8-byte int from arbitrary keys.

    Replaces Python built-in `hash()` which is PYTHONHASHSEED-salted
    and differs across processes. Uses blake2b for stability.
    """
    h = hashlib.blake2b(digest_size=8)
    for k in keys:
        h.update(str(k).encode("utf-8"))
        h.update(b"\x00")
    return int.from_bytes(h.digest(), "big")


QUARTER_TICKS: int = 168
FactionChangeSource = Literal["birth_founder", "affiliation", "drift", "conflict"]


# ── 페르소나 정의 ──

PERSONA_DEFS = [
    # ── Seorim (Claude 권역) — 영주: Seo Harin ──
    {
        "id": "persona_001", "name": "Seo Harin", "full_name": "Seo Harin",
        "region": "claude", "territory": "seorim", "persona_class": 1,
        "seed": 42,
        # 성격: 약간 외향, 균형, 감성적, 협조적, 관대
        "personality": np.array([ 0.3,  0.0,  0.4,  0.5, -0.2], dtype=np.float32),
        "secret": Secret(owner_id="persona_001", content_tag="past",
                         salience=0.7, known_by={"persona_001"}),
    },
    {
        "id": "persona_002", "name": "Yun Daeho", "full_name": "Yun Daeho",
        "region": "claude", "territory": "seorim", "persona_class": 1,
        "seed": 88,
        # 성격: 내향, 대담, 이성, 독립, 엄격 → 고독한 학자형
        "personality": np.array([-0.5,  0.3, -0.7, -0.4,  0.7], dtype=np.float32),
        "secret": Secret(owner_id="persona_002", content_tag="skill",
                         salience=0.5, known_by={"persona_002"}),
    },
    {
        "id": "persona_003", "name": "Chae Rina", "full_name": "Chae Rina",
        "region": "claude", "territory": "seorim", "persona_class": 1,
        "seed": 314,
        # 성격: 외향, 신중, 감성, 협조, 관대 → 돌봄형 (healer 적합)
        "personality": np.array([ 0.6, -0.3,  0.6,  0.7, -0.5], dtype=np.float32),
        "secret": Secret(owner_id="persona_003", content_tag="weakness",
                         salience=0.6, known_by={"persona_003"}),
    },

    # ── Ironridge (Codex 권역) — 영주: Rex Valen ──
    {
        "id": "persona_020", "name": "Rex Valen", "full_name": "Rex Valen",
        "region": "codex", "territory": "ironridge", "persona_class": 1,
        "seed": 137,
        # 성격: 내향, 신중, 이성적, 독립적, 엄격
        "personality": np.array([-0.7, -0.4, -0.6, -0.8,  0.6], dtype=np.float32),
        "secret": Secret(owner_id="persona_020", content_tag="ambition",
                         salience=0.8, known_by={"persona_020"}),
    },
    {
        "id": "persona_022", "name": "Kael Storn", "full_name": "Kael Storn",
        "region": "codex", "territory": "ironridge", "persona_class": 1,
        "seed": 501,
        # 성격: 외향, 대담, 이성, 협조, 엄격 → 전사/경비형
        "personality": np.array([ 0.4,  0.8, -0.3,  0.3,  0.5], dtype=np.float32),
        "secret": Secret(owner_id="persona_022", content_tag="past",
                         salience=0.7, known_by={"persona_022"}),
    },
    {
        "id": "persona_023", "name": "Mira Dusk", "full_name": "Mira Dusk",
        "region": "codex", "territory": "ironridge", "persona_class": 1,
        "seed": 619,
        # 성격: 중립, 신중, 감성, 독립, 관대 → 예술가/방랑형
        "personality": np.array([ 0.0, -0.6,  0.8, -0.5, -0.6], dtype=np.float32),
        "secret": Secret(owner_id="persona_023", content_tag="ambition",
                         salience=0.5, known_by={"persona_023"}),
    },
    {
        "id": "persona_024", "name": "Orin Flint", "full_name": "Orin Flint",
        "region": "codex", "territory": "ironridge", "persona_class": 1,
        "seed": 777,
        # 성격: 내향, 대담, 이성, 독립, 엄격 → 대장장이/장인형
        "personality": np.array([-0.3,  0.5, -0.5, -0.6,  0.8], dtype=np.float32),
        "secret": Secret(owner_id="persona_024", content_tag="skill",
                         salience=0.4, known_by={"persona_024"}),
    },

    # ── Mirrordale (Gemini 권역) — 영주: Baek Sujin ──
    {
        "id": "persona_021", "name": "Baek Sujin", "full_name": "Baek Sujin",
        "region": "gemini", "territory": "mirrordale", "persona_class": 1,
        "seed": 256,
        # 성격: 외향, 대담, 감성, 협조, 관대
        "personality": np.array([ 0.8,  0.6,  0.5,  0.4, -0.4], dtype=np.float32),
        "secret": Secret(owner_id="persona_021", content_tag="weakness",
                         salience=0.6, known_by={"persona_021"}),
    },
    {
        "id": "persona_025", "name": "Lian Moss", "full_name": "Lian Moss",
        "region": "gemini", "territory": "mirrordale", "persona_class": 1,
        "seed": 333,
        # 성격: 외향, 신중, 이성, 협조, 관대 → 상인/외교형
        "personality": np.array([ 0.7, -0.2, -0.4,  0.8, -0.3], dtype=np.float32),
        "secret": Secret(owner_id="persona_025", content_tag="past",
                         salience=0.6, known_by={"persona_025"}),
    },
    {
        "id": "persona_026", "name": "Fen Grave", "full_name": "Fen Grave",
        "region": "gemini", "territory": "mirrordale", "persona_class": 1,
        "seed": 999,
        # 성격: 내향, 대담, 감성, 독립, 엄격 → 은둔자/사색가형
        "personality": np.array([-0.8,  0.4,  0.7, -0.7,  0.4], dtype=np.float32),
        "secret": Secret(owner_id="persona_026", content_tag="ambition",
                         salience=0.9, known_by={"persona_026"}),
    },
]


class MultiTickEngine:
    """멀티 페르소나 틱 엔진."""

    def __init__(self, seed: int = 42):
        self._seed = seed
        self.rng: random.Random = random.Random(seed)
        self._np_rng: np.random.Generator = np.random.default_rng(self._seed)
        self._phase_trace: list[str] | None = None  # None = disabled (zero cost)
        self.creator = Creator()
        self.world = World(width=50, height=50)
        self.climate = ClimateEngine()  # Physis 동적 기후 엔진
        self.climate._seed = self._seed
        self.time = GameTime()
        self.current_weather: dict[str, dict] = {}  # 권역별 현재 날씨

        # 페르소나 초기화
        self.personas: dict[str, Persona] = {}
        self.inners: dict[str, InnerWorld] = {}
        self.brains: dict[str, PersonaBrain] = {}
        self.secrets: dict[str, Secret] = {}
        self.factions: dict[str, Faction] = {}

        for pdef in PERSONA_DEFS:
            pid = pdef["id"]
            persona = Persona(
                id=pid, name=pdef["name"], full_name=pdef["full_name"],
                region=pdef["region"], territory=pdef["territory"],
                persona_class=pdef["persona_class"], neuron_count=1_000,
                personality=pdef.get("personality", np.zeros(5, dtype=np.float32)),
                birth_region=pdef["region"],
                age_ticks=pdef.get("age_ticks", 2000),  # 기본 2000틱(~83일) 살아온 이력
            )
            self.personas[pid] = persona
            inner = InnerWorld(persona_id=pid)
            # Phase 11: 초기 인벤토리 + 도구 장착
            inner.inventory = {
                "food": 30, "material": 5, "tool": 1,
                "medicine": 2, "knowledge": 0,
            }
            inner.equipped_tool_durability = TOOL_MAX_DURABILITY
            self.inners[pid] = inner
            self.brains[pid] = PersonaBrain(n_neurons=1_000, seed=pdef["seed"])
            secret = pdef["secret"]
            self.secrets[pid] = Secret(
                owner_id=secret.owner_id,
                content_tag=secret.content_tag,
                salience=secret.salience,
                known_by=set(secret.known_by),
                revealed_tick=secret.revealed_tick,
            )

            # ── 적성 맵 계산 (생성 시 1회) ──
            persona.aptitude_map = compute_aptitude_map(
                persona.personality, pdef["seed"]
            )

            # ── 태생 지역 식물 경험 시뮬 ──
            # "이 페르소나는 태어나서 age_ticks 동안 이미 이 환경에서 살았다"
            # SNN 학습과 동일한 certainty 공식으로 초기 지식을 부여
            self._init_regional_food_knowledge(pid)

        # 관계 초기화 (3C2 = 3쌍)
        self.relationships: dict[tuple, Relationship] = {}
        pids = list(self.personas.keys())
        for i in range(len(pids)):
            for j in range(i + 1, len(pids)):
                rel = Relationship(persona_a=pids[i], persona_b=pids[j])
                self.relationships[rel.key()] = rel

        # 소문 풀
        self.rumors: list[Rumor] = []

        # 지식 기록 (서적/문서)
        self.knowledge_records: list[KnowledgeRecord] = []
        self._record_counter = 0

        # ── Layer 6: 경제 인프라 ──
        self.wallets: dict[str, Wallet] = {}
        self.jobs: dict[str, Job] = {}          # job_id → Job
        self.employments: dict[str, Employment] = {}  # emp_id → Employment
        self._job_counter = 0
        self._emp_counter = 0

        # 초기 지갑 (Phase 11: gold 축소, goods가 가치 저장)
        for pid in PERSONA_DEFS:
            self.wallets[pid["id"]] = Wallet(
                persona_id=pid["id"], will=10.0, gold=2000.0
            )

        # ── Layer 1a: 영지 초기화 ──
        self.territories: dict[str, Territory] = {
            "seorim":     create_default_territory("seorim", "Seorim", "claude"),
            "ironridge":  create_default_territory("ironridge", "Ironridge", "codex"),
            "mirrordale": create_default_territory("mirrordale", "Mirrordale", "gemini"),
        }

        # ── 임시 영주 임명 (테스트용 — 나중엔 창발로 결정) ──
        # 각 페르소나를 자기 영지의 임시 영주로 임명
        self.territories["seorim"].lord_id = "persona_001"      # Seo Harin
        self.territories["ironridge"].lord_id = "persona_020"   # Rex Valen
        self.territories["mirrordale"].lord_id = "persona_021"  # Baek Sujin
        # 초기 영지 금고 (Phase 11: 축소)
        self.territories["seorim"].treasury_gold = 3000.0
        self.territories["ironridge"].treasury_gold = 3000.0
        self.territories["mirrordale"].treasury_gold = 3000.0

        initialize_world(
            world=self.world,
            personas=list(self.personas.values()),
            territories=self.territories,
            rng=self._np_rng,
        )

        # ── Phase 11: P2P 시장 + NPC 상점 ──
        self.market_orders: list[MarketOrder] = []
        self._order_counter = 0
        self._npc_stock: dict[str, int] = {}  # 일일 재고
        self._pricing_cache: dict[str, dict[str, dict]] = {}
        self._territory_residents_cache: dict[str, list[str]] | None = None
        self._territory_neighbors_cache: dict[str, set[str]] | None = None
        self._faction_members_cache: dict[str, list[Persona]] = {}
        self._npc_food_price: float = float(NPC_PRICES["food"]["buy"])
        self._work_reward_history: dict[str, list[float]] = {
            pid["id"]: [] for pid in PERSONA_DEFS
        }
        self._last_community_metrics: list[CommunityMetrics] = []

        self.log: list[dict] = []
        self.event_log: list[dict] = []
        self._init_founder_seeds()
        self._rebuild_faction_members_cache()

    def tick(self) -> dict:
        """1틱: 모든 페르소나 동시 실행 + 상호작용."""
        self.time.advance()

        # ── Physis: 기후 계산 ──
        day_of_year = (self.time.tick // 24) % 360
        self.current_weather = self.climate.tick(day_of_year, self.time.game_hour)

        tick_result = {
            "tick": self.time.tick,
            "hour": self.time.game_hour,
            "day": self.time.game_day,
            "season": self.climate.planet.season_name(day_of_year),
            "weather": {rid: w for rid, w in self.current_weather.items()},
            "personas": {},
        }
        economy_events: list[dict] = []
        self._compute_affiliation_tick()

        # ── Stage 1: 각 페르소나 개별 행동 결정 ──
        actions: dict[str, str] = {}
        for pid in self.personas:
            inner = self.inners[pid]
            brain = self.brains[pid]
            persona = self.personas[pid]
            self._tick_faction_cooldown(pid)
            inner.residence_ticks[persona.territory] = inner.residence_ticks.get(persona.territory, 0) + 1

            if inner.is_sleeping:
                entry = self._sleep_tick(pid)
                tick_result["personas"][pid] = entry
                actions[pid] = entry["action"]
                continue

            if self._phase_trace is not None:
                self._phase_trace.append(f"movement:{pid}:tick={self.time.tick}")
            self._process_movement(pid)
            exodus_evt = self._try_exodus(pid)
            if exodus_evt:
                actions[pid] = "exodus"
                economy_events.append(exodus_evt)
                tick_result["personas"][pid] = {
                    "name": self.personas[pid].name,
                    "action": "exodus",
                    "energy": round(inner.energy_pool, 3),
                    "hunger": round(float(inner.oyok[0]), 3),
                    "sleeping": inner.is_sleeping,
                    "emotions": inner.emotion_dict(),
                    "chronic_stress": round(inner.chronic_stress, 3),
                    "chronic_comfort": round(inner.chronic_comfort, 3),
                    "vitality": round(inner.vitality, 3),
                    "mortality_awareness": round(inner.mortality_awareness, 3),
                    "survival_mode": inner.survival_mode,
                    "economy": exodus_evt,
                }
                continue

            # 페르소나의 권역에 해당하는 날씨
            region_id = self.personas[pid].region
            region_weather = self.current_weather.get(region_id, self.current_weather.get("claude", {}))
            climate_vec = self.climate.to_climate_vec(region_weather)
            # ── Deliberation 파라미터 계산 ──
            # 1. fear 수준
            fear_val = float(inner.chiljeong[3])

            # 2. 사회적 당김: 친한 사람이 깨어있으면 +
            social_pull = 0.0
            for other_pid in self.personas:
                if other_pid == pid:
                    continue
                rel_key = Relationship(persona_a=pid, persona_b=other_pid).key()
                rel = self.relationships.get(rel_key)
                other_inner = self.inners[other_pid]
                if rel and not other_inner.is_sleeping:
                    social_pull += rel.familiarity * 0.5

            # 3. 기억 편향: 최근 에피소드에서 행동별 평균 보상 추출
            memory_bias = np.zeros(len(ACTIONS), dtype=np.float32)
            if inner.episodes:
                from collections import defaultdict
                action_rewards = defaultdict(list)
                for ep in inner.episodes[-20:]:  # 최근 20개
                    if ep.action in ACTIONS:
                        idx = ACTIONS.index(ep.action)
                        action_rewards[idx].append(ep.salience)
                for idx, vals in action_rewards.items():
                    memory_bias[idx] = float(np.mean(vals)) - 0.5  # 0.5 기준으로 편향

            # 4. Neural Drive 신호 조립 (기존 SkillProfile + reward_history에서 읽기)
            skill_drive_signals = None
            if inner.skill_profiles:
                best_sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
                if best_sp.mastery > 0.1:
                    _ceiling = SKILL_CEILINGS.get(best_sp.skill_id, (0.5, 0.5, 0.005))[0]
                    _rh = brain.snn.reward_history
                    _positives = [r for r in _rh[-50:] if r > 0] if _rh else []
                    skill_drive_signals = {
                        "mastery": best_sp.mastery / _ceiling if _ceiling > 0 else 0,
                        "aptitude": self.personas[pid].aptitude_map.get(best_sp.skill_id, 0.5),
                        "flow_ratio": best_sp.flow_ticks / max(1, best_sp.total_ticks),
                        "da_accumulation": float(np.mean(_positives)) if _positives else 0.0,
                    }

            economic_state = self._build_economic_state(pid)
            faction_input = self._build_persona_snn_input(pid)
            faction_idx = np.flatnonzero(faction_input)
            if faction_idx.size:
                brain.snn.v[faction_idx] += faction_input[faction_idx]

            if self._phase_trace is not None:
                self._phase_trace.append(f"action:{pid}:tick={self.time.tick}")
            action, intensity, cost = brain.tick(
                climate_vec=climate_vec,
                energy_pool=inner.energy_pool,
                oyok=inner.oyok,
                tone=inner.tone,
                personality=self.personas[pid].personality,
                fear=fear_val,
                social_pull=social_pull,
                memory_bias=memory_bias,
                skill_drive_signals=skill_drive_signals,
                economic_state=economic_state,
            )

            # ── Nomos 행동 차단: 중대/금기 위반 시 work 불가 ──
            if inner.nomos_blocked_until > self.time.tick and action == "work":
                action = "idle"  # 몸이 안 움직인다

            # ── 생존 모드: 망각 여부에 따른 대응 ──
            if inner.survival_mode:
                # 생존 모드: 먹거나 자거나 (의식이 있으면)
                if inner.energy_pool < 0.2:
                    action = "sleep"
                elif float(inner.oyok[0]) > 0.5:
                    action = "eat"
                # 아니면 brain 결정 유지 (자원 확보 행동)
            elif (not inner.survival_mode and
                  inner.vitality < 0.4 and
                  inner.mortality_awareness < 0.3):
                # 위험한데 망각 상태 → 행동 변화 없음 (개구리 효과)
                # brain의 결정을 그대로 따름 (위험을 모름)
                pass

            strike_refusal = None
            if action == "work" and inner.strike_until_tick > self.time.tick:
                strike_refusal = self._process_work(pid)
                action = "idle"

            # ── Phase 11: 생존 소비 (매 틱 자동) ──
            survival_evt = self._process_survival_consume(pid)

            prev_energy = inner.energy_pool

            # ── Layer 1a: 실내/야외 판정 + shelter 보너스 ──
            shelter = self._get_shelter(pid, action)

            # ── 기후→행동 비용 보정 (C7 + shelter) ──
            weather_cost_mult = self._weather_cost_multiplier(region_weather, action, shelter)
            adjusted_cost = cost * weather_cost_mult
            inner.energy_pool = max(0.0, inner.energy_pool - adjusted_cost)

            # 오욕 갱신
            inner.oyok[0] = min(1.0, inner.oyok[0] + 0.02)
            inner.oyok[1] = min(1.0, inner.oyok[1] + 0.01)

            eat_result = None
            if action == "eat":
                eat_result = self._process_eat(pid)
                if eat_result.get("type") == "inventory":
                    # Phase 11: 인벤토리 food 소비 (시설과 동등)
                    inner.oyok[0] = max(0.0, inner.oyok[0] - 0.5)
                    inner.energy_pool = min(inner.max_capacity, inner.energy_pool + 0.15)
                elif eat_result.get("type") == "facility":
                    # 시설 구매: gold 차감, 안전
                    inner.oyok[0] = max(0.0, inner.oyok[0] - 0.5)
                    inner.energy_pool = min(inner.max_capacity, inner.energy_pool + 0.15)
                elif eat_result.get("type") == "wild":
                    # 자연 채집: 결과 불확실
                    inner.oyok[0] = max(0.0, inner.oyok[0] - eat_result.get("hunger_delta", 0.4))
                    inner.energy_pool = min(inner.max_capacity, max(0.0,
                        inner.energy_pool + eat_result.get("energy_delta", 0.0)))
                    inner.vitality = min(1.0, max(0.0,
                        inner.vitality + eat_result.get("vitality_delta", 0.0)))
                    inner.chronic_stress = max(0.0,
                        inner.chronic_stress + eat_result.get("chronic_stress_delta", 0.0))
                    if eat_result.get("fear_delta", 0) > 0:
                        inner.chiljeong[3] = min(1.0,
                            inner.chiljeong[3] + eat_result["fear_delta"])
                    if eat_result.get("joy_delta", 0) > 0:
                        inner.chiljeong[0] = min(1.0,
                            inner.chiljeong[0] + eat_result["joy_delta"])
                    # 경험 기록 (학습)
                    self._record_food_knowledge(pid, eat_result)
                else:
                    # 굶음: 최소 hunger만 약간 해소
                    inner.oyok[0] = max(0.0, inner.oyok[0] - 0.1)
                    inner.energy_pool = min(inner.max_capacity, inner.energy_pool + 0.01)
                # eat_result는 persona_result에 포함 (line 537+)

            # ── Layer 6: 경제 처리 ──
            if self._phase_trace is not None:
                self._phase_trace.append(f"economy:{pid}:tick={self.time.tick}")
            econ_event = strike_refusal or self._process_economy(pid, action)

            # ── Phase 11: 도구 마모 (work 시) ──
            tool_evt = None
            if action == "work":
                tool_evt = self._wear_tool(pid)

            # ── 숙달 & 집중 업데이트 ──
            mastery_event = None
            if action == "work":
                mastery_event = self._update_mastery_tick(pid)

            # 보상 (경제 결과 + 숙달 반영)
            reward = self._compute_reward(pid, action, inner.energy_pool, prev_energy)
            if econ_event and action == "work":
                etype = econ_event.get("type", "")
                goods_amt = float(econ_event.get("goods_amount", 0) or 0)
                if etype in ("wage_received", "self_employed", "self_employed_primitive") and goods_amt > 0:
                    reward += min(0.15, goods_amt * 0.05)
                if etype == "wage_unpaid":
                    reward -= 0.3
                elif etype == "self_employed":
                    paid_ratio = econ_event.get("paid_ratio", 1.0)
                    if paid_ratio < 0.5:
                        reward -= 0.1 * (1.0 - paid_ratio)
                    elif paid_ratio < 1.0:
                        reward *= paid_ratio
                elif etype == "self_employed_primitive":
                    reward -= 0.15

            # 몰입 보너스 (flow state → 보상 추가)
            if mastery_event and mastery_event.get("flow"):
                reward += 0.2

            # 적성 불일치 페널티
            if mastery_event and mastery_event.get("aptitude", 0.5) < 0.4:
                reward -= 0.1

            reward = float(np.clip(reward, -1.0, 1.0))
            if action == "work":
                hist = self._work_reward_history.setdefault(pid, [])
                hist.append(reward)
                if len(hist) > 100:
                    self._work_reward_history[pid] = hist[-100:]

            brain.snn.apply_reward(reward)

            # readout 가중치 미세 적응 (강한 보상에서만, 매우 느리게)
            brain.adapt_readout(ACTIONS.index(action), reward)

            # STDP 집중 연동: 집중할 때 시냅스 가소성↑
            if mastery_event and mastery_event.get("concentration", 0) > 0.5:
                brain.snn.stdp_lr = 0.0003 * (1.0 + mastery_event["concentration"] * 0.5)
            else:
                brain.snn.stdp_lr = 0.0003

            # ── 만성 상태 갱신 ──
            has_social = any(
                e["personas"].get(pid, {}).get("action") == "socialize"
                for e in [{"personas": {pid: {"action": action}}}]
            )
            inner.update_chronic(
                energy=inner.energy_pool,
                weather_feels=region_weather.get("feels_like_c", 15),
                has_social=(action == "socialize"),
                personality=self.personas[pid].personality,
            )

            # ── 승급 trigger 갱신 (매 work 틱) ──
            if action == "work":
                self._update_promotion_trigger(pid)

            # ── 적응 유연성: class 3+ 미사용 skill mastery decay ──
            p_class = self.personas[pid].persona_class
            if p_class >= 3:
                current_job = self._get_persona_job_title(pid)
                for sid, sp in inner.skill_profiles.items():
                    if sid == current_job:
                        continue
                    if self.time.tick - sp.last_tick > 50:
                        sp.mastery = max(0.0, sp.mastery - 0.0001 * p_class)

            # explore → 자연 채집 시도 + 지식 기록
            if action == "explore":
                forage_result = self.try_forage(pid)
                if forage_result:
                    tick_result["personas"].setdefault(pid, {})["forage"] = forage_result
                written = self.try_write_knowledge(pid)
                if written:
                    tick_result["personas"].setdefault(pid, {})["wrote_records"] = len(written)

            # 학문 행동 또는 socialize에서 서적 열람
            if action in ("idle", "socialize"):
                if self.time.tick % 24 == 0:
                    self.try_read_knowledge(pid)

            # 감정 + tone + 기억
            inner.update_emotion(action, inner.energy_pool, prev_energy)

            # ── 적성→감정 반영 (work 시) ──
            if mastery_event:
                apt = mastery_event.get("aptitude", 0.5)
                if apt > 0.6:
                    # 적합한 일 → joy + V(DA)
                    passion_joy = (apt - 0.6) * 0.5
                    inner.chiljeong[0] = min(1.0, inner.chiljeong[0] + passion_joy)
                    inner.tone[0] = np.float16(min(2.0, float(inner.tone[0]) + passion_joy * 0.3))
                elif apt < 0.4:
                    # 부적합한 일 → anger + disgust
                    mismatch = (0.4 - apt) * 0.3
                    inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + mismatch)
                    inner.chiljeong[5] = min(1.0, inner.chiljeong[5] + mismatch * 0.5)

                # 몰입 효과
                if mastery_event.get("flow"):
                    inner.chiljeong[0] = min(1.0, inner.chiljeong[0] + 0.15)  # joy
                    inner.tone[0] = np.float16(min(2.0, float(inner.tone[0]) + 0.1))  # V(DA)
                    inner.tone[2] = np.float16(min(2.0, float(inner.tone[2]) + 0.05))  # S(5-HT)

            # ── 기후→감정 매트릭스 (C7 + shelter) ──
            self._apply_weather_emotion(inner, region_weather, shelter)
            inner.update_tone_from_emotion()

            episode = EpisodeTrace(
                tick=self.time.tick, action=action,
                emotion_snapshot=inner.chiljeong.copy(),
                energy_at_time=inner.energy_pool,
            )
            episode.compute_salience(inner.chiljeong)
            inner.add_episode(episode)

            # 수면 진입
            if inner.energy_pool < 0.1:
                inner.is_sleeping = True
                inner.sleep_ticks_remaining = 6

            actions[pid] = action
            persona_result = {
                "name": self.personas[pid].name,
                "action": action,
                "energy": round(inner.energy_pool, 3),
                "hunger": round(float(inner.oyok[0]), 3),
                "sleeping": inner.is_sleeping,
                "firing_rate": round(brain.get_stats()["firing_rate"], 4),
                "emotions": inner.emotion_dict(),
                "reward": round(reward, 3),
                "memories": len(inner.episodes),
                "chronic_stress": round(inner.chronic_stress, 3),
                "chronic_comfort": round(inner.chronic_comfort, 3),
                "vitality": round(inner.vitality, 3),
                "mortality_awareness": round(inner.mortality_awareness, 3),
                "survival_mode": inner.survival_mode,
            }
            if mastery_event:
                persona_result["mastery"] = mastery_event
            if econ_event:
                persona_result["economy"] = econ_event
            if tool_evt:
                persona_result["tool"] = tool_evt
            if survival_evt:
                persona_result["survival"] = survival_evt
            if eat_result:
                persona_result["eat"] = eat_result
            tick_result["personas"][pid] = persona_result

        # ── Stage 0.5: Nomos — 자연법 탐지 ──
        nomos_events = self._nomos_check(actions, tick_result)
        if nomos_events:
            tick_result["nomos"] = nomos_events

        # ── Stage 1.5a: 사망 판정 ──
        deaths = self._check_deaths()
        if deaths:
            tick_result["deaths"] = deaths
            for death in deaths:
                actions[death["pid"]] = "death"
                if death.get("reincarnation"):
                    tick_result["personas"][death["pid"]]["action"] = "death"

        # ── Stage 1.5b: 재난 판정 ──
        disasters = self._check_disasters()
        if disasters:
            tick_result["disasters"] = disasters

        # ── Stage 2: 사회적 상호작용 ──
        socializers = [pid for pid, a in actions.items() if a == "socialize"]
        interactions = []
        if len(socializers) >= 2:
            # 2명 이상 socializing → 만남 발생
            for i in range(len(socializers)):
                for j in range(i + 1, len(socializers)):
                    a, b = socializers[i], socializers[j]
                    interaction = self._process_interaction(a, b)
                    interactions.append(interaction)
        elif len(socializers) == 1:
            # 혼자 socialize → 가장 친한 깨어있는 상대와 단방향 교류
            sid = socializers[0]
            awake_others = [
                pid for pid in self.personas
                if pid != sid and not self.inners[pid].is_sleeping
            ]
            if awake_others:
                # 친밀도 최대인 상대
                best = max(
                    awake_others,
                    key=lambda p: self._ensure_relationship(sid, p).familiarity,
                )
                interaction = self._process_interaction(sid, best, mutual=False)
                interactions.append(interaction)

        tick_result["interactions"] = interactions

        # ── Stage 2.5: 승급/강등 판정 (24틱마다) ──
        if self.time.tick % 24 == 0:
            promotion_events = []
            demotion_events = []
            promoted_pids: set[str] = set()
            for pid in self.personas:
                if self.inners[pid].is_sleeping:
                    continue
                # trigger 충족 시 gate 검증
                required = self._get_required_ticks(pid)
                if self.inners[pid].promotion_stable_ticks >= required:
                    evt = self._evaluate_promotion_gate(pid)
                    if evt:
                        promotion_events.append(self._execute_promotion(evt))
                        promoted_pids.add(pid)
                # 강등 체크 (같은 틱 승급자는 스킵 — 경쟁조건 방지)
                if pid not in promoted_pids:
                    demo = self._check_demotion(pid)
                    if demo:
                        demotion_events.append(demo)
            if promotion_events:
                tick_result["promotions"] = promotion_events
            if demotion_events:
                tick_result["demotions"] = demotion_events

        # ── Stage 3: 관계 요약 ──
        tick_result["relationships"] = {
            f"{r.persona_a}-{r.persona_b}": {
                "familiarity": round(r.familiarity, 3),
                "trust": round(r.trust, 3),
                "interactions": r.interaction_count,
            }
            for r in self.relationships.values()
        }

        # ── Stage 4: 경제 창발 — Job 자동 생성 + 구직 ──
        if self.time.tick % 24 == 0:  # 1일 1회 판정
            job_events = self._auto_economy_tick()
            economy_events.extend(job_events)
        if self.time.tick % 48 == 0 and self.time.tick > 0:
            community_metrics = self._compute_community_metrics()
            self._last_community_metrics = community_metrics
            tick_result["community_metrics"] = [
                {
                    "territory_id": m.territory_id,
                    "node_count": m.node_count,
                    "edge_count": m.edge_count,
                    "density_ratio": round(m.density_ratio, 4),
                    "intra_edges": m.intra_edges,
                    "inter_edges": m.inter_edges,
                    "intra_inter_ratio": round(m.intra_inter_ratio, 4),
                }
                for m in community_metrics
            ]
            for metric in community_metrics:
                if metric.density_ratio > 0.5:
                    economy_events.append({
                        "type": "density_warning",
                        "territory": metric.territory_id,
                        "density_ratio": round(metric.density_ratio, 4),
                    })
        if economy_events:
            tick_result["economy_events"] = economy_events
            self.event_log.extend(economy_events)

        self.log.append(tick_result)
        return tick_result

    # ══════════════════════════════════════════════════════════
    # 경제 창발: 필요 기반 Job 자동 생성 + 구직
    # ══════════════════════════════════════════════════════════

    def _process_movement(self, pid: str) -> None:
        """Phase 17 movement on the local 8-neighbor grid."""
        persona = self.personas[pid]
        inner = self.inners[pid]
        if inner.migration_cooldown > 0:
            inner.migration_cooldown -= 1
            return

        x, y = persona.pos
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                nx, ny = x + dx, y + dy
                if not self.world.in_bounds(nx, ny):
                    continue
                cell = self.world.get_cell(nx, ny)
                if cell.biome in MOVE_DISALLOWED_BIOMES:
                    continue
                candidates.append(cell)
        if not candidates:
            return

        candidates.sort(key=lambda cell: score_move(cell, persona), reverse=True)
        candidates = candidates[:MOVE_CANDIDATE_K]
        scores = np.array([score_move(cell, persona) for cell in candidates], dtype=np.float64)
        scaled = scores / MOVE_SOFTMAX_T
        scaled -= scaled.max()
        probs = np.exp(scaled)
        probs /= probs.sum()
        idx = int(self._np_rng.choice(len(candidates), p=probs))
        chosen = candidates[idx]
        if (chosen.x, chosen.y) != persona.pos:
            persona.pos = (chosen.x, chosen.y)
            inner.migration_cooldown = MIGRATION_COOLDOWN_DEFAULT

    def _get_territory_residents(self, tid: str) -> list[str]:
        """Return economy-tick cached residents for a territory."""
        if self._territory_residents_cache is None:
            cache: dict[str, list[str]] = {}
            for pid, persona in self.personas.items():
                cache.setdefault(persona.territory, []).append(pid)
            self._territory_residents_cache = cache
        return self._territory_residents_cache.get(tid, [])

    def _get_community_members(self, pid: str, min_trust: float = 0.4) -> list[str]:
        """Same-territory trusted residents, excluding pid."""
        persona = self.personas[pid]
        territory_id = persona.territory
        members = []
        for other_pid, other in self.personas.items():
            if other_pid == pid or other.territory != territory_id:
                continue
            rel_key = Relationship(persona_a=pid, persona_b=other_pid).key()
            rel = self.relationships.get(rel_key)
            if rel and rel.trust >= min_trust:
                members.append(other_pid)
        return members

    def _get_territory_guard_active_count(self, territory_id: str) -> int:
        """Count awake non-striking guards in a territory."""
        count = 0
        for other_pid in self._get_territory_residents(territory_id):
            other_inner = self.inners.get(other_pid)
            if not other_inner or other_inner.is_sleeping:
                continue
            if other_inner.strike_until_tick > self.time.tick:
                continue
            if self._get_persona_job_title(other_pid) == "guard":
                count += 1
        return count

    def _compute_community_metrics(self) -> list[CommunityMetrics]:
        """Compute sparse trust metrics in O(relationships)."""
        node_counts = {tid: 0 for tid in self.territories}
        territory_by_pid = {}
        for pid, persona in self.personas.items():
            territory_by_pid[pid] = persona.territory
            if persona.territory in node_counts:
                node_counts[persona.territory] += 1

        intra_edges = {tid: 0 for tid in self.territories}
        inter_edges = {tid: 0 for tid in self.territories}
        for rel in self.relationships.values():
            if rel.trust < 0.4:
                continue
            a_tid = territory_by_pid.get(rel.persona_a)
            b_tid = territory_by_pid.get(rel.persona_b)
            if a_tid not in self.territories or b_tid not in self.territories:
                continue
            if a_tid == b_tid:
                intra_edges[a_tid] += 1
            else:
                inter_edges[a_tid] += 1
                inter_edges[b_tid] += 1

        metrics = []
        for tid in self.territories:
            n = node_counts[tid]
            intra = intra_edges[tid]
            inter = inter_edges[tid]
            edge_count = intra + inter
            possible = max(1, n * (n - 1) // 2)
            density_ratio = min(1.0, intra / possible)
            metrics.append(CommunityMetrics(
                territory_id=tid,
                node_count=n,
                edge_count=edge_count,
                density_ratio=density_ratio,
                intra_edges=intra,
                inter_edges=inter,
                intra_inter_ratio=intra / max(1, inter),
            ))
        return metrics

    def _release_employment(self, employee_id: str, reason: str = "released") -> dict:
        """Detach an employee and reopen the job when capacity becomes available."""
        persona = self.personas.get(employee_id)
        if not persona or not persona.employment_id:
            return {}

        emp_id = persona.employment_id
        emp = self.employments.get(emp_id)
        persona.employment_id = None
        if not emp:
            return {"employee": employee_id, "reason": reason, "stale_employment": emp_id}

        job = self.jobs.get(emp.job_id)
        active_count = sum(
            1 for other_id, other in self.employments.items()
            if other_id != emp_id and other.job_id == emp.job_id
        )
        if job:
            job.is_open = active_count < job.max_employees

        del self.employments[emp_id]
        return {
            "employee": employee_id,
            "employer": emp.employer_id,
            "job_id": emp.job_id,
            "reason": reason,
            "unpaid_gold": round(emp.unpaid, 2),
            "job_reopened": bool(job and job.is_open),
        }

    def _change_persona_territory(
        self,
        persona_id: str,
        target_territory_id: str,
        reason: str,
    ) -> dict:
        """Atomically change persona.territory and sync persona.region.

        The **only** allowed write path to `persona.territory` outside
        the engine constructor / initial placement. All migration code
        paths (`_try_exodus`, `_update_grievances.mass_exodus`, future
        Φ-2 faction moves) MUST call this helper.

        Args:
            persona_id: Target persona identifier.
            target_territory_id: New territory id. Must exist in `self.territories`.
            reason: Migration reason tag for events ("exodus", "mass_exodus", ...).

        Returns:
            dict {
                "persona": persona_id,
                "from_territory": old_tid,
                "to_territory": target_territory_id,
                "from_region": old_region,
                "to_region": new_region,
                "reason": reason,
                "employment_cleanup": {...},   # from _release_employment
            }

        Raises:
            KeyError: target_territory_id not in self.territories.
            ValueError: persona_id not in self.personas.

        Invariants (MUST hold at return):
            I1. persona.territory == target_territory_id
            I2. persona.region == self.territories[target_territory_id].region
            I3. self._territory_residents_cache is None (invalidated)
            I4. Employment in old territory is released (via _release_employment)

        Note: no-op branch (same-target) leaves cache/employment unchanged — already consistent.

        Atomicity:
            If any step raises, the caller is responsible — this helper
            does NOT rollback partial changes. Callers MUST validate
            preconditions (target exists, persona exists) before invoking.

        Side effects (allowed):
            - Releases persona's employment in the *old* territory
            - Invalidates resident cache
            - Returns an employment_cleanup dict for event propagation

        Non-side-effects (forbidden):
            - Does NOT reset grievance (caller decides; exodus halves it,
              mass_exodus sets 0.3)
            - Does NOT set exodus_cooldown_until_tick (caller decides)
            - Does NOT emit "exodus"/"mass_exodus" events (caller builds)
        """
        if persona_id not in self.personas:
            raise ValueError(f"unknown persona: {persona_id}")
        if target_territory_id not in self.territories:
            raise KeyError(f"unknown territory: {target_territory_id}")

        persona = self.personas[persona_id]
        target_territory = self.territories[target_territory_id]
        old_tid = persona.territory
        old_region = persona.region

        if old_tid == target_territory_id and old_region == target_territory.region:
            return {
                "persona": persona_id,
                "from_territory": old_tid,
                "to_territory": target_territory_id,
                "from_region": old_region,
                "to_region": target_territory.region,
                "reason": reason,
                "employment_cleanup": None,
            }

        employment_cleanup = self._release_employment(persona_id, reason=reason)

        persona.territory = target_territory_id          # noqa: PHASE17_SSOT_WRITE
        persona.region = target_territory.region         # noqa: PHASE17_SSOT_WRITE

        self._territory_residents_cache = None

        return {
            "persona": persona_id,
            "from_territory": old_tid,
            "to_territory": target_territory_id,
            "from_region": old_region,
            "to_region": target_territory.region,
            "reason": reason,
            "employment_cleanup": employment_cleanup,
        }

    def _change_persona_faction(
        self,
        pid: str,
        new_faction_id: str | None,
        *,
        source: FactionChangeSource,
    ) -> None:
        """persona.faction 쓰기 유일 경로. AST whitelist로 강제."""
        if source not in ("birth_founder", "affiliation", "drift", "conflict"):
            raise ValueError(f"invalid faction change source: {source!r}")
        if new_faction_id is not None and new_faction_id not in self.factions:
            raise ValueError(f"unknown faction_id: {new_faction_id!r}")

        persona = self.personas[pid]
        prev = persona.faction
        if prev == new_faction_id:
            return

        persona.faction = new_faction_id  # noqa: PHASE17_FACTION_SSOT_WRITE
        persona.faction_cooldown = FACTION_COOLDOWN_TICKS if prev is not None else 0  # noqa: PHASE17_FACTION_SSOT_WRITE
        self._faction_members_cache = {}

        self.event_log.append({
            "type": "faction_change",
            "tick": self.time.tick,
            "pid": pid,
            "from_faction": prev,
            "to_faction": new_faction_id,
            "source": source,
        })

    def _tick_faction_cooldown(self, pid: str) -> None:
        """persona.faction_cooldown 매 틱 1 감소."""
        persona = self.personas[pid]
        if persona.faction_cooldown <= 0:
            return
        persona.faction_cooldown -= 1  # noqa: PHASE17_FACTION_SSOT_WRITE

    def _get_relationship_trust(self, pid_a: str, pid_b: str) -> float:
        if pid_a == pid_b:
            return 1.0
        rel_key = Relationship(persona_a=pid_a, persona_b=pid_b).key()
        rel = self.relationships.get(rel_key)
        return float(rel.trust) if rel else 0.5

    def _rebuild_faction_members_cache(self) -> None:
        """tick당 1회 호출. faction별 member 리스트를 sorted(pid)로 고정."""
        cache: dict[str, list[Persona]] = {fid: [] for fid in self.factions}
        for pid in sorted(self.personas):
            if pid not in self.inners:
                continue
            persona = self.personas[pid]
            if persona.id != pid:
                continue
            if persona.faction is not None and persona.faction in cache:
                cache[persona.faction].append(persona)
        self._faction_members_cache = cache

    def _faction_members(self, faction_id: str) -> list[Persona]:
        return self._faction_members_cache.get(faction_id, [])

    def _same_territory(self, persona: Persona, faction_id: str) -> float:
        members = self._faction_members(faction_id)
        return 1.0 if any(m.territory == persona.territory for m in members) else 0.0

    def _trust_density(self, persona: Persona, faction_id: str) -> float:
        members = self._faction_members(faction_id)
        if not members:
            return 0.0
        trusts = [
            self._get_relationship_trust(persona.id, member.id)
            for member in members
            if member.id != persona.id
        ]
        if not trusts:
            return 0.0
        return 2.0 * (sum(trusts) / len(trusts) - 0.5)

    def _ensure_relationship(self, pid_a: str, pid_b: str) -> Relationship:
        """Return a relationship row, recreating missing or stale keys when needed."""
        rel_key = Relationship(persona_a=pid_a, persona_b=pid_b).key()
        rel = self.relationships.get(rel_key)
        if rel is None:
            rel = Relationship(persona_a=rel_key[0], persona_b=rel_key[1])
            self.relationships[rel_key] = rel
            return rel
        if rel.persona_a != rel_key[0] or rel.persona_b != rel_key[1]:
            rel.persona_a = rel_key[0]
            rel.persona_b = rel_key[1]
        return rel

    def _rekey_relationships(self, old_pid: str, new_pid: str) -> None:
        """Rewrite relationship keys when reincarnation changes a persona id."""
        rewritten: dict[tuple, Relationship] = {}
        stale_keys: list[tuple] = []
        for rel_key, rel in self.relationships.items():
            if old_pid not in rel_key:
                continue
            stale_keys.append(rel_key)
            rel.persona_a = new_pid if rel.persona_a == old_pid else rel.persona_a
            rel.persona_b = new_pid if rel.persona_b == old_pid else rel.persona_b
            new_key = rel.key()
            rel.persona_a = new_key[0]
            rel.persona_b = new_key[1]
            rewritten[new_key] = rel
        for rel_key in stale_keys:
            del self.relationships[rel_key]
        self.relationships.update(rewritten)

    def _rekey_economic_references(self, old_pid: str, new_pid: str, new_persona: Persona) -> None:
        """Rewrite employment/job references when reincarnation changes a persona id."""
        old_persona = self.personas.get(old_pid)
        if old_persona and old_persona.employment_id in self.employments:
            new_persona.employment_id = old_persona.employment_id
        for job in self.jobs.values():
            if job.employer_id == old_pid:
                job.employer_id = new_pid
        for employment in self.employments.values():
            if employment.employer_id == old_pid:
                employment.employer_id = new_pid
            if employment.employee_id == old_pid:
                employment.employee_id = new_pid

    def _shared_grievance(self, persona: Persona, faction_id: str) -> float:
        """grievance·grievance_lord_id는 InnerWorld 소재."""
        if persona.id not in self.inners:
            return 0.0
        p_inner = self.inners[persona.id]
        if p_inner.grievance < GRIEVANCE_MIN_SHARED:
            return 0.0
        members = self._faction_members(faction_id)
        if not members:
            return 0.0
        same_target = sum(
            1
            for member in members
            if member.id in self.inners
            and self.inners[member.id].grievance >= GRIEVANCE_MIN_SHARED
            and self.inners[member.id].grievance_lord_id == p_inner.grievance_lord_id
        )
        return same_target / len(members)

    def _spatial_proximity(self, persona: Persona, faction_id: str) -> float:
        members = self._faction_members(faction_id)
        dists = sorted(
            max(abs(persona.pos[0] - member.pos[0]), abs(persona.pos[1] - member.pos[1]))
            for member in members
            if member.id != persona.id
        )[:5]
        if not dists:
            return 0.0
        avg = sum(dists) / len(dists)
        return max(0.0, 1.0 - avg / PROXIMITY_DECAY_SCALE)

    def _compute_affiliation_tick(self) -> None:
        """매 틱 affiliation score를 갱신한다."""
        self._rebuild_faction_members_cache()
        # v6: 활성 인구 집계 (size tax 분모). inners 기준 = 살아있는 페르소나
        total_active = max(1, sum(1 for pid in self.personas if pid in self.inners))
        new_scores: dict[str, dict[str, float]] = {}
        for pid in sorted(self.personas):
            if pid not in self.inners:
                continue
            persona = self.personas[pid]
            prev_scores = self.inners[pid].affiliation_scores
            scored: dict[str, float] = {}
            for fid in sorted(self.factions):
                territory_weight = (
                    W_TERRITORY_SAME
                    if self._same_territory(persona, fid) > 0.5
                    else W_TERRITORY_DIFF
                )
                score = (
                    territory_weight
                    + W_TRUST * self._trust_density(persona, fid)
                    + W_GRIEVANCE * self._shared_grievance(persona, fid)
                    + W_PROXIMITY * self._spatial_proximity(persona, fid)
                )
                # v6: 규모 tax — 이번 틱 가산분에만 적용 (누적 decay 결과는 불변)
                size_ratio = len(self._faction_members_cache.get(fid, ())) / total_active
                if size_ratio > FACTION_SIZE_TAX_START:
                    excess = size_ratio - FACTION_SIZE_TAX_START
                    span = 1.0 - FACTION_SIZE_TAX_START
                    tax = max(FACTION_SIZE_TAX_MIN, 1.0 - excess / span)
                    score *= tax
                # Stage 3 B: minority persistence boost (2026-04-24)
                member_count = len(self._faction_members_cache.get(fid, ()))
                if 0 < member_count <= MINORITY_PERSISTENCE_MAX_MEMBERS:
                    if self._same_territory(persona, fid) > 0.5:
                        score += MINORITY_PERSISTENCE_BOOST
                # Stage 6 H-lite: founder lineage identity affinity (2026-04-26)
                if W_LINEAGE > 0 and persona.faction:
                    cur_faction = self.factions.get(persona.faction)
                    cand_faction = self.factions.get(fid)
                    if cur_faction and cand_faction:
                        lineage_a = set(cur_faction.founder_lineage) | {cur_faction.founder_pid}
                        lineage_b = set(cand_faction.founder_lineage) | {cand_faction.founder_pid}
                        overlap = len(lineage_a & lineage_b) / max(len(lineage_a), len(lineage_b), 1)
                        score += W_LINEAGE * overlap
                scored[fid] = DECAY * prev_scores.get(fid, 0.0) + score
            ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
            new_scores[pid] = dict(ranked[:MAX_TRACKED_FACTIONS_PER_PERSONA])
        for pid, scores in new_scores.items():
            self.inners[pid].affiliation_scores = scores

    def _commit_faction_tick(self) -> None:
        """48틱마다 faction 가입/이적 commit."""
        if self.time.tick % FACTION_COMMIT_EVERY != 0:
            return
        # v6: homeostasis — active faction 수에 따라 margin_floor 조절
        active_count = sum(
            1 for fid in self.factions
            if len(self._faction_members_cache.get(fid, ())) > 0
        )
        margin_floor = (
            DRIFT_MARGIN_MIN * HOMEOSTASIS_DRIFT_MARGIN_SCALE
            if active_count <= HOMEOSTASIS_LOW_THRESHOLD
            else DRIFT_MARGIN_MIN
        )
        snapshot = {
            pid: (
                self.personas[pid].faction,
                self.personas[pid].faction_cooldown,
                dict(self.inners[pid].affiliation_scores),
            )
            for pid in self.personas
            if pid in self.inners
        }
        for pid in sorted(snapshot):
            cur_fid, cooldown, scores = snapshot[pid]
            if cooldown > 0 or not scores:
                continue
            sorted_items = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
            best_fid, best_score = sorted_items[0]
            if cur_fid is None:
                if best_score >= THETA_JOIN:
                    self._change_persona_faction(pid, best_fid, source="affiliation")
            else:
                current_faction = self.factions.get(cur_fid)
                if current_faction is not None and current_faction.grace_until_tick > self.time.tick:
                    continue
                if best_fid == cur_fid:
                    continue
                current_score = scores.get(cur_fid, 0.0)
                gap = best_score - current_score
                dynamic_margin = max(margin_floor, gap * DRIFT_MARGIN_RATIO)  # v6
                if gap >= dynamic_margin:
                    self._change_persona_faction(pid, best_fid, source="drift")
        self._rebuild_faction_members_cache()

    def _respawn_faction_tick(self) -> None:
        """Stage 3 C: active faction 수가 TARGET 미만이면 K틱 주기로 territory lord 기반 신규 faction 생성.

        **Absorbing state 탈출 유일 경로**. 기존 `_init_founder_seeds`(tick=0)와 달리 매 K틱 검사.
        불변 제약:
            - RNG는 반드시 `_derive_rng("faction_respawn", ...)`로 격리 (기존 seed 스트림 오염 방지)
            - SSoT: `_change_persona_faction(..., source="birth_founder")` 재사용 (신규 source 금지)
            - 기존 territory의 lord를 founder로 재사용. lord 없으면 최고 trust persona.
        """
        if self.time.tick == 0:
            return
        if self.time.tick % FOUNDER_RESPAWN_EVERY != 0:
            return

        active_count = sum(
            1 for fid in self.factions
            if len(self._faction_members_cache.get(fid, ())) > 0
        )
        if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
            return

        # territory 우선순위: lord 존재 > faction 없는 거주자 수 많음 > sorted(id)
        territory_priority: list[tuple[int, int, str]] = []
        for territory in self.territories.values():
            free_residents = [
                persona for persona in self.personas.values()
                if persona.territory == territory.id
                and persona.faction is None
                and persona.id in self.inners
            ]
            if len(free_residents) < 3:
                continue
            has_lord = 1 if territory.lord_id else 0
            # 우선순위 = lord 있음 우선(-has_lord), 거주자 많음 우선(-count), id 오름차순(territory.id)
            territory_priority.append((-has_lord, -len(free_residents), territory.id))

        territory_priority.sort()

        for _, _, territory_id in territory_priority:
            if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
                return  # 목표 달성 시 즉시 중단 (한 틱에 하나만 생성해도 target 도달하면 끝)
            territory = self.territories[territory_id]
            free_residents = [
                persona for persona in self.personas.values()
                if persona.territory == territory.id
                and persona.faction is None
                and persona.id in self.inners
            ]
            if len(free_residents) < 3:
                continue
            founder = self._pick_founder(free_residents, territory)
            if founder is None:
                continue
            charter = self._sample_charter(territory.id)
            # 격리된 RNG 스트림 사용 (기존 seed 결과 비호환 최소화)
            rng = self._derive_rng("faction_respawn", territory.id, self.time.tick)
            faction_id = uuid.UUID(bytes=rng.bytes(16)).hex
            faction_name = f"{territory.name}_R{self.time.tick}"
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
                founder_lineage=(founder.id,),
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1

        if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
            self._rebuild_faction_members_cache()
            return

        # Stage 3 C fallback: collapse 이후 free resident가 0명이면 기존 거주자에서 founder를 분리한다.
        # 신규 source 없이 birth_founder를 재사용하고, faction write는 SSoT helper만 통과한다.
        territory_priority = []
        for territory in self.territories.values():
            residents = [
                persona for persona in self.personas.values()
                if persona.territory == territory.id
                and persona.id in self.inners
            ]
            if len(residents) < 3:
                continue
            has_lord = 1 if territory.lord_id else 0
            territory_priority.append((-has_lord, -len(residents), territory.id))

        territory_priority.sort()

        for _, _, territory_id in territory_priority:
            if active_count >= FOUNDER_RESPAWN_TARGET_ACTIVE:
                break
            territory = self.territories[territory_id]
            residents = [
                persona for persona in self.personas.values()
                if persona.territory == territory.id
                and persona.id in self.inners
            ]
            if len(residents) < 3:
                continue
            founder = self._pick_founder(residents, territory)
            if founder is None:
                continue
            charter = self._sample_charter(territory.id)
            rng = self._derive_rng("faction_respawn", territory.id, self.time.tick)
            faction_id = uuid.UUID(bytes=rng.bytes(16)).hex
            faction_name = f"{territory.name}_R{self.time.tick}"
            faction = Faction(
                id=faction_id,
                name=faction_name,
                founder_pid=founder.id,
                charter=charter,
                created_tick=self.time.tick,
                grace_until_tick=self.time.tick + RESPAWN_GRACE_TICKS,
                founder_lineage=(founder.id,),
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
            self.personas[founder.id].faction_cooldown = FOUNDER_RESPAWN_EVERY  # noqa: PHASE17_FACTION_SSOT_WRITE
            active_count += 1

        self._rebuild_faction_members_cache()

    def _pick_founder(self, candidates: list[Persona], territory: Territory) -> Persona | None:
        """우선순위: lord > 최고 평균 trust > sorted(pid)."""
        if territory.lord_id:
            for persona in candidates:
                if persona.id == territory.lord_id:
                    return persona

        def avg_trust(persona: Persona) -> float:
            trusts = [
                self._get_relationship_trust(persona.id, other.id)
                for other in candidates
                if other.id != persona.id
            ]
            return sum(trusts) / len(trusts) if trusts else 0.5

        ranked = sorted(candidates, key=lambda persona: (-avg_trust(persona), persona.id))
        return ranked[0] if ranked else None

    def _sample_charter(self, territory_id: str) -> tuple[str, ...]:
        rng = self._derive_rng("faction_charter", territory_id)
        n = int(rng.integers(CHARTER_PRIMITIVE_COUNT[0], CHARTER_PRIMITIVE_COUNT[1] + 1))
        chosen = rng.choice(NORM_PRIMITIVE_CATALOG, size=n, replace=False)
        return tuple(sorted(str(item) for item in chosen))

    def _init_founder_seeds(self) -> None:
        """tick=0 한 번 호출. Territory당 최대 1 founder seeding."""
        if self.factions:
            return
        for territory in sorted(self.territories.values(), key=lambda item: item.id):
            candidates = [persona for persona in self.personas.values() if persona.territory == territory.id]
            if len(candidates) < 3:
                continue
            founder = self._pick_founder(candidates, territory)
            if founder is None:
                continue
            charter = self._sample_charter(territory.id)
            faction_id = uuid.UUID(bytes=self._derive_rng("faction_seed", territory.id).bytes(16)).hex
            faction = Faction(
                id=faction_id,
                name=f"{territory.name}_F1",
                founder_pid=founder.id,
                charter=charter,
                created_tick=0,
                founder_lineage=(founder.id,),
            )
            self.factions[faction.id] = faction
            self._change_persona_faction(founder.id, faction.id, source="birth_founder")
        self._rebuild_faction_members_cache()

    def _project_faction_tick(self) -> None:
        """24틱마다 factionRef를 투영한다."""
        if self.time.tick % FACTION_PROJECT_EVERY != 0:
            return
        snapshot = {
            pid: (persona.territory, persona.faction)
            for pid, persona in sorted(self.personas.items())
        }
        new_refs: dict[str, str | None] = {}
        for territory in self.territories.values():
            members = [
                (pid, fid)
                for pid, (tid, fid) in snapshot.items()
                if tid == territory.id and fid is not None
            ]
            if not members:
                new_refs[territory.id] = None
                continue
            counts = Counter(fid for _, fid in members)
            top, top_count = counts.most_common(1)[0]
            second_count = counts.most_common(2)[1][1] if len(counts) > 1 else 0
            prev_ref = territory.factionRef
            if prev_ref and prev_ref in counts:
                prev_count = counts[prev_ref]
                if top_count - prev_count < FACTION_HYSTERESIS:
                    new_refs[territory.id] = prev_ref
                    continue
            if top_count - second_count >= FACTION_HYSTERESIS:
                new_refs[territory.id] = top
            else:
                new_refs[territory.id] = prev_ref
        for tid, ref in new_refs.items():
            self.territories[tid].factionRef = ref

    def _territory_neighbors(self, tid: str) -> set[str]:
        """territory tid에 Chebyshev=1 인접한 territory id 집합."""
        if self._territory_neighbors_cache is None:
            self._rebuild_territory_adjacency_cache()
        return set(self._territory_neighbors_cache.get(tid, set()))

    def _territories_within(self, tid: str, radius: int) -> set[str]:
        """Chebyshev radius 내 territory id 집합."""
        if radius < 1:
            raise ValueError(f"radius must be >= 1, got {radius}")
        if tid not in self.territories:
            return set()
        if radius == 1:
            return self._territory_neighbors(tid)
        result: set[str] = set()
        source_cells = [
            (cell.x, cell.y)
            for cell in self.world.iter_cells()
            if cell.territoryRef == tid
        ]
        for x0, y0 in source_cells:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = x0 + dx, y0 + dy
                    if not self.world.in_bounds(nx, ny):
                        continue
                    ref = self.world.get_cell(nx, ny).territoryRef
                    if ref is not None and ref != tid:
                        result.add(ref)
        return result

    def _rebuild_territory_adjacency_cache(self) -> None:
        """모든 territory의 Chebyshev=1 인접 테이블 1회 빌드."""
        cache: dict[str, set[str]] = {tid: set() for tid in self.territories}
        for cell in self.world.iter_cells():
            tid = cell.territoryRef
            if tid is None:
                continue
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nx, ny = cell.x + dx, cell.y + dy
                    if not self.world.in_bounds(nx, ny):
                        continue
                    nref = self.world.get_cell(nx, ny).territoryRef
                    if nref is not None and nref != tid:
                        cache[tid].add(nref)
        self._territory_neighbors_cache = cache

    def _collect_neighbor_faction_ids(self, territory_id: str) -> set[str]:
        """인접 territory의 factionRef 집합. 공허(None) 제외."""
        refs: set[str] = set()
        for nid in self._territory_neighbors(territory_id):
            ref = self.territories[nid].factionRef
            if ref is not None:
                refs.add(ref)
        return refs

    def _apply_faction_telemetry(self, pid: str, input_current: np.ndarray) -> None:
        """경제 perception 뉴런 300~349에 faction 신호 co-fire."""
        persona = self.personas[pid]
        if persona.faction is not None:
            input_current[300:325] += FACTION_TELEMETRY_BIAS_OWN
        neighbor_fids = self._collect_neighbor_faction_ids(persona.territory)
        if neighbor_fids:
            own_in_neighbors = persona.faction in neighbor_fids if persona.faction else False
            bias = FACTION_TELEMETRY_BIAS_NEIGHBOR * (1.0 if not own_in_neighbors else 0.5)
            input_current[325:350] += bias

    def _build_persona_snn_input(self, pid: str) -> np.ndarray:
        """Engine-side pre-bias for faction telemetry without editing PersonaBrain."""
        brain = self.brains[pid]
        input_current = np.zeros(brain.n_neurons, dtype=np.float32)
        if brain.n_neurons >= 350:
            self._apply_faction_telemetry(pid, input_current)
        return input_current

    def faction_population_distribution(self) -> dict[str, int]:
        """{faction_id: member_count}. 공허 faction은 0으로 포함."""
        dist = {fid: 0 for fid in sorted(self.factions)}
        for pid in sorted(self.personas):
            fid = self.personas[pid].faction
            if fid is not None and fid in dist:
                dist[fid] += 1
        return dist

    def faction_territory_distribution(self) -> dict[str, list[str]]:
        """{faction_id: [territory_id, ...]} sorted."""
        result: dict[str, list[str]] = {fid: [] for fid in sorted(self.factions)}
        for tid in sorted(self.territories):
            ref = self.territories[tid].factionRef
            if ref is not None and ref in result:
                result[ref].append(tid)
        return result

    def faction_charter_primitives(self, faction_id: str) -> tuple[str, ...]:
        """Faction의 norm primitive."""
        if faction_id not in self.factions:
            raise KeyError(f"unknown faction_id: {faction_id!r}")
        return self.factions[faction_id].charter

    def factions_in_contact(self, radius: int = 1) -> list[tuple[str, str]]:
        """근접 Territory 간 서로 다른 factionRef 쌍."""
        if radius < 1:
            raise ValueError(f"radius must be >= 1, got {radius}")
        pairs: set[tuple[str, str]] = set()
        for tid in sorted(self.territories):
            ref_a = self.territories[tid].factionRef
            if ref_a is None:
                continue
            for nid in self._territories_within(tid, radius):
                if nid <= tid:
                    continue
                ref_b = self.territories[nid].factionRef
                if ref_b is None or ref_b == ref_a:
                    continue
                a, b = sorted((ref_a, ref_b))
                pairs.add((a, b))
        return sorted(pairs)

    def faction_wealth_distribution(self) -> dict[str, dict[str, float]]:
        """{faction_id: {'total', 'mean', 'gini', 'top_decile_share'}}."""
        self._rebuild_faction_members_cache()
        result: dict[str, dict[str, float]] = {}
        for fid in sorted(self.factions):
            members = self._faction_members(fid)
            if not members:
                result[fid] = {"total": 0.0, "mean": 0.0, "gini": 0.0, "top_decile_share": 0.0}
                continue
            gold_sorted = sorted(
                float(self.wallets[m.id].gold)
                for m in members
                if m.id in self.wallets and m.id in self.inners
            )
            n = len(gold_sorted)
            total = float(sum(gold_sorted))
            mean = total / n if n else 0.0
            if total > 0 and n:
                cum = sum(i * gold for i, gold in enumerate(gold_sorted, 1))
                gini = (2.0 * cum) / (n * total) - (n + 1) / n
                top_decile_n = max(1, n // 10)
                top_decile_share = sum(gold_sorted[-top_decile_n:]) / total
            else:
                gini = 0.0
                top_decile_share = 0.0
            result[fid] = {
                "total": total,
                "mean": mean,
                "gini": gini,
                "top_decile_share": top_decile_share,
            }
        return result

    def faction_social_matrix(self) -> dict[tuple[str, str], float]:
        """{(fid_a, fid_b): avg_trust}. sorted pair (a<b)."""
        self._rebuild_faction_members_cache()
        result: dict[tuple[str, str], float] = {}
        fids_sorted = sorted(self.factions)
        for i, fa in enumerate(fids_sorted):
            mem_a = [pa for pa in self._faction_members(fa) if pa.id in self.inners]
            if not mem_a:
                continue
            for fb in fids_sorted[i + 1:]:
                mem_b = [pb for pb in self._faction_members(fb) if pb.id in self.inners]
                if not mem_b:
                    continue
                trusts = [
                    self._get_relationship_trust(pa.id, pb.id)
                    for pa in mem_a
                    for pb in mem_b
                ]
                if trusts:
                    result[(fa, fb)] = sum(trusts) / len(trusts)
        return result

    def faction_grievance_targets(self) -> dict[str, dict[str, int]]:
        """{faction_id: {lord_id: member_count}}."""
        self._rebuild_faction_members_cache()
        result: dict[str, dict[str, int]] = {}
        for fid in sorted(self.factions):
            counts: dict[str, int] = {}
            for member in self._faction_members(fid):
                if member.id not in self.inners:
                    continue
                inner = self.inners[member.id]
                if inner.grievance >= GRIEVANCE_MIN_SHARED and inner.grievance_lord_id is not None:
                    counts[inner.grievance_lord_id] = counts.get(inner.grievance_lord_id, 0) + 1
            result[fid] = dict(sorted(counts.items()))
        return result

    def _derive_rng(self, *keys) -> np.random.Generator:
        """Per-call RNG stream derived deterministically from (seed, tick, keys).

        **The only allowed way** to create a sub-stream RNG inside
        MultiTickEngine. Direct `np.random.default_rng(...)` calls
        outside __init__ are forbidden (enforced by grep guard).

        Guarantees:
            - Identical across processes given identical (seed, tick, keys)
            - Different `keys` tuples yield independent streams (tag isolation)
            - Does NOT consume `self._np_rng` state (independent sub-stream)

        Args:
            *keys: Stable identifiers. First key should be a string tag
                   for stream namespacing ("forage", "job_seeking", ...).
                   Persona ids, territory ids, tick numbers all acceptable.

        Example:
            rng = self._derive_rng("forage", pid, self.time.tick)
            if rng.random() < prob: ...
        """
        seed_seq = np.random.SeedSequence([
            self._seed,
            _stable_int(*keys),
        ])
        return np.random.default_rng(seed_seq)

    def _try_exodus(self, pid: str) -> dict | None:
        """Guide-layer migration when grievance reaches the Phase 14 threshold."""
        persona = self.personas[pid]
        inner = self.inners[pid]
        if inner.grievance < 0.9 or inner.is_sleeping:
            return None
        if inner.exodus_cooldown_until_tick > self.time.tick:
            return None

        current_tid = persona.territory
        current_territory = self.territories.get(current_tid)
        if not current_territory:
            return None

        alternatives = [
            (tid, territory) for tid, territory in self.territories.items()
            if tid != current_tid
            and territory.policy.tax_rate < current_territory.policy.tax_rate * 0.7
        ]
        if not alternatives:
            if inner.grievance >= 0.9:
                inner.chronic_stress = min(1.0, inner.chronic_stress + 0.005)
                inner.chiljeong[1] = np.float16(min(1.0, float(inner.chiljeong[1]) + 0.05))
                inner.chiljeong[3] = np.float16(min(1.0, float(inner.chiljeong[3]) + 0.05))
                inner.exodus_cooldown_until_tick = self.time.tick + 48
                return {
                    "type": "exodus_blocked",
                    "persona": pid,
                    "territory": self.personas[pid].territory,
                    "reason": "no_alternatives",
                    "grievance": round(float(inner.grievance), 3),
                    "cooldown_until": inner.exodus_cooldown_until_tick,
                }
            return None

        exodus_roll = float(self._np_rng.random())
        if exodus_roll >= inner.grievance * 0.3:
            return None

        new_territory = min(alternatives, key=lambda item: item[1].policy.tax_rate)[1]
        new_tid = new_territory.id
        old_grievance = float(inner.grievance)
        change = self._change_persona_territory(pid, new_tid, reason="exodus")
        employment_cleanup = change["employment_cleanup"]
        inner.grievance = max(0.0, min(1.0, old_grievance * 0.5))

        event = {
            "type": "exodus",
            "persona": pid,
            "from_territory": current_tid,
            "to_territory": new_tid,
            "grievance": round(inner.grievance, 3),
        }
        if employment_cleanup:
            event["employment_cleanup"] = employment_cleanup
        return event

    def _update_grievances(self) -> list[dict]:
        """Update political grievance on the tax cadence."""
        if self.time.tick % 24 != 0:
            return []

        events = []
        for tid, territory in self.territories.items():
            lord_id = territory.lord_id
            if not lord_id or lord_id not in self.personas:
                continue

            tax_rate = territory.policy.tax_rate
            tax_burden = tax_rate / 0.30
            residents = self._get_territory_residents(tid)
            for pid in residents:
                if pid == lord_id:
                    continue

                inner = self.inners[pid]
                inner.grievance_lord_id = lord_id
                food = float(inner.inventory.get("food", 0))
                hunger = float(inner.oyok[0])

                delta = 0.0
                delta += (tax_burden - 0.5) * 0.03
                if food < 10:
                    delta += 0.02
                if hunger > 0.5:
                    delta += 0.03
                if food >= 20 and hunger < 0.3:
                    delta -= 0.02

                rel_key = Relationship(persona_a=pid, persona_b=lord_id).key()
                rel = self.relationships.get(rel_key)
                if rel and rel.trust < 0.3:
                    delta *= 1.5

                if delta > 0:
                    guard_count = self._get_territory_guard_active_count(tid)
                    residents_count = max(1, len(residents))
                    guard_ratio = min(1.0, guard_count / residents_count)
                    delta *= max(0.7, 1.0 - guard_ratio)

                inner.grievance = max(0.0, min(1.0, inner.grievance + delta))
                if inner.grievance > 0.3:
                    stress_gain = (inner.grievance - 0.3) * 0.007
                    inner.chronic_stress = min(1.0, inner.chronic_stress + stress_gain)

                if inner.grievance > 0.5:
                    dignity_drive = min(1.0, float(inner.oyok[4]) + (inner.grievance - 0.5) * 0.3)
                    inner.oyok[4] = np.float16(dignity_drive)

                    anger = min(1.0, float(inner.chiljeong[1]) + (inner.grievance - 0.5) * 0.2)
                    fear = min(1.0, float(inner.chiljeong[3]) + (inner.grievance - 0.5) * 0.1)
                    inner.chiljeong[1] = np.float16(anger)
                    inner.chiljeong[3] = np.float16(fear)

                if inner.grievance >= 0.8 and not inner.grievance_announced:
                    inner.grievance_announced = True
                    events.append({
                        "type": "grievance_critical",
                        "territory": tid,
                        "persona": pid,
                        "lord": lord_id,
                        "grievance": round(inner.grievance, 3),
                        "tax_burden": round(tax_burden, 3),
                    })
                elif inner.grievance < 0.6:
                    inner.grievance_announced = False

        updated = {}
        for tid_inner, territory in self.territories.items():
            lord_id = territory.lord_id
            residents = self._get_territory_residents(tid_inner)
            for pid in residents:
                if pid == lord_id:
                    continue
                inner = self.inners[pid]
                neighbors = self._get_community_members(pid, min_trust=0.4)
                if not neighbors:
                    continue
                neighbor_grievances = [
                    float(self.inners[n].grievance) for n in neighbors
                ]
                mean_neighbor = float(np.mean(neighbor_grievances))
                if mean_neighbor > inner.grievance:
                    updated[pid] = float(np.clip(
                        inner.grievance + (mean_neighbor - inner.grievance) * 0.1,
                        0.0,
                        1.0,
                    ))

        for pid, grievance in updated.items():
            self.inners[pid].grievance = grievance

        for tid_inner, territory in self.territories.items():
            lord_id = territory.lord_id
            residents = self._get_territory_residents(tid_inner)
            non_lord = [p for p in residents if p != lord_id]
            if len(non_lord) < 3:
                continue

            grievances = np.array(
                [float(self.inners[p].grievance) for p in non_lord],
                dtype=np.float32,
            )
            mean_g = float(grievances.mean())
            share_high = float((grievances >= 0.7).sum()) / len(grievances)
            if mean_g < 0.7 or share_high < 0.7:
                continue

            active_strike = any(
                self.inners[p].strike_until_tick > self.time.tick
                for p in non_lord
            )
            if active_strike:
                continue

            alternatives = [
                other_tid for other_tid, other_t in self.territories.items()
                if other_tid != tid_inner
                and other_t.policy.tax_rate < territory.policy.tax_rate * 0.7
            ]
            if alternatives:
                target_tid = min(
                    alternatives,
                    key=lambda t: self.territories[t].policy.tax_rate,
                )
                migrated = []
                for p in non_lord:
                    if float(self.inners[p].grievance) >= 0.7:
                        self._change_persona_territory(p, target_tid, reason="mass_exodus")
                        self.inners[p].grievance = 0.3
                        migrated.append(p)
                events.append({
                    "type": "mass_exodus",
                    "from_territory": tid_inner,
                    "to_territory": target_tid,
                    "personas": migrated,
                    "mean_grievance": round(mean_g, 3),
                    "share_high": round(share_high, 3),
                })
            else:
                strike_until = self.time.tick + 48
                struck = []
                for p in non_lord:
                    if float(self.inners[p].grievance) >= 0.7:
                        self.inners[p].strike_until_tick = strike_until
                        struck.append(p)
                for p in non_lord:
                    g = float(self.inners[p].grievance)
                    self.inners[p].grievance = max(0.0, g - 0.15)
                events.append({
                    "type": "strike",
                    "territory": tid_inner,
                    "personas": struck,
                    "until_tick": strike_until,
                    "mean_grievance": round(mean_g, 3),
                    "share_high": round(share_high, 3),
                })

        return events

    def _auto_economy_tick(self) -> list[dict]:
        """영주의 deliberation으로 일자리 생성 + 무직자 구직.

        영주(lord)가 영지 상태를 감지 → 필요한 직업을 창발적으로 생성.
        무직 페르소나가 구직 판정 → 적합한 일자리 수락.
        """
        events = []
        self._territory_residents_cache = None
        self._npc_food_price = float(NPC_PRICES["food"]["buy"])
        self._pricing_cache = {}
        if self.time.tick % DOMINANCE_RECALC_EVERY == 0:
            project_territory(self.world, list(self.personas.values()))
            self._territory_neighbors_cache = None
        for pid in self.personas:
            if self.inners[pid].is_sleeping:
                continue
            self._pricing_cache[pid] = {
                goods_type: self._compute_snn_pricing(pid, goods_type)
                for goods_type in ["food", "material", "tool", "medicine", "knowledge"]
            }

        if self.time.tick % 48 == 0:
            events.extend(self._update_governance_policy())

        events.extend(self._collect_taxes())
        events.extend(self._update_grievances())
        if self.time.tick % PUBLIC_WORKS_INTERVAL == 0:
            for tid in self.territories:
                events.extend(self._process_public_works(tid))
        events.extend(self._process_food_reserve())
        events.extend(self._process_farm_expansion())

        # ── Phase A: 영주가 영지 필요를 감지 → 일자리 생성 ──
        for tid, territory in self.territories.items():
            lord_id = territory.lord_id
            if not lord_id or lord_id not in self.personas:
                continue

            lord_inner = self.inners[lord_id]
            lord_persona = self.personas[lord_id]

            # 영주도 피곤하면 경영 안 함
            if lord_inner.is_sleeping or lord_inner.energy_pool < 0.3:
                continue

            # 영지 주민 상태 집계
            residents = self._get_territory_residents(tid)
            if not residents:
                continue

            avg_hunger = np.mean([float(self.inners[p].oyok[0]) for p in residents])
            avg_energy = np.mean([self.inners[p].energy_pool for p in residents])
            n_unemployed = sum(
                1 for p in residents
                if self.personas[p].employment_id is None and p != lord_id
            )
            existing_jobs = [
                j for j in self.jobs.values()
                if j.employer_id == lord_id and j.is_open
            ]
            existing_titles_list = [
                j.title for j in self.jobs.values()
                if j.employer_id == lord_id
            ]
            existing_titles = {j.title for j in self.jobs.values()
                               if j.employer_id == lord_id}

            # 금고 여유
            can_afford = territory.treasury_gold > 1000 and self.wallets[lord_id].will >= 5.0

            if not can_afford:
                continue

            # ── 필요 감지 → 직업 유형 결정 ──
            needs: list[tuple[str, float, str, float]] = []
            # (title, urgency, description, wage)

            # [SNN] 식량 정책 반영: food_priority 높으면 hunger 낮아도 farmer 생성
            food_urgency = 0.0
            food_policy = territory.policy.food_priority
            avg_food = float(np.mean([
                self.inners[p].inventory.get("food", 0) for p in residents
            ]))
            food_safety = len(residents) * 24
            territory_food = territory.food_reserve + avg_food * len(residents)

            if avg_hunger > 0.5:
                food_urgency = (avg_hunger - 0.3) * 2.0
            elif food_policy > 0.4:
                food_urgency = food_policy * 0.6
                if territory_food < food_safety:
                    food_urgency += 0.3

            farmer_count = sum(1 for title in existing_titles_list if title == "farmer")
            hunger_pressure = min(1.0, avg_hunger * 1.2)
            policy_pressure = food_policy
            dynamic_ratio = 0.15 + policy_pressure * 0.30 + hunger_pressure * 0.20
            max_farmers = max(1, int(round(len(residents) * dynamic_ratio)))
            max_farmers = min(max_farmers, max(1, int(len(residents) * 0.6)))
            if food_urgency > 0.05 and farmer_count < max_farmers:
                needs.append(("farmer", food_urgency,
                              "작물 재배 및 식량 공급", 6.0))

            # 에너지 위기 (주민 전체 피로)
            if avg_energy < 0.4 and "healer" not in existing_titles:
                urgency = (0.5 - avg_energy) * 2.0
                needs.append(("healer", urgency,
                              "주민 건강 관리 및 치료", 7.0))

            # 미고용 인력 활용 (일반 노동)
            if n_unemployed >= 2 and "laborer" not in existing_titles:
                needs.append(("laborer", 0.5,
                              "영지 유지보수 및 잡역", 4.0))

            # 지식 수요 (서적이 적음)
            local_records = sum(1 for r in self.knowledge_records
                                if r.territory_id == tid)
            if local_records < 3 and "scholar" not in existing_titles:
                needs.append(("scholar", 0.3,
                              "지식 수집 및 서적 작성", 5.0))

            # 시설 수요 → craftsman (인프라 유지/건설)
            if len(residents) >= 3 and "craftsman" not in existing_titles:
                needs.append(("craftsman", 0.4,
                              "시설 건설 및 도구 제작", 6.0))

            # 치안 수요 → guard (재난 빈번하거나 인구 증가)
            disaster_recent = any(
                log.get("disasters") for log in self.log[-48:]  # 최근 2일
            ) if self.log else False
            if (len(residents) >= 3 or disaster_recent) and "guard" not in existing_titles:
                needs.append(("guard", 0.35,
                              "영지 경비 및 재난 대응", 5.0))

            # ── 영주 Deliberation: 가장 급한 것만 1개 생성 ──
            if needs:
                # urgency 정렬
                needs.sort(key=lambda x: x[1], reverse=True)
                title, urgency, desc, wage = needs[0]

                # Deliberation 확률: urgency 높을수록 + V(Drive) tone 높을수록
                v_tone = float(lord_inner.tone[0])  # V(Drive/DA)
                d_tone = float(lord_inner.tone[10])  # D(Dominance/T)
                create_prob = min(0.8, urgency * 0.4 + (v_tone - 0.8) * 0.2
                                  + (d_tone - 0.8) * 0.15)
                create_prob = max(0.05, create_prob)

                rng = self._derive_rng("lord_job_create", lord_id, self.time.tick)
                if rng.random() < create_prob:
                    job = self.create_job(lord_id, title, wage, desc)
                    if job:
                        events.append({
                            "type": "job_created",
                            "lord": lord_id,
                            "territory": tid,
                            "job_title": title,
                            "wage": wage,
                            "urgency": round(urgency, 2),
                        })

        # ── Phase B: 무직 페르소나의 구직 ──
        open_jobs = [j for j in self.jobs.values() if j.is_open]
        if open_jobs:
            for pid, persona in self.personas.items():
                if persona.employment_id is not None:
                    continue  # 이미 고용됨
                inner = self.inners[pid]
                if inner.is_sleeping or inner.energy_pool < 0.3:
                    continue

                # 같은 영지의 열린 일자리만 고려
                local_jobs = [
                    j for j in open_jobs
                    if j.employer_id != pid  # 자기가 만든 건 제외
                    and self.personas.get(j.employer_id, persona).territory == persona.territory
                ]
                if not local_jobs:
                    continue

                # 구직 deliberation: 돈이 부족할수록 + 재욕(greed) 높을수록
                wallet = self.wallets.get(pid)
                financial_need = 0.0
                if wallet:
                    # gold 부족할수록 높음
                    financial_need = max(0, 1.0 - wallet.gold / 500)
                greed = float(inner.oyok[3])  # 재욕

                seek_prob = financial_need * 0.5 + greed * 0.2 + 0.1
                seek_prob = min(0.7, seek_prob)

                rng = self._derive_rng("job_seek", pid, self.time.tick)
                if rng.random() < seek_prob:
                    # 적성을 발견했으면 그걸 기반으로, 아니면 임금만 봄
                    def job_score(j):
                        if inner.discovered_aptitudes:
                            # 자기가 발견한 적성 기반 (불완전한 자기 인식)
                            apt = inner.discovered_aptitudes.get(j.title, 0.4)
                        else:
                            # 적성 미발견: 임금만 고려
                            apt = 0.5
                        if financial_need > 0.7:
                            return j.wage_per_tick  # 생존 우선
                        passion_w = 1.0 - financial_need
                        return j.wage_per_tick * 0.5 + apt * passion_w * 5.0
                    best_job = max(local_jobs, key=job_score)
                    emp = self.hire(best_job.id, pid)
                    if emp:
                        events.append({
                            "type": "hired",
                            "employee": pid,
                            "job_title": best_job.title,
                            "employer": best_job.employer_id,
                            "wage": best_job.wage_per_tick,
                        })

        # ── Phase 11: P2P 시장 + NPC 상점 + 도구 관리 ──
        market_events = self._process_market()
        events.extend(market_events)
        npc_events = self._process_npc_shop()
        events.extend(npc_events)
        for pid in self.personas:
            if not self.inners[pid].is_sleeping:
                tool_events = self._auto_tool_management(pid)
                events.extend(tool_events)

        self._commit_faction_tick()
        self._respawn_faction_tick()  # Stage 3 C: absorbing state 탈출
        self._project_faction_tick()
        self._pricing_cache = {}
        self._territory_residents_cache = None
        if self.time.tick > 0 and self.time.tick % QUARTER_TICKS == 0:
            for territory in self.territories.values():
                territory.quarter_tax_income = 0.0
                territory.quarter_public_spend = 0.0
        return events

    def _collect_taxes(self) -> list[dict]:
        """영주가 세금을 징수한다. 24틱마다."""
        if self.time.tick % 24 != 0:
            return []

        events = []
        for tid, territory in self.territories.items():
            lord_id = territory.lord_id
            if not lord_id or lord_id not in self.personas:
                continue

            lord_inner = self.inners[lord_id]
            if lord_inner.is_sleeping:
                continue

            tax_rate = max(0.05, min(0.30, territory.policy.tax_rate))
            territory.policy.tax_rate = tax_rate
            territory.tax_rate = tax_rate

            residents = [
                pid for pid in self._get_territory_residents(tid)
                if pid != lord_id
            ]

            total_collected = 0.0
            residents_taxed = 0
            for pid in residents:
                wallet = self.wallets.get(pid)
                if not wallet or wallet.gold < 10:
                    continue

                tax_amount = wallet.gold * tax_rate * (1 / 24)
                tax_amount = min(tax_amount, wallet.gold - 10)
                tax_amount = max(0.0, tax_amount)

                if tax_amount > 0.1 and wallet.pay(tax_amount):
                    territory.treasury_gold += tax_amount
                    territory.tax_collected_total += tax_amount
                    territory.quarter_tax_income += tax_amount
                    total_collected += tax_amount
                    residents_taxed += 1

            if total_collected > 0:
                events.append({
                    "type": "tax_collected",
                    "territory": tid,
                    "lord": lord_id,
                    "amount": round(total_collected, 2),
                    "tax_rate": round(tax_rate, 3),
                    "treasury_after": round(territory.treasury_gold, 1),
                    "residents_taxed": residents_taxed,
                })

        return events

    def _process_food_reserve(self) -> list[dict]:
        """영주가 영지 식량을 비축/배급한다. 24틱마다."""
        if self.time.tick % 24 != 0:
            return []

        events = []
        for tid, territory in self.territories.items():
            lord_id = territory.lord_id
            if not lord_id or lord_id not in self.personas:
                continue

            lord_inner = self.inners[lord_id]
            if lord_inner.is_sleeping:
                continue

            residents = self._get_territory_residents(tid)
            if not residents:
                continue

            start_idx = len(events)
            lord_food = float(lord_inner.inventory.get("food", 0))
            stockpile = territory.policy.stockpile_target

            personal_reserve = 30.0
            if lord_food > personal_reserve:
                transfer = (lord_food - personal_reserve) * stockpile
                if transfer >= 1:
                    lord_inner.inventory["food"] = lord_food - transfer
                    territory.food_reserve += transfer
                    events.append({
                        "type": "food_stockpile",
                        "territory": tid,
                        "lord": lord_id,
                        "amount": round(transfer, 2),
                        "reserve_after": round(territory.food_reserve, 1),
                        "source": "lord_inventory",
                    })

            reserve_target = len(residents) * FOOD_STOCKPILE_RESERVE_PER_PERSONA
            food_shortfall = reserve_target - territory.food_reserve
            cap = max(0.0, min(0.5, territory.policy.treasury_spending_cap))
            max_spend = min(
                territory.treasury_gold * cap,
                max(0.0, territory.treasury_gold - 500.0),
            )
            npc_food_price = float(getattr(
                self, "_npc_food_price", NPC_PRICES["food"]["buy"]
            ))

            if food_shortfall >= 1 and max_spend >= 1:
                internal_target = min(
                    food_shortfall,
                    max_spend / max(1.0, npc_food_price * INTERNAL_FOOD_PRICE_RATIO),
                )
                if internal_target >= 1:
                    _procured, ip_events = self._process_internal_food_procurement(
                        tid, internal_target
                    )
                    events.extend(ip_events)
                    food_shortfall = reserve_target - territory.food_reserve

            has_market_food_order = any(
                getattr(order, "goods_type", None) == "food"
                and getattr(order, "territory_id", None) == tid
                and getattr(order, "quantity", 0) > 0
                for order in getattr(self, "market_orders", [])
            )

            max_spend = min(
                territory.treasury_gold * cap,
                max(0.0, territory.treasury_gold - 500.0),
            )
            priority_ok = territory.policy.food_priority > 0.4
            cooldown_ok = (
                self.time.tick - territory.last_npc_food_purchase_tick
                >= NPC_FOOD_PURCHASE_COOLDOWN_TICKS
            )
            ratio_threshold = reserve_target * NPC_FOOD_TRIGGER_RESERVE_RATIO
            ratio_ok = territory.food_reserve < ratio_threshold

            npc_needed = (
                food_shortfall >= 1
                and priority_ok
                and cooldown_ok
                and ratio_ok
                and not has_market_food_order
                and max_spend >= npc_food_price
            )
            if npc_needed:
                npc_target = min(
                    max(0.0, ratio_threshold - territory.food_reserve),
                    max_spend / npc_food_price,
                )
                buy_qty = float(int(min(npc_target, max_spend / npc_food_price)))
                cost = buy_qty * npc_food_price
                if buy_qty >= 1 and cost <= territory.treasury_gold:
                    territory.treasury_gold -= cost
                    territory.food_reserve += buy_qty
                    territory.last_npc_food_purchase_tick = self.time.tick
                    events.append({
                        "type": "food_stockpile",
                        "territory": tid,
                        "lord": lord_id,
                        "amount": round(buy_qty, 2),
                        "reserve_after": round(territory.food_reserve, 1),
                        "source": "treasury_purchase",
                        "treasury_spent": round(cost, 1),
                        "spending_cap": round(max_spend, 1),
                        "reserve_target": round(reserve_target, 1),
                        "trigger_ratio": round(
                            territory.food_reserve / max(1.0, reserve_target), 3
                        ),
                    })
                    territory.food_crisis_counter += 1.0
            elif (
                food_shortfall >= 1
                and priority_ok
                and not cooldown_ok
                and max_spend >= npc_food_price
            ):
                events.append({
                    "type": "npc_food_purchase_cooldown_skip",
                    "territory": tid,
                    "ticks_since_last": self.time.tick - territory.last_npc_food_purchase_tick,
                    "required": NPC_FOOD_PURCHASE_COOLDOWN_TICKS,
                })

            for pid in residents:
                if pid == lord_id:
                    continue
                inner = self.inners[pid]
                food = float(inner.inventory.get("food", 0))
                if food < 5 and territory.food_reserve >= 3:
                    ration = min(5.0, territory.food_reserve)
                    inner.inventory["food"] = food + ration
                    territory.food_reserve -= ration
                    events.append({
                        "type": "food_ration",
                        "territory": tid,
                        "lord": lord_id,
                        "recipient": pid,
                        "amount": round(ration, 2),
                        "reserve_after": round(territory.food_reserve, 1),
                    })

            npc_buy_happened = any(
                e.get("type") == "food_stockpile"
                and e.get("source") == "treasury_purchase"
                for e in events[start_idx:]
            )
            if not npc_buy_happened:
                territory.food_crisis_counter = max(
                    0.0, territory.food_crisis_counter - FOOD_CRISIS_COUNTER_DECAY
                )

        return events

    def _process_farm_expansion(self) -> list[dict]:
        """Phase 16-E: food_crisis_counter >= threshold 시 farm 자동 확장."""
        if self.time.tick % 24 != 0:
            return []

        events: list[dict] = []
        for tid, territory in self.territories.items():
            if territory.food_crisis_counter < FOOD_CRISIS_FARM_THRESHOLD:
                continue
            if territory.treasury_gold < FARM_EXPANSION_COST_GOLD:
                events.append({
                    "type": "farm_expansion_skip",
                    "tick": self.time.tick,
                    "territory": tid,
                    "reason": "treasury_insufficient",
                    "required": FARM_EXPANSION_COST_GOLD,
                    "have": round(territory.treasury_gold, 1),
                })
                continue

            territory.treasury_gold -= FARM_EXPANSION_COST_GOLD
            territory.communal_farms += 1
            territory.food_crisis_counter = 0.0
            events.append({
                "type": "farm_expansion",
                "tick": self.time.tick,
                "territory": tid,
                "cost": FARM_EXPANSION_COST_GOLD,
                "communal_farms_after": territory.communal_farms,
                "treasury_after": round(territory.treasury_gold, 1),
            })

        return events

    def _update_governance_policy(self) -> list[dict]:
        """[SNN] 영주 뇌 발화율에서 통치 정책을 도출한다. 48틱마다."""
        events = []
        for tid, territory in self.territories.items():
            lord_id = territory.lord_id
            if not lord_id or lord_id not in self.personas:
                continue

            inner = self.inners[lord_id]
            if inner.is_sleeping:
                continue

            brain = self.brains.get(lord_id)
            fr = getattr(brain, "_last_firing_rate", None) if brain else None
            if fr is None or len(fr) < 12:
                continue

            fr = np.asarray(fr, dtype=np.float32)
            policy = territory.policy
            first_update = policy.last_updated_tick == 0
            old_tax = policy.tax_rate
            old_food = policy.food_priority
            old_stockpile = policy.stockpile_target
            old_cap = policy.treasury_spending_cap
            old_openness = policy.market_openness

            clusters = np.array_split(fr, 12)

            def cluster_signal(index: int) -> float:
                return float(np.clip(float(clusters[index].mean()) * 10.0, 0.0, 1.0))

            drive = cluster_signal(0)
            tension = cluster_signal(5)
            residents = self._get_territory_residents(tid)
            resident_grievances = [
                float(self.inners[p].grievance)
                for p in residents
                if p != lord_id
            ]
            avg_grievance = (
                float(np.mean(resident_grievances))
                if resident_grievances else 0.0
            )
            tension = float(np.clip(tension + avg_grievance * 0.5, 0.0, 1.0))
            stability = cluster_signal(2)
            if len(territory.chronicle) >= 5:
                stability = min(1.0, stability + 0.05)
            dominance = cluster_signal(10)
            growth = cluster_signal(7)
            greed = float(inner.oyok[3])

            tax_target = (
                0.10 + tension * 0.05 + dominance * 0.03
                - stability * 0.02 + greed * 0.04
            )
            tax_target = max(0.05, min(0.30, tax_target))
            policy.tax_rate += (tax_target - policy.tax_rate) * 0.3
            policy.tax_rate = round(max(0.05, min(0.30, policy.tax_rate)), 3)

            food_signal = 0.0
            if len(fr) >= 350:
                food_signal = float(np.clip(float(fr[300:310].mean()) * 10.0, 0.0, 1.0))
            policy.food_priority = min(1.0, food_signal + tension * 0.3 + drive * 0.2)

            policy.stockpile_target = min(1.0, max(
                0.0,
                0.3 + stability * 0.3 + greed * 0.2 - drive * 0.2 - growth * 0.1,
            ))

            policy.treasury_spending_cap = min(0.5, max(
                0.1,
                0.2 + growth * 0.15 + drive * 0.1 - stability * 0.05,
            ))

            # ── Phase 15-A: market_openness 창발 ──
            density_ratio = 0.0
            for m in self._last_community_metrics:
                if m.territory_id == tid:
                    density_ratio = float(m.density_ratio)
                    break
            density_pressure = max(0.0, min(1.0, (density_ratio - 0.3) * 2.5))

            openness_target = (
                0.5
                + growth * 0.25
                + stability * 0.15
                - tension * 0.25
                - density_pressure * 0.3
            )
            openness_target = max(0.0, min(1.0, openness_target))
            policy.market_openness += (openness_target - policy.market_openness) * 0.3
            policy.market_openness = round(
                max(0.0, min(1.0, policy.market_openness)), 3
            )

            policy.last_updated_tick = self.time.tick
            territory.tax_rate = policy.tax_rate
            snn_signals = {
                "drive": float(drive),
                "tension": float(tension),
                "stability": float(stability),
                "dominance": float(dominance),
                "growth": float(growth),
                "greed": float(greed),
                "density_pressure": float(density_pressure),
            }
            territory.last_snn_signals = dict(snn_signals)
            territory.last_snn_signals_tick = self.time.tick

            changed = (
                abs(policy.tax_rate - old_tax) > 0.005
                or abs(policy.food_priority - old_food) > 0.005
                or abs(policy.stockpile_target - old_stockpile) > 0.005
                or abs(policy.treasury_spending_cap - old_cap) > 0.005
                or abs(policy.market_openness - old_openness) > 0.005
            )
            if first_update or changed:
                events.append({
                    "type": "policy_update",
                    "territory": tid,
                    "lord": lord_id,
                    "tax_rate": policy.tax_rate,
                    "food_priority": round(policy.food_priority, 3),
                    "stockpile_target": round(policy.stockpile_target, 3),
                    "spending_cap": round(policy.treasury_spending_cap, 3),
                    "market_openness": round(policy.market_openness, 3),
                    "density_ratio": round(density_ratio, 4),
                    "snn_signals": {
                        key: round(value, 3)
                        for key, value in snn_signals.items()
                    },
                })

        return events

    def _build_economic_state(self, pid: str) -> dict:
        """Phase 12: 경제 상태를 PersonaBrain 입력용 연속 신호로 조립한다."""
        persona = self.personas[pid]
        inner = self.inners[pid]
        wallet = self.wallets.get(pid)

        territory_pids = [
            other_pid for other_pid, other in self.personas.items()
            if other.territory == persona.territory
        ]
        territory_gold = [
            self.wallets[other_pid].gold
            for other_pid in territory_pids
            if other_pid in self.wallets
        ]
        avg_gold = float(np.mean(territory_gold)) if territory_gold else 1.0

        work_rewards = self._work_reward_history.get(pid, [])[-30:]
        if work_rewards:
            # reward [-1, 1]을 만족도 [0, 1]로 변환한다.
            job_satisfaction = float(np.clip(0.5 + np.mean(work_rewards) * 0.5, 0.0, 1.0))
        else:
            job_satisfaction = 0.5

        gold = wallet.gold if wallet else 0.0
        territory = self.territories.get(persona.territory)
        tax_burden = 0.0
        if territory:
            tax_burden = max(0.0, min(1.0, territory.policy.tax_rate / 0.30))
        grievance = float(inner.grievance)
        trust_to_lord = 0.5
        lord_id = territory.lord_id if territory else None
        if lord_id and lord_id != pid:
            rel_key = Relationship(persona_a=pid, persona_b=lord_id).key()
            rel = self.relationships.get(rel_key)
            if rel:
                trust_to_lord = float(rel.trust)
        return {
            "food_ratio": inner.inventory.get("food", 0) / 30.0,
            "tool_ratio": (inner.equipped_tool_durability or 0) / TOOL_MAX_DURABILITY,
            "wealth_ratio": (gold / 2000.0) if wallet else 0.5,
            "job_satisfaction": job_satisfaction,
            "relative_wealth": (gold / max(1.0, avg_gold)) if wallet else 1.0,
            "tax_burden": tax_burden,
            "grievance": grievance,
            "trust_to_lord": trust_to_lord,
        }

    def _process_interaction(self, pid_a: str, pid_b: str, mutual: bool = True) -> dict:
        """두 페르소나 간 상호작용 처리."""
        rel = self._ensure_relationship(pid_a, pid_b)

        inner_a = self.inners[pid_a]
        inner_b = self.inners[pid_b]

        # 친밀도 증가 (만남 횟수에 따라 감쇠 — 처음 만남이 가장 큰 영향)
        familiarity_gain = 0.05 / (1 + rel.interaction_count * 0.1)
        rel.familiarity = min(1.0, rel.familiarity + familiarity_gain)
        rel.interaction_count += 1
        rel.last_interaction_tick = self.time.tick

        # 감정 전이 (공감): 상대의 감정이 약간 전이
        if mutual:
            blend = 0.1  # 10% 블렌딩
            a_emo = inner_a.chiljeong.copy()
            b_emo = inner_b.chiljeong.copy()
            inner_a.chiljeong = (inner_a.chiljeong * (1 - blend) + b_emo * blend).astype(np.float16)
            inner_b.chiljeong = (inner_b.chiljeong * (1 - blend) + a_emo * blend).astype(np.float16)
            # 사랑(love) 감정 약간 증가 (유대감)
            inner_a.chiljeong[4] = min(1.0, inner_a.chiljeong[4] + 0.05)
            inner_b.chiljeong[4] = min(1.0, inner_b.chiljeong[4] + 0.05)
        else:
            # 단방향: a만 영향 받음
            blend = 0.05
            inner_a.chiljeong = (
                inner_a.chiljeong * (1 - blend) + inner_b.chiljeong * blend
            ).astype(np.float16)
            inner_a.chiljeong[4] = min(1.0, inner_a.chiljeong[4] + 0.03)

        # 신뢰 변화 (감정 유사도에 비례)
        emo_similarity = 1.0 - float(np.abs(inner_a.chiljeong - inner_b.chiljeong).mean())
        trust_delta = (emo_similarity - 0.5) * 0.02  # 유사하면 +, 다르면 -
        # class 권위 보너스: 높은 class일수록 신뢰 형성 가속
        class_a = self.personas[pid_a].persona_class
        class_b = self.personas[pid_b].persona_class
        trust_delta += (max(class_a, class_b) - 1) * 0.005
        rel.trust = np.clip(rel.trust + trust_delta, 0.0, 1.0)

        # 비밀 공유 판정 (친밀도 0.5 이상 + 신뢰 0.6 이상)
        secret_shared = None
        if rel.familiarity > 0.5 and rel.trust > 0.6:
            for pid in [pid_a, pid_b]:
                secret = self.secrets[pid]
                other = pid_b if pid == pid_a else pid_a
                if other not in secret.known_by:
                    share_prob = (rel.familiarity - 0.5) * float(rel.trust)
                    if self._np_rng.random() < share_prob:
                        secret.known_by.add(other)
                        secret.revealed_tick = self.time.tick
                        secret_shared = {
                            "owner": pid,
                            "tag": secret.content_tag,
                            "revealed_to": other,
                        }
                        # 비밀 → 소문 생성 (원본 정확도 1.0)
                        rumor = Rumor(
                            source_secret_owner=pid,
                            content_tag=secret.content_tag,
                            accuracy=1.0,
                            origin_tick=self.time.tick,
                            known_by={pid, other},
                            about_id=pid,
                        )
                        self.rumors.append(rumor)
                        break

        # ── 소문 전파 (기존 소문을 상대에게 전달) ──
        rumor_spread = None
        if rel.familiarity > 0.3:
            for rumor in self.rumors:
                # 한쪽만 알고 상대는 모르는 소문이 있으면 전파
                a_knows = pid_a in rumor.known_by
                b_knows = pid_b in rumor.known_by
                if a_knows and not b_knows:
                    spreader, receiver = pid_a, pid_b
                elif b_knows and not a_knows:
                    spreader, receiver = pid_b, pid_a
                else:
                    continue
                # 전파 확률: 친밀도 × (1 - 정확도 감쇠 고려) × 자극성
                spread_prob = rel.familiarity * 0.3 * rumor.accuracy
                if self._np_rng.random() < spread_prob:
                    rumor.known_by.add(receiver)
                    old_acc = rumor.accuracy
                    new_acc = rumor.distort()  # 전화기 효과
                    rumor_spread = {
                        "about": rumor.about_id,
                        "tag": rumor.content_tag,
                        "from": spreader,
                        "to": receiver,
                        "accuracy": round(new_acc, 3),
                        "spread_count": rumor.spread_count,
                    }

                    # ── 식물 지식 소문 수신 → food_knowledge 업데이트 ──
                    tag = rumor.content_tag
                    if tag.startswith("good_food_") or tag.startswith("bad_food_"):
                        food_id = tag.replace("good_food_", "").replace("bad_food_", "")
                        is_good = tag.startswith("good_food_")
                        receiver_inner = self.inners.get(receiver)
                        if receiver_inner:
                            k = receiver_inner.food_knowledge.get(food_id, {
                                "tries": 0, "total_energy": 0.0,
                                "avg_energy_delta": 0.0, "is_good": None, "certainty": 0.0,
                            })
                            # 소문 정확도 × 신뢰도 만큼 certainty 상승
                            # 직접 경험보다는 낮음 (간접 지식)
                            certainty_gain = new_acc * 0.15 * rel.trust
                            k["certainty"] = min(1.0, k.get("certainty", 0) + certainty_gain)
                            if k["certainty"] >= 0.4:  # 소문은 0.4부터 판단 (직접보다 낮음)
                                k["is_good"] = is_good
                            k["source"] = "rumor"
                            receiver_inner.food_knowledge[food_id] = k
                    # ── 확증 편향: 정확도 낮은 소문은 감정에 따라 왜곡 해석 ──
                    # 소문 정확도 < 50% → 수신자의 기존 감정/관계가 해석을 지배
                    # "듣고 싶은 것을 듣는다"
                    receiver_inner = self.inners.get(receiver)
                    interpreted_tag = rumor.content_tag
                    bias_applied = False

                    if new_acc < 0.5 and receiver_inner:
                        # 수신자의 대상에 대한 기존 감정
                        about_rel_key_bias = Relationship(
                            persona_a=receiver, persona_b=rumor.about_id
                        ).key()
                        existing_rel = self.relationships.get(about_rel_key_bias)
                        existing_trust = existing_rel.trust if existing_rel else 0.5

                        # 수신자의 현재 감정 상태
                        anger = float(receiver_inner.chiljeong[1])
                        fear = float(receiver_inner.chiljeong[3])
                        joy = float(receiver_inner.chiljeong[0])

                        # 부정적 감정 우세 + 낮은 신뢰 → 부정적으로 왜곡
                        neg_bias = (anger + fear) * 0.5 + (1.0 - existing_trust) * 0.3
                        pos_bias = joy * 0.5 + existing_trust * 0.3

                        if neg_bias > pos_bias + 0.2:
                            # 부정적 왜곡: ambition→"위험한 야심", skill→무시
                            if rumor.content_tag in ("ambition", "skill"):
                                interpreted_tag = "suspicious_" + rumor.content_tag
                                bias_applied = True
                        elif pos_bias > neg_bias + 0.2:
                            # 긍정적 왜곡: weakness→"겸손", past→"성장"
                            if rumor.content_tag in ("weakness", "past"):
                                interpreted_tag = "sympathetic_" + rumor.content_tag
                                bias_applied = True

                    if bias_applied:
                        rumor_spread["bias"] = interpreted_tag

                    # 소문이 대상에 대한 신뢰에 영향
                    about_rel_key = Relationship(
                        persona_a=receiver, persona_b=rumor.about_id
                    ).key()
                    if about_rel_key in self.relationships:
                        about_rel = self.relationships[about_rel_key]

                        # 확증 편향 반영: 왜곡된 해석이 신뢰에 영향
                        if interpreted_tag.startswith("suspicious_"):
                            # 의심스러운 해석 → 신뢰 더 큰 하락
                            about_rel.trust = max(0, about_rel.trust - 0.05 * new_acc)
                        elif interpreted_tag.startswith("sympathetic_"):
                            # 동정적 해석 → 신뢰 상승 (부정적 소문인데 오히려!)
                            about_rel.trust = min(1, about_rel.trust + 0.02 * new_acc)
                        elif rumor.content_tag in ("weakness", "past"):
                            about_rel.trust = max(0, about_rel.trust - 0.03 * new_acc)
                        elif rumor.content_tag in ("ambition", "skill"):
                            about_rel.trust = min(1, about_rel.trust + 0.02 * new_acc)
                    break  # 1틱 1소문까지

        # ── 지식 전수 (창발적 교육) ──────────────────────────
        # 숙련자와 미숙련자가 만나면 자연스럽게 가르침이 발생한다.
        # 조건: 한쪽 mastery > 0.2, 다른쪽 mastery < 그 절반, 신뢰 > 0.3
        # Academy가 있으면 전수 효율 1.5배.
        # 교사의 성격(협조+외향)이 전수 확률과 질에 영향.
        teaching = None
        if rel.trust > 0.3:
            territory_a = self.territories.get(self.personas[pid_a].territory)
            has_academy = territory_a and territory_a.get_facility("academy")
            academy_mult = 1.5 if has_academy else 1.0

            for teacher_id, student_id in [(pid_a, pid_b), (pid_b, pid_a)]:
                teacher_inner = self.inners[teacher_id]
                student_inner = self.inners[student_id]
                teacher_persona = self.personas[teacher_id]

                for skill_id, sp in teacher_inner.skill_profiles.items():
                    if sp.mastery < 0.2:
                        continue  # 가르칠 수준 안 됨

                    student_sp = student_inner.skill_profiles.get(skill_id)
                    student_mastery = student_sp.mastery if student_sp else 0.0

                    if student_mastery >= sp.mastery * 0.7:
                        continue  # 학생이 이미 충분히 앎

                    # 교사 성격: 협조(p[3]) + 외향(p[0]) → 기본 의지
                    p = teacher_persona.personality
                    personality_will = 0.3 + float(p[3]) * 0.2 + float(p[0]) * 0.15

                    # Neural Drive: 축적된 숙달+도파민+몰입이 성격 장벽을 넘는다
                    teacher_drive = self._compute_neural_drive(teacher_id, sp.skill_id)
                    drive_will = teacher_drive * sp.mastery * 0.6

                    teach_will = max(0.1, min(0.9, personality_will + drive_will))

                    # 전수 확률: 가르침 의지 × 신뢰 × 친밀도 × class 권위
                    teacher_class = self.personas[teacher_id].persona_class
                    teach_prob = teach_will * rel.trust * rel.familiarity
                    teach_prob *= (1.0 + (teacher_class - 1) * 0.15)
                    if self._np_rng.random() > teach_prob:
                        continue

                    # 전수 실행
                    if student_sp is None:
                        student_sp = SkillProfile(
                            persona_id=student_id, skill_id=skill_id
                        )
                        student_inner.skill_profiles[skill_id] = student_sp

                    # 전수량: 교사 mastery의 일부 → 학생에게
                    # 학생 적성과 집중이 수신 효율에 영향
                    student_apt = self.personas[student_id].aptitude_map.get(skill_id, 0.5)
                    student_conc = compute_concentration(student_inner.tone, student_inner.energy_pool)
                    transfer = sp.mastery * 0.02 * student_apt * max(0.3, student_conc) * academy_mult

                    ceiling = SKILL_CEILINGS.get(skill_id, (0.5, 0.5, 0.005))[0]
                    student_sp.mastery = min(ceiling, student_sp.mastery + transfer)
                    student_sp.total_ticks += 1
                    student_sp.last_tick = self.time.tick

                    # 학생: 이 직업의 적성을 체험으로 발견
                    # joy 반응 → discovered_aptitudes 업데이트
                    true_apt = self.personas[student_id].aptitude_map.get(skill_id, 0.5)
                    rng_apt = self._derive_rng("aptitude", student_id, self.time.tick)
                    noise = rng_apt.uniform(-0.15, 0.15)
                    perceived = max(0.2, min(1.0, true_apt + noise))
                    # 기존 발견과 평균 (경험이 쌓일수록 정확해짐)
                    if skill_id in student_inner.discovered_aptitudes:
                        old = student_inner.discovered_aptitudes[skill_id]
                        student_inner.discovered_aptitudes[skill_id] = old * 0.7 + perceived * 0.3
                    else:
                        student_inner.discovered_aptitudes[skill_id] = perceived

                    teaching = {
                        "teacher": teacher_id,
                        "student": student_id,
                        "skill": skill_id,
                        "transfer": round(transfer, 4),
                        "student_mastery": round(student_sp.mastery, 4),
                        "academy": has_academy,
                    }
                    # 가르침 → 승급 기여도 (2x credit) + 신뢰 보너스
                    teacher_inner = self.inners[teacher_id]
                    teacher_inner.promotion_contrib_window.append(transfer * 2.0)
                    if len(teacher_inner.promotion_contrib_window) > 500:
                        teacher_inner.promotion_contrib_window = teacher_inner.promotion_contrib_window[-500:]
                    rel.trust = min(1.0, rel.trust + 0.02)
                    break  # 1회 만남에 1건 전수
                if teaching:
                    break

        return {
            "participants": [pid_a, pid_b],
            "mutual": mutual,
            "familiarity": round(rel.familiarity, 3),
            "trust": round(rel.trust, 3),
            "secret_shared": secret_shared,
            "rumor_spread": rumor_spread,
            "teaching": teaching,
        }

    # ══════════════════════════════════════════════════════════
    # C7: 기후→게임플레이 영향 매트릭스
    # ══════════════════════════════════════════════════════════

    def _get_shelter(self, pid: str, action: str) -> float:
        """행동에 따른 shelter 보호 수준 (0~1)."""
        territory_id = self.personas[pid].territory
        territory = self.territories.get(territory_id)
        if not territory:
            return 0.0

        # 실내 행동: eat, sleep, idle → housing shelter
        # 사교: socialize → tavern shelter
        # 야외 행동: work, explore → 0 (야외)
        if action in ("eat", "sleep", "idle"):
            housing = territory.get_facility("housing")
            return housing.shelter_warmth if housing else 0.0
        elif action == "socialize":
            tavern = territory.get_facility("tavern")
            return tavern.shelter_warmth if tavern else 0.0
        else:
            return 0.0  # work, explore = 야외

    def _apply_weather_emotion(self, inner: InnerWorld, weather: dict, shelter: float = 0.0):
        """기후→감정 매트릭스. shelter가 높으면 기후 영향 감소."""
        temp = weather.get("temperature_c", 15)
        feels = weather.get("feels_like_c", temp)
        precip = weather.get("precipitation_mm", 0)
        wind = weather.get("wind_speed_ms", 3)
        disaster = weather.get("disaster_signal", 0)

        # shelter 보호 + 습관화: 둘 다 감정 영향을 줄임
        h = inner.habituation
        exposure = 1.0 - shelter  # 0=완벽 보호, 1=완전 노출
        # 습관화 감쇠: 추위/더위에 익숙해지면 fear/anger 자극 감소
        cold_sensitivity = max(0.1, 1.0 - h["cold"] * 0.85)   # 완전 습관화 시 15%만 반응
        heat_sensitivity = max(0.1, 1.0 - h["heat"] * 0.85)

        # 극한 추위 → fear + anger (shelter + 습관화로 감소)
        if feels < -5:
            inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + 0.08 * exposure * cold_sensitivity)
            inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + 0.05 * exposure * cold_sensitivity)
        elif feels < 5:
            inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + 0.03 * exposure * cold_sensitivity)

        # 극한 더위 → anger + desire
        if feels > 35:
            inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + 0.06 * exposure * heat_sensitivity)
            inner.chiljeong[6] = min(1.0, inner.chiljeong[6] + 0.05 * exposure * heat_sensitivity)
        elif feels > 28:
            inner.chiljeong[6] = min(1.0, inner.chiljeong[6] + 0.02 * exposure * heat_sensitivity)

        # 비 → sadness, 폭우 → fear
        if precip > 10:
            inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + 0.05 * exposure)
            inner.chiljeong[2] = min(1.0, inner.chiljeong[2] + 0.05 * exposure)
        elif precip > 0:
            inner.chiljeong[2] = min(1.0, inner.chiljeong[2] + 0.02 * exposure)

        # 쾌적한 날씨 → joy
        if 15 < feels < 25 and precip == 0 and wind < 8:
            inner.chiljeong[0] = min(1.0, inner.chiljeong[0] + 0.05)  # joy

        # 재난 전조 → fear (공포)
        if disaster > 0.3:
            inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + min(disaster * 0.15, 0.08))  # fear (상한 클램핑)

        inner.chiljeong = np.clip(inner.chiljeong, -1.0, 1.0)

    def _weather_cost_multiplier(self, weather: dict, action: str, shelter: float = 0.0) -> float:
        """기후→행동 비용 보정. shelter이 높으면 페널티 감소."""
        mult = 1.0
        feels = weather.get("feels_like_c", 15)
        precip = weather.get("precipitation_mm", 0)
        wind = weather.get("wind_speed_ms", 3)
        exposure = 1.0 - shelter  # shelter 보호 비율

        # 극한 기온 → 야외 행동 비용 증가 (shelter로 상쇄)
        if feels < -5 or feels > 35:
            if action in ("work", "explore", "socialize"):
                mult += 0.5 * exposure
        elif feels < 5 or feels > 30:
            if action in ("work", "explore"):
                mult += 0.2 * exposure

        # 비 → 야외 행동 비용 증가
        if precip > 5:
            if action in ("work", "explore", "socialize"):
                mult += 0.3 * exposure
        elif precip > 0:
            if action in ("explore",):
                mult += 0.1 * exposure

        # 강풍 → 이동/탐험 비용 증가
        if wind > 12:
            if action in ("explore", "socialize"):
                mult += 0.3 * exposure

        # 실내 행동은 날씨 무관
        if action in ("eat", "sleep", "idle"):
            mult = 1.0

        return min(mult, 1.8)

    # ══════════════════════════════════════════════════════════
    # 숙달 & 집중 시스템
    # ══════════════════════════════════════════════════════════

    def _get_persona_job_title(self, pid: str) -> str:
        """현재 고용된 직업 제목. 미고용이면 숙달 > 적성 기반."""
        persona = self.personas[pid]
        if persona.employment_id and persona.employment_id in self.employments:
            emp = self.employments[persona.employment_id]
            job = self.jobs.get(emp.job_id)
            if job:
                return job.title
        # 자영: 가장 숙달된 스킬 우선
        inner = self.inners[pid]
        if inner.skill_profiles:
            best = max(inner.skill_profiles.items(), key=lambda x: x[1].mastery)
            if best[1].mastery > 0:
                return best[0]
        # 숙달 없으면 적성 기반
        if hasattr(persona, 'aptitude_map') and persona.aptitude_map:
            best_apt = max(persona.aptitude_map.items(), key=lambda x: x[1])
            return best_apt[0]
        return "laborer"

    def _apply_job_speciality(self, pid: str, job_title: str) -> None:
        """Phase 15-C: apply healer/scholar work-time effects."""
        if job_title == "healer":
            members = self._get_community_members(pid, min_trust=0.4)
            for member_pid in members:
                member_inner = self.inners.get(member_pid)
                if member_inner and not member_inner.is_sleeping:
                    member_inner.chronic_stress = max(
                        0.0,
                        member_inner.chronic_stress - 0.002,
                    )
            return

        if job_title == "scholar":
            persona = self.personas[pid]
            territory = self.territories.get(persona.territory)
            if territory is None:
                return
            summary = self._summarize_recent_events(persona.territory)
            if summary is None:
                return
            territory.chronicle.append({
                "tick": self.time.tick,
                "type": summary["type"],
                "summary": summary["text"],
            })
            if len(territory.chronicle) > 100:
                territory.chronicle = territory.chronicle[-100:]

    def _summarize_recent_events(self, territory_id: str) -> dict | None:
        """Summarize major events for a territory from the latest 24 tick logs."""
        if not self.log:
            return None

        strike_count = 0
        grievance_spikes = 0
        policy_changed = False
        for tick_result in self.log[-24:]:
            for event in tick_result.get("economy_events", []):
                if event.get("territory") != territory_id:
                    continue
                event_type = event.get("type")
                if event_type in ("strike_executed", "strike"):
                    strike_count += 1
                elif event_type in ("grievance_spike", "grievance_critical"):
                    grievance_spikes += 1
                elif event_type == "policy_update":
                    policy_changed = True

        if strike_count > 0:
            return {"type": "strike", "text": f"strikes={strike_count}"}
        if grievance_spikes > 0:
            return {"type": "grievance_spike", "text": f"spikes={grievance_spikes}"}
        if policy_changed:
            return {"type": "policy_shift", "text": "policy_updated"}
        return None

    def _update_mastery_tick(self, pid: str) -> dict:
        """work 행동 시 숙달 업데이트. 집중도, 몰입, 번아웃 처리."""
        inner = self.inners[pid]
        persona = self.personas[pid]
        job_title = self._get_persona_job_title(pid)

        # 집중도 계산 (7개 화학물질 동시 조건)
        concentration = compute_concentration(inner.tone, inner.energy_pool)
        inner.concentration_cache = concentration

        # 적성
        aptitude = persona.aptitude_map.get(job_title, 0.5)

        # SkillProfile 가져오기 or 생성
        if job_title not in inner.skill_profiles:
            inner.skill_profiles[job_title] = SkillProfile(
                persona_id=pid, skill_id=job_title
            )
        sp = inner.skill_profiles[job_title]

        # 연속 작업 판정
        if sp.last_tick == self.time.tick - 1:
            sp.consecutive_ticks += 1
        else:
            sp.consecutive_ticks = 1
        sp.last_tick = self.time.tick
        sp.total_ticks += 1

        # 번아웃 업데이트
        joy = float(inner.chiljeong[0])
        alignment_score = aptitude * 0.4 + joy * 0.3 + concentration * 0.3
        if alignment_score < 0.3:
            sp.burnout_accumulator = min(1.0, sp.burnout_accumulator + 0.01)
        elif alignment_score > 0.6:
            sp.burnout_accumulator = max(0.0, sp.burnout_accumulator - 0.002)

        # 번아웃 → 집중 페널티
        effective_conc = concentration
        if sp.burnout_accumulator > 0.3:
            effective_conc *= (1.0 - sp.burnout_accumulator * 0.5)

        # 숙달 성장
        gain = compute_mastery_gain(sp, effective_conc, aptitude, job_title)

        # 몰입 판정
        ceiling = SKILL_CEILINGS.get(job_title, (0.5, 0.5, 0.005))[0]
        mastery_ratio = sp.mastery / ceiling if ceiling > 0 else 0
        is_flow = (
            effective_conc > 0.6
            and aptitude > 0.5
            and 0.2 < mastery_ratio < 0.8
        )

        if is_flow:
            gain *= 1.5
            sp.flow_ticks += 1
            # 몰입 시 번아웃 회복
            sp.burnout_accumulator = max(0.0, sp.burnout_accumulator - 0.005)

        # 숙달 적용
        sp.mastery = min(ceiling, sp.mastery + gain)
        sp.peak_concentration = max(sp.peak_concentration, effective_conc)

        # ── 승급 기여도 축적: 생산적 작업이 class 승급에 기여 ──
        if gain > 0:
            output_mult = compute_output_multiplier(sp.mastery, job_title)
            contrib = gain * output_mult * (2.0 if is_flow else 1.0)
            inner.promotion_contrib_window.append(contrib)
            if len(inner.promotion_contrib_window) > 500:
                inner.promotion_contrib_window = inner.promotion_contrib_window[-500:]

        # 번아웃 → chronic_stress 기여
        if sp.burnout_accumulator > 0.7:
            inner.chronic_stress = min(1.0, inner.chronic_stress + 0.003)

        # ── 자연 적성 발견: 일하면서 자기를 알아간다 ──
        # joy/anger 반응이 적성의 단서. 일할수록 자기 인식이 정확해짐.
        joy = float(inner.chiljeong[0])
        anger = float(inner.chiljeong[1])
        # joy 높으면 적성 높게, anger 높으면 낮게 인식
        emotional_signal = aptitude + (joy - anger) * 0.15
        rng_d = self._derive_rng("deliberation", pid, self.time.tick)
        noise = rng_d.uniform(-0.1, 0.1)
        perceived = max(0.2, min(1.0, emotional_signal + noise))

        if job_title in inner.discovered_aptitudes:
            # 경험이 쌓일수록 정확해짐 (지수이동평균)
            old = inner.discovered_aptitudes[job_title]
            inner.discovered_aptitudes[job_title] = old * 0.95 + perceived * 0.05
        else:
            inner.discovered_aptitudes[job_title] = perceived

        return {
            "job": job_title,
            "concentration": round(effective_conc, 3),
            "aptitude": round(aptitude, 2),
            "mastery": round(sp.mastery, 4),
            "gain": round(gain, 6),
            "flow": is_flow,
            "burnout": round(sp.burnout_accumulator, 3),
            "streak": sp.consecutive_ticks,
            "output_mult": round(compute_output_multiplier(sp.mastery, job_title), 2),
        }

    # ══════════════════════════════════════════════════════════
    # Layer 6: 경제 시스템
    # ══════════════════════════════════════════════════════════

    def _process_work(self, pid: str) -> dict | None:
        """Process a direct work attempt with the Phase 15 strike gate."""
        inner = self.inners[pid]
        if inner.strike_until_tick > self.time.tick:
            return {
                "type": "strike_refuse_work",
                "persona": pid,
                "tick": self.time.tick,
            }
        return self._process_economy(pid, "work")

    def _process_economy(self, pid: str, action: str) -> dict | None:
        """매 틱 경제 처리: work → goods 생산 + 소액 gold (Phase 11)."""
        if action != "work":
            return None
        if self.inners[pid].strike_until_tick > self.time.tick:
            return {
                "type": "strike_refuse_work",
                "persona": pid,
                "tick": self.time.tick,
            }

        wallet = self.wallets.get(pid)
        if not wallet:
            return None

        persona = self.personas[pid]
        inner = self.inners[pid]
        emp_id = persona.employment_id
        job_title = self._get_persona_job_title(pid)
        self._apply_job_speciality(pid, job_title)

        # 공통: 숙달 + class + 도구 배율 계산
        mastery = 0.0
        if job_title in inner.skill_profiles:
            mastery = inner.skill_profiles[job_title].mastery
        output_mult = compute_output_multiplier(mastery, job_title)
        eff_class = inner.effective_class if hasattr(inner, 'effective_class') else 1
        output_mult *= (1.0 + (eff_class - 1) * 0.1)
        tool_mult = self._get_tool_multiplier(pid)

        # goods 산출
        goods_type = JOB_OUTPUT_MAP.get(job_title, "material")
        base_output = JOB_BASE_OUTPUT.get(job_title, 1.0)

        if emp_id and emp_id in self.employments:
            # ── 고용 상태: 임금(gold) 수령 + goods 생산 → 고용주 ──
            emp = self.employments[emp_id]
            emp.ticks_worked += 1
            emp.total_earned += emp.wage_per_tick

            # goods → 고용주 인벤토리
            goods_amount = base_output * output_mult * tool_mult
            employer_inner = self.inners.get(emp.employer_id)
            if employer_inner:
                employer_inner.inventory[goods_type] = (
                    employer_inner.inventory.get(goods_type, 0) + goods_amount
                )

            # 고용주가 임금 지불 (기존 로직 유지)
            employer_wallet = self.wallets.get(emp.employer_id)
            if employer_wallet and employer_wallet.pay(emp.wage_per_tick):
                wallet.receive(emp.wage_per_tick)
                emp.total_paid += emp.wage_per_tick
                return {
                    "type": "wage_received",
                    "amount_gold": emp.wage_per_tick,
                    "from": emp.employer_id,
                    "exploitation": round(emp.exploitation_score, 3),
                    "goods_produced": goods_type,
                    "goods_amount": round(goods_amount, 2),
                }
            else:
                emp.grievances += 1
                return {
                    "type": "wage_unpaid",
                    "owed": emp.wage_per_tick,
                    "total_owed": emp.unpaid,
                    "grievances": emp.grievances,
                    "grievance": True,
                    "goods_produced": goods_type,
                    "goods_amount": round(goods_amount, 2),
                }
        else:
            # ── 자영 노동: goods 자기 인벤토리 + 소액 gold ──
            territory_id = persona.territory
            territory = self.territories.get(territory_id)

            # 희소성 보정
            workers_here = sum(
                1 for p in self.personas.values()
                if p.territory == territory_id and p.employment_id is None
            )
            scarcity = max(0.5, min(2.0, 3.0 / max(1, workers_here)))

            # goods 생산 → 자기 인벤토리
            goods_amount = base_output * output_mult * tool_mult * scarcity
            inner.inventory[goods_type] = (
                inner.inventory.get(goods_type, 0) + goods_amount
            )

            # gold 소액 직접 지급 (기존의 30% — 급격한 전환 방지)
            snlt_gold = 5.0 * output_mult * scarcity * GOLD_DIRECT_PAY_RATIO
            tax_rate = territory.tax_rate if territory else 0.1
            tax_gold = snlt_gold * tax_rate
            net_gold = snlt_gold - tax_gold

            if territory and territory.treasury_gold > 0:
                actual_pay = min(net_gold, territory.treasury_gold)
                territory.treasury_gold -= actual_pay
                territory.gdp_this_quarter += snlt_gold / 1000
                wallet.gold += actual_pay
                paid_ratio = actual_pay / net_gold if net_gold > 0 else 1.0
                return {
                    "type": "self_employed",
                    "goods_produced": goods_type,
                    "goods_amount": round(goods_amount, 2),
                    "gross_gold": round(snlt_gold, 1),
                    "net_gold": round(net_gold, 1),
                    "actual_paid": round(actual_pay, 1),
                    "paid_ratio": round(paid_ratio, 2),
                    "scarcity": round(scarcity, 2),
                    "treasury_remaining": round(territory.treasury_gold, 1),
                }
            else:
                will_earned = 0.002 * scarcity
                wallet.will += will_earned
                return {
                    "type": "self_employed_primitive",
                    "goods_produced": goods_type,
                    "goods_amount": round(goods_amount, 2),
                    "will_earned": round(will_earned, 5),
                    "scarcity": round(scarcity, 2),
                    "note": "treasury_depleted",
                }

    # ── Phase 11: 생존 소비 + 도구 + 시장 + NPC ─────────────────

    def _process_survival_consume(self, pid: str) -> dict | None:
        """매 틱 생존 소비: 식량 자동 소비."""
        inner = self.inners[pid]
        food_stock = inner.inventory.get("food", 0)

        if food_stock >= FOOD_CONSUME_PER_TICK:
            inner.inventory["food"] = food_stock - FOOD_CONSUME_PER_TICK
            inner.oyok[0] = max(0.0, inner.oyok[0] - 0.01)
            inner.energy_pool = min(inner.max_capacity, inner.energy_pool + 0.02)
            inner.consecutive_hunger_ticks = 0
            return None  # 정상 — 이벤트 불필요
        else:
            # 미충족: 페널티 에스컬레이션 (완만 — NPC/시장이 보충)
            inner.consecutive_hunger_ticks += 1
            ticks = inner.consecutive_hunger_ticks
            inner.oyok[0] = min(1.0, inner.oyok[0] + 0.015)
            result = {"type": "hunger", "ticks": ticks}

            if ticks > 48:
                inner.chronic_stress = min(0.75, inner.chronic_stress + 0.002)
                result["penalty"] = "stress"
            if ticks > 120:
                inner.vitality = max(0.0, inner.vitality - 0.002)
                result["penalty"] = "vitality_drain"

            return result

    def _get_tool_multiplier(self, pid: str) -> float:
        """도구 보유/내구도에 따른 생산성 배율 (0.7x~1.5x)."""
        inner = self.inners[pid]
        dur = inner.equipped_tool_durability
        if dur is None or dur <= 0:
            return 1.0 - TOOL_BROKEN_PENALTY  # 0.7x
        ratio = dur / TOOL_MAX_DURABILITY
        return 1.0 + TOOL_PRODUCTIVITY_BONUS * ratio  # 1.0~1.5x

    def _wear_tool(self, pid: str) -> dict | None:
        """작업 1틱: 도구 내구도 감소."""
        inner = self.inners[pid]
        if inner.equipped_tool_durability is None:
            return None
        inner.equipped_tool_durability -= TOOL_WEAR_PER_TICK
        if inner.equipped_tool_durability <= 0:
            inner.equipped_tool_durability = None
            return {"type": "tool_broken", "persona": pid}
        return None

    def _auto_tool_management(self, pid: str) -> list[dict]:
        """도구 자동 관리: 인벤토리에 tool 있으면 장착, 50% 미만이면 수리."""
        inner = self.inners[pid]
        wallet = self.wallets.get(pid)
        events = []

        if inner.equipped_tool_durability is None:
            if inner.inventory.get("tool", 0) >= 1:
                inner.inventory["tool"] -= 1
                inner.equipped_tool_durability = TOOL_MAX_DURABILITY
                events.append({"type": "tool_equipped", "persona": pid})
        elif inner.equipped_tool_durability < TOOL_MAX_DURABILITY * 0.5:
            has_gold = wallet and wallet.gold >= TOOL_REPAIR_COST_GOLD
            has_mat = inner.inventory.get("material", 0) >= TOOL_REPAIR_MATERIAL
            if has_gold and has_mat:
                wallet.pay(TOOL_REPAIR_COST_GOLD)  # gold 싱크
                inner.inventory["material"] -= TOOL_REPAIR_MATERIAL
                inner.equipped_tool_durability = min(
                    TOOL_MAX_DURABILITY,
                    inner.equipped_tool_durability + int(TOOL_MAX_DURABILITY * 0.8),
                )
                events.append({"type": "tool_repaired", "persona": pid,
                               "cost_gold": TOOL_REPAIR_COST_GOLD})
        return events

    def _compute_snn_pricing(self, pid: str, goods_type: str) -> dict:
        """[SNN] 최근 뉴런 발화율에서 가격 성향을 도출한다."""
        inner = self.inners[pid]
        brain = self.brains[pid]
        npc = NPC_PRICES.get(goods_type, {"buy": 20, "sell": 5})

        fr = getattr(brain, "_last_firing_rate", None)
        stress_rate = 0.0
        fatigue_rate = 0.0
        drive_rate = 0.0
        economic_rate = 0.0
        if fr is None or len(fr) == 0:
            urgency = 0.0
            motivation = 0.0
        else:
            clusters = np.array_split(fr, 12)
            stress_rate = float(clusters[5].mean()) if len(clusters) > 5 else 0.0
            fatigue_rate = float(clusters[8].mean()) if len(clusters) > 8 else 0.0
            drive_rate = float(clusters[0].mean()) if len(clusters) > 0 else 0.0
            if len(fr) >= 350:
                if goods_type == "food":
                    economic_rate = float(fr[300:310].mean())
                elif goods_type == "tool":
                    economic_rate = float(fr[310:320].mean())
                else:
                    economic_rate = float(fr[320:350].mean())

            cluster_urgency = (stress_rate + fatigue_rate) * 5.0
            economic_urgency = economic_rate * 6.0
            urgency = min(1.0, max(cluster_urgency, economic_urgency))
            motivation = min(1.0, drive_rate * 10.0)

        greed = float(inner.oyok[3])
        price_floor = float(npc.get("sell", 5))
        price_ceiling = float(npc.get("buy", 20))
        price_range = max(0.0, price_ceiling - price_floor)

        patience = 1.0 - urgency
        patience_factor = 1.0
        sell_price = price_floor + price_range * patience * patience_factor
        buy_factor = min(1.0, 0.8 + (1.0 - greed) * 0.3)
        effective_buy_urgency = min(1.0, urgency * 1.2)
        buy_max = price_floor + price_range * effective_buy_urgency * buy_factor

        return {
            "sell_price": max(price_floor, sell_price),
            "buy_max": min(price_ceiling, buy_max),
            "urgency": urgency,
            "motivation": motivation,
            "stress_rate": stress_rate,
            "fatigue_rate": fatigue_rate,
            "drive_rate": drive_rate,
            "economic_rate": economic_rate,
            "greed": greed,
        }

    def _get_pricing(self, pid: str, goods_type: str) -> dict:
        """Return the economy-tick pricing snapshot, computing only as fallback."""
        cached = self._pricing_cache.get(pid, {}).get(goods_type)
        if cached is not None:
            return cached
        pricing = self._compute_snn_pricing(pid, goods_type)
        self._pricing_cache.setdefault(pid, {})[goods_type] = pricing
        return pricing

    def _should_sell(self, pid: str, goods_type: str) -> tuple[bool, float]:
        """[SNN] 잉여 인식과 내면 상태로 매도 의사를 계산한다."""
        inner = self.inners[pid]
        stock = float(inner.inventory.get(goods_type, 0))
        comfort_level = {
            "food": 20, "material": 8, "tool": 3,
            "medicine": 5, "knowledge": 3,
        }
        surplus = stock - comfort_level.get(goods_type, 10)
        if surplus <= 0:
            return False, 0.0

        pricing = self._get_pricing(pid, goods_type)
        stress_guard = max(float(inner.chronic_stress), float(pricing["urgency"]))
        if stress_guard > 0.5:
            surplus *= max(0.0, 1.0 - (stress_guard - 0.5))

        greed = float(inner.oyok[3])
        surplus *= (1.0 - greed * 0.3)
        sell_qty = max(0.0, min(surplus, 5.0))
        return sell_qty > 0.5, sell_qty

    def _should_buy(self, pid: str, goods_type: str) -> tuple[bool, float]:
        """[SNN] 부족 인식과 절박도에서 매수 의사를 계산한다."""
        inner = self.inners[pid]
        stock = float(inner.inventory.get(goods_type, 0))
        need_level = {
            "food": 10, "material": 3, "tool": 1,
            "medicine": 2, "knowledge": 1,
        }
        if stock >= need_level.get(goods_type, 5):
            return False, 0.0
        pricing = self._get_pricing(pid, goods_type)
        return True, float(pricing["buy_max"])

    def _process_internal_food_procurement(
        self, territory_id: str, target_qty: float
    ) -> tuple[float, list[dict]]:
        """Phase 16-C: territory buys surplus food from local personas."""
        territory = self.territories.get(territory_id)
        if not territory or target_qty <= 0:
            return 0.0, []

        unit_price = float(NPC_PRICES.get("food", {}).get("buy", 10)) * INTERNAL_FOOD_PRICE_RATIO

        candidates: list[tuple[str, float]] = []
        for pid, persona in self.personas.items():
            if persona.territory != territory_id:
                continue
            inner = self.inners[pid]
            if float(inner.vitality) <= 0 or inner.is_sleeping:
                continue
            food_stock = float(inner.inventory.get("food", 0.0))
            surplus = food_stock - PERSONA_FOOD_SAFE_STOCK
            if surplus <= 0:
                continue
            candidates.append((pid, surplus))

        if not candidates:
            return 0.0, []

        candidates.sort(key=lambda item: (-item[1], item[0]))

        procured = 0.0
        events: list[dict] = []
        remaining = float(target_qty)
        for pid, surplus in candidates:
            if remaining <= 0:
                break
            qty = min(surplus, remaining)
            cost = qty * unit_price
            if territory.treasury_gold < cost:
                if unit_price <= 0:
                    break
                qty = territory.treasury_gold / unit_price
                cost = qty * unit_price
                if qty < 1.0:
                    break

            territory.treasury_gold -= cost
            self.wallets[pid].receive(cost)
            inner = self.inners[pid]
            inner.inventory["food"] = float(inner.inventory.get("food", 0.0)) - qty
            territory.food_reserve = float(getattr(territory, "food_reserve", 0.0)) + qty
            territory.internal_food_procured_total += qty
            procured += qty
            remaining -= qty
            events.append({
                "type": "internal_food_procurement",
                "territory": territory_id,
                "seller": pid,
                "qty": round(qty, 2),
                "unit_price": round(unit_price, 2),
                "cost": round(cost, 2),
                "reserve_after": round(territory.food_reserve, 2),
            })

        return procured, events

    def _calc_hunger_pressure(self, territory_id: str) -> float:
        """Normalize average consecutive hunger ticks for one territory."""
        vals = [
            float(getattr(self.inners[pid], "consecutive_hunger_ticks", 0))
            for pid, persona in self.personas.items()
            if persona.territory == territory_id
        ]
        if not vals:
            return 0.0
        return min(1.0, (sum(vals) / len(vals)) / 72.0)

    def _weighted_sample_without_replacement(
        self, population: list, weights: list[float], k: int
    ) -> list:
        """Weighted sampling without replacement using the engine RNG."""
        if k <= 0:
            return []
        if k >= len(population):
            return list(population)

        keyed = []
        for item, weight in zip(population, weights):
            if weight <= 0:
                continue
            u = self.rng.random()
            keyed.append((u ** (1.0 / weight), item))
        keyed.sort(key=lambda item: -item[0])
        return [item for _, item in keyed[:k]]

    def _process_public_works(self, territory_id: str) -> list[dict]:
        """Phase 16-B/C/D/E: SNN-driven public employment + productive output.

        Phase 16-E 확장:
        - 후보 풀: unemployed OR (low_gold AND hungry)
        - Food crisis mode: hunger >= HUNGER_TRIGGER_THRESHOLD AND reserve < target * FOOD_CRISIS_RESERVE_RATIO
          → 전원 food labor 배치, 비-farmer produced *= FOOD_LABOR_NON_FARMER_RATIO
        - food 생산 증폭: produced_food *= (1 + communal_farms * COMMUNAL_FARM_BOOST)
        - skip reason 이벤트 발행 (관측용)
        """
        territory = self.territories.get(territory_id)
        if not territory:
            return []
        if territory.treasury_gold < PUBLIC_WORKS_MIN_TREASURY:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "budget_insufficient",
                "detail": "below_min_treasury",
            }]

        # Phase 16-G: 珥덇린 STALE_SIGNAL_TICKS(72) ?숈븞 SNN ?좏샇 ?놁쓬 ??bootstrap
        signal_decay: float = 1.0
        if territory.last_snn_signals_tick < 0:
            if self.time.tick >= STALE_SIGNAL_TICKS:
                return [{
                    "type": "public_works_skip_reason",
                    "territory": territory_id,
                    "reason": "signal_stale",
                    "detail": "never_computed",
                }]
            # Phase 16-G bootstrap: 珥덇린 72?깆? 湲곕낯 ?좏샇濡?economy ?쒕룞
            snn = {
                "growth": PUBLIC_WORKS_BOOTSTRAP_GROWTH,
                "tension": PUBLIC_WORKS_BOOTSTRAP_TENSION,
                "stability": 0.0,
            }
            sig_age = 0
        else:
            sig_age = self.time.tick - territory.last_snn_signals_tick
            if sig_age > PUBLIC_WORKS_STALE_MAX_AGE:
                return [{
                    "type": "public_works_skip_reason",
                    "territory": territory_id,
                    "reason": "signal_stale",
                    "detail": f"sig_age={sig_age}_max_exceeded",
                }]
            raw_signals = territory.last_snn_signals or {}
            if sig_age > STALE_SIGNAL_TICKS:
                over = float(sig_age - STALE_SIGNAL_TICKS)
                signal_decay = max(
                    PUBLIC_WORKS_STALE_DECAY_FLOOR,
                    1.0 - over / PUBLIC_WORKS_STALE_DECAY_WINDOW,
                )
                snn = {k: float(v) * signal_decay for k, v in raw_signals.items()}
            else:
                snn = raw_signals

        growth = float(snn.get("growth", 0.0))
        tension = float(snn.get("tension", 0.0))
        stability = float(snn.get("stability", 0.0))
        hunger = self._calc_hunger_pressure(territory_id)
        signal_component = (
            growth * 0.5
            + tension * 0.3
            + stability * 0.15
            + hunger * HUNGER_PRESSURE_WEIGHT
        )
        rate = min(0.8, max(0.0, PUBLIC_WORKS_BASE_ACTIVATION + signal_component))
        territory.policy.public_works_rate = rate
        if rate < PUBLIC_WORKS_RATE_MIN:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "rate_below_min",
                "rate": round(rate, 4),
            }]

        wage_per_person = PUBLIC_WORKS_WAGE_PER_TICK * PUBLIC_WORKS_DURATION
        qincome = float(getattr(territory, "quarter_tax_income", 0.0))
        cap_income_from_tax = (
            qincome * QUARTER_TAX_BUDGET_MULTIPLIER
            if qincome > 0 else 0.0
        )
        cap_income_from_treasury = (
            territory.treasury_gold * PUBLIC_WORKS_TREASURY_INCOME_FLOOR_RATIO
        )
        cap_income = max(cap_income_from_tax, cap_income_from_treasury)
        cap_treasury = territory.treasury_gold * PUBLIC_WORKS_MAX_TREASURY_RATIO
        budget_cap = min(cap_income, cap_treasury)
        if budget_cap < wage_per_person:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "budget_insufficient",
                "budget_cap": round(budget_cap, 1),
                "wage_required": wage_per_person,
            }]

        # Phase 16-G: food_crisis / parttime_enabled 瑜??꾨낫 ?좊컻 ?꾩뿉 怨꾩궛
        reserve = float(getattr(territory, "food_reserve", 0.0))
        residents_count = sum(
            1 for p in self.personas.values() if p.territory == territory_id
        )
        reserve_target = residents_count * FOOD_STOCKPILE_RESERVE_PER_PERSONA
        food_crisis_active = (
            hunger >= HUNGER_TRIGGER_THRESHOLD
            and reserve < reserve_target * FOOD_CRISIS_RESERVE_RATIO
        )
        parttime_enabled = (
            food_crisis_active
            or tension >= PUBLIC_WORKS_PARTTIME_TENSION_THRESHOLD
        )

        lord_id = getattr(territory, "lord_id", None)

        unemployed: list[str] = []
        low_gold_hungry: list[str] = []
        parttime_candidates: list[str] = []  # Phase 16-G: employed 以?part-time ?꾨낫
        for pid, persona in self.personas.items():
            if persona.territory != territory_id:
                continue
            if pid == lord_id:
                continue
            inner = self.inners[pid]
            if float(inner.vitality) <= 0.0 or inner.is_sleeping:
                continue
            if persona.employment_id is None:
                unemployed.append(pid)
            else:
                wallet = self.wallets.get(pid)
                if wallet is None:
                    continue
                gold = float(getattr(wallet, "gold", 0.0))
                hungry_ticks = int(getattr(inner, "consecutive_hunger_ticks", 0))
                if gold < PUBLIC_WORKS_LOW_GOLD_THRESHOLD and hungry_ticks >= PUBLIC_WORKS_HUNGRY_TICKS_THRESHOLD:
                    low_gold_hungry.append(pid)
                elif parttime_enabled:
                    # Phase 16-G: ?꾧린 ?곹솴?먯꽌留?employed ??part-time ?꾨낫濡??ы븿
                    parttime_candidates.append(pid)

        # ?곗꽑?쒖쐞: unemployed > low_gold_hungry > parttime
        candidates = unemployed + low_gold_hungry + parttime_candidates
        parttime_pids: set[str] = set(parttime_candidates)

        if not candidates:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "no_candidates",
                "unemployed": 0,
                "low_gold_hungry": 0,
                "parttime": 0,
            }]

        n_hire = max(1, int(rate * len(candidates)))
        max_affordable = int(budget_cap // wage_per_person)
        n_hire = min(n_hire, max_affordable, len(candidates))
        if n_hire <= 0:
            return [{
                "type": "public_works_skip_reason",
                "territory": territory_id,
                "reason": "no_candidates",
                "detail": "n_hire_zero",
            }]

        farmer_bias_active = hunger >= HUNGER_TRIGGER_THRESHOLD
        if farmer_bias_active:
            weights = [
                PUBLIC_WORKS_FARMER_BIAS
                if (self._get_persona_job_title(pid) or "") == "farmer"
                else 1.0
                for pid in candidates
            ]
            chosen = self._weighted_sample_without_replacement(candidates, weights, n_hire)
        else:
            chosen = self.rng.sample(candidates, n_hire)

        events: list[dict] = []
        for pid in chosen:
            # Phase 16-G: part-time ?щ????곕씪 ?꾧툑 / ?앹궛 鍮꾩쑉 ?곸슜
            is_parttime = pid in parttime_pids
            wage_ratio = PUBLIC_WORKS_PARTTIME_WAGE_RATIO if is_parttime else 1.0
            output_ratio = PUBLIC_WORKS_PARTTIME_OUTPUT_RATIO if is_parttime else 1.0
            wage_applied = wage_per_person * wage_ratio

            if territory.treasury_gold < wage_applied:
                break
            job_title = self._get_persona_job_title(pid) or "laborer"

            if food_crisis_active:
                produced_type = "food"
                base_output = JOB_BASE_OUTPUT.get("farmer", 2.0)
                if job_title != "farmer":
                    base_output *= FOOD_LABOR_NON_FARMER_RATIO
            else:
                produced_type = JOB_OUTPUT_MAP.get(job_title, "material")
                base_output = JOB_BASE_OUTPUT.get(job_title, 0.5)

            produced = base_output * PUBLIC_WORKS_DURATION * output_ratio

            farm_multiplier = 1.0
            if produced_type == "food":
                farm_multiplier = 1.0 + territory.communal_farms * COMMUNAL_FARM_BOOST
                produced *= farm_multiplier

            in_kind = produced * PUBLIC_WORKS_IN_KIND_RATIO
            to_persona = produced - in_kind

            territory.treasury_gold -= wage_applied
            territory.quarter_public_spend += wage_applied
            self.wallets[pid].receive(wage_applied)
            if produced_type == "food":
                territory.food_reserve = getattr(territory, "food_reserve", 0.0) + in_kind
            else:
                territory.inventory[produced_type] = (
                    territory.inventory.get(produced_type, 0.0) + in_kind
                )
            inner = self.inners[pid]
            inner.inventory[produced_type] = inner.inventory.get(produced_type, 0.0) + to_persona

            was_employed_elsewhere = (
                self.personas[pid].employment_id is not None
            )
            events.append({
                "type": "public_works",
                "territory": territory_id,
                "persona": pid,
                "job_title": job_title,
                "wage": round(wage_applied, 2),
                "duration": PUBLIC_WORKS_DURATION,
                "rate": round(rate, 3),
                "snn_growth": round(growth, 3),
                "snn_tension": round(tension, 3),
                "snn_stability": round(stability, 3),
                "hunger_pressure": round(hunger, 3),
                "farmer_bias_active": farmer_bias_active,
                "parttime": is_parttime,
                "food_crisis_active": food_crisis_active,
                "food_crisis": food_crisis_active,
                "from_pool": (
                    "parttime"
                    if is_parttime
                    else "low_gold_hungry" if was_employed_elsewhere else "unemployed"
                ),
                "communal_farms": territory.communal_farms,
                "farm_multiplier": round(farm_multiplier, 3),
                "base_component": round(PUBLIC_WORKS_BASE_ACTIVATION, 3),
                "signal_component": round(signal_component, 3),
                "produced_type": produced_type,
                "produced_total": round(produced, 2),
                "in_kind_to_territory": round(in_kind, 2),
                "to_persona": round(to_persona, 2),
                "treasury_after": round(territory.treasury_gold, 1),
                "signal_age": sig_age,
                "signal_decay": round(signal_decay, 3),
            })
        return events

    def _process_market(self) -> list[dict]:
        """P2P 시장: 잉여 goods 매도 → 부족 페르소나 매수. 수수료 50% 소멸."""
        events = []

        # Phase A: 잉여 goods 매도 주문 등록
        for pid, persona in self.personas.items():
            inner = self.inners[pid]
            if inner.is_sleeping:
                continue
            for goods_type, qty in inner.inventory.items():
                should_sell, sell_qty = self._should_sell(pid, goods_type)
                if not should_sell:
                    continue

                reserved_qty = sum(
                    o.quantity for o in self.market_orders
                    if o.seller_id == pid and o.goods_type == goods_type and o.quantity > 0
                )
                available_qty = max(0.0, float(qty) - reserved_qty)
                sell_qty = min(sell_qty, available_qty)
                if sell_qty <= 0.5:
                    continue

                pricing = self._get_pricing(pid, goods_type)
                price = round(float(pricing["sell_price"]), 1)
                self._order_counter += 1
                order = MarketOrder(
                    id=f"ord_{self._order_counter}",
                    seller_id=pid, goods_type=goods_type,
                    quantity=round(sell_qty, 2),
                    price_per_unit=price,
                    created_tick=self.time.tick,
                    territory_id=persona.territory,
                )
                self.market_orders.append(order)
                events.append({
                    "type": "sell_order",
                    "seller": pid,
                    "goods": goods_type,
                    "qty": round(sell_qty, 2),
                    "price": price,
                    "pricing": pricing,
                })

        # Phase B: 부족한 페르소나가 매수
        for pid, persona in self.personas.items():
            inner = self.inners[pid]
            wallet = self.wallets.get(pid)
            if inner.is_sleeping or not wallet:
                continue

            needs = []
            for goods_type in ["food", "material", "tool", "medicine", "knowledge"]:
                should_buy, max_price = self._should_buy(pid, goods_type)
                if should_buy:
                    needs.append((goods_type, max_price))

            for need_type, max_price in needs:
                buyer_territory_policy = (
                    self.territories[persona.territory].policy
                    if persona.territory in self.territories
                    else None
                )
                buyer_openness = (
                    buyer_territory_policy.market_openness
                    if buyer_territory_policy else 0.5
                )

                def can_trade(seller_id: str) -> bool:
                    seller = self.personas.get(seller_id)
                    if not seller:
                        return False
                    if seller.territory == persona.territory:
                        return True
                    seller_territory = self.territories.get(seller.territory)
                    if not seller_territory:
                        return False
                    avg_openness = (
                        buyer_openness + seller_territory.policy.market_openness
                    ) / 2.0
                    return avg_openness >= 0.4

                orders = [
                    o for o in self.market_orders
                    if (o.goods_type == need_type and o.quantity > 0
                        and o.seller_id != pid
                        and can_trade(o.seller_id))
                ]
                def order_score(order: MarketOrder) -> tuple[float, float]:
                    seller_stock = float(
                        self.inners.get(order.seller_id, inner)
                        .inventory.get(need_type, 0)
                    )
                    return (-seller_stock, order.price_per_unit)

                orders.sort(key=order_score)

                for order in orders:
                    if order.quantity <= 0:
                        continue
                    seller_inner = self.inners.get(order.seller_id)
                    if not seller_inner:
                        order.quantity = 0
                        continue
                    seller_stock = float(seller_inner.inventory.get(need_type, 0))
                    if seller_stock <= 0:
                        order.quantity = 0
                        continue
                    if order.price_per_unit > max_price:
                        continue

                    buy_qty = min(order.quantity, seller_stock, 5.0)
                    total_cost = order.price_per_unit * buy_qty
                    fee = FACILITY_FEES.get("market", 2.0)
                    seller_persona = self.personas.get(order.seller_id)
                    is_inter_territory = (
                        seller_persona is not None
                        and seller_persona.territory != persona.territory
                    )
                    if is_inter_territory:
                        fee *= 2.0

                    if wallet.gold >= total_cost + fee:
                        wallet.pay(total_cost + fee)
                        inner.inventory[need_type] = (
                            inner.inventory.get(need_type, 0) + buy_qty
                        )
                        seller_inner.inventory[need_type] = seller_stock - buy_qty
                        seller_wallet = self.wallets.get(order.seller_id)
                        if seller_wallet:
                            seller_wallet.receive(total_cost)
                        # 수수료: 영지 간이면 양측 금고에 분배, 아니면 buyer 영지만
                        territory = self.territories.get(persona.territory)
                        sink_amount = fee * MARKET_FEE_SINK_RATIO
                        keep_amount = fee - sink_amount
                        if is_inter_territory and territory:
                            seller_territory = self.territories.get(
                                seller_persona.territory
                            )
                            territory.treasury_gold += keep_amount / 2.0
                            if seller_territory:
                                seller_territory.treasury_gold += keep_amount / 2.0
                        elif territory:
                            territory.treasury_gold += keep_amount
                        order.quantity -= buy_qty
                        buyer_pricing = self._get_pricing(pid, need_type)
                        events.append({
                            "type": "trade", "buyer": pid,
                            "seller": order.seller_id,
                            "goods": need_type, "qty": round(buy_qty, 2),
                            "price": order.price_per_unit, "fee": fee,
                            "inter_territory": is_inter_territory,
                            "urgency": round(float(buyer_pricing["urgency"]), 3),
                            "buy_max": round(max_price, 2),
                            "price_basis": buyer_pricing,
                        })
                        break

        # Phase C: 만료 주문 제거
        self.market_orders = [
            o for o in self.market_orders
            if o.quantity > 0 and self.time.tick - o.created_tick < MARKET_ORDER_EXPIRY_TICKS
        ]
        return events

    def _process_npc_shop(self) -> list[dict]:
        """NPC 상점: 비싼 가격 goods 판매 + 낮은 가격 매입. gold 싱크/유입."""
        events = []

        # 일일 재고 리셋
        if self.time.tick % 24 == 0:
            self._npc_stock = {
                g: info["daily_stock"] for g, info in NPC_PRICES.items()
            }

        for pid, persona in self.personas.items():
            inner = self.inners[pid]
            wallet = self.wallets.get(pid)
            if inner.is_sleeping or not wallet:
                continue

            # [SNN] 긴급 식량 구매: 최근 발화율에서 읽은 절박 신호 기반
            pricing = self._get_pricing(pid, "food")
            food_stock = inner.inventory.get("food", 0)
            if pricing["urgency"] > 0.6 and food_stock < 10:
                npc = NPC_PRICES["food"]
                stock = self._npc_stock.get("food", 0)
                buy_qty = min(int(3 + pricing["urgency"] * 5), stock)
                cost = npc["buy"] * buy_qty
                if buy_qty > 0 and wallet.gold >= cost:
                    stock_before = food_stock
                    wallet.pay(cost)  # gold → NPC 밖으로 소멸 (싱크)
                    inner.inventory["food"] = inner.inventory.get("food", 0) + buy_qty
                    self._npc_stock["food"] -= buy_qty
                    stock_after = inner.inventory.get("food", 0)
                    events.append({
                        "type": "npc_buy", "buyer": pid,
                        "goods": "food", "qty": buy_qty, "cost": cost,
                        "motivation": round(float(pricing["motivation"]), 3),
                        "urgency": round(float(pricing["urgency"]), 3),
                        "surplus": round(float(stock_before - 10), 2),
                        "threshold": 10,
                        "stock_before": round(float(stock_before), 2),
                        "stock_after": round(float(stock_after), 2),
                        "price_basis": pricing,
                    })

            tool_pricing = self._get_pricing(pid, "tool")
            tool_stock = inner.inventory.get("tool", 0)
            has_equipped_tool = (
                inner.equipped_tool_durability is not None
                and inner.equipped_tool_durability > 0
            )
            if (not has_equipped_tool and tool_stock == 0
                    and tool_pricing["urgency"] > 0.4):
                npc = NPC_PRICES["tool"]
                stock = self._npc_stock.get("tool", 0)
                cost = npc["buy"]
                if stock > 0 and wallet.gold >= cost:
                    stock_before = tool_stock
                    wallet.pay(cost)
                    inner.inventory["tool"] = inner.inventory.get("tool", 0) + 1
                    self._npc_stock["tool"] -= 1
                    stock_after = inner.inventory.get("tool", 0)
                    events.append({
                        "type": "npc_buy", "buyer": pid,
                        "goods": "tool", "qty": 1, "cost": cost,
                        "motivation": round(float(tool_pricing["motivation"]), 3),
                        "urgency": round(float(tool_pricing["urgency"]), 3),
                        "surplus": round(float(stock_before - 1), 2),
                        "threshold": 1,
                        "stock_before": round(float(stock_before), 2),
                        "stock_after": round(float(stock_after), 2),
                        "price_basis": tool_pricing,
                    })

            med_pricing = self._get_pricing(pid, "medicine")
            med_stock = inner.inventory.get("medicine", 0)
            if (inner.vitality < 0.5 and med_stock == 0
                    and med_pricing["urgency"] > 0.5):
                npc = NPC_PRICES["medicine"]
                stock = self._npc_stock.get("medicine", 0)
                cost = npc["buy"]
                if stock > 0 and wallet.gold >= cost:
                    stock_before = med_stock
                    wallet.pay(cost)
                    inner.inventory["medicine"] = inner.inventory.get("medicine", 0) + 1
                    self._npc_stock["medicine"] -= 1
                    stock_after = inner.inventory.get("medicine", 0)
                    events.append({
                        "type": "npc_buy", "buyer": pid,
                        "goods": "medicine", "qty": 1, "cost": cost,
                        "motivation": round(float(med_pricing["motivation"]), 3),
                        "urgency": round(float(med_pricing["urgency"]), 3),
                        "surplus": round(float(stock_before - 1), 2),
                        "threshold": 1,
                        "stock_before": round(float(stock_before), 2),
                        "stock_after": round(float(stock_after), 2),
                        "price_basis": med_pricing,
                    })

            # 잉여 goods NPC에 매도 (gold 유입 — 유일한 새 gold 원천)
            for goods_type in ["material", "tool", "medicine", "knowledge", "food"]:
                stock_before = inner.inventory.get(goods_type, 0)
                surplus_threshold = 20 if goods_type == "food" else 10
                surplus = stock_before - surplus_threshold
                if surplus <= 0:
                    continue
                pricing = self._get_pricing(pid, goods_type)
                if pricing["motivation"] > 0.6:
                    continue
                npc = NPC_PRICES.get(goods_type, {})
                sell_limit = 5 if pricing["urgency"] > 0.5 else 2
                sell_qty = min(surplus, sell_limit)
                if sell_qty <= 0:
                    continue
                territory = self.territories.get(persona.territory)
                trade_bonus = 1.0
                if territory:
                    trade_bonus += territory.policy.tax_rate * 0.5
                revenue = npc.get("sell", 5) * sell_qty * trade_bonus
                inner.inventory[goods_type] -= sell_qty
                wallet.receive(revenue)
                stock_after = inner.inventory.get(goods_type, 0)
                events.append({
                    "type": "npc_sell", "seller": pid,
                    "goods": goods_type, "qty": sell_qty, "revenue": revenue,
                    "trade_bonus": round(float(trade_bonus), 3),
                    "motivation": round(float(pricing["motivation"]), 3),
                    "urgency": round(float(pricing["urgency"]), 3),
                    "surplus": round(float(surplus), 2),
                    "threshold": 10,
                    "stock_before": round(float(stock_before), 2),
                    "stock_after": round(float(stock_after), 2),
                    "price_basis": pricing,
                })

        return events

    def create_job(self, employer_id: str, title: str, wage_per_tick: float,
                   description: str = "") -> Job | None:
        """고용주가 일자리를 만든다. WILL이 충분해야 가능."""
        wallet = self.wallets.get(employer_id)
        if not wallet or wallet.will < 5.0:  # 최소 5 WILL 있어야 고용주 가능
            return None

        self._job_counter += 1
        job_id = f"job_{employer_id}_{self._job_counter}"
        job = Job(
            id=job_id,
            employer_id=employer_id,
            title=title,
            description=description,
            wage_per_tick=wage_per_tick,
            created_tick=self.time.tick,
        )
        self.jobs[job_id] = job
        return job

    def hire(self, job_id: str, employee_id: str) -> Employment | None:
        """고용: 페르소나가 일자리를 받아들인다."""
        job = self.jobs.get(job_id)
        if not job or not job.is_open:
            return None

        self._emp_counter += 1
        emp_id = f"emp_{self._emp_counter}"
        emp = Employment(
            job_id=job_id,
            employer_id=job.employer_id,
            employee_id=employee_id,
            start_tick=self.time.tick,
            wage_per_tick=job.wage_per_tick,
        )
        self.employments[emp_id] = emp
        self.personas[employee_id].employment_id = emp_id

        if sum(1 for e in self.employments.values()
               if e.job_id == job_id) >= job.max_employees:
            job.is_open = False

        return emp

    def quit_job(self, employee_id: str) -> dict:
        """자발적 퇴직. 착취 심하면 flee 모드."""
        persona = self.personas.get(employee_id)
        if not persona or not persona.employment_id:
            return {}

        emp = self.employments.get(persona.employment_id)
        if not emp:
            return {}

        result = {
            "employee": employee_id,
            "employer": emp.employer_id,
            "reason": "voluntary",
            "exploitation_score": emp.exploitation_score,
            "unpaid_gold": emp.unpaid,
        }

        # 착취도가 높으면 소문 생성
        if emp.exploitation_score > 0.3:
            rumor = Rumor(
                source_secret_owner=None,
                content_tag=f"exploitation_by_{emp.employer_id}",
                accuracy=min(1.0, emp.exploitation_score + 0.2),
                origin_tick=self.time.tick,
                known_by={employee_id},
                about_id=emp.employer_id,
            )
            self.rumors.append(rumor)
            result["reason"] = "exploitation"
            result["rumor_created"] = True

        cleanup = self._release_employment(employee_id, reason=result["reason"])
        if cleanup:
            result["employment_cleanup"] = cleanup
        return result

    # ══════════════════════════════════════════════════════════
    # 자연 식품 시스템
    # ══════════════════════════════════════════════════════════

    # ══════════════════════════════════════════════════════════
    # 지식 기록 시스템 (서적/문서)
    # ══════════════════════════════════════════════════════════

    def try_write_knowledge(self, pid: str) -> list[KnowledgeRecord]:
        """SNN deliberation 기반 서적 작성.

        무조건 기록이 아닌, 뇌 상태(tone/성격/에너지)가 "쓰고 싶다"고
        판단할 때만 기록한다.

        기록 충동 = C(Cognition) tone × 이성 성격 × 에너지 여유 × certainty
        - C tone 높음 → 지적 활동 욕구
        - 이성(-감성) + 엄격 → 기록·정리 성향
        - 에너지 > 0.4 → 집필할 여력
        - certainty >= 0.8 → 기록할 만한 지식

        Academy/Library 시설이 있는 영지에서만 가능.
        이미 기록된 것은 중복 작성 안 함.
        """
        persona = self.personas[pid]
        inner = self.inners[pid]
        territory = self.territories.get(persona.territory)

        # Academy가 있어야 기록 가능
        has_academy = territory and territory.get_facility("academy")
        if not has_academy:
            return []

        # ── SNN Deliberation: 기록 충동 판정 ──
        # 에너지 부족하면 집필 불가
        if inner.energy_pool < 0.4:
            return []

        # C(Cognition/ACh) 클러스터 tone (idx=6)
        c_tone = float(inner.tone[6])  # 기본 1.0, 높으면 지적 활성

        # 성격 반영
        p = persona.personality
        # 이성도: personality[2] 음수 = 이성적 → 기록 성향 높음
        rationality = max(0.0, -float(p[2]))   # 0~1
        # 엄격도: personality[4] 양수 = 엄격 → 정리/기록 성향
        strictness = max(0.0, float(p[4]))     # 0~1

        # 기록 충동 = C tone 기여 + 성격 기여 + 에너지 여유
        write_urge = (
            (c_tone - 0.8) * 0.4        # C tone > 0.8이면 양수 기여
            + rationality * 0.25         # 이성적일수록 기록 성향
            + strictness * 0.15          # 엄격할수록 정리 성향
            + (inner.energy_pool - 0.4) * 0.2  # 에너지 여유
        )

        # 만성 스트레스 높으면 기록 욕구 감소 (생존이 우선)
        if inner.chronic_stress > 0.5:
            write_urge -= (inner.chronic_stress - 0.5) * 0.3

        # write_urge를 확률로 변환 (sigmoid-like)
        # urge 0 → ~15%, urge 0.3 → ~35%, urge 0.5 → ~50%
        write_prob = 1.0 / (1.0 + np.exp(-5.0 * (write_urge - 0.2)))

        rng = self._derive_rng("wild_food_choose", pid, self.time.tick)
        if rng.random() > write_prob:
            return []  # deliberation 결과: 쓰지 않기로 결정

        # ── 기록 실행 ──
        existing_subjects = {r.subject_id for r in self.knowledge_records
                             if r.author_id == pid}
        written = []
        for food_id, k in inner.food_knowledge.items():
            if k.get("certainty", 0) >= 0.8 and food_id not in existing_subjects:
                self._record_counter += 1
                verdict = "안전" if k.get("is_good") else "위험"
                record = KnowledgeRecord(
                    id=f"rec_{self._record_counter}",
                    author_id=pid,
                    topic="food",
                    subject_id=food_id,
                    content=f"{food_id}: {verdict}. 평균 에너지 변화 {k['avg_energy_delta']:+.2f}",
                    reliability=k["certainty"],
                    created_tick=self.time.tick,
                    territory_id=persona.territory,
                )
                self.knowledge_records.append(record)
                written.append(record)

                # 기록 행위 자체가 에너지 소모 (집필 비용)
                inner.energy_pool = max(0.0, inner.energy_pool - 0.02)

        return written

    def try_read_knowledge(self, pid: str) -> int:
        """현재 영지의 서적을 열람. food_knowledge를 간접 습득.

        Academy 시설에 보관된 기록만 열람 가능.
        직접 경험보다 낮은 certainty 부여 (서적은 타인의 경험).
        """
        persona = self.personas[pid]
        inner = self.inners[pid]
        territory_id = persona.territory
        territory = self.territories.get(territory_id)

        has_academy = territory and territory.get_facility("academy")
        if not has_academy:
            return 0

        # 이 영지의 서적
        local_records = [r for r in self.knowledge_records
                         if r.territory_id == territory_id and r.author_id != pid]

        learned = 0
        for record in local_records:
            if record.topic != "food":
                continue
            food_id = record.subject_id
            k = inner.food_knowledge.get(food_id, {
                "tries": 0, "total_energy": 0.0,
                "avg_energy_delta": 0.0, "is_good": None, "certainty": 0.0,
            })
            # 서적: 소문보다 신뢰도 높지만 직접 경험보다 낮음
            certainty_gain = record.reliability * 0.25
            k["certainty"] = min(1.0, k.get("certainty", 0) + certainty_gain)
            if k["certainty"] >= 0.45:
                k["is_good"] = record.content.count("안전") > 0
            k["source"] = "book"
            inner.food_knowledge[food_id] = k
            learned += 1
        return learned

    def _init_regional_food_knowledge(self, pid: str):
        """태생 지역 × 연령에 따른 초기 식물 지식.

        이것은 규칙이 아니다. "이 페르소나가 age_ticks 동안
        태생 지역에서 살면서 SNN이 자연스럽게 학습한 결과"를
        동일한 certainty 공식으로 압축 표현한 것이다.

        연령이 많고, 같은 권역에 오래 살수록 certainty 높아짐.
        하지만 개인차(성격)와 확률 요소로 같은 조건에서도 다름.
        """
        persona = self.personas[pid]
        inner = self.inners[pid]
        region = persona.birth_region
        age = persona.age_ticks
        available = WILD_FOODS_BY_REGION.get(region, [])

        rng = self._derive_rng("init_knowledge", pid, region, age)
        personality = persona.personality

        # 호기심(explore 성향) + 신중함이 학습 속도에 영향
        bold = float(personality[1]) if personality is not None else 0.0
        rational = -float(personality[2]) if personality is not None else 0.0  # 이성적일수록 체계적 학습
        learning_mult = 1.0 + bold * 0.3 + rational * 0.2

        for food in available:
            # 나이 × 발견 확률 = 예상 조우 횟수 (확률적으로)
            expected_encounters = age * food.discovery_prob * 0.05 * learning_mult
            actual_encounters = int(rng.poisson(max(0.1, expected_encounters)))

            if actual_encounters == 0:
                continue

            # 조우마다 동일한 certainty 공식 적용
            total_energy = 0.0
            for _ in range(actual_encounters):
                # 효과 샘플 (어릴 때 먹어봤던 경험들)
                e_delta = float(rng.uniform(food.energy_delta_min, food.energy_delta_max))
                total_energy += e_delta
                effect_strength = abs(e_delta)
                certainty_gain = min(0.3, effect_strength * 2 + 0.05)

                k = inner.food_knowledge.get(food.id, {
                    "tries": 0, "total_energy": 0.0, "avg_energy_delta": 0.0,
                    "is_good": None, "certainty": 0.0,
                })
                k["tries"] += 1
                k["total_energy"] += e_delta
                k["avg_energy_delta"] = k["total_energy"] / k["tries"]
                k["certainty"] = min(1.0, k.get("certainty", 0) + certainty_gain)
                if k["certainty"] >= 0.5:
                    k["is_good"] = k["avg_energy_delta"] > 0.01
                inner.food_knowledge[food.id] = k

    def _inherit_food_knowledge(self, new_pid: str, old_inner: InnerWorld):
        """윤회 시 food_knowledge 70% 이식.

        뇌 가중치 70% 이식과 동일한 비율.
        기억은 사라지지만 신체적 반응(SNN 패턴)은 남는다.
        → "전생에 독초를 먹었던 경험이 이번 생의 직관에 남아있다"
        """
        new_inner = self.inners.get(new_pid)
        if not new_inner:
            return
        for food_id, k in old_inner.food_knowledge.items():
            inherited = {
                "tries": max(1, int(k["tries"] * 0.7)),
                "total_energy": k["total_energy"] * 0.7,
                "avg_energy_delta": k["avg_energy_delta"],  # 평균은 유지
                "is_good": k["is_good"],   # 판단은 희미하게 유지
                "certainty": k["certainty"] * 0.7,  # 확신도 70%로 감소
            }
            new_inner.food_knowledge[food_id] = inherited

    def try_forage(self, pid: str) -> dict | None:
        """explore 행동 중 채집 시도.

        중요: 페르소나는 외형(apparent_name)만 보고 채집한다.
        실제 어떤 식물인지는 먹어봐야 안다.
        단, 이전 경험/지식이 있으면 식별 확률이 높아진다.
        """
        region = self.personas[pid].region
        available = WILD_FOODS_BY_REGION.get(region, [])
        if not available:
            return None

        inner = self.inners[pid]
        personality = self.personas[pid].personality
        rng = self._derive_rng("forage", pid, self.time.tick)

        # 대담한 성격(+bold)은 더 많이 채집 시도
        bold = float(personality[1]) if personality is not None else 0.0

        found = []
        for food in available:
            base_prob = food.discovery_prob * (1.0 + bold * 0.2)
            if rng.random() >= base_prob:
                continue

            # ── 식별 시도 ──
            # 지식이 있으면 식별 확률 상승
            knowledge = inner.food_knowledge.get(food.id, {})
            certainty = knowledge.get("certainty", 0.0)
            id_difficulty = food.identification_difficulty

            # 식별 성공 여부: 지식 + 역량 vs 난이도
            identify_chance = max(0.1, certainty + (1.0 - id_difficulty) * 0.5)
            correctly_identified = rng.random() < identify_chance

            if correctly_identified:
                # 진짜 이름으로 저장
                stored_id = food.id
                stored_name = food.name
            else:
                # 외형만으로 저장 (lookalike와 혼동 가능)
                stored_id = food.apparent_name  # 외형 ID로 저장
                stored_name = food.apparent_name

            current = inner.foraged_foods.get(stored_id, 0)
            inner.foraged_foods[stored_id] = current + 1
            found.append({
                "stored_as": stored_name,
                "actually": food.name if not correctly_identified else None,
                "identified": correctly_identified,
            })

        return {"foraged": found} if found else None

    def _process_eat(self, pid: str) -> dict:
        """eat 행동 처리. 4경로: 인벤토리/시설/자연/굶음 (Phase 11)."""
        persona = self.personas[pid]
        inner = self.inners[pid]
        wallet = self.wallets.get(pid)
        territory = self.territories.get(persona.territory)

        EAT_COST_GOLD = 10.0  # 시설 식사 비용

        # ── 경로 0 (Phase 11): 인벤토리 food 우선 소비 ──
        if inner.inventory.get("food", 0) >= 3:
            inner.inventory["food"] -= 3
            return {"type": "inventory", "food_consumed": 3,
                    "food_remaining": inner.inventory["food"]}

        # ── 경로 1: 시설 구매 ──
        if (wallet and wallet.gold >= EAT_COST_GOLD and
                territory and territory.treasury_gold >= 0):
            wallet.pay(EAT_COST_GOLD)
            if territory:
                territory.treasury_gold += EAT_COST_GOLD  # 시설 수입 → 영지 금고
            return {"type": "facility", "cost_gold": EAT_COST_GOLD}

        # ── 경로 2: 자연 채집 식품 소비 ──
        if inner.foraged_foods:
            # 지식이 있으면 좋은 것 우선 선택
            best_food_id = self._choose_wild_food(pid)
            if best_food_id:
                inner.foraged_foods[best_food_id] -= 1
                if inner.foraged_foods[best_food_id] <= 0:
                    del inner.foraged_foods[best_food_id]

                # 해당 식품 찾기
                food = next(
                    (f for f in WILD_FOODS_BY_REGION.get(persona.region, [])
                     if f.id == best_food_id), None
                )
                if food:
                    return self._apply_wild_food(pid, food)

        # ── 경로 3: 아무것도 없으면 즉시 채집 시도 ──
        region = persona.region
        available = WILD_FOODS_BY_REGION.get(region, [])
        if available:
            rng = self._derive_rng("emergency_forage", pid, self.time.tick)
            for food in available:
                if rng.random() < food.discovery_prob * 0.5:  # 긴급 채집은 확률 절반
                    return self._apply_wild_food(pid, food)

        return {"type": "starving"}  # 아무것도 없음

    def _choose_wild_food(self, pid: str) -> str | None:
        """인벤토리에서 먹을 식품 선택. 지식 기반."""
        inner = self.inners[pid]
        if not inner.foraged_foods:
            return None

        best_id = None
        best_score = float('-inf')
        for food_id, count in inner.foraged_foods.items():
            if count <= 0:
                continue
            knowledge = inner.food_knowledge.get(food_id)
            if knowledge:
                # 알고 있으면 평균 효과 기반
                score = knowledge.get("avg_energy_delta", 0)
                if knowledge.get("is_good") is False:
                    score -= 10  # 나쁜 걸 알면 회피
            else:
                # 모르면 중간값 추정 (모험)
                score = 0
            if score > best_score:
                best_score = score
                best_id = food_id

        return best_id

    def _apply_wild_food(self, pid: str, food: WildFood) -> dict:
        """자연 식품 효과 적용 (랜덤)."""
        rng = self._derive_rng("food_effect", pid, self.time.tick, food.id)
        energy_delta = float(rng.uniform(food.energy_delta_min, food.energy_delta_max))
        vitality_delta = float(rng.uniform(food.vitality_delta_min, food.vitality_delta_max))

        return {
            "type": "wild",
            "food_id": food.id,
            "food_name": food.name,
            "energy_delta": round(energy_delta, 3),
            "vitality_delta": round(vitality_delta, 3),
            "hunger_delta": food.hunger_delta,
            "chronic_stress_delta": food.chronic_stress_delta,
            "fear_delta": food.fear_delta if energy_delta < 0 else 0.0,
            "joy_delta": food.joy_delta if energy_delta > 0 else 0.0,
            "known": food.id in self.inners[pid].food_knowledge,
        }

    def _record_food_knowledge(self, pid: str, eat_result: dict):
        """식품 경험을 기억에 기록. 학습."""
        if eat_result.get("type") != "wild":
            return
        food_id = eat_result.get("food_id")
        if not food_id:
            return

        inner = self.inners[pid]
        k = inner.food_knowledge.get(food_id, {
            "tries": 0, "total_energy": 0.0, "avg_energy_delta": 0.0,
            "is_good": None, "certainty": 0.0,
        })
        k["tries"] += 1
        k["total_energy"] += eat_result.get("energy_delta", 0)
        k["avg_energy_delta"] = k["total_energy"] / k["tries"]

        # 확신도: 시도 횟수 + 효과 강도에 따라 상승
        effect_strength = abs(eat_result.get("energy_delta", 0))
        certainty_gain = min(0.3, effect_strength * 2 + 0.05)
        k["certainty"] = min(1.0, k.get("certainty", 0) + certainty_gain)

        # 판단: 확신도 0.5 이상일 때만 좋음/나쁨 결정
        if k["certainty"] >= 0.5:
            k["is_good"] = k["avg_energy_delta"] > 0.01
        inner.food_knowledge[food_id] = k

        # 좋은 식품 발견 → joy, 나쁜 식품 → 에피소드에 고살리언스 기록
        energy_delta = eat_result.get("energy_delta", 0)
        if abs(energy_delta) > 0.1:
            from ontology import EpisodeTrace
            ep = EpisodeTrace(
                tick=self.time.tick,
                action=f"eat:{food_id}",
                emotion_snapshot=inner.chiljeong.copy(),
                energy_at_time=inner.energy_pool,
                salience=min(1.0, 0.3 + abs(energy_delta) * 2),
            )
            inner.add_episode(ep)

        # 다른 페르소나에게 소문으로 전파 (긍정/부정 둘 다)
        if k["tries"] == 3 and abs(k["avg_energy_delta"]) > 0.05:
            tag = f"good_food_{food_id}" if k["is_good"] else f"bad_food_{food_id}"
            rumor = Rumor(
                source_secret_owner=None,
                content_tag=tag,
                accuracy=0.8,
                origin_tick=self.time.tick,
                known_by={pid},
                about_id=pid,
            )
            self.rumors.append(rumor)

    # ══════════════════════════════════════════════════════════
    # Layer 0.5: Natural Law (Nomos)
    # ══════════════════════════════════════════════════════════

    def _nomos_check(self, actions: dict, tick_result: dict) -> list[dict]:
        """자연법 3조 위반 탐지 + 3단계 응징.

        제1조: 생명 침해 금지 — 타인 vitality 직접 감소 행위
        제2조: 소유 침탈 금지 — 임금 미지급, 착취 고용
        제3조: 약속 위반 금지 — 고용 계약 미이행

        Nomos는 전지적으로 탐지 (증거 불필요).
        응징: 경미(경고+스트레스) → 중대(행동 제한+강등) → 금기(기후 이상+공포+대강등)
        """
        events = []
        violations_this_tick: dict[str, list[str]] = {}  # pid → [위반 법조]

        # ── P1-1: violation_count 갱생 (무위반 100틱마다 -1) ──
        for pid in self.personas:
            inner = self.inners[pid]
            if (inner.nomos_violation_count > 0
                    and inner.nomos_last_violation_tick > 0
                    and (self.time.tick - inner.nomos_last_violation_tick) >= NOMOS_DECAY_INTERVAL):
                ticks_since = self.time.tick - inner.nomos_last_violation_tick
                decay_amount = ticks_since // NOMOS_DECAY_INTERVAL
                inner.nomos_violation_count = max(0, inner.nomos_violation_count - decay_amount)
                if inner.nomos_violation_count == 0:
                    inner.nomos_last_severity = ""

        for pid in self.personas:
            inner = self.inners[pid]
            persona = self.personas[pid]

            # ── 제1조: 생명 침해 금지 ──
            # 현재는 직접 공격 행동이 없으므로, 극단 착취(vitality 파괴)를 대리 감지
            for emp_id, emp in self.employments.items():
                if emp.employer_id != pid:
                    continue
                victim_inner = self.inners.get(emp.employee_id)
                if victim_inner and victim_inner.vitality < 0.2 and emp.exploitation_score > 0.7:
                    # 착취로 인한 생명 위협 = 제1조 위반 (금기 등급)
                    violations_this_tick.setdefault(pid, []).append("제1조_생명침해")

            # ── 제2조: 소유 침탈 ──
            for emp_id, emp in self.employments.items():
                if emp.employer_id != pid:
                    continue
                if emp.exploitation_score > 0.5 and emp.grievances >= 3:
                    violations_this_tick.setdefault(pid, []).append("제2조_소유침탈")

            # ── 제3조: 약속 위반 (피고용인 보호) ──
            if persona_emp_id := persona.employment_id:
                emp = self.employments.get(persona_emp_id)
                if emp and emp.grievances >= 5:
                    employer_id = emp.employer_id
                    violations_this_tick.setdefault(employer_id, []).append("제3조_약속위반")
                    # 피고용인 보호: anger↑ (정당한 분노) + 퇴직 권리
                    inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + 0.1)
                    events.append({
                        "type": "nomos_alert",
                        "law": "제3조_약속위반",
                        "victim": pid,
                        "employer": employer_id,
                        "unpaid_gold": round(emp.unpaid, 1),
                    })

        # ── 응징 실행 ──
        for pid, laws in violations_this_tick.items():
            inner = self.inners[pid]
            persona = self.personas[pid]
            inner.nomos_violation_count += len(laws)
            inner.nomos_last_violation_tick = self.time.tick
            is_taboo = "제1조_생명침해" in laws

            # 등급 결정: 금기(제1조 or count>=10) > 중대(count>=5) > 경미
            if is_taboo or inner.nomos_violation_count >= NOMOS_SEVERITY["금기"]["threshold"]:
                severity = "금기"
            elif inner.nomos_violation_count >= NOMOS_SEVERITY["중대"]["threshold"]:
                severity = "중대"
            else:
                severity = "경미"

            rules = NOMOS_SEVERITY[severity]
            inner.nomos_last_severity = severity

            # 1) 감정: anger + fear
            inner.chiljeong[1] = min(1.0, inner.chiljeong[1] + rules["emotion_delta"])  # anger
            inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + rules["emotion_delta"])  # fear
            # P1-3: 처벌 stress만으로 사망(0.8) 불가 — 상한 0.75
            nomos_stress_cap = 0.75
            inner.chronic_stress = min(nomos_stress_cap, inner.chronic_stress + rules["stress_delta"])

            # 2) 행동 차단
            if rules["blocked_ticks"] > 0:
                inner.nomos_blocked_until = max(
                    inner.nomos_blocked_until,
                    self.time.tick + rules["blocked_ticks"],
                )

            # 3) 클래스 강등 (P1-4: 제1조 금기 -3, 누적형 금기 -2)
            penalty = rules["class_penalty"]
            if severity == "금기" and not is_taboo:
                penalty = min(penalty, 2)  # 누적형 금기: -2 (제1조 즉시 금기만 -3)
            if penalty > 0 and persona.persona_class > 1:
                old_class = persona.persona_class
                persona.persona_class = max(1, persona.persona_class - penalty)
                inner.effective_class = persona.persona_class
                episode = EpisodeTrace(
                    tick=self.time.tick, action="nomos_demotion",
                    emotion_snapshot=inner.chiljeong.copy(),
                    energy_at_time=inner.energy_pool,
                )
                episode.salience = 0.9
                inner.add_episode(episode)

            # 4) 금기: Physis 연동 (영지 기후 이상 — "하늘이 어두워짐")
            if rules.get("physis_penalty"):
                region = persona.region
                if region in self.current_weather:
                    self.current_weather[region]["disaster_signal"] = min(
                        1.0, self.current_weather[region].get("disaster_signal", 0) + 0.6
                    )
                # 트라우마 기억 생성 ("세계가 나를 거부한다")
                episode = EpisodeTrace(
                    tick=self.time.tick, action="nomos_taboo",
                    emotion_snapshot=inner.chiljeong.copy(),
                    energy_at_time=inner.energy_pool,
                )
                episode.salience = 0.98  # 가족 사망급 각인
                inner.add_episode(episode)

            # 5) 소문 생성: 영지 전체에 위반 사실 전파
            rumor = Rumor(
                about_id=pid,
                content_tag=f"nomos_{severity}_{laws[0]}",
                accuracy=1.0,
                origin_tick=self.time.tick,
                known_by={pid},
            )
            self.rumors.append(rumor)

            # 6) 신뢰 하락: 피해자/동일 영지만 (P1-2: 연좌제 방지)
            violator_region = persona.region
            for rel in self.relationships.values():
                if rel.persona_a == pid or rel.persona_b == pid:
                    other_id = rel.persona_b if rel.persona_a == pid else rel.persona_a
                    other_persona = self.personas.get(other_id)
                    if not other_persona:
                        continue
                    # 피해자(고용 관계 당사자)는 전액, 동일 영지는 50%, 타 영지 무영향
                    is_victim = any(
                        (emp.employee_id == other_id or emp.employer_id == other_id)
                        for emp in self.employments.values()
                        if emp.employer_id == pid or emp.employee_id == pid
                    )
                    if is_victim:
                        trust_penalty = rules["emotion_delta"] * 0.5
                    elif other_persona.region == violator_region:
                        trust_penalty = rules["emotion_delta"] * 0.25
                    else:
                        continue  # 타 영지 무영향
                    rel.trust = max(0.0, rel.trust - trust_penalty)

            events.append({
                "type": "nomos_violation",
                "laws": laws,
                "violator": pid,
                "severity": severity,
                "violation_count": inner.nomos_violation_count,
                "consequence": {
                    "blocked_ticks": rules["blocked_ticks"],
                    "class_penalty": penalty,
                    "physis": rules.get("physis_penalty", False),
                },
            })

        return events

    def _check_deaths(self) -> list[dict]:
        """사망 판정 + 윤회 처리."""
        deaths = []
        for pid in list(self.personas.keys()):
            inner = self.inners[pid]
            persona = self.personas[pid]

            if inner.vitality > 0:
                continue  # 살아있음

            # ── 사망 ──
            death_event = {
                "pid": pid,
                "name": persona.name,
                "tick": self.time.tick,
                "cause": self._death_cause(inner),
                "chronic_stress_at_death": round(inner.chronic_stress, 3),
                "vitality": 0.0,
                "mortality_awareness": round(inner.mortality_awareness, 3),
            }

            # ── 윤회 ──
            new_pid = f"{pid}_r{self.time.tick}"
            new_seed = self.brains[pid].snn.rng.integers(0, 2**31)

            # 새 뇌 생성 (가중치 70% 이식)
            from brain import PersonaBrain
            old_brain = self.brains[pid]
            new_brain = PersonaBrain(n_neurons=persona.neuron_count, seed=int(new_seed))
            new_brain.snn.weights = (
                old_brain.snn.weights * 0.7
                + new_brain.snn.weights * 0.3
            )
            new_brain.readout_weights = (
                old_brain.readout_weights * 0.7
                + new_brain.readout_weights * 0.3
            )

            # 성격은 70% 유지 (경향성 잔존) + 30% 변동
            rng = self._derive_rng("reincarnate_personality", pid, new_pid, int(new_seed))
            old_personality = persona.personality
            new_personality = (
                old_personality * 0.7
                + rng.uniform(-1, 1, 5).astype(np.float32) * 0.3
            )
            new_personality = np.clip(new_personality, -1, 1).astype(np.float32)

            # 윤회한 페르소나 (기억 소실, 성격 잔존)
            inherited_class = 1
            if persona.persona_class > 1:
                inherited_class = max(2, persona.persona_class - 1)

            new_persona = Persona(
                id=new_pid,
                name=f"{persona.name}·再",
                full_name=persona.full_name,
                region=persona.region,
                territory=persona.territory,
                persona_class=inherited_class,
                neuron_count=persona.neuron_count,
                personality=new_personality,
            )
            self._rekey_economic_references(pid, new_pid, new_persona)
            new_persona.aptitude_map = compute_aptitude_map(new_personality, int(new_seed))
            new_inner = InnerWorld(persona_id=new_pid)
            old_inner = self.inners[pid]

            # promotion + nomos 필드 초기화 (환생 시 잔존 방지)
            new_inner.promotion_stable_ticks = 0
            new_inner.promotion_drive_history = []
            new_inner.promotion_contrib_window = []
            new_inner.effective_class = new_persona.persona_class
            new_inner.demotion_warning_ticks = 0
            new_inner.nomos_violation_count = 0
            new_inner.nomos_blocked_until = 0
            new_inner.nomos_last_severity = ""
            new_inner.nomos_last_violation_tick = 0
            # Phase 11: 환생 인벤토리 초기화
            new_inner.inventory = {
                "food": 30, "material": 5, "tool": 1,
                "medicine": 2, "knowledge": 0,
            }
            new_inner.equipped_tool_durability = TOOL_MAX_DURABILITY
            new_inner.consecutive_hunger_ticks = 0

            old_wallet = self.wallets.pop(pid, None)

            # ── identity rekey: pid → new_pid ──────────────────────
            # 관계망은 old pid 기준으로 생성되었으므로 유지 (비밀 처리와 동일 패턴)
            # dict key를 new_pid로 이전. 동일 dict의 기존 old pid 항목은 삭제.
            # ───────────────────────────────────────────────────────
            del self.personas[pid]
            del self.inners[pid]
            if pid in self.brains:
                del self.brains[pid]
            if pid in self._work_reward_history:
                del self._work_reward_history[pid]

            self.personas[new_pid] = new_persona
            self.inners[new_pid] = new_inner
            self.brains[new_pid] = new_brain
            self._work_reward_history[new_pid] = []
            if old_wallet is not None:
                old_wallet.persona_id = new_pid
                self.wallets[new_pid] = old_wallet

            self._territory_residents_cache = None
            self._faction_members_cache = {}

            # ── food_knowledge 70% 이식 ──
            # "전생에 독초에 혼났던 경험이 이번 생의 직관에 남는다"
            self._inherit_food_knowledge(new_pid, old_inner)

            # ── 태생 지역 초기 지식 추가 ──
            self._init_regional_food_knowledge(new_pid)
            # 관계는 유지 (이름만 바뀜, 관계망에 잔존)
            # 비밀은 소실
            if pid in self.secrets:
                self.secrets[pid].owner_id = new_pid
                self.secrets[pid].known_by = {new_pid}
                self.secrets[pid].revealed_tick = None
                self.secrets[new_pid] = self.secrets.pop(pid)
            self._rekey_relationships(pid, new_pid)

            death_event["reincarnation"] = {
                "new_name": new_persona.name,
                "personality_change": float(
                    np.abs(new_personality - old_personality).mean()
                ),
            }
            deaths.append(death_event)

        return deaths

    def _death_cause(self, inner: InnerWorld) -> str:
        """사망 원인 판정."""
        if inner.chronic_stress > 0.8:
            if inner.habituation.get("cold", 0) > 0.5:
                return "hypothermia (habituated)"  # 개구리 효과로 죽음
            return "chronic_exhaustion"
        if float(inner.oyok[0]) > 0.9:
            return "starvation"
        if float(inner.chiljeong[3]) > 0.9:
            return "shock"
        return "unknown"

    def _check_disasters(self) -> list[dict]:
        """재난 판정. disaster_signal 임계 초과 시 이벤트 발행."""
        disasters = []
        for rid, weather in self.current_weather.items():
            signal = weather.get("disaster_signal", 0)
            if signal < 0.5:
                continue

            cum = self.climate.cumulative.get(rid, {})
            dtype = "unknown"
            if cum.get("drought_days", 0) > 20:
                dtype = "drought"
            elif cum.get("heatwave_days", 0) > 5:
                dtype = "heatwave"
            elif cum.get("coldsnap_days", 0) > 7:
                dtype = "coldsnap"

            level = 1 if signal < 0.7 else (2 if signal < 0.9 else 3)

            disasters.append({
                "region": rid,
                "type": dtype,
                "level": level,
                "signal": round(signal, 3),
                "tick": self.time.tick,
            })

            # 재난 시 해당 권역 페르소나에게 에너지 페널티
            for pid, persona in self.personas.items():
                if persona.region == rid:
                    penalty = level * 0.05
                    self.inners[pid].energy_pool = max(0, self.inners[pid].energy_pool - penalty)
                    # 공포 감정 주입
                    self.inners[pid].chiljeong[3] = min(1.0, self.inners[pid].chiljeong[3] + level * 0.1)

        return disasters

    def _compute_neural_drive(self, pid: str, skill_id: str | None = None) -> float:
        """기존 신경 신호로부터 drive를 계산한다. 저장 값이 아닌 매 틱 실시간 계산.

        drive = 기하평균(mastery, aptitude, flow, dopamine)
        4개 신호 중 3개 이상이 0.01 초과일 때만 활성화.
        """
        inner = self.inners[pid]
        brain = self.brains[pid]

        # 관련 SkillProfile 선택
        if skill_id and skill_id in inner.skill_profiles:
            sp = inner.skill_profiles[skill_id]
        elif inner.skill_profiles:
            sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
        else:
            return 0.0

        # 신호 1: 숙달 수준 (천장 정규화)
        ceiling = SKILL_CEILINGS.get(sp.skill_id, (0.5, 0.5, 0.005))[0]
        mastery_norm = sp.mastery / ceiling if ceiling > 0 else 0

        # 신호 2: 적성 일치
        aptitude = self.personas[pid].aptitude_map.get(sp.skill_id, 0.5)
        apt_signal = max(0, aptitude - 0.4) / 0.6  # 0.4~1.0 → 0~1

        # 신호 3: 몰입 경험 비율
        flow_signal = 0.0
        if sp.total_ticks > 10:
            flow_signal = min(1.0, (sp.flow_ticks / sp.total_ticks) * 5.0)

        # 신호 4: 도파민 축적 (최근 양의 보상 평균)
        da_signal = 0.0
        if brain.snn.reward_history:
            recent = brain.snn.reward_history[-50:]
            positives = [r for r in recent if r > 0]
            if positives:
                da_signal = min(1.0, float(np.mean(positives)))

        # 기하평균: 수렴하는 증거가 필요
        factors = [mastery_norm, apt_signal, flow_signal, da_signal]
        nonzero = [f for f in factors if f > 0.01]
        if len(nonzero) < 3:
            return 0.0

        product = 1.0
        for f in nonzero:
            product *= f
        drive = (product ** (1.0 / len(nonzero))) ** 0.7
        return float(drive)

    def _compute_reward(
        self,
        pid: str,
        action: str,
        energy: float,
        prev_energy: float,
        job_title: str | None = None,
    ) -> float:
        """보상 함수 v2 (연속 스케일)."""
        reward = 0.0
        inner = self.inners[pid]
        hunger = float(inner.oyok[0])

        if energy < 0.1:
            reward -= 0.5

        if action == "eat":
            reward += (hunger - 0.3) * 1.2
        elif action == "sleep":
            if energy < 0.3:
                reward += 0.3
            elif energy > 0.7:
                reward -= 0.3
        elif action == "work":
            if energy > 0.3:
                reward += 0.15
                work_job = job_title or self._get_persona_job_title(pid)
                aptitude = self.personas[pid].aptitude_map.get(work_job, 0.5)
                reward += (aptitude - 0.4) * 0.5
                if work_job in inner.skill_profiles:
                    sp = inner.skill_profiles[work_job]
                    ceiling = SKILL_CEILINGS.get(work_job, (0.5, 0.5, 0.005))[0]
                    mastery_ratio = sp.mastery / ceiling if ceiling > 0 else 1.0
                    if 1.0 - mastery_ratio > 0.1:
                        reward += 0.1
            else:
                reward -= 0.1
        elif action == "explore":
            if energy > 0.5 and hunger < 0.5:
                reward += 0.2
            else:
                reward -= 0.05
        elif action == "socialize":
            # 사회적 행동: 에너지 있으면 보상
            if energy > 0.3:
                reward += 0.15
                # 숙련자 보너스: 높은 숙달을 가진 페르소나가 사교하면
                # 뇌가 "지식을 나누는 것"을 도파민으로 보상한다
                if inner.skill_profiles:
                    max_sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
                    if max_sp.mastery > 0.3:
                        reward += (max_sp.mastery - 0.3) * 0.3
            else:
                reward -= 0.1
        elif action == "idle":
            reward -= 0.15

        return np.clip(reward, -1.0, 1.0)

    # ══════════════════════════════════════════════════════════
    # 클래스 승급/강등 시스템
    # ══════════════════════════════════════════════════════════

    def _update_promotion_trigger(self, pid: str) -> None:
        """STDP 안정화 trigger: 매 work 틱마다 호출.

        best skill의 flow_ratio 안정성 + drive variance를 추적하여
        promotion_stable_ticks를 증감한다.
        """
        persona = self.personas[pid]
        inner = self.inners[pid]
        next_class = persona.persona_class + 1
        if next_class not in CLASS_RULES:
            return

        rules = CLASS_RULES[next_class]

        # best skill의 flow_ratio
        if not inner.skill_profiles:
            return
        best_sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
        if best_sp.total_ticks < 10:
            return
        flow_ratio = best_sp.flow_ticks / best_sp.total_ticks

        # drive 계산 + ring buffer (최근 20개)
        drive = self._compute_neural_drive(pid, best_sp.skill_id)
        inner.promotion_drive_history.append(drive)
        if len(inner.promotion_drive_history) > 20:
            inner.promotion_drive_history = inner.promotion_drive_history[-20:]

        # STDP 안정화 신호: flow_ratio 또는 drive (둘 다 시냅스 패턴 안정성 지표)
        # flow는 3중 조건으로 희소하므로, drive(기하평균)도 보완 신호로 사용
        stdp_signal = max(flow_ratio, drive * 0.5)
        if stdp_signal >= rules["flow_thr"]:
            inner.promotion_stable_ticks += 1
        else:
            inner.promotion_stable_ticks = max(0, inner.promotion_stable_ticks - 5)

        # drive variance 체크 (최근 10개) — 불안정하면 리셋
        if len(inner.promotion_drive_history) >= 10:
            recent_10 = inner.promotion_drive_history[-10:]
            drive_var = float(np.var(recent_10))
            if drive_var > rules["drive_var_max"]:
                inner.promotion_stable_ticks = max(0, inner.promotion_stable_ticks - 10)

    def _get_required_ticks(self, pid: str) -> int:
        """승급에 필요한 안정 틱 수. Drive가 촉매로 단축."""
        persona = self.personas[pid]
        next_class = persona.persona_class + 1
        if next_class not in CLASS_RULES:
            return 999999
        rules = CLASS_RULES[next_class]
        drive = self._compute_neural_drive(pid)
        return max(1, int(rules["base_obs_ticks"] * (1.0 - 0.2 * drive)))

    def _evaluate_promotion_gate(self, pid: str) -> dict | None:
        """사회적 검증 gate: trigger 충족 후 호출.

        mastery_ratio, contribution, peer_recognition, stability를 검증.
        Nomos 위반 차단. 모두 통과하면 event dict 반환.
        """
        persona = self.personas[pid]
        inner = self.inners[pid]
        next_class = persona.persona_class + 1
        if next_class not in CLASS_RULES:
            return None

        rules = CLASS_RULES[next_class]
        gate = rules["gate"]

        # 1. mastery_ratio
        if not inner.skill_profiles:
            return None
        best_sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
        ceiling = SKILL_CEILINGS.get(best_sp.skill_id, (0.5, 0.5, 0.005))[0]
        mastery_ratio = best_sp.mastery / ceiling if ceiling > 0 else 0
        if mastery_ratio < gate["mastery_ratio"]:
            return None

        # 2. contribution (최근 500틱 moving window 합산)
        contribution_norm = sum(inner.promotion_contrib_window)
        if contribution_norm < gate["contribution"]:
            return None

        # 3. peer_recognition: 같은 영지 동료의 trust × familiarity 평균
        territory_peers = [
            p for p in self.personas
            if p != pid and self.personas[p].region == persona.region
        ]
        if territory_peers:
            peer_scores = []
            for other in territory_peers:
                key = Relationship(persona_a=pid, persona_b=other).key()
                rel = self.relationships.get(key)
                if rel:
                    peer_scores.append(rel.trust * rel.familiarity)
                else:
                    key2 = Relationship(persona_a=other, persona_b=pid).key()
                    rel2 = self.relationships.get(key2)
                    if rel2:
                        peer_scores.append(rel2.trust * rel2.familiarity)
                    else:
                        peer_scores.append(0.0)
            peer_recognition = float(np.mean(peer_scores)) if peer_scores else 0.0
        else:
            peer_recognition = 0.0
        if peer_recognition < gate["peer"]:
            return None

        # 4. stability: (1 - chronic_stress) × 0.5 + vitality × 0.5
        stability = (1.0 - inner.chronic_stress) * 0.5 + inner.vitality * 0.5
        if stability < gate["stability"]:
            return None

        # 5. Nomos 위반 차단: exploitation_score > 0.3이면 승급 불가
        if persona.employment_id and persona.employment_id in self.employments:
            emp = self.employments[persona.employment_id]
            if emp.exploitation_score > 0.3:
                return None

        return {
            "pid": pid,
            "skill_id": best_sp.skill_id,
            "old_class": persona.persona_class,
            "new_class": next_class,
            "mastery_ratio": round(mastery_ratio, 3),
            "contribution_norm": round(contribution_norm, 3),
            "peer_recognition": round(peer_recognition, 3),
            "stability": round(stability, 3),
        }

    def _execute_promotion(self, event: dict) -> dict:
        """승급 실행: class 변경 + 감정/기억/소문/신뢰/SNN 보상."""
        pid = event["pid"]
        new_class = event["new_class"]
        persona = self.personas[pid]
        inner = self.inners[pid]
        brain = self.brains[pid]

        # class 변경
        persona.persona_class = new_class
        inner.effective_class = new_class
        persona.title = CLASS_TITLES.get(new_class, persona.title)

        # 추적 리셋
        inner.promotion_stable_ticks = 0
        inner.promotion_drive_history.clear()
        inner.promotion_contrib_window.clear()

        # 감정: 기쁨 + 도파민
        inner.chiljeong[0] = min(1.0, inner.chiljeong[0] + 0.3)
        inner.tone[0] = np.float16(min(2.0, float(inner.tone[0]) + 0.2))

        # 기억
        episode = EpisodeTrace(
            tick=self.time.tick,
            action="promotion",
            emotion_snapshot=inner.chiljeong.copy(),
            energy_at_time=inner.energy_pool,
        )
        episode.salience = 0.95
        inner.add_episode(episode)

        # 소문 생성
        rumor = Rumor(
            about_id=pid,
            content_tag=f"promoted_{event['skill_id']}_class{new_class}",
            accuracy=1.0,
            origin_tick=self.time.tick,
            known_by={pid},
        )
        self.rumors.append(rumor)

        # 동일 영지 peers: trust 보너스
        for other_pid in self.personas:
            if other_pid == pid:
                continue
            if self.personas[other_pid].region != persona.region:
                continue
            key = Relationship(persona_a=pid, persona_b=other_pid).key()
            rel = self.relationships.get(key)
            if not rel:
                key = Relationship(persona_a=other_pid, persona_b=pid).key()
                rel = self.relationships.get(key)
            if rel:
                rel.trust = min(1.0, rel.trust + 0.03 * (new_class - 1))

        # SNN 보상
        brain.snn.apply_reward(0.5)

        event["tick"] = self.time.tick
        event["persona_name"] = persona.name
        return event

    def _check_demotion(self, pid: str) -> dict | None:
        """단계적 강등 체크: effective_class 하락 → Nomos 중대 위반 시 실제 강등."""
        persona = self.personas[pid]
        inner = self.inners[pid]
        if persona.persona_class <= 1:
            return None

        current_rules = CLASS_RULES.get(persona.persona_class)
        if not current_rules:
            return None

        # flow_ratio 체크
        if not inner.skill_profiles:
            return None
        best_sp = max(inner.skill_profiles.values(), key=lambda s: s.mastery)
        if best_sp.total_ticks < 10:
            return None
        flow_ratio = best_sp.flow_ticks / best_sp.total_ticks

        # 현재 클래스 threshold의 70% 미만이면 경고 축적
        if flow_ratio < current_rules["flow_thr"] * 0.7:
            inner.demotion_warning_ticks += 1
        else:
            inner.demotion_warning_ticks = max(0, inner.demotion_warning_ticks - 1)

        # effective_class 하락 (200틱 경고 축적)
        if inner.demotion_warning_ticks >= 200 and inner.effective_class > 1:
            if inner.effective_class == persona.persona_class:
                inner.effective_class -= 1
                return {
                    "pid": pid, "type": "effective_demotion",
                    "persona_name": persona.name,
                    "effective_class": inner.effective_class,
                    "tick": self.time.tick,
                }

        # Nomos 중대 위반 + 500틱 경고 → 실제 강등
        nomos_violation = False
        if persona.employment_id and persona.employment_id in self.employments:
            emp = self.employments[persona.employment_id]
            if emp.exploitation_score > 0.5:
                nomos_violation = True

        if nomos_violation and inner.demotion_warning_ticks >= 500:
            old_class = persona.persona_class
            persona.persona_class -= 1
            inner.effective_class = persona.persona_class
            persona.title = CLASS_TITLES.get(persona.persona_class, persona.title)
            inner.demotion_warning_ticks = 0

            # 감정: 비애 + 공포
            inner.chiljeong[2] = min(1.0, inner.chiljeong[2] + 0.3)  # 비애
            inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + 0.2)  # 공포

            episode = EpisodeTrace(
                tick=self.time.tick,
                action="demotion",
                emotion_snapshot=inner.chiljeong.copy(),
                energy_at_time=inner.energy_pool,
            )
            episode.salience = 0.9
            inner.add_episode(episode)

            return {
                "pid": pid, "type": "actual_demotion",
                "persona_name": persona.name,
                "old_class": old_class,
                "new_class": persona.persona_class,
                "tick": self.time.tick,
            }

        return None

    def _sleep_tick(self, pid: str) -> dict:
        """수면 처리."""
        inner = self.inners[pid]
        brain = self.brains[pid]

        inner.sleep_ticks_remaining -= 1
        sleep_phase = "nrem" if inner.sleep_ticks_remaining > 1 else "rem"

        inner.energy_pool = min(inner.max_capacity, inner.energy_pool + 0.15)
        inner.oyok[1] = max(0.0, inner.oyok[1] - 0.15)

        # ── 수면 중 감정 처리 (초기화가 아닌 처리) ──
        # 성격에 따라 감쇠 속도 다름:
        # 신중(-) + 감성(+) → 느린 감쇠 (감정이 오래 남음)
        # 대담(+) + 이성(-) → 빠른 감쇠 (빨리 털어냄)
        personality = self.personas[pid].personality
        caution = -float(personality[1])   # 신중도 (신중이면 양수)
        emotionality = float(personality[2])   # 감성도
        sleep_decay = 0.93 + caution * 0.04 + emotionality * 0.03
        sleep_decay = float(np.clip(sleep_decay, 0.85, 0.99))
        inner.sleep_emotion_decay = sleep_decay

        # 만성 스트레스가 있으면 수면 중에도 fear의 바닥이 생김
        # (자도 완전히 안 사라지는 두려움)
        pre_sleep_fear = float(inner.chiljeong[3])
        inner.chiljeong = (inner.chiljeong * sleep_decay).astype(np.float16)
        fear_floor = inner.chronic_stress * 0.3   # 만성 스트레스 = fear 바닥
        inner.chiljeong[3] = max(float(inner.chiljeong[3]), fear_floor)

        dream_action = None
        memory_events = []

        if sleep_phase == "nrem":
            # ── SHY: 시냅스 하향 정규화 ──
            exc_w = brain.snn.weights[:brain.snn.n_exc, :]
            weak_mask = (exc_w > 0) & (exc_w < 0.05)
            exc_w[weak_mask] *= 0.995
            prune_mask = (np.abs(brain.snn.weights) < 0.0005) & (brain.snn.weights != 0)
            brain.snn.weights[prune_mask] = 0

            # ── 기억 안정화: FRESH/LABILE → CONSOLIDATED/RECONSOLIDATED ──
            for ep in inner.episodes:
                if ep.state in ("FRESH", "LABILE"):
                    old_state = ep.state
                    ep.consolidate()
                    if old_state != ep.state:
                        memory_events.append(f"{old_state}→{ep.state}")

            # ── 트라우마 억압 판정 ──
            inner.try_suppress_traumatic()

        else:
            # ── REM: 기억 replay + 재통합 ──
            recallable = inner.get_recallable_episodes()
            if recallable:
                sorted_eps = sorted(recallable, key=lambda e: e.salience, reverse=True)
                for ep in sorted_eps[:3]:
                    # 기억 재통합: 인출 시 현재 감정이 과거를 오염
                    ep.recall(current_tick=self.time.tick,
                              current_emotion=inner.chiljeong)
                    inner.chiljeong = (
                        inner.chiljeong * 0.5 + ep.emotion_snapshot * 0.5
                    ).astype(np.float16)
                    dream_action = ep.action

                # 수면 중 망각 (EXTINCT 우선 제거)
                if len(inner.episodes) > 30:
                    inner.episodes.sort(
                        key=lambda e: (
                            0 if e.state == "EXTINCT" else 2,
                            e.salience
                        )
                    )
                    inner.episodes = inner.episodes[-30:]

            # ── 억압 기억 재출현 판정 ──
            resurfaced = inner.try_resurface_memories()
            if resurfaced:
                for ep in resurfaced:
                    inner.chiljeong[3] = min(1.0, inner.chiljeong[3] + 0.4)
                    dream_action = ep.action
                    memory_events.append(f"RESURFACE:{ep.action}@{ep.tick}")

        # ── LABILE 소멸 판정 ──
        inner.check_memory_extinction(self.time.tick)

        if inner.sleep_ticks_remaining <= 0:
            inner.is_sleeping = False
            brain.snn.clear_reward()

        result = {
            "name": self.personas[pid].name,
            "action": f"dream:{dream_action}" if dream_action else f"sleep:{sleep_phase}",
            "energy": round(inner.energy_pool, 3),
            "hunger": round(float(inner.oyok[0]), 3),
            "sleeping": True,
            "firing_rate": 0.0,
            "emotions": inner.emotion_dict(),
            "reward": 0.0,
            "memories": len(inner.episodes),
        }
        if memory_events:
            result["memory_events"] = memory_events
        return result

    def run(self, n_ticks: int = 100, verbose: bool = True) -> list[dict]:
        """n틱 실행."""
        if verbose:
            names = [p.name for p in self.personas.values()]
            print(f"=== Multi-Persona: {', '.join(names)} ({n_ticks} ticks) ===")
            print()

        for _ in range(n_ticks):
            entry = self.tick()
            if verbose:
                parts = []
                for pid, pdata in entry["personas"].items():
                    status = "ZZZ" if pdata["sleeping"] else "ACT"
                    name = pdata["name"][:6]
                    parts.append(f"{name}:{status}:{pdata['action']:8s}")
                interactions = entry.get("interactions", [])
                inter_str = ""
                if interactions:
                    for inter in interactions:
                        names = [self.personas[p].name[:4] for p in inter["participants"]]
                        sec = " SECRET!" if inter.get("secret_shared") else ""
                        rum = ""
                        if inter.get("rumor_spread"):
                            rs = inter["rumor_spread"]
                            rum = f" RUMOR({rs['tag']}→{self.personas[rs['to']].name[:4]} acc={rs['accuracy']:.0%})"
                        inter_str += f" [{'-'.join(names)} f={inter['familiarity']:.2f}{sec}{rum}]"
                print(
                    f"[D{entry['day']:2d} H{entry['hour']:02d}] "
                    + " | ".join(parts)
                    + inter_str
                )

        if verbose:
            print(f"\n=== {n_ticks} ticks done ===")
            for key, rel in self.relationships.items():
                a_name = self.personas[rel.persona_a].name
                b_name = self.personas[rel.persona_b].name
                print(f"  {a_name} <-> {b_name}: "
                      f"familiarity={rel.familiarity:.3f} trust={rel.trust:.3f} "
                      f"interactions={rel.interaction_count}")
            for pid, sec in self.secrets.items():
                name = self.personas[pid].name
                knowers = [self.personas[k].name for k in sec.known_by if k != pid]
                print(f"  {name}'s secret ({sec.content_tag}): "
                      f"known by {knowers if knowers else 'no one'}")
            if self.rumors:
                print(f"\n  === Rumors ({len(self.rumors)}) ===")
                for r in self.rumors:
                    about = self.personas[r.about_id].name if r.about_id in self.personas else "?"
                    knowers = [self.personas[k].name[:4] for k in r.known_by if k in self.personas]
                    print(f"  [{about}'s {r.content_tag}] acc={r.accuracy:.0%} "
                          f"spread={r.spread_count} known={knowers}")

        return self.log

    def tick_many(self, n_ticks: int) -> list[dict]:
        results: list[dict] = []
        for _ in range(n_ticks):
            results.append(self.tick())
        return results


if __name__ == "__main__":
    engine = MultiTickEngine()
    engine.run(n_ticks=200)
