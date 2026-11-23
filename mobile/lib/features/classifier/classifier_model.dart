/// Kết quả nhận diện on-device từ mô hình TFLite
class ClassifierResult {
  final String label;
  final double confidence;
  final int inferenceTimeMs;
  final bool requiresClarification;
  final int? classIndex;

  const ClassifierResult({
    required this.label,
    required this.confidence,
    required this.inferenceTimeMs,
    this.requiresClarification = false,
    this.classIndex,
  });

  /// Ngưỡng tự tin tối thiểu (60%) theo PRD & review HCI.
  /// Dưới 60% sẽ nhắc người dùng chụp lại rõ hơn hoặc bật đèn flash.
  bool get isConfident => confidence >= 0.60;
}

