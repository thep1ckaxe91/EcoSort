import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_tts/flutter_tts.dart';

/// Giao diện trừu tượng bọc engine TTS để dễ kiểm thử đơn vị (mocking).
abstract class TtsEngine {
  Future<void> configureVietnamese({required double speechRate});
  Future<void> speak(String text);
  Future<void> stop();
  void setLifecycleHandlers({
    required VoidCallback onComplete,
    required VoidCallback onCancel,
    required ValueChanged<dynamic> onError,
  });
}

/// Triển khai mặc định sử dụng package `flutter_tts` (vi-VN).
/// Khởi tạo `FlutterTts` theo kiểu lười (lazy) để không đụng MethodChannel lúc khởi động app
/// hoặc trong unit test thuần Dart.
class FlutterTtsEngine implements TtsEngine {
  FlutterTts? _tts;
  VoidCallback? _onComplete;
  VoidCallback? _onCancel;
  ValueChanged<dynamic>? _onError;

  FlutterTtsEngine([FlutterTts? tts]) : _tts = tts;

  FlutterTts _resolvePlugin() {
    if (_tts != null) return _tts!;
    final instance = FlutterTts();
    if (_onComplete != null) instance.setCompletionHandler(_onComplete!);
    if (_onCancel != null) instance.setCancelHandler(_onCancel!);
    if (_onError != null) instance.setErrorHandler(_onError!);
    _tts = instance;
    return instance;
  }

  @override
  void setLifecycleHandlers({
    required VoidCallback onComplete,
    required VoidCallback onCancel,
    required ValueChanged<dynamic> onError,
  }) {
    _onComplete = onComplete;
    _onCancel = onCancel;
    _onError = onError;
    if (_tts != null) {
      _tts!.setCompletionHandler(onComplete);
      _tts!.setCancelHandler(onCancel);
      _tts!.setErrorHandler(onError);
    }
  }

  @override
  Future<void> configureVietnamese({required double speechRate}) async {
    final tts = _resolvePlugin();
    await tts.setLanguage('vi-VN');
    await tts.setSpeechRate(speechRate);
    await tts.setVolume(1.0);
    await tts.setPitch(1.0);
    await tts.awaitSpeakCompletion(false);
  }

  @override
  Future<void> speak(String text) async {
    await _resolvePlugin().speak(text);
  }

  @override
  Future<void> stop() async {
    await _resolvePlugin().stop();
  }
}

/// Dịch vụ giọng nói tiếng Việt (TTS) đọc kết quả và hướng dẫn xử lý rác.
/// Mặc định tắt tự động đọc (`autoSpeakEnabled = false`); luôn đọc khi người dùng
/// bấm nút Loa hoặc khi bật Chế độ Người cao tuổi.
class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;

  TtsService._internal();

  TtsEngine? _engine;
  bool _initialized = false;
  bool _isSpeaking = false;

  /// Tự động đọc kết quả khi hiển thị thẻ (mặc định tắt, bật ở Elderly Mode).
  bool autoSpeakEnabled = false;

  /// Tốc độ đọc tối ưu cho người lớn tuổi (rõ chữ, vừa phải).
  double speechRate = 0.48;

  bool get isSpeaking => _isSpeaking;

  TtsEngine _getOrCreateEngine() {
    if (_engine != null) return _engine!;
    final engine = FlutterTtsEngine();
    _attachHandlers(engine);
    _engine = engine;
    return engine;
  }

  void _attachHandlers(TtsEngine engine) {
    engine.setLifecycleHandlers(
      onComplete: () => _isSpeaking = false,
      onCancel: () => _isSpeaking = false,
      onError: (_) => _isSpeaking = false,
    );
  }

  /// Thay engine trong unit test để không phụ thuộc Platform Channel.
  @visibleForTesting
  void setEngineForTesting(TtsEngine engine) {
    _engine = engine;
    _initialized = false;
    _isSpeaking = false;
    _attachHandlers(engine);
  }

  /// Khởi tạo cấu hình `vi-VN` một lần trước khi phát âm đầu tiên.
  Future<void> ensureInitialized() async {
    if (_initialized) return;
    try {
      await _getOrCreateEngine().configureVietnamese(speechRate: speechRate);
      _initialized = true;
    } on MissingPluginException {
      debugPrint('[TTS vi-VN]: MissingPluginException during init (headless mode).');
    } catch (e) {
      debugPrint('[TTS vi-VN]: Failed to configure TTS: $e');
    }
  }

  /// Phát giọng nói tiếng Việt ngay lập tức (dùng cho nút Loa hoặc khi đã kiểm tra điều kiện).
  Future<void> speak(String text) async {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;

    await ensureInitialized();
    try {
      final engine = _getOrCreateEngine();
      await engine.stop();
      _isSpeaking = true;
      await engine.speak(trimmed);
    } on MissingPluginException {
      _isSpeaking = false;
      debugPrint('[TTS vi-VN]: $trimmed');
    } catch (e) {
      _isSpeaking = false;
      debugPrint('[TTS vi-VN]: Error speaking "$trimmed": $e');
    }
  }

  /// Chỉ tự động đọc nếu `autoSpeakEnabled == true` (Chế độ Người cao tuổi).
  Future<void> speakIfAutoEnabled(String text) async {
    if (!autoSpeakEnabled) return;
    await speak(text);
  }

  /// Dừng phát âm thanh đang chạy.
  Future<void> stop() async {
    _isSpeaking = false;
    if (_engine == null && !_initialized) {
      return;
    }
    try {
      await _getOrCreateEngine().stop();
    } on MissingPluginException {
      debugPrint('[TTS Stopped]');
    } catch (e) {
      debugPrint('[TTS Stop Error]: $e');
    }
  }
}
