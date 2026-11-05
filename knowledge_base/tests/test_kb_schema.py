#!/usr/bin/env python3
"""
Automated Schema & State-Aware Logic Verification Suite for EcoSort Knowledge Base.
Validates `knowledge_base/rules.json` against `knowledge_base/schemas/waste_rule_schema.json`
and tests the deterministic (is_clean, has_food) state resolution engine across all 20 classes.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "knowledge_base" / "schemas" / "waste_rule_schema.json"
RULES_PATH = REPO_ROOT / "knowledge_base" / "rules.json"

VALID_STREAMS = {"recyclable", "food_waste", "residual_waste"}
VALID_CATEGORIES = {
    "plastic",
    "metal",
    "paper",
    "glass",
    "organic",
    "composite",
    "textile_medical",
    "ceramic",
    "hazardous",
}
VALID_CONDITIONS = {
    "none",
    "cleanliness_check",
    "food_separation_check",
    "hazardous_handling",
}


def resolve_state_branch(rule: dict[str, Any], is_clean: bool, has_food: bool) -> dict[str, Any]:
    """Deterministic state-aware lookup given (is_clean, has_food)."""
    state_rules: list[dict[str, Any]] = rule["state_rules"]
    if not rule["requires_clarification"] or len(state_rules) == 1:
        return state_rules[0]

    # Exact match on (is_clean, has_food)
    for branch in state_rules:
        if branch["is_clean"] == is_clean and branch["has_food"] == has_food:
            return branch

    # Fallback match on primary cleanliness flag
    for branch in state_rules:
        if branch["is_clean"] == is_clean:
            return branch

    raise LookupError(
        f"No matching state branch for item_id={rule['item_id']} "
        f"with is_clean={is_clean}, has_food={has_food}"
    )


def run_verification() -> int:
    print("======================================================================")
    print("   EcoSort Knowledge Base — Schema & State-Aware Verification Suite   ")
    print("======================================================================")

    if not SCHEMA_PATH.is_file():
        print(f"[FAIL] Missing schema file: {SCHEMA_PATH}")
        return 1
    if not RULES_PATH.is_file():
        print(f"[FAIL] Missing rules file: {RULES_PATH}")
        return 1

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    kb = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    print("[PASS] Loaded JSON files without syntax errors.")

    # Optional jsonschema library check if present in local environment
    try:
        import jsonschema  # type: ignore

        jsonschema.validate(instance=kb, schema=schema)
        print("[PASS] Validated rules.json via jsonschema (Draft 2020-12).")
    except ImportError:
        print("[INFO] jsonschema package not installed; running strict built-in structural validator.")
    except Exception as exc:
        print(f"[FAIL] jsonschema validation error: {exc}")
        return 1

    # 1. Top-level metadata validation
    assert kb.get("total_classes") == 20, "total_classes must be 20"
    assert set(kb.get("streams", {}).keys()) == VALID_STREAMS, "Invalid streams dictionary keys"
    for stream_key, stream_meta in kb["streams"].items():
        assert re.match(r"^#[0-9A-Fa-f]{6}$", stream_meta["color_hex"]), f"Invalid hex for {stream_key}"
    print("[PASS] Verified 3 statutory waste streams (recyclable, food_waste, residual_waste).")

    # 2. Rules array & 20-class bijection
    rules: list[dict[str, Any]] = kb.get("rules", [])
    assert len(rules) == 20, f"Expected exactly 20 rules, found {len(rules)}"

    seen_indices: set[int] = set()
    seen_ids: set[str] = set()
    clarification_count = 0

    for idx, rule in enumerate(rules):
        c_idx = rule["class_index"]
        item_id = rule["item_id"]
        assert c_idx == idx, f"Rule at position {idx} has mismatched class_index={c_idx}"
        assert c_idx not in seen_indices, f"Duplicate class_index={c_idx}"
        assert item_id not in seen_ids, f"Duplicate item_id={item_id}"
        assert re.match(r"^[a-z0-9_]+$", item_id), f"Invalid item_id format: {item_id}"
        seen_indices.add(c_idx)
        seen_ids.add(item_id)

        assert rule["category_code"] in VALID_CATEGORIES, f"Invalid category_code in {item_id}"
        assert rule["default_stream"] in VALID_STREAMS, f"Invalid default_stream in {item_id}"
        assert rule["condition"] in VALID_CONDITIONS, f"Invalid condition in {item_id}"
        assert isinstance(rule["requires_clarification"], bool)
        assert isinstance(rule["is_hazardous"], bool)

        names_vi = rule["common_names"]["vi"]
        names_en = rule["common_names"]["en"]
        assert len(names_vi) >= 1 and len(names_en) >= 1, f"Empty common_names in {item_id}"

        state_rules = rule["state_rules"]
        assert len(state_rules) >= 1, f"Empty state_rules in {item_id}"

        if rule["requires_clarification"]:
            clarification_count += 1
            q_vi = rule["clarification_question_vi"]
            assert isinstance(q_vi, str) and len(q_vi) >= 10, f"Missing clarification_question_vi in {item_id}"
            assert len(state_rules) >= 2, f"Clarification item {item_id} must have >= 2 state branches"
            clean_flags = {b["is_clean"] for b in state_rules}
            assert clean_flags == {True, False}, f"{item_id} must cover both is_clean=True and is_clean=False"
        else:
            assert rule["clarification_question_vi"] is None, f"Non-clarification item {item_id} must have null question"

        for branch in state_rules:
            assert isinstance(branch["is_clean"], bool), f"is_clean must be bool in {item_id}"
            assert isinstance(branch["has_food"], bool), f"has_food must be bool in {item_id}"
            assert branch["resolved_stream"] in VALID_STREAMS, f"Invalid resolved_stream in {item_id}"
            assert 10 <= len(branch["tts_readout_vi"]) <= 180, f"TTS readout length out of bounds in {item_id}"
            assert len(branch["actionable_instructions_vi"]) >= 10, f"Instructions too short in {item_id}"

        # 3. Exhaustive truth-table resolution test across all 4 (is_clean, has_food) combinations
        for is_clean_val in (True, False):
            for has_food_val in (True, False):
                resolved = resolve_state_branch(rule, is_clean=is_clean_val, has_food=has_food_val)
                assert resolved["resolved_stream"] in VALID_STREAMS

    print(f"[PASS] Verified all 20 canonical classes (0..19) with zero index gaps or duplicate IDs.")
    print(f"[PASS] Verified {clarification_count}/20 state-dependent classes with (is_clean, has_food) rules.")
    print("[PASS] Exhaustive truth-table simulation (20 classes x 4 state combinations = 80 lookups) succeeded.")
    print("======================================================================")
    print("ALL KNOWLEDGE BASE CHECKS PASSED (EXIT CODE 0)")
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
