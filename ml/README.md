# EcoSort Machine Learning Pipeline (`ml/`)

## Module Overview
- **Owner**: Bùi Khánh An (AI/ML Engineer, Student ID: `23021459`)
- **Core Technology**: PyTorch / TensorFlow, MobileNetV3-Small / EfficientNet-Lite, TFLite (Post-Training Quantization - INT8/FP16), OpenCV
- **Target Metrics**: Top-1 Accuracy $\ge 90\%$, Macro F1 $\ge 0.88$, On-device inference latency $\le 80\text{ms}$ on ARM64 mobile CPUs.

## Critical Mandate: Group-Split Anti-Data-Leakage Policy
> [!CAUTION]
> **Zero Frame-Level Shuffling**: Random splitting (`train_test_split`) across sequential video frames or camera burst shots of the same item is strictly forbidden.
> It introduces catastrophic train-to-test contamination, yielding inflated 99%+ accuracy during validation that catastrophically collapses in real-world deployment.

### Group-Split Protocol
1. **Grouping Keys**: Every sample must record an `object_id` (the physical item instance) and `session_id` (environmental lighting/background session).
2. **Partitioning**: Splits MUST use `GroupShuffleSplit` or `GroupKFold`:
   ```python
   from sklearn.model_selection import GroupShuffleSplit

   splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
   train_idx, test_idx = next(splitter.split(X, y, groups=df['object_id']))
   ```
3. **Leakage Verification**: Automated check in PR pipeline confirms:
   $$\text{unique\_objects}(\text{Train}) \cap \text{unique\_objects}(\text{Val}) = \emptyset$$

## Directory Layout
```
ml/
├── configs/             # Training and quantization hyperparameter configs (YAML)
├── datasets/            # Local data directory (git-ignored, tracked via external storage)
│   └── .gitkeep
├── notebooks/           # Exploratory data analysis (EDA) & Grad-CAM visualization
├── src/
│   ├── data/            # Dataset loaders, augmentations, and Group-Split validators
│   ├── models/          # Model architectures (MobileNetV3, EfficientNet)
│   ├── training/        # PyTorch training loops, loss functions, metrics
│   └── export/          # Quantization pipelines (PTQ INT8) and TFLite export
├── weights/             # Quantized models (tracked as release artifacts, not committed raw)
├── requirements.txt     # Python dependencies (locked versions)
└── README.md
```

## Dataset Git Hygiene
- Raw images (`.jpg`, `.jpeg`, `.png`) and archives (`.zip`, `.tar.gz`) are blocked by `.gitignore`.
- Raw datasets are synchronized via cloud buckets / DVC. Never run `git add` on binary media.
- Weights larger than 10MB must be published to GitHub Releases and pulled during build time.

## Verification Checklist
Every PR touching `ml/` must provide:
1. Cross-entropy loss and Macro F1 curve logs.
2. Group-Split non-overlap proof.
3. Quantized `.tflite` model size ($\le 15\text{MB}$) and benchmark latency report on target edge hardware.
