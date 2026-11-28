"""Single source of truth for where each model version reads inputs and writes outputs.

v1 paths are the exact paths hard-coded before issue #15, so every v1 command keeps its
behaviour. v2 writes to separate locations so a v2 run can never overwrite the v1 model,
metrics, confusion matrices, Grad-CAM samples or split report.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

MODEL_VERSIONS = ("v1", "v2")
MAX_TFLITE_BYTES = 5 * 1024 * 1024  # 5.0 MB hard PRD limit
ERROR_ANALYSIS_V2 = Path("ml") / "reports" / "error_analysis_v2.md"


@dataclass(frozen=True)
class ArtifactPaths:
    version: str
    manifest: Path
    splits_dir: Path
    split_report: Path
    reports_dir: Path
    gradcam_dir: Path
    metrics: Path
    weights_tflite: Path
    mobile_tflite: Path
    # v2-only artifacts (None for v1)
    keras_model: Path | None = None
    keras_test_predictions: Path | None = None
    tflite_verification_log: Path | None = None
    test_vn_csv: Path | None = None
    test_vn_manifest: Path | None = None
    vn_comparison_dir: Path | None = None
    qa_dir: Path | None = None

    def written_outputs(self) -> set[Path]:
        """Every file/dir a training + split run of this version may write."""
        outs = {
            self.splits_dir,
            self.split_report,
            self.gradcam_dir,
            self.metrics,
            self.weights_tflite,
            self.mobile_tflite,
            self.reports_dir / "confusion_matrix_20classes.png",
            self.reports_dir / "confusion_matrix_3streams.png",
        }
        for extra in (
            self.keras_model,
            self.keras_test_predictions,
            self.tflite_verification_log,
            self.test_vn_csv,
            self.test_vn_manifest,
        ):
            if extra is not None:
                outs.add(extra)
        return outs


def artifact_paths(version: str = "v1", repo_root: Path = REPO_ROOT) -> ArtifactPaths:
    """Return the input/output layout for one model version."""
    ml = repo_root / "ml"
    models = repo_root / "mobile" / "assets" / "models"
    if version == "v1":
        reports = ml / "reports"
        return ArtifactPaths(
            version="v1",
            manifest=ml / "datasets" / "manifest.csv",
            splits_dir=ml / "datasets" / "splits",
            split_report=reports / "split_verification.json",
            reports_dir=reports,
            gradcam_dir=reports / "gradcam_samples",
            metrics=reports / "metrics.json",
            weights_tflite=ml / "weights" / "ecosort_v1.tflite",
            mobile_tflite=models / "ecosort_v1.tflite",
        )
    if version == "v2":
        reports = ml / "reports" / "v2"
        splits = ml / "datasets" / "splits_v2"
        return ArtifactPaths(
            version="v2",
            manifest=ml / "datasets" / "manifest_v2.csv",
            splits_dir=splits,
            split_report=reports / "split_verification.json",
            reports_dir=reports,
            gradcam_dir=reports / "gradcam_samples",
            metrics=reports / "metrics.json",
            weights_tflite=ml / "weights" / "ecosort_v2.tflite",
            mobile_tflite=models / "ecosort_v2.tflite",
            keras_model=ml / "weights" / "ecosort_v2.keras",
            keras_test_predictions=reports / "keras_test_predictions.csv",
            tflite_verification_log=reports / "tflite_verification.json",
            test_vn_csv=splits / "test_vn.csv",
            test_vn_manifest=reports / "test_vn_manifest.json",
            vn_comparison_dir=reports / "vn_comparison",
            qa_dir=reports / "qa",
        )
    raise ValueError(f"Unknown model version {version!r}; expected one of {MODEL_VERSIONS}")
