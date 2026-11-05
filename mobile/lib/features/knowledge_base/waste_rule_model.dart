import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_strings.dart';

/// 3 luồng phân loại rác theo Luật Bảo vệ môi trường 2020 (Điều 75)
enum WasteStream {
  recyclable,
  foodWaste,
  residualWaste,
}

extension WasteStreamExtension on WasteStream {
  String get displayName {
    switch (this) {
      case WasteStream.recyclable:
        return AppStrings.streamRecyclable;
      case WasteStream.foodWaste:
        return AppStrings.streamFoodWaste;
      case WasteStream.residualWaste:
        return AppStrings.streamResidual;
    }
  }

  Color get color {
    switch (this) {
      case WasteStream.recyclable:
        return AppColors.recyclable;
      case WasteStream.foodWaste:
        return AppColors.foodWaste;
      case WasteStream.residualWaste:
        return AppColors.residualWaste;
    }
  }

  IconData get icon {
    switch (this) {
      case WasteStream.recyclable:
        return Icons.recycling;
      case WasteStream.foodWaste:
        return Icons.restaurant;
      case WasteStream.residualWaste:
        return Icons.delete_outline;
    }
  }
}

/// Trạng thái vật lý của vật phẩm (State-Aware)
enum PhysicalState {
  clean,
  dirty,
  liquidRemaining,
}

