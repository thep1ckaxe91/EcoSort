import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';

/// Tiện ích hỗ trợ người cao tuổi và chuẩn trợ năng WCAG 2.1 AA
class AccessibilityUtils {
  AccessibilityUtils._();

  /// Giới hạn hệ số phóng to chữ tự động (Dynamic Font Scaling) để không bị vỡ layout
  static double getClampedTextScaler(BuildContext context, {double min = 1.0, double max = 1.5}) {
    final scale = MediaQuery.textScalerOf(context).scale(1.0);
    return scale.clamp(min, max);
  }

  /// Thông báo cho trình đọc màn hình (TalkBack)
  static void announce(BuildContext context, String message) {
    SemanticsService.sendAnnouncement(
      View.of(context),
      message,
      TextDirection.ltr,
    );
  }
}

