import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/tts/tts_service.dart';

class _FakeTtsEngine implements TtsEngine {
  bool configured = false;
  double? configuredRate;
  final List<String> spokenTexts = [];
  int stopCalls = 0;
  VoidCallback? _onComplete;

  @override
  void setLifecycleHandlers({
    required VoidCallback onComplete,
    required VoidCallback onCancel,
    required ValueChanged<dynamic> onError,
  }) {
    _onComplete = onComplete;
  }

  @override
  Future<void> configureVietnamese({required double speechRate}) async {
    configured = true;
    configuredRate = speechRate;
  }

  @override
  Future<void> speak(String text) async {
    spokenTexts.add(text);
  }

  @override
  Future<void> stop() async {
    stopCalls++;
  }

  void triggerComplete() => _onComplete?.call();
}

void main() {
  group('TtsService (vi-VN) Unit Tests', () {
    late TtsService service;
    late _FakeTtsEngine fakeEngine;

    setUp(() {
      service = TtsService();
      fakeEngine = _FakeTtsEngine();
      service.setEngineForTesting(fakeEngine);
      service.autoSpeakEnabled = false;
    });

    test('initializes vi-VN configuration once and speaks text', () async {
      await service.speak('Đây là chai nhựa sạch, bỏ vào thùng màu cam.');

      expect(fakeEngine.configured, isTrue);
      expect(fakeEngine.configuredRate, 0.48);
      expect(fakeEngine.stopCalls, 1);
      expect(fakeEngine.spokenTexts, [
        'Đây là chai nhựa sạch, bỏ vào thùng màu cam.',
      ]);
      expect(service.isSpeaking, isTrue);

      fakeEngine.triggerComplete();
      expect(service.isSpeaking, isFalse);
    });

    test('ignores empty/whitespace speech requests', () async {
      await service.speak('   ');
      expect(fakeEngine.configured, isFalse);
      expect(fakeEngine.spokenTexts, isEmpty);
    });

    test('respects autoSpeakEnabled gating for Elderly Mode', () async {
      await service.speakIfAutoEnabled('Đọc tự động');
      expect(fakeEngine.spokenTexts, isEmpty);

      service.autoSpeakEnabled = true;
      await service.speakIfAutoEnabled('Đọc tự động');
      expect(fakeEngine.spokenTexts, ['Đọc tự động']);
    });

    test('stop resets speaking state and delegates to engine', () async {
      await service.speak('Hộp sữa giấy');
      expect(service.isSpeaking, isTrue);

      await service.stop();
      expect(service.isSpeaking, isFalse);
      expect(fakeEngine.stopCalls, 2);
    });
  });
}
