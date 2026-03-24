# Run Summary: gdd-analysis

## 요청
`/gdd` (게임 기획 디렉터)를 기반으로 범용 기획 스킬을 만들지, 새로 만들지 분석

## 3개 엔진 결론 — 완전 수렴

| 엔진 | 추천 | 핵심 근거 |
|------|------|----------|
| Claude (opus) | **신규 생성 + /gdd 구조 포크** | 72% ADAPTABLE → 재사용 가치 높음, 그러나 /gdd 직접 수정은 게임 정밀함 훼손 |
| Gemini (pro) | **골격 추출 → 신규 스킬** | 55% GENERIC + 15% ADAPTABLE = 70%가 범용 가능, /gdd는 유지 |
| Codex (GPT) | **Protocol Kernel + Domain Pack** | Phase agent는 공통, domain pack으로 질문/판정/검증/출력만 주입 |

## 합의점

1. **접근법**: /gdd를 직접 수정하지 말고, 골격을 추출하여 새 범용 스킬 생성
2. **재사용율**: 70~85% (엔진별 산정 차이 있으나 대부분 재사용 가능)
3. **아키텍처**: 공통 Phase Kernel + Domain Pack (선언형 프로필)
4. **마이그레이션**: game → generic → software 순서로 점진적 검증
5. **/gdd 보존**: 기존 /gdd는 domain=game 프리셋으로 재정의하여 호환 유지

## 핵심 매핑 테이블 (3 엔진 합의)

| GDD 개념 | 범용 개념 | 전환 난이도 |
|----------|----------|-----------|
| Game DNA | Project Charter | Low |
| 핵심 감정 | Primary Outcome / Value Proposition | Low |
| 코어 루프 | Operating Loop / User Flow | Low |
| 장르 컨벤션 | Baseline Expectations | Low |
| USP | Differentiation Thesis | Low |
| 시스템 | Components / Workstreams | Low |
| 재미 4문항 | Value Contribution Test | Medium |
| 핀셋 인터뷰 | Decision Card Interview | Medium |
| 22종 시스템 템플릿 | Domain Component Catalog | High (도메인별 신규) |
| Mode B 분석 | Existing Product Analysis | High (도메인별 재설계) |

## 예상 작업량
- 코어 신설: ~18개 파일
- /gdd 마이그레이션: ~15개 파일 수정/이동
- generic + software MVP: ~10개 파일
- **총 ~40개 파일, 3단계 점진적 진행 권장**
