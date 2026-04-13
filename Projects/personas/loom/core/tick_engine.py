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

import numpy as np
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
        prev_energy = self.inner.energy_pool
        self.inner.energy_pool = max(0.0, self.inner.energy_pool - cost)

        # 오욕 갱신
        self.inner.oyok[0] = min(1.0, self.inner.oyok[0] + 0.02)   # 식욕
        self.inner.oyok[1] = min(1.0, self.inner.oyok[1] + 0.01)   # 수면욕

        # 식사하면 식욕 감소 + 에너지 약간 회복
        if action == "eat":
            self.inner.oyok[0] = max(0.0, self.inner.oyok[0] - 0.5)
            self.inner.energy_pool = min(self.inner.max_capacity, self.inner.energy_pool + 0.05)

        # ── Phase 2: 도파민 RL (보상 신호 계산 + 주입) ──
        reward = self._compute_reward(action, self.inner.energy_pool, prev_energy)
        self.brain.snn.apply_reward(reward)

        # ── Phase 1: 감정 갱신 ──
        self.inner.update_emotion(action, self.inner.energy_pool, prev_energy)

        # ── Phase 1: 감정 → tone 반영 ──
        self.inner.update_tone_from_emotion()

        # ── Phase 1: 에피소드 기억 저장 ──
        from ontology import EpisodeTrace
        episode = EpisodeTrace(
            tick=self.time.tick,
            action=action,
            emotion_snapshot=self.inner.chiljeong.copy(),
            energy_at_time=self.inner.energy_pool,
        )
        episode.compute_salience(self.inner.chiljeong)
        self.inner.add_episode(episode)

        # 수면 진입 판정
        if self.inner.energy_pool < 0.1:
            self.inner.is_sleeping = True
            self.inner.sleep_ticks_remaining = 6

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
            # Phase 1 추가
            "emotions": self.inner.emotion_dict(),
            "tone_V": round(float(self.inner.tone[0]), 3),
            "tone_A": round(float(self.inner.tone[4]), 3),
            "tone_I": round(float(self.inner.tone[9]), 3),
            "memories": len(self.inner.episodes),
            "reward": round(reward, 3),
        }
        self.log.append(entry)
        return entry

    def _compute_reward(self, action: str, energy: float, prev_energy: float) -> float:
        """행동 결과 → 보상 신호 (Nomos 등가)."""
        reward = 0.0
        hunger = float(self.inner.oyok[0])

        # 생존 보상/벌점
        if energy < 0.1:
            reward -= 0.5  # 에너지 고갈 = 큰 벌점
        elif energy < prev_energy - 0.1:
            reward -= 0.1  # 에너지 급락

        # 행동별 보상
        if action == "eat" and hunger > 0.5:
            reward += 0.5  # 배고플 때 먹음 = 큰 보상
        elif action == "eat" and hunger < 0.2:
            reward -= 0.2  # 안 배고픈데 먹음 = 벌점 (낭비)

        if action == "sleep" and energy < 0.3:
            reward += 0.3  # 피곤할 때 잠 = 보상
        elif action == "sleep" and energy > 0.7:
            reward -= 0.2  # 에너지 충분한데 잠 = 벌점

        if action == "work" and energy > 0.5 and hunger < 0.5:
            reward += 0.2  # 여유 있을 때 일 = 보상

        if action == "explore" and energy > 0.6:
            reward += 0.1  # 여유 있을 때 탐험 = 소량 보상

        if action == "idle":
            reward -= 0.05  # 아무것도 안 함 = 미세 벌점

        return np.clip(reward, -1.0, 1.0)

    def _sleep_tick(self) -> dict:
        """수면 중 처리."""
        self.inner.sleep_ticks_remaining -= 1

        # ATP 회복 (6틱에 ~90% 회복)
        recovery = 0.15
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
                emo = entry.get("emotions", {})
                joy = emo.get("joy", 0)
                anger = emo.get("anger", 0)
                fear = emo.get("fear", 0)
                desire = emo.get("desire", 0)
                mem = entry.get("memories", 0)
                rw = entry.get("reward", 0)
                rw_str = f"+{rw:.1f}" if rw >= 0 else f"{rw:.1f}"
                print(
                    f"[D{entry['day']:2d} H{entry['hour']:02d}] "
                    f"{status} {entry['action']:8s} "
                    f"E={entry['energy']:.2f} "
                    f"h={entry['hunger']:.1f} "
                    f"fr={entry['firing_rate']:.3f} "
                    f"R={rw_str:>5s} "
                    f"joy={joy:.1f} fear={fear:.1f} "
                    f"mem={mem}"
                )

        if verbose:
            print(f"\n=== {n_ticks}틱 완료 ===")
            awake = sum(1 for e in self.log if not e["sleeping"])
            asleep = sum(1 for e in self.log if e["sleeping"])
            print(f"깨어있음: {awake}틱, 수면: {asleep}틱")

        return self.log


if __name__ == "__main__":
    engine = TickEngine()
    log = engine.run(n_ticks=100)  # 100틱 안정화 검증

    # Phase 0 완성 기준 검증
    awake = [e for e in log if not e["sleeping"]]
    asleep = [e for e in log if e["sleeping"]]
    avg_fr = sum(e["firing_rate"] for e in awake) / len(awake) if awake else 0
    print(f"\n--- Phase 0 검증 ---")
    print(f"평균 발화율: {avg_fr:.4f} (목표: 0.01~0.05)")
    print(f"활동: {len(awake)}틱, 수면: {len(asleep)}틱")
    if awake:
        print(f"수면 주기: ~{len(awake) // max(1, len([e for e in log if e['action']=='sleeping' and log[max(0,log.index(e)-1)]['action']!='sleeping']))}틱 활동 후 수면")
    print(f"STDP: {'활성' if hasattr(engine.brain.snn, 'spike_trace') else '미구현'}")
    if 0.01 <= avg_fr <= 0.05:
        print(">>> Phase 0 발화율 기준 PASS")
    else:
        print(f">>> Phase 0 발화율 기준 FAIL (현재 {avg_fr:.4f})")
