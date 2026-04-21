# Round 2 — Codex gpt-5.4

### Q1 답변
`commit hash` 주석만으로는 drift를 "방지"하지는 못하고, 사후 추적만 가능하게 합니다. 48시간짜리 단기 ablation이면 `복사 원본 commit hash + 실행 artifact에 동일 hash 기록 + 종료 후 archive/read-only 보관`이면 운영상 충분할 수 있지만, 장기 재실행까지 생각하면 fork는 본질적으로 D보다 drift 리스크가 큽니다.

### Q2 답변 (핵심)
결론부터 말하면 **D-1은 실제 Python 실행 경로로 성립합니다. D-2는 필수가 아닙니다.**

근거는 `v2.py`의 실행 순서가 명확합니다.

1. `V2Engine.__init__`에서 `self.predictors`는 생성만 됩니다.
   `v2.py:605-625`를 보면 `self.predictors = {a: OnlinePredictor() ...}` 뒤에 곧바로 `pm/history/prices/tick_count/prev_features/_last_funding`만 세팅하고 끝납니다. 이 구간에서 `self.predictors[...]`를 읽어 쓰는 추가 로직이 없습니다.

2. predictor의 첫 실제 사용은 `tick()`입니다.
   `v2.py:714-723`에서 처음 `predictor = self.predictors[asset]`를 꺼내 `update()`와 `predict()`를 호출합니다. 즉, **부모 `__init__`가 끝난 뒤 subclass에서 `self.predictors`를 재할당해도 사용 시점보다 충분히 앞**입니다.

3. `run()` 순서도 D-1에 유리합니다.
   `v2.py:877-879`에서 `run()`은 `self._load_state()`를 먼저 호출하고, 그 다음 `init()`, 그 다음 루프에서 `tick()`을 돕니다. 따라서 subclass가 생성자에서 `self.predictors`를 교체해두면, `_load_state()`도 **교체된 predictor 인스턴스들**에 state를 주입합니다.

4. `_load_state()` / `_save_state()`가 요구하는 인터페이스도 subclass로 충족됩니다.
   `v2.py:841-873`에서 접근하는 것은 `pred.w`, `pred.b`, `pred.norm.mean/var/warm`뿐입니다. `OnlinePredictor` subclass면 그대로 상속받으므로 문제 없습니다. `snapshot()` / `_log_tick()`도 `direction_accuracy()`, `memory_entropy()`, `feature_importance`, `accuracy_history`, `predictions`만 쓰는데 역시 상속으로 충족됩니다.

따라서 이런 구조는 작동합니다.

```python
class NoRule2Predictor(v2.OnlinePredictor):
    def _rebalance_memory(self):
        return None

class AblationEngine(v2.V2Engine):
    def __init__(self, assets, port):
        super().__init__(assets, port=port)
        self.predictors = {a: NoRule2Predictor() for a in assets}
```

다만 **실행 가능성**과 **실험 순수성 디테일**은 구분해야 합니다.

- `V2Engine.__init__(..., port: int = DASH_PORT)`의 default는 함수 정의 시점에 8897로 캡처됩니다. 그래서 import 후 `v2.DASH_PORT`를 재바인딩해도, **부모 `__init__` default는 안 바뀝니다**. D-1에서는 subclass가 `port`를 명시 전달하거나 `__init__` 시그니처를 다시 잡아야 합니다.
- `LOG_PATH` / `STATE_PATH`는 `_log_tick()` / `_save_state()` / `_load_state()`에서 글로벌을 런타임에 읽으므로, wrapper에서 import 후 재바인딩하면 됩니다.
- 비차단 caveat 하나는, `super().__init__()`가 먼저 기본 `OnlinePredictor`들을 만들고 버린 뒤 subclass predictor를 다시 만들기 때문에 RNG를 한 번 더 소비한다는 점입니다. **이건 D-1의 불가능 사유는 아니고**, strict one-variable 비교를 원하면 control도 같은 harness로 돌리거나, 기존 predictor 상태를 복제/패치하는 식으로 맞추면 됩니다.

정리하면: **D-1은 언어/실행 경로상 가능**하고, 내가 Round 1에서 말한 "v2.py 무수정 subclass harness"는 코드 기준으로 유지 가능합니다.

### Q3 답변
만약 D-1이 막혔다면 A 구현은 매우 직선적입니다. 실제로는 내 Round 1의 A 공수 추정이 과했습니다.

A 구현 경로:
1. `Projects/Trading Value/scripts/v2.py`를 `scripts/v2_ablation.py` 또는 `scripts/oracle_rule2_ablation.py`로 복사
2. 상단 상수 `STATE_PATH`, `LOG_PATH`, `DASH_PORT`를 variant 전용 값으로 변경
3. 상수 하나 추가: `ENABLE_RULE2 = False`
4. `v2.py:302`의 `self._rebalance_memory()`를
   ```python
   if ENABLE_RULE2:
       self._rebalance_memory()
   ```
   로 변경
5. 필요하면 docstring / argparse description만 variant 이름에 맞게 수정

즉, A는 실제 코드 기준으로 **1개 호출부 gate + artifact 경로 분리**가 핵심입니다. 구현만 보면 A도 충분히 싸고 현실적입니다.

### Q4 답변
질문에 적힌 하이브리드, 즉 **"A의 포크 방식 + 파일명만 `oracle_rule2_ablation.py`"** 는 제 판단으로는 진짜 절충안이 아닙니다. 기술적 실익은 거의 전부 A이고, D의 핵심 장점인 **`v2.py` 실행 경로 재사용 / drift 최소화**는 사라집니다. 얻는 건 사실상 naming optics뿐입니다.

오히려 Charter 명명 이슈가 걱정이면 **D 구현 파일 자체를 `oracle_rule2_ablation.py`로 이름 짓는 것**이 더 낫습니다. 그 경우 이름은 맞추면서도 구현은 여전히 D입니다. 그래서 prompt가 말한 hybrid는 굳이 선택할 이유가 약합니다.

### 최종 결론
Position: **D**
Reasoning: `v2.py:605-625`, `714-723`, `841-879`를 보면 D-1은 실제로 성립합니다. 다만 내가 Round 1에서 본 A 공수는 높게 잡았고, 현실적으로는 A도 싸지만, `v2.py` 무수정과 drift 최소화라는 핵심 이점 때문에 최종 입장은 여전히 D입니다.

[POSITION: T2=D]
