import 'dart:convert';
import 'package:crypto/crypto.dart';
import '../../core/storage/key_value_store.dart';
import '../knowledge_base/waste_rule_model.dart';
import 'scan_history_item.dart';

/// Trạng thái check-in một ngày trong biểu đồ 7 ngày gần nhất (US-05 AC-05.3).
class DailyCheckIn {
  final DateTime date;
  final bool completed;
  final int itemsSorted;

  const DailyCheckIn({
    required this.date,
    required this.completed,
    required this.itemsSorted,
  });
}

/// Snapshot tổng hợp điểm Eco-Points, chuỗi ngày (streak) và kiểm tra toàn vẹn.
class EcoStreakSummary {
  final int ecoPoints;
  final int dailyStreak;
  final int todayCount;
  final int totalSorted;
  final DateTime? lastActivityAt;
  final bool streakWasReset;
  final int bonusAwarded;
  final bool integrityValid;

  const EcoStreakSummary({
    required this.ecoPoints,
    required this.dailyStreak,
    required this.todayCount,
    required this.totalSorted,
    required this.lastActivityAt,
    required this.streakWasReset,
    required this.bonusAwarded,
    required this.integrityValid,
  });
}

/// Quản lý lưu trữ cục bộ Eco-Streak, Eco-Points và lịch sử quét (US-05).
/// - +10 điểm cho mỗi lần phân loại hợp lệ (AC-05.2).
/// - +50 điểm thưởng mỗi mốc chuỗi 7 ngày liên tiếp (7, 14, 21...).
/// - Tăng streak tối đa +1 mỗi ngày lịch địa phương; reset về 0 nếu quá 48h (AC-05.1).
/// - Ký HMAC SHA-256 lên trạng thái điểm/chuỗi để chống sửa tay cơ bản (AC-05.4).
class EcoStreakRepository {
  static const int pointsPerSort = 10;
  static const int sevenDayBonusPoints = 50;
  static const int maxHistoryItems = 200;

  static const String _kPoints = 'ecosort_eco_points';
  static const String _kStreak = 'ecosort_daily_streak';
  static const String _kLastActivity = 'ecosort_last_activity_iso';
  static const String _kChecksum = 'ecosort_streak_hmac';
  static const String _kHistory = 'ecosort_scan_history_json';

  final KeyValueStore _store;
  final List<int> _hmacKey;

  EcoStreakRepository(
    this._store, {
    String hmacSecret = 'ecosort-vnu-uet-mvp-local-integrity-v1',
  }) : _hmacKey = utf8.encode(hmacSecret);

  static Future<EcoStreakRepository> create() async {
    final store = await SharedPreferencesStore.create();
    return EcoStreakRepository(store);
  }

  String _computeHmac(int points, int streak, String lastActivityIso) {
    final payload = '$points|$streak|$lastActivityIso';
    final hmac = Hmac(sha256, _hmacKey);
    return hmac.convert(utf8.encode(payload)).toString();
  }

  /// Kiểm tra chữ ký HMAC SHA-256 trên dữ liệu đã lưu.
  bool verifyIntegrity() {
    final storedHmac = _store.getString(_kChecksum);
    if (storedHmac == null) {
      // Chưa có dữ liệu điểm nào được ghi => hợp lệ mặc định.
      return _store.getInt(_kPoints) == null && _store.getInt(_kStreak) == null;
    }
    final points = _store.getInt(_kPoints) ?? 0;
    final streak = _store.getInt(_kStreak) ?? 0;
    final lastIso = _store.getString(_kLastActivity) ?? '';
    return storedHmac == _computeHmac(points, streak, lastIso);
  }

  /// Trả về danh sách lịch sử quét mới nhất trước.
  List<ScanHistoryItem> loadHistory() {
    final raw = _store.getString(_kHistory);
    if (raw == null || raw.isEmpty) return const [];
    try {
      final list = jsonDecode(raw) as List<dynamic>;
      return list
          .map((e) => ScanHistoryItem.fromJson(e as Map<String, dynamic>))
          .toList(growable: false);
    } catch (_) {
      return const [];
    }
  }

  /// Đọc tổng hợp trạng thái hiện tại, tự động phản ánh việc hết hạn streak (> 48h).
  EcoStreakSummary getSummary({DateTime? now}) {
    final current = now ?? DateTime.now();
    final integrity = verifyIntegrity();
    final points = integrity ? (_store.getInt(_kPoints) ?? 0) : 0;
    var streak = integrity ? (_store.getInt(_kStreak) ?? 0) : 0;
    final lastIso = _store.getString(_kLastActivity);
    final lastAt =
        (lastIso != null && lastIso.isNotEmpty) ? DateTime.tryParse(lastIso) : null;

    var reset = false;
    if (lastAt != null && streak > 0 && _isStreakExpired(lastAt, current)) {
      streak = 0;
      reset = true;
    }

    final history = loadHistory();
    final todayKey = _dayKey(current);
    final todayCount =
        history.where((h) => _dayKey(h.timestamp) == todayKey).length;

    return EcoStreakSummary(
      ecoPoints: points,
      dailyStreak: streak,
      todayCount: todayCount,
      totalSorted: history.length,
      lastActivityAt: lastAt,
      streakWasReset: reset,
      bonusAwarded: 0,
      integrityValid: integrity,
    );
  }

  /// Ghi nhận một lượt phân loại rác đã xác nhận, cộng điểm và cập nhật chuỗi ngày.
  Future<EcoStreakSummary> recordConfirmedSort({
    required String itemName,
    required WasteStream stream,
    int? classIndex,
    String? itemId,
    double? confidence,
    DateTime? now,
  }) async {
    final current = now ?? DateTime.now();
    final integrity = verifyIntegrity();
    var points = integrity ? (_store.getInt(_kPoints) ?? 0) : 0;
    var streak = integrity ? (_store.getInt(_kStreak) ?? 0) : 0;

    final lastIso = _store.getString(_kLastActivity);
    final lastAt =
        (lastIso != null && lastIso.isNotEmpty) ? DateTime.tryParse(lastIso) : null;

    var streakReset = false;
    var bonus = 0;

    if (lastAt == null) {
      streak = 1;
    } else if (_isSameCalendarDay(lastAt, current)) {
      // Đã tính streak cho ngày hôm nay rồi (tối đa +1 mỗi ngày).
      if (streak == 0) streak = 1;
    } else if (_isStreakExpired(lastAt, current)) {
      // Bỏ lỡ >= 48 giờ hoặc cách >= 2 ngày lịch => bắt đầu lại từ 1 cho hôm nay.
      streak = 1;
      streakReset = true;
    } else {
      // Ngày kế tiếp liên tục trong khung <= 48 giờ.
      streak += 1;
      if (streak % 7 == 0) {
        bonus = sevenDayBonusPoints;
      }
    }

    final earned = pointsPerSort + bonus;
    points += earned;

    final currentIso = current.toIso8601String();
    await _store.setInt(_kPoints, points);
    await _store.setInt(_kStreak, streak);
    await _store.setString(_kLastActivity, currentIso);
    await _store.setString(_kChecksum, _computeHmac(points, streak, currentIso));

    final existing = loadHistory();
    final entry = ScanHistoryItem(
      id: '${current.microsecondsSinceEpoch}_${itemId ?? itemName.hashCode}',
      itemName: itemName,
      resolvedStream: stream,
      timestamp: current,
      classIndex: classIndex,
      itemId: itemId,
      confidence: confidence,
      pointsAwarded: earned,
    );
    final updated = <ScanHistoryItem>[entry, ...existing];
    if (updated.length > maxHistoryItems) {
      updated.removeRange(maxHistoryItems, updated.length);
    }
    await _store.setString(
      _kHistory,
      jsonEncode(updated.map((e) => e.toJson()).toList(growable: false)),
    );

    final todayKey = _dayKey(current);
    final todayCount =
        updated.where((h) => _dayKey(h.timestamp) == todayKey).length;

    return EcoStreakSummary(
      ecoPoints: points,
      dailyStreak: streak,
      todayCount: todayCount,
      totalSorted: updated.length,
      lastActivityAt: current,
      streakWasReset: streakReset,
      bonusAwarded: bonus,
      integrityValid: true,
    );
  }

  /// Trả về 7 ngày gần nhất (từ 6 ngày trước đến hôm nay) cho thanh tiến độ 7 ngày.
  List<DailyCheckIn> getLast7DaysActivity({DateTime? now}) {
    final current = now ?? DateTime.now();
    final today = DateTime(current.year, current.month, current.day);
    final history = loadHistory();

    final countsByDay = <String, int>{};
    for (final item in history) {
      final k = _dayKey(item.timestamp);
      countsByDay[k] = (countsByDay[k] ?? 0) + 1;
    }

    return List<DailyCheckIn>.generate(7, (i) {
      final day = today.subtract(Duration(days: 6 - i));
      final count = countsByDay[_dayKey(day)] ?? 0;
      return DailyCheckIn(
        date: day,
        completed: count > 0,
        itemsSorted: count,
      );
    }, growable: false);
  }

  static bool _isSameCalendarDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  static bool _isStreakExpired(DateTime lastAt, DateTime current) {
    if (current.difference(lastAt) >= const Duration(hours: 48)) {
      return true;
    }
    final lastDay = DateTime(lastAt.year, lastAt.month, lastAt.day);
    final currentDay = DateTime(current.year, current.month, current.day);
    return currentDay.difference(lastDay).inDays >= 2;
  }

  static String _dayKey(DateTime dt) =>
      '${dt.year.toString().padLeft(4, '0')}-'
      '${dt.month.toString().padLeft(2, '0')}-'
      '${dt.day.toString().padLeft(2, '0')}';
}
