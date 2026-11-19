import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/storage/key_value_store.dart';
import 'package:ecosort/features/history/eco_streak_repository.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_model.dart';

void main() {
  group('EcoStreakRepository (US-05) Unit Tests', () {
    late InMemoryKeyValueStore store;
    late EcoStreakRepository repo;

    setUp(() {
      store = InMemoryKeyValueStore();
      repo = EcoStreakRepository(store);
    });

    test('increments streak max once per calendar day and awards +10 points per sort',
        () async {
      final day1Morning = DateTime(2026, 11, 10, 8, 30);
      final day1Evening = DateTime(2026, 11, 10, 19, 15);

      final s1 = await repo.recordConfirmedSort(
        itemName: 'Chai nhựa PET',
        stream: WasteStream.recyclable,
        classIndex: 0,
        itemId: 'chai_nhua_pet',
        now: day1Morning,
      );
      expect(s1.dailyStreak, 1);
      expect(s1.ecoPoints, 10);
      expect(s1.todayCount, 1);
      expect(s1.bonusAwarded, 0);
      expect(s1.integrityValid, isTrue);

      final s2 = await repo.recordConfirmedSort(
        itemName: 'Vỏ trứng',
        stream: WasteStream.residualWaste,
        classIndex: 11,
        itemId: 'vo_trung',
        now: day1Evening,
      );
      expect(s2.dailyStreak, 1);
      expect(s2.ecoPoints, 20);
      expect(s2.todayCount, 2);
      expect(repo.loadHistory().length, 2);
    });

    test('awards +50 bonus points on 7-day consecutive streak milestone', () async {
      late EcoStreakSummary latest;
      for (var d = 0; d < 7; d++) {
        latest = await repo.recordConfirmedSort(
          itemName: 'Lon nhôm',
          stream: WasteStream.recyclable,
          classIndex: 1,
          itemId: 'lon_nhom',
          now: DateTime(2026, 11, 10 + d, 9, 0),
        );
      }

      expect(latest.dailyStreak, 7);
      expect(latest.bonusAwarded, 50);
      // 7 * 10 + 50 = 120
      expect(latest.ecoPoints, 120);

      final week = repo.getLast7DaysActivity(now: DateTime(2026, 11, 16, 12, 0));
      expect(week.length, 7);
      expect(week.every((d) => d.completed && d.itemsSorted == 1), isTrue);
    });

    test('resets streak after >= 48 hours of inactivity', () async {
      await repo.recordConfirmedSort(
        itemName: 'Hộp sữa giấy',
        stream: WasteStream.recyclable,
        now: DateTime(2026, 11, 10, 9, 0),
      );
      await repo.recordConfirmedSort(
        itemName: 'Hộp sữa giấy',
        stream: WasteStream.recyclable,
        now: DateTime(2026, 11, 11, 9, 0),
      );

      // 50 hours later -> summary shows expired streak (0)
      final expiredSummary =
          repo.getSummary(now: DateTime(2026, 11, 13, 11, 0));
      expect(expiredSummary.dailyStreak, 0);
      expect(expiredSummary.streakWasReset, isTrue);

      // Sorting again restarts streak at 1 and flags streakWasReset
      final restarted = await repo.recordConfirmedSort(
        itemName: 'Hộp xốp',
        stream: WasteStream.residualWaste,
        now: DateTime(2026, 11, 13, 11, 5),
      );
      expect(restarted.dailyStreak, 1);
      expect(restarted.streakWasReset, isTrue);
      expect(restarted.ecoPoints, 30);
    });

    test('detects client-side tampering via HMAC SHA-256 checksum', () async {
      await repo.recordConfirmedSort(
        itemName: 'Chai nhựa PET',
        stream: WasteStream.recyclable,
        now: DateTime(2026, 11, 10, 8, 0),
      );
      expect(repo.verifyIntegrity(), isTrue);

      // Tamper stored points directly without updating HMAC
      await store.setInt('ecosort_eco_points', 999999);
      expect(repo.verifyIntegrity(), isFalse);

      final summary = repo.getSummary(now: DateTime(2026, 11, 10, 9, 0));
      expect(summary.integrityValid, isFalse);
      expect(summary.ecoPoints, 0);
    });
  });
}
