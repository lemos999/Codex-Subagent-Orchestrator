"""
Teacher Net: LLM 응답 데이터로 SNN readout 가중치 학습.

800개 시나리오 × 4 Teacher → SNN이 "인간다운 행동"을 출력하도록 학습.
"""
from __future__ import annotations
import json
import glob
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brain.lif_network import LIFNetwork
from brain.persona_brain import PersonaBrain, ACTIONS


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "teacher")
MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "models")


def load_all_teacher_data() -> list[dict]:
    """모든 Teacher 데이터 로드 (최신 200개 파일만)."""
    all_data = []
    for teacher in ["haiku", "sonnet", "codex", "gemini"]:
        files = sorted(glob.glob(os.path.join(DATA_DIR, f"{teacher}_*_200.json")))
        if files:
            with open(files[-1], "r", encoding="utf-8") as f:
                data = json.load(f)
                # idle=200 같은 파싱 실패 데이터 필터링
                valid = [d for d in data if d.get("action") in ACTIONS and d.get("response", "").startswith("ERROR") is False]
                all_data.extend(valid)
                print(f"  {teacher}: {len(valid)} samples loaded")
    print(f"  Total: {len(all_data)} samples")
    return all_data


def scenario_to_input(sc: dict, n_neurons: int = 1000) -> np.ndarray:
    """시나리오를 SNN 입력 벡터로 변환 (persona_brain.tick과 동일 로직)."""
    rng = np.random.default_rng(sc.get("id", 0))
    input_signal = np.zeros(n_neurons, dtype=np.float32)
    n_input = min(100, n_neurons)

    # 에너지 관련 입력
    energy = sc["energy"]
    hunger = sc["hunger"]
    sleepiness = sc["sleepiness"]

    # 감각 입력 분산
    climate = np.array([0.5, 0.1, 0.1, 0.5, 0.3, 0.5, 0.5, 0], dtype=np.float32)
    for i in range(8):
        spread = rng.choice(n_input, size=8, replace=False)
        input_signal[spread] += climate[i] * 0.2

    # 오욕 (배고픔, 수면욕)
    oyok = np.array([hunger, sleepiness, 0, 0.1, 0.1], dtype=np.float32)
    for i in range(5):
        if oyok[i] > 0.1:
            spread = rng.choice(range(n_input, min(n_input + 50, n_neurons)), size=3, replace=False)
            input_signal[spread] += oyok[i] * 0.3

    # 감정 입력
    fear = sc.get("fear", 0)
    joy = sc.get("joy", 0)
    anger = sc.get("anger", 0)
    if fear > 0.1:
        spread = rng.choice(range(150, min(200, n_neurons)), size=5, replace=False)
        input_signal[spread] += fear * 0.3
    if joy > 0.1:
        spread = rng.choice(range(200, min(250, n_neurons)), size=5, replace=False)
        input_signal[spread] += joy * 0.2
    if anger > 0.1:
        spread = rng.choice(range(250, min(300, n_neurons)), size=5, replace=False)
        input_signal[spread] += anger * 0.25

    # 배경 노이즈 + 에너지 영향
    input_signal += rng.exponential(0.045, n_neurons).astype(np.float32)
    input_signal *= (0.3 + 0.7 * energy)

    return input_signal


def get_firing_pattern(brain: PersonaBrain, input_signal: np.ndarray) -> np.ndarray:
    """입력으로 SNN을 실행하고 발화 패턴 반환."""
    total_spikes = np.zeros(brain.n_neurons, dtype=np.float32)
    rng = np.random.default_rng(0)
    base_input = input_signal.copy()
    for step in range(10):
        step_input = base_input * 0.7 + rng.exponential(0.03, brain.n_neurons).astype(np.float32)
        spikes = brain.snn.step(step_input)
        total_spikes += spikes.astype(np.float32)
    return total_spikes / 10.0  # 발화율


def action_to_target(action: str) -> np.ndarray:
    """행동을 원-핫 타겟으로 변환."""
    target = np.zeros(len(ACTIONS), dtype=np.float32)
    if action in ACTIONS:
        target[ACTIONS.index(action)] = 1.0
    return target


def train(epochs: int = 50, lr: float = 0.01, batch_log: int = 100):
    """SNN readout 가중치 학습."""
    print("=== Teacher Net Training ===\n")

    # 데이터 로드
    data = load_all_teacher_data()
    if not data:
        print("No data found!")
        return

    # 모델 초기화
    brain = PersonaBrain(n_neurons=1000, seed=42)
    n_actions = len(ACTIONS)

    print(f"\nTraining: {len(data)} samples, {epochs} epochs, lr={lr}")
    print(f"Actions: {ACTIONS}")
    print()

    # Teacher 합의 가중치: 4개 Teacher가 동의한 경우 더 강하게 학습
    # (같은 시나리오 id에서 Teacher 간 합의도)
    # 간단 버전: 동일 가중치

    best_acc = 0
    for epoch in range(epochs):
        # 셔플
        indices = np.random.permutation(len(data))
        total_loss = 0
        correct = 0

        for idx in indices:
            sc = data[idx]
            target_action = sc["action"]
            target = action_to_target(target_action)

            # 입력 → 발화 패턴
            input_signal = scenario_to_input(sc, brain.n_neurons)
            firing = get_firing_pattern(brain, input_signal)

            # 현재 예측
            logits = brain.readout_weights @ firing
            # softmax
            exp_logits = np.exp(logits - logits.max())
            probs = exp_logits / exp_logits.sum()

            # cross-entropy loss
            target_idx = ACTIONS.index(target_action)
            loss = -np.log(probs[target_idx] + 1e-8)
            total_loss += loss

            # 정확도
            if np.argmax(probs) == target_idx:
                correct += 1

            # 그래디언트 (softmax + cross-entropy)
            grad = probs - target  # [n_actions]
            # readout weight 업데이트: W -= lr * grad.outer(firing)
            dW = np.outer(grad, firing)
            brain.readout_weights -= lr * dW

        acc = correct / len(data)
        avg_loss = total_loss / len(data)

        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:3d}/{epochs}: loss={avg_loss:.4f} acc={acc:.3f} ({correct}/{len(data)})")

        if acc > best_acc:
            best_acc = acc

    print(f"\nBest accuracy: {best_acc:.3f}")

    # 저장
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "readout_weights_v1.npy")
    np.save(model_path, brain.readout_weights)
    print(f"Saved readout weights to {model_path}")

    # 검증: 몇 개 샘플로 확인
    print("\n=== Sample Predictions ===")
    for sc in data[:10]:
        input_signal = scenario_to_input(sc, brain.n_neurons)
        firing = get_firing_pattern(brain, input_signal)
        logits = brain.readout_weights @ firing
        pred = ACTIONS[np.argmax(logits)]
        print(f"  E={sc['energy']:.2f} H={sc['hunger']:.1f} S={sc['sleepiness']:.1f} "
              f"fear={sc.get('fear',0):.1f} -> teacher={sc['action']} pred={pred} "
              f"{'OK' if pred == sc['action'] else 'MISS'}")

    return brain


if __name__ == "__main__":
    train(epochs=50, lr=0.01)
