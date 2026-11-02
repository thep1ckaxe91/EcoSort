import '../knowledge_base/waste_rule_model.dart';

/// Mục lịch sử quét và ghi nhận chuỗi phân loại đúng (Streak)
class ScanHistoryItem {
  final String id;
  final String itemName;
  final WasteStream resolvedStream;
  final DateTime timestamp;

  const ScanHistoryItem({
    required this.id,
    required this.itemName,
    required this.resolvedStream,
    required this.timestamp,
  });
}

