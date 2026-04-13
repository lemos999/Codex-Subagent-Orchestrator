"""
PersonaBrain 실시간 대시보드 서버.

WebSocket으로 매 틱의 뉴런 상태를 브라우저에 전송.
"""
from __future__ import annotations
import asyncio
import json
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import websockets
import numpy as np
import numpy as np
from ontology import Creator, Weather, GameTime, Persona, InnerWorld, ActionProposal
from brain import PersonaBrain
from brain.lif_network import LIFNetwork


class DashboardEngine:
    """틱 엔진 + WebSocket 대시보드."""

    def __init__(self):
        self.weather = Weather()
        self.time = GameTime()
        self.persona = Persona(
            id="persona_001", name="Seo Harin", full_name="Seo Harin",
            region="claude", territory="seorim", persona_class=1, neuron_count=1_000,
        )
        self.inner = InnerWorld(persona_id=self.persona.id)
        self.brain = PersonaBrain(n_neurons=self.persona.neuron_count, seed=42)
        self.clients: set = set()
        self.running = False
        self.tick_interval = 0.5  # 0.5초마다 1틱 (실시간 관찰용)

    def get_neuron_snapshot(self) -> dict:
        """현재 뉴런 네트워크의 전체 스냅샷."""
        snn = self.brain.snn
        n = snn.n

        # 뉴런 상태
        voltages = snn.v.tolist()
        spikes = snn.spikes.astype(int).tolist()
        refractory = snn.refractory.tolist()

        # 연결 정보 (상위 연결만 — 전체는 너무 큼)
        # 각 뉴런의 가장 강한 입력 연결 5개
        connections = []
        weight_matrix = snn.weights
        for i in range(min(n, 200)):  # 처음 200뉴런만 (성능)
            row = weight_matrix[i]
            nonzero = np.nonzero(row)[0]
            if len(nonzero) > 0:
                top_k = min(3, len(nonzero))
                top_idx = nonzero[np.argsort(np.abs(row[nonzero]))[-top_k:]]
                for j_idx in range(len(top_idx)):
                    j = int(top_idx[j_idx])
                    w = float(row[j])
                    connections.append({"from": j, "to": i, "weight": round(w, 4)})

        # 흥분/억제 분류
        exc_count = snn.n_exc
        inh_count = snn.n_inh

        # 발화 통계
        exc_spikes = int(snn.spikes[:exc_count].sum())
        inh_spikes = int(snn.spikes[exc_count:].sum())

        return {
            "n_neurons": n,
            "n_exc": exc_count,
            "n_inh": inh_count,
            "voltages": voltages[:200],  # 처음 200개만
            "spikes": spikes[:200],
            "refractory": refractory[:200],
            "exc_spikes": exc_spikes,
            "inh_spikes": inh_spikes,
            "firing_rate": round(float(snn.spikes.sum()) / n, 4),
            "connections": connections[:500],  # 상위 500개 연결
            "threshold": float(snn.threshold[0]),
        }

    def tick(self) -> dict:
        """1틱 실행 + 전체 상태 반환."""
        self.time.advance()

        if self.inner.is_sleeping:
            self.inner.sleep_ticks_remaining -= 1
            sleep_phase = "nrem" if self.inner.sleep_ticks_remaining > 1 else "rem"
            self.inner.energy_pool = min(self.inner.max_capacity, self.inner.energy_pool + 0.15)
            self.inner.oyok[1] = max(0.0, self.inner.oyok[1] - 0.15)

            # Phase 3: 꿈
            dream_action = None
            if sleep_phase == "nrem":
                self.brain.snn.weights[:self.brain.snn.n_exc, :] *= 0.998
                mask = np.abs(self.brain.snn.weights) < 0.001
                self.brain.snn.weights[mask] = 0
            else:
                if self.inner.episodes:
                    sorted_eps = sorted(self.inner.episodes, key=lambda e: e.salience, reverse=True)
                    for ep in sorted_eps[:3]:
                        self.inner.chiljeong = (self.inner.chiljeong * 0.5 + ep.emotion_snapshot * 0.5).astype(np.float16)
                        ep.recall_count += 1
                        dream_action = ep.action
                    if len(self.inner.episodes) > 30:
                        self.inner.episodes.sort(key=lambda e: e.salience, reverse=True)
                        self.inner.episodes = self.inner.episodes[:30]

            if self.inner.sleep_ticks_remaining <= 0:
                self.inner.is_sleeping = False
                self.brain.snn.clear_reward()

            action = f"dream:{dream_action}" if dream_action else f"sleep:{sleep_phase}"
            intensity, cost = 0, 0.0
            firing_rate = 0.0
        else:
            climate_vec = self.weather.to_climate_vec()
            action, intensity, cost = self.brain.tick(
                climate_vec=climate_vec,
                energy_pool=self.inner.energy_pool,
                oyok=self.inner.oyok,
                tone=self.inner.tone,
            )
            prev_energy = self.inner.energy_pool
            self.inner.energy_pool = max(0.0, self.inner.energy_pool - cost)
            self.inner.oyok[0] = min(1.0, self.inner.oyok[0] + 0.02)
            self.inner.oyok[1] = min(1.0, self.inner.oyok[1] + 0.01)
            if action == "eat":
                self.inner.oyok[0] = max(0.0, self.inner.oyok[0] - 0.5)
                self.inner.energy_pool = min(self.inner.max_capacity, self.inner.energy_pool + 0.05)

            # Phase 2: 도파민 RL (tick_engine과 동일)
            reward = self._compute_reward(action, self.inner.energy_pool, prev_energy)
            self.brain.snn.apply_reward(reward)

            # Phase 1: 감정 + tone + 기억
            self.inner.update_emotion(action, self.inner.energy_pool, prev_energy)
            self.inner.update_tone_from_emotion()

            from ontology import EpisodeTrace
            episode = EpisodeTrace(
                tick=self.time.tick, action=action,
                emotion_snapshot=self.inner.chiljeong.copy(),
                energy_at_time=self.inner.energy_pool,
            )
            episode.compute_salience(self.inner.chiljeong)
            self.inner.add_episode(episode)

            if self.inner.energy_pool < 0.1:
                self.inner.is_sleeping = True
                self.inner.sleep_ticks_remaining = 6
            firing_rate = self.brain.get_stats()["firing_rate"]

        neuron_snapshot = self.get_neuron_snapshot() if not self.inner.is_sleeping else None
        try:
            reward_val = reward
        except UnboundLocalError:
            reward_val = 0.0

        return {
            "tick": self.time.tick,
            "hour": self.time.game_hour,
            "day": self.time.game_day,
            "season": self.time.season,
            "persona": {
                "name": self.persona.name,
                "class": self.persona.persona_class,
                "region": self.persona.region,
                "territory": self.persona.territory,
            },
            "inner": {
                "energy": round(self.inner.energy_pool, 4),
                "tone": self.inner.tone_dict(),
                "chiljeong": self.inner.chiljeong.tolist(),
                "oyok": self.inner.oyok.tolist(),
                "sleeping": self.inner.is_sleeping,
                "emotions": self.inner.emotion_dict(),
                "memories": len(self.inner.episodes),
            },
            "action": {
                "type": action,
                "intensity": intensity,
                "cost": cost,
                "reward": round(reward_val, 3),
            },
            "brain": {
                "firing_rate": round(firing_rate, 4),
                "stats": self.brain.get_stats() if not self.inner.is_sleeping else None,
                "neurons": neuron_snapshot,
            },
        }

    def _compute_reward(self, action, energy, prev_energy):
        reward = 0.0
        hunger = float(self.inner.oyok[0])
        if energy < 0.1: reward -= 0.5
        elif energy < prev_energy - 0.1: reward -= 0.1
        if action == "eat" and hunger > 0.5: reward += 0.5
        elif action == "eat" and hunger < 0.2: reward -= 0.2
        if action == "sleep" and energy < 0.3: reward += 0.3
        elif action == "sleep" and energy > 0.7: reward -= 0.2
        if action == "work" and energy > 0.5 and hunger < 0.5: reward += 0.2
        if action == "explore" and energy > 0.6: reward += 0.1
        if action == "idle": reward -= 0.05
        return max(-1.0, min(1.0, reward))

    async def broadcast(self, data: dict):
        if not self.clients:
            return
        msg = json.dumps(data, ensure_ascii=False)
        dead = set()
        for c in list(self.clients):  # list() 복사로 iteration 안전
            try:
                await c.send(msg)
            except Exception:
                dead.add(c)
        self.clients -= dead

    async def handler(self, ws):
        self.clients.add(ws)
        try:
            async for msg in ws:  # noqa
                cmd = json.loads(msg)
                if cmd.get("type") == "set_speed":
                    self.tick_interval = max(0.1, cmd.get("interval", 0.5))
                elif cmd.get("type") == "pause":
                    self.running = False
                elif cmd.get("type") == "resume":
                    self.running = True
                elif cmd.get("type") == "step":
                    state = self.tick()
                    await ws.send(json.dumps(state, ensure_ascii=False))
        finally:
            self.clients.discard(ws)

    async def tick_loop(self):
        self.running = True
        while True:
            if self.running:
                state = self.tick()
                await self.broadcast(state)
            await asyncio.sleep(self.tick_interval)

    async def start(self, host="localhost", port=8765):
        print(f"PersonaBrain Dashboard: ws://{host}:{port}")
        print(f"Open dashboard/index.html in browser")
        async with websockets.serve(self.handler, host, port):
            await self.tick_loop()


if __name__ == "__main__":
    engine = DashboardEngine()
    asyncio.run(engine.start())
