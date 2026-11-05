# Danh Mục 20 Lớp Rác Cốt Lõi & Ma Trận Điều Kiện Trạng Thái (MVP Taxonomy)

> **Trạng thái tài liệu**: CHỐT MVP (Locked Baseline for ML Dataset V1 & Knowledge Base)  
> **Người chủ trì**: Đào Phương Nam (`23021639` — Team Lead, Backend & Multimodal Dev)  
> **Đồng chủ trì**: Bùi Khánh An (`23021459` — AI/ML), Ngô Thị Ngọc Linh (`23021608` — HCI/QA), Nguyễn Thị Hải Yến (`23021756` — PM/Mobile)  
> **Căn cứ pháp lý**:  
> - [Luật Bảo vệ môi trường 2020 số 72/2020/QH14 (Điều 75)](https://vanban.chinhphu.vn/?pageid=27160&docid=202611)  
> - [Nghị định 45/2022/NĐ-CP (Điều 26 — Quy định xử phạt vi phạm phân loại rác sinh hoạt)](https://vanban.chinhphu.vn/?pageid=27160&docid=206129)  
> - [Hướng dẫn kỹ thuật phân loại chất thải rắn sinh hoạt (Công văn 9368/BTNMT-KSONMT)](https://monre.gov.vn/VanBan/Lists/VanBanChiDao/DispForm.aspx?ID=2947)

---

## 1. Nguyên Lý Thiết Kế Phân Loại Phụ Thuộc Trạng Thái (State-Aware Taxonomy)

Các mô hình phân loại ảnh truyền thống (ImageNet, TrashNet) mắc sai lầm nghiêm trọng khi giả định **Nhãn vật thể $\equiv$ Nhóm rác**. Trên thực tế tại hộ gia đình Việt Nam, luồng xử lý của một vật phẩm phụ thuộc trực tiếp vào hai biến trạng thái vật lý:

1. **`is_clean` (`boolean`)**: Bề mặt vật phẩm có sạch sẽ, khô ráo, không bám dầu mỡ/hóa chất bẩn hay không?
2. **`has_food` (`boolean`)**: Bên trong hoặc trên bề mặt vật phẩm có còn sót lại thức ăn thừa, chất lỏng hữu cơ (nước phở, sữa thừa, trân châu, cơm dính) hay không?

### Công thức ánh xạ quyết định (Deterministic State Resolution)
$$\text{Luồng Rác Đích} = \mathcal{F}(\text{class\_id}, \text{is\_clean}, \text{has\_food})$$

| Tổ hợp trạng thái | `is_clean` | `has_food` | Nhãn nút bấm trên UI (Clarification Dialog) | Quy tắc xử lý cốt lõi |
| :--- | :---: | :---: | :--- | :--- |
| **Trạng thái Sạch (Clean & Empty)** | `true` | `false` | `[Đã rửa sạch / Khô ráo]` | Vật liệu có khả năng tái chế được đưa thẳng vào **Rác tái chế (Màu Cam)**. |
| **Bẩn / Dính dầu mỡ (Soiled)** | `false` | `false` | `[Dính bẩn / Còn thức ăn]` | Dầu mỡ/nhớt làm hỏng lô tái chế $\rightarrow$ Chuyển sang **Rác sinh hoạt khác (Màu Xám)** (kèm khuyên tráng rửa). |
| **Còn thức ăn / Chất lỏng (Food Remaining)** | `false` | `true` | `[Dính bẩn / Còn thức ăn]` | Bắt buộc **trút bỏ phần thức ăn thừa vào Rác thực phẩm (Xanh lá)**, sau đó vỏ bẩn bỏ vào **Rác sinh hoạt khác (Xám)** hoặc rửa sạch để tái chế. |

---

## 2. Bảng 20 Lớp Rác Cốt Lõi (20 Canonical Classes) & Ma Trận Trạng Thái

Bộ 20 lớp được thiết kế cân bằng giữa **3 nhóm rác theo luật định** và bao phủ các vật phẩm đặc thù sinh hoạt Việt Nam (hộp xôi xốp, lá chuối/lá dong, cốc trà sữa, vỏ hộp sữa giấy, chai nước mắm).

| Index | `item_id` (Class Label) | Tên hiển thị Tiếng Việt | Nhóm gốc (Default) | Hỏi trạng thái? (`requires_clarification`) | Kết quả khi SẠCH (`is_clean=true, has_food=false`) | Kết quả khi BẨN / CÓ ĐỒ ĂN (`is_clean=false` hoặc `has_food=true`) |
| :---: | :--- | :--- | :--- | :---: | :--- | :--- |
| `0` | `chai_nhua_pet` | Chai nhựa PET (nước suối, nước ngọt) | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Đổ hết nước, tháo nắp, bóp dẹt. | **Rác khác (Xám)**: Đổ bỏ nước thừa, súc sạch nếu muốn tái chế; nếu dính dầu mỡ đặc thì bỏ rác khác. |
| `1` | `lon_nhom` | Lon nhôm (lon bia, nước ngọt) | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Đổ cạn nước, bóp dẹt lon. | **Rác khác (Xám)**: Đổ hết nước ngọt/bia thừa để tránh kiến gián, tráng qua nước trước khi tái chế. |
| `2` | `hop_sua_giay` | Vỏ hộp sữa giấy (Tetra Pak) | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Cắt góc, tráng sạch, làm phẳng. | **Rác khác (Xám)**: Sữa thừa gây mùi hôi và mốc giấy. Bỏ vào rác khác hoặc súc sạch để tái chế. |
| `3` | `coc_nhua_tra_sua` | Cốc nhựa trà sữa, cà phê mang đi | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Bỏ ống hút/màng ép, rửa sạch cốc nhựa. | **Rác khác (Xám)**: Đổ đá và trân châu/thạch vào **Rác thực phẩm**, vỏ cốc bẩn bỏ vào **Rác khác**. |
| `4` | `giay_bao_sach_vo` | Giấy báo, sách vở, giấy văn phòng | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Xếp gọn, buộc chặt, giữ khô ráo. | **Rác khác (Xám)**: Giấy ướt sũng hoặc thấm dầu mỡ không thể tái chế, bỏ vào thùng rác khác. |
| `5` | `thung_bia_carton` | Thùng bìa carton, hộp giấy | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Gỡ băng dính nhựa, gấp phẳng. | **Rác khác (Xám)**: Phần bìa dính dầu mỡ thức ăn (như đáy hộp pizza) phải xé bỏ vào rác khác. |
| `6` | `chai_lo_thuy_tinh` | Chai lọ thủy tinh (nước mắm, gia vị) | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Tráng sạch cặn mắm/dầu, tháo nắp nhựa. | **Rác khác (Xám)**: Đổ bỏ cặn gia vị thừa, tráng sạch trước khi đưa vào luồng tái chế. |
| `7` | `do_hop_kim_loai` | Hộp sắt/thiếc đựng thực phẩm (đồ hộp) | Rác tái chế | **Có** | **Rác tái chế (Cam)**: Rửa sạch dầu/sốt, cẩn thận cạnh sắc. | **Rác khác (Xám)**: Vét hết thịt/cá thừa vào **Rác thực phẩm**, vỏ hộp dính mỡ bỏ rác khác nếu không rửa. |
| `8` | `rau_cu_qua_thua` | Rau củ quả héo, vỏ trái cây | Rác thực phẩm | Không | *Không áp dụng* (`is_clean=false, has_food=true`) | **Rác thực phẩm (Xanh lá)**: Để ráo nước, bỏ túi ni-lông bọc ngoài trước khi đổ vào thùng hữu cơ. |
| `9` | `thuc_an_thua_com_canh` | Cơm canh thừa, bún phở, thịt cá | Rác thực phẩm | Không | *Không áp dụng* (`is_clean=false, has_food=true`) | **Rác thực phẩm (Xanh lá)**: Chắt bỏ nước canh thừa vào cống thoát có lưới lọc, phần cái bỏ thùng xanh. |
| `10` | `ba_tra_ca_phe` | Bã trà, bã cà phê (không túi lọc nilon) | Rác thực phẩm | Không | *Không áp dụng* (`is_clean=false, has_food=true`) | **Rác thực phẩm (Xanh lá)**: Bỏ trực tiếp vào thùng rác thực phẩm hoặc ủ phân bón cây. |
| `11` | `vo_trung` | Vỏ trứng gà, trứng vịt | Rác thực phẩm | Không | *Không áp dụng* (`is_clean=false, has_food=true`) | **Rác thực phẩm (Xanh lá)**: Bóp vụn vỏ trứng và bỏ vào thùng rác thực phẩm màu xanh lá. |
| `12` | `la_chuoi_la_dong` | Lá chuối, lá dong gói bánh/xôi | Rác thực phẩm | **Có** | **Rác thực phẩm (Xanh lá)**: Lá tự nhiên chỉ dính cơm/xôi nhẹ, tháo dây lạt nilon, bỏ thùng thực phẩm. | **Rác khác (Xám)**: Nếu lá quấn băng dính nhựa dày hoặc dính nilon không tách được, bỏ vào thùng rác khác. |
| `13` | `hop_xop_dung_thuc_an` | Hộp xốp đựng cơm, xôi, bún | Rác khác | **Có** | **Rác khác (Xám)**: Xốp dùng 1 lần không tái chế được tại hộ gia đình. Bẻ gọn, bỏ thùng xám. | **Rác khác (Xám)**: Bắt buộc trút hết cơm/thức ăn thừa sang thùng **Rác thực phẩm**, vỏ hộp xốp bỏ thùng **Rác khác**. |
| `14` | `tui_nilon_ban` | Túi ni-lông mỏng, màng bọc thực phẩm | Rác khác | **Có** | **Rác tái chế (Cam)**: Túi ni-lông dày, sạch, khô ráo có thể gom lại cho vào túi tái chế. | **Rác khác (Xám)**: Túi ni-lông ướt, rách hoặc dính máu cá/thức ăn bắt buộc bỏ thùng rác sinh hoạt khác. |
| `15` | `giay_an_da_qua_su_dung` | Giấy ăn, khăn giấy đã lau dầu mỡ | Rác khác | Không | *Không áp dụng* (`is_clean=false, has_food=false`) | **Rác khác (Xám)**: Sợi giấy ngắn và nhiễm khuẩn/dầu mỡ, tuyệt đối không bỏ vào thùng giấy tái chế. |
| `16` | `khau_trang_y_te` | Khẩu trang y tế đã qua sử dụng | Rác khác | Không | *Không áp dụng* (`is_clean=false, has_food=false`) | **Rác khác (Xám)**: Gập đôi mặt trong lại, buộc gọn bằng dây đeo để tránh phát tán mầm bệnh, bỏ thùng xám. |
| `17` | `manh_gom_su_thuy_tinh_vo` | Mảnh bát đĩa sành sứ, thủy tinh vỡ | Rác khác | Không | *Không áp dụng* (`is_clean=true, has_food=false`) | **Rác khác (Xám)**: Bọc kỹ bằng nhiều lớp giấy báo dày để không đâm thủng túi và gây thương tích cho công nhân. |
| `18` | `pin_da_qua_su_dung` | Pin tiểu, pin điện thoại hỏng (Nguy hại) | Rác khác (Nguy hại) | Không | *Không áp dụng* (`is_clean=true, has_food=false`) | **Rác khác / Điểm thu hồi nguy hại (Xám + Cảnh báo đỏ)**: Không vứt lẫn rác thường! Gom riêng mang tới điểm thu hồi pin. |
| `19` | `vo_goi_mi_bim_bim` | Vỏ gói mì tôm, vỏ bim bim, túi tráng nhôm | Rác khác | **Có** | **Rác khác (Xám)**: Bao bì đa lớp tráng nhôm không tái chế cơ học được, xếp gọn bỏ thùng xám. | **Rác khác (Xám)**: Đổ hết vụn mì/gia vị thừa vào **Rác thực phẩm**, vỏ gói bỏ vào thùng **Rác khác**. |

---

## 3. Phân Bổ Tỷ Lệ & Độ Phủ Tình Huống (Coverage Summary)

- **Tổng số lớp MVP**: `20` lớp (`class_index: 0..19`).
- **Phân bổ theo Nhóm rác gốc**:
  - **Rác tái chế (`recyclable`)**: 8 lớp (`40%`) — Nhựa PET, Nhôm, Tetra Pak, Cốc nhựa PP/PET, Giấy báo, Carton, Thủy tinh nguyên vẹn, Đồ hộp kim loại.
  - **Rác thực phẩm (`food_waste`)**: 5 lớp (`25%`) — Rau củ quả, Cơm canh thừa, Bã trà/cà phê, Vỏ trứng, Lá chuối/lá dong.
  - **Rác sinh hoạt khác & Nguy hại (`residual_waste`)**: 7 lớp (`35%`) — Hộp xốp, Túi nilon, Giấy ăn bẩn, Khẩu trang, Sành sứ/thủy tinh vỡ, Pin thải nguy hại, Vỏ bao bì phức hợp (mì tôm/bim bim).
- **Tỷ lệ lớp có kiểm tra trạng thái (`requires_clarification: true`)**: **12 / 20 lớp (`60%`)**, đảm bảo tính năng cốt lõi **State-Aware Clarification Dialog (US-02)** được kích hoạt thường xuyên và thực chất trong quá trình kiểm thử.
