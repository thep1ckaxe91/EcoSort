import '../storage/key_value_store.dart';
import '../tts/tts_service.dart';

/// Trạng thái cài đặt trợ năng và giọng nói (US-03 & USER_FLOW_v2 §4.5).
class UserSettings {
  final bool elderlyModeEnabled;
  final bool autoSpeakEnabled;
  final bool userOverrodeTts;

  const UserSettings({
    this.elderlyModeEnabled = false,
    this.autoSpeakEnabled = false,
    this.userOverrodeTts = false,
  });

  /// Hệ số phóng đại cỡ chữ: Elderly Mode đảm bảo tiêu đề >= 22sp và nội dung >= 18sp.
  double get textScaleFactor => elderlyModeEnabled ? 1.375 : 1.0;

  /// Chiều cao tối thiểu nút bấm theo chuẩn WCAG/US-03 (48dp chuẩn, 64dp chữ to).
  double get minTouchTargetDp => elderlyModeEnabled ? 64.0 : 48.0;
}

/// Lưu trữ cục bộ chế độ Người cao tuổi và đồng bộ trạng thái tự động đọc sang [TtsService].
class UserSettingsRepository {
  static const String _kElderly = 'ecosort_elderly_mode';
  static const String _kAutoSpeak = 'ecosort_auto_speak';
  static const String _kUserSetTts = 'ecosort_user_overrode_tts';

  final KeyValueStore _store;
  final TtsService _ttsService;

  UserSettingsRepository(this._store, {TtsService? ttsService})
      : _ttsService = ttsService ?? TtsService();

  static Future<UserSettingsRepository> create() async {
    final store = await SharedPreferencesStore.create();
    final repo = UserSettingsRepository(store);
    repo.syncToTtsService();
    return repo;
  }

  UserSettings load() {
    return UserSettings(
      elderlyModeEnabled: _store.getBool(_kElderly) ?? false,
      autoSpeakEnabled: _store.getBool(_kAutoSpeak) ?? false,
      userOverrodeTts: _store.getBool(_kUserSetTts) ?? false,
    );
  }

  void syncToTtsService() {
    _ttsService.autoSpeakEnabled = load().autoSpeakEnabled;
  }

  /// Bật/tắt chế độ Người cao tuổi ("Chữ to, nút to").
  /// Khi bật, tự động bật Đọc to trừ khi người dùng trước đó đã tự tay tắt Đọc to.
  Future<UserSettings> setElderlyMode(bool enabled) async {
    final current = load();
    var nextAutoSpeak = current.autoSpeakEnabled;

    if (enabled && !current.userOverrodeTts) {
      nextAutoSpeak = true;
    }

    await _store.setBool(_kElderly, enabled);
    await _store.setBool(_kAutoSpeak, nextAutoSpeak);
    _ttsService.autoSpeakEnabled = nextAutoSpeak;

    return UserSettings(
      elderlyModeEnabled: enabled,
      autoSpeakEnabled: nextAutoSpeak,
      userOverrodeTts: current.userOverrodeTts,
    );
  }

  /// Người dùng tự bật/tắt công tắc Đọc to — ghi nhớ lựa chọn để không bị ghi đè.
  Future<UserSettings> setAutoSpeakByUser(bool enabled) async {
    final current = load();
    await _store.setBool(_kAutoSpeak, enabled);
    await _store.setBool(_kUserSetTts, true);
    _ttsService.autoSpeakEnabled = enabled;

    return UserSettings(
      elderlyModeEnabled: current.elderlyModeEnabled,
      autoSpeakEnabled: enabled,
      userOverrodeTts: true,
    );
  }
}
