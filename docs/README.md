# EcoSort HCI Documentation & Research Artifacts (`docs/`)

## Module Overview
- **Owners**:
  - Ngô Thị Ngọc Linh (HCI/UX Designer & QA Lead, Student ID: `23021608`)
  - Nguyễn Thị Hải Yến (PM & Mobile Dev, Student ID: `23021756`)
- **Course**: Human-Computer Interaction (HCI) — VNU University of Engineering and Technology (VNU-UET)
- **Primary Mission**: House all human-centered research, user empathy artifacts, prototype designs, usability evaluation plans, and experimental protocols.

## HCI Engineering Deliverables
1. **Target User Personas**:
   - *Persona 1*: Urban Household Resident (Fast-paced, needs classification in $<3$ seconds at the bin).
   - *Persona 2*: Senior Citizen / Elderly Householder (Needs high-contrast visual indicators, large fonts, and clear Vietnamese voice readouts).
   - *Persona 3*: Sanitation Worker / Collection Operator (Needs high separation purity to avoid bin contamination).
2. **User Journey & Task Analysis**:
   - Waste generation $\rightarrow$ Decision hesitation at bin $\rightarrow$ Scan / Voice Query $\rightarrow$ State inspection (clean vs dirty) $\rightarrow$ Disposal into correct bin $\rightarrow$ Positive reinforcement / Gamification feedback.
3. **Wireframes & Figma Prototypes**:
   - Mobile camera scanning HUD, disambiguation dialogue, accessibility layout modes.
4. **Usability Evaluation Protocol**:
   - System Usability Scale (SUS) benchmarking (Target score $\ge 80$).
   - Think-aloud protocol during real household sorting trials.
   - Task Completion Rate (TCR) and Time-on-Task (ToT) metrics.
5. **Data Collection Guidelines**:
   - Ethics and user privacy protocols (no faces, strictly waste objects).
   - Group-split labeling conventions for ML pipeline ingestion.

## Directory Structure
```
docs/
├── personas/            # Persona descriptions, empathy maps, and user scenarios
├── wireframes/          # UI mockups, Figma links, flow diagrams
├── evaluation/          # SUS questionnaires, user trial protocols, feedback analysis
├── guidelines/          # Data collection guidelines & photo labeling standard
└── README.md
```

## Governance Note
All formal academic report chapters (`.tex`) and PRD master documentation are managed under `/home/thep1ckaxe/Repos/HCI_Project_Manager`.
Markdown files in `docs/` serve as the living operational documentation for sprint tasks.
