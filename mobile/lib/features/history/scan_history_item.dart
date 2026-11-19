import '../knowledge_base/waste_rule_model.dart';

/// Mục lịch sử quét và ghi nhận chuỗi phân loại đúng (Streak)
class ScanHistoryItem {
  final String id;
  final String itemName;
  final WasteStream resolvedStream;
  final DateTime timestamp;
  final int? classIndex;
  final String? itemId;
  final double? confidence;
  final int pointsAwarded;

  const ScanHistoryItem({
    required this.id,
    required this.itemName,
    required this.resolvedStream,
    required this.timestamp,
    this.classIndex,
    this.itemId,
    this.confidence,
    this.pointsAwarded = 10,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'item_name': itemName,
        'resolved_stream': _streamToKey(resolvedStream),
        'timestamp': timestamp.toIso8601String(),
        if (classIndex != null) 'class_index': classIndex,
        if (itemId != null) 'item_id': itemId,
        if (confidence != null) 'confidence': confidence,
        'points_awarded': pointsAwarded,
      };

  factory ScanHistoryItem.fromJson(Map<String, dynamic> json) {
    return ScanHistoryItem(
      id: json['id'] as String,
      itemName: json['item_name'] as String,
      resolvedStream: wasteStreamFromKey(json['resolved_stream'] as String),
      timestamp: DateTime.parse(json['timestamp'] as String),
      classIndex: json['class_index'] as int?,
      itemId: json['item_id'] as String?,
      confidence: (json['confidence'] as num?)?.toDouble(),
      pointsAwarded: (json['points_awarded'] as int?) ?? 10,
    );
  }

  static String _streamToKey(WasteStream stream) {
    switch (stream) {
      case WasteStream.recyclable:
        return 'recyclable';
      case WasteStream.foodWaste:
        return 'food_waste';
      case WasteStream.residualWaste:
        return 'residual_waste';
    }
  }
}
