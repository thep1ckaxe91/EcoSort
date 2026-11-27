#!/usr/bin/env python3
"""Stratified object-level GroupShuffleSplit (70/15/15) with zero-leakage assertions."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from sklearn.model_selection import GroupShuffleSplit

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "ml" / "datasets" / "manifest.csv"
SPLITS_DIR = REPO_ROOT / "ml" / "datasets" / "splits"
REPORT_PATH = REPO_ROOT / "ml" / "reports" / "split_verification.json"


@dataclass(frozen=True)
class ManifestEntry:
    filepath: str
    class_index: int
    item_id: str
    object_id: str
    session_id: str
    source: str


def load_manifest(path: Path) -> list[ManifestEntry]:
    """Load dataset manifest CSV into typed entries."""
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = [
            ManifestEntry(
                filepath=row["filepath"],
                class_index=int(row["class_index"]),
                item_id=row["item_id"],
                object_id=row["object_id"],
                session_id=row["session_id"],
                source=row["source"],
            )
            for row in csv.DictReader(f)
        ]
    return rows


def write_split_csv(path: Path, entries: list[ManifestEntry]) -> None:
    """Persist one split CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filepath", "class_index", "item_id", "object_id", "session_id", "source"])
        for e in entries:
            writer.writerow([e.filepath, e.class_index, e.item_id, e.object_id, e.session_id, e.source])


def run_group_split(
    manifest_path: Path = MANIFEST_PATH,
    splits_dir: Path = SPLITS_DIR,
    report_path: Path = REPORT_PATH,
    seed: int = 42,
) -> dict[str, object]:
    """Split manifest 70/15/15 per class grouped strictly by object_id."""
    entries = load_manifest(manifest_path)
    if not entries:
        raise RuntimeError(f"Manifest {manifest_path} is empty.")

    by_class: dict[int, list[ManifestEntry]] = {}
    for entry in entries:
        by_class.setdefault(entry.class_index, []).append(entry)

    train_all: list[ManifestEntry] = []
    val_all: list[ManifestEntry] = []
    test_all: list[ManifestEntry] = []

    for class_idx in sorted(by_class):
        cls_entries = by_class[class_idx]
        indices = np.arange(len(cls_entries))
        groups = np.array([e.object_id for e in cls_entries])

        # Stage 1: 70% Train vs 30% Temp
        gss1 = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=seed + class_idx)
        tr_idx, tmp_idx = next(gss1.split(indices, groups=groups))

        # Stage 2: Split 30% Temp evenly -> 15% Val, 15% Test
        tmp_entries = [cls_entries[i] for i in tmp_idx]
        tmp_indices = np.arange(len(tmp_entries))
        tmp_groups = np.array([e.object_id for e in tmp_entries])
        gss2 = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=seed + 100 + class_idx)
        va_idx, te_idx = next(gss2.split(tmp_indices, groups=tmp_groups))

        train_all.extend(cls_entries[i] for i in tr_idx)
        val_all.extend(tmp_entries[i] for i in va_idx)
        test_all.extend(tmp_entries[i] for i in te_idx)

    write_split_csv(splits_dir / "train.csv", train_all)
    write_split_csv(splits_dir / "val.csv", val_all)
    write_split_csv(splits_dir / "test.csv", test_all)

    report = verify_splits(splits_dir)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def verify_splits(splits_dir: Path = SPLITS_DIR) -> dict[str, object]:
    """Assert zero object_id overlap and full 20-class coverage across Train/Val/Test."""
    train = load_manifest(splits_dir / "train.csv")
    val = load_manifest(splits_dir / "val.csv")
    test = load_manifest(splits_dir / "test.csv")

    train_objs = {e.object_id for e in train}
    val_objs = {e.object_id for e in val}
    test_objs = {e.object_id for e in test}

    assert len(train_objs & val_objs) == 0, "Data leakage: train/val object_id overlap!"
    assert len(train_objs & test_objs) == 0, "Data leakage: train/test object_id overlap!"
    assert len(val_objs & test_objs) == 0, "Data leakage: val/test object_id overlap!"

    expected_classes = set(range(20))
    assert {e.class_index for e in train} == expected_classes, "Missing classes in train split"
    assert {e.class_index for e in val} == expected_classes, "Missing classes in val split"
    assert {e.class_index for e in test} == expected_classes, "Missing classes in test split"

    total = len(train) + len(val) + len(test)
    report: dict[str, object] = {
        "total_images": total,
        "train_images": len(train),
        "val_images": len(val),
        "test_images": len(test),
        "train_ratio": round(len(train) / total, 4),
        "val_ratio": round(len(val) / total, 4),
        "test_ratio": round(len(test) / total, 4),
        "unique_objects_train": len(train_objs),
        "unique_objects_val": len(val_objs),
        "unique_objects_test": len(test_objs),
        "overlap_train_val": 0,
        "overlap_train_test": 0,
        "overlap_val_test": 0,
        "classes_covered": 20,
        "zero_leakage_verified": True,
    }
    print("[PASS] GroupShuffleSplit verified (0% object_id leakage, all 20 classes covered):")
    print(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="EcoSort Object-Level GroupShuffleSplit")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing split CSVs")
    args = parser.parse_args()

    if args.verify_only:
        verify_splits()
    else:
        run_group_split()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
