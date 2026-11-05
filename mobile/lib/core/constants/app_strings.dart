/// Chuỗi văn bản tiếng Việt chuẩn hóa cho EcoSort (WCAG 2.1 AA & Localization)
class AppStrings {
  AppStrings._();

  static const String appName = 'EcoSort';
  static const String appSubtitle = 'Phân loại rác thông minh tại nguồn';

  // 3 luồng rác theo Điều 75 Luật BVMT 2020
  static const String streamRecyclable = 'Rác tái chế';
  static const String streamFoodWaste = 'Rác thực phẩm';
  static const String streamResidual = 'Rác sinh hoạt khác';

  // Camera & Scan HUD
  static const String cameraPrompt = 'Hướng camera vào vật phẩm cần phân loại';
  static const String cameraCapture = 'Chụp ảnh';
  static const String cameraFlash = 'Bật/Tắt đèn Flash';
  static const String captureButtonTooltip = 'Chụp và phân loại rác';
  static const String voiceInputTooltip = 'Nhập bằng giọng nói (Voice)';
  static const String closeButtonTooltip = 'Đóng';
  static const String reportWrongButton = 'Kết quả này sai?';
  static const String voiceFeatureNotice = 'Tính năng Voice ASR: Sẽ tích hợp trong giai đoạn Sprint kế tiếp.';
  static const String feedbackThankYou = 'Cảm ơn bạn đã phản hồi! Góp ý đã được ghi nhận.';

  // Camera Status & Error handling thân thiện
  static const String cameraPermissionDenied = 'Vui lòng cấp quyền truy cập Camera trong Cài đặt để quét rác.';
  static const String cameraNotFound = 'Không tìm thấy camera phần cứng. Đang bật chế độ giả lập HUD.';
  static const String cameraErrorGeneric = 'Không thể khởi động camera. Đang bật chế độ giả lập HUD.';
  static const String flashError = 'Không thể điều khiển đèn flash trên thiết bị này.';

  // Clarification Dialog
  static const String dialogTitle = 'Xác nhận trạng thái vật phẩm';
  static const String dialogPromptDefault = 'Vật phẩm này đã được làm sạch và bóp dẹt chưa?';
  static const String optionClean = 'Đã rửa sạch / Khô ráo';
  static const String optionDirty = 'Dính bẩn / Còn thức ăn';
  static const String lawNoticeResidual = 'Luật BVMT: Rác bẩn lẫn thực phẩm sẽ chuyển sang luồng rác sinh hoạt khác.';

  // Sample data cho luồng demo
  static const String sampleItemTetraPak = 'Hộp sữa giấy (Tetra Pak)';
  static const String sampleItemTetraPakClean = 'Hộp sữa giấy';
  static const String sampleItemTetraPakDirty = 'Hộp sữa giấy dính cặn';
  static const String sampleInstructionsClean = 'Đã rửa sạch và bóp dẹt. Bỏ vào thùng rác tái chế màu Cam.';
  static const String sampleInstructionsDirty = 'Chưa được rửa sạch. Bỏ vào thùng rác sinh hoạt khác màu Xám.';

  // Accessibility / Trợ năng
  static const String ttsButtonTooltip = 'Đọc kết quả bằng giọng nói';
}
