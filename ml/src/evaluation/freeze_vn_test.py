#!/usr/bin/env python3
"""Freeze the real-VN test list from the v2 object-level split (or --check that it is unchanged).

    ml/.venv/bin/python ml/src/evaluation/freeze_vn_test.py          # after group_split.py --model-version v2
    ml/.venv/bin/python ml/src/evaluation/freeze_vn_test.py --check  # before training / comparing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ml" / "src"))

from ecosort_ml.artifacts import artifact_paths  # noqa: E402
from ecosort_ml.evalkit import EvalDataError  # noqa: E402
from ecosort_ml.vn_test import check_frozen_vn_test, freeze_vn_test  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    v2 = artifact_paths("v2", REPO_ROOT)
    parser = argparse.ArgumentParser(description="Freeze / check the real-VN test list")
    parser.add_argument("--splits-dir", type=Path, default=v2.splits_dir)
    parser.add_argument("--out-csv", type=Path, default=v2.test_vn_csv)
    parser.add_argument("--manifest", type=Path, default=v2.test_vn_manifest)
    parser.add_argument("--check", action="store_true", help="only verify the frozen list against its manifest")
    parser.add_argument("--force", action="store_true", help="overwrite a different existing frozen list")
    args = parser.parse_args(argv)
    try:
        if args.check:
            rows, manifest = check_frozen_vn_test(args.out_csv, args.manifest, args.splits_dir, REPO_ROOT)
            print(f"[PASS] Frozen VN test unchanged: {len(rows)} images, fingerprint {str(manifest['fingerprint'])[:12]}")
        else:
            manifest = freeze_vn_test(args.splits_dir, args.out_csv, args.manifest, REPO_ROOT, force=args.force)
            summary = {k: manifest[k] for k in ("images", "objects", "labels_present", "vn_classes_absent_from_test")}
            print("[PASS] Froze real-VN test list:")
            print(json.dumps(summary, indent=2, ensure_ascii=False))
            if manifest["vn_classes_absent_from_test"]:
                print("[WARN] VN classes with no object in test - collect more independent objects for them.")
    except EvalDataError as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
