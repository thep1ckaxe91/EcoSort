# EcoSort State-Aware Knowledge Base (`knowledge_base/`)

## Module Overview
- **Owner**: Đào Phương Nam (Team Lead, Backend & Multimodal Dev, Student ID: `23021639`)
- **Core Technology**: JSON Schema, Deterministic Rule Evaluation Engine, SQLite/In-Memory JSON cache
- **Domain Foundation**: Vietnamese Law on Environmental Protection 2020 ([Luật số 72/2020/QH14](https://vanban.chinhphu.vn/?pageid=27160&docid=202611), Article 75: Source Separation of Municipal Solid Waste into 3 Streams).

## The State-Aware Classification Paradigm
Standard computer vision classifiers only answer *"What is this object?"* (e.g., `plastic_bottle`).
In municipal waste management, this answer is fundamentally incomplete and leads to cross-contamination.

EcoSort introduces **State-Aware Reasoning**:
$$\text{Disposal Stream} = f(\text{Object Category}, \text{Physical State}, \text{Local Municipality Regulations})$$

### State Distinction Examples
1. **Clean PET Bottle**:
   - State: `empty`, `rinsed`, `dry`
   - Destination: **Recyclable (Rác tái chế)**
2. **Food-Contaminated PET Container**:
   - State: `greasy`, `food_residue_uncleaned`
   - Destination: **Residual Waste (Rác sinh hoạt khác)** (unless washed). Actionable advice: Prompt user to rinse before sorting.
3. **Hazardous Household Items**:
   - Example: Spent lithium batteries, CFL light bulbs, chemical containers.
   - Destination: **Hazardous Drop-off (Chất thải nguy hại)**. Never dump into regular household bins.

## `rules.json` Schema Specification
All classification mappings adhere to the following schema structure:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EcoSortWasteRule",
  "type": "object",
  "required": [
    "item_id",
    "category_code",
    "common_names",
    "target_stream_default",
    "state_rules"
  ],
  "properties": {
    "item_id": { "type": "string", "example": "pet_bottle" },
    "category_code": { "type": "string", "enum": ["plastic", "paper", "metal", "glass", "organic", "hazardous", "textile", "residual"] },
    "common_names": {
      "type": "object",
      "properties": {
        "vi": { "type": "array", "items": { "type": "string" } },
        "en": { "type": "array", "items": { "type": "string" } }
      }
    },
    "target_stream_default": {
      "type": "string",
      "enum": ["recyclable", "food_waste", "residual_waste", "hazardous"]
    },
    "state_rules": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["state_condition", "resolved_stream", "actionable_instructions_vi"],
        "properties": {
          "state_condition": { "type": "string", "enum": ["clean_empty", "soiled_greasy", "liquid_remaining", "damaged"] },
          "resolved_stream": { "type": "string", "enum": ["recyclable", "food_waste", "residual_waste", "hazardous"] },
          "actionable_instructions_vi": { "type": "string" },
          "warning_flag": { "type": "boolean" }
        }
      }
    }
  }
}
```

## Directory Structure
```
knowledge_base/
├── schemas/             # JSON Schema definitions (`waste_rule_schema.json`)
├── rules.json           # Master state-aware ontology dataset
├── tests/               # Schema validation tests and edge-case unit tests
└── README.md
```

## Verification Checklist
1. All entries in `rules.json` must strictly validate against `waste_rule_schema.json`.
2. Every item must have clear Vietnamese instructions (`actionable_instructions_vi`) formatted for audio TTS synthesis.
