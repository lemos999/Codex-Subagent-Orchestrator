# Φ-4 Nation Charter — Decision Cards

**일자**: 2026-05-04
**Phase**: design Phase 3 (Decision Cards)
**Codex 검토**: APPROVE_WITH_NOTES (2026-05-04, [response](PHASE-17-NATION-CHARTER-REVIEW-RESPONSE-CODEX.md))
**Finding 반영**: #1 (review-request 경로 정정), #2 B-2 (raw JSON canonical input), #3 (SIS distribution extractor + 임계 freeze 금지)

---

## 1차 — 비코어 [확정] (코어 게이트 §3.3.2 불요)

### DC-1: SIS — Sovereignty Intensity Sensor

| 항목 | 내용 |
|---|---|
| **OQ** | 1 (주권 강도 정의) |
| **결정** | 1차 spec = **windowed distribution table extractor** (read-only telemetry). mechanism 무수정. **임계 freeze 절대 금지** (Finding #3 반영, Codex Optional #1) |
| **1차 산출** | `dom_share`, `member_share`, `conflict_pair`, `cross_faction_lord_count`의 windowed 분포 테이블 (per seed × per territory × per window) |
| **sovereignty_score** | **후보 진단 필드만**. P50/P67/P75 분위수 후보 도출까지만 허용. 임계 freeze는 §3.7 5단(3엔진 cross-check) 통과 후. |
| **Canonical Input** | V3 raw 데이터 (`Projects/personas/loom/data/phase17_probe_phi3-case-c-diagnosis-v3/seed-{7,13,42}/case_c_events.json` + JSON metrics). **mojibake `summary.md` 사용 금지** (Finding #2 B-2) |
| **§3.7 사슬** | 1단(windowed 분포) → 2단(V3 seed별 분위수) → 3단(cross_faction_lord 잠재력 결합점) → 4단(P50/P67/P75 후보) → 5단(3엔진 cross-check, Gemini=`gemini-3.1-pro`) → 6단(closure 보고서) |
| **대안 기각** | (a) 단일 수식 `0.6·dom_share + 0.4·member_share` — top-down magic threshold (axis A 동형) (b) 새 trigger mechanism — axis C 거부 |
| **검증** | (i) 3 seed windowed 분포 일관성 (ii) raw JSON 직접 파싱(mojibake 우회) (iii) §3.7 5단 cross-check |
| **주의** | review-request §3.2 ④ Charter Differentiation에 인용된 `dom_share window=720 ≥ 0.55`는 **Phase 17 entry trigger 신호일 뿐**. SIS sovereignty 임계와 동일시 금지 (Codex Finding #3 핵심). **DC-1 1차 추출 결과 (2026-05-04, V3 raw 3 seed × 28 windows, [data/phase17_phi4_sis/aggregate/distribution.json](data/phase17_phi4_sis/aggregate/distribution.json))**: P50/P67/P75 일관성 12셀 중 2셀만 ±10% 통과 (`dom_share P75 = 1.0` 동률 / `cross_faction_lord_count P67 = 1.0` 동률). aggregate `dom_share` P50=0.78 / P67=1.0 / P75=1.0이지만 seed별 P50은 0.90 / 0.74 / 0.68로 분산 — **단일 분위수 임계 freeze 절대 금지의 raw 데이터 근거**. §3.7 5단(3엔진 cross-check) 통과 전까지 `sovereignty_score`는 후보 진단 필드로만 유지. |
| **태그** | **[확정]** |

### DC-2: CPCM — Charter Primitives Convergence Meter

| 항목 | 내용 |
|---|---|
| **OQ** | 4 (charter primitives 수렴 측정) |
| **결정** | persona charter primitive overlap을 PersonaBrain **read-only** API로 측정. **primitive 주입·수렴 금지** (Codex Optional #2). brain·SNN API 무변경 |
| **Canonical Input** | V3 raw — PersonaBrain charter primitive vector + raw event_log. **mojibake summary 사용 금지** (Finding #2 B-2) |
| **§3.7 사슬** | 1단(pair-wise overlap, cosine 또는 Jaccard) → 2단(V3 분포) → 3단(SIS 상관) → 4단(P50/P67/P75 후보) → 5단(cross-check) → 6단(closure) |
| **대안 기각** | (a) charter 강제 정렬 mechanism — top-down (b) persona-level voting trigger — mechanism 추가 거부 |
| **검증** | V3 데이터 vector 추출 → 분포 분석 → SIS sovereignty와 결합 검토 → 5단 cross-check |
| **태그** | **[확정]** |

### DC-3: P5R — Φ-5 Read-only API Surface (1차안)

| 항목 | 내용 |
|---|---|
| **OQ** | 6 (Φ-5 인계) |
| **결정** | read-only 5 슬롯 인터페이스 **shape만** [확정]. body semantics는 SIS/CPCM/NDP/LRT/FMR 5 컴포넌트 안정화 후 (Codex Optional #3) |
| **5 슬롯 (shape only)** | `nation.sovereignty` (← SIS) · `nation.charter_overlap` (← CPCM) · `nation.dissolution_history` (← NDP) · `nation.lord_replacement_history` (← LRT) · `nation.federation_state` (← FMR) |
| **방향성** | Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1 (단방향, 역방향 mutate 금지) |
| **대안 기각/보류** | (a) read-write API — 안전 위반 (기각) (b) event-stream subscription — 보류 (1차 read-only 충분) |
| **선결조건** | SIS·CPCM·NDP·LRT·FMR 5개 [확정] 후 body 정의 |
| **태그** | shape **[확정]** / body **[보류]** |

---

## 2차 — 코어 (사용자 사전 승인 + 구현 전 cross-check 필수)

> Codex Optional #4 권고: FMR/NDP/LRT는 구현 전 `/spec-review` 또는 3엔진 cross-check 필수 통과.

### 사전 승인 요청 #1: FMR — Federation/Merge Resolver

```
- 코어 영역: mechanism logic
- 변경 범위: territory pair (sovereignty + charter_overlap + conflict_pair) →
  branch decision (merge / federation / none) 산출 함수 신설
- 정당화: OQ 2 — 측정만으로 환원 불가, decision 함수 자체가 mechanism.
  axis C 가드레일 우선 통과 후 신설.
- 대안 검토 (비코어 우회): SIS·CPCM 측정만으로 분기 추론 →
  기각 사유: branch 결정은 결정 시점·결정 주체가 필요한 mechanism, 측정만으로 환원 불가.
- 추가 요건 (Codex Optional #4): 구현 전 /spec-review 또는 3엔진 cross-check 필수
- 사용자 사전 승인 일자: 2026-05-04
- 사용자 결정: [ 승인 / 조건부 승인 / 거부 ] — 대기
```

### 사전 승인 요청 #2: NDP — Nation Dissolution Path

```
- 코어 영역: mechanism logic + acceptance
- 변경 범위: grievance accumulation + sovereignty 감소 추세 →
  dissolution event + Φ-3 재진입 신호 (Φ-3 mechanism 자체는 무수정)
- 정당화: OQ 3 — Φ-3·Φ-4 경계 mechanism. acceptance 정의(언제 Φ-3로 돌아가는가) 필요.
- 대안 검토 (비코어 우회): SIS sovereignty 감소만으로 dissolution 추론 →
  기각 사유: Φ-3 재진입 신호는 acceptance 정의 필요, acceptance는 코어.
- 추가 요건 (Codex Optional #4): 구현 전 /spec-review 또는 3엔진 cross-check 필수
- 사용자 사전 승인 일자: 2026-05-04
- 사용자 결정: [ 승인 / 조건부 승인 / 거부 ] — 대기
```

### 사전 승인 요청 #3: LRT — Lord Replacement Trigger

```
- 코어 영역: mechanism logic
- 변경 범위: Φ-3 grievance accumulation + SIS sovereignty 결합 →
  lord_replacement event 발생 (state 변경)
- 정당화: OQ 5 — V3 데이터 사례 측정 우선 → 자연 빈도 분석 후
  trigger 임계 분위수 도출. 영주 교체는 자연 발생 mechanism.
- 대안 검토 (비코어 우회): grievance + sovereignty 측정만 노출 →
  기각 사유: replacement event 자체가 state 변경 mechanism, 측정만으로 환원 불가.
- 추가 요건 (Codex Optional #4): 구현 전 /spec-review 또는 3엔진 cross-check 필수
- 사용자 사전 승인 일자: 2026-05-04
- 사용자 결정: [ 승인 / 조건부 승인 / 거부 ] — 대기
```

---

## Finding 처리 요약 (Codex 회신 반영)

| Finding | Severity | 처리 |
|---|---|---|
| **#1** axis A spec 경로 오류 | MINOR | review-request §4 정정 (3 파일 분산: PHASE-14B-AFFILIATION-RESONANCE-SPEC.md / PHASE-17-CASE-C-COLLAPSE-DIAGNOSIS-SPEC.md / subagent-runs/discuss/phase14b-a-cross-check-2026-04-28-quick/) |
| **#2** V3 SUMMARY mojibake | MINOR | **B-2 채택** — DC-1·DC-2 Canonical Input을 raw JSON / case_c_events.json으로 명시. mojibake hotfix는 권장 순서 2번 (별도 작업)으로 분리 |
| **#3** SIS 임계 freeze 금지 | MINOR | DC-1 SIS 본문 = "windowed distribution table extractor" only. sovereignty_score는 후보 진단 필드, P50/P67/P75 재유도 + 3엔진 cross-check 통과 전 임계 freeze 금지 |

---

## 다음 단계

### Phase 3 1차 (비코어, 즉시 진행 가능)

1. **SIS spec** — `/spec`로 windowed distribution table extractor 지시서 작성 → Codex 위임 (자율성 존중, 코어 게이트 우회)
2. **CPCM spec** — `/spec`로 read-only PersonaBrain consumer 지시서 작성 → Codex 위임
3. **P5R spec** — shape interface freeze (TypeScript 또는 Python protocol). body는 보류

### Phase 3 2차 (코어, 사용자 사전 승인 후)

위 사전 승인 요청 #1~#3 사용자 결정 받은 후:
- 승인되면 → `/spec-review` 또는 3엔진 cross-check 통과 후 spec 작성
- 거부되면 → 비코어 우회 방안 재검토

### Phase 4 Verify (모든 6 Decision Card [확정] 후)

- 3엔진 cross-check (Claude + Codex + Gemini, Gemini=`gemini-3.1-pro` 고정)
- §3.7 5단 통과

### Phase 5 Package

- Φ-4 Nation Charter 본문 ([확정]/[보류]/[미결] 태그)
- Decision Card 6 전체
- Φ-5 인계 read-only API spec 1차안

---

**작성자**: Claude (loom 설계 담당, 2026-05-04)
