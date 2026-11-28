#!/usr/bin/env python3
"""Tests for the issue #15 v2 pipeline: v1/v2 output isolation, strict v2 verifier, frozen VN test,
v1-vs-v2 comparison and local_vn QA. Runs without TensorFlow (TFLite is replaced by fake runners;
a stub module is injected only if TensorFlow is not installed)."""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
for sub in ("ml/src", "ml/src/data", "ml/src/training", "ml/src/evaluation", "ml/tests"):
    sys.path.insert(0, str(REPO_ROOT / sub))

try:  # real TF in ml/.venv; a stub is enough for the path/CLI logic exercised here
    import tensorflow  # noqa: F401

    HAVE_TF = True
except ImportError:
    sys.modules["tensorflow"] = types.ModuleType("tensorflow")
    HAVE_TF = False

import bootstrap_dataset  # noqa: E402
import compare_tflite_vn  # noqa: E402
import group_split  # noqa: E402
import qa_local_vn  # noqa: E402
import train_and_export  # noqa: E402
import verify_tflite_model  # noqa: E402
from ecosort_ml.artifacts import artifact_paths  # noqa: E402
from ecosort_ml.evalkit import KERAS_PRED_FIELDS, EvalDataError, fingerprint_rows, read_rows, summarize, write_rows  # noqa: E402
from ecosort_ml.vn_test import check_frozen_vn_test, freeze_vn_test  # noqa: E402

LABELS = bootstrap_dataset.load_canonical_labels()


def color_img(path: Path, cls: int, fmt: str = "JPEG", size: int = 256, shade: int = 0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (size, size), color=(cls * 10, 100 + shade, 50)).save(path, format=fmt, quality=100)


def class_from_pixels(img: np.ndarray) -> int:
    return int(round(float(img[0, 0, 0]) / 10.0))


def onehot(c: int) -> np.ndarray:
    v = np.zeros(20, dtype=np.float32)
    v[c] = 1.0
    return v


def oracle_factory(_model: Path):
    return lambda img: onehot(class_from_pixels(img))


def always_zero_factory(_model: Path):
    return lambda img: onehot(0)


def must_not_run(_model: Path):
    raise AssertionError("TFLite inference must not start when data preconditions fail")


def quiet(fn, *a, **kw):
    with redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


class TestArtifactIsolation(unittest.TestCase):
    def test_v1_defaults_are_the_pre_issue15_paths(self) -> None:
        v1 = artifact_paths("v1")
        self.assertEqual(v1.splits_dir, train_and_export.SPLITS_DIR)
        self.assertEqual(v1.weights_tflite, train_and_export.WEIGHTS_OUT)
        self.assertEqual(v1.mobile_tflite, train_and_export.MOBILE_MODEL_OUT)
        self.assertEqual(v1.reports_dir, train_and_export.REPORTS_DIR)
        self.assertEqual(v1.gradcam_dir, train_and_export.GRADCAM_DIR)
        self.assertEqual(v1.mobile_tflite, verify_tflite_model.TFLITE_PATH)
        self.assertEqual(v1.metrics, verify_tflite_model.METRICS_PATH)
        self.assertEqual(v1.split_report, group_split.REPORT_PATH)
        self.assertEqual(v1.manifest, bootstrap_dataset.MANIFEST_PATH)

    def test_v2_never_writes_a_v1_artifact(self) -> None:
        v1, v2 = artifact_paths("v1"), artifact_paths("v2")
        self.assertEqual(v1.written_outputs() & v2.written_outputs(), set())
        self.assertEqual(v2.mobile_tflite.name, "ecosort_v2.tflite")
        self.assertEqual(v2.mobile_tflite.parent, v1.mobile_tflite.parent)
        for out in v2.written_outputs():
            self.assertNotIn("ecosort_v1", out.name)
        # group_split's literal v2 defaults must agree with artifacts.py
        self.assertEqual(group_split.V2_SPLITS_DIR, v2.splits_dir)
        self.assertEqual(group_split.V2_REPORT_PATH, v2.split_report)
        self.assertEqual(group_split.V2_MANIFEST_PATH, v2.manifest)

    def test_cli_defaults_stay_v1(self) -> None:
        self.assertEqual(train_and_export.parse_args([]).model_version, "v1")
        self.assertEqual(train_and_export.parse_args(["--model-version", "v2"]).model_version, "v2")
        ns = types.SimpleNamespace(model_version="v1", manifest=None, splits_dir=None, report_path=None)
        self.assertEqual(
            group_split.resolve_paths(ns), (group_split.MANIFEST_PATH, group_split.SPLITS_DIR, group_split.REPORT_PATH)
        )
        ns.model_version = "v2"
        self.assertEqual(group_split.resolve_paths(ns)[1], group_split.V2_SPLITS_DIR)

    def test_v1_verifier_rejects_v2_only_flags(self) -> None:
        with self.assertRaises(SystemExit), redirect_stdout(io.StringIO()), \
                __import__("contextlib").redirect_stderr(io.StringIO()):
            verify_tflite_model.main(["--test-csv", "x.csv"])


class _V2Fixture(unittest.TestCase):
    """Temp repo with 20 classes of solid-colour images whose colour encodes the class."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.rows: list[dict[str, str]] = []
        for cls in range(3):
            for k in range(2):
                p = self.root / "imgs" / f"c{cls}_{k}.jpg"
                color_img(p, cls)
                self.rows.append({"filepath": str(p), "class_index": str(cls), "item_id": LABELS[cls],
                                  "object_id": f"o{cls}_{k}", "session_id": "s", "source": "local_vn"})
        self.test_csv = self.root / "test.csv"
        write_rows(self.test_csv, self.rows, ["filepath", "class_index", "item_id", "object_id", "session_id", "source"])
        self.model = self.root / "ecosort_v2.tflite"
        self.model.write_bytes(b"fake-v2-model")
        self.v1_model = self.root / "ecosort_v1.tflite"
        self.v1_model.write_bytes(b"fake-v1-model")
        self.keras = self.root / "keras_test_predictions.csv"
        self.log = self.root / "log.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write_keras(self, rows=None, wrong: int = 0) -> None:
        rows = rows if rows is not None else self.rows
        _, shas = fingerprint_rows(rows, self.root)
        out = []
        for i, r in enumerate(rows):
            pred = int(r["class_index"]) if i >= wrong else (int(r["class_index"]) + 1) % 20
            out.append({"filepath": r["filepath"], "class_index": r["class_index"], "sha256": shas[r["filepath"]],
                        "keras_pred": pred, "keras_conf": "1.0"})
        write_rows(self.keras, out, KERAS_PRED_FIELDS)

    def verify(self, factory=must_not_run, model=None):
        return quiet(verify_tflite_model.verify_v2, model or self.model, self.test_csv, self.keras, self.log,
                     self.v1_model, self.root, factory)


class TestStrictV2Verifier(_V2Fixture):
    def test_fails_when_test_csv_missing_instead_of_synthetic_pass(self) -> None:
        self.write_keras()
        self.test_csv.unlink()
        with self.assertRaises(EvalDataError):
            self.verify()
        self.assertFalse(self.log.exists())

    def test_fails_on_empty_test_csv(self) -> None:
        self.write_keras()
        write_rows(self.test_csv, [], ["filepath", "class_index"])
        with self.assertRaises(EvalDataError):
            self.verify()

    def test_fails_when_image_missing(self) -> None:
        self.write_keras()
        Path(self.rows[0]["filepath"]).unlink()
        with self.assertRaises(EvalDataError):
            self.verify()

    def test_fails_without_keras_reference(self) -> None:
        with self.assertRaises(EvalDataError):
            self.verify()

    def test_fails_when_samples_cannot_be_proven_identical(self) -> None:
        self.write_keras()
        color_img(Path(self.rows[0]["filepath"]), 0, shade=40)  # bytes changed after Keras run
        with self.assertRaises(EvalDataError):
            self.verify()
        self.write_keras(rows=self.rows[1:])  # Keras never saw one sample
        with self.assertRaises(EvalDataError):
            self.verify()

    def test_rejects_the_v1_artifact_as_v2(self) -> None:
        self.write_keras()
        with self.assertRaises(verify_tflite_model.AcceptanceError):
            self.verify(model=self.v1_model)  # same path
        copy = self.root / "renamed_v2.tflite"
        shutil.copy2(self.v1_model, copy)
        with self.assertRaises(verify_tflite_model.AcceptanceError):
            self.verify(model=copy)  # v1 bytes under a v2 name

    def test_passes_and_logs_real_sample_count_and_fingerprint(self) -> None:
        self.write_keras(wrong=0)
        log = self.verify(factory=oracle_factory)
        self.assertTrue(log["passed"])
        self.assertEqual(log["n_images"], 6)
        self.assertEqual(log["abs_drift"], 0.0)
        self.assertEqual(log["test_fingerprint"], fingerprint_rows(self.rows, self.root)[0])
        self.assertTrue(self.log.is_file())

    def test_fails_when_drift_exceeds_002(self) -> None:
        self.write_keras(wrong=1)  # Keras 5/6 vs TFLite 6/6 -> drift 0.1667
        with self.assertRaises(verify_tflite_model.AcceptanceError):
            self.verify(factory=oracle_factory)


class TestFrozenVnTestAndComparison(unittest.TestCase):
    """E2E on Option-B folders: bootstrap (VN-replaced, no network) -> split -> freeze -> compare."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        vn = self.root / "local_vn"
        for cls, item in enumerate(LABELS):
            for obj in range(1, 9):
                for ang in range(2):
                    color_img(vn / item / f"yen_obj{obj:02d}" / f"IMG_{ang}.jpg", cls, shade=obj * 2 + ang)
        self.manifest = self.root / "manifest_v2.csv"
        quiet(bootstrap_dataset.build_dataset, local_vn_dir=vn, vn_replace_classes=True,
              min_vn_objects=8, manifest_path=self.manifest)
        self.splits = self.root / "splits_v2"
        self.report = quiet(group_split.run_group_split, self.manifest, self.splits,
                            self.root / "split_verification.json", detailed=True)
        self.frozen = self.splits / "test_vn.csv"
        self.frozen_manifest = self.root / "test_vn_manifest.json"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bootstrap_writes_to_given_manifest_only(self) -> None:
        self.assertTrue(self.manifest.is_file())
        self.assertEqual(len(read_rows(self.manifest)), 20 * 8 * 2)
        self.assertIn("breakdown", self.report)
        self.assertEqual(self.report["overlap_train_test"], 0)

    def test_freeze_is_stable_and_detects_changes(self) -> None:
        man = freeze_vn_test(self.splits, self.frozen, self.frozen_manifest, self.root)
        self.assertGreater(man["images"], 0)
        self.assertEqual(set(man["labels_present"]), set(LABELS))
        man2 = freeze_vn_test(self.splits, self.frozen, self.frozen_manifest, self.root)
        self.assertEqual(man["fingerprint"], man2["fingerprint"])
        rows, _ = check_frozen_vn_test(self.frozen, self.frozen_manifest, self.splits, self.root)
        self.assertEqual(len(rows), man["images"])
        # editing a frozen image must be detected
        color_img(Path(rows[0]["filepath"]), int(rows[0]["class_index"]), shade=99)
        with self.assertRaises(EvalDataError):
            check_frozen_vn_test(self.frozen, self.frozen_manifest, self.splits, self.root)
        with self.assertRaises(EvalDataError):
            freeze_vn_test(self.splits, self.frozen, self.frozen_manifest, self.root)  # refuses silent re-freeze

    def test_freeze_fails_when_no_vn_rows(self) -> None:
        rows = read_rows(self.splits / "test.csv")
        for r in rows:
            r["source"] = "hf_fritz1024"
        write_rows(self.splits / "test.csv", rows, list(rows[0].keys()))
        with self.assertRaises(EvalDataError):
            freeze_vn_test(self.splits, self.frozen, self.frozen_manifest, self.root)

    def test_compare_runs_both_models_on_identical_list(self) -> None:
        freeze_vn_test(self.splits, self.frozen, self.frozen_manifest, self.root)
        v1, v2 = self.root / "v1.tflite", self.root / "v2.tflite"
        v1.write_bytes(b"v1")
        v2.write_bytes(b"v2")
        calls: list[str] = []

        def factory(path: Path):
            calls.append(path.name)
            return always_zero_factory(path) if path == v1 else oracle_factory(path)

        out = self.root / "cmp"
        payload = quiet(compare_tflite_vn.compare, v1, v2, self.frozen, self.frozen_manifest, out,
                        self.splits, self.root, factory, False)
        n = payload["v1"]["n"]
        self.assertEqual(calls, ["v1.tflite", "v2.tflite"])
        self.assertEqual(payload["v2"]["correct"], n)
        self.assertEqual(payload["v1"]["correct"], payload["v1"]["per_class"][LABELS[0]]["support"])
        self.assertEqual(len(payload["per_class_delta"]), 20)
        self.assertTrue((out / "tables.md").is_file())
        self.assertEqual(len(read_rows(out / "predictions.csv")), n)
        v2.write_bytes(b"v1")
        with self.assertRaises(EvalDataError):
            quiet(compare_tflite_vn.compare, v1, v2, self.frozen, self.frozen_manifest, out,
                  self.splits, self.root, factory, False)


class TestMetricsAndQa(unittest.TestCase):
    def test_macro_f1_uses_present_labels_only(self) -> None:
        s = summarize([0, 0, 1, 1], [0, 0, 1, 5], LABELS)
        self.assertEqual(s.present_labels, [0, 1])
        self.assertAlmostEqual(s.top1, 0.75)
        self.assertEqual(s.per_class[1]["correct"], 1)
        self.assertEqual(s.top_confusions[0]["pred"], LABELS[5])

    def test_qa_flags_heic_corrupt_duplicates_and_structure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            vn = Path(tmp) / "local_vn"
            color_img(vn / "hop_sua_giay" / "yen_obj01" / "a.jpg", 2)
            (vn / "coc_nhua_tra_sua" / "yen_obj01").mkdir(parents=True)
            shutil.copy2(vn / "hop_sua_giay" / "yen_obj01" / "a.jpg", vn / "coc_nhua_tra_sua" / "yen_obj01" / "dup.jpg")
            (vn / "hop_sua_giay" / "yen_obj02").mkdir(parents=True)
            (vn / "hop_sua_giay" / "yen_obj02" / "x.heic").write_bytes(b"heic")
            (vn / "hop_sua_giay" / "yen_obj02" / "bad.jpg").write_bytes(b"nope")
            color_img(vn / "hop_sua_giay" / "IMG_flat.jpg", 2)
            color_img(vn / "not_a_label" / "a_obj01" / "z.jpg", 1)
            summary, images = qa_local_vn.run_qa(vn, LABELS)
            self.assertEqual(summary["status_counts"]["heic"], 1)
            self.assertEqual(summary["status_counts"]["corrupt"], 1)
            self.assertEqual(summary["exact_duplicate_groups"][0]["kind"], "cross_class")
            self.assertEqual(summary["unknown_class_dirs"], ["not_a_label"])
            self.assertTrue(any("directly under class" in s for s in summary["structure_issues"]))
            self.assertIn("possibly_blurry", next(i for i in images if i.rel.endswith("a.jpg")).flags)
            self.assertGreater(summary["blocking_issues"], 0)
            out = Path(tmp) / "qa"
            rc = quiet(qa_local_vn.main, ["--local-vn-dir", str(vn), "--out-dir", str(out), "--strict"])
            self.assertEqual(rc, 1)
            self.assertTrue((out / "qa_review_list.csv").is_file())


if __name__ == "__main__":
    unittest.main(verbosity=2)
