import 'package:flutter/material.dart';
import '../../core/accessibility/accessibility_utils.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_strings.dart';
import '../../core/tts/tts_service.dart';
import '../knowledge_base/waste_rule_model.dart';

/// Thẻ hiển thị kết quả phân loại rác theo chuẩn Wireframe & WCAG 2.1 AA
class ResultCard extends StatefulWidget {
  final String itemName;
  final WasteStream stream;
  final String instructions;
  final VoidCallback? onClose;
  final VoidCallback? onReportWrong;

  /// Tự động đọc kết quả bằng TTS khi thẻ xuất hiện (mặc định tắt).
  /// Khi bật, thẻ KHÔNG gửi thông báo TalkBack nữa để tránh hai giọng nói chồng nhau.
  final bool autoSpeak;

  const ResultCard({
    super.key,
    required this.itemName,
    required this.stream,
    required this.instructions,
    this.onClose,
    this.onReportWrong,
    this.autoSpeak = false,
  });

  @override
  State<ResultCard> createState() => _ResultCardState();
}

class _ResultCardState extends State<ResultCard> {
  String get _spokenText =>
      '${widget.itemName}: ${widget.stream.displayName}. ${widget.instructions}';

  @override
  void initState() {
    super.initState();
    _deliverResult();
  }

  @override
  void didUpdateWidget(covariant ResultCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Camera view thay thẻ mới tại cùng vị trí => widget được cập nhật chứ không tạo lại
    final changed = oldWidget.itemName != widget.itemName ||
        oldWidget.stream != widget.stream ||
        oldWidget.instructions != widget.instructions;
    if (changed) {
      _deliverResult();
    }
  }

  @override
  void dispose() {
    // Đóng thẻ (hoặc thẻ bị gỡ) thì dừng đọc
    TtsService().stop();
    super.dispose();
  }

  /// Báo kết quả đúng MỘT lần khi thẻ xuất hiện hoặc đổi nội dung:
  /// - autoSpeak bật: TTS đọc, không gửi thông báo TalkBack (tránh nói chồng).
  /// - autoSpeak tắt: gửi một thông báo cho TalkBack.
  void _deliverResult() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (widget.autoSpeak) {
        TtsService().speak(_spokenText);
      } else {
        AccessibilityUtils.announce(context, _spokenText);
      }
    });
  }

  /// Chọn màu chữ (trắng/đen) có độ tương phản cao hơn so với màu nền.
  Color _onColor(Color background) {
    final l = background.computeLuminance();
    final whiteContrast = 1.05 / (l + 0.05);
    final blackContrast = (l + 0.05) / 0.05;
    return whiteContrast >= blackContrast ? Colors.white : Colors.black;
  }

  @override
  Widget build(BuildContext context) {
    final stream = widget.stream;
    final badgeFg = _onColor(stream.color);
    final maxHeight = MediaQuery.of(context).size.height * 0.45;

    return ConstrainedBox(
      constraints: BoxConstraints(maxHeight: maxHeight),
      child: Card(
        elevation: 6,
        shadowColor: Colors.black45,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: BorderSide(
            color: stream.color.withValues(alpha: 0.4),
            width: 1.5,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header: Stream Badge, TTS Button, Close Button
              Row(
                children: [
                  Flexible(
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 6,
                      ),
                      decoration: BoxDecoration(
                        color: stream.color,
                        borderRadius: BorderRadius.circular(24),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(stream.icon, color: badgeFg, size: 18),
                          const SizedBox(width: 6),
                          Flexible(
                            child: Text(
                              stream.displayName,
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                color: badgeFg,
                                fontWeight: FontWeight.bold,
                                fontSize: 14,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton(
                    icon: const Icon(
                      Icons.volume_up,
                      color: AppColors.textPrimary,
                    ),
                    tooltip: AppStrings.ttsButtonTooltip,
                    onPressed: () => TtsService().speak(_spokenText),
                  ),
                  if (widget.onClose != null)
                    IconButton(
                      icon: const Icon(
                        Icons.close,
                        color: AppColors.textSecondary,
                      ),
                      tooltip: AppStrings.closeButtonTooltip,
                      onPressed: widget.onClose,
                    ),
                ],
              ),
              const SizedBox(height: 12),

              // Nội dung có thể cuộn khi chữ to hoặc hướng dẫn dài
              Flexible(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        widget.itemName,
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        widget.instructions,
                        style: const TextStyle(
                          fontSize: 16,
                          height: 1.4,
                          color: AppColors.textSecondary,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 12),

              // Footer: nút "Báo sai" (Active Learning)
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  TextButton.icon(
                    onPressed: widget.onReportWrong ??
                        () {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text(AppStrings.feedbackThankYou),
                              duration: Duration(seconds: 2),
                            ),
                          );
                        },
                    icon: const Icon(
                      Icons.flag_outlined,
                      size: 18,
                      color: AppColors.textSecondary,
                    ),
                    label: const Text(
                      AppStrings.reportWrongButton,
                      style: TextStyle(
                        fontSize: 15,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}