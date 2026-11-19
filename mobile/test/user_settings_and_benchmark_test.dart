import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/benchmark/inference_benchmark_logger.dart';
import 'package:ecosort/core/settings/user_settings_repository.dart';
import 'package:ecosort/core/storage/key_value_store.dart';
import 'package:ecosort/core/tts/tts_service.dart';

void main() {
  group('UserSettingsRepository (US-03 Elderly Mode & TTS Sync)', () {
    late InMemoryKeyValueStore store;
    late TtsService tts;
    late UserSettingsRepository repo;

    setUp(() {
      store = InMemoryKeyValueStore();
      tts = TtsService();
      tts.autoSpeakEnabled = false;
      repo = UserSettingsRepository(store, ttsService: tts);
    });

    test('defaults to normal mode with TTS auto-speak off', () {
      final s = repo.load();
      expect(s.elderlyModeEnabled, isFalse);
      expect(s.autoSpeakEnabled, isFalse);
      expect(s.textScaleFactor, 1.0);
      expect(s.minTouchTargetDp, 48.0);
    });

    test('enabling Elderly Mode auto-enables TTS unless user explicitly overrode TTS',
        () async {
      final enabled = await repo.setElderlyMode(true);
      expect(enabled.elderlyModeEnabled, isTrue);
      expect(enabled.autoSpeakEnabled, isTrue);
      expect(enabled.textScaleFactor, 1.375);
      expect(enabled.minTouchTargetDp, 64.0);
      expect(tts.autoSpeakEnabled, isTrue);

      // User manually turns TTS off -> preference remembered
      await repo.setAutoSpeakByUser(false);
      expect(tts.autoSpeakEnabled, isFalse);

      // Re-toggling Elderly Mode does NOT force TTS back on
      await repo.setElderlyMode(false);
      final reEnabled = await repo.setElderlyMode(true);
      expect(reEnabled.autoSpeakEnabled, isFalse);
      expect(tts.autoSpeakEnabled, isFalse);
    });
  });

  group('InferenceBenchmarkLogger (US-01 Latency & Task Time)', () {
    test('computes mean, p50, p95, low-confidence count, and JSON report', () {
      final logger = InferenceBenchmarkLogger(maxSamples: 5);
      final latencies = [80, 100, 120, 140, 180];
      for (var i = 0; i < latencies.length; i++) {
        logger.record(
          classIndex: i,
          confidence: i == 0 ? 0.52 : 0.88,
          inferenceMs: latencies[i],
          totalTaskMs: 2500 + i * 500,
          timestamp: DateTime(2026, 11, 19, 12, 0, i),
        );
      }

      final summary = logger.summarize();
      expect(summary.sampleCount, 5);
      expect(summary.meanInferenceMs, 124.0);
      expect(summary.p50InferenceMs, 120.0);
      expect(summary.p95InferenceMs, closeTo(172.0, 0.01));
      expect(summary.lowConfidenceCount, 1);
      expect(summary.meetsInferenceLatencyTarget, isTrue);
      expect(summary.meetsTaskTimeTarget, isTrue);

      // Exceeding ring buffer drops oldest sample
      logger.record(
        classIndex: 9,
        confidence: 0.91,
        inferenceMs: 260,
        totalTaskMs: 9000,
      );
      expect(logger.samples.length, 5);
      expect(logger.summarize().meetsInferenceLatencyTarget, isFalse);
      expect(logger.summarize().meetsTaskTimeTarget, isFalse);

      final report = jsonDecode(
        logger.exportReportJson(
          deviceModel: 'Honor 50',
          modelName: 'ecosort_v1.tflite',
        ),
      ) as Map<String, dynamic>;
      expect(report['device_model'], 'Honor 50');
      expect((report['samples'] as List).length, 5);
    });
  });
}
