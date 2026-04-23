# Phase 15 Fix: density_ratio 수식 정정

## 배경

500틱 통합 시뮬(2026-04-18 observe_phase15_stack.py)에서 관측된 이상:
```
  mirrordale  openness=0.373 density_ratio=2.6667
```

**density_ratio 2.67**은 밀도 의미상 불가능(0~1 범위여야 함).

## 근본 원인

[multi_tick_engine.py:744-776](Projects/personas/loom/core/multi_tick_engine.py#L744-L776) `_compute_community_metrics`:

```python
for rel in self.relationships.values():
    if rel.trust < 0.4:
        continue
    a_tid = territory_by_pid.get(rel.persona_a)
    b_tid = territory_by_pid.get(rel.persona_b)
    if a_tid == b_tid:
        intra_edges[a_tid] += 1       # 1 pair = 1 카운트
    else:
        inter_edges[a_tid] += 1
        inter_edges[b_tid] += 1       # 1 pair = 2 카운트 (양쪽 영지)
# ...
edge_count = intra + inter
density_ratio = edge_count / max(1, n * n)
```

**두 가지 문제**:
1. inter edges가 양쪽 영지에 2번 카운트. 이 영지 관점에선 `inter`가 실제 외부 pair의 2배.
2. 분모 `n*n`은 자기 자신과의 edge까지 포함하는 완전 그래프 + 외부 공간. undirected graph의 표준 density는 `edges / (n*(n-1)/2)`.

**복합 효과**: `edge_count`에 intra+inter 합치면 "이 영지 기준 전체 연결수"인데 이를 `n*n`으로 나누니 1 초과 가능.

## 수정

**의미 재정의**: `density_ratio`는 **단결도(intra density)**, `intra_inter_ratio`는 별도 metric. 혼용 금지.

### Step 1: `_compute_community_metrics` 수정

[multi_tick_engine.py:769-776](Projects/personas/loom/core/multi_tick_engine.py#L769-L776)

**Before**:
```python
        for tid in self.territories:
            n = node_counts[tid]
            intra = intra_edges[tid]
            inter = inter_edges[tid]
            edge_count = intra + inter
            metrics.append(CommunityMetrics(
                territory_id=tid,
                node_count=n,
                edge_count=edge_count,
                density_ratio=edge_count / max(1, n * n),
                intra_edges=intra,
                inter_edges=inter,
                intra_inter_ratio=intra / max(1, inter),
            ))
```

**After**:
```python
        for tid in self.territories:
            n = node_counts[tid]
            intra = intra_edges[tid]
            inter = inter_edges[tid]
            edge_count = intra + inter
            # undirected intra density: intra / C(n, 2)
            possible = max(1, n * (n - 1) // 2)
            density_ratio = min(1.0, intra / possible)
            metrics.append(CommunityMetrics(
                territory_id=tid,
                node_count=n,
                edge_count=edge_count,
                density_ratio=density_ratio,
                intra_edges=intra,
                inter_edges=inter,
                intra_inter_ratio=intra / max(1, inter),
            ))
```

### Step 2: density_warning threshold 재조정

[multi_tick_engine.py:~692](Projects/personas/loom/core/multi_tick_engine.py#L692)

**Before**: `if metric.density_ratio > 0.05:`
**After**: `if metric.density_ratio > 0.5:`

새 공식은 0~1 범위. 0.5는 "과반수 pair가 trust 연결"을 의미. 밀집 공동체 판정 기준으로 적절.

### Step 3: Phase 15-A `density_pressure` 재조정

[multi_tick_engine.py:~1451](Projects/personas/loom/core/multi_tick_engine.py#L1451) (또는 현재 구현 위치)

**Before**: `density_pressure = max(0.0, min(1.0, (density_ratio - 0.03) * 20.0))`
**After**: `density_pressure = max(0.0, min(1.0, (density_ratio - 0.3) * 2.5))`

새 공식: density_ratio 0.3~0.7을 0~1로 매핑. 중간값(0.5)에서 0.5, 포화점 0.7.

### Step 4: 테스트 업데이트

[test_phase15_collective_action.py:129-131](Projects/personas/loom/test_phase15_collective_action.py#L129-L131)

**Before**:
```python
    assert source_metric.inter_edges == 1
    assert source_metric.edge_count == 3
    assert abs(source_metric.density_ratio - (3 / (source_metric.node_count ** 2))) < 1e-9
```

**After**:
```python
    assert source_metric.inter_edges == 1
    assert source_metric.edge_count == 3
    n = source_metric.node_count
    possible = max(1, n * (n - 1) // 2)
    expected = min(1.0, source_metric.intra_edges / possible)
    assert abs(source_metric.density_ratio - expected) < 1e-9
```

[test_phase15_collective_action.py:~149](Projects/personas/loom/test_phase15_collective_action.py#L149)

테스트 T5 (또는 관련 assertion) 중 `density_ratio > 0.05`는 **새 threshold에 맞게** `density_ratio > 0.5` 또는 구체적 값으로 수정. 테스트 시나리오가 충분한 intra 연결을 만드는지 확인하고 assertion 조정.

[test_phase15a_market_openness.py:86](Projects/personas/loom/test_phase15a_market_openness.py#L86)

**Before**: `CommunityMetrics(tid, node_count=3, edge_count=1, density_ratio=0.08, ...)`
**After** (새 스케일 유지): `CommunityMetrics(tid, node_count=3, edge_count=3, density_ratio=0.8, intra_edges=3, inter_edges=0, intra_inter_ratio=3.0)` — density_pressure가 충분히 발동하도록.

T3 (density_ratio 높은 영지의 market_openness 하락) 테스트가 새 공식에서도 동일하게 통과하는지 확인. 필요 시 assertion 조정.

---

## 테스트 검증

```bash
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15_collective_action.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15a_market_openness.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase15c_job_diversity.py
C:\Users\haj\AppData\Local\Programs\Python\Python314\python.exe Projects/personas/loom/test_phase14b_snn_integration.py
```

모든 테스트 PASS 유지 + 통합 시뮬에서 `density_ratio ≤ 1.0` 보장.

---

## 설계 근거

1. **intra만 사용**: "공동체 단결도"의 직관적 의미. inter는 `intra_inter_ratio`로 별도 추적.
2. **C(n, 2) 분모**: undirected graph의 표준. 1이 최대 밀도(완전 그래프) 의미.
3. **clip [0, 1]**: 이론상 불가능하지만 정수 나눗셈 안전망.
4. **threshold 0.5**: 과반수 연결. 15-A density_pressure 공식과 조화.
5. **Phase 15-A 재조정**: 기존 threshold 0.03→0.3은 단결도 30% 이상을 밀집으로 본다는 뜻. 3인 영지면 intra ≥ 1이면 이미 0.33이라 민감도 확보.
