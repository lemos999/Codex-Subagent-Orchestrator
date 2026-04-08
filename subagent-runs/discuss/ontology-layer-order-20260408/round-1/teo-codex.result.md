# Teo Kang (Codex GPT-5.4) — 게임 설계 관점

**제3안: 존재론은 B, 런타임은 A처럼 운용**

게임 엔진에선 보통 World가 맵·영역·시간축 같은 상태와 좌표계를 들고, System이 그 위를 순회하며 갱신한다. ECS도 동일 — World(엔티티/컴포넌트/리소스)가 바닥이고 System은 읽고 쓴다.

CK3·RimWorld류도 월드 스키마가 먼저, 기후·경제·AI가 그 위에 얹힌다. Dwarf Fortress도 지형·시간축이 규칙의 기판.

World Ontology 문서라면 Layer 1은 Space-Time, Layer 2는 Physis+Triad가 자연스럽다.

다만 존재론 문서와 런타임 아키텍처의 순서는 같을 필요 없다. 전자는 "무엇이 먼저 존재하나", 후자는 "무엇이 먼저 계산되나".

**추가 제안: 데몬은 "레이어"보다 "횡단 실행자"로 표기하라.**
