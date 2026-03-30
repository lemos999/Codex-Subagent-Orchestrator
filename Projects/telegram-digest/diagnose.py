"""Telegram Digest 자동 진단 및 복구."""

import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")
LOG = []


def log(icon, msg):
    print(f"  {icon} {msg}")
    LOG.append(f"{icon} {msg}")


def check_config():
    """config.yaml 존재 및 필수 키 확인."""
    if not os.path.exists(CONFIG_PATH):
        log("❌", "config.yaml 없음")
        return False
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            c = yaml.safe_load(f)
        tg = c.get("telegram", {})
        if not tg.get("api_id") or not tg.get("api_hash"):
            log("❌", "config.yaml에 api_id 또는 api_hash 누락")
            return False
        log("✅", "config.yaml 정상")
        return True
    except Exception as e:
        log("❌", f"config.yaml 파싱 실패: {e}")
        return False


def check_packages():
    """필수 패키지 설치 확인 및 자동 설치."""
    missing = []
    for pkg, import_name in [("pyyaml", "yaml"), ("httpx", "httpx"), ("telethon", "telethon"), ("pyaes", "pyaes"), ("rsa", "rsa"), ("cryptg", "cryptg")]:
        try:
            __import__(import_name)
        except ImportError:
            missing.append(pkg)

    if missing:
        log("🔧", f"누락 패키지 발견: {missing} — 설치 시도")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + missing,
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log("✅", "패키지 설치 완료")
            return True
        else:
            log("❌", f"패키지 설치 실패: {result.stderr[:200]}")
            return False
    log("✅", "필수 패키지 모두 정상")
    return True


def check_ollama():
    """Ollama 서버 상태 확인 및 자동 시작."""
    try:
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            log("✅", f"Ollama 실행 중, 모델: {models}")
            return True
    except Exception:
        pass

    log("🔧", "Ollama 서버 미실행 — 시작 시도")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        import time
        time.sleep(5)
        import httpx
        r = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if r.status_code == 200:
            log("✅", "Ollama 시작 성공")
            return True
    except Exception as e:
        log("❌", f"Ollama 시작 실패: {e}")
    return False


def check_session():
    """Telegram 세션 파일 존재 확인."""
    import yaml
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        c = yaml.safe_load(f)
    session_name = c.get("telegram", {}).get("session_name", "digest_session")
    session_file = os.path.join(BASE_DIR, session_name + ".session")
    if os.path.exists(session_file):
        log("✅", f"세션 파일 존재: {session_name}.session")
        return True
    log("❌", "세션 파일 없음 — 터미널에서 수동 로그인 필요 (py -3.12 main.py)")
    return False


def check_network():
    """인터넷 연결 확인."""
    try:
        import httpx
        r = httpx.get("https://api.telegram.org", timeout=10)
        log("✅", "인터넷 연결 정상")
        return True
    except Exception:
        log("❌", "인터넷 연결 실패 — 네트워크 확인 필요")
        return False


def send_report(config):
    """진단 결과를 봇으로 전송."""
    try:
        import httpx
        tg = config.get("telegram", {})
        token = tg.get("bot_token")
        chat_id = tg.get("bot_chat_id", 66124342)
        if not token:
            return
        report = "⚠️ Telegram Digest 자동 진단 결과\n\n" + "\n".join(LOG)
        httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": report},
            timeout=10,
        )
    except Exception:
        pass


def main():
    print("\n🔍 Telegram Digest 자동 진단 시작\n")

    all_ok = True
    all_ok &= check_config()
    all_ok &= check_packages()
    all_ok &= check_network()
    all_ok &= check_ollama()
    all_ok &= check_session()

    print()
    if all_ok:
        print("✅ 모든 항목 정상 — 일시적 오류였을 수 있습니다.")
    else:
        print("❌ 위 항목을 확인하세요.")

    # 진단 결과를 봇으로도 전송
    try:
        import yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        send_report(config)
    except Exception:
        pass


if __name__ == "__main__":
    main()
