/// Kết quả nhận diện on-device từ mô hình TFLite
class ClassifierResult {
  final String label;
  final double confidence;
  final int inferenceTimeMs;
  final bool requiresClarification;

  const ClassifierResult({
    required this.label,
    required this.confidence,
    required this.inferenceTimeMs,
    this.requiresClarification = false,
  });

  bool get isConfident => confidence >= 0.70;
}

