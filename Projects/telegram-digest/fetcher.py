"""텔레그램 메시지 가져오기 모듈."""

import json
import os
from datetime import datetime, timezone

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User

STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_state(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


async def get_monitored_dialogs(client: TelegramClient, config: dict) -> list:
    """참여한 그룹/채널 중 모니터링 대상 반환."""
    include = config.get("monitor", {}).get("include", [])
    exclude = config.get("monitor", {}).get("exclude", [])

    dialogs = []
    async for dialog in client.iter_dialogs():
        entity = dialog.entity
        # 그룹, 채널, 1:1 채팅 모두 포함
        if not isinstance(entity, (Channel, Chat, User)):
            continue
        # 봇과의 1:1은 제외
        if isinstance(entity, User) and entity.bot:
            continue
        name = dialog.name or ""
        # include 필터: 비어있으면 전부, 아니면 이름 매칭
        if include and not any(inc in name for inc in include):
            continue
        # exclude 필터
        if any(exc in name for exc in exclude):
            continue
        dialogs.append(dialog)
    return dialogs


async def fetch_recent_messages(
    client: TelegramClient,
    dialog,
    since: datetime,
    max_per_group: int = 100,
) -> list[dict]:
    """특정 대화방에서 since 이후 메시지를 가져온다."""
    messages = []
    async for msg in client.iter_messages(
        dialog, offset_date=None, limit=max_per_group
    ):
        if msg.date.replace(tzinfo=timezone.utc) <= since.replace(tzinfo=timezone.utc):
            break
        if not msg.text:
            continue
        sender = ""
        if msg.sender:
            sender = getattr(msg.sender, "first_name", "") or getattr(
                msg.sender, "title", ""
            )
        messages.append(
            {
                "group": dialog.name,
                "sender": sender,
                "text": msg.text,
                "timestamp": msg.date.isoformat(),
            }
        )
    return messages


async def fetch_all(client: TelegramClient, config: dict) -> dict[str, list[dict]]:
    """모든 모니터링 대상에서 새 메시지를 가져온다."""
    import asyncio

    state = _load_state()
    dialogs = await get_monitored_dialogs(client, config)
    interval = config.get("schedule", {}).get("interval_minutes", 30)
    default_since = datetime.now(timezone.utc).replace(
        second=0, microsecond=0
    )
    # 기본: interval분 전부터
    from datetime import timedelta

    default_since = default_since - timedelta(minutes=interval)

    result: dict[str, list[dict]] = {}
    for dialog in dialogs:
        dialog_id = str(dialog.id)
        since_str = state.get(dialog_id)
        if since_str:
            since = datetime.fromisoformat(since_str)
        else:
            since = default_since

        msgs = await fetch_recent_messages(client, dialog, since)
        if msgs:
            result[dialog.name] = msgs

        # 타임스탬프 갱신
        state[dialog_id] = datetime.now(timezone.utc).isoformat()
        await asyncio.sleep(0.5)  # flood wait 방지

    _save_state(state)
    return result
