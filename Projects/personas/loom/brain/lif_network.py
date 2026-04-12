"""
PersonaBrain Phase 0: 최소 LIF (Leaky Integrate-and-Fire) 네트워크.

1,000개 뉴런, E/I balance (80% 흥분 / 20% 억제), refractory period.
STDP는 Phase 1에서 추가.
"""
from __future__ import annotations
import numpy as np


class LIFNetwork:
    """Leaky Integrate-and-Fire 스파이킹 뉴런 네트워크."""

    def __init__(self, n_neurons: int = 1_000, e_ratio: float = 0.8, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n = n_neurons
        self.n_exc = int(n_neurons * e_ratio)
        self.n_inh = n_neurons - self.n_exc

        # 뉴런 상태
        self.v = np.zeros(n_neurons, dtype=np.float32)       # 막전위
        self.threshold = np.full(n_neurons, 1.0, dtype=np.float32)  # 발화 임계값
        self.reset_v = 0.0
        self.leak = 0.95                                     # 누출 계수 (매 스텝 5% 감쇠)

        # Refractory period
        self.refractory = np.zeros(n_neurons, dtype=np.int8)  # 남은 불응기 (스텝)
        self.refractory_period = 2  # 2 스텝 불응기

        # 시냅스 가중치 (희소 연결, ~5% 연결 확률)
        connectivity = 0.05
        self.weights = self.rng.standard_normal((n_neurons, n_neurons)).astype(np.float32)
        mask = self.rng.random((n_neurons, n_neurons)) < connectivity
        self.weights *= mask

        # E/I 부호: 흥분 뉴런은 양수, 억제 뉴런은 음수
        self.weights[self.n_exc:, :] = -np.abs(self.weights[self.n_exc:, :])
        self.weights[:self.n_exc, :] = np.abs(self.weights[:self.n_exc, :])

        # 자기 연결 제거
        np.fill_diagonal(self.weights, 0)

        # 스케일링 (안정성)
        self.weights *= 0.1

        # 스파이크 기록
        self.spikes = np.zeros(n_neurons, dtype=np.bool_)

    def step(self, external_input: np.ndarray | None = None) -> np.ndarray:
        """1 시뮬레이션 스텝 실행. 스파이크 배열 반환."""
        # 불응기 중인 뉴런은 입력 무시
        active = self.refractory == 0

        # 누출 (Leaky)
        self.v *= self.leak

        # 시냅스 입력 (이전 스파이크로부터)
        if np.any(self.spikes):
            synaptic = self.weights[:, self.spikes].sum(axis=1)
            self.v += synaptic * active

        # 외부 입력
        if external_input is not None:
            self.v += external_input * active

        # 발화 판정
        self.spikes = (self.v >= self.threshold) & active

        # 발화한 뉴런: 리셋 + 불응기
        self.v[self.spikes] = self.reset_v
        self.refractory[self.spikes] = self.refractory_period

        # 불응기 카운트다운
        self.refractory = np.maximum(self.refractory - 1, 0)

        return self.spikes.copy()

    def get_firing_rate(self) -> float:
        """현재 스텝의 발화율."""
        return float(self.spikes.sum()) / self.n

    def get_exc_inh_rates(self) -> tuple[float, float]:
        """흥분/억제 뉴런 별도 발화율."""
        exc_rate = float(self.spikes[:self.n_exc].sum()) / self.n_exc
        inh_rate = float(self.spikes[self.n_exc:].sum()) / self.n_inh
        return exc_rate, inh_rate
