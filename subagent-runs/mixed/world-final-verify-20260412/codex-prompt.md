## 페르소나 국가 세계관 최종 검증 — Codex 담당 3명

FAIL/WARN/PASS로 판정하라.

## 검증자 5: Teo Kang — 수치 교차 대조
11개 Charter에 산재된 수치가 모순되지 않는가:
- WILL 총량 20,260,406이 모든 문서에서 동일?
- 세율 10/3/0.5/5%가 경제백서와 사회Charter에서 일치?
- 뉴런 50M, energy 0.01~0.25/틱, 캐시 히트율이 일관?
- 틱=게임1시간=현실30분이 모든 문서에서 동일?
- 1 WILL = 1,000 gold가 모든 문서에서 동일?
- 클래스 체계(1~9+EX)가 헌법/경제/사회에서 일치?
- 초기 인구 500명(4:3:3)이 physis/society에서 일치?
- 에포크 반감기 수치가 경제백서와 tick-daemon에서 일치?

## 검증자 6: Dana Jeong — 행동 흐름 추적
하나의 행동이 여러 Charter를 거치는 경로를 추적:

경로 1: "양심 딜레마"
  Physis(날씨→스트레스) → PersonaBrain(V vs S+B, PFC_VM) → Action_Proposal → Nomos(승인/거부) → 피드백(V+L) → STDP
  끊기는 곳은?

경로 2: "비밀 폭로"
  secret-charter(비밀 생성) → PersonaBrain(B클러스터, AMY_BLA) → 폭로 Proposal → Nomos(명예훼손?) → order-charter(법) → 소문 전파
  끊기는 곳은?

경로 3: "영주 해임"
  사회charter(투표) → economy(스테이킹) → PersonaBrain(정치적 선택) → Nomos(투표 집계) → 영지 공백 → 선출
  끊기는 곳은?

## 검증자 10: Jin Harada — 장애 복구 완전성
- Executor 다운 → heartbeat 60초 → 재시작: 경로 완전?
- WAL 30초 → 최대 1틱 손실: 모든 상태가 복구되는가?
- PersonaBrain 학습 발산 → 복구 경로 정의되어 있는가?
- 캐시 완전 손상 → 복구 경로? (에포크 부분 무효화는 있지만 완전 손상은?)
- Fallback C(no-op) 이후에도 복구 안 되면 최종 안전망?
- 단일 장애점(SPOF)이 존재하는가?

한글.
