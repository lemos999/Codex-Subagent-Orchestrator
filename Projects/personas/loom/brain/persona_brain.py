"""
PersonaBrain Phase 0: 최소 뇌 — 입력 → LIF → 행동 결정.

"서하린이 숨을 쉰다" — 에너지 소비, 피로, 수면을 느끼는 뇌.
"""
from __future__ import annotations
import os
import numpy as np
from .lif_network import LIFNetwork


# 행동 공간 (Phase 3: socialize 추가)
ACTIONS = ["idle", "work", "eat", "sleep", "explore", "socialize"]

# 강도별 에너지 소비
# 강도별 에너지 소비 (16~18틱 활동 후 수면을 목표)
# 강도1 주로 사용: 0.05/틱 × 18틱 = 0.9 소모 → energy 0.1 → 수면
ENERGY_COST = {1: 0.05, 2: 0.08, 3: 0.12, 4: 0.25}


class PersonaBrain:
    """Phase 0 PersonaBrain: LIF 네트워크 + 에너지 관리."""

    def __init__(self, n_neurons: int = 1_000, seed: int = 42):
        self.snn = LIFNetwork(n_neurons=n_neurons, seed=seed)
        self.n_neurons = n_neurons
        self.sim_steps = 7

        # 행동 readout 가중치 (Layer 2)
        model_path = os.path.join(os.path.dirname(__file__), "..", "data", "models", "readout_weights_v1.npy")
        rng = np.random.default_rng(seed + 1)
        if os.path.exists(model_path):
            loaded = np.load(model_path)
            if loaded.shape[0] < len(ACTIONS):
                # 기존 5행 → 6행 확장 (socialize 행 추가)
                extra = rng.standard_normal(
                    (len(ACTIONS) - loaded.shape[0], n_neurons)
                ).astype(np.float32) * 0.01
                self.readout_weights = np.vstack([loaded, extra])
            else:
                self.readout_weights = loaded
            self._teacher_trained = True
        else:
            self.readout_weights = rng.standard_normal(
                (len(ACTIONS), n_neurons)
            ).astype(np.float32) * 0.01
            self._teacher_trained = False

    def tick(
        self,
        climate_vec: np.ndarray,              # float16[8]
        energy_pool: float,                   # 0.0 ~ 1.0
        oyok: np.ndarray,                     # float16[5] 오욕
        tone: np.ndarray,                     # float16[12] 12클러스터
        personality: np.ndarray | None = None,  # float32[5] 성격 5축
        fear: float = 0.0,                    # 공황 온도 조절용
        social_pull: float = 0.0,             # 관계 밀도 (친한 사람이 있으면 양수)
        memory_bias: np.ndarray | None = None,  # float32[6] 과거 성공 행동 편향
        skill_drive_signals: dict | None = None,  # 신경 drive 신호 (숙달/적성/몰입/도파민)
        economic_state: dict | None = None,   # Phase 12: 경제 지각 신호
    ) -> tuple[str, int, float]:
        """
        1틱 추론 (Deliberation 포함).

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
        # 높은 욕구 = 해당 행동 뉴런 흥분
        # 낮은 욕구 = 해당 행동 뉴런 억제 (포만감 = GABA 억제)
        for i in range(5):
            drive = float(oyok[i])
            target_start = n_input + i * 10
            target_end = min(target_start + 10, self.n_neurons)
            if drive > 0.3:
                # 욕구 높음 → 관련 뉴런 흥분
                spread = rng.choice(range(target_start, target_end), size=min(5, target_end - target_start), replace=False)
                input_signal[spread] += drive * 0.4
            elif drive < 0.2:
                # 욕구 낮음 → 관련 뉴런 억제 (포만감/충분함)
                spread = rng.choice(range(target_start, target_end), size=min(5, target_end - target_start), replace=False)
                input_signal[spread] -= 0.2  # 억제 신호

        # ── Phase 12: 경제 지각 (뉴런 300~349) ───────────────
        # 경제 상태는 행동을 직접 고르지 않고, 뉴런 전류로만 들어간다.
        # 작은 테스트용 브레인에서는 범위가 없을 수 있으므로 안전하게 건너뛴다.
        self._last_economic_state = economic_state
        if economic_state is not None and self.n_neurons >= 350:
            eco = economic_state
            eco_base = 300

            def stimulate(start: int, amount: float, width: int = 10):
                end = min(start + width, self.n_neurons)
                if end <= start or abs(amount) <= 0:
                    return
                input_signal[start:end] += amount * 0.5

            # 채널 1: 식량 부족. 부족할수록 생존 위협 전류가 강해진다.
            food_scarcity = 1.0 - min(1.0, float(eco.get("food_ratio", 1.0)))
            if food_scarcity > 0.1:
                stimulate(eco_base, food_scarcity * 0.5)

            # 채널 2: 도구 부족. 도구가 없거나 닳았을수록 필요 신호가 생긴다.
            tool_lack = 1.0 - min(1.0, float(eco.get("tool_ratio", 0.0)))
            if tool_lack > 0.3:
                stimulate(eco_base + 10, tool_lack * 0.3)

            # 채널 3: 경제적 안정. 빈곤은 흥분, 풍요는 약한 억제.
            wealth_ratio = min(2.0, float(eco.get("wealth_ratio", 1.0)))
            if wealth_ratio < 0.5:
                stimulate(eco_base + 20, (0.5 - wealth_ratio) * 0.4)
            elif wealth_ratio > 1.5:
                stimulate(eco_base + 20, -0.15)

            # 채널 4: 직업 만족도. 낮으면 불만족/이직 동기 신호가 생긴다.
            job_sat = float(eco.get("job_satisfaction", 0.5))
            if job_sat < 0.3:
                stimulate(eco_base + 30, (0.3 - job_sat) * 0.5)
            elif job_sat > 0.7:
                stimulate(eco_base + 30, -0.1)

            # 채널 5: 상대적 부. 평균보다 가난하면 박탈감 전류가 생긴다.
            rel_wealth = float(eco.get("relative_wealth", 1.0))
            if rel_wealth < 0.5:
                stimulate(eco_base + 40, (0.5 - rel_wealth) * 0.4)

            # Phase 14-B: 정치 스트레스는 생존 위협 회로를 공유한다.
            grievance = float(eco.get("grievance", 0.0))
            tax_burden = float(eco.get("tax_burden", 0.0))
            trust_to_lord = float(eco.get("trust_to_lord", 0.5))

            political_stress = grievance + max(0.0, tax_burden - 0.5) * 0.5
            if trust_to_lord < 0.3:
                political_stress *= 1.3

            if political_stress > 0.1:
                stimulate(eco_base + 20, min(0.6, political_stress * 0.35))

            if grievance > 0.3:
                stimulate(eco_base + 30, grievance * 0.4)

            self._last_economic_input = input_signal[eco_base:eco_base + 50].copy()
        else:
            self._last_economic_input = np.zeros(0, dtype=np.float32)

        # 에너지 충만 → sleep 관련 뉴런 억제 (각성 유지)
        if energy_pool > 0.5:
            sleep_neurons = range(n_input + 10, min(n_input + 20, self.n_neurons))  # 수면욕 뉴런
            for idx in sleep_neurons:
                input_signal[idx] -= 0.15 * energy_pool  # 에너지 높을수록 강한 수면 억제

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

        # 2. SNN 실행 (sim_steps 시뮬레이션 스텝 = 1틱)
        # 매 스텝 동일한 입력 유지 (뇌: 자극은 지속됨, 즉시 사라지지 않음)
        total_spikes = np.zeros(self.n_neurons, dtype=np.float32)
        base_drive = input_signal * 0.7
        step_noise = rng.exponential(
            0.03, (self.sim_steps, self.n_neurons)
        ).astype(np.float32)
        for step in range(self.sim_steps):
            # 지속 입력 + 스텝별 노이즈
            step_input = base_drive + step_noise[step]
            spikes = self.snn.step(step_input)
            total_spikes += spikes.astype(np.float32)

        # 발화율
        firing_rate = total_spikes / float(self.sim_steps)
        self._last_firing_rate = firing_rate  # readout 적응용 캐시

        # 3. 에너지 강도 판정 (Phase 0: 강도1만 사용)
        intensity = 1

        # 4. 행동 결정 (readout)
        action_logits = self.readout_weights @ firing_rate

        # 오욕 → logit 보정 (연속 스케일, 하드코딩 제거)
        # 식욕: 0→-0.3, 0.5→+0.2, 1.0→+0.7 (부드러운 곡선)
        eat_bonus = (float(oyok[0]) - 0.3) * 1.0
        action_logits[ACTIONS.index("eat")] += eat_bonus
        # 수면욕: 에너지 낮으면 수면 선호
        sleep_bonus = max(0, (1.0 - energy_pool) * 0.5 - 0.1)
        action_logits[ACTIONS.index("sleep")] += sleep_bonus
        # work 기본 바이어스 (주요 행동이므로)
        action_logits[ACTIONS.index("work")] += 0.2
        # socialize: B(Bonding/OXT) tone + 에너지 여유 + 사회적 욕구
        bonding_tone = float(tone_f32[3]) if len(tone_f32) > 3 else 1.0  # B cluster
        # 기본 사회적 바이어스 0.1 + Bonding tone 보너스 + 에너지 여유
        socialize_bonus = 0.1 + (bonding_tone - 0.8) * 0.5 + max(0, energy_pool - 0.4) * 0.2
        action_logits[ACTIONS.index("socialize")] += socialize_bonus
        # idle 음수 바이어스 (무행동 억제)
        action_logits[ACTIONS.index("idle")] -= 0.1

        # ── Neural Drive ────────────────────────────────────────
        # 축적된 도파민/숙달/몰입/적성이 수렴하면 drive가 생긴다.
        # drive는 성격 장벽을 "부수는" 것이 아니라 "부드럽게 하는" 것이다.
        # 새로운 데이터 구조가 아닌 기존 신경 신호의 합산.
        drive = 0.0
        if skill_drive_signals is not None:
            s = skill_drive_signals
            factors = [
                s.get("mastery", 0),                           # 숙달 수준
                max(0, s.get("aptitude", 0) - 0.4) / 0.6,     # 적성 일치 (0.4 이하 무시)
                min(1.0, s.get("flow_ratio", 0) * 5.0),       # 몰입 경험 비율
                max(0, s.get("da_accumulation", 0)),           # 도파민 축적
            ]
            nonzero = [f for f in factors if f > 0.01]
            if len(nonzero) >= 3:  # 3개 이상의 수렴 증거 필요
                product = 1.0
                for f in nonzero:
                    product *= f
                drive = (product ** (1.0 / len(nonzero))) ** 0.7

        # ── Deliberation Layer ──────────────────────────────────
        # 성격이 logit에 녹아든다 — 외부 override가 아닌 내부 가중치
        # drive가 강하면 성격의 영향력이 줄어든다 (최대 60% 감쇠, 40% 영구 보존)
        personality_scale = 1.0 - drive * 0.6

        if personality is not None:
            p = personality  # [-1, +1] 5축
            ps = personality_scale
            # [0] 내향(-) ↔ 외향(+): 외향 → socialize, explore 선호
            action_logits[ACTIONS.index("socialize")] += p[0] * 0.3 * ps
            action_logits[ACTIONS.index("explore")]   += p[0] * 0.2 * ps
            # [1] 신중(-) ↔ 대담(+): 대담 → explore, work 과감히 / 신중 → idle, sleep 보수적
            action_logits[ACTIONS.index("explore")]   += p[1] * 0.25 * ps
            action_logits[ACTIONS.index("work")]      += p[1] * 0.15 * ps
            action_logits[ACTIONS.index("idle")]      -= p[1] * 0.15 * ps
            # [2] 이성(-) ↔ 감성(+): 감성 → 감정 행동(eat, socialize), 이성 → work
            action_logits[ACTIONS.index("eat")]       += p[2] * 0.15 * ps
            action_logits[ACTIONS.index("socialize")] += p[2] * 0.15 * ps
            action_logits[ACTIONS.index("work")]      -= p[2] * 0.1 * ps
            # [3] 독립(-) ↔ 협조(+): 협조 → socialize, 독립 → explore/work 혼자
            action_logits[ACTIONS.index("socialize")] += p[3] * 0.35 * ps
            action_logits[ACTIONS.index("explore")]   -= p[3] * 0.1 * ps
            # [4] 관대(-) ↔ 엄격(+): 엄격 → work 강조, 관대 → idle 용인
            action_logits[ACTIONS.index("work")]      += p[4] * 0.2 * ps
            action_logits[ACTIONS.index("idle")]      -= p[4] * 0.2 * ps

        # ── Drive → 사교/교육 당김 ──────────────────────────────
        # drive가 충분하면 숙련자로서 지식을 나누려는 신경 충동 발생
        if skill_drive_signals is not None and drive > 0.3:
            teach_pull = drive * skill_drive_signals.get("mastery", 0) * 0.4
            action_logits[ACTIONS.index("socialize")] += teach_pull

        # 과거 기억 편향 (최근 성공한 행동에 작은 보너스)
        if memory_bias is not None and len(memory_bias) == len(ACTIONS):
            action_logits += memory_bias * 0.15

        # 사회적 당김 (친한 사람이 있으면 socialize 더 당김)
        if social_pull > 0:
            action_logits[ACTIONS.index("socialize")] += social_pull * 0.3

        # 에너지 → 선택지 제한 (에너지 낮으면 야외 행동 불리)
        if energy_pool < 0.3:
            action_logits[ACTIONS.index("work")]    -= (0.3 - energy_pool) * 1.0
            action_logits[ACTIONS.index("explore")] -= (0.3 - energy_pool) * 1.5

        # ── 온도 샘플링 (fear → 공황 = 무작위, 침착 = 계산적) ──
        # 에너지 고갈 시 강제 수면 (유일한 하드코딩)
        if energy_pool < 0.1:
            action_idx = ACTIONS.index("sleep")
        elif fear > 0.7:
            # 공황 상태: softmax 샘플링 (높은 온도 = 덜 계산적)
            temperature = 0.5 + fear * 1.5  # fear=0.7→1.55, fear=1.0→2.0
            logits_t = action_logits / temperature
            logits_t -= logits_t.max()
            probs = np.exp(logits_t)
            probs /= probs.sum()
            action_idx = int(rng.choice(len(ACTIONS), p=probs))
        else:
            # 침착 상태: argmax (계산적 선택)
            action_idx = int(np.argmax(action_logits))

        action = ACTIONS[action_idx]
        cost = ENERGY_COST.get(intensity, 0.01)

        return action, intensity, cost

    def adapt_readout(self, action_idx: int, reward: float, lr: float = 0.0001):
        """readout 가중치 미세 적응. 강한 보상 신호에서만 작동.

        SNN 내부 STDP는 self.weights를 변경하지만 readout은 고정이었다.
        이 메서드로 readout도 도파민 신호에 의해 매우 느리게 적응한다.
        """
        if abs(reward) < 0.2:
            return  # 약한 신호는 무시
        fr = getattr(self, '_last_firing_rate', None)
        if fr is None:
            return
        delta = lr * reward * fr
        self.readout_weights[action_idx] += delta
        # row 정규화 (발산 방지)
        row_norm = np.linalg.norm(self.readout_weights[action_idx])
        if row_norm > 1.0:
            self.readout_weights[action_idx] /= row_norm

    def get_stats(self) -> dict:
        """현재 네트워크 통계."""
        exc_rate, inh_rate = self.snn.get_exc_inh_rates()
        return {
            "firing_rate": self.snn.get_firing_rate(),
            "exc_rate": exc_rate,
            "inh_rate": inh_rate,
            "n_neurons": self.n_neurons,
        }
