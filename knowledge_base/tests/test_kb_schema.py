#!/usr/bin/env python3
"""
Automated Schema, Legal Compliance (CV 9368), Label Sync, & Engine Verification Suite.
Validates `knowledge_base/rules.json` against `knowledge_base/schemas/waste_rule_schema.json`,
asserts 1:1 parity with `knowledge_base/labels.txt`, verifies WCAG 2.1 AA stream colors,
and exercises `KnowledgeBaseEngine` lookups and Vietnamese search.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "knowledge_base"))

from kb_engine import KnowledgeBaseEngine  # noqa: E402

SCHEMA_PATH = REPO_ROOT / "knowledge_base" / "schemas" / "waste_rule_schema.json"
RULES_PATH = REPO_ROOT / "knowledge_base" / "rules.json"
LABELS_PATH = REPO_ROOT / "knowledge_base" / "labels.txt"

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
    "material_check",
    "infectious_check",
    "hazardous_handling",
}


def relative_luminance(hex_color: str) -> float:
    """Compute WCAG 2.1 relative luminance for #RRGGBB."""
    h = hex_color.lstrip("#")
    channels = [int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio_white(hex_color: str) -> float:
    """Contrast ratio of #FFFFFF foreground text against hex_color background."""
    lum_bg = relative_luminance(hex_color)
    return 1.05 / (lum_bg + 0.05)


def run_verification() -> int:
    print("======================================================================")
    print("   EcoSort Knowledge Base — CV 9368, WCAG & Engine Verification       ")
    print("======================================================================")

    for required_file in (SCHEMA_PATH, RULES_PATH, LABELS_PATH):
        if not required_file.is_file():
            print(f"[FAIL] Missing required file: {required_file}")
            return 1

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    kb = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    print("[PASS] Loaded rules.json, waste_rule_schema.json, and labels.txt.")

    try:
        import jsonschema  # type: ignore

        jsonschema.validate(instance=kb, schema=schema)
        print("[PASS] Validated rules.json via jsonschema (Draft 2020-12).")
    except ImportError:
        print("[INFO] jsonschema package not installed; running built-in strict validator.")
    except Exception as exc:
        print(f"[FAIL] jsonschema validation error: {exc}")
        return 1

    # 1. Stream definitions & WCAG 2.1 AA contrast >= 4.5:1 with white text
    assert kb.get("total_classes") == 20, "total_classes must be 20"
    streams = kb.get("streams", {})
    assert VALID_STREAMS.issubset(streams.keys()), "Missing mandatory streams"
    for stream_key, stream_meta in streams.items():
        hex_val = stream_meta["color_hex"]
        assert re.match(r"^#[0-9A-Fa-f]{6}$", hex_val), f"Invalid hex for {stream_key}"
        ratio = contrast_ratio_white(hex_val)
        assert ratio >= 4.5, f"Stream {stream_key} ({hex_val}) fails WCAG AA white text contrast: {ratio:.2f}:1"
    print("[PASS] Verified all stream colors pass WCAG 2.1 AA contrast (>= 4.5:1 with white text).")

    # 2. Rules array, 20-class bijection & labels.txt parity
    rules: list[dict[str, Any]] = kb.get("rules", [])
    assert len(rules) == 20, f"Expected 20 rules, found {len(rules)}"

    labels = [line.strip() for line in LABELS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(labels) == 20, f"Expected 20 lines in labels.txt, found {len(labels)}"

    clarification_count = 0
    engine = KnowledgeBaseEngine(RULES_PATH)

    for idx, rule in enumerate(rules):
        c_idx = rule["class_index"]
        item_id = rule["item_id"]
        assert c_idx == idx, f"Position {idx} has mismatched class_index={c_idx}"
        assert labels[idx] == item_id, f"labels.txt mismatch at index {idx}: {labels[idx]} != {item_id}"
        assert re.match(r"^[a-z0-9_]+$", item_id), f"Invalid item_id: {item_id}"
        assert rule["category_code"] in VALID_CATEGORIES
        assert rule["default_stream"] in VALID_STREAMS
        assert rule["condition"] in VALID_CONDITIONS

        state_rules = rule["state_rules"]
        if rule["requires_clarification"]:
            clarification_count += 1
            assert isinstance(rule["clarification_question_vi"], str) and len(rule["clarification_question_vi"]) >= 10
            assert len(state_rules) >= 2
            assert {b["is_clean"] for b in state_rules} == {True, False}
        else:
            assert rule["clarification_question_vi"] is None

        for branch in state_rules:
            assert branch["resolved_stream"] in VALID_STREAMS
            assert len(branch["legal_citation"]) >= 5
            assert 10 <= len(branch["tts_readout_vi"]) <= 180
            assert len(branch["actionable_instructions_vi"]) >= 10

        for is_clean_val in (True, False):
            for has_food_val in (True, False):
                resolved = engine.resolve_state(rule, is_clean=is_clean_val, has_food=has_food_val)
                assert resolved["resolved_stream"] in VALID_STREAMS

    print("[PASS] Verified 20 canonical classes (0..19) and 1:1 parity with labels.txt.")
    print(f"[PASS] Verified {clarification_count}/20 state-dependent classes (80/80 state lookups passed).")

    # 3. CV 9368 legal compliance assertions
    assert engine.lookup_by_id("ba_tra_ca_phe")["default_stream"] == "residual_waste"
    assert engine.lookup_by_id("vo_trung")["default_stream"] == "residual_waste"
    assert engine.lookup_by_id("la_chuoi_la_dong")["default_stream"] == "residual_waste"

    mask_rule = engine.lookup_by_id("khau_trang_y_te")
    assert engine.resolve_state(mask_rule, is_clean=True, has_food=False).get("is_hazardous_branch") is False
    assert engine.resolve_state(mask_rule, is_clean=False, has_food=False).get("is_hazardous_branch") is True

    shard_rule = engine.lookup_by_id("manh_gom_su_thuy_tinh_vo")
    assert engine.resolve_state(shard_rule, is_clean=True, has_food=False)["resolved_stream"] == "recyclable"
    assert engine.resolve_state(shard_rule, is_clean=False, has_food=False)["resolved_stream"] == "residual_waste"
    print("[PASS] Verified CV 9368/BTNMT-KSONMT legal mappings (3.3.1, 3.1.1, 1.4.3 vs 3.3.5).")

    # 4. Vietnamese search tests (diacritic + unsigned alias matching)
    assert any(r["item_id"] == "rau_cu_qua_thua" for r in engine.search("vỏ chuối"))
    assert any(r["item_id"] == "rau_cu_qua_thua" for r in engine.search("vo chuoi"))
    assert any(r["item_id"] == "ba_tra_ca_phe" for r in engine.search("bã cà phê"))
    assert any(r["item_id"] == "hop_sua_giay" for r in engine.search("hộp sữa"))
    assert any(r["item_id"] == "manh_gom_su_thuy_tinh_vo" for r in engine.search("sành sứ"))
    print("[PASS] Verified Vietnamese diacritic and unsigned search over common_names aliases.")

    print("======================================================================")
    print("ALL KNOWLEDGE BASE CHECKS PASSED (EXIT CODE 0)")
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
