# Round 2 — Claude opus

### Q1 답변 (A의 drift 리스크)

**결론**: commit hash 주석만으로는 부족. **포크 파일에 commit hash 헤더 + CI-level read-only 보강**이 필요.

**논증**:
- 48h 동안 v2.py 수정 가능성은 낮지만 0이 아님. 실제로 v2.py는 `_rebalance_memory()` 수식 자체가 이미 두 번 수정된 이력이 있다(주석 "FIX: importance = |w| only" 라인 316, "FIX: exploration noise for underused features" 라인 338). 즉 Rule 2 로직은 **활성 수정 영역**이다. Ablation이 "현행 Rule 2"를 대변하려면 포크 시점의 commit hash 고정이 필수.
- drift 방지 3중 장치:
  1. **파일 상단 헤더**: `# Forked from v2.py @ <40-char SHA> on 2026-04-21. DO NOT sync.`
  2. **git 수준 격리**: `scripts/archive/` 아래에 두지 말고 `scripts/v2_ablation.py`에 두되, `.gitattributes`로 `linguist-generated=true` 마킹 (리뷰 시 diff 노이즈 억제 + 자동 머지 방지 의도 명시).
  3. **48h 만료 체크리스트**: `project-status/current.md` Open Items에 "YYYY-MM-DD 이전 archive 이동" 자동화 스크립트 등록.
- drift "검증" 차원에서 48h 이후 `diff scripts/v2.py scripts/v2_ablation.py`가 `_rebalance_memory` 블록 외에만 변경이 있도록 강제하는 sanity check 스크립트도 좋다(이탈 시 PASS/FAIL 결론 invalidate).

`.gitattributes`의 read-only branch나 worktree를 쓸 수도 있으나 **오버엔지니어링**. 48h 임시 실험에는 헤더 주석 + 만료 체크리스트로 충분.

---

### Q2 답변 (핵심) — Codex D-1안 Python 실행경로 검증

**결론**: **D-1은 Python 문법상 가능하지만, v2.py 실제 코드 구조 때문에 "v2.py 무수정" 장점이 붕괴된다.** 따라서 D는 실질적으로 D-2(v2.py 수정)로 수렴하거나 A와 공수 동등이 된다.

#### 검증 포인트 1: `self.predictors` 재할당 부작용 검증

v2.py:605-625 `V2Engine.__init__` 분석:

```python
def __init__(self, assets: list[str], port: int = DASH_PORT):
    self.assets = assets
    ...
    self.predictors: dict[str, OnlinePredictor] = {
        a: OnlinePredictor() for a in assets  # <-- 부모가 먼저 생성
    }
    self.pm = PositionManager()
    self.history: dict[str, pd.DataFrame] = {}
    ...
    self.prev_features: dict[str, np.ndarray] = {}
    self._last_funding: dict[str, float] = {a: 0.0 for a in assets}
```

**중요 관찰**: `__init__` 본문 내에서 `self.predictors` dict는 **생성 후 추가 사용되지 않는다**. 즉 부모 `__init__` 리턴 직후 subclass가 `self.predictors = { a: NoRule2Predictor() for a in assets }`로 재할당해도 **생성 시점 부작용은 없다**.

`OnlinePredictor.__init__` (v2.py:252-268) 자체도 순수 초기화(numpy array, list, EMANormalizer 인스턴스화)만 수행하고 외부 파일·네트워크·전역 상태 변경이 없다. 즉 부모가 만든 OnlinePredictor 4개(ETH/BTC/SOL/XRP)는 `self.predictors` 재할당 시 참조 카운트가 0이 되어 즉시 GC 대상.

→ **D-1의 subclass 메커니즘은 파이썬 수준에서 문제없이 작동한다.** 낭비되는 초기화 4회분은 수백 마이크로초 수준으로 무시 가능.

#### 검증 포인트 2: `_rebalance_memory` no-op 오버라이드 시 `update()` 정합성

v2.py:275-312 `update()` 메서드 분석:

```python
def update(self, x_prev, y_true):
    self.norm.update(x_prev)
    x_n = self.norm.normalize(x_prev)
    y_pred = ...
    # SGD ... self.w -= self.lr * grad_w; self.b -= self.lr * grad_b
    self.predictions.append(y_pred)
    self.actuals.append(y_true)
    self._rebalance_memory()   # <-- Rule 2 진입 지점
    if len(self.predictions) >= 10:
        # accuracy_history.append(...)
```

`_rebalance_memory` (v2.py:314-342)가 수행하는 변경:
- `self.feature_importance = p` (또는 uniform)
- `self.entropy_history.append(...)`
- `self.l2_per_feat = self.base_l2 * (1.0 + ...)`
- `self.w += np.random.randn(self.n) * noise_scale` (underused features 한정)

→ `_rebalance_memory`를 단순 `pass`로 오버라이드하면 **Rule 2가 건드리는 4개 상태(`feature_importance`, `entropy_history`, `l2_per_feat`, `w`)가 초기값 그대로 고정**된다. 이는 정확히 "Rule 2 OFF" 의미.

하지만 **여기서 부작용 2가지 발생**:

1. **`entropy_history`가 비어 있으면 `memory_entropy()` (v2.py:344-347)가 항상 1.0 반환** → `calibration()` (v2.py:354-362)의 `ent_factor = max(ent, 0.3)`이 항상 1.0 → no-rule2 variant는 **엔트로피 floor 보정의 영향을 덜 받는다** (현재 코드상 max(ent,0.3)가 bottleneck인 케이스가 있으면 그 영향 제거). 이건 실험 관점에서는 **바람직**(Rule 2가 calibration에 미치는 영향도 함께 변수로 들어가야 함).
2. **`l2_per_feat`가 `base_l2`로 고정됨** → `update()` 내 `grad_w = error * x_n + self.l2_per_feat * self.w`가 항상 uniform L2 regularization을 사용. 이게 바로 "Rule 2 OFF" 정의 그 자체이므로 의도대로.

→ `predict()` (v2.py:270-273)는 `self.w`, `self.b`, `self.norm`만 읽으므로 동일하게 동작.
→ `update()`는 마지막 블록(`accuracy_history` 계산)도 동일하게 동작.

**결론**: no-op 오버라이드는 Rule 2 단일 변수 분리를 정확히 달성한다. **예측 레이어 메커니즘은 D-1이 A보다 오히려 깨끗하다.**

#### 검증 포인트 3 (결정타): 모듈-레벨 글로벌 참조

**여기서 D-1이 붕괴한다.**

v2.py는 `STATE_PATH`, `LOG_PATH`, `DASH_PORT`를 **모듈 상수**로 정의(v2.py:46-48)하고 클래스 메서드 내부에서 **직접 참조**한다:

```python
# v2.py:790 — _log_tick
with open(LOG_PATH, "a") as f:   # <-- 모듈 전역 LOG_PATH

# v2.py:852 — _save_state
np.savez_compressed(STATE_PATH, **state)  # <-- 모듈 전역 STATE_PATH

# v2.py:858, 861 — _load_state
if not STATE_PATH.exists(): ...
d = np.load(STATE_PATH, allow_pickle=True)
```

**이게 치명적**인 이유:
- `V2Engine.port`는 `__init__` 파라미터로 들어오므로 subclass가 다른 포트를 넘길 수 있다 (8897 → 8902).
- 그러나 **`LOG_PATH`, `STATE_PATH`는 `self`를 경유하지 않는다.** subclass에서 이 경로를 분리하려면 다음 중 하나가 필수:
  - **(a) monkey-patch**: `import v2; v2.LOG_PATH = Path(...); v2.STATE_PATH = Path(...)` — 런타임 전역 오염. ablation harness가 live v2.py 프로세스와 같은 인터프리터에 있지 않으므로 실제로는 안전하지만 **"코드 무수정" 원칙의 스피릿 위반** + 런타임 디버깅 지옥.
  - **(b) `_log_tick`, `_save_state`, `_load_state` 3개 메서드 모두 오버라이드**: 각 메서드는 각각 15~25 LOC. 3개 × 20 LOC = 약 60 LOC를 subclass에 복붙해야 함. 이 순간 "D = 얇은 wrapper"의 본질이 무너진다 — 실질적으로 포크와 동등한 코드 중복.
  - **(c) v2.py 수정**: `STATE_PATH`/`LOG_PATH`를 `self.state_path`/`self.log_path`로 승격 + `__init__` 파라미터화 — **v2.py 수정 필요** → D의 유일한 장점("v2.py 무수정") 소멸. 이게 바로 Q2 프롬프트가 말한 **D-2 시나리오**.

**정량 비교**:
| 방안 | v2.py 수정 | 추가 파일 LOC | 리스크 |
|------|-----------|---------------|-------|
| A (포크) | 없음 | ~900 (복사본) + 5 LOC flag | 3 |
| D-1 (monkey-patch) | 없음 | ~50 (subclass 2개) + monkey-patch | 4 (전역 오염) |
| D-1 (메서드 3개 오버라이드) | 없음 | ~80 (subclass 2개 + 메서드 복붙) | 3 |
| D-2 (v2.py 파라미터화) | 5-8 LOC | ~30 | 3 (live 회귀 가능성) |

**핵심 반전**: Codex가 주장한 "D는 6-10h / 리스크 2" 수치는 **`STATE_PATH`/`LOG_PATH` 분리 공수를 누락**한 것. 모듈-레벨 글로벌을 실제로 분리하면 D-1(메서드 복붙)은 80 LOC 수준으로 A(포크 + 5 LOC flag)와 **실질적으로 동등한 공수**가 된다. "D-1 최소 추가 파일" 주장은 코드 읽기 없이 나온 낙관론이다.

→ **Q2 최종**: D-1은 Python 언어 문법상 가능하지만, **v2.py의 모듈-레벨 글로벌 참조가 D의 "얇은 wrapper" 성격을 부정**한다. 현실적으로 D는 A보다 이득이 없다.

---

### Q3 답변 (A 구체 구현 경로)

A로 갈 때 D를 주장하던 Codex가 "A 실제 공수"를 놓친 부분을 메우기 위해 **라인 레벨 체크리스트**를 제시한다.

**단계**:
1. **포크**: `cp scripts/v2.py scripts/v2_ablation.py`
2. **헤더 주석 추가** (파일 최상단):
   ```python
   """V2 Rule 2 Ablation Fork.
   Forked from v2.py @ <SHA-to-be-filled> on 2026-04-21.
   Purpose: Rule 2 on/off A-B test. 48h lifecycle. Archive to scripts/archive/ after 2026-04-23.
   DO NOT sync with v2.py — this is a snapshot for experiment purity.
   """
   ```
3. **모듈 상수 재정의** (v2.py:46-48 대응 라인):
   ```python
   STATE_PATH = DATA_DIR / "v2_ablation_state.npz"   # 기존 v2_state.npz → 격리
   LOG_PATH = DATA_DIR / "v2_ablation.jsonl"         # 기존 v2.jsonl → 격리
   DASH_PORT = 8902                                   # 기존 8897 → 격리
   ```
4. **variant flag 추가** (argparse 영역 main 함수 내):
   ```python
   parser.add_argument("--no-rule2", action="store_true",
                       help="Disable Rule 2 (_rebalance_memory). For ablation.")
   ```
   그리고 variant별 산출물 분리:
   ```python
   global STATE_PATH, LOG_PATH  # main() 내
   suffix = "_no_rule2" if args.no_rule2 else "_with_rule2"
   STATE_PATH = DATA_DIR / f"v2_ablation{suffix}_state.npz"
   LOG_PATH = DATA_DIR / f"v2_ablation{suffix}.jsonl"
   ```
5. **Rule 2 OFF 구현** — v2.py:302 대응 라인 한 군데:
   ```python
   # 변경 전: self._rebalance_memory()
   # 변경 후:
   if not NO_RULE2:   # 모듈 수준 flag
       self._rebalance_memory()
   ```
   `NO_RULE2`는 main()에서 global 선언 후 args.no_rule2로 세팅.
6. **OnlinePredictor 생성자에서 flag 주입하고 싶으면** (더 깔끔한 형태):
   ```python
   class OnlinePredictor:
       def __init__(self, ..., enable_rule2: bool = True):
           self.enable_rule2 = enable_rule2
           ...
       def update(self, ...):
           ...
           if self.enable_rule2:
               self._rebalance_memory()
           ...
   ```
   그리고 V2Engine이 `OnlinePredictor(enable_rule2=not args.no_rule2)`로 넘김. 이게 **argparse로 동일 파일에서 두 variant를 한 번에 돌리는 방식**.
7. **포지션/재개 상태 무효화**: ablation 시작 시 `v2_ablation*_state.npz` 파일이 없도록 한 번 clean.
8. **48h 후 archive**: `scripts/archive/v2_ablation_2026-04-21.py`로 자동 이동하는 one-liner cron 또는 수동 체크리스트.

**총 수정 LOC**: argparse 3줄 + global 2줄 + `if not NO_RULE2` 1줄 + header 5줄 + 경로 상수 3줄 ≈ **14 LOC**. 
**공수**: 2-3h(코드) + 48h 관찰 + 0.5h archive 정리.

---

### Q4 답변 (하이브리드 실현 가능성)

**"A의 포크 + 파일명만 `oracle_rule2_ablation.py`"** 하이브리드는 **양쪽 단점만 합친 안**이다. 기각.

**논증**:
- Charter 조항 I의 **입법 취지**(live 환경 보호)는 A(포크)가 이미 충족. **문언**("oracle.py 격리")은 파일명만 바꿔도 만족되지 않는다 — 내용이 `V2Engine` 포크인데 이름만 `oracle_...`로 붙이면 **Charter 정신에 더 반하는** 혼란을 만든다. "Oracle 레이어 파일인 줄 알고 읽었더니 V2 포크" — Phase 3 Oracle 선구현 시점에 실제 `oracle.py`나 `oracle_rule2_ablation.py`를 신설할 때 **네이밍 충돌 + 의미 혼동** 리스크.
- A의 본질적 주장은 "변수 분리 정확도". 파일명을 Oracle로 바꾸면 이 명분은 유지되지만 **혼란은 늘고 이득은 없다**.
- D의 본질적 주장은 "동일 코드경로 + 무수정". 파일명만 Oracle로 바꿔도 **내용이 V2 포크이면 D의 본질을 버린 것**.

**각 진영의 본질적 주장 만족 여부**:
| 진영 주장 | 하이브리드에서 | 결론 |
|----------|---------------|------|
| A: 변수 분리 정확도 | 유지 | OK |
| A: 공수 최소 | 유지 | OK |
| D: v2.py 무수정 + 동일 경로 | **불충족** (포크임) | 실패 |
| Charter 문언 | 파일명은 oracle_* | 표면 만족 |
| Charter 입법 취지 | live 격리 | 만족 |
| 차후 Oracle 파일 네이밍 | **충돌 유발** | 실패 |

**대안 제시**: 하이브리드가 진정 필요하면 **"A + Phase 2 Component Map 각주 명시"**가 낫다 — 파일명은 `v2_ablation.py`(내용과 일치), 각주에 "Charter 조항 I의 입법 취지(live 환경 보호) 충족을 위한 예외적 V2 포크. Phase 3 Oracle 파일과 무관"을 남긴다. 이는 Charter 문언 위배를 **투명하게** 기록하고 후속 리뷰가 가능하게 한다.

---

### 최종 결론

- **Position**: **A** (`scripts/v2_ablation.py` — V2 포크 + `--no-rule2` flag)
- **Reasoning**: D-1은 Python 문법상 가능하지만 v2.py의 모듈-레벨 글로벌(`STATE_PATH`/`LOG_PATH`/`DASH_PORT`) 때문에 "얇은 wrapper" 성격이 붕괴되어 실질 공수·리스크가 A와 동등 내지 더 나빠진다. 반면 A는 14 LOC 수정으로 변수 분리 정확도를 최고 수준으로 달성하며, commit hash 헤더 + 48h 만료 체크리스트로 drift를 통제할 수 있다.
- **Shift from Round 1**: **없음**. Round 1에서 "Rule 2는 단일 라인, 포크 수정 3-5 LOC" 주장을 유지. Round 2에서 v2.py 실제 코드를 읽어 오히려 **Codex의 D-1이 누락한 공수(모듈-레벨 글로벌 분리)를 특정**함으로써 A 입장이 더 강화됨. 지적 정직성 관점에서 D-1의 Python 실행 가능성은 인정하되, 실제 v2.py 구조가 D의 경제성 주장을 부정한다는 새 증거가 나왔다.

[POSITION: T2=A]
