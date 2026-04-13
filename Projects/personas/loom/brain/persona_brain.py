"""
PersonaBrain Phase 0: 최소 뇌 — 입력 → LIF → 행동 결정.

"서하린이 숨을 쉰다" — 에너지 소비, 피로, 수면을 느끼는 뇌.
"""
from __future__ import annotations
import os
import numpy as np
from .lif_network import LIFNetwork


# 행동 공간 (Phase 0 최소)
ACTIONS = ["idle", "work", "eat", "sleep", "explore"]

# 강도별 에너지 소비
# 강도별 에너지 소비 (16~18틱 활동 후 수면을 목표)
# 강도1 주로 사용: 0.05/틱 × 18틱 = 0.9 소모 → energy 0.1 → 수면
ENERGY_COST = {1: 0.05, 2: 0.08, 3: 0.12, 4: 0.25}


class PersonaBrain:
    """Phase 0 PersonaBrain: LIF 네트워크 + 에너지 관리."""

    def __init__(self, n_neurons: int = 1_000, seed: int = 42):
        self.snn = LIFNetwork(n_neurons=n_neurons, seed=seed)
        self.n_neurons = n_neurons

        # 행동 readout 가중치 (Layer 2)
        model_path = os.path.join(os.path.dirname(__file__), "..", "data", "models", "readout_weights_v1.npy")
        if os.path.exists(model_path):
            self.readout_weights = np.load(model_path)
            self._teacher_trained = True
        else:
            rng = np.random.default_rng(seed + 1)
            self.readout_weights = rng.standard_normal(
                (len(ACTIONS), n_neurons)
            ).astype(np.float32) * 0.01
            self._teacher_trained = False

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

        # 기후가 넓은 뉴런 집단에 확산 (실제 뇌: 감각 입력은 넓게 퍼짐)
        n_input = min(100, self.n_neurons)  # 첫 100뉴런이 감각 입력 수신
        rng = np.random.default_rng(self.snn.rng.integers(0, 2**31))

        # 기후 → 감각 뉴런에 분산 주입
        for i in range(min(8, n_input)):
            spread = rng.choice(n_input, size=8, replace=False)
            input_signal[spread] += float(climate_vec[i]) * 0.2

        # 오욕 → 동기 뉴런에 주입 (욕구가 높을수록 강한 신호)
        for i in range(5):
            if float(oyok[i]) > 0.1:
                spread = rng.choice(range(n_input, min(n_input + 50, self.n_neurons)), size=3, replace=False)
                input_signal[spread] += float(oyok[i]) * 0.3

        # Phase 1: 12클러스터 tone이 뉴런 입력에 영향
        # tone > 1.0이면 해당 영역 활성↑, < 1.0이면 ↓
        tone_f32 = tone.astype(np.float32)
        tone_mean = float(tone_f32.mean())
        # tone이 전체 입력 강도를 조절 (기분 좋으면 활성↑, 나쁘면 ↓)
        tone_gain = 0.8 + 0.2 * tone_mean  # 0.8~1.2 범위

        # A(Acute/NE, idx=4)가 높으면 각성↑ → 입력 강화
        acute_boost = float(tone_f32[4]) - 1.0  # 0이면 기본, 양수면 강화
        # I(Inhibition/GABA, idx=9)가 높으면 억제↑ → 입력 약화
        inhibit_dampen = float(tone_f32[9]) - 1.0  # 양수면 억제

        # 배경 노이즈 + tone 영향
        noise_scale = max(0.02, 0.045 * tone_gain * (1.0 + acute_boost * 0.3) * (1.0 - inhibit_dampen * 0.3))
        input_signal += rng.exponential(noise_scale, self.n_neurons).astype(np.float32)

        # 에너지 수준이 전체에 영향
        input_signal *= (0.3 + 0.7 * energy_pool)

        # 2. SNN 실행 (10 시뮬레이션 스텝 = 1틱)
        # 매 스텝 동일한 입력 유지 (뇌: 자극은 지속됨, 즉시 사라지지 않음)
        total_spikes = np.zeros(self.n_neurons, dtype=np.float32)
        base_input = input_signal.copy()
        for step in range(10):
            # 지속 입력 + 스텝별 노이즈
            step_input = base_input * 0.7 + rng.exponential(0.03, self.n_neurons).astype(np.float32)
            spikes = self.snn.step(step_input)
            total_spikes += spikes.astype(np.float32)

        # 발화율
        firing_rate = total_spikes / 10.0

        # 3. 에너지 강도 판정 (Phase 0: 강도1만 사용)
        intensity = 1

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
