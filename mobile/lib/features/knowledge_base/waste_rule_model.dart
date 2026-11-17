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

/// Chuyển đổi khóa chuỗi từ `rules.json` sang enum [WasteStream].
WasteStream wasteStreamFromKey(String key) {
  switch (key) {
    case 'recyclable':
      return WasteStream.recyclable;
    case 'food_waste':
      return WasteStream.foodWaste;
    case 'residual_waste':
      return WasteStream.residualWaste;
    default:
      throw FormatException('Unknown waste stream key: $key');
  }
}

/// Chuyển đổi mã hex `#RRGGBB` sang [Color].
Color colorFromHex(String hex) {
  final cleaned = hex.replaceFirst('#', '');
  if (cleaned.length != 6) {
    throw FormatException('Invalid hex color: $hex');
  }
  return Color(int.parse('FF$cleaned', radix: 16));
}

/// Thông tin mô tả và màu sắc chuẩn WCAG 2.1 AA cho từng luồng rác.
class WasteStreamMetadata {
  final String key;
  final String nameVi;
  final String colorNameVi;
  final String colorHex;
  final String descriptionVi;

  const WasteStreamMetadata({
    required this.key,
    required this.nameVi,
    required this.colorNameVi,
    required this.colorHex,
    required this.descriptionVi,
  });

  Color get color => colorFromHex(colorHex);

  factory WasteStreamMetadata.fromJson(String key, Map<String, dynamic> json) {
    return WasteStreamMetadata(
      key: key,
      nameVi: json['name_vi'] as String,
      colorNameVi: json['color_name_vi'] as String,
      colorHex: json['color_hex'] as String,
      descriptionVi: json['description_vi'] as String,
    );
  }
}

/// Một nhánh quyết định phụ thuộc vào (`is_clean`, `has_food`) trong `rules.json`.
class StateRuleBranch {
  final bool isClean;
  final bool hasFood;
  final String uiOptionLabelVi;
  final WasteStream resolvedStream;
  final bool isHazardousBranch;
  final bool secondaryFoodStreamRequired;
  final String legalCitation;
  final String actionableInstructionsVi;
  final String ttsReadoutVi;

  const StateRuleBranch({
    required this.isClean,
    required this.hasFood,
    required this.uiOptionLabelVi,
    required this.resolvedStream,
    required this.isHazardousBranch,
    required this.secondaryFoodStreamRequired,
    required this.legalCitation,
    required this.actionableInstructionsVi,
    required this.ttsReadoutVi,
  });

  factory StateRuleBranch.fromJson(Map<String, dynamic> json) {
    return StateRuleBranch(
      isClean: json['is_clean'] as bool,
      hasFood: json['has_food'] as bool,
      uiOptionLabelVi: json['ui_option_label_vi'] as String,
      resolvedStream: wasteStreamFromKey(json['resolved_stream'] as String),
      isHazardousBranch: (json['is_hazardous_branch'] as bool?) ?? false,
      secondaryFoodStreamRequired:
          (json['secondary_food_stream_required'] as bool?) ?? false,
      legalCitation: json['legal_citation'] as String,
      actionableInstructionsVi: json['actionable_instructions_vi'] as String,
      ttsReadoutVi: json['tts_readout_vi'] as String,
    );
  }
}

/// Quy tắc của một lớp vật phẩm trong bộ 20 lớp chuẩn (`class_index: 0..19`).
class WasteRuleItem {
  final int classIndex;
  final String itemId;
  final String categoryCode;
  final List<String> commonNamesVi;
  final List<String> commonNamesEn;
  final WasteStream defaultStream;
  final String condition;
  final bool requiresClarification;
  final bool isHazardous;
  final String? clarificationQuestionVi;
  final List<StateRuleBranch> stateRules;

  const WasteRuleItem({
    required this.classIndex,
    required this.itemId,
    required this.categoryCode,
    required this.commonNamesVi,
    required this.commonNamesEn,
    required this.defaultStream,
    required this.condition,
    required this.requiresClarification,
    required this.isHazardous,
    required this.clarificationQuestionVi,
    required this.stateRules,
  });

  String get primaryNameVi => commonNamesVi.first;

  factory WasteRuleItem.fromJson(Map<String, dynamic> json) {
    final names = json['common_names'] as Map<String, dynamic>;
    final rawBranches = json['state_rules'] as List<dynamic>;
    return WasteRuleItem(
      classIndex: json['class_index'] as int,
      itemId: json['item_id'] as String,
      categoryCode: json['category_code'] as String,
      commonNamesVi: List<String>.from(names['vi'] as List<dynamic>),
      commonNamesEn: List<String>.from(names['en'] as List<dynamic>),
      defaultStream: wasteStreamFromKey(json['default_stream'] as String),
      condition: json['condition'] as String,
      requiresClarification: json['requires_clarification'] as bool,
      isHazardous: json['is_hazardous'] as bool,
      clarificationQuestionVi: json['clarification_question_vi'] as String?,
      stateRules: rawBranches
          .map((b) => StateRuleBranch.fromJson(b as Map<String, dynamic>))
          .toList(growable: false),
    );
  }
}

/// Kết quả phân giải cuối cùng sẵn sàng hiển thị lên [ResultCard] và đọc qua TTS.
class ResolvedWasteDecision {
  final WasteRuleItem item;
  final StateRuleBranch branch;
  final WasteStreamMetadata? streamMetadata;
  final Color displayColor;

  const ResolvedWasteDecision({
    required this.item,
    required this.branch,
    required this.streamMetadata,
    required this.displayColor,
  });

  WasteStream get stream => branch.resolvedStream;
  bool get isHazardous => item.isHazardous || branch.isHazardousBranch;
  bool get requiresSecondaryFoodSeparation =>
      branch.secondaryFoodStreamRequired;
  String get itemNameVi => item.primaryNameVi;
  String get instructionsVi => branch.actionableInstructionsVi;
  String get ttsReadoutVi => branch.ttsReadoutVi;
  String get legalCitation => branch.legalCitation;
}
