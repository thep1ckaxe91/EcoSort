"""Freeze and re-check the real-Vietnam test list (source == local_vn rows of the v2 test split).

The frozen list is the only test set used for the v1-vs-v2 comparison table. It is derived
from the object-level split, never edited by hand, and protected by a content fingerprint.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from ecosort_ml.artifacts import REPO_ROOT
from ecosort_ml.evalkit import (
    SPLIT_FIELDS,
    EvalDataError,
    dump_json,
    fingerprint_rows,
    load_labels,
    read_rows,
    repo_relative,
    validate_eval_rows,
    write_rows,
)

VN_SOURCE = "local_vn"


def _vn_classes_in_splits(splits_dir: Path) -> dict[str, set[str]]:
    """item_id -> set of split names that contain local_vn rows of that class."""
    seen: dict[str, set[str]] = defaultdict(set)
    for split in ("train", "val", "test"):
        for r in read_rows(splits_dir / f"{split}.csv"):
            if r["source"] == VN_SOURCE:
                seen[r["item_id"]].add(split)
    return seen


def freeze_vn_test(
    splits_dir: Path,
    out_csv: Path,
    manifest_path: Path,
    repo_root: Path = REPO_ROOT,
    force: bool = False,
) -> dict[str, object]:
    """Filter test.csv to local_vn rows, write the frozen CSV and its fingerprint manifest."""
    labels = load_labels()
    test_rows = read_rows(splits_dir / "test.csv")
    vn_rows = sorted((r for r in test_rows if r["source"] == VN_SOURCE), key=lambda r: r["filepath"])
    if not vn_rows:
        raise EvalDataError(
            f"No source=={VN_SOURCE!r} rows in {splits_dir / 'test.csv'}; "
            "the real-VN test list would be empty. Add VN photos, rebuild the manifest and re-split."
        )
    validate_eval_rows(vn_rows, repo_root)
    fp, _ = fingerprint_rows(vn_rows, repo_root)

    if manifest_path.is_file() and not force:
        import json

        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") != fp:
            raise EvalDataError(
                f"A different frozen VN test list already exists ({manifest_path}). "
                "Refusing to overwrite a frozen test set; pass --force only if the split was intentionally rebuilt."
            )

    per_class: dict[str, dict[str, object]] = {}
    for r in vn_rows:
        entry = per_class.setdefault(r["item_id"], {"images": 0, "objects": set(), "sessions": set()})
        entry["images"] = int(entry["images"]) + 1
        entry["objects"].add(r["object_id"])  # type: ignore[union-attr]
        entry["sessions"].add(r["session_id"])  # type: ignore[union-attr]

    vn_classes = _vn_classes_in_splits(splits_dir)
    absent = sorted(c for c in vn_classes if c not in per_class)

    write_rows(out_csv, vn_rows, SPLIT_FIELDS)
    manifest = {
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_split": repo_relative(splits_dir / "test.csv", repo_root),
        "frozen_csv": repo_relative(out_csv, repo_root),
        "fingerprint": fp,
        "fingerprint_definition": "sha256 of sorted 'filepath|class_index|sha256(file bytes)' lines",
        "images": len(vn_rows),
        "objects": len({r["object_id"] for r in vn_rows}),
        "labels_present": [lbl for lbl in labels if lbl in per_class],
        "vn_classes_absent_from_test": absent,
        "per_class": {
            k: {"images": v["images"], "objects": len(v["objects"]), "sessions": sorted(v["sessions"])}  # type: ignore[arg-type]
            for k, v in sorted(per_class.items(), key=lambda kv: labels.index(kv[0]))
        },
        "object_ids": sorted({r["object_id"] for r in vn_rows}),
    }
    dump_json(manifest_path, manifest)
    return manifest


def check_frozen_vn_test(
    frozen_csv: Path,
    manifest_path: Path,
    splits_dir: Path | None = None,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[dict[str, str]], dict[str, object]]:
    """Return the frozen rows after proving they still match the manifest (and the v2 test split)."""
    import json

    if not manifest_path.is_file():
        raise EvalDataError(
            f"Frozen VN test manifest missing: {manifest_path}. Run ml/src/evaluation/freeze_vn_test.py first."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = read_rows(frozen_csv)
    validate_eval_rows(rows, repo_root)
    fp, _ = fingerprint_rows(rows, repo_root)
    if fp != manifest.get("fingerprint"):
        raise EvalDataError(
            f"Frozen VN test list changed: fingerprint {fp[:12]} != manifest {str(manifest.get('fingerprint'))[:12]}"
        )
    if splits_dir is not None:
        test_paths = {r["filepath"] for r in read_rows(splits_dir / "test.csv")}
        leaked = [r["filepath"] for r in rows if r["filepath"] not in test_paths]
        if leaked:
            raise EvalDataError(f"{len(leaked)} frozen VN row(s) are no longer in {splits_dir / 'test.csv'}")
        train_val_objs = {
            r["object_id"] for s in ("train", "val") for r in read_rows(splits_dir / f"{s}.csv")
        }
        overlap = sorted({r["object_id"] for r in rows} & train_val_objs)
        if overlap:
            raise EvalDataError(f"Frozen VN test objects also appear in train/val: {overlap[:5]}")
    return rows, manifest
