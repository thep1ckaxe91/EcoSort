import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/core/constants/app_strings.dart';
import 'package:ecosort/features/camera/camera_view.dart';
import 'package:ecosort/features/knowledge_base/waste_rule_model.dart';
import 'package:ecosort/features/result/clarification_dialog.dart';
import 'package:ecosort/features/result/result_card.dart';

void main() {
  group('UI Components & Wireframe Tests (Nhiệm vụ 2)', () {
    testWidgets('ResultCard renders correctly for Recyclable stream', (WidgetTester tester) async {
      bool closed = false;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: ResultCard(
              itemName: 'Chai nhựa PET',
              stream: WasteStream.recyclable,
              instructions: 'Rửa sạch, tháo nhãn và bỏ thùng Cam.',
              onClose: () => closed = true,
            ),
          ),
        ),
      );

      // Kiểm tra tên vật phẩm và tên luồng
      expect(find.text('Chai nhựa PET'), findsOneWidget);
      expect(find.text(AppStrings.streamRecyclable), findsOneWidget);
      expect(find.text('Rửa sạch, tháo nhãn và bỏ thùng Cam.'), findsOneWidget);

      // Kiểm tra icon loa phát âm thanh
      expect(find.byIcon(Icons.volume_up), findsOneWidget);

      // Kiểm tra nút đóng
      await tester.tap(find.byIcon(Icons.close));
      expect(closed, isTrue);
    });

    testWidgets('ClarificationDialog handles state selection accurately', (WidgetTester tester) async {
      PhysicalState? selectedState;

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: Builder(
              builder: (context) => ElevatedButton(
                onPressed: () {
                  showDialog(
                    context: context,
                    builder: (_) => ClarificationDialog(
                      itemName: 'Hộp xốp',
                      onStateSelected: (state) => selectedState = state,
                    ),
                  );
                },
                child: const Text('Open'),
              ),
            ),
          ),
        ),
      );

      // Mở popup
      await tester.tap(find.text('Open'));
      await tester.pumpAndSettle();

      // Kiểm tra tiêu đề và câu hỏi
      expect(find.text(AppStrings.dialogTitle), findsOneWidget);
      expect(find.text('Hộp xốp'), findsOneWidget);
      expect(find.text(AppStrings.optionClean), findsOneWidget);
      expect(find.text(AppStrings.optionDirty), findsOneWidget);

      // Chọn phương án sạch
      await tester.tap(find.text(AppStrings.optionClean));
      await tester.pumpAndSettle();

      expect(selectedState, PhysicalState.clean);
    });

    testWidgets('CameraView interaction flow: capture -> dialog -> result card', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: CameraView(),
        ),
      );
      await tester.pump();

      // Kiểm tra hiển thị nút chụp và khung ngắm
      expect(find.byIcon(Icons.camera_alt), findsOneWidget);
      expect(find.byIcon(Icons.mic), findsOneWidget);

      // Nhấn nút chụp
      await tester.tap(find.byIcon(Icons.camera_alt));
      await tester.pumpAndSettle();

      // Xác nhận dialog xuất hiện
      expect(find.text(AppStrings.dialogTitle), findsOneWidget);

      // Chọn "Đã rửa sạch / Khô ráo"
      await tester.tap(find.text(AppStrings.optionClean));
      await tester.pumpAndSettle();

      // Xác nhận ResultCard xuất hiện với nhãn rác tái chế màu Cam
      expect(find.text(AppStrings.streamRecyclable), findsOneWidget);
      expect(find.text('Hộp sữa giấy'), findsOneWidget);

      // Đóng thẻ kết quả
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      // Xác nhận thẻ kết quả đã được đóng
      expect(find.text('Hộp sữa giấy'), findsNothing);
    });
  });
}

