import 'dart:convert';
import 'dart:math';
import '../../core/storage/key_value_store.dart';
import 'feedback_report_model.dart';

/// Ngoại lệ ném ra nếu ứng dụng cố ghi báo cáo phản hồi khi người dùng chưa xác nhận Opt-In (US-04 AC-04.4).
class FeedbackConsentRequiredException implements Exception {
  final String message;
  const FeedbackConsentRequiredException([
    this.message = 'Người dùng chưa đồng ý (Opt-In) gửi dữ liệu phản hồi ẩn danh.',
  ]);

  @override
  String toString() => 'FeedbackConsentRequiredException: $message';
}

/// Hàng đợi phản hồi lỗi cục bộ 100% offline (US-04 AC-04.3 & AC-04.4).
class FeedbackRepository {
  static const int maxQueuedReports = 500;

  static const String _kOptIn = 'ecosort_feedback_privacy_opt_in';
  static const String _kAnonId = 'ecosort_anonymous_device_uuid';
  static const String _kQueue = 'ecosort_feedback_queue_json';

  final KeyValueStore _store;
  final Random _rng;

  FeedbackRepository(this._store, {Random? random})
      : _rng = random ?? Random.secure();

  static Future<FeedbackRepository> create() async {
    final store = await SharedPreferencesStore.create();
    return FeedbackRepository(store);
  }

  /// Trạng thái đồng ý thu thập dữ liệu phản hồi ẩn danh một lần (Opt-In).
  bool get hasPrivacyOptIn => _store.getBool(_kOptIn) ?? false;

  Future<void> setPrivacyOptIn(bool granted) => _store.setBool(_kOptIn, granted);

  /// Sinh và lưu UUID v4 ẩn danh cho thiết bị (không gắn thông tin định danh cá nhân).
  Future<String> getOrCreateAnonymousDeviceId() async {
    final existing = _store.getString(_kAnonId);
    if (existing != null && existing.isNotEmpty) return existing;
    final generated = _generateUuidV4();
    await _store.setString(_kAnonId, generated);
    return generated;
  }

  List<FeedbackReport> loadAllReports() {
    final raw = _store.getString(_kQueue);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final list = jsonDecode(raw) as List<dynamic>;
      return list
          .map((e) => FeedbackReport.fromJson(e as Map<String, dynamic>))
          .toList(growable: false);
    } catch (_) {
      return const [];
    }
  }

  List<FeedbackReport> getPendingReports() =>
      loadAllReports().where((r) => !r.synced).toList(growable: false);

  /// Ghi nhận một phản hồi sai vào hàng đợi offline. Bắt buộc đã có Opt-In trước.
  Future<FeedbackReport> submitReport({
    required int predictedClassIndex,
    required String predictedItemId,
    required int correctedClassIndex,
    required String correctedItemId,
    required double confidence,
    String? note,
    DateTime? now,
  }) async {
    if (!hasPrivacyOptIn) {
      throw const FeedbackConsentRequiredException();
    }

    final current = now ?? DateTime.now();
    final anonId = await getOrCreateAnonymousDeviceId();
    final report = FeedbackReport(
      reportId: _generateUuidV4(),
      anonymousDeviceId: anonId,
      timestamp: current,
      predictedClassIndex: predictedClassIndex,
      predictedItemId: predictedItemId,
      correctedClassIndex: correctedClassIndex,
      correctedItemId: correctedItemId,
      confidence: confidence,
      note: note?.trim(),
      synced: false,
    );

    final updated = <FeedbackReport>[report, ...loadAllReports()];
    if (updated.length > maxQueuedReports) {
      updated.removeRange(maxQueuedReports, updated.length);
    }
    await _saveAll(updated);
    return report;
  }

  /// Đánh dấu danh sách bản ghi đã đồng bộ thành công (khi có mạng / export).
  Future<void> markSynced(Iterable<String> reportIds) async {
    final idSet = reportIds.toSet();
    final updated = loadAllReports()
        .map((r) => idSet.contains(r.reportId) ? r.copyWith(synced: true) : r)
        .toList(growable: false);
    await _saveAll(updated);
  }

  /// Xuất toàn bộ hàng đợi chưa đồng bộ ra JSON string để chẩn đoán hoặc đồng bộ batch.
  String exportPendingJson() {
    final pending = getPendingReports();
    return jsonEncode(pending.map((e) => e.toJson()).toList(growable: false));
  }

  Future<void> _saveAll(List<FeedbackReport> reports) => _store.setString(
        _kQueue,
        jsonEncode(reports.map((e) => e.toJson()).toList(growable: false)),
      );

  String _generateUuidV4() {
    final bytes = List<int>.generate(16, (_) => _rng.nextInt(256));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    String hex(int b) => b.toRadixString(16).padLeft(2, '0');
    final h = bytes.map(hex).join();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-'
        '${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20, 32)}';
  }
}
