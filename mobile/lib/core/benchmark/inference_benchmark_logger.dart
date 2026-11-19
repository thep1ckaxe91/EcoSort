import 'dart:convert';

/// Một mẫu đo hiệu năng suy luận TFLite & thời gian tác vụ End-to-End (US-01 AC-01.1 & AC-01.3).
class BenchmarkSample {
  final DateTime timestamp;
  final int classIndex;
  final double confidence;
  final int inferenceMs;
  final int totalTaskMs;

  const BenchmarkSample({
    required this.timestamp,
    required this.classIndex,
    required this.confidence,
    required this.inferenceMs,
    required this.totalTaskMs,
  });

  Map<String, dynamic> toJson() => {
        'timestamp': timestamp.toIso8601String(),
        'class_index': classIndex,
        'confidence': confidence,
        'inference_ms': inferenceMs,
        'total_task_ms': totalTaskMs,
      };
}

/// Thống kê tổng hợp dùng để xuất báo cáo benchmark trên máy Android thật (US-01).
class BenchmarkSummary {
  static const double maxInferenceTargetMs = 200.0;
  static const double maxTaskTimeTargetMs = 8000.0;

  final int sampleCount;
  final double meanInferenceMs;
  final double p50InferenceMs;
  final double p95InferenceMs;
  final double meanTaskTimeMs;
  final double p95TaskTimeMs;
  final int lowConfidenceCount;

  const BenchmarkSummary({
    required this.sampleCount,
    required this.meanInferenceMs,
    required this.p50InferenceMs,
    required this.p95InferenceMs,
    required this.meanTaskTimeMs,
    required this.p95TaskTimeMs,
    required this.lowConfidenceCount,
  });

  bool get meetsInferenceLatencyTarget =>
      sampleCount > 0 && p95InferenceMs <= maxInferenceTargetMs;

  bool get meetsTaskTimeTarget =>
      sampleCount > 0 && p95TaskTimeMs <= maxTaskTimeTargetMs;

  Map<String, dynamic> toJson() => {
        'sample_count': sampleCount,
        'mean_inference_ms': double.parse(meanInferenceMs.toStringAsFixed(2)),
        'p50_inference_ms': double.parse(p50InferenceMs.toStringAsFixed(2)),
        'p95_inference_ms': double.parse(p95InferenceMs.toStringAsFixed(2)),
        'mean_task_time_ms': double.parse(meanTaskTimeMs.toStringAsFixed(2)),
        'p95_task_time_ms': double.parse(p95TaskTimeMs.toStringAsFixed(2)),
        'low_confidence_count': lowConfidenceCount,
        'meets_inference_target_200ms': meetsInferenceLatencyTarget,
        'meets_task_time_target_8000ms': meetsTaskTimeTarget,
      };
}

/// Bộ ghi log vòng (ring buffer) đo latency on-device cho giai đoạn test `ecosort_v1.tflite`.
class InferenceBenchmarkLogger {
  static const double confidenceThreshold = 0.60;

  final int maxSamples;
  final List<BenchmarkSample> _samples = [];

  InferenceBenchmarkLogger({this.maxSamples = 500});

  List<BenchmarkSample> get samples => List.unmodifiable(_samples);

  void record({
    required int classIndex,
    required double confidence,
    required int inferenceMs,
    required int totalTaskMs,
    DateTime? timestamp,
  }) {
    if (_samples.length >= maxSamples) {
      _samples.removeAt(0);
    }
    _samples.add(
      BenchmarkSample(
        timestamp: timestamp ?? DateTime.now(),
        classIndex: classIndex,
        confidence: confidence,
        inferenceMs: inferenceMs,
        totalTaskMs: totalTaskMs,
      ),
    );
  }

  void clear() => _samples.clear();

  BenchmarkSummary summarize() {
    if (_samples.isEmpty) {
      return const BenchmarkSummary(
        sampleCount: 0,
        meanInferenceMs: 0,
        p50InferenceMs: 0,
        p95InferenceMs: 0,
        meanTaskTimeMs: 0,
        p95TaskTimeMs: 0,
        lowConfidenceCount: 0,
      );
    }

    final inf = _samples.map((s) => s.inferenceMs).toList()..sort();
    final task = _samples.map((s) => s.totalTaskMs).toList()..sort();
    final meanInf = inf.reduce((a, b) => a + b) / inf.length;
    final meanTask = task.reduce((a, b) => a + b) / task.length;
    final lowConf =
        _samples.where((s) => s.confidence < confidenceThreshold).length;

    return BenchmarkSummary(
      sampleCount: _samples.length,
      meanInferenceMs: meanInf,
      p50InferenceMs: _percentile(inf, 0.50),
      p95InferenceMs: _percentile(inf, 0.95),
      meanTaskTimeMs: meanTask,
      p95TaskTimeMs: _percentile(task, 0.95),
      lowConfidenceCount: lowConf,
    );
  }

  String exportReportJson({String? deviceModel, String? modelName}) {
    return jsonEncode({
      if (deviceModel != null) 'device_model': deviceModel,
      if (modelName != null) 'model_name': modelName,
      'summary': summarize().toJson(),
      'samples': _samples.map((s) => s.toJson()).toList(growable: false),
    });
  }

  static double _percentile(List<int> sorted, double q) {
    if (sorted.length == 1) return sorted.first.toDouble();
    final pos = (sorted.length - 1) * q;
    final lower = pos.floor();
    final upper = pos.ceil();
    if (lower == upper) return sorted[lower].toDouble();
    final weight = pos - lower;
    return sorted[lower] * (1 - weight) + sorted[upper] * weight;
  }
}
