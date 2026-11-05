# EcoSort State-Aware Knowledge Base (`knowledge_base/`)

## Module Overview
- **Owner**: Đào Phương Nam (Team Lead, Backend & Multimodal Dev, Student ID: `23021639`)
- **Core Technology**: JSON Schema Draft 2020-12, Deterministic State-Aware Rule Engine (`is_clean`, `has_food`)
- **Domain Foundation**:
  - [Luật Bảo vệ môi trường 2020 số 72/2020/QH14 (Điều 75)](https://vanban.chinhphu.vn/?pageid=27160&docid=202611)
  - [Nghị định 45/2022/NĐ-CP (Điều 26)](https://vanban.chinhphu.vn/?pageid=27160&docid=206129)

## The State-Aware Classification Paradigm (`is_clean` & `has_food`)
Standard computer vision classifiers only answer *"What is this object?"* (e.g., `chai_nhua_pet`, `hop_xop_dung_thuc_an`).
In municipal solid waste sorting, physical condition dictates the final stream:

$$\text{Disposal Stream} = \mathcal{F}(\text{item\_id}, \text{is\_clean}, \text{has\_food})$$

- **`is_clean` (`boolean`)**: True if the container/item is rinsed, dry, and free of grease or oil residue.
- **`has_food` (`boolean`)**: True if food scraps, organic liquids, or edible toppings (e.g., milk tea pearls, leftover rice, soup) remain inside.
- **`secondary_food_stream_required` (`boolean`)**: When `has_food == true` on a non-organic container (like a Styrofoam box or plastic cup), the user is instructed to first empty the organic food into **Rác thực phẩm (Xanh lá `#4CAF50`)** before discarding the soiled packaging into **Rác sinh hoạt khác (Xám `#757575`)**.

## Directory Structure
```
knowledge_base/
├── schemas/
│   └── waste_rule_schema.json   # Formal JSON Schema (Draft 2020-12) with is_clean & has_food
├── rules.json                   # Master 20-class state-aware ontology dataset
├── tests/
│   └── test_kb_schema.py        # Automated CLI verification & truth-table validator
└── README.md
```

## Automated Verification
Every modification to `rules.json` or `waste_rule_schema.json` must pass the automated test suite:
```bash
python3 knowledge_base/tests/test_kb_schema.py
```
