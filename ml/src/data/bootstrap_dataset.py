#!/usr/bin/env python3
"""Bootstrap the 20-class EcoSort dataset from open HuggingFace garbage data + local VN shots."""

from __future__ import annotations

import argparse
import csv
import io
import random
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
LABELS_PATH = REPO_ROOT / "knowledge_base" / "labels.txt"
DATASETS_DIR = REPO_ROOT / "ml" / "datasets"
RAW_DIR = DATASETS_DIR / "raw"
LOCAL_VN_DIR = DATASETS_DIR / "local_vn"
MANIFEST_PATH = DATASETS_DIR / "manifest.csv"

HF_BASE_URL = "https://huggingface.co/datasets/fritz1024/garbage-classify-with-chinese/resolve/main"
HF_TRAIN_CSV_URL = f"{HF_BASE_URL}/train.csv"

MAX_PER_CLASS = 200
RANDOM_SEED = 42

# Mapping verified against fritz1024/garbage-classify-with-chinese classname.txt & train.csv
ITEM_TO_HF_FOLDERS: dict[str, list[str]] = {
    "chai_nhua_pet": ["192"],
    "lon_nhom": ["117"],
    "hop_sua_giay": ["111"],
    "coc_nhua_tra_sua": ["233", "246"],
    "giay_bao_sach_vo": ["164", "185", "199"],
    "thung_bia_carton": ["198"],
    "chai_lo_thuy_tinh": ["56", "98"],
    "do_hop_kim_loai": ["140", "129"],
    "rau_cu_qua_thua": ["25", "46"],
    "thuc_an_thua_com_canh": ["7"],
    "ba_tra_ca_phe": ["9", "34"],
    "vo_trung": ["12"],
    "la_chuoi_la_dong": ["6"],
    "hop_xop_dung_thuc_an": ["205", "146"],
    "tui_nilon_ban": ["236"],
    "giay_an_da_qua_su_dung": ["206", "239", "235"],
    "khau_trang_y_te": ["231"],
    "manh_gom_su_thuy_tinh_vo": ["234", "209"],
    "pin_da_qua_su_dung": ["252", "255"],
    "vo_goi_mi_bim_bim": ["47"],
}


@dataclass(frozen=True)
class SampleRecord:
    filepath: str
    class_index: int
    item_id: str
    object_id: str
    session_id: str
    source: str


@dataclass(frozen=True)
class DownloadTask:
    class_index: int
    item_id: str
    hf_rel_path: str
    folder_id: str
    dest_path: Path


def load_canonical_labels(labels_path: Path = LABELS_PATH) -> list[str]:
    """Load ordered 20 canonical item_id labels (0..19)."""
    labels = [line.strip() for line in labels_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(labels) != 20:
        raise ValueError(f"Expected 20 canonical labels in {labels_path}, got {len(labels)}")
    return labels


def fetch_hf_folder_index(csv_url: str = HF_TRAIN_CSV_URL) -> dict[str, list[str]]:
    """Fetch train.csv from HuggingFace and group relative image paths by source folder ID."""
    req = urllib.request.Request(csv_url, headers={"User-Agent": "EcoSort-Bootstrap/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw_csv = resp.read().decode("utf-8-sig")

    by_folder: dict[str, list[str]] = {}
    for row in csv.DictReader(io.StringIO(raw_csv)):
        rel_path = row["image"].strip()
        parts = rel_path.split("/")
        if len(parts) >= 3:
            folder_id = parts[1]
            by_folder.setdefault(folder_id, []).append(rel_path)
    return by_folder


def download_and_validate_image(task: DownloadTask) -> SampleRecord | None:
    """Download one JPEG (or validate cached file) and return a SampleRecord on success."""
    task.dest_path.parent.mkdir(parents=True, exist_ok=True)
    stem = Path(task.hf_rel_path).stem
    object_id = f"hf_{task.folder_id}_{stem}"
    session_id = f"hf_{task.folder_id}"

    if task.dest_path.is_file() and task.dest_path.stat().st_size > 0:
        try:
            with Image.open(task.dest_path) as img:
                img.convert("RGB")
            return SampleRecord(
                filepath=str(task.dest_path.relative_to(REPO_ROOT)),
                class_index=task.class_index,
                item_id=task.item_id,
                object_id=object_id,
                session_id=session_id,
                source="hf_fritz1024",
            )
        except Exception:
            task.dest_path.unlink(missing_ok=True)

    url = f"{HF_BASE_URL}/{task.hf_rel_path}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "EcoSort-Bootstrap/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            with Image.open(io.BytesIO(data)) as img:
                rgb = img.convert("RGB")
                rgb.save(task.dest_path, format="JPEG", quality=92)
            return SampleRecord(
                filepath=str(task.dest_path.relative_to(REPO_ROOT)),
                class_index=task.class_index,
                item_id=task.item_id,
                object_id=object_id,
                session_id=session_id,
                source="hf_fritz1024",
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            if attempt == 1:
                return None
    return None


ALLOWED_IMAGE_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png"})
_MEMBER_OBJ_RE = re.compile(r"^([a-zA-Z0-9-]+)_obj\d+", re.IGNORECASE)
_FLAT_OBJ_RE = re.compile(r"__(obj\d+)", re.IGNORECASE)
_FLAT_SESS_RE = re.compile(r"__(sess\d+)", re.IGNORECASE)


def _extract_member_session(folder_name: str) -> str:
    """Extract normalized member session identifier from an Option-B leaf folder name."""
    match = _MEMBER_OBJ_RE.match(folder_name)
    if match:
        return f"vn_{match.group(1).lower()}"
    return "vn_local"


def _validate_image(img_path: Path) -> bool:
    """Return True if an image file can be opened and converted to RGB cleanly."""
    try:
        with Image.open(img_path) as img:
            img.convert("RGB")
        return True
    except Exception:
        return False


def _format_record_path(img_path: Path, repo_root: Path) -> str:
    """Store paths relative to repo_root when possible, else preserve string path."""
    try:
        return str(img_path.relative_to(repo_root))
    except ValueError:
        return str(img_path)


def collect_local_vn_samples(
    labels: list[str],
    local_vn_dir: Path = LOCAL_VN_DIR,
    repo_root: Path = REPO_ROOT,
) -> list[SampleRecord]:
    """Scan local_vn/<item_id>/ supporting Option-B object subfolders and Option-A flat files."""
    if not local_vn_dir.is_dir():
        return []
    label_to_idx = {name: idx for idx, name in enumerate(labels)}
    records: list[SampleRecord] = []
    skipped_heic = 0
    skipped_corrupt = 0

    for class_dir in sorted(local_vn_dir.iterdir()):
        if not class_dir.is_dir() or class_dir.name not in label_to_idx:
            continue
        item_id = class_dir.name
        class_idx = label_to_idx[item_id]

        for entry in sorted(class_dir.iterdir()):
            if entry.name.startswith("."):
                continue
            if entry.is_dir():
                # Option B leaf folder: <item_id>/<member>_objXX/*.jpg
                object_id = f"vn_{item_id}_{entry.name}"
                session_id = _extract_member_session(entry.name)
                for img_path in sorted(entry.rglob("*")):
                    if not img_path.is_file() or img_path.name.startswith("."):
                        continue
                    ext = img_path.suffix.lower()
                    if ext == ".heic":
                        skipped_heic += 1
                        continue
                    if ext not in ALLOWED_IMAGE_EXTENSIONS:
                        continue
                    if not _validate_image(img_path):
                        skipped_corrupt += 1
                        continue
                    records.append(
                        SampleRecord(
                            filepath=_format_record_path(img_path, repo_root),
                            class_index=class_idx,
                            item_id=item_id,
                            object_id=object_id,
                            session_id=session_id,
                            source="local_vn",
                        )
                    )
            elif entry.is_file():
                # Option A backwards-compatible flat files: <item_id>/<member>__objXX__sessYY.jpg
                ext = entry.suffix.lower()
                if ext == ".heic":
                    skipped_heic += 1
                    continue
                if ext not in ALLOWED_IMAGE_EXTENSIONS:
                    continue
                if not _validate_image(entry):
                    skipped_corrupt += 1
                    continue
                obj_match = _FLAT_OBJ_RE.search(entry.stem)
                sess_match = _FLAT_SESS_RE.search(entry.stem)
                object_id = f"vn_{item_id}_{obj_match.group(1) if obj_match else entry.stem}"
                session_id = sess_match.group(1) if sess_match else "vn_local"
                records.append(
                    SampleRecord(
                        filepath=_format_record_path(entry, repo_root),
                        class_index=class_idx,
                        item_id=item_id,
                        object_id=object_id,
                        session_id=session_id,
                        source="local_vn",
                    )
                )

    if skipped_heic or skipped_corrupt:
        print(
            f"[WARN] local_vn scan skipped {skipped_heic} .heic file(s) "
            f"and {skipped_corrupt} corrupt image(s)."
        )
    return records


def select_replaced_classes(local_records: list[SampleRecord], min_vn_objects: int) -> set[str]:
    """Return item_ids whose distinct local VN object_id count meets min_vn_objects."""
    objects_by_class: dict[str, set[str]] = {}
    for rec in local_records:
        objects_by_class.setdefault(rec.item_id, set()).add(rec.object_id)
    return {
        item_id
        for item_id, obj_ids in objects_by_class.items()
        if len(obj_ids) >= min_vn_objects
    }


def build_dataset(
    max_per_class: int = MAX_PER_CLASS,
    workers: int = 16,
    local_vn_dir: Path = LOCAL_VN_DIR,
    vn_replace_classes: bool = False,
    min_vn_objects: int = 8,
    manifest_path: Path = MANIFEST_PATH,
) -> int:
    """Download balanced 20-class dataset + local_vn overrides, validate, and write manifest.csv."""
    labels = load_canonical_labels()
    missing_maps = [name for name in labels if name not in ITEM_TO_HF_FOLDERS]
    if missing_maps:
        raise KeyError(f"Missing HF mapping for labels: {missing_maps}")

    local_records = collect_local_vn_samples(labels, local_vn_dir=local_vn_dir)
    replaced_classes: set[str] = (
        select_replaced_classes(local_records, min_vn_objects)
        if vn_replace_classes
        else set()
    )
    if replaced_classes:
        print(
            f"[INFO] --vn-replace-classes active (min_vn_objects={min_vn_objects}): "
            f"replacing HF data for {len(replaced_classes)} class(es): {sorted(replaced_classes)}"
        )

    per_class_records: dict[int, list[SampleRecord]] = {i: [] for i in range(20)}
    tasks: list[DownloadTask] = []

    if len(replaced_classes) < len(labels):
        print("[INFO] Fetching fritz1024/garbage-classify-with-chinese index...")
        by_folder = fetch_hf_folder_index()
        rng = random.Random(RANDOM_SEED)

        for class_idx, item_id in enumerate(labels):
            if item_id in replaced_classes:
                continue
            candidates: list[tuple[str, str]] = []
            for folder_id in ITEM_TO_HF_FOLDERS[item_id]:
                for rel_path in by_folder.get(folder_id, []):
                    candidates.append((folder_id, rel_path))
            rng.shuffle(candidates)
            selected = candidates[: max_per_class + 15]
            class_dir = RAW_DIR / f"{class_idx:02d}_{item_id}"
            for folder_id, rel_path in selected:
                stem = Path(rel_path).stem
                dest = class_dir / f"hf_{folder_id}_{stem}.jpg"
                tasks.append(
                    DownloadTask(
                        class_index=class_idx,
                        item_id=item_id,
                        hf_rel_path=rel_path,
                        folder_id=folder_id,
                        dest_path=dest,
                    )
                )

    if tasks:
        print(f"[INFO] Downloading/verifying {len(tasks)} candidate HF images...")
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(download_and_validate_image, t) for t in tasks]
            completed = 0
            for fut in as_completed(futures):
                completed += 1
                rec = fut.result()
                if rec is not None and len(per_class_records[rec.class_index]) < max_per_class:
                    per_class_records[rec.class_index].append(rec)
                if completed % 500 == 0 or completed == len(tasks):
                    total_ok = sum(len(v) for v in per_class_records.values())
                    print(f"[INFO] Progress: {completed}/{len(tasks)} checked, {total_ok} valid kept.")

    all_records: list[SampleRecord] = []
    for idx in range(20):
        all_records.extend(sorted(per_class_records[idx], key=lambda r: r.filepath))
    all_records.extend(local_records)

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["filepath", "class_index", "item_id", "object_id", "session_id", "source"])
        for r in all_records:
            writer.writerow([r.filepath, r.class_index, r.item_id, r.object_id, r.session_id, r.source])

    print(f"[PASS] Wrote {len(all_records)} verified image records to {manifest_path}.")
    for idx, item_id in enumerate(labels):
        cls_local = [r for r in local_records if r.class_index == idx]
        n_cls = len(per_class_records[idx]) + len(cls_local)
        n_local_objs = len({r.object_id for r in cls_local})
        tag = "VN-REPLACED" if item_id in replaced_classes else "HF+VN"
        print(f"  class {idx:02d} ({item_id}) [{tag}]: {n_cls} images ({len(cls_local)} local, {n_local_objs} obj)")
        if item_id in replaced_classes:
            if n_local_objs < 3 or n_cls < 15:
                raise RuntimeError(
                    f"Insufficient local VN coverage for replaced class {idx} ({item_id}): "
                    f"{n_cls} images across {n_local_objs} objects (need >= 15 images, >= 3 objects)"
                )
        elif n_cls < 50:
            raise RuntimeError(f"Insufficient images ({n_cls}) for class {idx} ({item_id})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="EcoSort 20-class dataset bootstrapper")
    parser.add_argument("--max-per-class", type=int, default=MAX_PER_CLASS)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--local-vn-dir", type=Path, default=LOCAL_VN_DIR)
    parser.add_argument(
        "--vn-replace-classes",
        action="store_true",
        help="Replace HuggingFace images with local_vn photos for classes meeting --min-vn-objects.",
    )
    parser.add_argument("--min-vn-objects", type=int, default=8)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=MANIFEST_PATH,
        help="Output manifest CSV (default ml/datasets/manifest.csv; v2 uses ml/datasets/manifest_v2.csv).",
    )
    args = parser.parse_args()

    return build_dataset(
        max_per_class=args.max_per_class,
        workers=args.workers,
        local_vn_dir=args.local_vn_dir,
        vn_replace_classes=args.vn_replace_classes,
        min_vn_objects=args.min_vn_objects,
        manifest_path=args.manifest,
    )


if __name__ == "__main__":
    raise SystemExit(main())
