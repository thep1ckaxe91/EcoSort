/// Bản ghi phản hồi sai ("Kết quả này sai?") lưu cục bộ phục vụ Active Learning (US-04).
/// Tuyệt đối không chứa dữ liệu sinh trắc học/khuôn mặt; chỉ lưu siêu dữ liệu ẩn danh.
class FeedbackReport {
  final String reportId;
  final String anonymousDeviceId;
  final DateTime timestamp;
  final int predictedClassIndex;
  final String predictedItemId;
  final int correctedClassIndex;
  final String correctedItemId;
  final double confidence;
  final String? note;
  final bool synced;

  const FeedbackReport({
    required this.reportId,
    required this.anonymousDeviceId,
    required this.timestamp,
    required this.predictedClassIndex,
    required this.predictedItemId,
    required this.correctedClassIndex,
    required this.correctedItemId,
    required this.confidence,
    this.note,
    this.synced = false,
  });

  FeedbackReport copyWith({bool? synced}) => FeedbackReport(
        reportId: reportId,
        anonymousDeviceId: anonymousDeviceId,
        timestamp: timestamp,
        predictedClassIndex: predictedClassIndex,
        predictedItemId: predictedItemId,
        correctedClassIndex: correctedClassIndex,
        correctedItemId: correctedItemId,
        confidence: confidence,
        note: note,
        synced: synced ?? this.synced,
      );

  Map<String, dynamic> toJson() => {
        'report_id': reportId,
        'anonymous_device_id': anonymousDeviceId,
        'timestamp': timestamp.toIso8601String(),
        'predicted_class_index': predictedClassIndex,
        'predicted_item_id': predictedItemId,
        'corrected_class_index': correctedClassIndex,
        'corrected_item_id': correctedItemId,
        'confidence': confidence,
        if (note != null && note!.isNotEmpty) 'note': note,
        'synced': synced,
      };

  factory FeedbackReport.fromJson(Map<String, dynamic> json) {
    return FeedbackReport(
      reportId: json['report_id'] as String,
      anonymousDeviceId: json['anonymous_device_id'] as String,
      timestamp: DateTime.parse(json['timestamp'] as String),
      predictedClassIndex: json['predicted_class_index'] as int,
      predictedItemId: json['predicted_item_id'] as String,
      correctedClassIndex: json['corrected_class_index'] as int,
      correctedItemId: json['corrected_item_id'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      note: json['note'] as String?,
      synced: (json['synced'] as bool?) ?? false,
    );
  }
}
