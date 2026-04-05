# RL 자동매매 — 대안 패러다임 연구 보고서

**날짜**: 2026-03-31
**근거**: rl_learning_log.md 50+ 사이클, rl_env_v2.py 코드, obs_predictability_test 결과

---

## 0. 근본 진단: 왜 RL이 실패하는가

50+ 사이클을 관통하는 핵심 딜레마:

```
많이 거래 → WR 70%이지만 방향 정확도 ~51% (동전) → 수수료에 잠식 → -60~90%
적게 거래 → 손실 회피 → -6%~+26% (1~4건) → 통계적 무의미
→ 모델이 "안 하는 게 이득" 방향으로 항상 수렴
```

**핵심 원인**: 330차원 관측 → 15분 후 가격 방향 예측 정확도 **51.5%** (동전 던지기).
고확신 서브셋도 **54.5%**. 이 예측력으로는 수수료(0.04% x 2 = 왕복 0.08%) + 슬리피지(0.01% x 2)를
극복하는 것이 수학적으로 불가능.

**결론**: 문제는 RL 알고리즘이 아니라, **1분/15분 단위 방향 예측 자체가 불가능에 가까운 과제**라는 점.

---

## 1. 문제 단순화 (Problem Simplification)

### 1A. Long-Only + Binary IN/OUT + 1시간봉

**아이디어**: 롱/숏/사이징 복잡성을 모두 제거. "ETH를 들고 있을까 말까"만 결정.

**구체적 설계**:
- 액션: {0: OUT (현금), 1: IN (ETH 롱 1x, 레버리지 없음)}
- 관측: 24개 1H 캔들 OHLCV (120dim) + RSI + MA20/50 위치 + ATR + 시간 = ~130dim
- 보상: equity_change (IN일 때만 ETH 가격 변동분)
- 수수료: 전환시만 0.04%

**Feasibility**: 높음. 기존 sim_1m.sqlite 데이터를 1H로 리샘플하면 됨. TradingEnvV2를 단순화한 새 환경 작성 ~200줄.

**Implementation**:
1. `rl_env_simple.py` 신규 작성 — Binary Discrete action, 1H 리샘플
2. PPO (MLP, LSTM 불필요) + 500K steps
3. 평가: buy-and-hold 대비 초과 수익 측정

**Expected edge**:
- 1H 봉은 1분 봉 대비 노이즈 60~80% 감소 (표본 크기 법칙)
- 트렌드 추종 신호가 더 명확
- 액션 2개 → 탐색 공간 기하급수적 축소
- 수수료 부담: 하루 1~2회 전환 = 0.08~0.16% (현재 하루 16건 = 1.28% 대비 10x 감소)

**Risk**:
- 1H 봉에서도 방향 예측이 동전일 수 있음
- 하락장에서 롱온리는 구조적으로 불리
- **mitigation**: 2021~2023 하락장 데이터로 반드시 검증

### 1B. 4시간봉 + 고정 포지션 + 트렌드 추종

**아이디어**: 더 느린 시간축. 4H 봉 기준, MA 크로스오버 + RL 필터.

**Feasibility**: 높음. 단 5년 데이터 = 4H 봉 약 10,950개 → 학습 데이터 부족 우려.

**Risk**: 학습 데이터 부족 + 4H에서도 예측력 미보장.

---

## 2. 2단계 접근 (Two-Stage: Prediction + Execution)

### 2A. XGBoost 분류기 → 규칙 기반 실행

**아이디어**: RL의 문제 = 예측과 실행을 동시에 학습. 분리하면?

**Stage 1 — 방향 예측기**:
- 입력: obs_predictability_test.py의 피처 세트 (MA deviation, RSI, ATR, Donchian, momentum, volume)
- 타겟: 다음 1H/4H 수익률 부호 (상승/하락)
- 모델: XGBoost 또는 LightGBM (트리 앙상블은 이 종류의 태뷸러 데이터에 최적)
- 학습: Walk-forward cross-validation (6개월 학습 → 1개월 테스트 슬라이딩)
- **핵심 차이**: RL처럼 "수렴"할 필요 없음. 과적합은 CV로 제어.

**Stage 2 — 실행 규칙**:
```python
if model.predict_proba(obs)[1] > 0.60:  # 확신도 60%+
    enter_long(size=fixed_1x)
    stop_loss = entry - 2 * ATR
    take_profit = entry + 3 * ATR  # 1.5:1 R:R
elif model.predict_proba(obs)[1] < 0.40:  # 하락 확신
    exit_if_in_position()
else:
    hold_current()  # 불확실하면 유지
```

**Feasibility**: 매우 높음. obs_predictability_test.py가 이미 피처 엔지니어링 + XGBoost 파이프라인 존재.

**Implementation**:
1. obs_predictability_test.py 확장 — 타겟을 1H/4H 방향으로 변경
2. Walk-forward CV 추가
3. 확신도 기반 실행 규칙 모듈 작성
4. sim_exchange.py 연동하여 백테스트

**Expected edge**:
- XGBoost는 피처 중요도를 직접 보여줌 → 디버깅 가능
- 확신도 필터로 "절반은 맞추는데 나머지가 다 틀림" 문제 회피
- **과적합 제어가 RL보다 훨씬 쉬움** (CV, early stopping, 정규화)
- 1분 → 1H 시간축 변경으로 노이즈 대폭 감소

**Risk**:
- obs_predictability_test 결과 51.5%가 피처 문제인지 시간축 문제인지 불명
- 1H로 올려도 52~53%면 여전히 수수료 못 이김
- **핵심 검증**: 1H 타겟으로 정확도 55%+ 나오는지 먼저 확인 필수

### 2B. 리턴 회귀 → 켈리 사이징

**아이디어**: 분류(방향) 대신 회귀(수익률 크기)로 예측.

- 타겟: 다음 4H의 리턴 (연속값)
- 실행: 예측 리턴 > threshold이면 롱, 사이즈 = Kelly fraction

**Risk**: 회귀는 분류보다 어려움. R-squared가 0.01이어도 쓸 수 있지만, 안정성 의문.

---

## 3. 진화적 방법 (Population-Based / Evolutionary)

### 3A. CMA-ES로 파라메트릭 전략 최적화

**아이디어**: RL 대신, 전략의 파라미터를 직접 최적화. 그래디언트 불필요.

**전략 파라미터화** (10~20차원):
```python
@dataclass
class Strategy:
    ma_fast: int          # 5~50 범위
    ma_slow: int          # 20~200 범위
    rsi_entry: float      # RSI < 이 값이면 롱 (20~45)
    rsi_exit: float       # RSI > 이 값이면 청산 (55~80)
    atr_mult_stop: float  # 손절 = ATR * 이 값 (1.0~4.0)
    atr_mult_tp: float    # 익절 = ATR * 이 값 (1.5~6.0)
    vol_filter: float     # 거래량 > MA * 이 값일 때만 진입 (1.0~3.0)
    hour_start: int       # 거래 시작 시간 (0~23)
    hour_end: int          # 거래 종료 시간 (0~23)
    cooldown: int          # 거래 후 대기 시간 (캔들 수)
```

**최적화**: CMA-ES (pycma 라이브러리)
- 목적함수: -Sharpe ratio (또는 -Sortino, 또는 -return/maxDD)
- 인구: 50~100
- 세대: 100~500
- 평가: 전체 5년 데이터 walk-forward (3년 in-sample + 1년 validation + 1년 test)

**Feasibility**: 높음. pycma 설치 한 줄. sim_exchange.py를 목적함수로 감싸면 됨.

**Implementation**:
1. `strategy_params.py` — Strategy 데이터클래스 + 실행 로직
2. `optimize_cma.py` — CMA-ES 루프
3. 기존 sim_exchange.py의 시뮬레이션 엔진 재사용
4. Walk-forward 분할로 과적합 방지

**Expected edge**:
- **탐색 공간이 10~20차원** (RL은 수백만 가중치)
- 그래디언트 없이 직접 최종 목적(Sharpe)을 최적화
- 과적합 여부가 즉시 보임 (IS vs OOS 비교)
- 해석 가능 (파라미터 값 직접 확인)
- **RL의 "안 하는 게 이득" 수렴 문제 없음** — 최소 거래수 제약 가능

**Risk**:
- 전략 자체가 수익성이 없으면 파라미터 최적화도 무의미
- 과적합: 파라미터 10개여도 5년 데이터에 핏팅 가능
- **mitigation**: Walk-forward + 파라미터 안정성 검증 (근처 파라미터도 수익인지)

### 3B. 유전 알고리즘 (GA) — 룰 조합 진화

**아이디어**: 개별 룰(MA 크로스, RSI 반전, 브레이크아웃 등)의 AND/OR 조합을 진화.

**Risk**: 구현 복잡도 높음, CMA-ES 대비 이점 불명확. 우선순위 낮음.

---

## 4. 앙상블 / 메타 학습 (Ensemble / Meta-Learning)

### 4A. 3 전문가 + 메타 선택기

**아이디어**:
- 전문가 1: 트렌드 추종 (MA 크로스오버 기반)
- 전문가 2: 평균 회귀 (RSI 극단 + 볼린저 밴드)
- 전문가 3: 브레이크아웃 (돈치안 채널 돌파)
- 메타 모델: 최근 N시간의 시장 특성 → 어떤 전문가가 최적인지 분류

**Feasibility**: 중간. 각 전문가는 단순하지만, 메타 모델 학습이 추가 복잡성.

**Implementation**:
1. 3개 전문가를 파라메트릭 전략으로 구현 (3A의 Strategy 재사용)
2. 각 전문가를 CMA-ES로 개별 최적화
3. 메타 선택기: 최근 48H의 각 전문가 가상 수익 → 가장 좋은 것 선택 (단순 규칙)
4. 또는: 레짐 분류기(변동성 고/저 x 추세 상/하/횡) → 전문가 매핑

**Expected edge**:
- 단일 전략은 특정 시장에만 작동. 앙상블은 적응성 확보
- 메타 선택을 "최근 성과 기반"으로 하면 학습 불필요

**Risk**:
- 개별 전문가 자체가 수익 못 내면 앙상블도 의미 없음
- 레짐 전환 감지 지연 → 전환기 손실
- **우선순위**: 먼저 단일 전략(3A)이 수익인지 확인 후 앙상블 시도

---

## 5. Minimum Viable Strategy (MVS)

### 5A. MA 크로스오버 베이스라인

**아이디어**: 가장 단순한 전략으로 "이 데이터에서 돈을 벌 수 있는가?" 확인.

```python
def ma_crossover_strategy(df_1h, fast=20, slow=50):
    """Long when MA_fast > MA_slow, flat otherwise."""
    ma_f = df_1h['close'].rolling(fast).mean()
    ma_s = df_1h['close'].rolling(slow).mean()
    signal = (ma_f > ma_s).astype(int)  # 1=long, 0=flat
    # 전환시만 수수료 발생
    trades = signal.diff().abs().sum() / 2
    returns = df_1h['close'].pct_change() * signal.shift(1)
    return returns, trades
```

**Implementation**: 30줄 스크립트. 1시간 소요.

**검증 기준**:
- Buy & Hold 대비 Sharpe 비교
- 랜덤 진입/청산 1000회 시뮬 대비 비교
- 이 베이스라인을 못 이기면 RL이든 뭐든 의미 없음

### 5B. 볼륨 필터 + MA 크로스

**아이디어**: 5A + "거래량이 평균 1.5배 이상일 때만 신호 유효"

### 5C. 세션 필터

**아이디어**: 5A + "UTC 08:00~16:00 (유럽+미국 겹침)에만 거래"

---

## 핵심 수치 검증: 시간축별 예측 가능성

현재 obs_predictability_test 결과 (1분봉, 5분 후 방향):
- 전체: 51.5% (동전)
- 고확신: 54.5% (동전+알파)

**반드시 먼저 검증해야 할 것**:
```
1H 방향 (다음 1시간 수익 부호) → XGBoost 정확도?
4H 방향 (다음 4시간 수익 부호) → XGBoost 정확도?
1D 방향 (다음 1일 수익 부호) → XGBoost 정확도?
```

만약 1H에서도 52% 미만이면: **이 피처로는 어떤 방법도 안 됨**.
53~55%이면: 확신도 필터 + 비대칭 R:R로 수익 가능성 있음.
56%+이면: 거의 확실히 수익 가능.

---

## Top 3 Concrete Proposals

### Rank 1: MVS + 시간축 예측력 검증 (소요: 3~4시간)

**왜 1순위**: 다른 모든 접근의 전제조건. 이것이 실패하면 피처 자체를 바꿔야 함.

**단계**:
1. `scripts/timeframe_predictability.py` 작성 (2시간)
   - sim_1m.sqlite에서 1m → 1H/4H/1D 리샘플
   - obs_predictability_test.py 피처 세트를 각 시간축에 적용
   - XGBoost + Walk-forward CV (6개월/1개월)
   - 출력: 각 시간축별 정확도, AUC, 피처 중요도
2. `scripts/mvs_baseline.py` 작성 (1시간)
   - MA 크로스오버 (fast=20, slow=50) on 1H
   - + 볼륨 필터, + 세션 필터 변형
   - Buy & Hold vs 랜덤 vs MA Cross 비교
   - 수수료 0.08% 왕복 포함
3. 결과에 따라 다음 단계 결정

**의사결정 트리**:
```
1H 정확도 < 52% → 피처 재설계 필요 (온체인, 오더북, 외부 데이터)
1H 정확도 52~54% → Proposal 2 (CMA-ES) 진행
1H 정확도 55%+ → Proposal 3 (XGBoost 2단계) 진행
MA Cross가 Buy&Hold 이김 → 트렌드 추종 유효 확인
MA Cross가 Buy&Hold 못 이김 → 평균 회귀 또는 다른 알파 소스 탐색
```

### Rank 2: CMA-ES 파라메트릭 전략 최적화 (소요: 4~6시간)

**왜 2순위**: RL의 핵심 약점(탐색 공간 거대, 수렴 불안정)을 정면 해결.

**단계**:
1. `scripts/strategy_cmaes.py` 작성
   ```python
   import cma

   def evaluate_strategy(params, df_1h):
       """params: [ma_fast, ma_slow, rsi_entry, rsi_exit, atr_stop, atr_tp, vol_filter, cooldown]"""
       # 1H 캔들로 트레이딩 시뮬레이션
       # return -sharpe_ratio (최소화)

   x0 = [20, 50, 30, 70, 2.0, 3.0, 1.5, 4]  # 초기값
   sigma0 = 0.3
   es = cma.CMAEvolutionStrategy(x0, sigma0, {'popsize': 50})

   while not es.stop():
       solutions = es.ask()
       fitnesses = [evaluate_strategy(s, df_train) for s in solutions]
       es.tell(solutions, fitnesses)

   best = es.result.xbest
   # Walk-forward OOS 검증
   ```
2. Walk-forward: 2021-2023 학습 → 2024 검증 → 2025 테스트
3. 파라미터 안정성 검증: 최적값 +-10% 범위에서도 수익인지

**기존 코드 재사용**:
- sim_exchange.py의 주문 실행 로직
- auto_train_v2.py의 데이터 로딩 + 평가 프레임워크

**Expected outcome**:
- IS Sharpe 1.0+ 나오면 → OOS에서 0.3+ 유지되면 성공
- IS에서도 Sharpe < 0.5면 → 이 피처/시간축으로는 한계

### Rank 3: XGBoost 2단계 (예측 + 규칙 실행) (소요: 5~7시간)

**왜 3순위**: Proposal 1에서 정확도 55%+ 확인된 경우에만 진행.

**단계**:
1. `src/trading_value/adapters/xgb_predictor.py` 작성
   - Walk-forward 학습 파이프라인 (매주 재학습)
   - predict_proba() → 확신도 출력
2. `src/trading_value/adapters/rule_executor.py` 작성
   - 확신도 > 0.58 → 롱 진입
   - 확신도 < 0.42 → 청산
   - ATR 기반 손절/익절
3. 기존 sim_exchange.py 연동 백테스트
4. paper.py 연동하여 페이퍼 트레이딩

**기존 코드 재사용**:
- obs_predictability_test.py의 피처 엔지니어링 전체
- sim_exchange.py의 시뮬레이션 엔진
- paper.py의 실시간 실행 프레임워크
- dashboard_v2.py의 모니터링

---

## 부록: 각 접근법 비교표

| 접근법 | 탐색 공간 | 과적합 제어 | 해석성 | 구현 난이도 | 기대 확률 |
|--------|-----------|------------|--------|------------|----------|
| 현재 RL (RecurrentPPO) | ~수백만 가중치 | 매우 어려움 | 없음 | 이미 존재 | 5% |
| 1A. Binary IN/OUT RL | ~수천 가중치 | 어려움 | 낮음 | 중간 | 15% |
| 2A. XGBoost 2단계 | ~수백 트리 | 쉬움 (CV) | 높음 | 중간 | 30% |
| 3A. CMA-ES 파라메트릭 | 10~20 파라미터 | 쉬움 (WF) | 매우 높음 | 낮음 | 25% |
| 4A. 앙상블 메타 | 30~60 파라미터 | 중간 | 높음 | 높음 | 20% |
| 5A. MVS 베이스라인 | 2~5 파라미터 | 자명 | 완전 | 매우 낮음 | 15% |

**"기대 확률"은 OOS에서 연 10%+ 수익을 달성할 확률의 주관적 추정.**

---

## 실행 순서 권장

```
Day 1 오전: Proposal 1 (MVS + 예측력 검증) → 3~4시간
   ↓ 결과에 따라 분기
Day 1 오후: Proposal 2 (CMA-ES) 또는 Proposal 3 (XGBoost)
Day 2: 선택한 접근법 OOS 검증 + 페이퍼 트레이딩 연결
```

**절대 규칙**: 어떤 새 접근법이든, OOS Walk-forward에서 수수료 차감 후 플러스가 아니면 배포하지 않는다.
