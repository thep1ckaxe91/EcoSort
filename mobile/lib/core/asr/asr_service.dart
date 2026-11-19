import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:speech_to_text/speech_to_text.dart';
import '../../features/knowledge_base/waste_rule_model.dart';
import '../../features/knowledge_base/waste_rule_repository.dart';

/// Giao diện trừu tượng bọc plugin ASR (`speech_to_text`) để dễ kiểm thử đơn vị.
abstract class AsrEngine {
  Future<bool> initialize({ValueChanged<String>? onStatus, ValueChanged<dynamic>? onError});
  Future<void> listen({
    required String localeId,
    required ValueChanged<String> onTranscript,
    Duration listenFor,
  });
  Future<void> stop();
  bool get isListening;
}

/// Triển khai mặc định bọc `speech_to_text` cấu hình `vi_VN`.
/// Khởi tạo lười (lazy) để không đụng Platform Channel trong unit tests.
class SpeechToTextAsrEngine implements AsrEngine {
  SpeechToText? _plugin;

  SpeechToText _resolvePlugin() => _plugin ??= SpeechToText();

  @override
  bool get isListening => _plugin?.isListening ?? false;

  @override
  Future<bool> initialize({
    ValueChanged<String>? onStatus,
    ValueChanged<dynamic>? onError,
  }) async {
    final plugin = _resolvePlugin();
    return plugin.initialize(
      onStatus: onStatus,
      onError: (err) => onError?.call(err),
    );
  }

  @override
  Future<void> listen({
    required String localeId,
    required ValueChanged<String> onTranscript,
    Duration listenFor = const Duration(seconds: 6),
  }) async {
    final plugin = _resolvePlugin();
    await plugin.listen(
      listenOptions: SpeechListenOptions(
        localeId: localeId,
        listenFor: listenFor,
      ),
      onResult: (result) {
        if (result.recognizedWords.isNotEmpty) {
          onTranscript(result.recognizedWords);
        }
      },
    );
  }

  @override
  Future<void> stop() async {
    if (_plugin != null) {
      await _plugin!.stop();
    }
  }
}

/// Kết quả phân tích câu nói tiếng Việt thành vật phẩm và trạng thái vật lý (US-03 AC-03.5).
class VoiceQueryMatch {
  final String rawTranscript;
  final String normalizedItemQuery;
  final WasteRuleItem? matchedRule;
  final bool? inferredIsClean;
  final bool? inferredHasFood;

  const VoiceQueryMatch({
    required this.rawTranscript,
    required this.normalizedItemQuery,
    required this.matchedRule,
    required this.inferredIsClean,
    required this.inferredHasFood,
  });

  /// True nếu câu nói đã chứa đủ trạng thái để bỏ qua hộp thoại hỏi lại (Clarification Dialog).
  bool get hasInferredState => inferredIsClean != null;
}

/// Bộ phân tích câu nói tiếng Việt thành truy vấn `WasteRuleRepository` + tách trạng thái sạch/bẩn.
class VoiceQueryResolver {
  static const List<String> _dirtyOrFoodPhrases = [
    'con thuc an',
    'dinh dau mo',
    'dinh dau',
    'dinh ban',
    'chua rua',
    'con sua',
    'con nuoc',
    'con tran chau',
    'con da',
    'bi ban',
    'uot ban',
    'nhiem khuan',
    'nguoi benh',
  ];

  static const List<String> _cleanPhrases = [
    'da rua sach',
    'da trang sach',
    'con sach',
    'da sach',
    'kho rao',
    'sach se',
    'da do het',
    'khong dinh',
  ];

  static const List<String> _fillerPhrases = [
    'day la',
    'cho hoi',
    'vut vao dau',
    'bo thung nao',
    'bo vao dau',
    'phan loai',
    'cai nay la',
    'mon nay la',
    'thuoc nhom nao',
    'giup toi',
  ];

  final WasteRuleRepository _repository;

  const VoiceQueryResolver(this._repository);

  VoiceQueryMatch resolve(String transcript) {
    final raw = transcript.trim();
    if (raw.isEmpty) {
      return const VoiceQueryMatch(
        rawTranscript: '',
        normalizedItemQuery: '',
        matchedRule: null,
        inferredIsClean: null,
        inferredHasFood: null,
      );
    }

    var stripped = WasteRuleRepository.stripVietnameseDiacritics(raw)
        .replaceAll(RegExp(r'[,.;:!?]+'), ' ')
        .replaceAll(RegExp(r'\s+'), ' ')
        .trim();

    bool? isClean;
    bool? hasFood;

    for (final phrase in _dirtyOrFoodPhrases) {
      if (stripped.contains(phrase)) {
        isClean = false;
        hasFood = true;
        stripped = stripped.replaceAll(phrase, ' ');
      }
    }
    if (isClean == null) {
      for (final phrase in _cleanPhrases) {
        if (stripped.contains(phrase)) {
          isClean = true;
          hasFood = false;
          stripped = stripped.replaceAll(phrase, ' ');
        }
      }
    }

    for (final filler in _fillerPhrases) {
      stripped = stripped.replaceAll(filler, ' ');
    }
    final cleanedQuery = stripped.replaceAll(RegExp(r'\s+'), ' ').trim();

    // Thử khớp đầy đủ trước; nếu người dùng nói thêm từ thừa thì lùi dần theo n-gram.
    WasteRuleItem? matched = _bestMatch(cleanedQuery);
    if (matched == null && cleanedQuery.isNotEmpty) {
      final words = cleanedQuery.split(' ');
      for (var len = words.length - 1; len >= 1 && matched == null; len--) {
        for (var start = 0; start <= words.length - len; start++) {
          final sub = words.sublist(start, start + len).join(' ');
          matched = _bestMatch(sub);
          if (matched != null) break;
        }
      }
    }

    return VoiceQueryMatch(
      rawTranscript: raw,
      normalizedItemQuery: cleanedQuery,
      matchedRule: matched,
      inferredIsClean: isClean,
      inferredHasFood: hasFood,
    );
  }

  WasteRuleItem? _bestMatch(String query) {
    if (query.isEmpty) return null;
    final hits = _repository.search(query);
    return hits.isNotEmpty ? hits.first : null;
  }
}

/// Dịch vụ nhận dạng giọng nói tiếng Việt (`vi_VN`) cho chế độ rảnh tay / người cao tuổi.
class AsrService {
  static final AsrService _instance = AsrService._internal();
  factory AsrService() => _instance;

  AsrService._internal();

  AsrEngine? _engine;
  bool _available = false;

  bool get isAvailable => _available;
  bool get isListening => _engine?.isListening ?? false;

  AsrEngine _getOrCreateEngine() => _engine ??= SpeechToTextAsrEngine();

  @visibleForTesting
  void setEngineForTesting(AsrEngine engine) {
    _engine = engine;
    _available = false;
  }

  Future<bool> ensureInitialized({
    ValueChanged<String>? onStatus,
    ValueChanged<dynamic>? onError,
  }) async {
    if (_available) return true;
    try {
      _available = await _getOrCreateEngine().initialize(
        onStatus: onStatus,
        onError: onError,
      );
      return _available;
    } on MissingPluginException {
      debugPrint('[ASR vi_VN]: MissingPluginException (headless mode).');
      _available = false;
      return false;
    } catch (e) {
      debugPrint('[ASR vi_VN]: Failed to initialize ASR: $e');
      _available = false;
      return false;
    }
  }

  Future<bool> startListening({
    required ValueChanged<String> onTranscript,
    Duration listenFor = const Duration(seconds: 6),
  }) async {
    final ready = await ensureInitialized();
    if (!ready) return false;
    try {
      await _getOrCreateEngine().listen(
        localeId: 'vi_VN',
        onTranscript: onTranscript,
        listenFor: listenFor,
      );
      return true;
    } on MissingPluginException {
      return false;
    } catch (e) {
      debugPrint('[ASR vi_VN]: Error starting listen: $e');
      return false;
    }
  }

  Future<void> stopListening() async {
    if (_engine == null) return;
    try {
      await _engine!.stop();
    } on MissingPluginException {
      debugPrint('[ASR Stopped]');
    } catch (e) {
      debugPrint('[ASR Stop Error]: $e');
    }
  }
}
