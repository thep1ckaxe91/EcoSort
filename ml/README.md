# EcoSort Machine Learning Pipeline (`ml/`)

## Module Overview
- **Owner**: Bùi Khánh An (`23021459`) — *Solo-rescued in Sprint 2 by Đào Phương Nam (`23021639`)*
- **Model Architecture**: `MobileNetV3Small` (ImageNet pretrained, `include_preprocessing=True` inside graph)
- **Quantization & Format**: FP16 Post-Training Quantization (`.tflite`, `< 5.0 MB`)
- **Label Contract**: Strictly consumes [`knowledge_base/labels.txt`](../knowledge_base/labels.txt) (`class_index: 0..19`)

## Isolated Environment Setup (`uv` Python 3.11)
Never install ML packages globally. Everything stays inside `ml/.venv`:
```bash
cd ml
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r <(python3 -c 'import tomllib; print("\n".join(tomllib.load(open("pyproject.toml","rb"))["project"]["dependencies"]))')
```

## End-to-End Reproduction Commands
1. **Bootstrap Balanced 20-Class Dataset** (open HuggingFace `fritz1024/garbage-classify-with-chinese` + Option-B `ml/datasets/local_vn/<item_id>/<member>_objXX/*.jpg` photos):
   ```bash
   ml/.venv/bin/python ml/src/data/bootstrap_dataset.py
   # Or replace HuggingFace classes once >= 8 local physical objects exist per VN class:
   ml/.venv/bin/python ml/src/data/bootstrap_dataset.py --vn-replace-classes --min-vn-objects 8
   ```
2. **Run Object-Level GroupShuffleSplit (70/15/15, zero frame leakage)**:
   ```bash
   ml/.venv/bin/python ml/src/data/group_split.py
   ml/.venv/bin/python ml/src/data/group_split.py --verify-only
   ```
3. **Train MobileNetV3-Small, Export FP16 `.tflite`, & Generate Confusion Matrices + Grad-CAM**:
   ```bash
   ml/.venv/bin/python ml/src/training/train_and_export.py
   ```
4. **Verify Loader (`Option B`) & TFLite Size (`< 5 MB`), Tensor Contract, Parity, & Latency**:
   ```bash
   ml/.venv/bin/python ml/tests/test_local_vn_loader.py
   ml/.venv/bin/python ml/tests/verify_tflite_model.py
   ```

## v2: VN hybrid fine-tune (issue #15)
v1 commands above are unchanged. Every v2 step writes to separate paths
(`ml/datasets/manifest_v2.csv`, `ml/datasets/splits_v2/`, `ml/reports/v2/`,
`mobile/assets/models/ecosort_v2.tflite`) so v1 artifacts are never overwritten.
Raw photos go to `ml/datasets/local_vn/<item_id>/<member>_objXX/*.jpg` (git-ignored; Drive keeps the originals).
```bash
# 0. Read-only QA of the VN photos -> ml/reports/v2/qa/{qa_summary.json, qa_review_list.csv}
#    Move rejected images (blurry / wrong class / duplicates) out of local_vn by hand, re-run until clean.
ml/.venv/bin/python ml/src/data/qa_local_vn.py --strict
# 1. Hybrid manifest (classes with >= 8 VN objects replace HuggingFace data)
ml/.venv/bin/python ml/src/data/bootstrap_dataset.py --vn-replace-classes --min-vn-objects 8 --manifest ml/datasets/manifest_v2.csv
# 2. Object-level 70/15/15 split + per-class/source breakdown -> ml/reports/v2/split_verification.json
ml/.venv/bin/python ml/src/data/group_split.py --model-version v2
# 3. Freeze the real-VN test list (source == local_vn rows of test) -> ml/reports/v2/test_vn_manifest.json
ml/.venv/bin/python ml/src/evaluation/freeze_vn_test.py
# 4. Train + export v2 (refuses to start unless step 3 is intact); also writes
#    ml/reports/v2/keras_test_predictions.csv with the same PIL loader the verifier uses
ml/.venv/bin/python ml/src/training/train_and_export.py --model-version v2
# 5. Strict acceptance: fails on missing/empty data, missing Keras reference, v1 artifact, or drift > 0.02
ml/.venv/bin/python ml/tests/verify_tflite_model.py --model-version v2
# 6. v1 vs v2 TFLite on the identical frozen VN list -> ml/reports/v2/vn_comparison/
ml/.venv/bin/python ml/src/evaluation/compare_tflite_vn.py
# Tests (no TensorFlow needed)
ml/.venv/bin/python ml/tests/test_v2_pipeline.py
```
Write `ml/reports/error_analysis_v2.md` from `ml/docs/error_analysis_v2_template.md`, pasting
`ml/reports/v2/vn_comparison/tables.md`.

## Directory Layout
```
ml/
├── pyproject.toml                       # Isolated Python 3.11 + TF/CUDA dependency spec
├── datasets/                            # Git-ignored raw images, manifest.csv, splits/*.csv
├── weights/                             # Git-ignored ecosort_v1.tflite copy
├── reports/                             # Committed metrics.json, split_verification.json, CM & Grad-CAM PNGs
├── src/
│   ├── data/
│   │   ├── bootstrap_dataset.py         # 20-class dataset builder + PIL image integrity check
│   │   └── group_split.py               # Stratified GroupShuffleSplit by object_id
│   └── training/
│       └── train_and_export.py          # 2-stage MobileNetV3Small fine-tune + FP16 TFLite + Grad-CAM
└── tests/
    ├── test_local_vn_loader.py          # Option-B leaf-folder QA, object_id isolation & split tests
    └── verify_tflite_model.py           # Automated size, tensor, accuracy parity & latency test
```
