import ast
import sys


src = open("core/multi_tick_engine.py", encoding="utf-8").read()
tree = ast.parse(src)

EXPECT = {
    "_compute_affiliation_tick": 60,
    "_uprising_trigger": 50,
    "_respawn_faction_tick": 155,
    "_change_persona_faction": 40,
    "tick": 0,
    "_record_cross_faction_lord_pair_events": 90,
}

errs = []
helper_node = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name in EXPECT:
        if node.name == "_record_cross_faction_lord_pair_events":
            helper_node = node
        if EXPECT[node.name] == 0:
            continue
        span = node.end_lineno - node.lineno
        if span > EXPECT[node.name]:
            errs.append(f"{node.name}: span {span} > expected {EXPECT[node.name]}")

helper_names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
required_helpers = {"_record_cross_faction_lord_pair_events"}
missing = required_helpers - helper_names
if missing:
    errs.append(f"missing required helpers: {sorted(missing)}")

def _verify_v3_helper(node: ast.FunctionDef) -> None:
    body_str = "\n".join(ast.unparse(stmt) for stmt in node.body)

    # 1. event_log iteration (territories iteration 제거 확인)
    assert "self.event_log" in body_str, "v3 helper must iterate self.event_log"

    # 1.5 helper body 안에 self.territories.values() 호출 부재
    for call_node in ast.walk(node):
        if (
            isinstance(call_node, ast.Call)
            and isinstance(call_node.func, ast.Attribute)
            and call_node.func.attr == "values"
            and isinstance(call_node.func.value, ast.Attribute)
            and call_node.func.value.attr == "territories"
            and isinstance(call_node.func.value.value, ast.Name)
            and call_node.func.value.value.id == "self"
        ):
            raise AssertionError(
                "v3 helper body must not call self.territories.values(); "
                "lord_to_factions must be built from event_log"
            )

    # 2. uprising_leader_snn_snapshot 이벤트 필터
    assert "uprising_leader_snn_snapshot" in body_str, (
        "v3 helper must filter uprising_leader_snn_snapshot events"
    )

    # 3. top_lord_id / fid 필드 사용
    assert "top_lord_id" in body_str, "missing PROBE top_lord_id field"
    assert "fid" in body_str, "missing PROBE fid field"

    # 4. definition payload 필드 명문장
    assert "probe_top_lord_id_accumulated" in body_str, (
        "missing v3 definition payload"
    )

    # 5. v2 풍부 상태 유지 검증
    assert "_cfl_pair_state" in body_str, "missing v2 state tracking"
    assert "first_seen_tick" in body_str, "missing v2 first_seen_tick tracking"
    assert "duration_ticks" in body_str, "missing v2 duration_ticks tracking"
    assert "collapse_reason" in body_str, "missing v2 H5a/b/c classification"
    assert "lord_persona_missing" in body_str, "missing H5c classification"
    assert "lord_id_replaced" in body_str, "missing H5b classification"
    assert "faction_consolidated" in body_str, "missing H5a classification"

    # 6. dict 기반 emit 패턴 확인 (rev.0 잘못된 패턴 제거)
    assert "_record_event(" not in body_str, "rev.0 _record_event pattern remains"
    assert "self._events" not in body_str, "rev.0 self._events pattern remains"

if helper_node is not None:
    try:
        _verify_v3_helper(helper_node)
    except AssertionError as exc:
        errs.append(str(exc))

if errs:
    sys.exit("\n".join(errs))
print("OK")
