"""Ollama LLM을 이용한 메시지 요약 모듈."""

import httpx
import logging

logger = logging.getLogger(__name__)

# 3b 모델에 최적화: 짧고 명확한 지시, 한국어 강제, 예시 포함
SYSTEM_PROMPT = """당신은 한국어 투자 뉴스 요약 전문가입니다.

입력된 텔레그램 메시지를 분석하여 아래 형식으로 한국어 요약을 작성하세요.

규칙:
1. 반드시 한국어로만 작성
2. 팩트와 의견을 구분 표기
3. 구체적 수치(가격, %, 날짜) 필수 포함
4. 마크다운(###, **, ```) 사용 금지
5. 정보 없으면: "주요 업데이트 없음."

카테고리: 🪙암호화폐 | 📈주식 | 💱외환/금리 | 🏦매크로 | 🛢️원자재 | ⚖️규제 | 📊시장심리 | 🌍재난/속보

출력 예시:
📊 투자 다이제스트
🕐 2026-03-28 09:00 ~ 09:20 KST

🪙 암호화폐
BTC 🟢강세
- [팩트] 87,500달러 돌파, 24시간 거래량 320억달러 (출처: 코인시그널)
- [의견] 88K 저항선 테스트 전망 (출처: 트레이더방)

📈 주식
삼성전자 🔴약세
- [팩트] 전일 대비 -2.3%, 외국인 순매도 1,200억 (출처: 주식토론방)

⚡ 핵심: BTC 87K 돌파, 삼성전자 외인 매도세
🎯 액션: BTC 88K 저항 확인 필요"""


def _build_prompt(messages_by_group: dict[str, list[dict]], collection_period: str = "") -> str:
    """메시지들을 하나의 프롬프트로 조합."""
    parts = []
    total_chars = 0
    max_chars = 3000  # 3b 모델 최적 입력 크기

    for group, msgs in messages_by_group.items():
        part = f"\n[{group}]\n"
        for m in msgs:
            line = f"{m['text']}\n"
            if total_chars + len(line) > max_chars:
                break
            part += line
            total_chars += len(line)
        parts.append(part)
        if total_chars >= max_chars:
            break

    period = f"🕐 {collection_period}\n" if collection_period else ""
    return f"{period}\n메시지:\n{''.join(parts)}"


async def summarize(
    messages_by_group: dict[str, list[dict]], config: dict, collection_period: str = ""
) -> str | None:
    """메시지를 요약하여 반환. 메시지가 없으면 None."""
    if not messages_by_group:
        return None

    total_msgs = sum(len(v) for v in messages_by_group.values())
    logger.info(f"요약 대상: {len(messages_by_group)}개 그룹, {total_msgs}개 메시지")

    ollama_cfg = config.get("ollama", {})
    base_url = ollama_cfg.get("base_url", "http://localhost:11434")
    model = ollama_cfg.get("model", "qwen2.5:3b")

    user_prompt = _build_prompt(messages_by_group, collection_period)

    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "system": SYSTEM_PROMPT,
                    "prompt": user_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "num_predict": 512,
                        "num_ctx": 4096,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()
            summary = data.get("response", "").strip()

            if not summary:
                return "주요 업데이트 없음."
            return summary

    except httpx.ConnectError:
        logger.error("Ollama 서버에 연결할 수 없습니다.")
        return "⚠️ Ollama 서버 연결 실패"
    except Exception as e:
        logger.error(f"요약 생성 실패: {e}")
        return f"⚠️ 요약 생성 오류: {e}"
