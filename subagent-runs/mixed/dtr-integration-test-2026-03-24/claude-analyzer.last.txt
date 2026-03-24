## checkOutputQuality 함수의 감지 패턴

`checkOutputQuality` 함수는 **Deep-Thinking Tokens 연구** 기반으로 워커 출력의 과도한 생각(overthinking) 신호를 감지합니다. 3가지 패턴을 검사합니다:

### 1️⃣ **반복(Repetition)** — 같은 구문 3회 이상
- 문장을 정규화(소문자, 공백 제거)하여 첫 60자를 기준으로 비교
- 20자 이상 길이의 구문만 추적
- **신호**: 동일 표현이 3번 이상 반복되면 경고
- **예시**: "이것은 중요합니다. ... 이것은 중요합니다. ... 이것은 중요합니다."

### 2️⃣ **한정/회피(Hedging)** — 결론 없는 가능성 제시
- 한정 마커 감지: `~일 수 있`, `~도 고려`, `could be`, `might be`, `it depends`, `상황에 따라`, `on the other hand`
- **신호**: 한정 마커 4개 이상이면서 결론 표현 부재
- 결론 표현: `선택`, `choose`, `recommend`, `결론`, `conclusion`, `verdict`
- **의미**: 불확실성만 강조하고 명확한 의사결정이 없는 패턴

### 3️⃣ **자기참조 반복(Self-reference loops)** — 메타-언어 과다 사용
- 메타참조 표현 감지: `앞서 말했듯`, `다시 정리하면`, `as mentioned`, `as I said`, `to summarize again`
- **신호**: 메타참조 3회 이상
- **의미**: 이미 언급한 내용을 반복적으로 재설명하는 overthinking 신호

### 반환 값
```typescript
QualitySignals {
  warningCount: number  // 감지된 경고 개수 (0 = 양호)
  warnings: string[]    // 구체적인 경고 메시지
}
```

**역설적 통찰**: 길이와 품질은 음의 상관관계(r=-0.594) — 길 = 좋음이 아니라, **결정+근거**가 진정한 깊은 생각입니다.