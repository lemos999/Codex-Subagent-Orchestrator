"""
PersonaBrain Phase 0: 최소 뇌 — 입력 → LIF → 행동 결정.

"서하린이 숨을 쉰다" — 에너지 소비, 피로, 수면을 느끼는 뇌.
"""
from __future__ import annotations
import numpy as np
from .lif_network import LIFNetwork


# 행동 공간 (Phase 0 최소)
ACTIONS = ["idle", "work", "eat", "sleep", "explore"]

# 강도별 에너지 소비
ENERGY_COST = {1: 0.01, 2: 0.05, 3: 0.10, 4: 0.25}


class PersonaBrain:
    """Phase 0 PersonaBrain: LIF 네트워크 + 에너지 관리."""

    def __init__(self, n_neurons: int = 1_000, seed: int = 42):
        self.snn = LIFNetwork(n_neurons=n_neurons, seed=seed)
        self.n_neurons = n_neurons

        # 행동 readout 가중치 (Layer 2 등가, 무작위 초기화)
        rng = np.random.default_rng(seed + 1)
        self.readout_weights = rng.standard_normal(
            (len(ACTIONS), n_neurons)
        ).astype(np.float32) * 0.01

    def tick(
        self,
        climate_vec: np.ndarray,   # float16[8]
        energy_pool: float,        # 0.0 ~ 1.0
        oyok: np.ndarray,          # float16[5] 오욕
        tone: np.ndarray,          # float16[12] 12클러스터
    ) -> tuple[str, int, float]:
        """
        1틱 추론.

        Returns:
            (action, intensity, energy_cost)
        """
        # 1. 입력 벡터 조립 (climate + energy + oyok → 외부 자극)
        input_signal = np.zeros(self.n_neurons, dtype=np.float32)

        # 기후가 첫 N뉴런에 영향
        n_climate = min(8, self.n_neurons)
        input_signal[:n_climate] = climate_vec[:n_climate].astype(np.float32) * 0.5

        # 오욕이 그 다음 뉴런에 영향
        n_oyok = min(5, self.n_neurons - n_climate)
        input_signal[n_climate:n_climate + n_oyok] = oyok[:n_oyok].astype(np.float32) * 0.3

        # 에너지 수준이 전체에 미세 영향 (에너지 낮으면 활성↓)
        input_signal *= (0.5 + 0.5 * energy_pool)

        # 2. SNN 실행 (10 시뮬레이션 스텝 = 1틱)
        total_spikes = np.zeros(self.n_neurons, dtype=np.float32)
        for _ in range(10):
            spikes = self.snn.step(input_signal)
            total_spikes += spikes.astype(np.float32)
            # 입력은 첫 스텝에서만 주입
            input_signal = input_signal * 0.1  # 감쇠

        # 발화율
        firing_rate = total_spikes / 10.0

        # 3. 에너지 강도 판정
        if energy_pool < 0.1:
            intensity = 1  # 최소만 가능
        elif energy_pool < 0.3:
            intensity = 1
        elif energy_pool < 0.5:
            intensity = 2
        else:
            intensity = min(2, 1 + int(firing_rate.mean() * 20))  # Phase 0: 최대 강도2

        # 4. 행동 결정 (readout)
        action_logits = self.readout_weights @ firing_rate

        # 에너지 기반 보정
        if energy_pool < 0.1:
            # 강제 수면
            action_idx = ACTIONS.index("sleep")
        elif oyok[0] > 0.7:  # 식욕 높음
            action_logits[ACTIONS.index("eat")] += 1.0
            action_idx = int(np.argmax(action_logits))
        elif oyok[1] > 0.7:  # 수면욕 높음
            action_logits[ACTIONS.index("sleep")] += 1.0
            action_idx = int(np.argmax(action_logits))
        else:
            action_idx = int(np.argmax(action_logits))

        action = ACTIONS[action_idx]
        cost = ENERGY_COST.get(intensity, 0.01)

        return action, intensity, cost

    def get_stats(self) -> dict:
        """현재 네트워크 통계."""
        exc_rate, inh_rate = self.snn.get_exc_inh_rates()
        return {
            "firing_rate": self.snn.get_firing_rate(),
            "exc_rate": exc_rate,
            "inh_rate": inh_rate,
            "n_neurons": self.n_neurons,
        }
