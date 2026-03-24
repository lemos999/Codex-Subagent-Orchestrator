# Codex/GPT — Architecture Advisor Result

## 추천 아키텍처: Option D — Protocol Kernel + Domain Pack

Option A(Base+Plugin) 뼈대 + Option B(인터페이스)를 선언형 domain profile로 + Option C(템플릿)는 출력 계층에만 제한

## 핵심 설계

### 디렉터리 구조
```
skills/planning-director/
  SKILL.md                  # 코어 실행 스킬
  core/                     # routing, state-model, phase-contracts, validation, change-control
  agents/                   # phase0~6 + analysis-mode (공통)
  templates/                # charter, component-map, decision-card, cross-impact, readiness, change-impact
  specs/                    # pipeline.claude.json, analysis.claude.json
  domains/
    generic/profile.yaml + heuristics.md + templates/
    game/profile.yaml + ontology.md + heuristics.md + catalogs/ + templates/ + overrides/
    software/profile.yaml + heuristics.md + templates/
    business/profile.yaml + heuristics.md + templates/
```

### 게임 → 범용 개념 매핑
| GDD 개념 | 일반화 개념 |
|---|---|
| DNA 5항목 | Charter |
| 핵심 감정 | Primary Outcome |
| 코어 루프 | Operating Loop |
| 장르 컨벤션 | Baseline Expectations |
| USP | Differentiation Thesis |
| 시스템 | Components / Workstreams |
| 핀셋 인터뷰 | Decision Card Interview |
| 재미 4문항 | Value Contribution Test |
| 코딩 착수 가능 | Execution-Ready Gate |

### 마이그레이션 경로
game → generic → software 순서로 검증 (한 번에 다도메인 확장 금지)

### 예상 작업량
- 코어 뼈대 신설: 14~18개 파일
- /gdd 마이그레이션: 수정 3~5개, 이동/분해 8~12개
- domains/generic: 3~5개
- domains/software MVP: 5~8개
- **총 22~30개 파일**
