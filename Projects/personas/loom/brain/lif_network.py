"""
PersonaBrain Phase 0: LIF (Leaky Integrate-and-Fire) 네트워크 + STDP.

1,000개 뉴런, E/I balance (80:20), refractory period, 기본 STDP.
목표: 기저 발화율 1~5%, E/I 균형 안정, 전역 발작 없음.
"""
from __future__ import annotations
import numpy as np


class LIFNetwork:
    """Leaky Integrate-and-Fire 스파이킹 뉴런 네트워크 + STDP."""

    def __init__(self, n_neurons: int = 1_000, e_ratio: float = 0.8, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n = n_neurons
        self.n_exc = int(n_neurons * e_ratio)
        self.n_inh = n_neurons - self.n_exc

        # 뉴런 상태
        self.v = np.zeros(n_neurons, dtype=np.float32)
        self.threshold = np.full(n_neurons, 0.8, dtype=np.float32)  # 발화 임계값 (0.5=과다, 1.5=과소 → 0.8)
        self.reset_v = 0.0
        self.leak = 0.92  # 누출 8%/스텝

        # Refractory period
        self.refractory = np.zeros(n_neurons, dtype=np.int8)
        self.refractory_period = 5  # 5스텝 불응기 (길게 → 발화율↓)

        # 시냅스 가중치 (희소 연결 ~5%)
        connectivity = 0.05
        w = self.rng.standard_normal((n_neurons, n_neurons)).astype(np.float32)
        mask = self.rng.random((n_neurons, n_neurons)) < connectivity
        w *= mask

        # E/I 부호
        w[self.n_exc:, :] = -np.abs(w[self.n_exc:, :])  # 억제 뉴런: 음수
        w[:self.n_exc, :] = np.abs(w[:self.n_exc, :])    # 흥분 뉴런: 양수

        np.fill_diagonal(w, 0)  # 자기 연결 제거

        # 억제를 더 강하게 (E/I balance)
        w[self.n_exc:, :] *= 1.5  # 억제가 흥분보다 1.5배 강함

        self.weights = w * 0.05  # 전체 스케일 (0.1→0.05)

        # 스파이크 기록
        self.spikes = np.zeros(n_neurons, dtype=np.bool_)

        # STDP 관련
        self.spike_trace = np.zeros(n_neurons, dtype=np.float32)  # 스파이크 흔적 (지수 감쇠)
        self.stdp_lr = 0.0003  # STDP 학습률 (0.001→0.0003, STDP 발산 억제)
        self.trace_decay = 0.95  # 흔적 감쇠율

        # 통계
        self.total_spikes_history = []

    def step(self, external_input: np.ndarray | None = None) -> np.ndarray:
        """1 시뮬레이션 스텝 실행."""
        active = self.refractory == 0

        # 누출 (Leaky)
        self.v *= self.leak

        # 시냅스 입력
        if np.any(self.spikes):
            synaptic = self.weights[:, self.spikes].sum(axis=1)
            self.v += synaptic * active

        # 외부 입력
        if external_input is not None:
            self.v += external_input * active

        # 막전위 하한 (음수 방지)
        self.v = np.maximum(self.v, -0.5)

        # 발화 판정
        self.spikes = (self.v >= self.threshold) & active

        # 발화한 뉴런: 리셋 + 불응기
        self.v[self.spikes] = self.reset_v
        self.refractory[self.spikes] = self.refractory_period

        # 불응기 카운트다운
        self.refractory = np.maximum(self.refractory - 1, 0)

        # STDP 업데이트
        self._stdp_update()

        # 통계 기록
        self.total_spikes_history.append(int(self.spikes.sum()))
        if len(self.total_spikes_history) > 100:
            self.total_spikes_history.pop(0)

        return self.spikes.copy()

    def _stdp_update(self):
        """기본 STDP: 함께 발화하면 강화, 시간차 있으면 약화."""
        # 흔적 감쇠
        self.spike_trace *= self.trace_decay

        # 발화한 뉴런의 흔적 갱신
        self.spike_trace[self.spikes] = 1.0

        if not np.any(self.spikes):
            return

        # Pre-post: post가 발화할 때, pre의 흔적이 높으면 강화
        spike_idx = np.where(self.spikes)[0]
        for post in spike_idx:
            if post >= self.n_exc:
                continue  # 억제 뉴런의 시냅스는 STDP 안 함
            # pre → post 시냅스 강화 (pre의 흔적에 비례)
            pre_trace = self.spike_trace.copy()
            pre_trace[post] = 0  # 자기 자신 제외
            dw = self.stdp_lr * pre_trace
            self.weights[post, :] += dw * (self.weights[post, :] != 0)  # 기존 연결만

        # 가중치 클리핑 (발산 방지)
        self.weights[:self.n_exc, :] = np.clip(self.weights[:self.n_exc, :], 0, 0.3)
        self.weights[self.n_exc:, :] = np.clip(self.weights[self.n_exc:, :], -0.5, 0)

    def get_firing_rate(self) -> float:
        """현재 스텝의 발화율."""
        return float(self.spikes.sum()) / self.n

    def get_exc_inh_rates(self) -> tuple[float, float]:
        """흥분/억제 뉴런 별도 발화율."""
        exc_rate = float(self.spikes[:self.n_exc].sum()) / self.n_exc if self.n_exc > 0 else 0
        inh_rate = float(self.spikes[self.n_exc:].sum()) / self.n_inh if self.n_inh > 0 else 0
        return exc_rate, inh_rate

    def get_avg_firing_rate(self, window: int = 50) -> float:
        """최근 N스텝 평균 발화율."""
        if not self.total_spikes_history:
            return 0.0
        recent = self.total_spikes_history[-window:]
        return float(np.mean(recent)) / self.n
