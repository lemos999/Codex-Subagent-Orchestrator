"""메시지 전처리: 노이즈 제거, 중복 제거, 핵심 정보 압축."""

import re

# 제거 대상 패턴
NOISE_PATTERNS = [
    r'^https?://\S+$',           # URL만 있는 메시지
    r'^.{1,3}$',                 # 3자 이하 (ㅋㅋ, ㅎㅎ, ㅇㅇ 등)
    r'^[ㅋㅎㅠㅜㅡ]+$',          # 자음 반복
    r'^(ㅇㅇ|ㄴㄴ|ㄱㄱ|ㅇㅋ)$',  # 단순 반응
    r'^\d+$',                    # 숫자만
    r'^(안녕|하이|ㅎㅇ|반가|굿모닝|굿밤|잘자|수고)',  # 인사
    r'(쿠폰|할인|세일|배송|주문|결제|환불|택배)',      # 쇼핑
    r'(광고|홍보|이벤트|참여하세요|클릭)',              # 광고
]

# 투자 관련 키워드 (이 중 하나라도 있으면 우선 보존)
INVEST_KEYWORDS = [
    # 암호화폐
    'btc', 'bitcoin', '비트코인', 'eth', '이더', 'xrp', '리플', '알트',
    '코인', '토큰', '바이낸스', '업비트', '김프',
    # 주식
    '주식', '종목', '매수', '매도', '상장', '코스피', '코스닥', '나스닥',
    's&p', '다우', '삼성', 'sk', '현대', '테슬라', '엔비디아', '애플',
    # 경제
    '금리', '환율', '달러', '엔화', '위안', '인플레', 'cpi', 'gdp',
    '고용', '실업', '연준', 'fed', '기준금리', '국채',
    # 원자재
    '금값', '유가', '원유', 'wti', '금', '은',
    # 시장
    '상승', '하락', '급등', '급락', '폭락', '반등', '돌파', '지지', '저항',
    '롱', '숏', '청산', '포지션', '레버리지', '선물', '옵션',
    # 재난
    '지진', '태풍', '홍수', '쓰나미', '속보',
    # 수치 패턴
    '%', '원', '달러', '조', '억',
]

COMPILED_NOISE = [re.compile(p, re.IGNORECASE) for p in NOISE_PATTERNS]


def is_noise(text: str) -> bool:
    """노이즈 메시지인지 판별."""
    text_stripped = text.strip()
    for pattern in COMPILED_NOISE:
        if pattern.search(text_stripped):
            return True
    return False


def has_invest_keyword(text: str) -> bool:
    """투자 관련 키워드 포함 여부."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in INVEST_KEYWORDS)


def deduplicate(messages: list[dict]) -> list[dict]:
    """유사 메시지 중복 제거 (앞 50자 기준)."""
    seen = set()
    result = []
    for m in messages:
        key = m['text'][:50].strip()
        if key not in seen:
            seen.add(key)
            result.append(m)
    return result


def compress_message(text: str) -> str:
    """메시지 압축: URL 제거, 공백 정리, 길면 자르기."""
    # URL을 [링크]로 대체
    text = re.sub(r'https?://\S+', '[링크]', text)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r'\s+', ' ', text).strip()
    # 300자 초과 시 자르기
    if len(text) > 300:
        text = text[:300] + '...'
    return text


def preprocess(messages_by_group: dict[str, list[dict]], config: dict) -> dict[str, list[dict]]:
    """전체 전처리 파이프라인."""
    exclude_topics = config.get("filter", {}).get("exclude_topics", [])
    result = {}

    for group, msgs in messages_by_group.items():
        filtered = []
        for m in msgs:
            text = m['text']

            # 1. 제외 토픽 필터
            if any(topic in text for topic in exclude_topics):
                continue

            # 2. 노이즈 제거 (단, 투자 키워드 있으면 보존)
            if is_noise(text) and not has_invest_keyword(text):
                continue

            # 3. 메시지 압축
            m = {**m, 'text': compress_message(text)}

            # 빈 메시지 제거
            if len(m['text'].strip()) > 5:
                filtered.append(m)

        # 4. 중복 제거
        filtered = deduplicate(filtered)

        if filtered:
            result[group] = filtered

    return result
