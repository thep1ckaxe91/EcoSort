import 'package:flutter/foundation.dart';

/// Dịch vụ giọng nói tiếng Việt (TTS) đọc kết quả tự động
class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  bool _isSpeaking = false;
  bool get isSpeaking => _isSpeaking;

  Future<void> speak(String text) async {
    // Stub triển khai: sẽ tích hợp package flutter_tts sau khi bổ sung dependency
    _isSpeaking = true;
    debugPrint('[TTS vi-VN]: $text');
    _isSpeaking = false;
  }

  Future<void> stop() async {
    _isSpeaking = false;
    debugPrint('[TTS Stopped]');
  }
}

