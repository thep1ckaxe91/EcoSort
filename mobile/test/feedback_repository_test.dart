import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/storage/key_value_store.dart';
import 'package:ecosort/features/feedback/feedback_repository.dart';

void main() {
  group('FeedbackRepository (US-04) Unit Tests', () {
    late InMemoryKeyValueStore store;
    late FeedbackRepository repo;

    setUp(() {
      store = InMemoryKeyValueStore();
      repo = FeedbackRepository(store);
    });

    test('blocks feedback submission until explicit privacy Opt-In is granted',
        () async {
      expect(repo.hasPrivacyOptIn, isFalse);

      await expectLater(
        repo.submitReport(
          predictedClassIndex: 0,
          predictedItemId: 'chai_nhua_pet',
          correctedClassIndex: 6,
          correctedItemId: 'chai_lo_thuy_tinh',
          confidence: 0.64,
        ),
        throwsA(isA<FeedbackConsentRequiredException>()),
      );
    });

    test('queues offline feedback with stable anonymous UUID and tracks sync state',
        () async {
      await repo.setPrivacyOptIn(true);
      expect(repo.hasPrivacyOptIn, isTrue);

      final r1 = await repo.submitReport(
        predictedClassIndex: 0,
        predictedItemId: 'chai_nhua_pet',
        correctedClassIndex: 6,
        correctedItemId: 'chai_lo_thuy_tinh',
        confidence: 0.64,
        note: 'Chai thủy tinh trong suốt',
        now: DateTime(2026, 11, 19, 10, 0),
      );
      final r2 = await repo.submitReport(
        predictedClassIndex: 13,
        predictedItemId: 'hop_xop_dung_thuc_an',
        correctedClassIndex: 5,
        correctedItemId: 'thung_bia_carton',
        confidence: 0.58,
        now: DateTime(2026, 11, 19, 10, 5),
      );

      expect(r1.anonymousDeviceId, r2.anonymousDeviceId);
      expect(
        RegExp(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')
            .hasMatch(r1.anonymousDeviceId),
        isTrue,
      );
      expect(repo.getPendingReports().length, 2);

      // Mark first report synced
      await repo.markSynced([r1.reportId]);
      final pending = repo.getPendingReports();
      expect(pending.length, 1);
      expect(pending.first.reportId, r2.reportId);

      // Export pending JSON
      final exported = jsonDecode(repo.exportPendingJson()) as List<dynamic>;
      expect(exported.length, 1);
      expect((exported.first as Map<String, dynamic>)['corrected_item_id'],
          'thung_bia_carton');
    });
  });
}
