import 'dart:convert';
import 'package:flutter/services.dart' show AssetBundle, rootBundle;
import 'classifier_model.dart';

/// Giao diện trừu tượng cho bộ phân loại rác on-device theo Clean Architecture.
/// Cho phép tráo đổi giữa Mock Classifier (trong môi trường test / dev)
/// và TFLite Classifier thực tế khi chạy trên thiết bị Android.
abstract class WasteClassifier {
  /// Khởi tạo tài nguyên mô hình và danh sách nhãn.
  Future<void> initialize();

  /// Phân loại ảnh đầu vào và trả về [ClassifierResult].
  /// [imageInput] có thể là đường dẫn file ảnh, mảng byte hoặc camera image buffer.
  Future<ClassifierResult> classifyImage(dynamic imageInput);

  /// Kiểm tra bộ phân loại đã sẵn sàng suy luận chưa.
  bool get isReady;

  /// Giải phóng bộ nhớ và tài nguyên liên kết.
  void dispose();
}

/// Triển khai giả lập (Mock) cho bộ phân loại rác EcoSort.
/// Hỗ trợ đọc nhãn từ `assets/kb/labels.txt`, trả về kết quả cấu hình sẵn
/// hoặc xoay vòng theo danh sách 20 lớp rác với độ trễ < 150ms.
class MockWasteClassifier implements WasteClassifier {
  static const String defaultLabelsAssetPath = 'assets/kb/labels.txt';

  final List<String> _labels;
  final String? _defaultLabel;
  bool _isReady = false;

  // Cấu hình kết quả mock tùy chỉnh
  String? _forcedLabel;
  double? _forcedConfidence;
  int? _forcedInferenceTimeMs;
  int? _forcedClassIndex;

  MockWasteClassifier({
    List<String>? labels,
    String? defaultLabel,
  })  : _labels = labels ?? [],
        _defaultLabel = defaultLabel;

  @override
  bool get isReady => _isReady;

  List<String> get labels => List.unmodifiable(_labels);

  @override
  Future<void> initialize({
    AssetBundle? bundle,
    String labelsPath = defaultLabelsAssetPath,
  }) async {
    if (_labels.isEmpty) {
      final source = bundle ?? rootBundle;
      try {
        final content = await source.loadString(labelsPath);
        final lines = const LineSplitter()
            .convert(content)
            .map((line) => line.trim())
            .where((line) => line.isNotEmpty)
            .toList(growable: false);
        _labels.addAll(lines);
      } catch (e) {
        // Fallback danh sách 20 lớp rác chuẩn nếu không load được asset
        _labels.addAll(defaultEcoSortLabels);
      }
    }
    _isReady = true;
  }

  /// Cấu hình kết quả mock cụ thể cho các bài kiểm thử hoặc kịch bản demo
  void setMockResult({
    String? label,
    double? confidence,
    int? inferenceTimeMs,
    int? classIndex,
  }) {
    _forcedLabel = label;
    _forcedConfidence = confidence;
    _forcedInferenceTimeMs = inferenceTimeMs;
    _forcedClassIndex = classIndex;
  }

  /// Xóa cấu hình mock cố định để quay về mặc định
  void resetMockResult() {
    _forcedLabel = null;
    _forcedConfidence = null;
    _forcedInferenceTimeMs = null;
    _forcedClassIndex = null;
  }

  @override
  Future<ClassifierResult> classifyImage(dynamic imageInput) async {
    if (!_isReady) {
      await initialize();
    }

    final targetLabel = _forcedLabel ??
        _defaultLabel ??
        (_labels.isNotEmpty ? _labels.first : 'chai_nhua_pet');
    final targetConfidence = _forcedConfidence ?? 0.88;
    final targetTimeMs = _forcedInferenceTimeMs ?? 42; // Phù hợp yêu cầu < 150ms

    int? targetIndex = _forcedClassIndex;
    if (targetIndex == null && _labels.isNotEmpty) {
      final idx = _labels.indexOf(targetLabel);
      if (idx != -1) {
        targetIndex = idx;
      }
    }

    return ClassifierResult(
      label: targetLabel,
      confidence: targetConfidence,
      inferenceTimeMs: targetTimeMs,
      classIndex: targetIndex,
    );
  }

  @override
  void dispose() {
    _isReady = false;
  }

  /// 20 lớp rác chuẩn của EcoSort MVP theo Luật BVMT 2020 & labels.txt
  static const List<String> defaultEcoSortLabels = [
    'chai_nhua_pet',
    'lon_nhom',
    'hop_sua_giay',
    'coc_nhua_tra_sua',
    'giay_bao_sach_vo',
    'thung_bia_carton',
    'chai_lo_thuy_tinh',
    'do_hop_kim_loai',
    'rau_cu_qua_thua',
    'thuc_an_thua_com_canh',
    'ba_tra_ca_phe',
    'vo_trung',
    'la_chuoi_la_dong',
    'hop_xop_dung_thuc_an',
    'tui_nilon_ban',
    'giay_an_da_qua_su_dung',
    'khau_trang_y_te',
    'manh_gom_su_thuy_tinh_vo',
    'pin_da_qua_su_dung',
    'vo_goi_mi_bim_bim',
  ];
}

