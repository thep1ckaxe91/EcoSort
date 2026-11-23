import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/constants/app_strings.dart';
import 'package:ecosort/core/storage/key_value_store.dart';
import 'package:ecosort/features/camera/camera_view.dart';
import 'package:ecosort/features/classifier/waste_classifier.dart';
import 'package:ecosort/features/feedback/feedback_repository.dart';
import 'package:ecosort/features/history/eco_streak_repository.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_model.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_repository.dart';

void main() {
  group('CameraView End-to-End Flow Integration Tests (Bước 3)', () {
    late MockWasteClassifier mockClassifier;
    late EcoStreakRepository streakRepo;
    late FeedbackRepository feedbackRepo;
    late WasteRuleRepository ruleRepo;

    const testRulesJson = '''
{
  "schema_version": "1.1.0",
  "legal_reference": "Luật BVMT 2020",
  "total_classes": 2,
  "streams": {
    "recyclable": {
      "name_vi": "Rác tái chế",
      "color_name_vi": "Màu Cam",
      "color_hex": "#C2410C",
      "description_vi": "Chất thải tái chế"
    },
    "residual_waste": {
      "name_vi": "Rác sinh hoạt khác",
      "color_name_vi": "Màu Xám",
      "color_hex": "#4B5563",
      "description_vi": "Rác còn lại"
    }
  },
  "rules": [
    {
      "class_index": 1,
      "item_id": "lon_nhom",
      "category_code": "metal",
      "common_names": {
        "vi": ["Lon nhôm"],
        "en": ["Aluminum can"]
      },
      "default_stream": "recyclable",
      "condition": "none",
      "requires_clarification": false,
      "is_hazardous": false,
      "clarification_question_vi": "",
      "state_rules": [
        {
          "is_clean": true,
          "has_food": false,
          "ui_option_label_vi": "Mặc định",
          "resolved_stream": "recyclable",
          "instructions_vi": "Bỏ vào thùng Rác tái chế (màu Cam)."
        }
      ]
    },
    {
      "class_index": 2,
      "item_id": "hop_sua_giay",
      "category_code": "paper_carton",
      "common_names": {
        "vi": ["Hộp sữa giấy"],
        "en": ["Milk carton"]
      },
      "default_stream": "recyclable",
      "condition": "cleanliness_check",
      "requires_clarification": true,
      "is_hazardous": false,
      "clarification_question_vi": "Hộp sữa này đã rửa sạch bên trong chưa?",
      "state_rules": [
        {
          "is_clean": true,
          "has_food": false,
          "ui_option_label_vi": "Đã rửa sạch / Khô ráo",
          "resolved_stream": "recyclable",
          "instructions_vi": "Bỏ thùng Rác tái chế."
        },
        {
          "is_clean": false,
          "has_food": false,
          "ui_option_label_vi": "Còn bẩn / Chưa tráng",
          "resolved_stream": "residual_waste",
          "instructions_vi": "Bỏ thùng Rác sinh hoạt khác."
        }
      ]
    }
  ]
}
''';

    setUp(() {
      mockClassifier = MockWasteClassifier(labels: ['lon_nhom', 'hop_sua_giay']);
      streakRepo = EcoStreakRepository(InMemoryKeyValueStore());
      feedbackRepo = FeedbackRepository(InMemoryKeyValueStore());
      ruleRepo = WasteRuleRepository.fromJsonString(testRulesJson);
    });

    testWidgets('Low confidence (< 0.60) prompts user to retake instead of opening dialog', (tester) async {
      mockClassifier.setMockResult(
        label: 'hop_sua_giay',
        confidence: 0.52, // < 0.60
        inferenceTimeMs: 40,
        classIndex: 2,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: CameraView(
            classifier: mockClassifier,
            ruleRepository: ruleRepo,
            streakRepository: streakRepo,
            feedbackRepository: feedbackRepo,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Nhấn nút chụp ảnh
      await tester.tap(find.byIcon(Icons.camera_alt));
      await tester.pumpAndSettle();

      // Không được mở ClarificationDialog
      expect(find.text(AppStrings.dialogTitle), findsNothing);
      // Hiển thị thông báo yêu cầu chụp lại rõ nét hơn
      expect(
        find.text('Hình ảnh chưa đủ rõ nét. Vui lòng chụp lại gần hơn hoặc bật đèn Flash.'),
        findsOneWidget,
      );
    });

    testWidgets('Non-state-dependent item (lon_nhom) directly shows ResultCard without ClarificationDialog', (tester) async {
      mockClassifier.setMockResult(
        label: 'lon_nhom',
        confidence: 0.92,
        inferenceTimeMs: 45,
        classIndex: 1,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: CameraView(
            classifier: mockClassifier,
            ruleRepository: ruleRepo,
            streakRepository: streakRepo,
            feedbackRepository: feedbackRepo,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Nhấn chụp
      await tester.tap(find.byIcon(Icons.camera_alt));
      await tester.pumpAndSettle();

      // Không mở dialog hỏi sạch/bẩn
      expect(find.text(AppStrings.dialogTitle), findsNothing);

      // Hiển thị trực tiếp ResultCard với Lon nhôm và rác tái chế
      expect(find.text('Lon nhôm'), findsOneWidget);
      expect(find.text(AppStrings.streamRecyclable), findsOneWidget);

      // Kiểm tra EcoStreak đã được cộng điểm
      final summary = streakRepo.getSummary();
      expect(summary.totalSorted, 1);
      expect(summary.ecoPoints, 10);
    });

    testWidgets('State-dependent item (hop_sua_giay) shows ClarificationDialog and records feedback on error report', (tester) async {
      mockClassifier.setMockResult(
        label: 'hop_sua_giay',
        confidence: 0.88,
        inferenceTimeMs: 42,
        classIndex: 2,
      );

      await tester.pumpWidget(
        MaterialApp(
          home: CameraView(
            classifier: mockClassifier,
            ruleRepository: ruleRepo,
            streakRepository: streakRepo,
            feedbackRepository: feedbackRepo,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Nhấn chụp
      await tester.tap(find.byIcon(Icons.camera_alt));
      await tester.pumpAndSettle();

      // Bắt buộc mở ClarificationDialog
      expect(find.text(AppStrings.dialogTitle), findsOneWidget);
      expect(find.text('Hộp sữa này đã rửa sạch bên trong chưa?'), findsOneWidget);

      // Chọn sạch
      await tester.tap(find.text(AppStrings.optionClean));
      await tester.pumpAndSettle();

      // Thẻ kết quả xuất hiện
      expect(find.text('Hộp sữa giấy'), findsOneWidget);
      expect(find.text(AppStrings.streamRecyclable), findsOneWidget);

      // Nhấn nút "Kết quả này sai?"
      await tester.tap(find.text(AppStrings.reportWrongButton));
      await tester.pumpAndSettle();

      // Kiểm tra báo cáo feedback đã được lưu vào hàng đợi offline
      final reports = feedbackRepo.loadAllReports();
      expect(reports.length, 1);
      expect(reports.first.predictedClassIndex, 2);
      expect(reports.first.predictedItemId, 'hop_sua_giay');
    });
  });
}

