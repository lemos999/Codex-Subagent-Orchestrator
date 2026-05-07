# Phase 17 Φ-1 Land rev.next STUB — Layer 1 Substrate Enrichment

> **rev**: STUB v0 (2026-05-07)
> **trigger**: Phase 17 Φ-4 Nation Charter Phase 3 closure 후 진로 B (paper 권고) 채택
> **선행 자료**: `Projects/personas/docs/paper_loom 자율 사회 시뮬레이션의 자연 창발 국가를 위한 구조 검토 논문식 정리.md` (2026-05-07 첨부)
> **선행 closure**: `subagent-runs/discuss/phase17-nation-phase3-verify-2026-05-07-quick/conclusion/conclusion.md` rev.3 §7-4 진로 B
> **선행 V-3 evidence**: `subagent-runs/discuss/phase17-nation-phase3-verify-2026-05-07-quick/conclusion/v3-tier1-result.md`
> **Encoding**: utf-8

---

## 0. 사용자 메모리 3계층 목적 (`feedback_loom_goal_first.md` 정합)

### 0.1 궁극 목적 (loom 프로젝트)
**자율 사회 시뮬 + SNN 창발 + PersonaBrain 논문 출판** — 페르소나가 자연·기후·영토·경제·갈등 속에서 살아가며 그 결과로 "국가"가 관측되는 자율 시뮬.

### 0.2 Phase 목적 (Phase 17 Φ-1 rev.next)
**Layer 1 Substrate 풍부함 enrichment** — 기후가 땅에 누적되고, 땅이 페르소나의 삶을 바꾸는 폐쇄 루프 형성. paper §4 "loom에 지금 필요한 것은 국가를 추가하는 것이 아니라 땅을 살아 있게 만드는 것" 정합.

### 0.3 본 STUB 고유 역할
**Φ-1 Land rev.next 진입 게이트 정의** — paper §7 7단계 작업 순서를 §3.3.2 코어 게이트 분류 + §3.7 6단 사슬 정합으로 매핑. probe (telemetry 무게이트) vs mechanism (사용자 사전 승인 게이트) 분리. 첫 spec 작성 가능 작업 우선순위 결정.

---

## 1. 배경 — V-3 4 sub-test FAIL의 직접 외부 검증

### 1.1 V-3 4 FAIL 신호
Phase 17 Φ-4 Nation Charter Phase 3 closure 직전 V-3 Tier 1 회귀 실측 (2026-05-07):

| sub-test | seed | 원인 | paper 정합 |
|---|---|---|---|
| `test_phi3_grievance_pairs_resonate` | 13 | closure-v2 §2.1 "1/3 PASS" stochastic 변동 | §4 "환경 풍부함 부족 → 자연 발생 임계 미달" |
| `test_grievance_propagate_natural_emergence` | 13 | propagation 자연 발생 임계 노이즈 | 동상 |
| `test_phi3_branch_lineage_chain` | 3 seed 합계 0 | branch_factions_total = 0 (closure-v2 §2.2 명시 부재) | §5.5 "같은 땅을 먹고, 고치고, 버티는 경험" 부재 |
| `test_respawn_seed_group_emitted` | 3 seed 합계 0 | respawn_seed_group 자연 부재 | §4 "ecological migration 약함" |

### 1.2 paper 진단의 직접 외부 검증
- 회귀 0% 확정 (mechanism 영역 git diff empty since 9175397)
- 자연 변동 + closure-v2 잔재 + paper 진단 정합의 **3중 일치**
- paper §1 "올바른 접근: 자연, 기후, 영토, 식량, 이주, 관계, 갈등의 폐쇄 루프를 강화" 정합

---

## 2. paper 9 검증 원칙 (§8) — 본 rev.next 적용 의무

각 단계는 다음 9 원칙을 만족해야 함:

1. **raw-first telemetry** — 첫 단계는 측정만, 임계 도출은 분포 분석 후
2. **deterministic seed replay** — seed 7/13/42 결정성 보존
3. **no-core-diff gate** — probe 단계는 mechanism 무수정
4. **no false PASS** — 거짓 PASS 절대 금지 (사용자 명시)
5. **threshold freeze 금지** — magic threshold 사전 박기 금지 (§1.0 caveat 정합)
6. **current-window vs cumulative 구분** — 시점별 측정값과 누적 측정값 분리
7. **long-run seed 7/13/42 검증** — Tier 1 회귀 7종 보존
8. **acceptance 변경 금지** — 기존 acceptance 4종 + 무파괴 9 + 안전 전제 5종 + BOOST=0.20
9. **SNN/brain 변경 시 별도 core 승인** — §3.3.2 코어 게이트 의무

---

## 3. paper 7 작업 순서 (§7) — §3.3.2 게이트 분류

### 3.1 게이트 분류 표

| # | paper 작업 | 영역 | §3.3.2 게이트 | 시작 가능 시점 |
|---|---|---|:---:|---|
| 1 | **Land-Climate Closure Probe** | telemetry (raw 측정) | **무게이트** (no-core-diff) | **즉시** |
| 2 | **Resource/Fertility Dynamics** | telemetry + 결정성 검증 | **무게이트** (probe 단계) | #1 결과 후 |
| 3 | **Land-backed Agriculture** | mechanism (farm cell 또는 territory farm asset) | **사용자 사전 승인** | #2 분포 분석 후 |
| 4 | **Ecological Migration Probe** | telemetry (drought/famine/degraded land → migration pressure 측정) | **무게이트** | #1·#2 누적 후 |
| 5 | **SocialHomeostasisField Probe** | telemetry (read-only field) | **무게이트 (probe 단계)** | #1~#4 입력 확보 후 |
| 6 | **Nation Candidate Snapshot** | telemetry (state가 아닌 후보 관측) | **무게이트 (snapshot 단계)** | #5 출력 입력 |
| 7 | **FMR/NDP/LRT 별도 spec** | mechanism (각 mechanism 독립 probe → spec) | **사용자 사전 승인** (각 component 별) | 충분한 자연 측정 누적 후 |

### 3.2 첫 spec 작성 가능 작업
**§7-1 Land-Climate Closure Probe** — paper §5.2 Layer 1 Substrate 추가 후보 측정의 1단계.

> **본 STUB rev.next 1단계 작업 후보**: §7-1 Probe Spec.

---

## 4. paper §5.2 Layer 1 Substrate 추가 후보 (참고용)

paper §5.2가 제안하는 LandCell 추가 필드 (mechanism 단계 — §3.3.2 사용자 사전 승인 의무):

| 필드 | 의미 | 첫 도입 단계 |
|---|---|---|
| `soil_moisture` | 토양 수분 | §7-2 Resource/Fertility Dynamics |
| `fertility` | 비옥도 | §7-2 |
| `rainfall_30d` | 30일 누적 강수량 | §7-1 Probe (probe 단계는 LandCell 외부에서 측정) |
| `temperature_30d` | 30일 누적 기온 | §7-1 Probe |
| `drought_days` | 가뭄 누적 일수 | §7-1 Probe |
| `depletion` | 자원 고갈 정도 | §7-2 |
| `recovery_rate` | 회복 속도 | §7-2 |
| `hazard_damage` | 재난 피해 누적 | §7-1 Probe (raw 측정) → §7-2 (mechanism) |

**§7-1 Probe 단계 원칙** (paper §5.2 정합):
- LandCell 본문 무수정 (no-core-diff)
- 측정값은 **외부 telemetry 객체**에 누적 (예: `physis/land_climate_telemetry.py` 신규 모듈)
- 분포 분석 후 §7-2/§7-3 mechanism spec에서 LandCell 필드 신설 결정

---

## 5. paper §6 SocialHomeostasisField (참고 — §7-5 후속)

§7-5 작업 시점에 활용. 본 STUB rev.next 1단계 작업과 무관 (참고용 보존).

### 5.1 입력 (paper §6)
food pressure / chronic stress / grievance / trust density / climate hazard / public works response lag / SNN tension/growth / faction contact / migration pressure

### 5.2 출력 (paper §6)
territory field intensity / faction field intensity / inter-territory coupling / recovery lag / resonance decay / crisis memory

### 5.3 금지 (paper §6 — §3.3.2 정합)
- 직접 행동 override
- faction 가입 boost
- uprising 강제
- sovereignty trigger
- acceptance 통과용 floor/sticky 보정

### 5.4 가능한 후속 연결 (먼 미래 — §3.3.2 사용자 사전 승인 의무)
public works priority / recovery work priority / food reserve allocation / SNN `tone` 약한 조절 / reward sensitivity 약한 조절 / sleep/recovery 효과 조절

---

## 6. Open Questions — Φ-1 Land rev.next 진입 시 해소

### OQ 1 — Probe 누적 시간 단위
- 30일 (rainfall_30d / temperature_30d) vs 다른 window
- paper §5.2가 30일 명시. 본 prob는 30일 기본 + 추가 window 분포 분석 후 결정

### OQ 2 — Probe telemetry 객체 위치
- `physis/land_climate_telemetry.py` 신규 모듈 vs `core/multi_tick_engine.py` 통합
- 권고: 신규 모듈 (no-core-diff 정합)

### OQ 3 — LandCell 본문 무수정 보존 검증
- §7-1 Probe 단계에서 LandCell 본문 변경 0건 검증 명령 (git diff)
- 회귀 7종 보존 (Tier 1) 검증

### OQ 4 — 분포 분석 후 §7-2 진입 결정 기준
- §7-1 30일 probe 데이터 누적 후 어느 분위수에서 §7-2 mechanism 진입 결정
- paper §8 "current-window vs cumulative 구분" 명시 정합

### OQ 5 — Nation Candidate Snapshot envelope (§7-6) 정합
- DC-3 P5R rev.2 `NationSovereignty` / `NationCharterOverlap` 와 paper §8 envelope (`current_*` / `cumulative_*` / `provenance` / `window` / `seed`) 통합 시점
- DC-3 rev.3 갱신 vs P5R v0 → v1 surface 확장 분리

### OQ 6 — Tier 2 신규 4종 author와 병행 가능성
- Phase 5 Package Tier 2 4종 author는 P5R v0 외부 검증 — Φ-1 Land rev.next §7-1 Probe와 독립 가능
- 사용자 자원 분산 위험 vs 진로 통합 가치 — 사용자 게이트

### OQ 1~6 결정 (2026-05-07)

**OQ 1** — 30일 기본 + 추가 window는 raw 분포 분석 후 결정
- 근거: paper §5.2 (rainfall_30d / temperature_30d) + DC-2 CPCM 30일 window 정합. spec body freeze 금지 (§1.0 caveat)

**OQ 2** — 신규 모듈 `physis/land_climate_telemetry.py`
- 근거: STUB §132 권고 + no-core-diff 정합. `core/multi_tick_engine.py` 통합 시 회귀 7종 + 무파괴 9 위반 위험

**OQ 3** — [physis/world.py:23](Projects/personas/loom/physis/world.py#L23) 본문 무수정 검증 (LandCell 실재 정의 위치)
- §7-1 spec body에 3중 검증 명시:
  - (a) `git diff Projects/personas/loom/physis/world.py` = 0 lines
  - (b) Tier 1 회귀 7종 동일 결과 (89 passed 유지)
  - (c) acceptance #1·#3·#5 PASS 동일
- 근거: 단방향 계약 보존 (telemetry = read-only observer). false-pass 차단 + invariant 7종 정합

**OQ 4** — DC-1 SIS extractor 동일 (P50/P67/P75 windowed) + paper §8 current/cumulative 분리
- 근거: top-down magic threshold 차단 + raw-first + 단방향 계약 강화 (DC-1 SIS와 단일 인터페이스)

**OQ 5** — DC-3 P5R v0 → v1 surface 확장 분리 (rev.3 갱신 X)
- 근거: DC-3 rev.2 [확정] 봉인 보존 + Φ-5 read-only API v0 안정성. envelope 도입은 v1 (rev.next §7-6 단계 도달 시)

**OQ 6** — 병행 (Phase 5 Package Tier 2 4종 author + §7-1 Probe Spec)
- 근거: Tier 2는 DC-3 P5R v0 외부 검증 — Φ-1 mechanism 영역 충돌 0%. breadth-first 정합

---

## 7. 보존 invariant (§3.3.2 정합)

본 STUB rev.next 진행 중 다음을 **반드시 보존**:

- **무파괴 9** — Phase 11~16 mechanism 무영향
- **안전 전제 5종**: HYSTERESIS=2, FOUNDER_RESPAWN_EVERY=480, TARGET_ACTIVE=2, COMMIT_EVERY=48, MAX_MEMBERS=2
- **BOOST=0.20** — Phase 17 Case-C v2 contract
- **회귀 7종 (Tier 1)** — `PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md` rev.2 권위
- **acceptance 4종** (uprising / grievance / dom_share / no_deaths) — 본 rev.next 변경 금지
- **brain·SNN API 무수정** — paper §5.3 정합 ("PersonaBrain은 당장 확장하지 않는 것이 좋다")
- **DC-1 SIS / DC-2 CPCM rev.3 / DC-3 P5R rev.2** — Φ-4 Nation Charter Phase 3 [확정] 본문 무변경

---

## 8. §3.7 6단 사슬 정합 (paper 통합)

본 STUB rev.next는 §3.7 사슬에 다음과 같이 진입:

| 단 | 작업 | paper §7 매핑 |
|:---:|---|---|
| 1단 | 자연 측정 | §7-1 Land-Climate Closure Probe (telemetry raw) |
| 2단 | 분포 분석 | §7-1 누적 후 30일 / cumulative 분위수 |
| 3단 | 결합점 후보 | §7-2~§7-4 mechanism 후보 도출 |
| 4단 | 임계 분위수 | §7-2 Resource/Fertility Dynamics 임계 |
| 5단 | 3엔진 cross-check | Claude + Codex + Gemini (gemini-3.1-pro 가용 시 또는 §3.7 예외 규칙 처리) |
| 6단 | closure 보고서 | rev.next closure (다음 spec 진입 게이트) |

---

## 9. 진입 게이트 — 사용자 결정 영역

본 STUB rev.next 진행 시 다음 결정 필요:

### 9.1 §7-1 Land-Climate Closure Probe Spec 작성 시점
- **즉시 진행** (no-core-diff 무게이트 — §3.3.2 외부)
- **STUB 검토 후 진행**
- **PHASE3 closure 봉인 완료 후 진행** (Tier 2 4종 author와 병행 자원 분리)

### 9.2 Tier 2 4종 author 병행 여부
- **병행** — Phase 5 Package Tier 2 4종 author와 §7-1 Probe Spec 동시 진행 (자원 분산 위험)
- **순차** — §7-1 Probe Spec 우선 (paper 진단 직접 외부 검증 신호 우선)

### 9.3 paper §7 7단계 누적 진행 vs 단계별 검토
- **누적** — §7-1 → §7-2 → ... 자동 진행 (paper §8 9 검증 원칙 통과 시)
- **단계별 검토** — 각 단계 closure 후 사용자 결정 (권장)

---

## 10. Actionable Next — STUB v0 → spec 진입

| 우선 | 작업 | 게이트 | 산출물 |
|:---:|---|:---:|---|
| 1 | **§7-1 Land-Climate Closure Probe Spec 작성** (OQ 1~6 결정 통합 + OQ 3 경로 `physis/world.py:23`) | STUB v0.1 검토 완료 (2026-05-07) | `PHASE-17-LAND-REV-NEXT-DC-1-LAND-CLIMATE-PROBE-SPEC.md` (가칭) |
| 2 | §7-1 spec 구현 (probe telemetry 객체 신설) | spec 검토 후 사용자 승인 | `physis/land_climate_telemetry.py` (가칭) |
| 3 | §7-1 30일 probe 데이터 누적 + 분포 분석 | 무게이트 (raw 측정) | §3.7 1·2단 결과 |
| 4 | §7-2 Resource/Fertility Dynamics Spec 작성 | 사용자 사전 승인 (§3.3.2 mechanism) | `PHASE-17-LAND-REV-NEXT-DC-2-RESOURCE-FERTILITY-SPEC.md` (가칭) |
| 5 | §7-3~§7-7 순차 진행 | 각 단계별 사용자 게이트 | 별도 |

---

## 11. 변경 이력

- **STUB v0** (2026-05-07): 초안 author. paper(2026-05-07) §1~§9 전 통합. V-3 4 sub-test FAIL 직접 외부 검증 신호 + closure-v2 §2.1/§2.2 잔재 + 사용자 메모리 [feedback_snn_emergence_first.md](C:\Users\haj\.claude\projects\c--Users-haj-projects-subagent-orchestrator\memory\feedback_snn_emergence_first.md) / [feedback_root_cause_first.md](C:\Users\haj\.claude\projects\c--Users-haj-projects-subagent-orchestrator\memory\feedback_root_cause_first.md) / [feedback_loom_goal_first.md](C:\Users\haj\.claude\projects\c--Users-haj-projects-subagent-orchestrator\memory\feedback_loom_goal_first.md) / [feedback_design_breadth_first.md](C:\Users\haj\.claude\projects\c--Users-haj-projects-subagent-orchestrator\memory\feedback_design_breadth_first.md) 정합. paper §7 7 작업 순서를 §3.3.2 게이트 분류 + §3.7 6단 사슬 매핑.
- **STUB v0.1** (2026-05-07): OQ 1~6 결정 통합. §9 진입 게이트 3 (9.1 STUB 검토 후 / 9.2 병행 / 9.3 단계별) 사용자 채택. OQ 3 LandCell 검증 경로 정정 — 추천 `ontology/land_cell.py` (실재 X) → 사용자 정정 `physis/world.py:23` (실재 LandCell 정의 위치). §10 Actionable Next #1 무게이트 → STUB v0.1 검토 완료 게이트.

### v0.2 — 2026-05-07 사용자 검토 finding 4 hotfix
- **추가**: §12 Future Work — DC-3 P5R v1 wrapper 권고 (Finding 4 / Minor)
- **무관**: OQ 1~6 결정 / §7-1 spec rev.0 본문 모두 변경 없음
- **trigger**: §7-1 collector/extractor hotfix 동시 commit (synthetic smoke 라벨 + strict JSON + `--ticks` argparse + Future Work memo)

### v0.3 — 2026-05-07 DC-1B ClimateEngine collector spec 분리 cross-reference
- **추가**: §12 Future Work — DC-1B ClimateEngine 기반 collector 신규 author (finding 1-b 응답)
- **링크**: [`PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md`](PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md) (rev.1 / 2026-05-07)
- **무관**: OQ 1~6 결정 / §7-1 spec rev.0 본문 / DC-1B spec 본문 모두 변경 없음
- **trigger**: synthetic smoke baseline 봉인 commit (`6197f8e`)과 분리된 cross-reference commit
  (사용자 정책: "synthetic baseline 봉인과 같은 변경 단위에 섞지 않음")

---

## 12. Open Questions / Future Work

### Future Work — DC-3 P5R v1 wrapper (Minor — 2026-05-07 finding 4)

현재 P5R rev.2 v0 baseline의 `NationSovereignty.dom_share` / `conflict_pair_count` 등은 단일 scalar property이다. consumer가 "국가 주권 *상태*"로 오해할 위험을 v0 단계에서는 §1.0 caveat 명문화로 차단한다. v1 단계 (실제 consumer 진입 직전)에서는 wrapper 확장 권고:

- `provenance: dict` (어떤 metric/window에서 도출됐는지)
- `window: int` (몇 tick 관측한 결과인지)
- `distribution: DistributionTable` (분위수 컨텍스트)
- `status: Literal["candidate", "confirmed"]` (자연 발생 검증 상태)

v1 wrapper는 v0과 별도 모듈(예: `api/nation_p5r_v1.py`)로 author하여 v0 invariant 유지.

### Future Work — DC-1B ClimateEngine 기반 collector (Major — 2026-05-07 finding 1-b)

DC-1 §7-1 rev.0 봉인 (commit `6197f8e`)의 collector
(`scripts/phase17_phi1_land_climate_collect.py`)는 **synthetic random walk** baseline.
paper §7-1 evidence value의 raw 기반으로는 **부족** — 실제 evidence는
`physis.climate_engine.ClimateEngine` 기반 자연 진화 결과여야 한다.

본 후속 spec은 synthetic baseline을 **무수정 보존**하면서 real driver를 **분리 author**한다:

- **신규 collector**: `scripts/phase17_phi1_land_climate_collect_real.py`
- **분리 출력 dir**: `data/phase17_phi1_land_climate_probe_real/` (synthetic `_probe/` 무영향)
- **wiring**: ClimateEngine `tick()` return → `LandCell.climate` direct mapping
  (`weather["precipitation_mm"]` / `weather["temperature_c"]`)
- **default ticks**: 90 (current/cumulative 분리 검증 기본값)
- **무수정 보존**: synthetic baseline / `LandClimateTelemetry` / extractor / `ClimateEngine` /
  `LandCell` / 단방향 계약 영역

권위 spec: [`PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md`](PHASE-17-LAND-REV-NEXT-DC-1B-CLIMATEENGINE-COLLECTOR-SPEC.md)
(rev.1 / 2026-05-07 — OQ 1B-1 + 1B-3 사용자 결정 반영, sub-implementer spawn 가능)

§7-2 mechanism spec 진입 전 본 후속 spec 결과 raw 분포가 **evidence base**로 사용된다.
synthetic vs real 비교 분포 차이가 유의미하면 paper §7-1 evidence value 봉인 단계로 진입.
