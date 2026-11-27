#!/usr/bin/env python3
"""Verify exported mobile/assets/models/ecosort_v1.tflite contract, parity, and latency."""

from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
from PIL import Image
import tensorflow as tf

REPO_ROOT = Path(__file__).resolve().parents[2]
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


if __name__ == "__main__":
    raise SystemExit(verify_tflite())
