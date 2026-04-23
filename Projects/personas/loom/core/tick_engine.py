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
        """행동 결과 → 보상 신호 (Nomos 등가).

        v2: eat 편향 교정 — 중립 지대 제거, work 보상 완화, idle 벌점 강화.
        원칙: 적절한 때에 적절한 행동 = 보상, 부적절하면 = 벌점 (빈틈 없이).
        """
        reward = 0.0
        hunger = float(self.inner.oyok[0])
        sleepiness = float(self.inner.oyok[1])

        # ── 생존 보상/벌점 ──
        if energy < 0.1:
            reward -= 0.5  # 에너지 고갈 = 큰 벌점

        # ── eat: 배고픔 연속 스케일 보상 ──
        if action == "eat":
            # hunger 0.0→-0.3, 0.3→0.0(중립), 0.5→+0.2, 0.7→+0.5, 1.0→+0.8
            reward += (hunger - 0.3) * 1.2  # 연속 함수: 배고프면 보상, 안 배고프면 벌점

        # ── sleep: 피로도 연속 스케일 ──
        elif action == "sleep":
            if energy < 0.3:
                reward += 0.3  # 피곤할 때 잠 = 보상
            elif energy > 0.7:
                reward -= 0.3  # 에너지 충분한데 잠 = 강한 벌점

        # ── work: 조건 완화 (에너지만 체크) ──
        elif action == "work":
            if energy > 0.3:
                reward += 0.3  # 에너지 있으면 일 = 보상 (주요 행동)
            else:
                reward -= 0.1  # 에너지 부족한데 일 = 약한 벌점

        # ── explore: 여유가 있으면 보상 ──
        elif action == "explore":
            if energy > 0.5 and hunger < 0.5:
                reward += 0.2  # 여유 있을 때 탐험
            else:
                reward -= 0.05

        # ── idle: 강한 벌점 (무행동 억제) ──
        elif action == "idle":
            reward -= 0.15  # 아무것도 안 함 = 더 강한 벌점

        return np.clip(reward, -1.0, 1.0)

    def _sleep_tick(self) -> dict:
        """수면 중 처리 + Phase 3 꿈 replay + 기억 상태기계."""
        self.inner.sleep_ticks_remaining -= 1
        sleep_phase = "nrem" if self.inner.sleep_ticks_remaining > 1 else "rem"

        # ATP 회복
        recovery = 0.15
        self.inner.energy_pool = min(
            self.inner.max_capacity, self.inner.energy_pool + recovery
        )

        # 수면욕 감소
        self.inner.oyok[1] = max(0.0, self.inner.oyok[1] - 0.15)

        # ── Phase 3: 꿈 + 기억 상태기계 ──
        dream_action = None
        memory_events = []

        if sleep_phase == "nrem":
            # NREM: 시냅스 하향 정규화 (SHY) — 약한 연결만 약화
            exc_w = self.brain.snn.weights[:self.brain.snn.n_exc, :]
            weak_mask = (exc_w > 0) & (exc_w < 0.05)
            exc_w[weak_mask] *= 0.995
            prune_mask = (np.abs(self.brain.snn.weights) < 0.0005) & (self.brain.snn.weights != 0)
            self.brain.snn.weights[prune_mask] = 0

            # ── 기억 안정화: FRESH/LABILE → CONSOLIDATED/RECONSOLIDATED ──
            for ep in self.inner.episodes:
                if ep.state in ("FRESH", "LABILE"):
                    old_state = ep.state
                    ep.consolidate()
                    if old_state != ep.state:
                        memory_events.append(f"{old_state}→{ep.state}")

            # ── 트라우마 억압 판정 ──
            self.inner.try_suppress_traumatic()

        else:
            # REM: 기억 replay — 인출 가능한 기억만 대상
            recallable = self.inner.get_recallable_episodes()
            if recallable:
                sorted_eps = sorted(recallable, key=lambda e: e.salience, reverse=True)
                top_eps = sorted_eps[:3]
                for ep in top_eps:
                    # ── 기억 재통합: 인출 시 현재 감정이 과거를 오염 ──
                    ep.recall(current_tick=self.time.tick,
                              current_emotion=self.inner.chiljeong)
                    # 꿈 = 기억의 재경험
                    self.inner.chiljeong = (
                        self.inner.chiljeong * 0.5 + ep.emotion_snapshot * 0.5
                    ).astype(np.float16)
                    dream_action = ep.action

                # 수면 중 망각 (EXTINCT 우선 제거)
                if len(self.inner.episodes) > 30:
                    self.inner.episodes.sort(
                        key=lambda e: (
                            0 if e.state == "EXTINCT" else 2,
                            e.salience
                        )
                    )
                    self.inner.episodes = self.inner.episodes[-30:]

            # ── 억압 기억 재출현 판정 ──
            resurfaced = self.inner.try_resurface_memories()
            if resurfaced:
                for ep in resurfaced:
                    # 재출현 = 악몽 (두려움 급증)
                    self.inner.chiljeong[3] = min(1.0, self.inner.chiljeong[3] + 0.4)
                    dream_action = ep.action
                    memory_events.append(f"RESURFACE:{ep.action}@{ep.tick}")

        # ── LABILE 소멸 판정 ──
        self.inner.check_memory_extinction(self.time.tick)

        # 기상 판정
        if self.inner.sleep_ticks_remaining <= 0:
            self.inner.is_sleeping = False
            self.brain.snn.clear_reward()

        entry = {
            "tick": self.time.tick,
            "hour": self.time.game_hour,
            "day": self.time.game_day,
            "action": f"dream:{dream_action}" if dream_action else f"sleep:{sleep_phase}",
            "intensity": 0,
            "energy": round(self.inner.energy_pool, 3),
            "hunger": round(float(self.inner.oyok[0]), 3),
            "sleepiness": round(float(self.inner.oyok[1]), 3),
            "sleeping": True,
            "firing_rate": 0.0,
        }
        if memory_events:
            entry["memory_events"] = memory_events
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
