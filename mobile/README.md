# EcoSort Mobile Application (`mobile/`)

## Module Overview
- **Owner**: Nguyễn Thị Hải Yến (PM & Mobile Dev, Student ID: `23021756`)
- **Technology Stack**: Flutter (Dart), Android SDK 34+, Material Design 3, `tflite_flutter`
- **Primary Mission**: Deliver an intuitive, low-latency, and accessible mobile interface for household waste classification at the bin.

## Setup Instructions
To initialize the Flutter project scaffold in this directory, run:
```bash
cd mobile
flutter create . --project-name ecosort --org vn.edu.vnu.uet
```

Ensure your environment satisfies:
- Flutter SDK `>=3.22.0`
- Android SDK API 34+
- Java JDK 17+

## Architectural Architecture
The mobile client follows Clean Architecture with strict separation of concerns:
```
mobile/
├── lib/
│   ├── app/                 # Application routing, themes, and global providers
│   ├── core/                # Constants, utilities, error handling, accessibility helpers
│   ├── features/
│   │   ├── camera/          # Real-time camera preview & frame capture
│   │   ├── classifier/      # On-device TFLite model runner & confidence thresholding
│   │   ├── knowledge_base/  # State-aware taxonomy lookup engine (local JSON)
│   │   ├── result/          # Classification result display, voice readout & disposal instructions
│   │   └── history/         # Local scan logging and gamification metrics
│   └── main.dart            # Application entrypoint
├── test/                    # Unit and widget tests
└── pubspec.yaml             # Dependencies and asset declarations
```

## Engineering & HCI Constraints
1. **Low Latency**: End-to-end inference + rule evaluation must execute under **150ms** on mid-range devices.
2. **Accessibility (WCAG 2.1 AA)**:
   - Dynamic large text mode support for older adults.
   - High contrast UI indicators for waste bins (Recyclables = White/Yellow, Food Waste = Green, Residual = Grey).
   - Audio guidance and voice prompts in Vietnamese.
3. **Offline First**: Primary scanning and taxonomy mapping must function with **zero internet connectivity**.

## Quality Assurance & Verification
Prior to raising any Pull Request touching `mobile/`:
```bash
flutter analyze
flutter test
```
All PRs must include screenshots/videos demonstrating UI compliance and verify accessibility mode rendering.
