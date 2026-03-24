# Run Summary — 큐 러너 TS 전환 검증

## 종합 결과: 수정 필요 5건

### Codex (GPT 5.4) — PS 호환성 검증

| # | 항목 | 결과 | 주요 이슈 |
|---|------|------|----------|
| 1 | 설정 파싱 | PARTIAL | hooks 평면 필드명 차이, 알 수 없는 훅 필드 전달 누락 |
| 2 | 이슈 정규화 | PASS | state 기본값 차이 (TS: '', PS: 'Todo') |
| 3 | 핑거프린트 | **FAIL** | TS는 정렬, PS는 원순서 유지. source_path/source_kind 보강 누락 |
| 4 | blocked_by | PARTIAL | PS는 status=completed이면 해소, TS는 fingerprint 필수 |
| 5 | 백오프 | PASS | 동일 |
| 6 | 상태 파일 | PARTIAL | 20필드(17아님), last_manifest/summary 미채움, schema_version 추가 |
| 7 | 디스패치 | PASS | 동일 |
| 8 | 우선순위 | **FAIL** | PS는 updated_at 오름차순, TS는 내림차순(newer first) |

### Gemini — 코드 품질 리뷰

총평: **잘 설계된 시스템**, 보완 필요 사항:
- Windows 프로세스 트리 종료 (SIGTERM → taskkill /t)
- spawn 실패 시 파일 핸들 누수 가능
- YAML 파서 한계 (복잡한 구조 미지원)
- drain 로직 중복 → reapWorkers() 추출 권장
- JSON 파싱 정규식 오작동 가능

## 수정 대상 (우선순위)

1. **핑거프린트 정렬 제거** — PS와 동일하게 원순서 유지
2. **updated_at 정렬 방향** — 오름차순으로 변경 (PS 동일)
3. **blocked_by 해소 로직** — status=completed이면 해소 (fingerprint 불필요)
4. **state 기본값** — '' → 'Todo'
5. **완료 시 last_manifest/summary 채우기**
