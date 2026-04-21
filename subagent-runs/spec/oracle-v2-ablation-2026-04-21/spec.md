# [기능+인프라] scripts/v2_ablation.py — V2 Rule 2 Ablation Fork

> **긴급도**: 높음 (Charter 태스크 1번 48h Go/No-Go gate, 5일 내 기동)
> **선행 조건**: v2.py commit `417534bdae39c0c09f93b8906d583893ddb98cc6` HEAD 유지
> **작업 유형**: 기능(백엔드 harness) + 인프라(포트/파일경로 분리)
> **DB migration**: 없음
> **외부 의존**: 없음 (기존 v2.py가 이미 사용 중인 `ccxt`, `numpy`, `pandas`, `scipy` 재사용)

---

## 배경

Oracle 예측 엔진 재설계(Phase 1 Charter 통과)의 **태스크 1번**은 V2 실패의 근본 원인이 Rule 2(엔트로피 균등화)인지 **단일 변수 실험**으로 48h 검증. 결과에 따라 분기:

- **PASS**: V2에 Rule 2 제거 패치만 적용 → Oracle 스코프 축소 재검토 (Charter Tier 2)
- **FAIL**: Oracle 재설계 원안대로 Phase 3 진입
- **INCONCLUSIVE**: 48h 1회 연장, 그래도 모호 시 FAIL

Oracle 본체는 Phase 3 이후 구현이므로 ablation은 **V2 포크 + `--no-rule2` flag**로 수행 (`/discuss oracle-design-decisions-2026-04-21` Round 2 투표 A 2/D 1 결과). v2.py 원본은 live(port 8897) 운영 중이므로 절대 수정 금지.

**참조 문서**:
- `subagent-runs/design/oracle-2026-04-21/phase1-charter.md` (조항 A~J, 태스크 1번)
- `subagent-runs/design/oracle-2026-04-21/phase2-component-map.md` (각주 1 — v2_ablation.py 예외 기록)
- `subagent-runs/design/oracle-2026-04-21/48h-ablation-plan.md` (§ 구현 체크리스트 10단계, 통과 기준 6항목)
- `subagent-runs/discuss/oracle-design-decisions-2026-04-21/conclusion.md` (A 채택 근거, Codex Round 2 caveat 포함)

---

## 접근 통제

ablation 대시보드는 **로컬 개발 머신에서만 접근 가능**해야 함 (paper trades 내부 관찰용, 외부 노출 금지).

**변경 대상**: `V2Engine.run()` 내 `http.server.HTTPServer` 바인딩 주소 (v2.py:882 기준).

**Before (v2.py:882 인근)**:
```python
server = http.server.HTTPServer(("0.0.0.0", self.port), DashboardHandler)
```

**After (v2_ablation.py 동일 위치)**:
```python
# ablation: loopback-only. live v2.py(0.0.0.0)와 다르게 외부 노출 금지.
server = http.server.HTTPServer(("127.0.0.1", self.port), DashboardHandler)
```

**근거**:
- v2.py는 live 운영 + Windows 로컬 네트워크 기기에서 관찰 가능하도록 `0.0.0.0` 바인딩. ablation은 임시 도구로 외부 노출 불필요.
- 운영 머신이 방화벽 밖에 있는 경우, `0.0.0.0` 바인딩 시 8902/8903이 LAN/인터넷에 노출 — 미인증 대시보드라 위험.

**검증**:
```bash
# 기동 후 LAN IP에서 접근 불가 확인 (연결 거부되어야 정상)
curl -sS -m 3 http://127.0.0.1:8902/ | head -5        # 정상 응답
curl -sS -m 3 http://<LAN_IP>:8902/ || echo "blocked"  # blocked 출력 기대
```

Windows 환경에서 LAN IP는 `ipconfig` 의 `IPv4 Address`. `curl -m 3`의 `timeout` 또는 `connection refused` 양쪽 모두 "blocked" 판정.

---

## 작업 범위

### [필수]
1. `Projects/Trading Value/scripts/v2.py`를 `Projects/Trading Value/scripts/v2_ablation.py`로 복사 후 본 지시서 라인별 수정.
2. 파일 헤더에 commit SHA(`417534bdae39c0c09f93b8906d583893ddb98cc6`), 목적, 48h 라이프사이클, 아카이브 일정 명시.
3. 모듈 상수 `STATE_PATH`, `LOG_PATH`, `DASH_PORT`를 ablation 전용 값으로 분리.
4. `OnlinePredictor.__init__`에 `enable_rule2: bool = True` 파라미터 추가.
5. `OnlinePredictor.update()` 내 `self._rebalance_memory()` 호출을 `if self.enable_rule2:` gate.
6. `V2Engine.__init__`에 `enable_rule2: bool = True` 파라미터 추가하여 predictor 생성 시 주입.
7. argparse에 `--no-rule2` (store_true) 추가. 기존 `--port`, `--assets` 유지.
8. variant별 산출물 경로 분기: `--no-rule2` 여부로 `_with_rule2` / `_no_rule2` suffix 적용.
9. RNG 고정: `main()` 시작 시 `numpy.random.seed(42)` (양 variant 동일 시점 호출).
10. smoke test 스크립트 `scripts/v2_ablation_smoke.py` 작성 (1 tick 실행 후 flag 검증).

### [선택]
- 48h 후 자동 archive 이관 스크립트 `scripts/archive/_archive_ablation.sh` (수동 이관으로 대체 가능).
- `data/v2_ablation_summary.csv` 하루 단위 집계 스크립트 (분석 Phase에서 작성 가능).

### [금지]
- **`Projects/Trading Value/scripts/v2.py` 원본 수정 금지** (live 8897 운영). diff가 0이어야 함.
- `data/v2.jsonl`, `data/v2_state.npz` 등 live 산출물 경로에 write 금지.
- 포트 8897(live)에 바인딩 금지.
- Live trading 활성화 금지 (paper trades only — v2.py 기본 동작 그대로).
- Oracle 본체 구현 금지 (ablation은 V2 기반, Oracle 미구현 상태 전제).
- 기존 `v2.py` import 후 monkey-patch 방식 금지 (포크 + 상수 교체만 허용, `/discuss` Round 2 결론).

---

## 구현 대상 — 라인별 체크리스트

아래 라인 번호는 **원본 `v2.py` 기준**. 포크본 `v2_ablation.py`에서 동일 위치를 찾아 수정.

### 단계 1. 파일 복사

```bash
cp "Projects/Trading Value/scripts/v2.py" "Projects/Trading Value/scripts/v2_ablation.py"
```

### 단계 2. 파일 헤더 추가 (v2_ablation.py 최상단, shebang/encoding 이전)

기존 v2.py에는 헤더 docstring이 없음. v2_ablation.py **파일 최상단**(import 이전)에 다음 docstring 추가:

```python
"""V2 Rule 2 Ablation Fork.

Forked from scripts/v2.py @ 417534bdae39c0c09f93b8906d583893ddb98cc6 on 2026-04-21.

Purpose
-------
Charter 태스크 1번 48h Rule 2 Go/No-Go gate. V2의 엔트로피 균등화 로직(Rule 2,
OnlinePredictor._rebalance_memory)을 단일 변수로 분리해 A-B test.

Variants
--------
- control   (Rule 2 유지): python scripts/v2_ablation.py --port 8902
- no_rule2  (Rule 2 제거): python scripts/v2_ablation.py --no-rule2 --port 8903

Artifacts
---------
- data/v2_ablation_{with_rule2|no_rule2}.jsonl   — tick 로그
- data/v2_ablation_{with_rule2|no_rule2}_state.npz — 가중치 스냅샷

Lifecycle
---------
48h paper trades. 2026-04-23 분석 후 scripts/archive/v2_ablation_2026-04-21.py 로 이관.

Constraints
-----------
- 이 파일은 v2.py와 동기화하지 않음 (`/discuss oracle-design-decisions-2026-04-21` A 채택).
- live port 8897은 건드리지 않음.
- paper trades only. Live trading 금지.
"""
```

### 단계 3. 모듈 상수 분리 (v2.py:46-48 대응)

**Before (v2.py:45-52)**:
```python
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
STATE_PATH = DATA_DIR / "v2_state.npz"
LOG_PATH = DATA_DIR / "v2.jsonl"
DASH_PORT = 8897
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800
```

**After (v2_ablation.py 동일 위치)**:
```python
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
# NOTE: STATE_PATH / LOG_PATH는 main()에서 variant suffix로 재바인딩됨.
#       여기서는 fallback/기본값만 지정.
STATE_PATH = DATA_DIR / "v2_ablation_with_rule2_state.npz"  # fallback
LOG_PATH = DATA_DIR / "v2_ablation_with_rule2.jsonl"         # fallback
DASH_PORT = 8902  # control default. --no-rule2 시 argparse에서 8903 override.
TICK_SEC = 60
HISTORY_BARS = 500
INITIAL_CAPITAL = 10_000.0
SAVE_INTERVAL = 1800
```

### 단계 4. `OnlinePredictor.__init__`에 flag 추가 (v2.py:252-268 대응)

**Before (v2.py:252-253)**:
```python
def __init__(self, n: int = N_FEATURES, lr: float = 0.003,
             base_l2: float = 0.001, memory_alpha: float = 2.0):
```

**After**:
```python
def __init__(self, n: int = N_FEATURES, lr: float = 0.003,
             base_l2: float = 0.001, memory_alpha: float = 2.0,
             enable_rule2: bool = True):
    self.enable_rule2 = enable_rule2
    # 기존 초기화 그대로 유지
```

**주의**: `self.enable_rule2 = enable_rule2` 라인은 기존 `self.n = n` **바로 앞**에 추가 (가독성).

### 단계 5. `OnlinePredictor.update()` gate (v2.py:300-302 대응)

**Before (v2.py:298-302)**:
```python
self.predictions.append(y_pred)
self.actuals.append(y_true)

# Rule 2: rebalance memory
self._rebalance_memory()
```

**After**:
```python
self.predictions.append(y_pred)
self.actuals.append(y_true)

# Rule 2: rebalance memory (gated for ablation)
if self.enable_rule2:
    self._rebalance_memory()
```

**금지**: `_rebalance_memory()` 본체(v2.py:314-342) 자체는 수정하지 말 것. gate만 추가.

### 단계 6. `V2Engine.__init__`에 flag 전파 (v2.py:604-625 대응)

**Before (v2.py:604-615)**:
```python
class V2Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT):
        self.assets = assets
        self.port = port
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        self.feature_engines: dict[str, FeatureEngine] = {
            a: FeatureEngine() for a in assets
        }
        # Per-asset predictors (Rule 1: each asset gets its own model)
        self.predictors: dict[str, OnlinePredictor] = {
            a: OnlinePredictor() for a in assets
        }
```

**After**:
```python
class V2Engine:
    def __init__(self, assets: list[str], port: int = DASH_PORT,
                 enable_rule2: bool = True):
        self.assets = assets
        self.port = port
        self.enable_rule2 = enable_rule2
        self.exchange = ccxt.bybit({"enableRateLimit": True})
        self.feature_engines: dict[str, FeatureEngine] = {
            a: FeatureEngine() for a in assets
        }
        # Per-asset predictors (Rule 1: each asset gets its own model)
        # Rule 2 toggle: enable_rule2=False → _rebalance_memory() no-op (ablation)
        self.predictors: dict[str, OnlinePredictor] = {
            a: OnlinePredictor(enable_rule2=enable_rule2) for a in assets
        }
```

### 단계 7. `main()` argparse + RNG + 상수 재바인딩 (v2.py:898-908 대응)

**Before (v2.py:898-908)**:
```python
def main():
    parser = argparse.ArgumentParser(description="V2 Prediction Engine")
    parser.add_argument("--assets", default="ETH,BTC,SOL,XRP")
    parser.add_argument("--port", type=int, default=DASH_PORT)
    args = parser.parse_args()
    assets = [a.strip().upper() for a in args.assets.split(",")]
    V2Engine(assets=assets, port=args.port).run()


if __name__ == "__main__":
    main()
```

**After**:
```python
def main():
    parser = argparse.ArgumentParser(
        description="V2 Rule 2 Ablation Harness (forked from v2.py). Paper trades only."
    )
    parser.add_argument("--assets", default="BTC,ETH,SOL",
                        help="Comma-separated. Default BTC,ETH,SOL (ablation priority).")
    parser.add_argument("--port", type=int, default=DASH_PORT,
                        help="Dashboard port. Default 8902 (control). Use 8903 for --no-rule2.")
    parser.add_argument("--no-rule2", dest="no_rule2", action="store_true",
                        help="Disable Rule 2 (_rebalance_memory no-op). Ablation treatment arm.")
    args = parser.parse_args()

    enable_rule2 = not args.no_rule2
    variant = "no_rule2" if args.no_rule2 else "with_rule2"

    # variant별 산출물 경로 재바인딩 (글로벌 교체 — _save_state/_load_state/_log_tick가 참조)
    global STATE_PATH, LOG_PATH
    STATE_PATH = DATA_DIR / f"v2_ablation_{variant}_state.npz"
    LOG_PATH = DATA_DIR / f"v2_ablation_{variant}.jsonl"

    # RNG 고정 (strict one-variable ablation — 양 variant 동일 시점 호출)
    np.random.seed(42)

    assets = [a.strip().upper() for a in args.assets.split(",")]

    print(f"[v2_ablation] variant={variant} port={args.port} enable_rule2={enable_rule2}")
    print(f"[v2_ablation] log={LOG_PATH.name} state={STATE_PATH.name}")
    print(f"[v2_ablation] assets={assets} seed=42")

    V2Engine(assets=assets, port=args.port, enable_rule2=enable_rule2).run()


if __name__ == "__main__":
    main()
```

**주의 1**: `global STATE_PATH, LOG_PATH` 선언 필수. 선언 없이 재할당하면 `main()` 스코프 지역 변수가 되어 `V2Engine._save_state`/`_load_state`/`_log_tick`의 글로벌 참조가 fallback(단계 3)을 사용하게 되어 양 variant가 같은 파일에 쓸 수 있음 — 치명적 버그.

**주의 2**: `--assets` 기본값을 기존 `ETH,BTC,SOL,XRP`에서 **`BTC,ETH,SOL`**로 변경 (48h-ablation-plan.md §Variant 구성 우선 종목).

---

## smoke test 스크립트 (단계 10)

**파일**: `Projects/Trading Value/scripts/v2_ablation_smoke.py` (신규 작성)

```python
"""Smoke test for v2_ablation.py.

v2_ablation 모듈을 import하여 enable_rule2=False로 V2Engine을 생성한 후
predictor 주입이 올바른지 검증. 실제 네트워크 fetch는 수행하지 않음.

실행: python scripts/v2_ablation_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v2_ablation as v2a


def test_flag_propagation():
    """V2Engine(enable_rule2=False) → 모든 predictor.enable_rule2 == False."""
    np.random.seed(42)
    engine = v2a.V2Engine(assets=["BTC", "ETH", "SOL"], port=18902, enable_rule2=False)

    for asset in ["BTC", "ETH", "SOL"]:
        assert engine.predictors[asset].enable_rule2 is False, \
            f"{asset} predictor enable_rule2 expected False, got {engine.predictors[asset].enable_rule2}"

    assert engine.enable_rule2 is False
    print("[OK] V2Engine.enable_rule2=False propagates to all predictors")


def test_rule2_noop():
    """enable_rule2=False인 predictor의 update()가 _rebalance_memory를 호출하지 않음."""
    from v2_ablation import OnlinePredictor, N_FEATURES

    pred = OnlinePredictor(enable_rule2=False)

    # _rebalance_memory 호출 카운터 주입
    call_count = {"n": 0}
    original = pred._rebalance_memory

    def counting_wrapper():
        call_count["n"] += 1
        return original()

    pred._rebalance_memory = counting_wrapper

    # update 10회 호출
    x = np.random.randn(N_FEATURES)
    for _ in range(10):
        pred.update(x, 0.001)

    assert call_count["n"] == 0, \
        f"enable_rule2=False with 10 updates: _rebalance_memory called {call_count['n']} times (expected 0)"
    print("[OK] update() with enable_rule2=False does NOT call _rebalance_memory (0/10)")


def test_rule2_on_default():
    """enable_rule2=True(default)인 predictor의 update()가 _rebalance_memory를 호출함."""
    from v2_ablation import OnlinePredictor, N_FEATURES

    pred = OnlinePredictor()  # default enable_rule2=True
    assert pred.enable_rule2 is True

    call_count = {"n": 0}
    original = pred._rebalance_memory

    def counting_wrapper():
        call_count["n"] += 1
        return original()

    pred._rebalance_memory = counting_wrapper

    x = np.random.randn(N_FEATURES)
    for _ in range(10):
        pred.update(x, 0.001)

    assert call_count["n"] == 10, \
        f"enable_rule2=True with 10 updates: _rebalance_memory called {call_count['n']} times (expected 10)"
    print("[OK] update() with enable_rule2=True calls _rebalance_memory (10/10)")


def test_log_path_isolation():
    """모듈 상수 기본값이 v2.jsonl이 아닌 v2_ablation_*.jsonl 패턴인지 확인."""
    from v2_ablation import STATE_PATH, LOG_PATH
    assert "v2_ablation" in STATE_PATH.name, f"STATE_PATH leaked: {STATE_PATH}"
    assert "v2_ablation" in LOG_PATH.name, f"LOG_PATH leaked: {LOG_PATH}"
    assert STATE_PATH.name != "v2_state.npz"
    assert LOG_PATH.name != "v2.jsonl"
    print(f"[OK] STATE_PATH/LOG_PATH isolated: {STATE_PATH.name}, {LOG_PATH.name}")


if __name__ == "__main__":
    test_flag_propagation()
    test_rule2_noop()
    test_rule2_on_default()
    test_log_path_isolation()
    print("\n[PASS] All smoke tests passed.")
```

**실행 기준 통과**: 4개 테스트 모두 `[OK]` 출력 후 `[PASS]`.

---

## 산출물 / 검증

### 기계 검증 (구현 직후 Codex가 수행)

1. **파이썬 구문 검증**:
   ```bash
   cd "Projects/Trading Value"
   python -m py_compile scripts/v2_ablation.py
   python -m py_compile scripts/v2_ablation_smoke.py
   ```
   에러 0.

2. **import 검증** (모듈 로드 시 부작용 없음 확인):
   ```bash
   python -c "import sys; sys.path.insert(0, 'scripts'); import v2_ablation; print('ok')"
   ```
   출력: `ok`

3. **diff 검증** (Rule 2 gate + 상수 + 헤더 외 코드 변경 없음 확인):
   ```bash
   diff scripts/v2.py scripts/v2_ablation.py | head -200
   ```
   예상 diff 위치:
   - 파일 상단 헤더 docstring (신규)
   - `STATE_PATH`/`LOG_PATH`/`DASH_PORT` 값 변경
   - `OnlinePredictor.__init__` 시그니처 + `self.enable_rule2` 라인 1개
   - `update()` 내 `if self.enable_rule2:` 1줄
   - `V2Engine.__init__` 시그니처 + `self.enable_rule2` + predictor 생성 시 flag 전달
   - `V2Engine.run()` `HTTPServer` 바인딩 `"0.0.0.0"` → `"127.0.0.1"` 1줄 (접근 통제 섹션)
   - `main()` 전체 재작성 (argparse + global + seed + 로깅)

   **그 외 위치에 diff가 있으면 재작업**. 특히 `_rebalance_memory` 본체(v2.py:314-342), `predict()`, `calibration()`, `PositionManager`, `DashboardHandler`, `FeatureEngine`, HTML dashboard는 건드리지 말 것.

4. **smoke test 실행**:
   ```bash
   python scripts/v2_ablation_smoke.py
   ```
   4/4 `[OK]` + `[PASS]`.

5. **argparse help 검증**:
   ```bash
   python scripts/v2_ablation.py --help
   ```
   `--no-rule2`, `--port`, `--assets` 3개 플래그 표시 확인.

### 계약 검증 (Claude 리뷰가 수행, 단계 11)

1. **포트 점유 선제 확인** (기동 전):
   ```bash
   netstat -ano | grep -E "890[23]"
   ```
   8902/8903이 비어있어야 함. 점유 시 예비 포트 8912/8913로 실행 가능하도록 argparse에 이미 `--port` 노출됨.

2. **경로 격리 실행 검증** (기동 후 ~2분):
   ```bash
   python scripts/v2_ablation.py --port 8902 &                   # control
   python scripts/v2_ablation.py --no-rule2 --port 8903 &        # no_rule2
   sleep 120
   ls -la "Projects/Trading Value/data/v2_ablation_"*            # 4개 파일 예상
   ls -la "Projects/Trading Value/data/v2.jsonl"                 # 수정 시각이 ablation 기동 전이어야 함 (live 미오염)
   ```

3. **live port 오염 없음 확인**:
   ```bash
   netstat -ano | grep "8897"   # live v2 port만 잡혀있어야 함. 8902/8903 신규 바인딩.
   ```

4. **Dashboard 분리 확인**:
   - `http://localhost:8902` → control variant 대시보드
   - `http://localhost:8903` → no_rule2 variant 대시보드
   - 두 URL이 독립적으로 응답해야 함. 같은 데이터 보이면 경로 재바인딩 실패 (단계 7 `global` 누락).

### 로그 스키마 참고 (Codex 구현 범위 외, Claude 분석 단계에서 작성)

`48h-ablation-plan.md §데이터 로그 스키마`는 **Oracle 기준**(`predicted_edge`, `uncertainty` 등 Oracle-specific 필드 포함). 본 ablation은 V2 기반이므로 **v2 기존 `trade_log` 스키마**(v2.py:454 PositionManager.close_position 참조) 그대로 유지.

**v2 기존 trade_log 필드** (v2.py:454-467):
```
asset, dir, entry, exit, size, raw, cost, net, capital, entry_time, exit_time (등)
```

**분석 단계에서 derivable한 추가 필드**:
- `pnl_after_fee` = `net` (이미 기록됨)
- `hit` = `net > 0` (derivable)
- `pnl_gross` = `raw` (이미 기록됨)
- `fee` = `cost` (이미 기록됨)
- `variant` = 파일명에서 추출 (`v2_ablation_no_rule2.jsonl` → `no_rule2`)

→ **Codex는 기존 `_log_tick` / `close_position` 로깅 로직을 수정하지 말 것**. Oracle-specific 컨텍스트(predicted_edge, uncertainty, vol_regime, time_bucket)는 Phase 3 Oracle 구현 이후 수집.

---

## 에러 케이스

기동/실행 중 발생 가능한 장애와 대응. exit code는 Python 기본 규약(0=정상, 1=일반 에러, 2=argparse).

| # | 상황 | 감지 | exit | 대응 |
|---|------|------|:---:|------|
| E1 | 포트 8902/8903 점유 (`OSError: [Errno 98] Address already in use`) | `V2Engine.run()` `serve_forever()` 직전 | 1 | 기동 전 `netstat -ano \| grep 890[23]` 확인. 점유 시 `--port 8912`/`8913` 예비 포트 사용 |
| E2 | `--port` 값 숫자 아님 / 1024 미만 권한 불가 | argparse `type=int` / OS bind 실패 | 2 / 1 | argparse 에러 메시지 그대로. 1024 미만은 관리자 권한 필요 — 사용 금지 |
| E3 | `data/` 디렉토리 부재 (`FileNotFoundError` on first `_log_tick`) | 첫 tick log append 시 | 1 | 기동 전 `mkdir -p "Projects/Trading Value/data"`. `v2.py`도 동일 전제라 live에선 이미 존재 |
| E4 | `data/v2_ablation_*.jsonl` write permission denied | `_log_tick` | 1 | `chmod u+w` / Windows ACL 확인. live 파일 소유자와 동일해야 함 |
| E5 | ccxt bybit rate limit / 네트워크 timeout (`ccxt.RateLimitExceeded` / `RequestTimeout`) | `fetch_ohlcv` 루프 | (계속 실행, tick 스킵) | v2.py 기본 동작 그대로(예외 잡아 tick 스킵). 48h 연속 발생 시 심볼 리스트 축소 검토 |
| E6 | smoke test `test_rule2_on_default` 실패 (default `enable_rule2=True`인데 `_rebalance_memory` 호출 0) | smoke test | 1 | `OnlinePredictor.__init__`의 기본값이 `True`로 유지되었는지 재확인. 단계 4 누락 |
| E7 | commit SHA 불일치 (`v2.py`가 `417534b...` 이후로 수정됨) | 리뷰 단계 `git log scripts/v2.py` | — | v2_ablation.py는 **재포크 금지**. v2.py 신규 변경은 48h 이후 Phase 6 변경관리 대상 (spec 헤더 docstring SHA 불변 유지) |

**장애 시 공통 조치**: 양 variant 프로세스 `Ctrl+C` → `_save_state()` 자동 호출 → 산출물 보존. 원인 수정 후 `STATE_PATH` 읽어 재개(기존 weight 복원). 재개 시에도 `np.random.seed(42)` 동일.

---

## 변경 파일

| 파일 | 작업 | 유형 |
|------|------|:---:|
| `Projects/Trading Value/scripts/v2_ablation.py` | 신규 (v2.py 복사 + 10개 수정) | 추가 |
| `Projects/Trading Value/scripts/v2_ablation_smoke.py` | 신규 | 추가 |

### 변경 없음 (금지)
- `Projects/Trading Value/scripts/v2.py` — **live 운영. diff 0 필수**
- `Projects/Trading Value/data/v2.jsonl`, `data/v2_state.npz` — live 산출물
- `Projects/Trading Value/scripts/dl_features.py`, `v3.py`, `triangular_arbitrage.py`, 기타 — 본 ablation과 무관
- `config/`, `packages/launcher/` — 주제 외

---

## Claude 리뷰 포인트

Codex 구현 완료 후 Claude가 아래 항목 리뷰:

1. **diff 리뷰** (`diff scripts/v2.py scripts/v2_ablation.py`):
   - 예상 5개 영역(헤더/상수/OnlinePredictor init+update/V2Engine init/main)만 변경되었는가?
   - `_rebalance_memory` 본체, `predict()`, `calibration()`, `memory_entropy()`, `direction_accuracy()`, `PositionManager` 일체 변경 없는가?

2. **gate 정확성**:
   - `if self.enable_rule2: self._rebalance_memory()` 정확 1줄, 들여쓰기 일치.
   - `update()` 내 다른 메서드(`self.predictions.append` 등) 호출 순서 불변.

3. **global 선언**:
   - `main()` 내 `global STATE_PATH, LOG_PATH` 존재.
   - variant suffix 재할당이 `V2Engine(...).run()` 호출 **이전**에 완료.

4. **RNG 시점**:
   - `np.random.seed(42)` 호출이 `V2Engine` 생성 **이전**에 있는가?
   - `OnlinePredictor.__init__`의 `self.w = np.random.randn(n) * 0.0001`이 양 variant에서 동일 값인지(시드 직후 첫 호출) 확인. 양 variant에서 `V2Engine(...)` 이전 RNG 소비가 동일해야 strict one-variable 보장.

5. **smoke test 4종 통과** + argparse help 출력.

6. **경로 격리 확인** (기동 후 2분):
   - `data/v2_ablation_with_rule2.jsonl` + `data/v2_ablation_no_rule2.jsonl` 2개 독립 생성.
   - `data/v2.jsonl` 수정 시각이 ablation 기동 전.

7. **Dashboard 분리** (`http://localhost:8902` vs `:8903` 독립 응답).

리뷰 통과 시 사용자 승인 절차 → 48h paper trades 기동.

---

## Rollback

- 구현 단계 롤백: `scripts/v2_ablation.py` + `scripts/v2_ablation_smoke.py` 2개 파일 삭제.
- 실행 단계 롤백: 두 프로세스 `Ctrl+C` → `_save_state()` 자동 호출. 산출물은 `data/v2_ablation_*.{jsonl,npz}`에 남음 (분석 재시도 용도).
- 데이터 영향 없음: live `v2.jsonl`/`v2_state.npz`/`v3_*.jsonl` 무변경.

---

## 후속 (본 지시서 범위 외, 참고용)

- **Day 1 말**: Claude 리뷰 완료 → User 승인 → 두 variant 기동
- **Day 1~3**: 48h 실행. Claude 24h 중간 점검 (샘플 수, 크래시 여부)
- **Day 3~4**: 분석 스크립트 작성 (`/sub`) → Walk-forward split + Wilson CI + calibration
- **Day 4**: PASS/FAIL/INCONCLUSIVE 판정 회의 → `ablation-verdict.md` 작성
- **Day 5**: 분기 — Phase 3 진입 / Charter Tier 2 변경 / 48h 연장
- **2026-04-23 이후**: `scripts/archive/v2_ablation_2026-04-21.py`로 이관 + Component Map 각주 업데이트

---

## GPT/Codex 전달 프롬프트 템플릿

```
당신은 Trading Value 프로젝트의 시니어 Python 개발자입니다.

## 프로젝트 경로
C:\Users\haj\projects\subagent-orchestrator\Projects\Trading Value\

## 기술 스택
Python 3.11+ / ccxt / numpy / pandas / scipy / http.server (dashboard)
운영 엔진: scripts/v2.py (port 8897), scripts/v3.py (별도 포트), scripts/triangular_arbitrage.py

## 작업 지시서
C:\Users\haj\projects\subagent-orchestrator\subagent-runs\spec\oracle-v2-ablation-2026-04-21\spec.md

## 규칙 (절대 준수)
1. 지시서의 [필수] 항목 100% 구현. [금지] 항목 절대 건드리지 말 것.
2. 지시서에 포함된 코드 블록은 **직접 복사**해서 반영. "해석"하지 말 것.
3. `scripts/v2.py`는 **읽기 전용**. 어떤 이유로도 수정 금지 (live 8897 운영 중).
4. commit SHA `417534bdae39c0c09f93b8906d583893ddb98cc6`의 v2.py 기준으로 복사. 이후 v2.py가 수정되어도 재포크 금지.
5. 검증 순서:
   a. python -m py_compile scripts/v2_ablation.py scripts/v2_ablation_smoke.py
   b. python -c "import sys; sys.path.insert(0, 'Projects/Trading Value/scripts'); import v2_ablation"
   c. diff "Projects/Trading Value/scripts/v2.py" "Projects/Trading Value/scripts/v2_ablation.py" | head -200
      → 예상 5개 영역만 변경되었는지 확인
   d. python "Projects/Trading Value/scripts/v2_ablation_smoke.py" → 4/4 PASS
   e. python "Projects/Trading Value/scripts/v2_ablation.py" --help → 3 flags 표시
6. 검증 실패 시 재작업, 통과할 때까지 반복.
7. 보고 내용:
   - 변경 파일 2개 경로
   - diff 출력 요약 (어떤 섹션이 변경되었는가)
   - smoke test 4종 결과
   - argparse help 출력
   - 예상 외 diff 발생 시 원인 + 대응

금지 사항 재확인:
- v2.py 수정 금지
- v2.jsonl / v2_state.npz 쓰기 금지
- 8897 포트 바인딩 금지
- Live trading 활성화 금지
- v2.py import 후 monkey-patch 방식 금지 (포크만 허용)
```

---

## 자체 검증 체크리스트 결과

### 공통
- [x] 메타(긴급도/선행/유형/migration/의존) 포함
- [x] 배경 3문단 설명
- [x] [필수/선택/금지] 태그 범위 분류
- [x] 변경 파일 표 + "변경 없음" 명시
- [x] 기계 검증 5종 (py_compile / import / diff / smoke / argparse help)
- [x] Rollback 섹션

### 기능 작업
- [x] CLI 인터페이스 명세 (argparse 3 flags + 실행 예시)
- [x] 에러 방지 정책 명시 (live 포트/파일 금지, global 누락 경고)
- [x] 비즈니스 로직 의사코드 (main() 재작성 전체)
- [x] smoke test 시나리오 4종
- [x] diff 예상 범위 명시 (6영역 — 헤더/상수/OnlinePredictor/V2Engine init/HTTPServer 바인딩/main)
- [x] 에러 케이스 테이블 (7행, exit code + 감지 시점 + 대응)

### 인프라 작업
- [x] 접근 통제 섹션 (loopback 바인딩 정책 + Before/After + curl 검증)
- [x] 포트/파일 격리 전략 (variant suffix + netstat 선제 점검)

### 금기 패턴 검사
- [x] 모호 표현 없음 ("적절히", "깔끔하게" 등 미사용)
- [x] "이식하세요" 단독 사용 없음 (Before/After 코드 블록 동반)
- [x] UI/DB 혼합 없음 (기능+인프라 경량 혼합)
