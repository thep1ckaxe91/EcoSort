# Biên Bản Weekly Sync Sprint 1: Đánh Giá Paper Test & Kế Hoạch Chụp Ảnh Dataset V1

> **Ngày họp**: Tuần 8 — Sprint 1 (Milestone Thiết kế HCI & Chốt Baseline Dữ liệu)  
> **Chủ trì**: Đào Phương Nam (`23021639` — Team Lead, Backend & Multimodal Dev)  
> **Thành viên tham dự**:  
> - Ngô Thị Ngọc Linh (`23021608` — HCI/UX Designer & QA)  
> - Nguyễn Thị Hải Yến (`23021756` — PM & Mobile Dev)  
> - Bùi Khánh An (`23021459` — AI/ML Engineer)  
> **Căn cứ pháp lý & Học thuật**:  
> - [Luật Bảo vệ môi trường 2020 số 72/2020/QH14 (Điều 75)](https://vanban.chinhphu.vn/?pageid=27160&docid=202611)  
> - Phương pháp Kiểm thử Bản mẫu Giấy (Paper Prototyping): [Rettig, M. (1994). Prototyping for Tiny Fingers. Communications of the ACM](https://dl.acm.org/doi/10.1145/175276.175288)  
> - 10 Nguyên lý Khả dụng của Nielsen: [Nielsen Norman Group — 10 Usability Heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)

---

## 1. Giải Thích & Đánh Giá Kết Quả Paper Test (Kiểm Thử Bản Mẫu Giấy)

### 1.1. "Paper Test" trong học phần HCI là gì?
Theo lộ trình môn học Tương tác Người – Máy (Tuần 7–8 trong `report.tex`: *"Wireframe Figma, user flow, test giấy với 3 người"*), **Paper Test (Low-Fidelity Paper Prototype Usability Test)** là kỹ thuật kiểm thử giao diện **trước khi đóng băng code**:
- Nhóm in các màn hình Wireframe (Camera HUD, Popup hỏi trạng thái Sạch/Bẩn, Thẻ kết quả) ra giấy (hoặc dùng màn hình tĩnh không có AI thật).
- **Kỹ thuật Wizard-of-Oz**: Một thành viên trong nhóm đóng vai "máy tính". Khi người dùng thử nghiệm đặt một vật phẩm rác trước tờ khung ngắm và lấy ngón tay "chạm" vào nút trên giấy, thành viên điều phối sẽ đặt tờ giấy Popup hoặc Thẻ kết quả tương ứng lên bàn (và đọc to câu thoại nếu người dùng bấm nút Loa).
- **Mục đích**: Phát hiện sớm các lỗi tư duy thiết kế (người dùng không hiểu câu hỏi, bấm nhầm nút, chữ quá nhỏ, luồng rườm rà) chỉ trong 15 phút mà không tốn công sửa code Flutter nhiều lần.

### 1.2. Hồ Sơ 3 Người Dùng Tham Gia Paper Test

| Mã người thử | Độ tuổi & Nghề nghiệp | Đại diện Persona | Kịch bản kiểm thử thực hiện |
| :---: | :--- | :--- | :--- |
| **U1** | 33 tuổi — Nhân viên văn phòng, nội trợ | **Chị Lan** (Bận rộn, cần nhanh $<8\text{s}$) | Quét vỏ hộp sữa giấy Tetra Pak & Hộp xốp đựng cơm thừa. |
| **U2** | 21 tuổi — Sinh viên đại học | Người trẻ ở trọ | Quét cốc nhựa trà sữa còn trân châu & Báo sai kết quả. |
| **U3** | 63 tuổi — Cán bộ hưu trí (viễn thị) | **Bác Tâm** (Mắt kém, cần TTS & chữ to) | Quét chai nhựa PET, nghe đọc giọng nói và chọn trạng thái trên Popup. |

### 1.3. Kết Quả Định Lượng & Các Phát Hiện Cốt Lõi (Key Findings)

| Chỉ số đo lường trên bản mẫu giấy | Kết quả trung bình | Mục tiêu MVP | Đánh giá |
| :--- | :---: | :---: | :---: |
| **Tỷ lệ hoàn thành tác vụ (Task Completion Rate)** | `100%` (9/9 lượt) | $\ge 90\%$ | Đạt |
| **Thời gian ra quyết định trên Clarification Dialog** | `3.8 giây` | $\le 5.0\text{s}$ | Đạt |
| **Số lần ngập ngừng / hỏi lại điều phối viên** | `2 lần` (tại U1 & U3) | Tối thiểu hóa | Cần tinh chỉnh câu chữ (xem mục 1.4) |

### 1.4. Các Vấn Đề Phát Hiện Từ Paper Test & Quyết Định Chốt Kỹ Thuật (Action Items)

1. **Vấn đề 1 — Quá tải nhận thức nếu hỏi tách rời 2 câu hỏi (`is_clean` và `has_food`)**:
   - *Quan sát*: Ở bản nháp đầu tiên, khi hỏi người dùng 2 bước liên tiếp (*"Vật phẩm có sạch không?"* rồi lại hỏi *"Có còn thức ăn không?"*), **U1** phàn nàn là mất thời gian vì tay đang cầm rác bẩn, còn **U3 (63t)** bị rối.
   - *Quyết định kỹ thuật (Nam & Yến)*: Trong `knowledge_base/rules.json`, động cơ bên dưới vẫn lưu trữ đầy đủ 2 biến boolean `is_clean` và `has_food` để suy luận chính xác, nhưng trên giao diện **Clarification Dialog** chỉ hiển thị **1 hộp thoại duy nhất với 2 nút bấm đối lập rõ ràng**:
     - Nút 1 (Xanh/Tích cực): `[Đã rửa sạch / Khô ráo]` $\rightarrow$ Ánh xạ thẳng vào `(is_clean: true, has_food: false)`.
     - Nút 2 (Viền Xám): `[Dính bẩn / Còn thức ăn]` $\rightarrow$ Ánh xạ thẳng vào `(is_clean: false, has_food: true)`.

2. **Vấn đề 2 — Xử lý rác "Hộp xốp còn thức ăn thừa" (`hop_xop_dung_thuc_an` & `coc_nhua_tra_sua`)**:
   - *Quan sát*: Khi quét hộp xốp còn cơm thừa, **U2** định vứt nguyên cả hộp lẫn cơm vào thùng Rác sinh hoạt khác (Xám). Điều này vi phạm quy định phân loại rác thực phẩm.
   - *Quyết định kỹ thuật (Nam)*: Bổ sung trường `"secondary_food_stream_required": true` vào Schema JSON. Khi `has_food == true` trên bao bì không tái chế, hướng dẫn xử lý (`actionable_instructions_vi`) và câu đọc TTS (`tts_readout_vi`) bắt buộc nhắc người dùng **2 bước**: *"Hãy đổ hết thức ăn thừa sang thùng màu xanh lá, sau đó bỏ vỏ hộp xốp vào thùng rác khác màu xám."*

3. **Vấn đề 3 — Trợ năng cho Người cao tuổi (U3 - Bác Tâm)**:
   - *Quan sát*: **U3** đọc chậm khi thẻ kết quả có quá nhiều chữ giải thích luật. Khi điều phối viên đọc to câu kết luận ngắn gọn (< 15 từ), **U3** thực hiện bỏ rác đúng ngay lập tức.
   - *Quyết định kỹ thuật (Nam & Yến)*: Tách riêng trường `tts_readout_vi` (giới hạn $\le 180$ ký tự, câu văn tự nhiên, nêu rõ **Tên vật + Trạng thái + Màu thùng**) khỏi trường `actionable_instructions_vi`. Kích thước nút bấm trên Popup bắt buộc $\ge 48\text{dp}$ chiều cao.

---

## 2. Chốt Đồng Bộ Liên Phân Hệ (Weekly Sync Cross-Module Contract)

Để chuẩn bị ghép nối code trong Tuần 9–10, 4 thành viên thống nhất khóa các giao thức sau:

- **Knowledge Base (`knowledge_base/` — Nam)**:
  - Đã khóa `waste_rule_schema.json` và `rules.json` với đúng 20 lớp (`class_index: 0..19`).
  - Mọi nhánh trạng thái đều chứa `is_clean` (`bool`), `has_food` (`bool`), `resolved_stream`, `actionable_instructions_vi`, và `tts_readout_vi`.
- **Mobile UI (`mobile/` — Yến)**:
  - Hộp thoại `ClarificationDialog` gọi trực tiếp `clarification_question_vi` từ JSON và truyền kết quả người dùng chọn về hàm phân giải trạng thái `(is_clean, has_food)`.
- **ML Pipeline (`ml/` — An)**:
  - File `labels.txt` xuất kèm mô hình TFLite phải khớp tuyệt đối thứ tự `class_index: 0..19` và chuỗi `item_id` trong `knowledge_base/rules.json`.

---

## 3. Kế Hoạch Chụp Ảnh Thu Thập Dataset V1 (Tuần 9–10)

### 3.1. Chỉ Tiêu Định Lượng (MVP Scale)
- **Mục tiêu Dataset V1 (Tuần 9–10)**: $\ge 800$ ảnh gốc thực tế tại Việt Nam $\rightarrow$ sau Data Augmentation ($5\times$) đạt $\ge 4{,}000$ ảnh (vượt chỉ tiêu $\ge 1{,}500$ ảnh V1 và $\ge 3{,}000$ ảnh V2 trong PRD).
- **Định mức mỗi thành viên**: Phụ trách **5 lớp rác cố định**, mỗi lớp chụp **40 ảnh** (tối thiểu **8 vật thể độc lập / lớp** $\times$ **5 góc chụp/điều kiện sáng khác nhau** = **200 ảnh gốc / thành viên**).

### 3.2. Phân Công Chi Tiết 20 Lớp Cho 4 Thành Viên

| Thành viên | Phụ trách các lớp (`class_index` — `item_id`) | Số vật thể tối thiểu | Số ảnh gốc cam kết |
| :--- | :--- | :---: | :---: |
| **1. Đào Phương Nam** | `0: chai_nhua_pet`, `1: lon_nhom`, `2: hop_sua_giay`, `3: coc_nhua_tra_sua`, `4: giay_bao_sach_vo` | $\ge 40$ vật thể (8 vật/lớp) | **200 ảnh** |
| **2. Nguyễn Thị Hải Yến** | `5: thung_bia_carton`, `6: chai_lo_thuy_tinh`, `7: do_hop_kim_loai`, `8: rau_cu_qua_thua`, `9: thuc_an_thua_com_canh` | $\ge 40$ vật thể (8 vật/lớp) | **200 ảnh** |
| **3. Bùi Khánh An** | `10: ba_tra_ca_phe`, `11: vo_trung`, `12: la_chuoi_la_dong`, `13: hop_xop_dung_thuc_an`, `14: tui_nilon_ban` | $\ge 40$ vật thể (8 vật/lớp) | **200 ảnh** |
| **4. Ngô Thị Ngọc Linh** | `15: giay_an_da_qua_su_dung`, `16: khau_trang_y_te`, `17: manh_gom_su_thuy_tinh_vo`, `18: pin_da_qua_su_dung`, `19: vo_goi_mi_bim_bim` | $\ge 40$ vật thể (8 vật/lớp) | **200 ảnh** |

### 3.3. Quy Tắc Đặt Tên File Chống Data Leakage (Mandatory Group-Split Standard)

> [!IMPORTANT]
> Tuyệt đối không chụp 10 ảnh liên tiếp của cùng 1 vỏ chai rồi đặt tên ngẫu nhiên! Để script `GroupShuffleSplit` của An tách tập Train/Val/Test (70/15/15) chuẩn xác 100% theo `object_id`, mọi ảnh tải lên Google Drive / DVC nhóm phải tuân thủ quy ước:

```text
<class_index>_<item_id>__obj<XX>__sess<YY>__f<ZZ>.jpg
```
- Ví dụ: `02_hop_sua_giay__obj01__sess01__f01.jpg`, `02_hop_sua_giay__obj01__sess01__f02.jpg` (cùng 1 hộp sữa số `01` chụp ở các góc khác nhau sẽ có chung mã `obj01` để toàn bộ các frame của hộp sữa này chỉ nằm ở tập Train HOẶC tập Test, không bao giờ nằm ở cả hai).
- **Quyền riêng tư & An toàn**: Không chụp dính khuôn mặt người, biển số xe, hoặc thông tin cá nhân trên hóa đơn/đơn hàng dán trên thùng carton.
