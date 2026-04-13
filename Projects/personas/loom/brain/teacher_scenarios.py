"""
Teacher Net Phase 1: 시나리오 생성기.

다양한 상황을 생성하여 LLM Teacher에게 "인간다운 행동"을 물어본다.
"""
from __future__ import annotations
import json
import itertools
import random


ACTIONS = ["idle", "work", "eat", "sleep", "explore"]

# 시나리오 변수 범위
ENERGY_LEVELS = [0.05, 0.15, 0.3, 0.5, 0.7, 0.9]
HUNGER_LEVELS = [0.0, 0.3, 0.5, 0.7, 0.9]
SLEEPINESS_LEVELS = [0.0, 0.2, 0.4, 0.7]
FEAR_LEVELS = [0.0, 0.3, 0.6]
JOY_LEVELS = [0.0, 0.3, 0.6]
ANGER_LEVELS = [0.0, 0.3, 0.6]


def generate_scenarios(n: int = 500, seed: int = 42) -> list[dict]:
    """다양한 상황 조합으로 시나리오 생성."""
    rng = random.Random(seed)
    scenarios = []

    # 핵심 조합 (에너지 × 배고픔 × 수면욕)
    core_combos = list(itertools.product(ENERGY_LEVELS, HUNGER_LEVELS, SLEEPINESS_LEVELS))
    rng.shuffle(core_combos)

    for i, (energy, hunger, sleepiness) in enumerate(core_combos[:n]):
        fear = rng.choice(FEAR_LEVELS)
        joy = rng.choice(JOY_LEVELS)
        anger = rng.choice(ANGER_LEVELS)

        scenario = {
            "id": i,
            "energy": energy,
            "hunger": hunger,
            "sleepiness": sleepiness,
            "fear": fear,
            "joy": joy,
            "anger": anger,
            "context": _describe_context(energy, hunger, sleepiness, fear, joy, anger),
        }
        scenarios.append(scenario)

    # 부족한 만큼 랜덤 생성
    while len(scenarios) < n:
        i = len(scenarios)
        scenarios.append({
            "id": i,
            "energy": round(rng.uniform(0.01, 1.0), 2),
            "hunger": round(rng.uniform(0.0, 1.0), 2),
            "sleepiness": round(rng.uniform(0.0, 0.8), 2),
            "fear": round(rng.uniform(0.0, 0.8), 2),
            "joy": round(rng.uniform(0.0, 0.8), 2),
            "anger": round(rng.uniform(0.0, 0.8), 2),
            "context": "",
        })
        scenarios[-1]["context"] = _describe_context(**{k: scenarios[-1][k] for k in ["energy", "hunger", "sleepiness", "fear", "joy", "anger"]})

    return scenarios


def _describe_context(energy, hunger, sleepiness, fear, joy, anger) -> str:
    """상태를 자연어로 설명."""
    parts = []
    if energy < 0.15:
        parts.append("extremely exhausted")
    elif energy < 0.3:
        parts.append("very tired")
    elif energy < 0.5:
        parts.append("somewhat tired")
    else:
        parts.append("energetic" if energy > 0.8 else "moderate energy")

    if hunger > 0.7:
        parts.append("very hungry")
    elif hunger > 0.4:
        parts.append("hungry")

    if sleepiness > 0.5:
        parts.append("very sleepy")
    elif sleepiness > 0.2:
        parts.append("a bit sleepy")

    if fear > 0.4:
        parts.append("afraid")
    if joy > 0.4:
        parts.append("happy")
    if anger > 0.4:
        parts.append("angry")

    return ", ".join(parts) if parts else "neutral state"


def build_prompt(scenario: dict) -> str:
    """시나리오를 LLM 프롬프트로 변환."""
    return f"""You are simulating a persona living in a virtual world. Given this state, choose the BEST single action.

State:
- Energy: {scenario['energy']:.2f} (0=exhausted, 1=full)
- Hunger: {scenario['hunger']:.2f} (0=satisfied, 1=starving)
- Sleepiness: {scenario['sleepiness']:.2f} (0=alert, 1=can't stay awake)
- Fear: {scenario['fear']:.2f} (0=calm, 1=terrified)
- Joy: {scenario['joy']:.2f} (0=neutral, 1=ecstatic)
- Anger: {scenario['anger']:.2f} (0=calm, 1=furious)
- Context: {scenario['context']}

Available actions: idle, work, eat, sleep, explore

Rules:
- If energy < 0.1, you MUST sleep
- If very hungry (hunger > 0.7), eating is urgent
- Explore when feeling safe and curious
- Work when energy is available and not distracted
- Idle when nothing is pressing

Respond with ONLY the action name (one word): idle, work, eat, sleep, or explore"""


def parse_response(text: str) -> str:
    """LLM 응답에서 행동 추출."""
    text = text.strip().lower()
    for action in ACTIONS:
        if action in text:
            return action
    return "idle"  # fallback


if __name__ == "__main__":
    scenarios = generate_scenarios(500)
    print(f"Generated {len(scenarios)} scenarios")
    print(f"Sample: {json.dumps(scenarios[0], indent=2)}")
    print(f"Prompt: {build_prompt(scenarios[0])}")
