# EcoSort MVP — User Stories & Acceptance Criteria Specification

> **Document Status**: LOCKED (Foundational Engineering Contract for MVP)  
> **Course**: Human-Computer Interaction (HCI) — VNU-UET  
> **Academic Context**: Law on Environmental Protection 2020 ([Luật Bảo vệ môi trường 2020 số 72/2020/QH14](https://vanban.chinhphu.vn/?pageid=27160&docid=202611), Article 75)  
> **Author & Reviewers**: Đào Phương Nam (Lead), Nguyễn Thị Hải Yến (PM/Flutter), Bùi Khánh An (ML), Ngô Thị Ngọc Linh (HCI/QA)  
> **Source of Truth Alignment**: `HCI_Project_Manager/PRD.docx` & `HCI_Project_Manager/report.tex`

---

## Executive Summary & Engineering Scope

This specification establishes the official engineering contract and verification boundaries for the **EcoSort MVP** mobile application (targeting Android 8.0+, API 26+). EcoSort provides real-time, on-device perception paired with a state-aware knowledge base to assist Vietnamese household residents in correctly separating waste into three statutory streams:
1. **Rác tái chế (Recyclable Waste)** — Color Code: **Cam / Orange** (`#FF9800`)
2. **Rác thực phẩm (Food Waste / Organic)** — Color Code: **Xanh lá / Green** (`#4CAF50`)
3. **Rác thải sinh hoạt khác (Other / Residual Waste)** — Color Code: **Xám / Grey** (`#757575`)

### Addressing Academic & Lecturer Feedback
This specification directly addresses the 4 core critiques delivered during milestone evaluations:
1. **State-Dependent Classification**: Pure object classification fails in municipal recycling. Clean PET is recyclable; greasy/food-contaminated PET is residual waste. Classification logic must account for physical state.
2. **Clarification Dialog**: Proactive, multi-turn UI interaction to disambiguate object cleanliness when camera inference detects contamination-prone classes.
3. **Strict Anti-Data-Leakage Protocol**: Absolute prohibition of frame-level train/test splitting. Dataset partitioning is strictly grouped by physical object instance (`object_id`) and capture session (`session_id`).
4. **Inclusive Accessibility & Usability Benchmarking**: First-class voice interaction (Vietnamese TTS/ASR), large-format UI affordances for older adults (Persona Bác Tâm, 62 tuổi), and empirical usability evaluation of Grad-CAM explainability maps.

---

## Core User Stories (MVP)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            EcoSort MVP User Stories                          │
├─────────┬────────────────────────────────────────────────────────┬───────────┤
│ US-01   │ Real-Time Offline-First Camera Perception              │ Priority  │
│         │ (Nhận diện rác thời gian thực qua Camera)              │    P0     │
├─────────┼────────────────────────────────────────────────────────┼───────────┤
│ US-02   │ Clarification Dialog & State-Aware Logic               │ Priority  │
│         │ (Làm rõ trạng thái vật phẩm tại nguồn)                 │    P0     │
├─────────┼────────────────────────────────────────────────────────┼───────────┤
│ US-03   │ Voice Interaction & Accessibility UI for Older Adults  │ Priority  │
│         │ (Trợ năng & Giọng nói tiếng Việt cho Người cao tuổi)   │    P0     │
├─────────┼────────────────────────────────────────────────────────┼───────────┤
│ US-04   │ Human-in-the-Loop Active Learning & Error Reporting    │ Priority  │
│         │ (Báo cáo kết quả sai & Tích lũy dữ liệu phản hồi)      │    P1     │
├─────────┼────────────────────────────────────────────────────────┼───────────┤
│ US-05   │ Eco-Streak & Core Habit Formation Gamification         │ Priority  │
│         │ (Động lực phân loại rác & Điểm thưởng Eco-Streak)      │    P1     │
└─────────┴────────────────────────────────────────────────────────┴───────────┘
```

---

### US-01: Nhận diện rác thời gian thực qua Camera (Offline-First Perception)

- **Story ID**: `US-01`
- **Priority**: `P0` (Must-Have for MVP)
- **Primary Persona**: **Chị Lan (34 tuổi)** — Nhân viên marketing, mẹ 2 con, bận rộn, cần phân loại rác nhanh tại thùng rác nhà bếp mà không mất công tra cứu danh bạ tĩnh.
- **User Story**:
  > **As a** busy urban householder standing at the waste bin,  
  > **I want** to point my smartphone camera at a discarded item and immediately view its classified waste stream and actionable handling steps,  
  > **So that** I can discard waste into the correct statutory bin in under 8 seconds without manual searching or risking municipal non-compliance penalties.

#### Acceptance Criteria (AC)

- **AC-01.1: On-Device Inference Latency**
  - **Given** an initialized camera stream running on an Android 8.0+ device (ARM64 mid-range processor, e.g., MediaTek Helio G88 / Snapdragon 680),
  - **When** the user centers a single waste item within the camera viewport,
  - **Then** the local TFLite neural model must execute image pre-processing, forward tensor inference, and post-processing in $\le 200\text{ms}$.

- **AC-01.2: Complete Offline Execution (Zero Network Dependency)**
  - **Given** the mobile device has Airplane Mode active (Wi-Fi disabled, Cellular data disabled, no socket connectivity),
  - **When** the user captures or focuses on a waste item,
  - **Then** the entire classification pipeline (camera preview $\rightarrow$ TFLite inference $\rightarrow$ local `rules.json` taxonomy lookup $\rightarrow$ result card rendering) must execute locally with 100% feature availability and zero network failure exceptions.

- **AC-01.3: Total Task Execution Time**
  - **Given** the user opens the application directly into camera perception mode,
  - **When** the waste object is presented to the viewfinder,
  - **Then** the total elapsed time from viewport acquisition to rendered decision card must be $\le 8.0\text{s}$.

- **AC-01.4: Visual Affordance & Stream Color Encoding**
  - **Given** an inference result is produced with confidence score $\ge 60\%$,
  - **When** the result card renders on the screen,
  - **Then** it must strictly adhere to the national tripartite color coding:
    - **Rác tái chế**: Cam / Orange banner (`#FF9800`) with high-contrast text.
    - **Rác thực phẩm**: Xanh lá / Green banner (`#4CAF50`) with high-contrast text.
    - **Rác sinh hoạt khác**: Xám / Grey banner (`#757575`) with high-contrast text.
  - **And** the card must display the localized item name (Tiếng Việt), the assigned stream name, actionable instructions (e.g., *"Tráng sạch nước sốt thừa, bóp dẹp"*), and a numeric confidence gauge (e.g., `Tin cậy: 88%`).

- **AC-01.5: Low-Confidence Fallback & Heuristic Guidance**
  - **Given** the on-device model produces a maximum class probability $< 60\%$,
  - **When** evaluating the inference tensor,
  - **Then** the system must **not** guess or assign a random stream;
  - **And** the UI must transition to a non-intrusive warning card: *"Chưa nhận diện rõ (< 60%). Vui lòng đưa camera lại gần hơn, đổi góc nhìn hoặc bật đèn pin"*, exposing a dedicated 1-tap Flashlight toggle button.

---

### US-02: Làm rõ trạng thái vật phẩm (Clarification Dialog & State-Aware Logic)

- **Story ID**: `US-02`
- **Priority**: `P0` (Must-Have for MVP)
- **Primary Persona**: **Chị Lan (34 tuổi)** & **Bác Tâm (62 tuổi)** — Người dùng cẩn thận, thường xuyên băn khoăn về các vật phẩm "nửa nạc nửa mỡ" (hộp xôi dính dầu mỡ, cốc trà sữa còn trân châu, hộp sữa chua chưa súc).
- **User Story**:
  > **As a** conscientious citizen separating municipal waste,  
  > **I want** the system to actively ask me clarifying questions when an item's recyclable status depends on its cleanliness or physical condition,  
  > **So that** greasy, food-soiled packaging is not mistakenly thrown into recycling bins where it contaminates clean paper and plastics.

#### Acceptance Criteria (AC)

- **AC-02.1: Cleanliness Check Trigger via Knowledge Base Schema**
  - **Given** the computer vision model detects a contamination-prone container class (specifically: `hop_xop` [Styrofoam meal box], `hop_sua_giay` [Tetra Pak carton], `coc_tra_sua` [Plastic bubble tea cup], `hop_nhua_dinh_dau` [Oily takeout box]),
  - **When** the local engine queries `knowledge_base/rules.json`,
  - **Then** the engine must detect the attribute `"condition": "cleanliness_check"` and suppress immediate static classification.

- **AC-02.2: Modal Clarification Bottom Sheet Display**
  - **Given** a state-dependent trigger is detected,
  - **When** rendering the decision prompt,
  - **Then** a modal Bottom Sheet must slide up within $\le 300\text{ms}$, asking a clear, conversational question in Vietnamese:
    - Text: *"Hộp này bên trong đã được rửa sạch / đổ hết thức ăn thừa chưa?"*
  - **And** provide two mutually exclusive, high-contrast touch targets:
    1. Button A (Affirmative): `[Đã sạch & Khô ráo]`
    2. Button B (Negative): `[Còn dính dầu mỡ / Thức ăn]`

- **AC-02.3: Deterministic State-to-Stream Resolution**
  - **Given** the Clarification Bottom Sheet is active,
  - **When** the user taps `[Đã sạch & Khô ráo]`,
  - **Then** the system immediately assigns the item to **Rác Tái Chế (Màu Cam)** with handling instruction: *"Gấp gọn / Bóp dẹt để tiết kiệm thể tích túi rác."*
  - **When** the user taps `[Còn dính dầu mỡ / Thức ăn]`,
  - **Then** the system redirects the item to **Rác Sinh Hoạt Khác (Màu Xám)** with handling instruction: *"Rác dính dầu mỡ không thể tái chế. Hãy rửa sạch trước khi bỏ vào rác tái chế, hoặc bỏ vào thùng rác khác."*

- **AC-02.4: Interaction Speed & Usability Constraint**
  - **Given** the bottom sheet is presented,
  - **When** the user executes the selection,
  - **Then** the total disambiguation workflow must require exactly 1 tap and complete within $\le 5.0\text{s}$.

- **AC-02.5: Synchronized Audio Readout**
  - **Given** the state-aware resolution completes,
  - **When** the final stream card renders,
  - **Then** the TTS engine must synthesize the corresponding state-specific advice without clipping.

---

### US-03: Trợ năng & Giọng nói cho Người cao tuổi (Voice & Accessibility UI)

- **Story ID**: `US-03`
- **Priority**: `P0` (Must-Have for MVP)
- **Primary Persona**: **Bác Tâm (62 tuổi)** — Cán bộ hưu trí, thị lực suy giảm (viễn thị, đục thủy tinh thể nhẹ), tay hơi run, ngại gõ chữ trên bàn phím ảo smartphone, muốn ứng dụng tự đọc to kết quả bằng tiếng Việt.
- **User Story**:
  > **As an** elderly citizen with diminished eyesight and reduced tactile dexterity,  
  > **I want** the application to verbalize classification results in clear Vietnamese audio and render high-contrast, enlarged typography,  
  > **So that** I can sort household garbage independently without straining my eyes, fumbling with tiny buttons, or depending on my grandchildren.

#### Acceptance Criteria (AC)

- **AC-03.1: Vietnamese Text-to-Speech (TTS) Latency & Naturalness**
  - **Given** an inference card or disambiguation outcome is displayed,
  - **When** "Chế độ Người cao tuổi" is enabled OR the prominent speaker icon is tapped,
  - **Then** Flutter TTS (`vi-VN` locale engine) must initiate audio synthesis within $\le 1.0\text{s}$ of card presentation;
  - **And** verbalize a concise, natural sentence: *"Đây là [Tên vật phẩm] [Trạng thái], hãy bỏ vào thùng [Tên nhóm rác] màu [Màu sắc]"* (e.g., *"Đây là chai nhựa sạch, hãy bỏ vào thùng rác tái chế màu cam"*).

- **AC-03.2: Accessible Typography Standards (Large-Text Mode)**
  - **Given** Elderly Mode is toggled on (or device system font scale is set $>1.2\times$),
  - **When** rendering any screen within the core classification and guidance flow,
  - **Then** all primary headers and stream names must render at font size $\ge 22\text{sp}$;
  - **And** all instructional body text must render at font size $\ge 18\text{sp}$ without text truncation, layout clipping, or horizontal overflow.

- **AC-03.3: Strict WCAG 2.1 AA Contrast Ratios**
  - **Given** any text or graphical affordance rendered on screen,
  - **When** evaluated using automated color contrast analyzers,
  - **Then** the luminance contrast ratio between foreground text and its background must achieve $\ge 4.5:1$ for regular text and $\ge 3.0:1$ for large text ($\ge 18\text{pt}$ / $24\text{px}$).

- **AC-03.4: Touch Target Ergonomics for Tremors / Motor Impairment**
  - **Given** all interactive UI elements (capture button, speaker icon, clarification buttons, flash toggle),
  - **When** laid out on the screen,
  - **Then** each interactive target must measure at least $48 \times 48\text{dp}$ in clickable bounds;
  - **And** adjacent interactive targets must maintain a minimum physical separation gap of $\ge 8\text{dp}$ to prevent accidental mis-taps caused by hand tremors.

- **AC-03.5: Voice Query Input (ASR Hands-Free Search)**
  - **Given** the user cannot or does not want to manipulate the camera,
  - **When** the user presses and holds the persistent microphone button and speaks a query (e.g., *"Pin đồng hồ hỏng", "Vỏ hộp bánh quy"*),
  - **Then** speech recognition must transcribe the query with Word Error Rate (WER) $\le 15\%$ in quiet/moderate indoor environments ($\le 60\text{dB}$) and retrieve the matching classification card from `rules.json` in $\le 1.5\text{s}$.

---

### US-04: Phản hồi lỗi & Học tăng cường (Human-in-the-Loop Active Learning)

- **Story ID**: `US-04`
- **Priority**: `P1` (Secondary / Enhancement for MVP)
- **Primary Persona**: **Chị Lan (34 tuổi)** & **Các thành viên dự án** — Người dùng nhận thấy AI nhận diện sai và muốn phản hồi ngay để cải thiện mô hình.
- **User Story**:
  > **As an** attentive user who encounters an incorrect AI classification,  
  > **I want** to tap a prominent "Báo sai / Sửa nhãn" button and select the correct item identity from a clean list,  
  > **So that** the system captures hard edge cases and feeds the engineering team verified data for the next fine-tuning cycle.

#### Acceptance Criteria (AC)

- **AC-04.1: Instant Discrepancy Reporting Entrypoint**
  - **Given** any classification result card rendered on the screen,
  - **When** the user observes a discrepancy between reality and prediction,
  - **Then** a visible, accessible secondary button *"Kết quả này sai?"* must be available directly below the main guidance card.

- **AC-04.2: Rapid Correction Picker (< 2 Taps)**
  - **Given** the user taps *"Kết quả này sai?"*,
  - **When** the correction dialog opens,
  - **Then** the app must present the 20 canonical EcoSort item classes categorized cleanly by stream (Tái chế / Thực phẩm / Khác);
  - **And** allow selecting the true item class in $\le 2$ taps without requiring keyboard input.

- **AC-04.3: Local Queuing & Resilient Offline Synchronization**
  - **Given** the user confirms the correction while offline,
  - **When** storing the feedback payload,
  - **Then** the payload (timestamp, device model, predicted class, true label, confidence score, anonymous image hash) must append immediately to a local encrypted SQLite / Hive store;
  - **And** automatically sync via background job to Firebase Firestore upon reconnection with exponential backoff (initial retry: $5\text{s}$, max: $300\text{s}$).

- **AC-04.4: Ethical Privacy & Facial Sanitization Safeguards**
  - **Given** feedback submission involves image transmission,
  - **When** preparing data for external upload,
  - **Then** the app must enforce an explicit one-time Opt-In consent dialog informing the user of academic data collection;
  - **And** run local contour/face bounding checks, rejecting or cropping any image containing human facial biometric features.

---

### US-05: Động lực & Gamification cơ bản (Eco-Streak & Habit Formation)

- **Story ID**: `US-05`
- **Priority**: `P1` (Secondary / Enhancement for MVP)
- **Primary Persona**: **Học sinh / Người trẻ / Cư dân đô thị** — Cần động lực bền vững và phản hồi tích cực để duy trì thói quen phân loại rác mỗi ngày.
- **User Story**:
  > **As a** household resident attempting to build eco-friendly habits,  
  > **I want** to track my consecutive daily sorting streak and earn Eco-Points,  
  > **So that** sorting garbage feels rewarding and motivates our whole family to maintain consistent source separation.

#### Acceptance Criteria (AC)

- **AC-05.1: Daily Eco-Streak Counter Logic**
  - **Given** a user successfully completes at least one verified waste classification on the current calendar day (local midnight-to-midnight window),
  - **When** the user confirms disposal,
  - **Then** the `daily_streak` counter must increment by $+1$ (maximum $+1$ increment per calendar day);
  - **And** if no classification event occurs for $\ge 48\text{hours}$, the streak counter resets to $0$ with an encouraging notification: *"Bắt đầu lại chuỗi xanh hôm nay nhé!"*.

- **AC-05.2: Eco-Points Allocation**
  - **Given** a confirmed classification action,
  - **When** points are calculated,
  - **Then** the system awards $+10$ Eco-Points for each valid item sorted, $+50$ bonus points upon achieving a 7-day streak milestone, and displays a subtle haptic feedback vibration ($50\text{ms}$).

- **AC-05.3: 7-Day Habit Tracker Visualization**
  - **Given** the home dashboard or drawer is visible,
  - **When** rendered,
  - **Then** the UI must render a 7-day circular check-in bar representing the last 7 calendar days, with filled green leaves for active days and unfilled circles for missed days.

- **AC-05.4: Tamper-Resistant Local Persistence**
  - **Given** streak and point updates occur on-device,
  - **When** saving to `shared_preferences` / local cache,
  - **Then** point totals must be signed with a local HMAC SHA-256 checksum to prevent trivial client tampering, syncing seamlessly to Firebase Auth/Firestore when signed in.

---

## Non-Functional Requirements & Engineering Guardrails

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                    Non-Functional Verification Guardrails                    │
├──────────────────────────┬───────────────────────────────────────────────────┤
│ Target Platform          │ Android 8.0+ (API Level 26 through 34)            │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Binary Model Footprint   │ MobileNetV3 / EfficientNet-Lite INT8 PTQ < 5.0 MB │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Complete APK Footprint   │ Release APK < 30.0 MB                             │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Data Splitting Protocol  │ Group-Split by object_id/session_id (0% leakage) │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ UI Response Latency      │ Card render < 200ms; TTS synthesis < 1.0s         │
├──────────────────────────┼───────────────────────────────────────────────────┤
│ Usability Cohort         │ N = 8-10 subjects (Minimum 2-3 elderly >= 55 yrs)  │
└──────────────────────────┴───────────────────────────────────────────────────┘
```

### 1. Platform & Device Compatibility
- **Operating System**: Android 8.0 Oreo (API 26) through Android 14 (API 34).
- **Target Hardware Benchmark**: Tested and certified on budget/mid-range chipsets (e.g., MediaTek Helio G88, Qualcomm Snapdragon 680, Samsung Exynos 850) with 3 GB RAM.
- **Runtime Resilience**: Application memory consumption during continuous camera inference must not exceed $180\text{MB}$ heap allocation, maintaining zero Out-Of-Memory (OOM) crashes across 50 consecutive scans.

### 2. Edge AI Model & Quantization Constraints
- **Model Topology**: MobileNetV3-Small or EfficientNet-Lite0 pretrained on ImageNet and fine-tuned on the Vietnamese municipal dataset (`EcoSort-VN mini dataset`, $\ge 3{,}000$ images, 20 classes).
- **Quantization Protocol**: Post-Training Quantization (PTQ) to INT8 with representative calibration dataset.
- **Model Size Ceiling**: The `.tflite` model asset committed into `mobile/assets/models/` must not exceed **$5.0\text{MB}$**.
- **Accuracy Targets on Independent Test Set**:
  - Macro F1-score across 3 statutory streams: $\ge 85\%$.
  - Top-1 Accuracy across 20 granular classes: $\ge 70\%$.

### 3. Anti-Data-Leakage Group-Split Protocol
- **Strict Prohibition**: Random partitioning (`sklearn.model_selection.train_test_split`) on image frames is **forbidden**.
- **Grouping Constraints**: Partitioning into Train (70%) / Validation (15%) / Test (15%) must use `GroupShuffleSplit` or `GroupKFold` grouped strictly by `object_id` (physical item instance) and `session_id` (lighting/capture burst).
- **Verification Condition**:
  $$\text{Objects}(\text{Train}) \cap \text{Objects}(\text{Validation}) \cap \text{Objects}(\text{Test}) = \emptyset$$
  Every pull request touching `ml/` must supply an automated assertion log proving zero intersection between split object partitions.

### 4. Explainable AI (XAI) Usability Benchmark (Grad-CAM)
- **Grad-CAM Activation Map**: A prototype heatmap visualization indicating where the convolutional filters activated on the waste object.
- **HCI Validation Gate**: Grad-CAM utility will be subjected to usability testing during Sprint 2.
- **Graduation Threshold**: If $< 50\%$ of non-technical test subjects comprehend the heatmap and deem it helpful for establishing trust, the feature will remain an opt-in "Chế độ Giải thích chuyên sâu" and will **not** be forced onto default user flows.

---

## Definition of Done (DoD) for MVP Features

A feature or User Story is considered **DONE** and eligible for sprint sign-off only when satisfying all five criteria:

1. **Automated Verification**:
   - Feature has undergone local self-testing using automated CLI scripts or unit tests.
   - Code passes static analysis without warnings (`flutter analyze` for Dart, `ruff` / `pytest` for Python).
2. **Branch & Review Policy**:
   - Developed on a dedicated branch (`feat/<module>-<desc>`).
   - Merged into `main` exclusively through a Pull Request approved by at least 1 peer reviewer (`REQUIRED_APPROVING_REVIEWS: 1`).
   - Zero commits directly to `main`; zero staging of `GEMINI.md`, PR reports, or raw dataset images.
3. **Artifact & Cleanliness Standards**:
   - All state transitions and taxonomy rules adhere to `knowledge_base/rules.json`.
   - Any UI feature complies with WCAG 2.1 AA contrast ($\ge 4.5:1$) and minimum touch bounds ($48 \times 48\text{dp}$).
4. **Offline Resilience Validation**:
   - Verified functioning on a physical Android device or emulator with Airplane Mode active.
5. **Usability Testing Quota**:
   - MVP final evaluation must complete Usability Testing with **8 to 10 participants**.
   - **Mandatory Quota**: At least **2 to 3 participants must be older adults ($\ge 55$ years old)** matching Persona Bác Tâm to empirically validate TTS voice clarity, readability, and task completion speed.
   - Overall System Usability Scale (SUS) target score must achieve $\ge 72$ (Good to Excellent).
