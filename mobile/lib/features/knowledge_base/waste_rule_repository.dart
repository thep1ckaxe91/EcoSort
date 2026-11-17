import 'dart:convert';
import 'package:flutter/services.dart' show AssetBundle, rootBundle;
import 'waste_rule_model.dart';

/// Repository đọc và truy vấn Cơ sở tri thức phân loại rác (`rules.json`).
/// Hỗ trợ tra cứu $O(1)$ theo `class_index` từ TFLite, phân giải trạng thái
/// `(is_clean, has_food)` và tìm kiếm ngoại tuyến tiếng Việt có dấu / không dấu.
class WasteRuleRepository {
  static const String defaultAssetPath = 'assets/kb/rules.json';

  final String schemaVersion;
  final String legalReference;
  final int totalClasses;
  final Map<String, WasteStreamMetadata> streams;
  final List<WasteRuleItem> rules;
  final Map<int, WasteRuleItem> _byIndex;
  final Map<String, WasteRuleItem> _byId;

  WasteRuleRepository._({
    required this.schemaVersion,
    required this.legalReference,
    required this.totalClasses,
    required this.streams,
    required this.rules,
  })  : _byIndex = {for (final r in rules) r.classIndex: r},
        _byId = {for (final r in rules) r.itemId: r};

  /// Khởi tạo từ chuỗi JSON đã đọc (hữu ích cho cả unit test không cần AssetBundle).
  factory WasteRuleRepository.fromJsonString(String jsonString) {
    final decoded = jsonDecode(jsonString) as Map<String, dynamic>;
    final rawStreams = decoded['streams'] as Map<String, dynamic>;
    final parsedStreams = <String, WasteStreamMetadata>{
      for (final entry in rawStreams.entries)
        entry.key: WasteStreamMetadata.fromJson(
          entry.key,
          entry.value as Map<String, dynamic>,
        ),
    };
    final rawRules = decoded['rules'] as List<dynamic>;
    final parsedRules = rawRules
        .map((r) => WasteRuleItem.fromJson(r as Map<String, dynamic>))
        .toList(growable: false);

    return WasteRuleRepository._(
      schemaVersion: decoded['schema_version'] as String,
      legalReference: decoded['legal_reference'] as String,
      totalClasses: decoded['total_classes'] as int,
      streams: parsedStreams,
      rules: parsedRules,
    );
  }

  /// Tải bất đồng bộ `rules.json` từ Flutter asset bundle.
  static Future<WasteRuleRepository> loadFromAsset({
    AssetBundle? bundle,
    String assetPath = defaultAssetPath,
  }) async {
    final source = bundle ?? rootBundle;
    final jsonString = await source.loadString(assetPath);
    return WasteRuleRepository.fromJsonString(jsonString);
  }

  /// Tra cứu lớp rác theo chỉ số đầu ra (`0..19`) của mô hình TFLite.
  WasteRuleItem? lookupByIndex(int classIndex) => _byIndex[classIndex];

  /// Tra cứu lớp rác theo mã định danh chuẩn `item_id`.
  WasteRuleItem? lookupById(String itemId) => _byId[itemId];

  /// Phân giải quyết định cuối cùng dựa trên bộ đôi trạng thái `(isClean, hasFood)`.
  ResolvedWasteDecision resolveState(
    WasteRuleItem item, {
    required bool isClean,
    required bool hasFood,
  }) {
    final branches = item.stateRules;
    StateRuleBranch? matched;

    if (!item.requiresClarification || branches.length == 1) {
      matched = branches.first;
    } else {
      for (final branch in branches) {
        if (branch.isClean == isClean && branch.hasFood == hasFood) {
          matched = branch;
          break;
        }
      }
      matched ??= branches.cast<StateRuleBranch?>().firstWhere(
            (b) => b!.isClean == isClean,
            orElse: () => null,
          );
    }

    if (matched == null) {
      throw StateError(
        'No state branch found for ${item.itemId} '
        '(isClean=$isClean, hasFood=$hasFood)',
      );
    }

    return _buildDecision(item, matched);
  }

  /// Chuyển đổi enum [PhysicalState] của UI `ClarificationDialog` sang quyết định cuối.
  ResolvedWasteDecision resolvePhysicalState(
    WasteRuleItem item,
    PhysicalState state,
  ) {
    switch (state) {
      case PhysicalState.clean:
        return resolveState(item, isClean: true, hasFood: false);
      case PhysicalState.dirty:
        return resolveState(item, isClean: false, hasFood: false);
      case PhysicalState.liquidRemaining:
        return resolveState(item, isClean: false, hasFood: true);
    }
  }

  ResolvedWasteDecision _buildDecision(
    WasteRuleItem item,
    StateRuleBranch branch,
  ) {
    final streamKey = _streamKey(branch.resolvedStream);
    final isHaz = item.isHazardous || branch.isHazardousBranch;
    final meta = isHaz
        ? (streams['hazardous_display'] ?? streams[streamKey])
        : streams[streamKey];
    final color = meta?.color ?? branch.resolvedStream.color;

    return ResolvedWasteDecision(
      item: item,
      branch: branch,
      streamMetadata: meta,
      displayColor: color,
    );
  }

  /// Tìm kiếm vật phẩm tiếng Việt ngoại tuyến trên toàn bộ `common_names` và `item_id`.
  /// - Gõ có dấu (vd: "vỏ chuối"): khớp chính xác dấu trên toàn bộ từ đồng nghĩa.
  /// - Gõ không dấu (vd: "vo chuoi"): chuẩn hóa không dấu trước khi so khớp.
  List<WasteRuleItem> search(String query) {
    final cleaned = query.trim();
    if (cleaned.isEmpty) {
      return List<WasteRuleItem>.unmodifiable(rules);
    }

    final useExactMarks = hasVietnameseDiacritics(cleaned);
    final normalizedQuery =
        useExactMarks ? cleaned.toLowerCase() : stripVietnameseDiacritics(cleaned);
    final tokens = normalizedQuery
        .split(RegExp(r'\s+'))
        .where((t) => t.isNotEmpty)
        .toList(growable: false);

    final hits = <WasteRuleItem>[];
    for (final rule in rules) {
      final buffer = <String>[
        ...rule.commonNamesVi,
        ...rule.commonNamesEn,
        rule.itemId,
      ].join(' ').toLowerCase();
      final haystack = useExactMarks ? buffer : stripVietnameseDiacritics(buffer);

      if (tokens.every((tok) => haystack.contains(tok))) {
        hits.add(rule);
      }
    }
    return hits;
  }

  static String _streamKey(WasteStream stream) {
    switch (stream) {
      case WasteStream.recyclable:
        return 'recyclable';
      case WasteStream.foodWaste:
        return 'food_waste';
      case WasteStream.residualWaste:
        return 'residual_waste';
    }
  }

  /// Kiểm tra chuỗi có chứa dấu thanh/mũ tiếng Việt hay không.
  static bool hasVietnameseDiacritics(String input) {
    final lowered = input.toLowerCase().replaceAll('đ', 'd');
    return stripVietnameseDiacritics(input) != lowered;
  }

  /// Chuẩn hóa chuỗi tiếng Việt về dạng không dấu chữ thường (zero dependencies).
  static String stripVietnameseDiacritics(String input) {
    const accented =
        'àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ';
    const plain =
        'aaaaaaaaaaaaaaaaaeeeeeeeeeeeiiiiiooooooooooooooooouuuuuuuuuuuyyyyyd';

    final lower = input.toLowerCase();
    final out = StringBuffer();
    for (var i = 0; i < lower.length; i++) {
      final ch = lower[i];
      final idx = accented.indexOf(ch);
      out.write(idx >= 0 ? plain[idx] : ch);
    }
    return out.toString();
  }
}
