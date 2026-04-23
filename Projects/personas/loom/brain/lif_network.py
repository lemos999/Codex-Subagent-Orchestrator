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
        self.conn_mask = self.weights != 0
        self.conn_indices = np.argwhere(self.conn_mask)
        self._conn_flat = np.flatnonzero(self.conn_mask.ravel())
        self._conn_rows = self.conn_indices[:, 0]
        self._conn_cols = self.conn_indices[:, 1]
        self._exc_conn_mask = self._conn_rows < self.n_exc
        self._exc_conn_flat = self._conn_flat[self._exc_conn_mask]
        self._exc_conn_rows = self._conn_rows[self._exc_conn_mask]
        self._exc_conn_cols = self._conn_cols[self._exc_conn_mask]
        self._conn_pre_by_post = [
            np.flatnonzero(self.conn_mask[row])
            for row in range(n_neurons)
        ]

        # 스파이크 기록
        self.spikes = np.zeros(n_neurons, dtype=np.bool_)

        # STDP 관련
        self.spike_trace = np.zeros(n_neurons, dtype=np.float32)  # 스파이크 흔적
        self.stdp_lr = 0.0003  # 기본 STDP 학습률
        self.trace_decay = 0.95  # 흔적 감쇠율

        # Phase 2: 3-factor STDP (도파민 RL)
        self.reward_signal = 0.0  # 외부 보상 신호 (-1 ~ +1)
        self.rl_lr = 0.005  # RL 학습률 (강하게 → 벌점이 빠르게 반영)
        self.eligibility_trace = np.zeros((n_neurons, n_neurons), dtype=np.float32)  # 적격 흔적
        self.eligibility_decay = 0.9  # 적격 흔적 감쇠

        # 항상성 가소성 (homeostatic plasticity)
        self.target_firing_rate = 0.04  # 목표 발화율 4%
        self.homeostatic_lr = 0.002  # 임계값 조정 속도 (0.001→0.002 빠른 수렴)
        self.homeostatic_window = 100  # 측정 윈도우 (스텝)

        # 통계
        self.total_spikes_history = []
        self.reward_history = []

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

        # 항상성 가소성: 발화율이 목표에서 벗어나면 임계값 조정
        if len(self.total_spikes_history) >= self.homeostatic_window:
            recent_rate = np.mean(self.total_spikes_history[-self.homeostatic_window:]) / self.n
            error = recent_rate - self.target_firing_rate
            # 발화율 높으면 임계값↑, 낮으면 임계값↓
            self.threshold += self.homeostatic_lr * error
            # 임계값 합리적 범위 유지
            self.threshold = np.clip(self.threshold, 0.3, 2.0)

        return self.spikes.copy()

    def _stdp_update(self):
        """3-factor STDP: pre × post × reward (도파민 RL). 벡터화 버전."""
        # 흔적 감쇠
        self.spike_trace *= self.trace_decay

        # 발화한 뉴런의 흔적 갱신
        self.spike_trace[self.spikes] = 1.0

        # 적격 흔적(eligibility trace) 감쇠
        elig_flat = self.eligibility_trace.ravel()
        elig_flat[self._conn_flat] *= self.eligibility_decay

        if not np.any(self.spikes):
            return

        # ── 벡터화된 Pre-post 적격 흔적 축적 ──
        exc_spikes = self.spikes.copy()
        exc_spikes[self.n_exc:] = False  # 억제 뉴런 제외
        changed_rows: set[int] = set()
        if np.any(exc_spikes):
            # post가 발화한 흥분 뉴런 인덱스
            post_idx = np.where(exc_spikes)[0]
            for pidx in post_idx:
                connected = self._conn_pre_by_post[pidx]
                if connected.size == 0:
                    continue
                self.eligibility_trace[pidx, connected] += self.spike_trace[connected]
                changed_rows.add(int(pidx))

        # 보상 신호가 있을 때만 실제 가중치 변경 (3rd factor)
        if abs(self.reward_signal) > 0.01:
            weights_flat = self.weights.ravel()
            elig = elig_flat[self._exc_conn_flat]
            active = np.abs(elig) > 0
            if np.any(active):
                active_flat = self._exc_conn_flat[active]
                dw = self.rl_lr * self.reward_signal * elig[active]
                weights_flat[active_flat] += dw
                changed_rows.update(int(row) for row in np.unique(active_flat // self.n))
            elig_flat[self._conn_flat] *= 0.5
            self.reward_history.append(self.reward_signal)
        else:
            # 보상 없으면 기본 STDP만 (벡터화)
            if np.any(exc_spikes):
                post_idx = np.where(exc_spikes)[0]
                for pidx in post_idx:
                    connected = self._conn_pre_by_post[pidx]
                    if connected.size == 0:
                        continue
                    self.weights[pidx, connected] += self.stdp_lr * self.spike_trace[connected]
                    changed_rows.add(int(pidx))

        # 가중치 클리핑 (발산 방지)
        if changed_rows:
            rows = np.array(sorted(changed_rows), dtype=np.int32)
            exc_rows = rows[rows < self.n_exc]
            inh_rows = rows[rows >= self.n_exc]
            if exc_rows.size:
                self.weights[exc_rows] = np.clip(self.weights[exc_rows], 0, 0.3)
            if inh_rows.size:
                self.weights[inh_rows] = np.clip(self.weights[inh_rows], -0.5, 0)

    def apply_reward(self, reward: float):
        """외부에서 보상 신호 주입. 다음 STDP 업데이트에 적용."""
        self.reward_signal = np.clip(reward, -1.0, 1.0)

    def clear_reward(self):
        """보상 신호 소비 후 초기화."""
        self.reward_signal = 0.0

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
