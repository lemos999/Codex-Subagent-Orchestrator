두 Codex 지시서 문서 작성 완료. 요약:

MTS-V1/CODEX_BRIEFS.md (6 briefs)
절대 불변: 7:3 비대칭, Layered 평균가 하향, Triple Confluence 희소 승급, Runner 대승 보호

#	내용	예상
#6	SPEC v5.2 Gap (Volume Profile close-single-bin 명시 + Fibo pivot 시간 순서)	0.5d
#1	Phase 3 State Machine (INIT→STAGE1→STAGE2→RUNNER→EXIT)	1.5d
#3	Phase 5 Hard SL (평균가 기준, 체결가 아님)	0.5d
#2	Phase 4 TP A/B/C (A=1R 분할, B=2R 승급 게이트, C=3R 트레일)	1d
#4	Phase 6 Runner (익절 금지, 트레일 전용)	0.5d
#5	Phase 7 Ops+Parity+Backtest (Pine/Python parity, walk-forward)	1.5d
권장 순서: #6 → #1 → #3 → #2 → #4 → #5

predictive_runner_paper/CODEX_BRIEFS.md (3 briefs)
절대 불변: strategy.py 수식(gate_high/low_score, tighten_mult, predictive_active 공식) 수정 금지. Track A로 기존 가설 반증됨, 다음은 OOS 확장 + allow-list 라우팅만.

#	내용	조건
#1	OOS 180d 확장 (r2_sixway_runner.py --days, market_data.py 캐시)	선행 필수
#2	자산 allow-list 라우팅 (ETH/XRP/BNB/DOGE만 R2, 수식 불변)	#1 PASS 후
#3	페이퍼 트레이딩 이관 (scripts/paper_trading_runner.py + 대시보드 섹션)	#2 PASS 후
봉인 섹션: gate 컷오프 재설계·tighten_mult 합성 등 전략 변경은 별도 승인 필요 항목으로 분리 고지.

두 문서 모두 self-contained (배경·SPEC 참조·편집 허용/금지·검증·완료 기준). Codex가 Claude 개입 없이 단독 수행 가능한 형태.

Codex 전달 순서 (9개)
순서	지시서	Brief	이유	예상
1	predictive	#1 OOS 180d	Track A 결과가 30d 한정 → 180d로 allow-list 전략 타당성 먼저 검증. 코드량 적음. 이후 #2·#3 방향 결정	0.5d
2	MTS-V1	#6 SPEC Gap	문서 수정 짧음. 이후 Phase 전부에 영향 (Volume Profile 정의·Fibo 순서)	0.5d
3	MTS-V1	#1 Phase 3 State Machine	이후 모든 Phase의 기반	1.5d
4	MTS-V1	#3 Phase 5 Hard SL	State Machine 위 안전 레이어. TP 구현 전 SL 보호 먼저	0.5d
5	MTS-V1	#2 Phase 4 TP A/B/C	핵심 익절 로직 (A=1R 분할, B=2R 승급, C=3R 트레일)	1d
6	MTS-V1	#4 Phase 6 Runner	Triple Confluence 검증 후 대승 처리	0.5d
7	MTS-V1	#5 Phase 7 Ops+Parity+Backtest	최종 검증 (Pine/Python parity + walk-forward)	1.5d
8	predictive	#2 allow-list	순서 1 PASS 조건부	0.5d
9	predictive	#3 paper trading	순서 8 PASS 조건부	1d
각 Brief 리뷰 체크리스트 (공통)
완료 보고 받으면 다음을 확인:

편집 범위 준수 — 지시서의 "편집 허용/금지" 범위 밖 파일 변경 없는가
절대 불변 보존 — 7:3 비대칭 / 수식 / SPEC 원칙 건드리지 않았는가
검증 실행 — mypy / ruff / pytest 실행 결과 첨부되었는가 (Windows Smart App Control로 mypy 차단 시 그 사실 명시)
완료 기준 충족 — 각 Brief 말미의 "완료 기준" 항목 전체 체크되는가
Evidence — 필요 시 subagent-runs/ 기록 여부
체크포인트 (순서 중단/분기 기준)
순서 1 FAIL (180d에서 allow-list 자산 열위) → 순서 2로 넘어가되, 8·9는 전략 재검토 후 재시작
순서 3 FAIL (State Machine 불변 위반) → 순서 4·5·6 전부 보류, 근본 원인 추적 먼저
순서 7 FAIL (Pine/Python parity 불일치) → 원인 Phase 역추적 (5→2→1 순)
권장: 순서 1과 2를 병렬 전달 가능 (독립 프로젝트). 다만 1개 Codex 세션만 가능하면 위 순서대로.

첫 번째로 전달하실 지시서 준비되었습니다: Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md의 Brief #1 (Step 1 OOS 180d).



순서 1
파일: Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md
   - Projects/Trading Value/predictive_runner_paper/strategy.py
   - Projects/Trading Value/predictive_runner_paper/r2_sixway_runner.py
   - Projects/Trading Value/predictive_runner_paper/market_data.py

2. CODEX_BRIEFS.md의 "Brief #1 (Step 1 OOS 180d)"만 수행한다.
   다른 Brief(#2, #3)는 건드리지 않는다.

3. 절대 불변: strategy.py의 수식(gate_high_score/gate_low_score/tighten_mult/predictive_active 공식) 수정 금지.
   market_data.py 캐시 확장과 r2_sixway_runner.py --days 인자 추가만 허용.

4. Windows 환경: RTK prefix 사용(rtk python ...), 127.0.0.1 고정, mypy Smart App Control 차단 시 명시.

5. 완료 시 다음 보고:
   - 변경 파일 목록 (diff 요약)
   - ruff/mypy 검증 결과 (차단되면 명시)
   - 180d run 결과 summary_all.json 경로
   - 자산별 expectancy_r / tail_winner_share 표
   - Brief #1 "완료 기준" 체크 리스트
순서 2
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md

2. CODEX_BRIEFS.md의 "Brief #6 (SPEC v5.2 Gap)"만 수행한다.
   다른 Brief는 건드리지 않는다.

3. 절대 불변: 7:3 비대칭 / Layered 평균가 하향 / Triple Confluence / Runner 대승 보호 원칙 변경 금지.
   SPEC_V5.md 수정만 허용 (Volume Profile close-single-bin 명시 + Fibo pivot 시간 순서 검증 조항 추가).

4. 완료 시 다음 보고:
   - SPEC_V5.md diff
   - 추가된 조항 전문
   - Brief #6 "완료 기준" 체크 리스트
순서 3
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md
   - Projects/Trading Value/MTS-V1/strategy.py
   - Projects/Trading Value/MTS-V1/REPORT.md

2. CODEX_BRIEFS.md의 "Brief #1 (Phase 3 State Machine)"만 수행한다.
   Phase 4/5/6/7은 건드리지 않는다.

3. 절대 불변: INIT→STAGE1→STAGE2→RUNNER→EXIT 전이 규칙은 SPEC_V5.md §State Machine 항 그대로.
   7:3 비대칭, Layered 평균가 하향 원칙 훼손 금지.

4. Windows 환경: RTK prefix(rtk python ...), mypy 차단 시 명시.

5. 완료 시 다음 보고:
   - strategy.py diff
   - 새 테스트 (tests/test_state_machine.py 등) 결과
   - pytest / ruff / mypy 실행 결과
   - Brief #1 "완료 기준" 체크 리스트
순서 4
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md
   - Projects/Trading Value/MTS-V1/strategy.py (순서 3 완료 후 상태)

2. CODEX_BRIEFS.md의 "Brief #3 (Phase 5 Hard SL)"만 수행한다.
   Phase 4/6/7은 건드리지 않는다.

3. 절대 불변: Hard SL은 **평균가 기준**이며 체결가(last-fill price)가 아니다.
   Layered 평균가 하향 원칙 그대로.

4. 완료 시 다음 보고:
   - strategy.py diff
   - SL 테스트 (평균가 갱신 시나리오 포함) 결과
   - pytest / ruff / mypy 결과
   - Brief #3 "완료 기준" 체크 리스트
순서 5
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md
   - Projects/Trading Value/MTS-V1/strategy.py (순서 3, 4 완료 후 상태)

2. CODEX_BRIEFS.md의 "Brief #2 (Phase 4 TP A/B/C)"만 수행한다.
   Phase 6/7은 건드리지 않는다.

3. 절대 불변:
   - TP A = 1R에서 부분 분할
   - TP B = 2R에서 Triple Confluence 승급 게이트 (희소 통과)
   - TP C = 3R 이후 트레일 전용
   - 7:3 비대칭 유지 (Runner 비중 30% 이상 보존)

4. 완료 시 다음 보고:
   - strategy.py diff
   - TP A/B/C 각 테스트 결과
   - Triple Confluence 미통과 시 TP C로 넘어가지 않음 확인 테스트
   - pytest / ruff / mypy 결과
   - Brief #2 "완료 기준" 체크 리스트
순서 6
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md
   - Projects/Trading Value/MTS-V1/strategy.py (순서 5 완료 후 상태)

2. CODEX_BRIEFS.md의 "Brief #4 (Phase 6 Runner)"만 수행한다.
   Phase 7은 건드리지 않는다.

3. 절대 불변:
   - Runner 구간(TP C 이후)은 **익절 금지**
   - 오직 트레일 SL로만 청산
   - Runner 대승 보호 원칙 그대로

4. 완료 시 다음 보고:
   - strategy.py diff
   - Runner 구간 진입/트레일/청산 테스트 결과
   - 익절 함수가 Runner 상태에서 호출되지 않음 확인 테스트
   - pytest / ruff / mypy 결과
   - Brief #4 "완료 기준" 체크 리스트
순서 7
파일: Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/MTS-V1/CODEX_BRIEFS.md
   - Projects/Trading Value/MTS-V1/SPEC_V5.md
   - Projects/Trading Value/MTS-V1/strategy.py (순서 6 완료 후 상태)
   - Projects/Trading Value/MTS-V1/strategy.pine

2. CODEX_BRIEFS.md의 "Brief #5 (Phase 7 Ops+Parity+Backtest)"만 수행한다.

3. 절대 불변: Pine Script v5 / Python CCXT 구현 parity 필수.
   walk-forward 검증 + Wilson 95% CI / Bill Williams 5-bar fractal.

4. Windows 환경: RTK prefix, 127.0.0.1 고정.

5. 완료 시 다음 보고:
   - strategy.py / strategy.pine diff
   - parity 테스트 (동일 입력 → 동일 시그널 비율) 결과
   - walk-forward 백테스트 결과 (자산별 expectancy_r, tail_winner_share)
   - Runner 모델 절대 기준(expectancy>0 AND tail_winner_share ≥ 0.13) 통과 자산 목록
   - pytest / ruff / mypy 결과
   - Brief #5 "완료 기준" 체크 리스트
   - REPORT.md 갱신
순서 8
조건: 순서 1 (OOS 180d) 리뷰 PASS 후에만 전달

파일: Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md
   - Projects/Trading Value/scripts/runner.py
   - 순서 1에서 생성된 180d summary_all.json

2. CODEX_BRIEFS.md의 "Brief #2 (자산 allow-list 라우팅)"만 수행한다.
   Brief #3는 건드리지 않는다.

3. 절대 불변:
   - strategy.py 수식 수정 금지 (gate_high_score / gate_low_score / tighten_mult / predictive_active 공식)
   - scripts/runner.py에 allow-list 필터만 추가 (ETH / XRP / BNB / DOGE)
   - "봉인된 과제"(gate 컷오프 재설계 등) 건드리지 않음

4. 완료 시 다음 보고:
   - scripts/runner.py diff
   - allow-list 적용 전/후 자산별 expectancy_r 비교 표
   - 제외 자산(BTC / SOL 등)이 실제로 R2 경로를 타지 않음 확인 로그
   - pytest / ruff / mypy 결과
   - Brief #2 "완료 기준" 체크 리스트
순서 9
조건: 순서 8 리뷰 PASS 후에만 전달

파일: Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md

지시 내용:


작업 디렉터리: c:\Users\haj\projects\subagent-orchestrator

1. 다음 파일을 읽는다:
   - Projects/Trading Value/predictive_runner_paper/CODEX_BRIEFS.md
   - Projects/Trading Value/scripts/runner.py (순서 8 완료 후 상태)
   - Projects/Trading Value/scripts/dashboard_unified.py

2. CODEX_BRIEFS.md의 "Brief #3 (페이퍼 트레이딩 이관)"만 수행한다.

3. 신규 생성:
   - Projects/Trading Value/scripts/paper_trading_runner.py
   - dashboard_unified.py에 R2 섹션 추가

4. 절대 불변:
   - strategy.py 수식 수정 금지
   - allow-list 동일하게 적용 (순서 8과 일치)
   - 127.0.0.1 고정 (localhost 사용 금지)

5. Windows 환경: RTK prefix 필수.

6. 완료 시 다음 보고:
   - 신규/변경 파일 diff
   - 페이퍼 트레이딩 dry-run 결과 (1일치 샘플)
   - 대시보드 스크린샷 경로 또는 섹션 렌더링 확인 로그
   - pytest / ruff / mypy 결과
   - Brief #3 "완료 기준" 체크 리스트



   //리뷰//
   안녕하세요. `predictive_runner_paper` Brief #1 (Step 1 OOS 180d)
  구현/검증 리뷰 부탁드립니다.

  기준 문서:
  - `Projects/Trading Value/predictive_runner_paper/
  CODEX_BRIEFS.md`
  - 수행 범위: **Brief #1 only**
  - Brief #2, #3는 건드리지 않았습니다.

  불변 조건 준수:
  - `strategy.py` 수식은 수정하지 않았습니다.
  - 특히 `gate_high_score`, `gate_low_score`, `tighten_mult`,
  `predictive_active` 공식 변경 없음
  - 허용 범위인 `market_data.py` 캐시 확장 + `r2_sixway_runner.py
  --days` 추가만 반영했습니다.

  변경 파일:
  - `Projects/Trading Value/predictive_runner_paper/
  market_data.py`
  - `Projects/Trading Value/predictive_runner_paper/
  r2_sixway_runner.py`

  주요 반영 내용:
  1. `market_data.py`
     - `cache_{days}d/` 일반화
     - `expected_bar_count()`, `minimum_cache_rows()`,
  `fetch_days_cache()`, `fetch_180d_cache()` 추가
     - 90d 캐시 로직을 파라미터화했지만 기존 `cache_90d/`는 삭제/
  변경하지 않음

  2. `r2_sixway_runner.py`
     - `--days` CLI 인자 추가
     - `--runs-subdir` 자동 생성 지원
     - `python -m predictive_runner_paper.r2_sixway_runner` 형태
  실행 가능하도록 import 보강
     - `--days 180` 실행 시 `cache_180d/` 사용
     - 새 run 디렉터리에 `summary_all.json` + `trades/*.csv` 저장
     - `comparison-90d-vs-180d.md` 생성
     - Brief #1 PASS/PARTIAL/FAIL 판정 로직 추가

  실행 명령:
  - `rtk python -m predictive_runner_paper.r2_sixway_runner --days
  180 --runs-subdir r2_sixway_oos_180d_20260424`

  검증 결과:
  - `rtk python -m pyflakes predictive_runner_paper/strategy.py
  predictive_runner_paper/r2_sixway_runner.py
  predictive_runner_paper/market_data.py` 통과
  - `rtk python -m pytest predictive_runner_paper/tests -q` → `21
  passed`
  - `rtk python -m ruff check predictive_runner_paper/
  r2_sixway_runner.py predictive_runner_paper/market_data.py` 통과
  - `rtk python -m mypy --explicit-package-bases ...` 실패
    - Smart App Control 차단은 아님
    - 원인: `pandas-stubs` 미설치로 `pandas`가 `import-untyped`

  산출물:
  - `Projects/Trading Value/predictive_runner_paper/runs/
  r2_sixway_oos_180d_20260424/summary_all.json`
  - `Projects/Trading Value/predictive_runner_paper/runs/
  r2_sixway_oos_180d_20260424/comparison-90d-vs-180d.md`

  180d 결과 요약:
  - 기준 variant: `r2_profiled_fixed`
  - BNB: `expectancy_r=+0.096684`, `tail_winner_share=0.285714`
  - BTC: `expectancy_r=+0.451669`, `tail_winner_share=0.272727`
  - DOGE: `expectancy_r=-0.056734`, `tail_winner_share=0.142857`
  - ETH: `expectancy_r=-0.111413`, `tail_winner_share=0.125000`
  - SOL: `expectancy_r=-0.555998`, `tail_winner_share=0.000000`
  - XRP: `expectancy_r=+0.112336`, `tail_winner_share=0.285714`

  Brief #1 판정:
  - `FAIL`

  해석:
  - ETH가 180d에서 core asset 기준(expectancy > 0,
  tail_winner_share >= 0.13)을 유지하지 못했고 DOGE도 이탈했습니
  다.
  - 반대로 BTC가 통과로 올라와 90d의 자산 경계가 OOS에서 뒤집혔습
  니다.
  - 따라서 Brief #2 / #3로 진행하면 안 된다고 판단했습니다.

  리뷰 시 특히 봐주시면 좋은 포인트:
  1. `strategy.py` 불변 수식에 영향이 전혀 없는지
  2. `market_data.py`의 180d 캐시 검증 기준이 Brief #1 요구와 맞는
  지
  3. `r2_sixway_runner.py`의 `--days`/출력 경로 처리와 기존 90d
  baseline 보존이 안전한지
  4. `comparison-90d-vs-180d.md`의 판정 기준이 문서 의도와 맞는지
  5. FAIL 시 Brief #2 차단 판단이 적절한지

  엄격하게 봐주셔도 됩니다. 규칙 위반, Brief 범위 초과, 판정 오류
  가 있으면 그 기준으로 바로 수정하겠습니다.


  // 리뷰에 대한 클로드 반응 //

  Brief #1 리뷰 결과: PASS (구현) / FAIL (판정) — 승인
검토 5개 포인트 전부 확인 완료. 구현·검증·판정 모두 지시서와 일치. Brief #2 차단 판단 적절.

1. strategy.py 불변 수식 영향 — ✅ OK
직접 grep 대조 결과 전부 원값 유지:

strategy.py:788 mfe_term_base = clip01((mfe_atr_val - 3.0) / 1.5) — 3.0 원값
strategy.py:790 near_peak = clip01(1.0 - (mfe_atr_val - unrealized_r) / 1.0) — 원값
strategy.py:890 predictive_active = current_r >= 2.0 and mfe_atr_val >= 3.0 — 3.0 원값
strategy.py:714, 717, 727, 730, 740, 743 gate_low_score=70/72, gate_high_score=85/88 — 원값
Track A에서 주입한 카운터(line 121-124 등)는 관측 전용이며 수식 영향 없음. Brief #1이 추가로 건드린 부분 없음.

2. market_data.py 180d 캐시 검증 — ✅ OK
minimum_cache_rows(15m, 180): max(17000, int(17280*0.98)) = max(17000, 16934) = 17000
지시서 line 109 요구 "각 파일 ≥ 17000 rows" 정확히 일치
cache_directory(base, 180) = cache_180d/ — 일반화된 경로 구조
fetch_days_cache에서 canonical (BTC.csv) + legacy (BTC_15m.csv) 둘 다 시도 → 기존 cache_90d/BTC_15m.csv 유지 ✓
target_path 분기 (days == 90 and legacy_path.exists())로 기존 포맷 보존 ✓
3. --days / 출력 경로 / 90d baseline 보존 — ✅ OK
--days 기본값 90 (기존 동작 보존)
--runs-subdir 자동 생성 (default_runs_subdir(180) → r2_sixway_oos_180d_<ts>)
baseline 파일 runs/r2_sixway/summary_all.json은 읽기만 (line 238-241) — 덮어쓰기 경로 없음
glob 확인: runs/r2_sixway/, runs/r2_sixway_track_a_*/ 모두 보존됨
4. comparison-90d-vs-180d.md 판정 기준 — ✅ OK
classify_brief_one 로직:


core_assets = ("ETH", "XRP", "BNB")
if any(not row_passes_threshold(by_asset.get(asset, {})) for asset in core_assets):
    return "FAIL", ...
CODEX_BRIEFS.md line 103 "ETH/XRP/BNB까지 일부 미달 → FAIL" 정의와 정확 일치
row_passes_threshold: expectancy_r > 0 AND tail_winner_share ≥ 0.13 — 지시서 line 51, 101 기준 정확 일치
PRIMARY_VARIANT = "r2_profiled_fixed" 선택 — Track A 결과 기준 variant로 적절
5. FAIL 시 Brief #2 차단 판단 — ✅ OK
CODEX_BRIEFS.md line 104 "FAIL: … Brief #2 보류, Claude 알림 후 대기"
line 266 "Brief #1 FAIL 시: Brief #2/#3 진행 금지"
Codex 판단 "Brief #2 / #3로 진행하면 안 된다" — 지시 그대로 준수
관찰 메모 (선택 권고, Brief #1 통과와 무관)
(a) BTC 역전 현상의 해석 문구 보강 권장
90d → 180d에서 자산 경계 반전이 발생:

90d 미달 → 180d 통과: BTC (exp -0.294 → +0.452)
90d 통과 → 180d 미달: ETH (exp +0.499 → -0.111), DOGE (+0.172 → -0.057)
현재 comparison-90d-vs-180d.md의 "This tells us:" 문장이 일반론에 그침. 다음 문단 추가 권장:


자산 경계 반전: ETH/DOGE가 90d 통과에서 180d 미달로 이탈한 반면, 
BTC가 180d에서 통과로 올라옴. This tells us: allow-list 전략이 
fixed boundary가 아닌 시기 의존적(period-dependent) 경계를 가짐. 
기간 고정 allow-list로는 OOS robust 보장 불가.
(b) mypy 미통과 — 수용 가능
Brief #1 검증 요구 (line 108): pyflakes + pytest만 명시. mypy는 요구사항 아님
pandas-stubs 미설치 원인으로 import-untyped는 환경 이슈. Smart App Control 차단 아님 — 명확히 구분됨
pyflakes 통과 + pytest 21/21 충족으로 Brief #1 검증 요건 완성
(c) Track A 카운터 잔존
predictive_active_count, near_peak_fix_effective_count 등 Track A에서 주입한 관측 필드가 summary_all.json에 기록되어 있음(strategy.py:622-625). Brief #1 위반 아니며, 향후 ETH/DOGE 180d 발화 패턴을 조사할 때 무료 진단 데이터로 활용 가능.

다음 액션
Brief #1 FAIL 판정 확정. predictive_runner_paper 계열은 일시 중단.

다음 전달 순서: 순서 2 — MTS-V1 Brief #6 (SPEC v5.2 Gap)

predictive_runner의 "봉인된 과제"(gate 컷오프 재설계 등)는 전략 변경 범주이므로 사용자 제약에 따라 이번 사이클에는 착수 불가. MTS-V1 쪽으로 전환하는 것이 제약 준수 경로.

Codex에 전달할 리뷰 회신 (복붙용)

Brief #1 리뷰 결과: PASS (구현 승인)

- strategy.py 불변 수식 3곳 grep 확인, 전부 원값 유지
- market_data.py minimum_cache_rows(15m, 180) = 17000 정확
- r2_sixway_runner.py --days / --runs-subdir 구현 + 90d baseline 보존 확인
- classify_brief_one (core=ETH/XRP/BNB) 판정 로직이 CODEX_BRIEFS.md 
  line 103 FAIL 정의와 일치
- Brief #2 차단 판단 적절 (line 104, 266 준수)

판정: Brief #1 = FAIL → Brief #2 진행 금지 확정.

선택 권고 (반영 여부 재량):
1. comparison-90d-vs-180d.md에 BTC 역전 해석 문단 추가
2. mypy는 Brief #1 요건 아님 — 그대로 수용

---

## 2026-04-24 Codex Step 8/9 Paper-Only Decision

원 Brief #1 판정은 계속 FAIL이다. 다만 사용자가 Step 9까지 진행 권한을 부여했으므로
전략 수식은 봉인한 채, 180d OOS에서 실제 통과한 자산만 라우팅하는 paper-only 경로로
Step 8/9를 재범위화했다.

- 원 배포 전제 `ETH/XRP/BNB/DOGE`는 무효.
- 180d OOS 통과 기준 allow-list는 `BTC/BNB/XRP`.
- `ETH/DOGE/SOL`은 paper runner R2 경로에서 skip.
- 이 결정은 실거래 승인 또는 원 Brief PASS가 아니라, 실주문 없는 paper-only 진행 경로다.
- Pine/MTS-V1은 TradingView 컴파일, 실제 CSV parity, 90d MTS-V1 trade log가 남아 있어 최종 readiness 보류.

다음 작업: Brief #1 계열 일시 중단. predictive_runner_paper 종료.
사용자가 MTS-V1 Brief #6로 전환할 예정.
