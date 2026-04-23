# Fix: test_phase12b_perf_npc.py — trade_bonus 반영

> **작성자**: Claude (리뷰)
> **구현자**: Codex
> **원인**: Phase 14에서 NPC 매도에 `trade_bonus = 1.0 + territory.policy.tax_rate * 0.5`를 도입. Phase 12-B 테스트가 보너스 없는 revenue를 기대하여 assert 실패.

---

## 변경 파일

1개: `Projects/personas/loom/test_phase12b_perf_npc.py`

---

## 현재 실패

```
assert sell["revenue"] == NPC_PRICES["material"]["sell"] * 5
AssertionError
```

line 82. Phase 14 이후 `_process_npc_shop()`의 NPC 매도 revenue에 `trade_bonus`가 곱해지므로 기대값이 달라졌다.

---

## 수정 내용

### 수정 1: line 82 — revenue assert를 trade_bonus 반영으로 변경

```python
# Before (line 82):
assert sell["revenue"] == NPC_PRICES["material"]["sell"] * 5

# After:
territory = engine.territories[engine.personas[pid].territory]
expected_bonus = 1.0 + territory.policy.tax_rate * 0.5
expected_revenue = NPC_PRICES["material"]["sell"] * 5 * expected_bonus
assert abs(sell["revenue"] - expected_revenue) < 1e-6, f"{sell['revenue']} != {expected_revenue}"
```

### 수정 2: trade_bonus 필드 존재 확인 추가

line 88 `assert "price_basis" in sell` 뒤에 추가:

```python
assert "trade_bonus" in sell
```

---

## 검증

```bash
cd Projects/personas/loom
py test_phase12b_perf_npc.py      # 5/5 PASS 필수
py test_economy_balance.py        # 6/6 PASS (회귀 확인)
```

---

## 금지

1. `_process_npc_shop()` 로직을 변경하지 마라 — 테스트만 수정
2. 다른 테스트 파일을 변경하지 마라
3. trade_bonus 계산 방식을 하드코딩하지 마라 — 엔진에서 실제 territory의 tax_rate를 읽어라
