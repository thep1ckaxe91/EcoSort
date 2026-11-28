#!/usr/bin/env python3
"""Verify exported EcoSort TFLite models: contract, Keras<->TFLite parity, and latency.

No arguments: the original v1 check of mobile/assets/models/ecosort_v1.tflite (unchanged).
``--model-version v2``: strict acceptance check of ecosort_v2.tflite. It FAILS (non-zero exit)
instead of passing when the test CSV is missing/empty, images are missing, the Keras v2 reference
predictions are missing, the samples cannot be proven identical, or the model is the v1 artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import numpy as np
from PIL import Image
import tensorflow as tf

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "ml" / "src"))

from ecosort_ml.artifacts import MAX_TFLITE_BYTES, artifact_paths  # noqa: E402
from ecosort_ml.tflite_runner import ContractError, Runner, make_tflite_runner  # noqa: E402
from ecosort_ml.evalkit import (  # noqa: E402
    PREPROCESSING_DESC,
    EvalDataError,
    dump_json,
    fingerprint_rows,
    load_keras_predictions,
    load_rgb_224,
    match_keras_predictions,
    read_rows,
    repo_relative,
    resolve_image,
    sha256_file,
    validate_eval_rows,
)

MAX_DRIFT = 0.02
TFLITE_PATH = REPO_ROOT / "mobile" / "assets" / "models" / "ecosort_v1.tflite"
TEST_CSV_PATH = REPO_ROOT / "ml" / "datasets" / "splits" / "test.csv"
METRICS_PATH = REPO_ROOT / "ml" / "reports" / "metrics.json"
MAX_BYTES = 5 * 1024 * 1024


def verify_tflite() -> int:
    """Validate TFLite tensor shapes, size budget, softmax output, parity, and CPU latency."""
    print("======================================================================")
    print("   EcoSort TFLite Model Contract & Inference Parity Verification      ")
    print("======================================================================")

    assert TFLITE_PATH.is_file(), f"Missing TFLite file: {TFLITE_PATH}"
    size_bytes = TFLITE_PATH.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    assert size_bytes < MAX_BYTES, f"TFLite size {size_mb:.2f} MB exceeds 5.0 MB limit"
    print(f"[PASS] File size: {size_mb:.2f} MB (< 5.00 MB limit).")

    interpreter = tf.lite.Interpreter(model_path=str(TFLITE_PATH), num_threads=4)
    interpreter.allocate_tensors()

    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    assert len(input_details) == 1 and len(output_details) == 1
    assert list(input_details[0]["shape"]) == [1, 224, 224, 3], f"Bad input shape: {input_details[0]['shape']}"
    assert list(output_details[0]["shape"]) == [1, 20], f"Bad output shape: {output_details[0]['shape']}"
    assert input_details[0]["dtype"] == np.float32, f"Expected float32 input, got {input_details[0]['dtype']}"
    print("[PASS] Tensor contract verified: [1, 224, 224, 3] float32 -> [1, 20] float32.")

    in_idx = input_details[0]["index"]
    out_idx = output_details[0]["index"]

    if not TEST_CSV_PATH.is_file():
        # Fallback synthetic smoke test if test split isn't present on disk
        dummy = np.random.default_rng(42).uniform(0, 255, size=(1, 224, 224, 3)).astype(np.float32)
        interpreter.set_tensor(in_idx, dummy)
        interpreter.invoke()
        probs = interpreter.get_tensor(out_idx)[0]
        assert abs(float(np.sum(probs)) - 1.0) < 1e-2, f"Softmax sum invalid: {np.sum(probs)}"
        print("[PASS] Synthetic inference smoke test passed.")
        return 0

    with TEST_CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    # Run inference on all test images to measure exact TFLite accuracy & latency
    eval_rows = rows
    latencies_ms: list[float] = []
    correct = 0

    for row in eval_rows:
        img_path = REPO_ROOT / row["filepath"]
        true_cls = int(row["class_index"])
        arr = np.asarray(
            Image.open(img_path).convert("RGB").resize((224, 224), resample=Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
        tensor = np.expand_dims(arr, axis=0)

        t0 = time.perf_counter()
        interpreter.set_tensor(in_idx, tensor)
        interpreter.invoke()
        probs = interpreter.get_tensor(out_idx)[0]
        dt_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(dt_ms)

        assert abs(float(np.sum(probs)) - 1.0) < 1e-2, f"Invalid softmax sum: {np.sum(probs)}"
        if int(np.argmax(probs)) == true_cls:
            correct += 1

    tflite_acc = correct / len(eval_rows)
    mean_ms = float(np.mean(latencies_ms))
    p95_ms = float(np.percentile(latencies_ms, 95))
    print(f"[PASS] Evaluated {len(eval_rows)} test images via TFLite C++ runtime:")
    print(f"       TFLite Top-1 Acc = {tflite_acc:.4f} | Mean Latency = {mean_ms:.2f} ms | p95 = {p95_ms:.2f} ms")

    if METRICS_PATH.is_file() and len(eval_rows) == len(rows):
        keras_acc = float(json.loads(METRICS_PATH.read_text(encoding="utf-8"))["test_20_class_accuracy"])
        diff = abs(tflite_acc - keras_acc)
        assert diff <= 0.02, f"TFLite vs Keras accuracy drift too large: {diff:.4f}"
        print(f"[PASS] Keras vs TFLite parity verified (drift = {diff:.4f} <= 0.0200).")

    print("======================================================================")
    print("ALL TFLITE VERIFICATION CHECKS PASSED (EXIT CODE 0)")
    return 0


class AcceptanceError(AssertionError):
    """v2 acceptance criterion not met."""


def verify_v2(
    model_path: Path,
    test_csv: Path,
    keras_predictions: Path,
    log_path: Path | None,
    v1_reference: Path,
    repo_root: Path = REPO_ROOT,
    runner_factory: Callable[[Path], Runner] = make_tflite_runner,
    max_drift: float = MAX_DRIFT,
) -> dict[str, object]:
    """Strict v2 acceptance: every data precondition is checked BEFORE any inference."""
    print("======================================================================")
    print("   EcoSort v2 TFLite Acceptance (contract, real-data parity, latency) ")
    print("======================================================================")
    # 1. Right artifact, right size
    if not model_path.is_file():
        raise AcceptanceError(f"Missing v2 TFLite file: {model_path}")
    model_sha = sha256_file(model_path)
    if v1_reference.is_file() and (
        model_path.resolve() == v1_reference.resolve() or model_sha == sha256_file(v1_reference)
    ):
        raise AcceptanceError(f"{model_path} is the v1 artifact ({v1_reference.name}); refusing to accept it as v2.")
    size_bytes = model_path.stat().st_size
    if size_bytes >= MAX_TFLITE_BYTES:
        raise AcceptanceError(f"TFLite size {size_bytes} bytes >= 5 MB limit")
    print(f"[PASS] Model {repo_relative(model_path, repo_root)}: {size_bytes} bytes (< 5 MB), sha256 {model_sha[:12]}")

    # 2. Real data present and identical to what Keras v2 saw
    rows = read_rows(test_csv)
    validate_eval_rows(rows, repo_root)
    fingerprint, row_sha = fingerprint_rows(rows, repo_root)
    keras_pred = match_keras_predictions(rows, row_sha, load_keras_predictions(keras_predictions))
    y_true = np.array([int(r["class_index"]) for r in rows])
    print(f"[PASS] {len(rows)} real test images, fingerprint {fingerprint[:12]}, all matched to Keras v2 predictions.")

    # 3. TFLite inference with the identical loader
    run = runner_factory(model_path)
    tflite_pred: list[int] = []
    latencies_ms: list[float] = []
    for r in rows:
        img = load_rgb_224(resolve_image(r, repo_root))
        t0 = time.perf_counter()
        probs = np.asarray(run(img))
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        if probs.shape != (20,) or abs(float(np.sum(probs)) - 1.0) >= 1e-2:
            raise AcceptanceError(f"Invalid softmax output for {r['filepath']}: shape {probs.shape}, sum {np.sum(probs)}")
        tflite_pred.append(int(np.argmax(probs)))

    keras_acc = float(np.mean(np.array(keras_pred) == y_true))
    tflite_acc = float(np.mean(np.array(tflite_pred) == y_true))
    drift = abs(keras_acc - tflite_acc)
    agreement = float(np.mean(np.array(keras_pred) == np.array(tflite_pred)))
    sources: dict[str, int] = {}
    for r in rows:
        sources[r.get("source", "unknown")] = sources.get(r.get("source", "unknown"), 0) + 1

    log = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": repo_relative(model_path, repo_root),
        "model_sha256": model_sha,
        "model_size_bytes": size_bytes,
        "test_csv": repo_relative(test_csv, repo_root),
        "test_fingerprint": fingerprint,
        "n_images": len(rows),
        "n_images_by_source": sources,
        "keras_reference": repo_relative(keras_predictions, repo_root),
        "preprocessing": PREPROCESSING_DESC,
        "keras_v2_top1": round(keras_acc, 4),
        "tflite_v2_top1": round(tflite_acc, 4),
        "abs_drift": round(drift, 4),
        "max_allowed_drift": max_drift,
        "keras_tflite_top1_agreement": round(agreement, 4),
        "latency_ms_mean": round(float(np.mean(latencies_ms)), 3),
        "latency_ms_p95": round(float(np.percentile(latencies_ms, 95)), 3),
        "environment": {"python": platform.python_version(), "tensorflow": getattr(tf, "__version__", "n/a")},
        "passed": drift <= max_drift,
    }
    if log_path is not None:
        dump_json(log_path, log)
    print(
        f"[INFO] Keras v2 top-1 {keras_acc:.4f} | TFLite v2 top-1 {tflite_acc:.4f} | "
        f"drift {drift:.4f} | agreement {agreement:.4f} | n={len(rows)}"
    )
    if drift > max_drift:
        raise AcceptanceError(f"Keras v2 vs TFLite v2 drift {drift:.4f} > {max_drift}")
    print(f"[PASS] Keras v2 vs TFLite v2 drift {drift:.4f} <= {max_drift:.4f}")
    print("ALL v2 ACCEPTANCE CHECKS PASSED (EXIT CODE 0)")
    return log


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EcoSort TFLite verifier")
    parser.add_argument("--model-version", choices=["v1", "v2"], default="v1")
    parser.add_argument("--model", type=Path, default=None, help="v2: override model path")
    parser.add_argument("--test-csv", type=Path, default=None, help="v2: real test CSV (default splits_v2/test.csv)")
    parser.add_argument("--keras-predictions", type=Path, default=None)
    parser.add_argument("--log", type=Path, default=None, help="v2: JSON log path (default ml/reports/v2/...)")
    args = parser.parse_args(argv)

    if args.model_version == "v1":
        if any(v is not None for v in (args.model, args.test_csv, args.keras_predictions, args.log)):
            parser.error("--model/--test-csv/--keras-predictions/--log apply to --model-version v2 only")
        return verify_tflite()

    v2 = artifact_paths("v2", REPO_ROOT)
    v1 = artifact_paths("v1", REPO_ROOT)
    try:
        verify_v2(
            model_path=args.model or v2.mobile_tflite,
            test_csv=args.test_csv or (v2.splits_dir / "test.csv"),
            keras_predictions=args.keras_predictions or v2.keras_test_predictions,  # type: ignore[arg-type]
            log_path=args.log or v2.tflite_verification_log,
            v1_reference=v1.mobile_tflite,
        )
    except (AcceptanceError, ContractError, EvalDataError) as exc:
        print(f"[FAIL] {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
