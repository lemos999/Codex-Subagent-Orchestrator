"""Telegram Digest — 30분마다 텔레그램 메시지를 투자 관점으로 요약."""

import asyncio
import logging
import os
import sys

import yaml

from fetcher import fetch_all
from preprocessor import preprocess
from summarizer import summarize

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.yaml")


def load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        logger.error(
            "config.yaml이 없습니다. config.yaml.example을 복사하여 설정하세요."
        )
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


async def send_summary(client, config: dict, summary: str):
    """요약을 텔레그램으로 전송 (봇 API 또는 유저 계정)."""
    tg = config.get("telegram", {})
    bot_token = tg.get("bot_token")

    # 텔레그램 메시지 길이 제한 (4096자)
    chunks = []
    while summary:
        if len(summary) <= 4096:
            chunks.append(summary)
            break
        cut = summary[:4096].rfind("\n")
        if cut == -1:
            cut = 4096
        chunks.append(summary[:cut])
        summary = summary[cut:].lstrip()

    if bot_token:
        # 봇 API로 전송 (일반 채팅처럼 도착)
        import httpx
        chat_id = tg.get("bot_chat_id", 66124342)
        async with httpx.AsyncClient() as http:
            for chunk in chunks:
                await http.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": chunk},
                )
                await asyncio.sleep(0.5)
    else:
        # fallback: 유저 계정으로 전송 (저장된 메시지)
        deliver_to = tg.get("deliver_to", "me")
        for chunk in chunks:
            await client.send_message(deliver_to, chunk)
            await asyncio.sleep(0.5)


async def run_cycle(client, config: dict):
    """한 사이클: 가져오기 → 요약 → 전송."""
    from datetime import datetime, timezone

    logger.info("메시지 수집 시작...")
    collect_start = datetime.now(timezone.utc)
    messages = await fetch_all(client, config)

    if not messages:
        logger.info("새 메시지 없음, 건너뜀")
        return

    raw_groups = len(messages)
    raw_total = sum(len(v) for v in messages.values())
    logger.info(f"{raw_groups}개 그룹에서 {raw_total}개 메시지 수집 완료")

    # 전처리: 노이즈 제거, 중복 제거, 압축
    messages = preprocess(messages, config)
    if not messages:
        logger.info("전처리 후 유의미한 메시지 없음, 건너뜀")
        return

    filtered_total = sum(len(v) for v in messages.values())
    logger.info(f"전처리 완료: {raw_total}개 → {filtered_total}개 ({raw_total - filtered_total}개 노이즈 제거)")

    # 수집 시간대 계산 (KST)
    from datetime import timedelta
    kst = timezone(timedelta(hours=9))
    interval = config.get("schedule", {}).get("interval_minutes", 30)
    start_kst = (collect_start - timedelta(minutes=interval)).astimezone(kst)
    end_kst = collect_start.astimezone(kst)
    collection_period = f"{start_kst.strftime('%Y-%m-%d %H:%M')} ~ {end_kst.strftime('%H:%M')} KST"

    logger.info("요약 생성 중 (Ollama)...")
    summary = await summarize(messages, config, collection_period)

    if summary:
        await send_summary(client, config, summary)
        logger.info("요약 전송 완료 ✓")


async def main():
    config = load_config()
    tg = config["telegram"]

    if not tg.get("api_id") or not tg.get("api_hash"):
        logger.error("config.yaml에 api_id와 api_hash를 입력하세요.")
        logger.error("https://my.telegram.org 에서 발급받을 수 있습니다.")
        sys.exit(1)

    from telethon import TelegramClient

    session_path = os.path.join(BASE_DIR, tg.get("session_name", "digest_session"))
    client = TelegramClient(session_path, tg["api_id"], tg["api_hash"])

    max_connect_retries = 5
    for attempt in range(1, max_connect_retries + 1):
        try:
            await client.start()
            logger.info("텔레그램 연결 완료")
            break
        except Exception as e:
            logger.error(f"텔레그램 연결 실패 ({attempt}/{max_connect_retries}): {e}")
            if attempt == max_connect_retries:
                raise
            await asyncio.sleep(30 * attempt)

    interval = config.get("schedule", {}).get("interval_minutes", 30)
    logger.info(f"다이제스트 시작 — {interval}분 간격으로 실행")

    consecutive_errors = 0
    max_consecutive = 5

    # 시작 시 즉시 1회 실행
    try:
        await run_cycle(client, config)
        consecutive_errors = 0
    except Exception as e:
        logger.error(f"사이클 오류: {e}")
        consecutive_errors += 1

    # 이후 주기적 실행
    while True:
        await asyncio.sleep(interval * 60)
        try:
            # 연결 끊김 복구
            if not client.is_connected():
                logger.warning("연결 끊김 감지, 재연결 중...")
                await client.connect()

            await run_cycle(client, config)
            consecutive_errors = 0
        except KeyboardInterrupt:
            break
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"사이클 오류 ({consecutive_errors}/{max_consecutive}): {e}")
            if consecutive_errors >= max_consecutive:
                logger.error(f"연속 {max_consecutive}회 실패, 재시작을 위해 종료합니다.")
                break
            # 에러 시 추가 대기 (백오프)
            await asyncio.sleep(min(60 * consecutive_errors, 300))

    await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("종료됨")
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        sys.exit(1)
