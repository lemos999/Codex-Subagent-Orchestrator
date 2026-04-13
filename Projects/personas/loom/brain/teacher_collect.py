"""
Teacher Net: 4개 LLM Teacher에게 시나리오를 던지고 응답을 수집.

사용법:
  python teacher_collect.py --teacher haiku --count 100
  python teacher_collect.py --teacher sonnet --count 100
  python teacher_collect.py --teacher codex --count 50
  python teacher_collect.py --teacher gemini --count 50
"""
from __future__ import annotations
import json
import os
import sys
import subprocess
import time
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from brain.teacher_scenarios import generate_scenarios, build_prompt, parse_response


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "teacher")


def collect_haiku(scenarios: list[dict], output_path: str):
    """Claude Haiku로 수집."""
    results = []
    for i, sc in enumerate(scenarios):
        prompt = build_prompt(sc)
        try:
            proc = subprocess.run(
                ["claude", "--print", "--model", "haiku", prompt],
                capture_output=True, text=True, timeout=30,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            response = proc.stdout.strip()
            action = parse_response(response)
        except Exception as e:
            action = "idle"
            response = f"ERROR: {e}"

        results.append({**sc, "teacher": "haiku", "response": response, "action": action})
        if (i + 1) % 10 == 0:
            print(f"  haiku: {i+1}/{len(scenarios)}")

    _save(results, output_path)
    return results


def collect_sonnet(scenarios: list[dict], output_path: str):
    """Claude Sonnet으로 수집."""
    results = []
    for i, sc in enumerate(scenarios):
        prompt = build_prompt(sc)
        try:
            proc = subprocess.run(
                ["claude", "--print", "--model", "sonnet", prompt],
                capture_output=True, text=True, timeout=30,
            )
            response = proc.stdout.strip()
            action = parse_response(response)
        except Exception as e:
            action = "idle"
            response = f"ERROR: {e}"

        results.append({**sc, "teacher": "sonnet", "response": response, "action": action})
        if (i + 1) % 10 == 0:
            print(f"  sonnet: {i+1}/{len(scenarios)}")

    _save(results, output_path)
    return results


def collect_codex(scenarios: list[dict], output_path: str):
    """Codex GPT-5.4로 수집."""
    results = []
    for i, sc in enumerate(scenarios):
        prompt = build_prompt(sc)
        try:
            proc = subprocess.run(
                "codex exec --full-auto",
                input=prompt, capture_output=True, text=True, timeout=60,
                shell=True,
            )
            response = proc.stdout.strip()
            # codex 출력에서 행동 키워드 추출 (헤더/메타 건너뛰기)
            lines = [l.strip() for l in response.split('\n') if l.strip()]
            # "codex" 또는 "tokens used" 이후 줄에서 행동 찾기
            action_found = "idle"
            for line in reversed(lines):
                if line.lower() in ("idle", "work", "eat", "sleep", "explore"):
                    action_found = line.lower()
                    break
                parsed = parse_response(line)
                if parsed != "idle" or "idle" in line.lower():
                    action_found = parsed
                    break
            action = action_found
        except Exception as e:
            action = "idle"
            response = f"ERROR: {e}"

        results.append({**sc, "teacher": "codex", "response": response[:200], "action": action})
        if (i + 1) % 10 == 0:
            print(f"  codex: {i+1}/{len(scenarios)}")

    _save(results, output_path)
    return results


def collect_gemini(scenarios: list[dict], output_path: str):
    """Gemini Pro로 수집."""
    results = []
    for i, sc in enumerate(scenarios):
        prompt = build_prompt(sc)
        try:
            proc = subprocess.run(
                ["npx", "@google/gemini-cli", "--yolo"],
                input=prompt, capture_output=True, text=True, timeout=60,
                shell=True,
            )
            response = proc.stdout.strip()
            lines = [l.strip() for l in response.split('\n') if l.strip() and not l.startswith('YOLO') and not l.startswith('Loaded')]
            response_clean = lines[-1] if lines else ""
            action = parse_response(response_clean)
        except Exception as e:
            action = "idle"
            response = f"ERROR: {e}"

        results.append({**sc, "teacher": "gemini", "response": response[:200], "action": action})
        if (i + 1) % 10 == 0:
            print(f"  gemini: {i+1}/{len(scenarios)}")

    _save(results, output_path)
    return results


def _save(results: list[dict], path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(results)} results to {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--teacher", choices=["haiku", "sonnet", "codex", "gemini", "all"], default="haiku")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    scenarios = generate_scenarios(args.count, seed=args.seed)
    print(f"Generated {len(scenarios)} scenarios")

    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")

    teachers = [args.teacher] if args.teacher != "all" else ["haiku", "sonnet", "codex", "gemini"]

    for teacher in teachers:
        path = os.path.join(DATA_DIR, f"{teacher}_{timestamp}_{args.count}.json")
        print(f"\nCollecting from {teacher}...")
        if teacher == "haiku":
            collect_haiku(scenarios, path)
        elif teacher == "sonnet":
            collect_sonnet(scenarios, path)
        elif teacher == "codex":
            collect_codex(scenarios, path)
        elif teacher == "gemini":
            collect_gemini(scenarios, path)

    print("\nDone!")
