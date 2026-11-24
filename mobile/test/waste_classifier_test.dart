import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/features/classifier/waste_classifier.dart';

void main() {
  group('WasteClassifier & MockWasteClassifier Tests', () {
    late MockWasteClassifier classifier;

    setUp(() {
      classifier = MockWasteClassifier();
    });

    tearDown(() {
      classifier.dispose();
    });

    test('Initializes with default fallback labels if asset is not provided', () async {
      expect(classifier.isReady, isFalse);
      await classifier.initialize();
      expect(classifier.isReady, isTrue);
      expect(classifier.labels.length, 20);
      expect(classifier.labels.first, 'chai_nhua_pet');
      expect(classifier.labels.last, 'vo_goi_mi_bim_bim');
    });

    test('Initializes with custom injected label list', () async {
      final customClassifier = MockWasteClassifier(labels: ['chai_nhua_pet', 'hop_sua_giay']);
      await customClassifier.initialize();
      expect(customClassifier.labels.length, 2);
      expect(customClassifier.labels, contains('hop_sua_giay'));
    });

    test('Classifies image with default mock result meeting latency constraint (< 150ms)', () async {
      await classifier.initialize();
      final result = await classifier.classifyImage('dummy_path.jpg');

      expect(result.label, 'chai_nhua_pet');
      expect(result.confidence, 0.88);
      expect(result.isConfident, isTrue);
      expect(result.inferenceTimeMs, lessThan(150));
      expect(result.classIndex, 0);
    });

    test('Supports setting custom forced mock result for specific test scenarios', () async {
      await classifier.initialize();

      classifier.setMockResult(
        label: 'hop_sua_giay',
        confidence: 0.95,
        inferenceTimeMs: 38,
        classIndex: 2,
      );

      final result = await classifier.classifyImage('milk_box.jpg');
      expect(result.label, 'hop_sua_giay');
      expect(result.confidence, 0.95);
      expect(result.isConfident, isTrue);
      expect(result.inferenceTimeMs, 38);
      expect(result.classIndex, 2);

      // Reset mock result
      classifier.resetMockResult();
      final resetResult = await classifier.classifyImage('test.jpg');
      expect(resetResult.label, 'chai_nhua_pet');
    });

    test('Handles low confidence scenario (< 0.60)', () async {
      await classifier.initialize();

      classifier.setMockResult(
        label: 'coc_nhua_tra_sua',
        confidence: 0.52,
        inferenceTimeMs: 60,
      );

      final result = await classifier.classifyImage('blurry_image.jpg');
      expect(result.confidence, 0.52);
      expect(result.isConfident, isFalse);
    });

    test('Dispose resets ready state', () async {
      await classifier.initialize();
      expect(classifier.isReady, isTrue);
      classifier.dispose();
      expect(classifier.isReady, isFalse);
    });
  });
}

