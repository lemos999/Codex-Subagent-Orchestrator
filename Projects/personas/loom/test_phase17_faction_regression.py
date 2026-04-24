"""Wrapper so `test_phase17_faction_*.py` covers the existing faction regression suite."""

from test_phase17_faction import (
    test_d1_faction_dataclass_contract,
    test_d2_persona_and_innerworld_faction_fields,
    test_d3_change_persona_faction_and_cooldown,
    test_d3_change_persona_faction_rejects_unknown_inputs,
    test_d4_affiliation_kernel_updates_innerworld_scores,
    test_d5_commit_loop_respects_thresholds_and_cooldown,
    test_d6_founder_seed_generator_is_deterministic,
    test_d7_territory_projection_uses_majority_and_hysteresis,
    test_d8_faction_ssot_write_is_whitelisted,
    test_d9_faction_telemetry_applies_expected_biases,
    test_d10_handoff_api_shapes_and_empty_cases,
    test_d11_adjacency_helpers_cover_radius_and_cache_copy,
)
