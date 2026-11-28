"""TensorFlow-free evaluation helpers shared by the verifier, VN-test freezing and v1/v2 comparison.

Everything here is deterministic and testable without TensorFlow: image loading for both
runtimes, sample fingerprints, Keras-prediction matching and per-class metrics.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
from PIL import Image

from ecosort_ml.artifacts import REPO_ROOT

LABELS_PATH = REPO_ROOT / "knowledge_base" / "labels.txt"
IMG_SIZE = (224, 224)
PREPROCESSING_DESC = (
    "PIL Image.open -> convert('RGB') -> resize(224x224, Image.Resampling.BILINEAR) -> "
    "float32 in [0,255], shape [1,224,224,3]; MobileNetV3 preprocessing is inside the graph"
)
SPLIT_FIELDS = ["filepath", "class_index", "item_id", "object_id", "session_id", "source"]
KERAS_PRED_FIELDS = ["filepath", "class_index", "sha256", "keras_pred", "keras_conf"]


class EvalDataError(RuntimeError):
    """Raised when evaluation data is missing, empty or cannot be proven identical."""


def load_labels(labels_path: Path = LABELS_PATH) -> list[str]:
    labels = [line.strip() for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(labels) != 20:
        raise ValueError(f"Expected 20 labels in {labels_path}, got {len(labels)}")
    return labels


def load_rgb_224(path: Path) -> np.ndarray:
    """The one image loader used for BOTH Keras and TFLite parity/evaluation runs."""
    with Image.open(path) as img:
        arr = np.asarray(
            img.convert("RGB").resize(IMG_SIZE, resample=Image.Resampling.BILINEAR),
            dtype=np.float32,
        )
    return arr


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.is_file():
        raise EvalDataError(f"Evaluation CSV not found: {csv_path}")
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(csv_path: Path, rows: Iterable[dict[str, str]], fields: Sequence[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def resolve_image(row: dict[str, str], repo_root: Path = REPO_ROOT) -> Path:
    p = Path(row["filepath"])
    return p if p.is_absolute() else repo_root / p


def validate_eval_rows(rows: list[dict[str, str]], repo_root: Path = REPO_ROOT, num_classes: int = 20) -> None:
    """Fail loudly instead of silently 'passing' on empty or broken evaluation data."""
    if not rows:
        raise EvalDataError("Evaluation CSV has zero rows; refusing to report accuracy on no data.")
    missing = [r["filepath"] for r in rows if not resolve_image(r, repo_root).is_file()]
    if missing:
        preview = ", ".join(missing[:5])
        raise EvalDataError(f"{len(missing)} evaluation image(s) missing on disk, e.g. {preview}")
    bad = [r["filepath"] for r in rows if not 0 <= int(r["class_index"]) < num_classes]
    if bad:
        raise EvalDataError(f"{len(bad)} row(s) have class_index outside 0..{num_classes - 1}")


def fingerprint_rows(rows: list[dict[str, str]], repo_root: Path = REPO_ROOT) -> tuple[str, dict[str, str]]:
    """Order-independent fingerprint of (filepath, class_index, file bytes) for a sample list."""
    per_file: dict[str, str] = {}
    lines: list[str] = []
    for r in rows:
        digest = sha256_file(resolve_image(r, repo_root))
        per_file[r["filepath"]] = digest
        lines.append(f"{r['filepath']}|{int(r['class_index'])}|{digest}")
    if len(per_file) != len(rows):
        raise EvalDataError("Duplicate filepath rows in evaluation CSV.")
    joined = "\n".join(sorted(lines)).encode("utf-8")
    return hashlib.sha256(joined).hexdigest(), per_file


def load_keras_predictions(path: Path) -> dict[str, dict[str, str]]:
    if path is None or not path.is_file():
        raise EvalDataError(
            f"Keras reference predictions not found: {path}. Run train_and_export.py --model-version v2 first."
        )
    rows = read_rows(path)
    if not rows:
        raise EvalDataError(f"Keras reference predictions file is empty: {path}")
    return {r["filepath"]: r for r in rows}


def match_keras_predictions(
    rows: list[dict[str, str]],
    row_sha: dict[str, str],
    keras_preds: dict[str, dict[str, str]],
) -> list[int]:
    """Return the Keras prediction for every eval row, proving both runtimes saw identical samples."""
    out: list[int] = []
    problems: list[str] = []
    for r in rows:
        ref = keras_preds.get(r["filepath"])
        if ref is None:
            problems.append(f"no Keras prediction for {r['filepath']}")
            continue
        if ref["sha256"] != row_sha[r["filepath"]]:
            problems.append(f"file bytes changed since Keras run: {r['filepath']}")
            continue
        if int(ref["class_index"]) != int(r["class_index"]):
            problems.append(f"label mismatch for {r['filepath']}")
            continue
        out.append(int(ref["keras_pred"]))
    if problems:
        raise EvalDataError(
            f"Cannot prove Keras and TFLite used the same samples ({len(problems)} problem(s)): "
            + "; ".join(problems[:5])
        )
    return out


@dataclass(frozen=True)
class Summary:
    n: int
    correct: int
    top1: float
    macro_f1_present: float
    present_labels: list[int]
    per_class: dict[int, dict[str, float]]
    confusion: list[list[int]]
    top_confusions: list[dict[str, object]]

    def to_json(self, labels: list[str]) -> dict[str, object]:
        return {
            "n": self.n,
            "correct": self.correct,
            "top1": round(self.top1, 4),
            "macro_f1_present_labels": round(self.macro_f1_present, 4),
            "macro_f1_label_set": [labels[i] for i in self.present_labels],
            "per_class": {
                labels[k]: {kk: (round(vv, 4) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                for k, v in self.per_class.items()
            },
            "top_confusions": self.top_confusions,
            "confusion_matrix_20": self.confusion,
        }


def summarize(y_true: Sequence[int], y_pred: Sequence[int], labels: list[str], top_k: int = 10) -> Summary:
    """Top-1, macro-F1 over labels present in y_true, per-class support/correct, top confusion pairs."""
    from sklearn.metrics import confusion_matrix, f1_score

    yt = np.asarray(y_true, dtype=int)
    yp = np.asarray(y_pred, dtype=int)
    if yt.size == 0:
        raise EvalDataError("Cannot summarise zero predictions.")
    n_cls = len(labels)
    present = sorted({int(c) for c in yt})
    cm = confusion_matrix(yt, yp, labels=list(range(n_cls)))
    per_class: dict[int, dict[str, float]] = {}
    for c in present:
        support = int(cm[c].sum())
        correct = int(cm[c, c])
        per_class[c] = {"support": support, "correct": correct, "recall": correct / support}
    pairs: list[dict[str, object]] = []
    for i in range(n_cls):
        for j in range(n_cls):
            if i != j and cm[i, j] > 0:
                support = int(cm[i].sum())
                pairs.append(
                    {
                        "true": labels[i],
                        "pred": labels[j],
                        "count": int(cm[i, j]),
                        "true_support": support,
                        "rate": round(int(cm[i, j]) / support, 4),
                    }
                )
    pairs.sort(key=lambda p: (-int(p["count"]), -float(p["rate"]), str(p["true"]), str(p["pred"])))
    return Summary(
        n=int(yt.size),
        correct=int((yt == yp).sum()),
        top1=float((yt == yp).mean()),
        macro_f1_present=float(f1_score(yt, yp, labels=present, average="macro", zero_division=0)),
        present_labels=present,
        per_class=per_class,
        confusion=cm.astype(int).tolist(),
        top_confusions=pairs[:top_k],
    )


def compare_summaries(v1: Summary, v2: Summary, labels: list[str]) -> list[dict[str, object]]:
    """Per-class delta table (percentage points) for classes present in the shared test list."""
    if v1.present_labels != v2.present_labels or v1.n != v2.n:
        raise EvalDataError("v1 and v2 summaries were not computed on the same test list.")
    rows: list[dict[str, object]] = []
    for c in v1.present_labels:
        a, b = v1.per_class[c], v2.per_class[c]
        rows.append(
            {
                "label": labels[c],
                "support": int(a["support"]),
                "v1_correct": int(a["correct"]),
                "v2_correct": int(b["correct"]),
                "v1_recall": round(float(a["recall"]), 4),
                "v2_recall": round(float(b["recall"]), 4),
                "delta_pp": round((float(b["recall"]) - float(a["recall"])) * 100, 2),
            }
        )
    return rows


def dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def repo_relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(Path(path).resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path)
