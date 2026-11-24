import 'package:flutter/material.dart';

/// Bảng màu chuẩn theo Luật Bảo vệ môi trường 2020 (Điều 75) & WCAG 2.1 AA
/// Đạt tỷ lệ tương phản tối thiểu >= 4.5:1 trên nền trắng/sáng theo review HCI
class AppColors {
  AppColors._();

  // 1. Rác tái chế (Recyclables) - Cam (#C2410C, contrast 5.18:1)
  static const Color recyclable = Color(0xFFC2410C);
  static const Color recyclableLight = Color(0xFFFFEDD5);
  static const Color recyclableDark = Color(0xFF9A3412);

  // 2. Rác thực phẩm (Food Waste) - Xanh lá (#2E7D32, contrast 5.13:1)
  static const Color foodWaste = Color(0xFF2E7D32);
  static const Color foodWasteLight = Color(0xFFDCFCE7);
  static const Color foodWasteDark = Color(0xFF1B5E20);

  // 3. Rác sinh hoạt khác (Residual Waste) - Xám than (#4B5563, contrast 7.56:1)
  static const Color residualWaste = Color(0xFF4B5563);
  static const Color residualWasteLight = Color(0xFFF3F4F6);
  static const Color residualWasteDark = Color(0xFF1F2937);

  // 4. Chất thải nguy hại (Hazardous Waste) - Đỏ cảnh báo (#B42318, contrast 6.57:1)
  static const Color hazardous = Color(0xFFB42318);
  static const Color hazardousLight = Color(0xFFFEE2E2);
  static const Color hazardousDark = Color(0xFF7F1D1D);

  // Background & Surface
  static const Color background = Color(0xFFF8F9FA);
  static const Color surface = Colors.white;
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF616161);

  // Trợ năng / Tương phản cao
  static const Color highContrastBorder = Color(0xFF1E1E1E);
}

