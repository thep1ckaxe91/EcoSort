import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/asr/asr_service.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_model.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_repository.dart';

class _FakeAsrEngine implements AsrEngine {
  bool _listening = false;
  bool initialized = false;
  String? lastLocale;
  String simulatedTranscript = 'hộp sữa giấy đã rửa sạch';

  @override
  bool get isListening => _listening;

  @override
  Future<bool> initialize({
    ValueChanged<String>? onStatus,
    ValueChanged<dynamic>? onError,
  }) async {
    initialized = true;
    return true;
  }

  @override
  Future<void> listen({
    required String localeId,
    required ValueChanged<String> onTranscript,
    Duration listenFor = const Duration(seconds: 6),
  }) async {
    lastLocale = localeId;
    _listening = true;
    onTranscript(simulatedTranscript);
  }

  @override
  Future<void> stop() async {
    _listening = false;
  }
}

void main() {
  late WasteRuleRepository kbRepo;
  late VoiceQueryResolver resolver;

  setUpAll(() {
    final jsonStr = File('assets/kb/rules.json').readAsStringSync();
    kbRepo = WasteRuleRepository.fromJsonString(jsonStr);
    resolver = VoiceQueryResolver(kbRepo);
  });

  group('VoiceQueryResolver & AsrService (US-03 AC-03.5)', () {
    test('extracts clean state and matches milk carton directly', () {
      final match = resolver.resolve('Cho hỏi hộp sữa giấy đã rửa sạch vứt vào đâu?');
      expect(match.matchedRule?.itemId, 'hop_sua_giay');
      expect(match.hasInferredState, isTrue);
      expect(match.inferredIsClean, isTrue);
      expect(match.inferredHasFood, isFalse);

      final resolved = kbRepo.resolveState(
        match.matchedRule!,
        isClean: match.inferredIsClean!,
        hasFood: match.inferredHasFood!,
      );
      expect(resolved.stream, WasteStream.recyclable);
    });

    test('extracts dirty/food state from bubble tea cup utterance', () {
      final match = resolver.resolve('Cốc nhựa trà sữa còn trân châu');
      expect(match.matchedRule?.itemId, 'coc_nhua_tra_sua');
      expect(match.inferredIsClean, isFalse);
      expect(match.inferredHasFood, isTrue);

      final resolved = kbRepo.resolveState(
        match.matchedRule!,
        isClean: match.inferredIsClean!,
        hasFood: match.inferredHasFood!,
      );
      expect(resolved.stream, WasteStream.residualWaste);
      expect(resolved.requiresSecondaryFoodSeparation, isTrue);
    });

    test('matches direct items without state keywords', () {
      final battery = resolver.resolve('Pin tiểu đã dùng');
      expect(battery.matchedRule?.itemId, 'pin_da_qua_su_dung');
      expect(battery.hasInferredState, isFalse);

      final banana = resolver.resolve('vỏ chuối');
      expect(banana.matchedRule?.itemId, 'rau_cu_qua_thua');
    });

    test('AsrService initializes vi_VN locale and delivers transcripts', () async {
      final asr = AsrService();
      final fake = _FakeAsrEngine();
      asr.setEngineForTesting(fake);

      String? received;
      final started = await asr.startListening(
        onTranscript: (text) => received = text,
      );

      expect(started, isTrue);
      expect(fake.initialized, isTrue);
      expect(fake.lastLocale, 'vi_VN');
      expect(received, 'hộp sữa giấy đã rửa sạch');
      expect(asr.isListening, isTrue);

      await asr.stopListening();
      expect(asr.isListening, isFalse);
    });
  });
}
