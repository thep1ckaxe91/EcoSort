import 'package:flutter/material.dart';

/// Bảng màu chuẩn theo Luật Bảo vệ môi trường 2020 (Điều 75) & WCAG 2.1 AA
class AppColors {
  AppColors._();

  // 1. Rác tái chế (Recyclables) - Cam
  static const Color recyclable = Color(0xFFFF9800);
  static const Color recyclableLight = Color(0xFFFFE0B2);
  static const Color recyclableDark = Color(0xFFF57C00);

  // 2. Rác thực phẩm (Food Waste) - Xanh lá
  static const Color foodWaste = Color(0xFF4CAF50);
  static const Color foodWasteLight = Color(0xFFC8E6C9);
  static const Color foodWasteDark = Color(0xFF388E3C);

  // 3. Rác sinh hoạt khác (Residual Waste) - Xám
  static const Color residualWaste = Color(0xFF757575);
  static const Color residualWasteLight = Color(0xFFE0E0E0);
  static const Color residualWasteDark = Color(0xFF424242);

  // Background & Surface
  static const Color background = Color(0xFFF8F9FA);
  static const Color surface = Colors.white;
  static const Color textPrimary = Color(0xFF212121);
  static const Color textSecondary = Color(0xFF616161);

  // Trợ năng / Tương phản cao
  static const Color highContrastBorder = Color(0xFF1E1E1E);
}

