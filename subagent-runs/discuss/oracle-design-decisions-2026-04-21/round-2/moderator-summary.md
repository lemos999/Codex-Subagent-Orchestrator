# Round 2 — Moderator 요약 및 수렴 판정

**Date**: 2026-04-21
**Scope**: Topic 2 (Ablation 파일 구조) 집중. Topic 1(BollRev 제외)은 Round 1에서 AGREE 확정.

---

## 응답 요약 표

| 엔진 | Round 1 | Round 2 | Shift |
|------|---------|---------|-------|
| Claude opus | A | **A** | 유지 (논거 강화) |
| Codex gpt-5.4 | D | **D** | 유지 (D-1 Python 경로 구체 검증) |
| Gemini 2.5-pro | A | **A** (Hybrid 형태) | 유지 |

**투표**: **A 2 / D 1** — Round 1과 동일.

---

## Q1 (drift 리스크) — 합의점 식별

3엔진 공통:
- commit hash 주석만으로는 "방지" 아닌 "사후 추적". 48h 단기 맥락에선 충분.
- 장기 재실행까지 고려하면 A가 D보다 drift 노출 큼 (**D에 유리**).

Claude opus 추가 제안: 헤더 주석 + `.gitattributes linguist-generated` + 48h 만료 체크리스트 + `diff` sanity check 스크립트.

---

## Q2 (D-1 Python 실행 경로) — 기술적 합의 + 가치 판단 분열 ★핵심★

### 3엔진 공통 합의 (기술적)
D-1은 Python 문법·실행 경로상 **작동한다**:
- `V2Engine.__init__`에서 `self.predictors`는 생성만 되고 즉시 사용 안 됨 (v2.py:605-625).
- 첫 실제 사용은 `tick()` (v2.py:714-723)이므로 subclass 재할당이 **시간상 앞섬**.
- `_load_state`/`_save_state`가 요구하는 인터페이스(`pred.w`, `pred.b`, `pred.norm.*`)는 subclass 상속으로 충족.
- `_rebalance_memory` no-op 오버라이드 시 다른 메서드(`predict`/`update` 나머지/`memory_entropy`/`feature_importance`) 동작 무결.

### 분열점: 모듈-레벨 글로벌 재바인딩 성격 판단

v2.py:46-48 `STATE_PATH`/`LOG_PATH`/`DASH_PORT`는 **모듈 상수**. `_log_tick`/`_save_state`/`_load_state` 내부에서 `self.X`가 아닌 **전역 이름으로 참조**된다(v2.py:790, 852, 858, 861).

Wrapper에서 분리 방법 3가지:
- **(a)** `import v2; v2.LOG_PATH = ...` 런타임 재바인딩
- **(b)** `_log_tick`/`_save_state`/`_load_state` 3개 메서드 모두 subclass 오버라이드 (~60 LOC 복붙)
- **(c)** v2.py에 경로 상수를 `self.X`로 승격 + `__init__` 파라미터화 (v2.py 수정 필요 → D-2)

**Codex**: (a)를 "standard module state override"로 분류. import 직후 재바인딩하면 dashboard thread 시작 전이므로 race 없음. D는 여전히 "얇은 harness".

**Gemini**: (a)를 "Monkey Patching"으로 분류. 추적 어렵고 리스크 큼. Charter 조항 I(Live 격리) 위반 위험.

**Claude opus**: (a)는 "런타임 전역 오염 — 무수정 원칙의 스피릿 위반". (b)는 60 LOC 복붙 → D의 "얇은 wrapper" 본질 붕괴. (c)는 v2.py 수정 필요 → D의 유일 장점 소멸. **정량 비교**: A(~905 LOC 포크 + 5 LOC flag) vs D-1-(b)(~80 LOC subclass + 메서드 복붙). Codex의 D=6-10h 수치는 **모듈-레벨 글로벌 분리 공수를 누락**한 낙관.

### 쟁점 압축
- **기술적 가능성**: 합의 ✓ (D-1 작동함)
- **"v2.py 무수정" 주장의 강도**: 재바인딩이 허용 가능한 "standard override"인가(Codex), 아니면 "monkey patch/스피릿 위반"(Claude/Gemini)인가
- **실질 공수**: Codex 6-10h vs Claude opus 14 LOC A / 60 LOC D-1(b)

---

## Q3 (A 구체 경로) — 3엔진 공통 확인

Codex가 Round 1의 A 공수 추정(8-12h)을 **재계산 후 인정**: 실제로는 단순. 
- 파일 복사 + 상수 3개 교체 + `ENABLE_RULE2 = False` + `if ENABLE_RULE2: self._rebalance_memory()` 1줄 gate
- 추가로 Claude opus: `OnlinePredictor.__init__`에 `enable_rule2` 파라미터 추가 시 더 깔끔 (동일 파일에서 양 variant 구동 가능)
- **총 ~14 LOC 수정, 2-3h 구현**

→ **A의 실질 공수가 Round 1 추정보다 낮음**이 드러남. 이건 A에 유리한 새 증거.

---

## Q4 (하이브리드) — 3엔진 분열

- **Gemini**: 최적의 낙착점 (A 구현 + Charter 명칭 충족)
- **Codex**: 진짜 절충 아님 (naming optics뿐, D 장점 전부 잃음). Charter 명칭 이슈면 **D 구현**에 `oracle_rule2_ablation.py` 파일명이 나음
- **Claude opus**: 기각 (양쪽 단점만 합침, Phase 3 Oracle 파일과 네이밍 충돌 유발). 대안: A + Component Map 각주에 "Charter 문언 예외" 투명 기록

### 공통 인정 쟁점
파일명 선택은 A/D 본질 결정 후에 부수적으로 다뤄질 문제. 본질은 "포크 vs subclass".

---

## 수렴 판정

| 구분 | 판정 |
|------|------|
| Topic 1 BollRev | **AGREE (제외)** — Round 1 확정 |
| Topic 2 Ablation | **PARTIAL (A 2 / D 1)** — 투표 동일, 쟁점 극도로 좁혀짐 |

### Round 2 진전 사항
1. **D-1 기술 가능성** 3엔진 합의 (Round 1 쟁점 Q2 해결)
2. **A 공수 하향** (Round 1 8-12h → Round 2 2-3h, Codex도 인정)
3. **핵심 분열점 식별**: 모듈-레벨 글로벌 재바인딩의 성격 판단 — **기술적이 아닌 아키텍처 스타일 감각 차이**

### Round 3 진행 판단: **불필요**
- 남은 쟁점은 "standard override vs monkey patch" 가치 판단 — 추가 라운드로 해소 불가
- 다수안(A 2표) + Codex도 "A가 싸고 현실적"임을 인정 + Q1(drift)에서 D 유리점은 48h 맥락상 경미함
- **Breakthrough Protocol**: 같은 차원 반복 → 차원 전환 또는 파셜 합의 고정 필요

---

## 합의안 (Moderator 제안)

### Topic 1 — BollRev 편입 여부
**결정**: **제외** (3/3 AGREE)

- Oracle 초기 variants: control / aggressive / conservative 3종 확정
- BollRev는 V3 확장 variant 후보 또는 Phase 6 별도 엔진 승격 경로
- feature reuse(`bb_pos`, `bb_width`, `dist_to_mid`, `rsi14`)는 Phase 3 전 Oracle 입력 ablation 1회 실행 후 uplift 검증

### Topic 2 — Ablation 파일 구조
**결정**: **A** (`scripts/v2_ablation.py` — V2 포크 + `--no-rule2` flag)

**채택 근거**:
1. **다수안** (Claude opus, Gemini)
2. **기술적 명료성**: 모듈-레벨 글로벌을 재바인딩 없이 분리 가능 (포크 파일에서 상수만 교체)
3. **실질 공수 최소**: 14 LOC + 2-3h (Round 2에서 Codex도 인정)
4. **drift 통제 가능**: commit hash 헤더 + 48h 만료 체크리스트 + diff sanity check

**구현 안전장치** (Claude opus Q3 제안 채택):
- 파일 헤더: `# Forked from v2.py @ <SHA> on 2026-04-21. DO NOT sync.`
- 상수 분리: `STATE_PATH = DATA_DIR / "v2_ablation_state.npz"`, `LOG_PATH = DATA_DIR / "v2_ablation.jsonl"`, `DASH_PORT = 8902`
- `OnlinePredictor.__init__`에 `enable_rule2: bool = True` 파라미터 추가 → argparse `--no-rule2`에서 False 주입
- 두 variant를 포트 8902(control) / 8903(no_rule2)로 병렬 구동
- 48h 후 `scripts/archive/v2_ablation_2026-04-21.py`로 이관 + Component Map 각주 추가

**Codex의 D 주장에서 수용할 요소**:
- 파일명을 `v2_ablation.py`로 유지 (Charter 문언 충족보다 내용 일치 우선). Component Map 각주에 "Charter 조항 I의 입법 취지(live 환경 보호) 충족을 위한 예외적 V2 포크. Phase 3 Oracle 파일과 무관" 투명 기록.
- RNG 상태 맞춤: control/no_rule2 양 variant 모두 동일 harness 사용하여 RNG 소비 동등화 (strict one-variable 보장).

### 기각 사유
- **D**: 기술 가능하나 모듈-레벨 글로벌 재바인딩이 "v2.py 무수정 + 얇은 wrapper" 본질 주장을 약화. 공수 이득도 재계산 결과 소멸.
- **Hybrid (A 포크 + oracle_* 파일명)**: 양쪽 단점만 결합. Phase 3 실제 Oracle 파일 신설 시 네이밍 충돌.

---

## Evidence
- Round 1: `round-1/claude_opus.md`, `codex.md`, `gemini.md`, `moderator-summary.md`
- Round 2: `round-2/claude_opus.md`, `codex.md`, `gemini.md`, `_prompt.md`
- 코드 검증 참조: `Projects/Trading Value/scripts/v2.py` (commit hash 미기록 — Phase 구현 시 고정 필수)
