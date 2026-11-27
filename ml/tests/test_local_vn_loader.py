#!/usr/bin/env python3
"""Unit and E2E split verification tests for Option-B local_vn dataset loading."""

from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml" / "src" / "data"))

import bootstrap_dataset  # noqa: E402
import group_split  # noqa: E402


def _write_solid_image(path: Path, fmt: str = "JPEG") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 32), color=(46, 125, 50)).save(path, format=fmt)


class TestLocalVnLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.labels = bootstrap_dataset.load_canonical_labels()

    def test_option_b_subfolder_walk_filters_and_isolates_object_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vn_dir = Path(tmp) / "local_vn"
            # Valid JPEGs + 1 corrupt .jpg + 1 .heic in yen_obj01
            for idx in range(3):
                _write_solid_image(vn_dir / "hop_sua_giay" / "yen_obj01" / f"IMG_{idx}.jpg")
            (vn_dir / "hop_sua_giay" / "yen_obj01" / "corrupt.jpg").write_bytes(b"not-a-jpeg")
            (vn_dir / "hop_sua_giay" / "yen_obj01" / "iphone.heic").write_bytes(b"heic")
            # Empty leaf folder should be ignored silently
            (vn_dir / "hop_sua_giay" / "yen_obj02").mkdir(parents=True, exist_ok=True)
            # Same leaf folder name across a different class must get distinct object_id
            for idx in range(2):
                _write_solid_image(vn_dir / "coc_nhua_tra_sua" / "yen_obj01" / f"shot_{idx}.png", fmt="PNG")

            records = bootstrap_dataset.collect_local_vn_samples(
                self.labels,
                local_vn_dir=vn_dir,
                repo_root=Path(tmp),
            )
            self.assertEqual(len(records), 5)

            milk_recs = [r for r in records if r.item_id == "hop_sua_giay"]
            cup_recs = [r for r in records if r.item_id == "coc_nhua_tra_sua"]
            self.assertEqual(len(milk_recs), 3)
            self.assertEqual(len(cup_recs), 2)
            self.assertEqual(milk_recs[0].object_id, "vn_hop_sua_giay_yen_obj01")
            self.assertEqual(cup_recs[0].object_id, "vn_coc_nhua_tra_sua_yen_obj01")
            self.assertNotEqual(milk_recs[0].object_id, cup_recs[0].object_id)
            self.assertEqual(milk_recs[0].session_id, "vn_yen")

    def test_option_a_flat_file_backwards_compatibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vn_dir = Path(tmp) / "local_vn"
            _write_solid_image(vn_dir / "chai_nhua_pet" / "nam__obj03__sess02.jpg")
            records = bootstrap_dataset.collect_local_vn_samples(
                self.labels,
                local_vn_dir=vn_dir,
                repo_root=Path(tmp),
            )
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].object_id, "vn_chai_nhua_pet_obj03")
            self.assertEqual(records[0].session_id, "sess02")
            self.assertEqual(records[0].source, "local_vn")

    def test_select_replaced_classes_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vn_dir = Path(tmp) / "local_vn"
            for obj_i in range(1, 11):
                _write_solid_image(vn_dir / "hop_sua_giay" / f"yen_obj{obj_i:02d}" / "a.jpg")
            for obj_i in range(1, 4):
                _write_solid_image(vn_dir / "la_chuoi_la_dong" / f"linh_obj{obj_i:02d}" / "a.jpg")

            records = bootstrap_dataset.collect_local_vn_samples(
                self.labels,
                local_vn_dir=vn_dir,
                repo_root=Path(tmp),
            )
            replaced = bootstrap_dataset.select_replaced_classes(records, min_vn_objects=8)
            self.assertEqual(replaced, {"hop_sua_giay"})

    def test_e2e_group_shuffle_split_zero_leakage_on_option_b(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            vn_dir = tmp_path / "local_vn"
            for item_id in self.labels:
                for obj_i in range(1, 11):
                    for ang_i in range(3):
                        _write_solid_image(
                            vn_dir / item_id / f"yen_obj{obj_i:02d}" / f"ang_{ang_i}.jpg"
                        )

            records = bootstrap_dataset.collect_local_vn_samples(
                self.labels,
                local_vn_dir=vn_dir,
                repo_root=tmp_path,
            )
            self.assertEqual(len(records), 600)

            manifest = tmp_path / "manifest.csv"
            with manifest.open("w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["filepath", "class_index", "item_id", "object_id", "session_id", "source"])
                for r in records:
                    writer.writerow([r.filepath, r.class_index, r.item_id, r.object_id, r.session_id, r.source])

            report = group_split.run_group_split(
                manifest_path=manifest,
                splits_dir=tmp_path / "splits",
                report_path=tmp_path / "split_verification.json",
            )
            self.assertTrue(report["zero_leakage_verified"])
            self.assertEqual(report["overlap_train_val"], 0)
            self.assertEqual(report["overlap_train_test"], 0)
            self.assertEqual(report["overlap_val_test"], 0)
            self.assertEqual(report["classes_covered"], 20)
            self.assertEqual(report["total_images"], 600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
