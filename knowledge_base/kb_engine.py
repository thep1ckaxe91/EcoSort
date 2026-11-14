#!/usr/bin/env python3
"""
Deterministic State-Aware Knowledge Base Reference Engine for EcoSort.
Provides O(1) class lookup, (is_clean, has_food) state resolution, and
diacritic-aware Vietnamese offline search across all 20 canonical classes.
"""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

DEFAULT_RULES_PATH = Path(__file__).resolve().parent / "rules.json"


def strip_vietnamese_diacritics(text: str) -> str:
    """Normalize Vietnamese text to lowercase ASCII without tone marks."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return stripped.replace("đ", "d")


def has_vietnamese_diacritics(text: str) -> bool:
    """Return True if query contains explicit Vietnamese tone/diacritic marks."""
    return strip_vietnamese_diacritics(text) != text.lower().replace("đ", "d")


class KnowledgeBaseEngine:
    """In-memory index over EcoSort's 20-class state-aware rules.json."""

    def __init__(self, rules_path: Path = DEFAULT_RULES_PATH) -> None:
        self.data: dict[str, Any] = json.loads(rules_path.read_text(encoding="utf-8"))
        self.streams: dict[str, dict[str, str]] = self.data["streams"]
        self.rules: list[dict[str, Any]] = self.data["rules"]
        self._by_index: dict[int, dict[str, Any]] = {r["class_index"]: r for r in self.rules}
        self._by_id: dict[str, dict[str, Any]] = {r["item_id"]: r for r in self.rules}

    def lookup_by_index(self, class_index: int) -> dict[str, Any]:
        """Return rule entry for TFLite output class_index (0..19)."""
        if class_index not in self._by_index:
            raise KeyError(f"Unknown class_index={class_index} (expected 0..19)")
        return self._by_index[class_index]

    def lookup_by_id(self, item_id: str) -> dict[str, Any]:
        """Return rule entry for canonical item_id."""
        if item_id not in self._by_id:
            raise KeyError(f"Unknown item_id={item_id!r}")
        return self._by_id[item_id]

    @staticmethod
    def resolve_state(rule: dict[str, Any], is_clean: bool, has_food: bool) -> dict[str, Any]:
        """Resolve exact state branch given (is_clean, has_food)."""
        branches: list[dict[str, Any]] = rule["state_rules"]
        if not rule["requires_clarification"] or len(branches) == 1:
            return branches[0]

        for branch in branches:
            if branch["is_clean"] == is_clean and branch["has_food"] == has_food:
                return branch

        for branch in branches:
            if branch["is_clean"] == is_clean:
                return branch

        raise LookupError(
            f"No matching state branch for item_id={rule['item_id']} "
            f"with is_clean={is_clean}, has_food={has_food}"
        )

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Search rules by Vietnamese or English common names/aliases.
        - If user types diacritics (e.g. 'vỏ chuối'), match accented text across ALL common_names.
        - If user types unsigned ASCII (e.g. 'vo chuoi'), match normalized ASCII across ALL common_names.
        """
        cleaned = query.strip()
        if not cleaned:
            return list(self.rules)

        use_exact_marks = has_vietnamese_diacritics(cleaned)
        tokens = (cleaned.lower() if use_exact_marks else strip_vietnamese_diacritics(cleaned)).split()

        matches: list[dict[str, Any]] = []
        for rule in self.rules:
            all_names = rule["common_names"]["vi"] + rule["common_names"]["en"] + [rule["item_id"]]
            haystack = " ".join(all_names).lower()
            if not use_exact_marks:
                haystack = strip_vietnamese_diacritics(haystack)
            if all(tok in haystack for tok in tokens):
                matches.append(rule)
        return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="EcoSort Knowledge Base CLI query tool")
    parser.add_argument("--query", "-q", type=str, help="Search waste item by Vietnamese/English name")
    parser.add_argument("--index", "-i", type=int, help="Lookup by TFLite class_index (0..19)")
    parser.add_argument("--clean", action="store_true", help="Set is_clean=True for state resolution")
    parser.add_argument("--food", action="store_true", help="Set has_food=True for state resolution")
    args = parser.parse_args()

    engine = KnowledgeBaseEngine()

    if args.index is not None:
        rule = engine.lookup_by_index(args.index)
        branch = engine.resolve_state(rule, is_clean=args.clean, has_food=args.food)
        print(json.dumps({"item_id": rule["item_id"], "resolved": branch}, ensure_ascii=False, indent=2))
        return 0

    if args.query is not None:
        hits = engine.search(args.query)
        summary = [
            {
                "class_index": r["class_index"],
                "item_id": r["item_id"],
                "primary_name_vi": r["common_names"]["vi"][0],
                "default_stream": r["default_stream"],
                "requires_clarification": r["requires_clarification"],
            }
            for r in hits
        ]
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
