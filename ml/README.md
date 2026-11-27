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
