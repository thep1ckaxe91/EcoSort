# EcoSort State-Aware Knowledge Base (`knowledge_base/`)

## Module Overview
- **Owner**: Đào Phương Nam (Team Lead, Backend & Multimodal Dev, Student ID: `23021639`)
- **Core Technology**: JSON Schema Draft 2020-12, Deterministic State-Aware Rule Engine (`is_clean`, `has_food`)
- **Domain Foundation**:
  - [Luật Bảo vệ môi trường 2020 số 72/2020/QH14 (Điều 75)](https://vanban.chinhphu.vn/?pageid=27160&docid=202611)
  - [Nghị định 45/2022/NĐ-CP (Điều 26)](https://vanban.chinhphu.vn/?pageid=27160&docid=206129)
  - [Công văn 9368/BTNMT-KSONMT ngày 02/11/2023](https://monre.gov.vn/VanBan/Lists/VanBanChiDao/DispForm.aspx?ID=2947)

## The State-Aware Classification Paradigm (`is_clean` & `has_food`)
Standard computer vision classifiers only answer *"What is this object?"* (e.g., `chai_nhua_pet`, `hop_xop_dung_thuc_an`).
In municipal solid waste sorting, physical condition dictates the final stream:

$$\text{Disposal Stream} = \mathcal{F}(\text{item\_id}, \text{is\_clean}, \text{has\_food})$$

- **`is_clean` (`boolean`)**: True if the container/item is clean/dry/intact/non-infectious (context-dependent on `condition`).
- **`has_food` (`boolean`)**: True if food scraps, organic liquids, or edible toppings (e.g., milk tea pearls, leftover rice, soup) remain inside.
- **`secondary_food_stream_required` (`boolean`)**: When `has_food == true` on a non-organic container (like a Styrofoam box or plastic cup), the user is instructed to first empty the organic food into **Rác thực phẩm (Xanh lá `#2E7D32`)** before discarding the soiled packaging into **Rác sinh hoạt khác (Xám `#4B5563`)**.
- **`is_hazardous_branch` (`boolean`)**: True if a specific state resolves to hazardous waste (e.g., `khau_trang_y_te` from an infectious patient under CV 9368 section 3.1.1, triggering `#B42318` alert).

## Directory Structure
```
knowledge_base/
├── schemas/
│   └── waste_rule_schema.json   # Formal JSON Schema (Draft 2020-12) with is_clean & has_food
├── rules.json                   # Master 20-class state-aware ontology dataset (CV 9368 compliant)
├── labels.txt                   # Canonical class_index (0..19) label contract for ML & Flutter
├── kb_engine.py                 # Deterministic reference lookup & diacritic-aware search CLI
├── tests/
│   └── test_kb_schema.py        # Automated CLI verification (schema, WCAG AA, labels.txt, CV 9368)
└── README.md
```

## Automated Verification
Every modification to `rules.json`, `labels.txt`, or `waste_rule_schema.json` must pass:
```bash
python3 knowledge_base/tests/test_kb_schema.py
python3 knowledge_base/kb_engine.py --query "vỏ chuối"
```
