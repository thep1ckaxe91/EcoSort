# EcoSort — Intelligent Waste Classification System

[![VNU-UET HCI](https://img.shields.io/badge/VNU--UET-HCI%20Course%20Project-006241.svg)](https://uet.vnu.edu.vn)
[![Branch Protection](https://img.shields.io/badge/Branch%20Protection-main%20enforced-brightgreen.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

EcoSort is an intelligent, multimodal, and state-aware mobile waste classification application developed for the Human-Computer Interaction (HCI) curriculum at the University of Engineering and Technology, Vietnam National University, Hanoi (VNU-UET).

The application addresses municipal source separation mandated by the Vietnamese Law on Environmental Protection 2020 ([Luật Bảo vệ môi trường 2020 số 72/2020/QH14](https://vanban.chinhphu.vn/?pageid=27160&docid=202611), Article 75), which partitions municipal solid waste into three distinct streams:
1. **Recyclable Solid Waste (Rác tái chế)**: Paper, plastic, metal, and glass.
2. **Food Waste (Rác thực phẩm)**: Organic leftovers, fruit peels, vegetable scraps.
3. **Other Solid Waste (Rác thải sinh hoạt khác)**: Residual waste, soiled packaging, and hazardous items requiring separate handling.

EcoSort elevates standard computer vision by incorporating a **State-Aware Knowledge Base** — discerning not only what an object is, but whether its cleanliness condition (e.g. unwashed food residue on plastic) requires pre-cleaning or diversion to residual waste to prevent recycling contamination.

---

## 👥 Team Roster & Roles

| Member | Student ID | Primary Role | Core Responsibilities |
| :--- | :--- | :--- | :--- |
| **Đào Phương Nam** | `23021639` | **Team Lead, Backend & Multimodal Dev** | State-Aware Waste Taxonomy (`rules.json`), multimodal engine (ASR/TTS voice flow), monorepo governance & CI verification. |
| **Nguyễn Thị Hải Yến** | `23021756` | **PM & Mobile Dev** | Sprint coordination, Flutter client architecture, camera preview pipeline, on-device TFLite model integration. |
| **Bùi Khánh An** | `23021459` | **AI/ML Engineer** | Dataset curation, Group-Split anti-leakage training pipelines, MobileNetV3/EfficientNet fine-tuning, INT8 PTQ quantization & TFLite export. |
| **Ngô Thị Ngọc Linh** | `23021608` | **HCI/UX Designer & QA** | User research, Personas, Figma wireframes & prototypes, usability benchmarking (SUS / think-aloud testing), functional QA. |

---

## 🏗 Monorepo Architecture

EcoSort is organized as a unified monorepo to maintain tight coupling between UI, machine learning models, and classification rules without artifact version drift:

```
EcoSort/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md        # Bug reporting format with device/environment spec
│   │   └── user_story.md       # PRD-aligned user story template with acceptance criteria
│   └── PULL_REQUEST_TEMPLATE.md # Standard PR checklist (self-test, anti-leakage, accessibility)
├── docs/                        # HCI artifacts, personas, wireframes, SUS test protocols
│   └── README.md
├── knowledge_base/              # State-aware taxonomy, rules schema, ontology engine
│   └── README.md
├── ml/                          # Training scripts, Group-Split data loaders, TFLite exports
│   ├── datasets/                # Local data storage (git-ignored, tracked externally)
│   │   └── .gitkeep
│   └── README.md
├── mobile/                      # Flutter client application (Android SDK 34+)
│   └── README.md
├── scripts/                     # Operational automation and repo verification scripts
│   └── verify_repo_setup.sh
├── .gitignore                   # Monorepo ignore rules (Flutter, ML datasets, caches, agent logs)
└── README.md                    # Project overview, team roster, and governance policy
```

---

## 🛡 Git Workflow & Governance Policy

To guarantee engineering integrity across all 4 contributors, direct commits to `main` are strictly blocked via GitHub Branch Protection.

### 1. Branch Naming Standard
Every feature, fix, or documentation update must originate on an isolated branch following this convention:
- Feature: `feat/<module>-<short-description>` (e.g. `feat/mobile-camera-preview`, `feat/ml-group-split`)
- Defect Fix: `fix/<module>-<short-description>` (e.g. `fix/kb-schema-validation`)
- Documentation: `docs/<short-description>` (e.g. `docs/sprint-1-personas`)

### 2. Pull Request & Code Review Rules
- **No Direct Push**: Direct pushes to `main` are rejected by GitHub Branch Protection.
- **Mandatory Review**: Every PR requires at least **1 approving peer review** (`REQUIRED_APPROVING_REVIEWS: 1`) before merge.
- **Dismiss Stale Approvals**: Approvals are automatically invalidated when new commits are pushed.
- **Branch Protection Enforced for Admins**: Enforce admins is active; no bypass is permitted.
- **Clean Commits & Hygiene**:
  - `GEMINI.md` and `*_pr_report.md` files are strictly git-ignored and must **never** be staged.
  - Raw ML photos (`.jpg`, `.png`, `.zip`) must never be committed to Git.
  - Teammate code comments and docstrings must be preserved.

### 3. Verification Script
The repository configuration and hygiene can be audited locally at any time:
```bash
./scripts/verify_repo_setup.sh
```
