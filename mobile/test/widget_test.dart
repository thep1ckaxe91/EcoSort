import 'package:flutter_test/flutter_test.dart';
import 'package:ecosort/app/app.dart';
import 'package:ecosort/core/constants/app_strings.dart';

void main() {
  testWidgets('EcoSortApp smoke test - verifies initial CameraView and title', (WidgetTester tester) async {
    await tester.pumpWidget(const EcoSortApp());
    await tester.pump();

    // Xác nhận AppBar hiển thị tên app EcoSort
    expect(find.text(AppStrings.appName), findsOneWidget);

    // Xác nhận chỉ dẫn hướng camera hiển thị trên màn hình
    expect(find.text(AppStrings.cameraPrompt), findsWidgets);
  });
}
