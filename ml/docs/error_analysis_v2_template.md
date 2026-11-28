# EcoSort v2 · Phân tích lỗi trên ảnh Việt Nam thật (issue #15)

> Mẫu cho `ml/reports/error_analysis_v2.md`. Chỉ điền số liệu đã đo bằng các lệnh trong `ml/README.md` (mục v2).
> Mỗi con số ghi kèm file nguồn. Tách rõ **nguyên nhân đã kiểm tra** và **giả thuyết**.

## 1. Dữ liệu
- Nguồn ảnh VN: Drive `EcoSort_Dataset` (#11 Yến, #12 Linh), ngày tải: …, người QA: …
- QA (`ml/reports/v2/qa/qa_summary.json`): số file nhận / dùng được / loại theo lý do (heic, hỏng, mờ, sai lớp, trùng) theo lớp.
- Lớp được thay HF bằng VN (`--min-vn-objects 8`): … · Lớp còn trộn HF+VN: … · Lớp VN còn thiếu vật: …
- Split (`ml/reports/v2/split_verification.json`): bảng train/val/test × nguồn (ảnh / vật); giao `object_id` train–val, train–test, val–test = 0/0/0.
- Test VN đóng băng (`ml/reports/v2/test_vn_manifest.json`): … ảnh, … vật, fingerprint `…`, nhãn có mặt: …, lớp VN vắng mặt trong test: …

## 2. So sánh công bằng v1 vs v2 (cùng danh sách test VN, cùng tiền xử lý)
<!-- dán ml/reports/v2/vn_comparison/tables.md -->
- Macro-F1 tính trên tập nhãn có mặt trong test VN (ghi rõ danh sách). Mô hình vẫn dự đoán đủ 20 nhãn.
- Lớp v2 giảm: ghi đúng mức giảm (pp) và mẫu số.

## 3. Ma trận nhầm lẫn và các cặp nhầm chính
- Tham chiếu baseline: `ml/reports/confusion_matrix_20classes.png` (dự đoán **Keras v1** trên test open-data cũ, sinh bởi `train_and_export.py`) — không cùng tập với mục 2.
- Mới: `ml/reports/v2/vn_comparison/confusion_vn_v1.png`, `confusion_vn_v2.png` (TFLite, test VN đóng băng, thứ tự 20 nhãn theo `labels.txt`).

| Nhãn thật → dự đoán | v1 (nhầm/ảnh lớp gốc) | v2 | Quan sát khi xem ảnh (`predictions.csv`) | Đã kiểm tra / giả thuyết |
|---|---|---|---|---|
| … | … | … | … | … |

## 4. Hiện vật và phép đo
- `mobile/assets/models/ecosort_v2.tflite`: … byte (< 5 242 880), sha256 `…`; hợp đồng [1,224,224,3] float32 [0,255] → [1,20] softmax.
- Drift (`ml/reports/v2/tflite_verification.json`): Keras v2 …, TFLite v2 …, |Δ| … ≤ 0.02, n = …, test fingerprint `…`.
- Lệnh đã chạy, môi trường (Python, TensorFlow, GPU).
- Baseline lịch sử (chỉ để mô tả): TFLite v1 70,44% (PR #8), Keras v1 68,92%, 3 luồng 84,97% trên test open-data cũ.

## 5. Kết luận cho nhóm
- Lớp cải thiện / giảm, giới hạn (số vật, người chụp, nền), ảnh cần chụp thêm.
- Đề xuất cho Yến: dùng v2 hay giữ v1, kèm bằng chứng.
