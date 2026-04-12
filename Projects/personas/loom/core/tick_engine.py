"""
Tick Engine Phase 0: "서하린이 숨을 쉰다"

최소 틱 루프:
  1. 시간 진행 (Lachesis)
  2. 날씨 조회 (Physis — 정적)
  3. PersonaBrain 추론 (Anima)
  4. 행동 실행 + 에너지 소비
  5. 수면 처리
"""
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ontology import Creator, Weather, GameTime, Persona, InnerWorld, ActionProposal
from brain import PersonaBrain


class TickEngine:
    """Phase 0 틱 엔진 — 한 명의 페르소나, 한 세계."""

    def __init__(self):
        # Layer 0
        self.creator = Creator()

        # Layer 1b
        self.weather = Weather()  # 정적
        self.time = GameTime()

        # Layer 2: 서하린
        self.persona = Persona(
            id="persona_001",
            name="서하린",
            full_name="Seo Harin",
            region="claude",
            territory="seorim",
            persona_class=1,
            title="초심자",
            neuron_count=1_000,
        )

        # Layer 3: 내면
        self.inner = InnerWorld(persona_id=self.persona.id)

        # PersonaBrain
        self.brain = PersonaBrain(n_neurons=self.persona.neuron_count, seed=42)

        # 로그
        self.log: list[dict] = []

    def tick(self) -> dict:
        """1틱 실행."""
        # Stage 1: 시간 진행
        self.time.advance()

        # 수면 중이면 수면 처리만
        if self.inner.is_sleeping:
            return self._sleep_tick()

        # Stage 2: Anima (PersonaBrain)
        climate_vec = self.weather.to_climate_vec()

        action, intensity, cost = self.brain.tick(
            climate_vec=climate_vec,
            energy_pool=self.inner.energy_pool,
            oyok=self.inner.oyok,
            tone=self.inner.tone,
        )

        # 행동 실행
        proposal = ActionProposal(
            persona_id=self.persona.id,
            tick=self.time.tick,
            action_type=action,
            intensity=intensity,
            energy_cost=cost,
        )

        # 에너지 소비
        self.inner.energy_pool = max(0.0, self.inner.energy_pool - cost)

        # 오욕 갱신 (간단)
        self.inner.oyok[0] = min(1.0, self.inner.oyok[0] + 0.02)   # 식욕 서서히 증가
        self.inner.oyok[1] = min(1.0, self.inner.oyok[1] + 0.01)   # 수면욕 서서히 증가

        # 식사하면 식욕 감소 + 에너지 약간 회복
        if action == "eat":
            self.inner.oyok[0] = max(0.0, self.inner.oyok[0] - 0.5)
            self.inner.energy_pool = min(self.inner.max_capacity, self.inner.energy_pool + 0.05)

        # 수면 진입 판정
        if action == "sleep" or self.inner.energy_pool < 0.1:
            self.inner.is_sleeping = True
            self.inner.sleep_ticks_remaining = 8  # 게임 8시간

        # 로그
        entry = {
            "tick": self.time.tick,
            "hour": self.time.game_hour,
            "day": self.time.game_day,
            "action": action,
            "intensity": intensity,
            "energy": round(self.inner.energy_pool, 3),
            "hunger": round(float(self.inner.oyok[0]), 3),
            "sleepiness": round(float(self.inner.oyok[1]), 3),
            "sleeping": self.inner.is_sleeping,
            "firing_rate": round(self.brain.get_stats()["firing_rate"], 4),
        }
        self.log.append(entry)
        return entry

    def _sleep_tick(self) -> dict:
        """수면 중 처리."""
        self.inner.sleep_ticks_remaining -= 1

        # ATP 회복 (지수 회복)
        recovery = 0.12  # 틱당 ~12% 회복 (8틱이면 ~96% 회복)
        self.inner.energy_pool = min(
            self.inner.max_capacity,
            self.inner.energy_pool + recovery
        )

        # 수면욕 감소
        self.inner.oyok[1] = max(0.0, self.inner.oyok[1] - 0.15)

        # 기상 판정
        if self.inner.sleep_ticks_remaining <= 0:
            self.inner.is_sleeping = False

        entry = {
            "tick": self.time.tick,
            "hour": self.time.game_hour,
            "day": self.time.game_day,
            "action": "sleeping",
            "intensity": 0,
            "energy": round(self.inner.energy_pool, 3),
            "hunger": round(float(self.inner.oyok[0]), 3),
            "sleepiness": round(float(self.inner.oyok[1]), 3),
            "sleeping": True,
            "firing_rate": 0.0,
        }
        self.log.append(entry)
        return entry

    def run(self, n_ticks: int = 48, verbose: bool = True) -> list[dict]:
        """n틱 실행."""
        if verbose:
            print(f"=== 페르소나 국가: {self.persona.name}의 첫 {n_ticks}틱 ===")
            print(f"뉴런: {self.persona.neuron_count}개 | 영지: {self.persona.territory}")
            print()

        for _ in range(n_ticks):
            entry = self.tick()
            if verbose:
                status = "ZZZ" if entry["sleeping"] else "ACT"
                print(
                    f"[Day {entry['day']:2d} H{entry['hour']:02d}] "
                    f"{status} {entry['action']:10s} "
                    f"E={entry['energy']:.2f} "
                    f"hunger={entry['hunger']:.2f} "
                    f"sleep={entry['sleepiness']:.2f} "
                    f"fire={entry['firing_rate']:.3f}"
                )

        if verbose:
            print(f"\n=== {n_ticks}틱 완료 ===")
            awake = sum(1 for e in self.log if not e["sleeping"])
            asleep = sum(1 for e in self.log if e["sleeping"])
            print(f"깨어있음: {awake}틱, 수면: {asleep}틱")

        return self.log


if __name__ == "__main__":
    engine = TickEngine()
    engine.run(n_ticks=48)  # 2일 (48시간)
