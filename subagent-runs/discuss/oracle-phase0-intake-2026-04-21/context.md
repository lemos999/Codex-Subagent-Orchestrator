# Discussion Topic

**Oracle 예측 엔진 (V2 재설계) Phase 0 Intake 요약이 설계 착수 조건으로 적합한가?**

## 배경

V2 Prediction Engine (`scripts/v2.py`, port 8897)은 3규칙 구조로 운영 중:
1. 예측 정확도 보상 (SGD ridge, 맞추면 ↑ / 틀리면 ↓)
2. 메모리 엔트로피 균등화 (context 가중치를 uniform distribution으로 감쇠)
3. 수익 극대화 (trust score로 게이팅)

결과: **-13.13%, 정확도 52%**. 근본 원인 진단 — 규칙 2(엔트로피 균등)가 학습된 가중치를 계속 uniform으로 끌어내려 **학습과 반대로 작동**. 단일 선형 모델이라 context별 신뢰도 분화 불가.

## 사용자 요구 (원문)
> "예측을 맞췄을 때 점수를 올리고, 못 맞추면 점수를 내립니다. 점수 높게 받기 위해 과거 예측치를 분석해서 높게 받도록 해야 합니다."

→ 핵심 원칙: **좋은 예측 패턴 강화 + 나쁜 예측 패턴 소거**. 균등 엔트로피는 금지.

## Phase 0 Intake 요약 (검증 대상)

### 1. 도메인
`software` 팩 사용 (예측 엔진 = 소프트웨어 설계 문제)

### 2. 스코프 (린)
- 팀: 사용자 1인 + Claude(설계/리뷰) + Codex(구현)
- 일정: 5일 내 기동, **승률 67%+ / 5일 +4% 목표**
- 리소스: 기존 V2/V3/TriArb 인프라 재활용

### 3. 제약
- **기술 스택**: Python 3.12, ccxt + numpy + pandas (신규 의존성 금지)
- **통합**: dashboard_unified.py MODELS dict에 `"oracle"` 키 추가 가능
- **상태/로그**: `data/oracle_state.npz` + `data/oracle.jsonl` (V3/TriArb와 일관)
- **포트**: 8897(V2 덮어쓰기) 또는 신규(8901?) — Phase 3 Decision Card에서 확정
- **v2.py 처리**: 덮어쓰기 vs 신규 `oracle.py` — Phase 3에서 확정
- **원칙**: `feedback_self_learning_algorithm.md` — 좋은 패턴 강화 + 나쁜 패턴 소거, 균등 엔트로피 금지
- **네트워크**: 로컬 HTTP는 `127.0.0.1` 하드코딩 (Windows IPv6 회피)

### Ambiguity Gate 판정
- Phase 0 통과 → Phase 1 (Charter) 진입 예정
- 포트/파일처리 2항목은 Phase 3 Decision Card로 지연

## 참고 시스템 (현재 운영 중)
- **V3** (`scripts/v3.py`, port 8898): Parker Brooks + self-learning + HTF. 6차원 context k-NN, warmup 30, EV<-0.5R & n≥20 → 블랙리스트. 7 variants (3m/5m/15m/30m + aggressive/conservative + control).
- **TriArb** (`scripts/triarb.py`, port 8899): 2-leg delta-neutral pairs ratio. 4 pairs (ETHBTC/SOLBTC/SOLETH/XRPBTC), z-score 회귀 + correlation gate + HTF bias. 5 variants.
- **Dashboard** (`scripts/dashboard_unified.py`, port 8900): 3모델 프록시 + variants 비교.

## 검증 질문 (답변 필수)

1. **Phase 1 Charter 진입 가능?** — Phase 0 요약이 Ambiguity Gate 통과에 충분한가?
2. **누락된 제약/모호성?** — Phase 1 전에 반드시 확정해야 할 항목 있나?
3. **Ambiguity Gate 적절?** — 포트/파일처리를 Phase 3로 지연하는 결정이 타당한가?
4. **설계 방향에 근본 결함?** — Oracle 접근이 V2 문제를 해결할까, 아니면 V2 수정이 더 나을까?

## 출력 형식

응답은 아래 구조로:
1. **Position**: 핵심 주장 (한 문단)
2. **Reasoning**: 근거 (2-4 bullet)
3. **Concerns**: 잠재적 리스크/함정 (2-4 bullet)
4. **Recommendation**: 권장 다음 단계 (구체적)

마지막 줄에 반드시:
`[POSITION: 한 줄 요약]`

30줄 이내로 작성.
