#!/usr/bin/env python3
"""Read-only QA of ml/datasets/local_vn (Option B) before building the v2 hybrid dataset.

Counts files per class/object/member, flags .heic / corrupt / unsupported / tiny / blurry /
EXIF-rotated images, finds exact (sha256) and near (dHash) duplicates across different objects
or classes, and writes a JSON summary plus a CSV list of images a human must review.
It never moves or deletes anything: rejected images are moved out of local_vn by hand
(e.g. to ml/datasets/local_vn_rejected/) and the QA is re-run until it passes.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = REPO_ROOT / "knowledge_base" / "labels.txt"
LOCAL_VN_DIR = REPO_ROOT / "ml" / "datasets" / "local_vn"
OUT_DIR = REPO_ROOT / "ml" / "reports" / "v2" / "qa"

ALLOWED = {".jpg", ".jpeg", ".png"}
LEAF_RE = re.compile(r"^([a-zA-Z0-9-]+)_obj\d+$", re.IGNORECASE)
MIN_SIDE = 224
BLUR_THRESHOLD = 60.0  # variance of Laplacian on a 512px grayscale; heuristic, always human-reviewed
NEAR_DUP_BITS = 4  # dHash Hamming distance <= this across different objects -> review


@dataclass
class ImageInfo:
    rel: str
    item_id: str
    object_dir: str
    member: str
    status: str  # ok | heic | corrupt | unsupported
    sha256: str = ""
    width: int = 0
    height: int = 0
    blur: float = -1.0
    exif_orientation: int = 1
    dhash: int = 0
    flags: list[str] = field(default_factory=list)


def load_labels(path: Path = LABELS_PATH) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def laplacian_variance(gray: np.ndarray) -> float:
    g = gray.astype(np.float32)
    lap = -4 * g[1:-1, 1:-1] + g[:-2, 1:-1] + g[2:, 1:-1] + g[1:-1, :-2] + g[1:-1, 2:]
    return float(lap.var())


def dhash(img: Image.Image, size: int = 8) -> int:
    small = np.asarray(img.convert("L").resize((size + 1, size), Image.Resampling.BILINEAR), dtype=np.int16)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def inspect(path: Path, root: Path, item_id: str, object_dir: str) -> ImageInfo:
    m = LEAF_RE.match(object_dir)
    info = ImageInfo(
        rel=str(path.relative_to(root)),
        item_id=item_id,
        object_dir=object_dir,
        member=m.group(1).lower() if m else "?",
        status="ok",
    )
    ext = path.suffix.lower()
    if ext == ".heic":
        info.status = "heic"
        return info
    if ext not in ALLOWED:
        info.status = "unsupported"
        return info
    info.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        with Image.open(path) as img:
            info.exif_orientation = int(img.getexif().get(0x0112, 1) or 1)
            rgb = img.convert("RGB")
            info.width, info.height = rgb.size
            scale = 512 / max(rgb.size)
            probe = rgb.resize((max(1, int(rgb.width * scale)), max(1, int(rgb.height * scale)))) if scale < 1 else rgb
            info.blur = round(laplacian_variance(np.asarray(probe.convert("L"))), 2)
            info.dhash = dhash(rgb)
    except Exception:
        info.status = "corrupt"
        return info
    if min(info.width, info.height) < MIN_SIDE:
        info.flags.append("too_small")
    if info.blur < BLUR_THRESHOLD:
        info.flags.append("possibly_blurry")
    if info.exif_orientation != 1:
        info.flags.append(f"exif_orientation_{info.exif_orientation}")
    return info


def run_qa(local_vn_dir: Path, labels: list[str]) -> tuple[dict[str, object], list[ImageInfo]]:
    if not local_vn_dir.is_dir():
        raise FileNotFoundError(f"local_vn directory not found: {local_vn_dir}")
    images: list[ImageInfo] = []
    structure_issues: list[str] = []
    unknown_class_dirs: list[str] = []
    for class_dir in sorted(p for p in local_vn_dir.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if class_dir.name not in labels:
            unknown_class_dirs.append(class_dir.name)
            continue
        for entry in sorted(class_dir.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_file():
                structure_issues.append(f"{class_dir.name}/{entry.name}: file directly under class (expected <member>_objXX/)")
                continue
            if not LEAF_RE.match(entry.name):
                structure_issues.append(f"{class_dir.name}/{entry.name}: folder name not <member>_objXX")
            files = [p for p in sorted(entry.rglob("*")) if p.is_file() and not p.name.startswith(".")]
            if not files:
                structure_issues.append(f"{class_dir.name}/{entry.name}: empty object folder")
            for f in files:
                images.append(inspect(f, local_vn_dir, class_dir.name, entry.name))

    ok = [i for i in images if i.status == "ok"]
    # Exact duplicates
    by_sha: dict[str, list[ImageInfo]] = defaultdict(list)
    for i in ok:
        by_sha[i.sha256].append(i)
    exact_dup_groups = []
    for sha, group in by_sha.items():
        if len(group) > 1:
            objs = {(g.item_id, g.object_dir) for g in group}
            kind = "cross_class" if len({g.item_id for g in group}) > 1 else (
                "cross_object" if len(objs) > 1 else "same_object"
            )
            for g in group:
                g.flags.append(f"exact_duplicate_{kind}")
            exact_dup_groups.append({"sha256": sha[:16], "kind": kind, "files": [g.rel for g in group]})
    # Near duplicates across different objects (possible re-shoot of the same object split into two folders)
    near_pairs = []
    for a_idx in range(len(ok)):
        a = ok[a_idx]
        for b in ok[a_idx + 1 :]:
            if (a.item_id, a.object_dir) == (b.item_id, b.object_dir) or a.sha256 == b.sha256:
                continue
            if bin(a.dhash ^ b.dhash).count("1") <= NEAR_DUP_BITS:
                near_pairs.append({"a": a.rel, "b": b.rel, "cross_class": a.item_id != b.item_id})
                a.flags.append("near_duplicate_other_object")
                b.flags.append("near_duplicate_other_object")

    per_class: dict[str, dict[str, object]] = {}
    for lbl in labels:
        cls_imgs = [i for i in images if i.item_id == lbl]
        if not cls_imgs:
            continue
        status = Counter(i.status for i in cls_imgs)
        cls_ok = [i for i in cls_imgs if i.status == "ok"]
        objs = Counter(i.object_dir for i in cls_ok)
        per_class[lbl] = {
            "files": len(cls_imgs),
            "usable": len(cls_ok),
            "skipped_by_loader": {k: v for k, v in status.items() if k != "ok"},
            "objects_with_usable_images": len(objs),
            "images_per_object_min": min(objs.values()) if objs else 0,
            "images_per_object_max": max(objs.values()) if objs else 0,
            "members": sorted({i.member for i in cls_ok}),
            "flagged_for_review": sum(1 for i in cls_ok if i.flags),
            "meets_replace_threshold_8_objects": len(objs) >= 8,
        }
    blocking = [g for g in exact_dup_groups if g["kind"] != "same_object"]
    summary = {
        "local_vn_dir": str(local_vn_dir),
        "total_files": len(images),
        "usable_images": len(ok),
        "status_counts": dict(Counter(i.status for i in images)),
        "classes_with_images": list(per_class),
        "vn_classes_without_images": [c for c in labels if c not in per_class],
        "unknown_class_dirs": unknown_class_dirs,
        "structure_issues": structure_issues,
        "per_class": per_class,
        "exact_duplicate_groups": exact_dup_groups,
        "near_duplicate_pairs_other_object": near_pairs,
        "thresholds": {"min_side_px": MIN_SIDE, "blur_laplacian_var": BLUR_THRESHOLD, "near_dup_bits": NEAR_DUP_BITS},
        "blocking_issues": len(blocking) + len(unknown_class_dirs),
        "note": "Flags are heuristics for human review; wrong-class images must be judged by a person.",
    }
    return summary, images


def write_outputs(summary: dict[str, object], images: list[ImageInfo], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "qa_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out_dir / "qa_review_list.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "item_id", "object_dir", "status", "width", "height", "blur", "exif_orientation", "flags", "decision"])
        for i in images:
            if i.status != "ok" or i.flags:
                w.writerow([i.rel, i.item_id, i.object_dir, i.status, i.width, i.height, i.blur,
                            i.exif_orientation, ";".join(i.flags), ""])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA local_vn Option-B photos (read-only)")
    parser.add_argument("--local-vn-dir", type=Path, default=LOCAL_VN_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--strict", action="store_true", help="exit 1 on cross-object/cross-class duplicates or unknown classes")
    args = parser.parse_args(argv)
    try:
        summary, images = run_qa(args.local_vn_dir, load_labels())
    except FileNotFoundError as exc:
        print(f"[FAIL] {exc}. Download the Drive folders into ml/datasets/local_vn/<item_id>/<member>_objXX/ first.")
        return 1
    write_outputs(summary, images, args.out_dir)
    print(json.dumps({k: summary[k] for k in ("total_files", "usable_images", "status_counts",
                                              "classes_with_images", "blocking_issues")}, indent=2, ensure_ascii=False))
    for lbl, c in summary["per_class"].items():  # type: ignore[union-attr]
        print(f"  {lbl}: usable {c['usable']}/{c['files']} | objects {c['objects_with_usable_images']} | review {c['flagged_for_review']}")
    print(f"[INFO] Wrote {args.out_dir / 'qa_summary.json'} and qa_review_list.csv")
    if args.strict and int(summary["blocking_issues"]) > 0:  # type: ignore[arg-type]
        print("[FAIL] Blocking QA issues (duplicates across objects/classes or unknown class folders).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
