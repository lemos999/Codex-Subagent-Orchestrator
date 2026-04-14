# Contrarian V2 검증 — 3엔진 교차 검증 결론

> /discuss --quick | 2026-04-13 | Claude(sonnet) + GPT(4.1) + Gemini(2.5-pro)

## 최종 판정: 실전 투입 불가

3엔진 **만장일치**: 현재 상태로 실거래 투입 시 계좌 0 수렴.

## 3엔진 비교 테이블

| 관점 | Claude (sonnet) | GPT (4.1) | Gemini (2.5-pro) |
|---|---|---|---|
| **결론** | 구조적으로 돈 못 번다 | 실거래 투입 부적합 | 수정 없이 가동하면 계좌 0 |
| **가장 심각한 문제** | 학습 타겟 시간 정렬 (lookahead) | 검증/체결/리스크 계층 부재 | 거래 비용 미반영 |
| **Welford** | M2 누적 아닌 분산 직접 추적 (수학 오류) | population var로 대체로 맞으나 regime shift에 둔감 | EMA로 교체 필요 |
| **Kelly** | 이중 사이징 + 상한 100% (CRITICAL) | 단위 불일치 + 비용 미반영 (CRITICAL) | 추정치 기반 full Kelly = 파산 (CRITICAL) |
| **선형 모델** | S/N ratio에서 51% 한계 | 비선형 관계 포착 불가 + 과소적합 | 피처 엔지니어링 보완 가능 |
| **피처** | 3쌍 중복 + crowd_vol 파생 + 이진값 | 3쌍 중복 + 공통 원천 오염 + entropy 왜곡 | 3쌍 중복 + Funding Rate/호가창 누락 |
| **거래 비용** | taker 0.055% x 2 > threshold 0.05% | 5bp threshold < 왕복 비용 | "수수료 기계" |
| **고유 발견** | lookahead bias, 단일 w 4자산 공유, API 오류시 SL 미작동 | entropy NaN 위험(w=0), label alignment 검증 필요, data-snooping bias | Funding Rate 최강 역추세 지표, Orderbook Imbalance |
| **수정 톤** | 즉시/단기/중기 8단계 | 8단계 우선순위 + 학술 근거 | 5항목 심각도 분류 |

## 합의 사항 (3엔진 동의)

### CRITICAL (즉시 수정)
1. **거래 비용 미반영** — 0.05% threshold < 0.11% 왕복 수수료 = 구조적 손실
2. **Full Kelly 파산 위험** — 추정치 기반 full Kelly는 자산 파괴, 0.1~0.25로 제한
3. **피처 3쌍 완전 중복** — entropy 계산 왜곡, 메모리 규칙 위반

### MAJOR (단기 수정)
4. **Welford 비정상성** — 전체 과거 누적으로 regime 변경 반영 못함, EMA 교체
5. **선형 모델 한계** — 비선형 시장에서 과소적합

## Claude 단독 발견 (GPT/Gemini 미언급)
- **학습 타겟 lookahead**: update(features, features[0])는 현재 바 수익률 학습 → 다음 바 예측 아님
- **단일 예측기 4자산 공유**: 상관 노이즈 학습
- **다중 자산 노출 합산 캡 없음**: 400% 동시 노출 가능
- **API 오류 시 SL 미작동**: fetch_latest 실패 시 청산 스킵

## GPT 단독 발견 (Claude/Gemini 미언급)
- **entropy NaN 위험**: w 초기값 0일 때 sum(imp)=0 → p=NaN
- **Kelly 단위 불일치**: Kelly fraction은 "잃을 자본 비율"인데 size는 notional fraction
- **data-snooping bias**: rule/threshold 튜닝 검증 없음
- **학술 근거 제시**: MacLean-Thorp-Ziemba(2010), White Reality Check(1989)

## Gemini 단독 발견 (Claude/GPT 미언급)
- **Funding Rate**: perp 시장 쏠림의 가장 강력한 역추세 지표 누락
- **Orderbook Imbalance**: 1분봉 예측에서 호가창 불균형 > 체결 데이터
- **선형 모델이 오히려 나을 수 있다**: 피처 엔지니어링 의존도 높이면 복잡 모델보다 안정

## 수정 우선순위 (합의 기반)

| 순위 | 항목 | 심각도 | 근거 |
|---|---|---|---|
| 1 | 학습 타겟을 t+1 수익률로 수정 | CRITICAL | Claude: lookahead bias |
| 2 | 거래 비용 0.11% + 슬리피지 반영 | CRITICAL | 3엔진 합의 |
| 3 | Kelly 상한 0.25, 총 노출 캡 | CRITICAL | 3엔진 합의 |
| 4 | 피처 3쌍 중복 제거 + NaN 방어 | CRITICAL | 3엔진 합의 + GPT NaN |
| 5 | Welford → EMA 정규화 | MAJOR | 3엔진 합의 |
| 6 | 자산별 별도 예측기 분리 | MAJOR | Claude |
| 7 | Funding Rate + OI 피처 추가 | MAJOR | Gemini + GPT |
| 8 | walk-forward OOS 검증 추가 | MAJOR | GPT |
