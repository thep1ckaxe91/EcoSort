#!/usr/bin/env python3
"""Train MobileNetV3-Small on Group-Split data, export FP16 TFLite (<5MB), evaluate & plot Grad-CAM.

Default (no arguments) is the original v1 run. ``--model-version v2`` reads ml/datasets/splits_v2,
writes reports to ml/reports/v2 and the model to mobile/assets/models/ecosort_v2.tflite, and never
touches any v1 artifact.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
import tensorflow as tf

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "ml" / "src"))

from ecosort_ml.artifacts import ArtifactPaths, artifact_paths  # noqa: E402
from ecosort_ml.evalkit import KERAS_PRED_FIELDS, load_rgb_224, sha256_file, write_rows  # noqa: E402
from ecosort_ml.vn_test import check_frozen_vn_test  # noqa: E402

LABELS_PATH = REPO_ROOT / "knowledge_base" / "labels.txt"
RULES_PATH = REPO_ROOT / "knowledge_base" / "rules.json"
SPLITS_DIR = REPO_ROOT / "ml" / "datasets" / "splits"
WEIGHTS_OUT = REPO_ROOT / "ml" / "weights" / "ecosort_v1.tflite"
MOBILE_MODEL_OUT = REPO_ROOT / "mobile" / "assets" / "models" / "ecosort_v1.tflite"
REPORTS_DIR = REPO_ROOT / "ml" / "reports"
GRADCAM_DIR = REPORTS_DIR / "gradcam_samples"

IMG_SIZE = (224, 224)
BATCH_SIZE = 32
MAX_TFLITE_BYTES = 5 * 1024 * 1024  # 5.0 MB hard PRD limit
STREAM_ORDER = ["recyclable", "food_waste", "residual_waste"]
STREAM_NAMES_VI = ["Recyclable\n(Cam)", "Food Waste\n(Xanh)", "Residual\n(Xam)"]


def configure_gpu() -> None:
    """Enable GPU memory growth when CUDA GPU is available."""
    gpus = tf.config.list_physical_devices("GPU")
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
        except RuntimeError:
            pass
    print(f"[INFO] TensorFlow {tf.__version__} | GPUs visible: {len(gpus)}")


def load_split_csv(csv_path: Path) -> tuple[list[str], list[int]]:
    """Return absolute filepaths and integer class indices from a split CSV."""
    paths: list[str] = []
    labels: list[int] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            paths.append(str(REPO_ROOT / row["filepath"]))
            labels.append(int(row["class_index"]))
    return paths, labels


def build_tf_dataset(paths: list[str], labels: list[int], training: bool) -> tf.data.Dataset:
    """Build deterministic or shuffled tf.data.Dataset returning float32 images in [0, 255]."""
    ds = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        ds = ds.shuffle(buffer_size=len(paths), seed=42, reshuffle_each_iteration=True)

    def _load(path: tf.Tensor, label: tf.Tensor) -> tuple[tf.Tensor, tf.Tensor]:
        raw = tf.io.read_file(path)
        img = tf.io.decode_image(raw, channels=3, expand_animations=False)  # JPEG and PNG
        img.set_shape([None, None, 3])
        img = tf.image.resize(img, IMG_SIZE)
        img = tf.cast(img, tf.float32)  # [0.0, 255.0] for MobileNetV3 include_preprocessing=True
        return img, label

    ds = ds.map(_load, num_parallel_calls=tf.data.AUTOTUNE)
    ds = ds.batch(BATCH_SIZE).prefetch(tf.data.AUTOTUNE)
    return ds


def build_models(num_classes: int = 20) -> tuple[tf.keras.Model, tf.keras.Model, tf.keras.Model]:
    """
    Build training model (with augmentation) and clean inference export model sharing
    exact backbone + classification head weights.
    """
    backbone = tf.keras.applications.MobileNetV3Small(
        input_shape=(224, 224, 3),
        include_top=False,
        weights="imagenet",
        include_preprocessing=True,
    )
    backbone.trainable = False

    gap = tf.keras.layers.GlobalAveragePooling2D(name="global_avg_pool")
    dropout = tf.keras.layers.Dropout(0.25, name="head_dropout")
    classifier = tf.keras.layers.Dense(num_classes, activation="softmax", name="predictions")

    # Training graph includes augmentation
    train_inputs = tf.keras.Input(shape=(224, 224, 3), name="image_input")
    x = tf.keras.layers.RandomFlip("horizontal")(train_inputs)
    x = tf.keras.layers.RandomRotation(0.12)(x)
    x = tf.keras.layers.RandomZoom(0.12)(x)
    x = tf.keras.layers.RandomContrast(0.12)(x)
    x = backbone(x, training=False)
    x = gap(x)
    x = dropout(x)
    train_outputs = classifier(x)
    train_model = tf.keras.Model(inputs=train_inputs, outputs=train_outputs, name="EcoSort_Train")

    # Clean inference export graph without augmentation layers
    inf_inputs = tf.keras.Input(shape=(224, 224, 3), name="image_input")
    y = backbone(inf_inputs, training=False)
    y = gap(y)
    y = dropout(y, training=False)
    inf_outputs = classifier(y)
    export_model = tf.keras.Model(inputs=inf_inputs, outputs=inf_outputs, name="EcoSort_MobileNetV3Small")

    return train_model, export_model, backbone


def plot_confusion(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: list[str],
    title: str,
    out_path: Path,
    figsize: tuple[int, int],
) -> None:
    """Save clean annotated confusion matrix figure."""
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(class_names))))
    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(cm, interpolation="nearest", cmap="Blues")
    ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        title=title,
        ylabel="True Label",
        xlabel="Predicted Label",
    )
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor", fontsize=8)
    plt.setp(ax.get_yticklabels(), fontsize=8)

    thresh = cm.max() / 2.0 if cm.max() > 0 else 0.5
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            if cm[i, j] > 0 or len(class_names) <= 5:
                ax.text(
                    j,
                    i,
                    format(int(cm[i, j]), "d"),
                    ha="center",
                    va="center",
                    fontsize=7 if len(class_names) > 10 else 11,
                    color="white" if cm[i, j] > thresh else "black",
                )
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def generate_gradcam_samples(
    backbone: tf.keras.Model,
    export_model: tf.keras.Model,
    test_paths: list[str],
    test_labels: list[int],
    labels: list[str],
    out_dir: Path,
    num_samples: int = 6,
) -> list[str]:
    """Compute Grad-CAM heatmaps on representative test images for HCI usability evaluation."""
    out_dir.mkdir(parents=True, exist_ok=True)

    # Locate last 4D feature map layer inside MobileNetV3Small backbone
    last_conv_name: str | None = None
    for layer in reversed(backbone.layers):
        out_shape = getattr(layer.output, "shape", None)
        if out_shape is not None and len(out_shape) == 4:
            last_conv_name = layer.name
            break
    if last_conv_name is None:
        raise RuntimeError("Could not find a 4D convolutional layer in backbone for Grad-CAM.")

    conv_extractor = tf.keras.Model(
        inputs=backbone.input,
        outputs=[backbone.get_layer(last_conv_name).output, backbone.output],
    )
    gap_layer = export_model.get_layer("global_avg_pool")
    pred_layer = export_model.get_layer("predictions")

    # Pick diverse classes evenly across the 20 classes
    chosen_indices: list[int] = []
    seen_classes: set[int] = set()
    step = max(1, len(test_paths) // 20)
    for i in range(0, len(test_paths), step):
        cls = test_labels[i]
        if cls not in seen_classes:
            chosen_indices.append(i)
            seen_classes.add(cls)
        if len(chosen_indices) >= num_samples:
            break

    saved_files: list[str] = []
    for k, sample_idx in enumerate(chosen_indices):
        img_path = test_paths[sample_idx]
        true_cls = test_labels[sample_idx]
        pil_img = Image.open(img_path).convert("RGB").resize(IMG_SIZE)
        arr = np.expand_dims(np.asarray(pil_img, dtype=np.float32), axis=0)

        with tf.GradientTape() as tape:
            inputs = tf.cast(arr, tf.float32)
            conv_outputs, backbone_out = conv_extractor(inputs, training=False)
            tape.watch(conv_outputs)
            pooled = gap_layer(backbone_out)
            preds = pred_layer(pooled)
            pred_cls = int(tf.argmax(preds[0]))
            conf = float(preds[0, pred_cls])
            target_score = preds[:, pred_cls]

        grads = tape.gradient(target_score, conv_outputs)
        if grads is None:
            continue
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        conv_map = conv_outputs[0]
        heatmap = tf.reduce_sum(conv_map * pooled_grads, axis=-1)
        heatmap = tf.maximum(heatmap, 0) / (tf.reduce_max(heatmap) + 1e-8)
        heatmap_np = heatmap.numpy()

        # Upsample heatmap to 224x224 and overlay on original image
        hm_img = Image.fromarray(np.uint8(heatmap_np * 255)).resize(IMG_SIZE, resample=Image.BILINEAR)
        hm_arr = np.asarray(hm_img, dtype=np.float32) / 255.0

        fig, axes = plt.subplots(1, 2, figsize=(7, 3.5))
        axes[0].imshow(pil_img)
        axes[0].set_title(f"Input: {labels[true_cls]}", fontsize=9)
        axes[0].axis("off")

        axes[1].imshow(pil_img)
        axes[1].imshow(hm_arr, cmap="jet", alpha=0.45)
        axes[1].set_title(f"Pred: {labels[pred_cls]} ({conf * 100:.1f}%)", fontsize=9)
        axes[1].axis("off")

        fig.tight_layout()
        out_file = out_dir / f"gradcam_{k}_{labels[true_cls]}.png"
        fig.savefig(out_file, dpi=140)
        plt.close(fig)
        saved_files.append(str(out_file.relative_to(REPO_ROOT)))

    return saved_files


def write_keras_reference_predictions(
    export_model: tf.keras.Model,
    test_csv: Path,
    out_csv: Path,
    batch: int = BATCH_SIZE,
) -> int:
    """Predict the test split with the shared PIL loader so TFLite parity compares identical inputs."""
    with test_csv.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out_rows: list[dict[str, object]] = []
    for start in range(0, len(rows), batch):
        chunk = rows[start : start + batch]
        imgs = np.stack([load_rgb_224(REPO_ROOT / r["filepath"]) for r in chunk])
        probs = export_model.predict(imgs, verbose=0)
        for r, p in zip(chunk, probs):
            out_rows.append(
                {
                    "filepath": r["filepath"],
                    "class_index": int(r["class_index"]),
                    "sha256": sha256_file(REPO_ROOT / r["filepath"]),
                    "keras_pred": int(np.argmax(p)),
                    "keras_conf": f"{float(np.max(p)):.6f}",
                }
            )
    write_rows(out_csv, out_rows, KERAS_PRED_FIELDS)  # type: ignore[arg-type]
    return len(out_rows)


def train_and_export(paths: ArtifactPaths | None = None, allow_unfrozen_vn: bool = False) -> int:
    """Run full 2-stage training, TFLite FP16 export, evaluation, and Grad-CAM generation."""
    paths = paths or artifact_paths("v1", REPO_ROOT)
    splits_dir = paths.splits_dir
    reports_dir = paths.reports_dir
    if paths.version == "v2" and not allow_unfrozen_vn:
        # Fine-tune only after real VN photos were QA'd and the VN test list was frozen.
        assert paths.test_vn_csv is not None and paths.test_vn_manifest is not None
        vn_rows, _ = check_frozen_vn_test(paths.test_vn_csv, paths.test_vn_manifest, splits_dir, REPO_ROOT)
        print(f"[INFO] Frozen real-VN test list verified: {len(vn_rows)} images.")

    tf.keras.utils.set_random_seed(42)
    configure_gpu()

    labels = [l.strip() for l in LABELS_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    kb = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    idx_to_stream: dict[int, int] = {
        r["class_index"]: STREAM_ORDER.index(r["default_stream"]) for r in kb["rules"]
    }

    tr_paths, tr_labels = load_split_csv(splits_dir / "train.csv")
    va_paths, va_labels = load_split_csv(splits_dir / "val.csv")
    te_paths, te_labels = load_split_csv(splits_dir / "test.csv")

    train_ds = build_tf_dataset(tr_paths, tr_labels, training=True)
    val_ds = build_tf_dataset(va_paths, va_labels, training=False)
    test_ds = build_tf_dataset(te_paths, te_labels, training=False)

    train_model, export_model, backbone = build_models(num_classes=len(labels))

    print("[STAGE 1] Frozen MobileNetV3Small warmup (6 epochs, LR=1e-3)...")
    train_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    train_model.fit(train_ds, validation_data=val_ds, epochs=6, verbose=2)

    print("[STAGE 2] Fine-tuning top 60 backbone layers (BatchNorm frozen, up to 15 epochs, LR=1e-4)...")
    backbone.trainable = True
    for layer in backbone.layers[:-60]:
        layer.trainable = False
    for layer in backbone.layers:
        if isinstance(layer, tf.keras.layers.BatchNormalization):
            layer.trainable = False

    train_model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=2, min_lr=1e-6),
    ]
    history = train_model.fit(train_ds, validation_data=val_ds, epochs=15, callbacks=callbacks, verbose=2)

    # Evaluate Keras export_model on independent Group-Split Test set
    y_prob = export_model.predict(test_ds, verbose=0)
    y_pred = np.argmax(y_prob, axis=1)
    y_true = np.array(te_labels)

    acc_20 = float(accuracy_score(y_true, y_pred))
    f1_20 = float(f1_score(y_true, y_pred, average="macro"))

    y_true_3 = np.array([idx_to_stream[int(c)] for c in y_true])
    y_pred_3 = np.array([idx_to_stream[int(c)] for c in y_pred])
    acc_3 = float(accuracy_score(y_true_3, y_pred_3))
    f1_3 = float(f1_score(y_true_3, y_pred_3, average="macro"))

    print(f"[METRICS] 20-Class Test Accuracy: {acc_20:.4f} | Macro F1: {f1_20:.4f}")
    print(f"[METRICS]  3-Stream Test Accuracy: {acc_3:.4f} | Macro F1: {f1_3:.4f}")

    # Export FP16 TFLite
    converter = tf.lite.TFLiteConverter.from_keras_model(export_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]
    tflite_bytes = converter.convert()

    size_bytes = len(tflite_bytes)
    size_mb = size_bytes / (1024 * 1024)
    if paths.version != "v1" and size_bytes >= MAX_TFLITE_BYTES:
        # v2+: refuse to write an oversized model into mobile/assets at all.
        raise RuntimeError(f"Exported TFLite exceeds 5 MB ceiling: {size_mb:.2f} MB")

    paths.weights_tflite.parent.mkdir(parents=True, exist_ok=True)
    paths.weights_tflite.write_bytes(tflite_bytes)
    paths.mobile_tflite.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(paths.weights_tflite, paths.mobile_tflite)

    print(f"[EXPORT] Wrote TFLite FP16 model: {size_mb:.2f} MB ({size_bytes} bytes) -> {paths.mobile_tflite}")
    if size_bytes >= MAX_TFLITE_BYTES:
        raise RuntimeError(f"Exported TFLite exceeds 5 MB ceiling: {size_mb:.2f} MB")

    if paths.keras_model is not None:
        paths.keras_model.parent.mkdir(parents=True, exist_ok=True)
        export_model.save(paths.keras_model)
        print(f"[EXPORT] Saved Keras inference model -> {paths.keras_model}")
    if paths.keras_test_predictions is not None:
        n_ref = write_keras_reference_predictions(export_model, splits_dir / "test.csv", paths.keras_test_predictions)
        print(f"[EXPORT] Wrote {n_ref} Keras reference predictions (PIL loader) -> {paths.keras_test_predictions}")

    # Save confusion matrices & Grad-CAM figures
    reports_dir.mkdir(parents=True, exist_ok=True)
    plot_confusion(
        y_true_3,
        y_pred_3,
        STREAM_NAMES_VI,
        f"EcoSort 3-Stream Confusion Matrix (Acc={acc_3 * 100:.1f}%, F1={f1_3:.2f})",
        reports_dir / "confusion_matrix_3streams.png",
        figsize=(6, 5),
    )
    plot_confusion(
        y_true,
        y_pred,
        labels,
        f"EcoSort 20-Class Confusion Matrix (Acc={acc_20 * 100:.1f}%, F1={f1_20:.2f})",
        reports_dir / "confusion_matrix_20classes.png",
        figsize=(12, 10),
    )
    gradcam_files = generate_gradcam_samples(
        backbone=backbone,
        export_model=export_model,
        test_paths=te_paths,
        test_labels=te_labels,
        labels=labels,
        out_dir=paths.gradcam_dir,
        num_samples=6,
    )

    metrics_payload = {
        "model_version": paths.version,
        "model_architecture": "MobileNetV3Small (ImageNet pretrained, include_preprocessing=True)",
        "quantization": "FP16 post-training quantization",
        "tflite_size_bytes": size_bytes,
        "tflite_size_mb": round(size_mb, 3),
        "train_samples": len(tr_paths),
        "val_samples": len(va_paths),
        "test_samples": len(te_paths),
        "epochs_finetuned": len(history.history.get("loss", [])),
        "test_20_class_accuracy": round(acc_20, 4),
        "test_20_class_macro_f1": round(f1_20, 4),
        "test_3_stream_accuracy": round(acc_3, 4),
        "test_3_stream_macro_f1": round(f1_3, 4),
        "gradcam_samples": gradcam_files,
    }
    if paths.version == "v1":
        metrics_payload.pop("model_version")
    else:
        metrics_payload["eval_note"] = (
            "Keras metrics above use the tf.data loader on the full v2 test split; "
            "TFLite parity uses keras_test_predictions.csv (PIL loader) - see tflite_verification.json."
        )
    paths.metrics.parent.mkdir(parents=True, exist_ok=True)
    paths.metrics.write_text(json.dumps(metrics_payload, indent=2), encoding="utf-8")
    print(f"[PASS] Saved metrics and evaluation figures to {reports_dir}.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EcoSort MobileNetV3Small training + FP16 TFLite export")
    parser.add_argument(
        "--model-version",
        choices=["v1", "v2"],
        default="v1",
        help="v1 (default) keeps the original output paths; v2 writes ecosort_v2.tflite and ml/reports/v2/.",
    )
    parser.add_argument(
        "--allow-unfrozen-vn",
        action="store_true",
        help="v2 only: skip the frozen real-VN test check (debug runs; results must not be reported).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return train_and_export(artifact_paths(args.model_version, REPO_ROOT), allow_unfrozen_vn=args.allow_unfrozen_vn)


if __name__ == "__main__":
    raise SystemExit(main())
