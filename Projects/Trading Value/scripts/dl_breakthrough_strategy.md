# DL 트레이딩 모델 정확도 55%+ 돌파 전략

## 1. 왜 50~51%에서 벽에 부딪히는가?

### 1.1 근본 원인 진단

**피처 정보량 vs 시장 노이즈 비율**:

현재 BTC LSTM은 18개 피처(OHLCV 정규화 + RSI + ATR + MA위치 + 모멘텀 + 시간인코딩)를
60-bar 시퀀스로 입력한다. `dl_architecture_compare.py`에서 5개 아키텍처 모두 50.7~50.8%로
수렴한 사실이 결정적 증거다:

**아키텍처가 아니라 피처가 병목이다.**

`dl_features.py`의 XGBoost 분석과 `rl_learning_log.md`의 "330차원 관측 → 51.5%"가
이를 재확인한다. 동일한 기술지표를 어떤 모델에 넣어도 정보가 없으면 50%를 넘지 못한다.

구체적으로:
- **높은 예측력 (abs corr > 0.02)**: `mom_1`, `mom_4`, `rsi14`, `macd_norm`, `bb_pos`
- **낮은 예측력 (abs corr < 0.005)**: `hour_sin`, `hour_cos`, `dow_sin`, `dow_cos`, `open_pct`
- **노이즈 원인**: 단일 타임프레임, 기술지표만 사용 (외부 정보 없음), 4H 바의 노이즈 비율이 높음

RL 학습 로그에서 발견된 핵심 패턴:
- 15분봉이 4H보다 예측력 우수 (52.74% vs 51.36%)
- 고신뢰 필터 시 15분봉 56.09% 달성 가능 (이미 55%+ 돌파!)
- XGBoost > LSTM for tabular features (RL 로그 교훈 #15)

### 1.2 자산별 차이 이유

| 자산 | 정확도 | 이유 |
|------|--------|------|
| BTC 50.3% | 24/7 거래, 제도적 가격발견 부재, 노이즈 최고 |
| AMZN 57.8% | 미국 시장 구조적 패턴, 섹터/인덱스 상관관계 활용 가능 |
| NVDA 60.0% | AI 테마 모멘텀 강함, SOXX/QQQ 상대강도가 높은 예측력 |

NVDA/AMZN이 높은 이유: `dl_features.py`에서 이미 외부 피처(`soxx_ret`, `qqq_ret`,
`vix_norm`, `nvda_qqq_rs`)를 사용 중. BTC는 `funding_rate`만 있고 실제 데이터도 NaN.

---

## 2. Top 3 전략 (구체적 구현 계획)

---

### 전략 1: 멀티 타임프레임 피처 + XGBoost 앙상블 (가장 높은 ROI)

**예상 향상**: BTC 50.3% -> 54~56%, NVDA 60% -> 63~65%
**구현 난이도**: 중 (2~3일)
**근거**: RL 로그에서 15분봉 고신뢰 56.09% 이미 달성. 멀티TF 결합 시 정보 채널 3배.

#### 왜 효과가 있는가

1. **정보 이론적 근거**: 15m/1H/4H는 서로 다른 시간 스케일의 정보를 포착.
   15m = 단기 모멘텀/리버전, 1H = 세션 내 추세, 4H = 중기 방향.
   Mutual information이 낮으므로 결합 시 총 정보량 증가.

2. **실증적 근거**: RL 로그의 시간축별 검증에서 15m (52.74%) > 1H (52.66%) > 4H (51.36%).
   각 TF가 독립적 정보를 가지므로 앙상블 효과 기대.

3. **학계 근거**: "Multi-Timeframe Features for Financial Prediction" 계열 연구에서
   단일 TF 대비 1.5~3%p 향상 보고. Temporal Fusion Transformer(Lim et al., 2021)가
   멀티스케일 시계열에서 SOTA.

#### 코드 구조

```python
# scripts/dl_multi_tf_ensemble.py

class MultiTimeframeFeatureBuilder:
    """각 타임프레임에서 독립적으로 피처를 생성하고 정렬."""

    def __init__(self, db_path: Path, timeframes: list[str] = ["15m", "1h", "4h"]):
        self.db_path = db_path
        self.timeframes = timeframes

    def build(self) -> tuple[np.ndarray, np.ndarray, list[str]]:
        """
        Returns:
            X: (n_samples, n_total_features) -- 모든 TF 피처 concat
            y: (n_samples,) -- 4H 기준 다음 봉 방향
            names: 피처명 리스트
        """
        frames = {}
        for tf in self.timeframes:
            # dl_features.py의 get_btc_features() 재활용
            X_tf, y_tf, names_tf = get_btc_features(self.db_path, tf)
            frames[tf] = (X_tf, y_tf, [f"{tf}_{n}" for n in names_tf])

        # 4H 타임스탬프 기준으로 정렬
        # 15m/1H 피처는 4H 봉 시작 시점의 최신값으로 forward-fill
        X_aligned = self._align_timeframes(frames)
        return X_aligned

    def _align_timeframes(self, frames: dict) -> tuple:
        """4H 인덱스에 15m/1H 피처를 asof join."""
        ...


class StackedEnsemble:
    """Level-0: XGBoost + LightGBM + CatBoost, Level-1: Logistic meta-learner."""

    def __init__(self, confidence_threshold: float = 0.55):
        self.threshold = confidence_threshold
        self.models_l0 = {
            "xgb": XGBClassifier(n_estimators=300, max_depth=5, ...),
            "lgb": LGBMClassifier(n_estimators=300, max_depth=5, ...),
            "cat": CatBoostClassifier(iterations=300, depth=5, ...),
        }
        self.meta = LogisticRegression()

    def fit(self, X_train: np.ndarray, y_train: np.ndarray,
            X_val: np.ndarray, y_val: np.ndarray) -> None:
        """Walk-forward에서 호출. Level-0 학습 -> OOF 예측 -> Level-1 학습."""
        oof_preds = np.zeros((len(X_train), len(self.models_l0)))
        for i, (name, model) in enumerate(self.models_l0.items()):
            # 5-fold time-series split for OOF
            for train_idx, val_idx in TimeSeriesSplit(5).split(X_train):
                model.fit(X_train[train_idx], y_train[train_idx])
                oof_preds[val_idx, i] = model.predict_proba(X_train[val_idx])[:, 1]
            model.fit(X_train, y_train)  # refit on full train
        self.meta.fit(oof_preds, y_train)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Level-0 예측 -> Level-1 결합."""
        l0_preds = np.column_stack([
            m.predict_proba(X)[:, 1] for m in self.models_l0.values()
        ])
        return self.meta.predict_proba(l0_preds)[:, 1]

    def predict_with_confidence(self, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """확신도 필터 포함 예측."""
        probs = self.predict_proba(X)
        confident = (probs > self.threshold) | (probs < (1 - self.threshold))
        preds = (probs >= 0.5).astype(int)
        return preds, confident
```

#### 구현 단계

1. `dl_features.py`의 `_load_btc_ohlcv()`가 이미 멀티TF 지원 ("15m", "1h", "4h")
2. 각 TF 피처 생성 후 4H 인덱스에 정렬 (asof merge)
3. 총 피처: 29 * 3 = ~87개 (TF별 접두사 추가)
4. XGBoost + LightGBM + CatBoost 스태킹 앙상블
5. Walk-forward 검증 (6개월 학습 / 1개월 테스트)
6. 고신뢰 필터 (>55% 확률만 거래)

---

### 전략 2: Focal Loss + Label Smoothing + Curriculum Learning (가장 빠른 구현)

**예상 향상**: BTC 50.3% -> 52~54%, 전 자산 HC accuracy +3~5%p
**구현 난이도**: 하 (0.5~1일)
**근거**: 노이지 라벨에 대한 학계의 표준 대응. 50% 근처 라벨은 사실상 노이즈.

#### 왜 효과가 있는가

1. **Label Smoothing**: 다음 봉 방향이 +0.01%인 경우, 이것을 "상승(1.0)"으로
   라벨링하면 모델에게 거짓말을 하는 것. 실제로는 "약간 상승(0.6)" 정도가 적절.
   Label smoothing은 이 문제를 직접 해결한다.

2. **Focal Loss**: 모델이 "쉬운 샘플"(강한 추세)에서는 이미 정확하다.
   문제는 "어려운 샘플"(횡보/전환점). Focal loss는 어려운 샘플에 가중치를 줌으로써
   결정 경계를 개선한다. 단, gamma가 너무 크면 노이즈에 오버피팅.

3. **Curriculum Learning**: 쉬운 샘플(큰 수익률 변동)부터 학습 -> 어려운 샘플 점진적 추가.
   모델이 먼저 명확한 패턴을 학습한 후 모호한 영역으로 확장.

4. **조합 효과**: 이 3가지는 상호 보완적. Label smoothing이 노이즈 감소,
   focal loss가 어려운 샘플 집중, curriculum이 학습 경로 최적화.

#### 코드 구조

```python
# scripts/dl_training_improvements.py

class FocalLossWithSmoothing(nn.Module):
    """Focal Loss + Label Smoothing 결합."""

    def __init__(self, gamma: float = 1.5, smoothing: float = 0.1,
                 return_based: bool = True):
        super().__init__()
        self.gamma = gamma
        self.smoothing = smoothing
        self.return_based = return_based

    def forward(self, logits: torch.Tensor, targets: torch.Tensor,
                returns: torch.Tensor | None = None) -> torch.Tensor:
        # 수익률 기반 동적 smoothing
        if self.return_based and returns is not None:
            # abs(return) < 0.1% -> 거의 50/50, 최대 smoothing
            # abs(return) > 1%  -> 확실한 방향, smoothing 없음
            confidence = (returns.abs() * 100).clamp(0, 1)  # 0~1
            smooth = self.smoothing * (1 - confidence)
        else:
            smooth = self.smoothing

        targets_smooth = targets * (1 - smooth) + (1 - targets) * smooth
        bce = F.binary_cross_entropy_with_logits(logits, targets_smooth, reduction='none')

        # Focal weighting
        probs = torch.sigmoid(logits)
        p_t = probs * targets + (1 - probs) * (1 - targets)
        focal_weight = (1 - p_t) ** self.gamma

        return (focal_weight * bce).mean()


class CurriculumScheduler:
    """수익률 크기 기반 curriculum learning."""

    def __init__(self, returns: np.ndarray, n_stages: int = 4):
        self.returns = returns
        self.n_stages = n_stages
        # 수익률 절대값 기준으로 난이도 구간 설정
        abs_ret = np.abs(returns)
        self.thresholds = np.percentile(abs_ret, np.linspace(100, 0, n_stages + 1))

    def get_mask(self, stage: int) -> np.ndarray:
        """stage 0 = 가장 쉬운 25%, stage 3 = 전체."""
        abs_ret = np.abs(self.returns)
        threshold = self.thresholds[min(stage + 1, self.n_stages)]
        return abs_ret >= threshold

    def get_schedule(self, total_epochs: int) -> list[int]:
        """각 stage에 할당할 epoch 수."""
        # 초반 stage에 더 많은 epoch
        weights = [3, 2, 1.5, 1][:self.n_stages]
        total_w = sum(weights)
        return [max(1, int(total_epochs * w / total_w)) for w in weights]


class ImprovedLSTM(nn.Module):
    """Label smoothing + Focal loss + Curriculum 적용 LSTM."""

    def __init__(self, input_dim: int, hidden_dim: int = 128,
                 num_layers: int = 2, dropout: float = 0.3):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                           dropout=dropout, batch_first=True)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        out = self.layer_norm(out[:, -1, :])
        out = self.dropout(out)
        return self.fc(out).squeeze(-1)
```

#### 구현 단계

1. `FocalLossWithSmoothing` 클래스 구현 (dl_btc_lstm.py의 BCEWithLogitsLoss 교체)
2. 수익률 기반 동적 smoothing (abs_return > 1% -> smoothing=0, < 0.1% -> smoothing=0.1)
3. CurriculumScheduler: 4단계 (큰 변동 25% -> 50% -> 75% -> 100%)
4. 기존 walk-forward 루프에 통합
5. LayerNorm 추가 (LSTM 출력 안정화)

---

### 전략 3: 멀티 타임프레임 Temporal Fusion Transformer (가장 높은 잠재력)

**예상 향상**: BTC 54~58%, NVDA 63~67%
**구현 난이도**: 상 (5~7일)
**근거**: TFT는 멀티스케일 시계열 예측에서 SOTA. Google 논문 기반.

#### 왜 효과가 있는가

1. **Variable Selection Network**: 자동으로 유용한 피처 선택 -> 노이즈 피처 억제.
   현재 29개 피처 중 절반 이상이 노이즈인 상황에서 결정적.

2. **Multi-head Attention with Interpretable Weights**: 어떤 시점이 중요한지 학습.
   최근 5봉이 중요한 경우 vs 20봉 전이 중요한 경우를 구분.

3. **Gated Residual Networks**: 비선형 관계를 효율적으로 학습하면서도
   불필요한 경로를 gate로 차단 -> 과적합 억제.

4. **Static + Temporal 분리**: 자산 특성(static)과 시계열 패턴(temporal)을
   별도 경로로 처리 -> 멀티에셋 학습 가능.

#### 코드 구조

```python
# scripts/dl_tft_multi_tf.py

class MultiTFEncoder(nn.Module):
    """각 타임프레임별 독립 인코더 -> 합산."""

    def __init__(self, tf_configs: dict[str, dict]):
        """
        tf_configs: {
            "15m": {"seq_len": 96, "n_features": 29, "hidden": 64},
            "1h":  {"seq_len": 24, "n_features": 29, "hidden": 64},
            "4h":  {"seq_len": 60, "n_features": 29, "hidden": 64},
        }
        """
        super().__init__()
        self.encoders = nn.ModuleDict()
        self.vsns = nn.ModuleDict()  # Variable Selection Networks
        total_hidden = 0

        for tf, cfg in tf_configs.items():
            self.vsns[tf] = VariableSelectionNetwork(
                n_features=cfg["n_features"],
                hidden_dim=cfg["hidden"],
            )
            self.encoders[tf] = nn.LSTM(
                input_size=cfg["hidden"],
                hidden_size=cfg["hidden"],
                num_layers=2, batch_first=True, dropout=0.2
            )
            total_hidden += cfg["hidden"]

        self.fusion = GatedResidualNetwork(total_hidden, total_hidden)

    def forward(self, inputs: dict[str, torch.Tensor]) -> torch.Tensor:
        """
        inputs: {"15m": (B, 96, 29), "1h": (B, 24, 29), "4h": (B, 60, 29)}
        returns: (B, total_hidden)
        """
        encodings = []
        for tf, x in inputs.items():
            x_selected = self.vsns[tf](x)        # (B, T, hidden)
            _, (h, _) = self.encoders[tf](x_selected)
            encodings.append(h[-1])               # (B, hidden)
        combined = torch.cat(encodings, dim=-1)   # (B, total_hidden)
        return self.fusion(combined)


class VariableSelectionNetwork(nn.Module):
    """TFT의 핵심 컴포넌트: 피처별 중요도를 학습하여 가중 선택."""

    def __init__(self, n_features: int, hidden_dim: int):
        super().__init__()
        self.grn = GatedResidualNetwork(n_features, hidden_dim)
        self.softmax = nn.Softmax(dim=-1)
        self.feature_transforms = nn.ModuleList([
            GatedResidualNetwork(1, hidden_dim) for _ in range(n_features)
        ])

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, T, n_features)
        B, T, F = x.shape
        # 전체 입력으로 피처 가중치 계산
        flat = x.reshape(B * T, F)
        weights = self.softmax(self.grn(flat))  # (B*T, hidden)
        # 각 피처 독립 변환
        transformed = []
        for i, transform in enumerate(self.feature_transforms):
            feat_i = x[:, :, i:i+1]  # (B, T, 1)
            transformed.append(transform(feat_i.reshape(-1, 1)))
        stacked = torch.stack(transformed, dim=1)  # (B*T, F, hidden)
        # 가중합
        weighted = (stacked * weights.unsqueeze(1)).sum(dim=1)
        return weighted.reshape(B, T, -1)


class GatedResidualNetwork(nn.Module):
    """Gated Linear Unit + skip connection."""

    def __init__(self, input_dim: int, hidden_dim: int, dropout: float = 0.1):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.gate = nn.Linear(hidden_dim, hidden_dim)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        self.dropout = nn.Dropout(dropout)
        self.skip = nn.Linear(input_dim, hidden_dim) if input_dim != hidden_dim else nn.Identity()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        h = F.elu(self.fc1(x))
        h = self.dropout(h)
        h = self.fc2(h) * torch.sigmoid(self.gate(h))  # GLU
        return self.layer_norm(h + residual)


class TFTDirectionPredictor(nn.Module):
    """Complete Multi-TF Temporal Fusion Transformer for direction prediction."""

    def __init__(self, tf_configs: dict, n_static: int = 0):
        super().__init__()
        self.encoder = MultiTFEncoder(tf_configs)
        total_h = sum(cfg["hidden"] for cfg in tf_configs.values())

        self.attention = nn.MultiheadAttention(total_h, num_heads=4, batch_first=True)
        self.output_grn = GatedResidualNetwork(total_h, total_h)
        self.head = nn.Linear(total_h, 1)

    def forward(self, inputs: dict[str, torch.Tensor]) -> torch.Tensor:
        encoded = self.encoder(inputs)  # (B, total_hidden)
        out = self.output_grn(encoded)
        return self.head(out).squeeze(-1)
```

#### 구현 단계

1. `GatedResidualNetwork`, `VariableSelectionNetwork` 기본 블록 구현
2. `MultiTFEncoder`: 15m(96봉=1일) + 1H(24봉=1일) + 4H(60봉=10일) 입력
3. `TFTDirectionPredictor`: 통합 모델
4. `dl_features.py`에서 멀티TF 데이터 로딩 (이미 지원)
5. Walk-forward 학습 (dl_train_pipeline.py 재활용)
6. 해석 가능성: VSN 가중치로 어떤 피처/시간이 중요한지 시각화

---

## 3. 추가 피처 제안 (무료 접근 가능)

### BTC 전용

| 피처 | 소스 | 예측력 근거 | 구현 |
|------|------|------------|------|
| Funding Rate (8h) | Binance API (무료) | 과매수/과매도 극단 시 반전 예측력 | `dl_features.py`에 이미 코드 존재, 데이터 수집만 필요 |
| Funding Rate 누적 (24h) | 위와 동일 | 지속적 양/음 = 추세 강도 | `funding_rate.rolling(3).sum()` |
| OI 변화율 (4h) | Binance Futures API | OI 급증 + 가격 상승 = 추세 지속 | ccxt로 수집 가능 |
| Exchange Netflow | CryptoQuant (무료 티어) | 거래소 유입 = 매도 압력 | API 호출, 일간 데이터 |
| BTC Dominance 변화 | CoinGecko (무료) | 알트코인 자금 유출입 지표 | API 호출 |
| Fear & Greed Index | alternative.me (무료) | 극단적 공포 = 반등 신호 | 단순 GET 요청 |

### NVDA/AMZN 전용 (이미 일부 구현됨)

| 피처 | 소스 | 현재 상태 |
|------|------|----------|
| VIX 변화율 | yfinance | dl_features.py에 `vix_norm` 존재, 변화율 추가 필요 |
| 섹터 상대강도 | yfinance | `nvda_qqq_rs` 존재, XLK/SMH 추가 가능 |
| Put/Call Ratio | CBOE (무료 지연) | 미구현, 일간 데이터 |
| 실적 시즌 거리 | 계산 | 실적 발표 전후 패턴 강함 |
| 10Y 금리 변화 | yfinance (^TNX) | 기술주 민감도 높음 |

---

## 4. 전략 비교 및 실행 순서

| # | 전략 | BTC 예상 | NVDA 예상 | 난이도 | 구현 시간 |
|---|------|---------|----------|--------|----------|
| 1 | 멀티TF + XGBoost Stacking | 54~56% | 63~65% | 중 | 2~3일 |
| 2 | Focal Loss + Smoothing + Curriculum | 52~54% | 62~64% | 하 | 0.5~1일 |
| 3 | TFT Multi-TF | 54~58% | 63~67% | 상 | 5~7일 |

### 권장 실행 순서

**1단계 (Day 1)**: 전략 2 먼저 적용.
- 기존 `dl_btc_lstm.py`에 Focal Loss + Label Smoothing만 교체하면 즉시 테스트 가능.
- 빠르게 baseline 향상 확인.

**2단계 (Day 2~3)**: 전략 1 구현.
- `dl_features.py`가 이미 멀티TF 지원하므로, 피처 정렬 + XGBoost 스태킹만 추가.
- RL 로그의 교훈 #15 ("예측 + 실행 분리가 RL보다 효과적")와 일관.

**3단계 (Day 4~7)**: 전략 3은 전략 1의 결과가 목표 미달일 경우에만.
- TFT는 구현 복잡도 대비 전략 1 보다 2~3%p 더 높을 수 있지만,
  XGBoost 스태킹이 이미 55%+ 달성하면 불필요.

### 핵심 주의사항

1. **RL 로그 교훈 #20**: 공격적 파라미터는 과적합만 증가. 보수적으로 시작.
2. **RL 로그 교훈 #15**: 예측(DL/ML) + 실행(CMA-ES 규칙) 분리가 최적.
3. **고신뢰 필터 필수**: 전체 정확도보다 HC(High Confidence) 정확도가 실전 수익과 직결.
   55%+ 확률인 샘플만 거래하면 전체 50%라도 거래 가능 구간에서 56%+ 가능.
4. **Walk-Forward 필수**: 단순 train/test split은 과적합 위험. 최소 6개월 rolling.
5. **기존 Hybrid 전략과 통합**: 새 DL 모델은 `strategy_deploy.py`의 XGBoost를 교체/보강.

---

## 5. 기존 코드와의 통합 경로

현재 프로덕션 전략: CMA-ES + XGBoost >55% + 동적 사이징 (strategy_deploy.py)

DL 개선은 이 파이프라인의 **XGBoost 예측기**를 교체/강화하는 형태로 통합:

```
[기존] CMA-ES 규칙 시그널 -> XGBoost 55% 필터 -> 동적 사이징 -> 거래
[개선] CMA-ES 규칙 시그널 -> Multi-TF Stacking 57%+ 필터 -> 동적 사이징 -> 거래
```

이렇게 하면:
- RL 로그 교훈 #15 유지 (예측 + 실행 분리)
- 기존 검증된 인프라 재활용
- DL 모델 실패 시 XGBoost 폴백 가능
