# Loom API — Φ-5 Read-only Surface (v0)

> **rev**: v0 (2 슬롯 freeze + 3 슬롯 reserved)
> **Spec**: [PHASE-17-NATION-DC-3-P5R-SPEC.md](../PHASE-17-NATION-DC-3-P5R-SPEC.md) rev.2
> **Regression contract**: [PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md](../PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md)
> **Encoding**: utf-8

---

## 목적

Φ-5 (외교·전쟁·문명) 계층이 Φ-4 (Nation) 계층을 read-only consume하기 위한 type signature surface. mutation 금지 — 단방향 계약.

---

## v0 frozen slots (2)

- `nation.sovereignty` (← DC-1 SIS rev.2 `distribution.json` aggregate shape)
- `nation.charter_overlap` (← DC-2 CPCM rev.3 `SnapshotMetrics` keys mirror)

### `NationSovereignty` (4 properties)

| property | type | source |
|---|---|---|
| `dom_share` | `float` | SIS rev.2 |
| `member_share_per_faction` | `dict[str, float]` | SIS rev.2 |
| `conflict_pair_count` | `int` | SIS rev.2 |
| `cross_faction_lord_count` | `int` | SIS rev.2 |

### `NationCharterOverlap` (2 properties — CPCM JSON key mirror)

| property | type | source |
|---|---|---|
| `mean_jaccard` | `float` | CPCM rev.3 `SnapshotMetrics.mean_jaccard` |
| `pair_count` | `int` | CPCM rev.3 `SnapshotMetrics.pair_count` |

> **Step 3.5 Finding 1 정정**: rev.1의 `overlap_score` / `primitive_count` (CPCM 출력과 hidden coupling) → rev.2에서 `mean_jaccard` / `pair_count` (CPCM JSON key mirror)로 정합.

---

## Reserved (provisional, awaiting §3.7 closure)

다음 3 슬롯은 사전 승인되었으나(2026-05-07) **typed field로 노출되지 않음**. 각 컴포넌트의 §3.7 6단 closure 통과 후 별도 rev에서 추가:

- `nation.dissolution_history` (← **NDP** Nation Dissolution Path) — pre-approved, awaiting mechanism spec + cross-check
- `nation.lord_replacement_history` (← **LRT** Lord Replacement Trigger) — pre-approved, awaiting mechanism spec + cross-check
- `nation.federation_state` (← **FMR** Federation/Merge Resolver) — pre-approved, awaiting mechanism spec + cross-check

> 본 시점에 typed body slot으로 박지 않는 이유: 구조 굳음 회피 (PIPELINE-DRAFT.md F2 + DC-3 §1 v0 핵심 원칙 3).

---

## Direction contract (단방향 계약)

```
Φ-5 → Φ-4 → Φ-3 → Φ-2 → Φ-1
(read-only, no reverse mutation)
```

상위 계층은 하위를 읽기만. 하위 → 상위 mutate 금지. 본 surface는 mutation API를 일체 노출하지 않음.

---

## §1.0 DC-1 caveat 계승

`nation.sovereignty` body semantics는 **SIS 분위수 값(P50/P67/P75)을 fixed type으로 박지 않음**. type signature만 contract — runtime 값은 동적이며 §3.7 closure cycle을 거치며 변동 가능.

마찬가지로 `nation.charter_overlap`은 CPCM의 `0.7 = 수렴 후보` 같은 수치를 fixed value로 박지 않음 (DC-2 §1.0 + caveat 정신 정합).

---

## 사용 예시 (placeholder — 실제 값 freeze 금지)

```python
from loom.api import NationReadOnly

def consume_nation(n: NationReadOnly) -> None:
    # placeholder: 실제 값은 runtime dynamic
    sov = n.sovereignty
    overlap = n.charter_overlap

    dom = sov.dom_share                      # placeholder float
    pair_count = overlap.pair_count          # placeholder int
    mean_jac = overlap.mean_jaccard          # placeholder float
    # ...
```

> 위 placeholder는 surface 형태만 보여줌. 실제 값/임계는 §3.7 분위수 분석 결과를 따름.

---

## 회귀 contract reference

본 모듈은 interface declaration이므로 mechanism 무영향. 회귀 검증은 별도 권위 문서:

→ [`PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md`](../PHASE-17-NATION-PHASE3-REGRESSION-CONTRACT.md) §Tier 1 (workspace 실재 7종)

Phase 5 Package 진입 시 Tier 2 신규 4종 author (별도 사용자 게이트).

---

## 변경 이력

- **v0** (2026-05-07): 초안 author. DC-3 P5R rev.2 [필수] 7종 그대로 매핑. Step 3.5 Findings 1-2 정정 반영.
