import 'package:camera/camera.dart';
import 'package:flutter/material.dart';
import '../../core/constants/app_colors.dart';
import '../../core/constants/app_strings.dart';
import '../knowledge_base/waste_rule_model.dart';
import '../result/clarification_dialog.dart';
import '../result/result_card.dart';

/// Màn hình Camera Preview & Quét nhận diện rác thời gian thực theo chuẩn Wireframe
class CameraView extends StatefulWidget {
  const CameraView({super.key});

  @override
  State<CameraView> createState() => _CameraViewState();
}

class _CameraViewState extends State<CameraView> with WidgetsBindingObserver {
  CameraController? _controller;
  bool _isCameraInitialized = false;
  bool _isFlashOn = false;
  String? _statusMessage;
  ResultCard? _currentResult;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initializeCamera();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _controller?.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final cameraController = _controller;
    if (cameraController == null || !cameraController.value.isInitialized) {
      return;
    }

    if (state == AppLifecycleState.inactive) {
      cameraController.dispose();
      if (mounted) {
        setState(() {
          _controller = null;
          _isCameraInitialized = false;
        });
      }
    } else if (state == AppLifecycleState.resumed) {
      _initializeCamera();
    }
  }

  Future<void> _initializeCamera() async {
    // Hủy controller cũ nếu có trước khi tạo mới
    await _controller?.dispose();

    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        if (!mounted) return;
        setState(() {
          _controller = null;
          _isCameraInitialized = false;
          _statusMessage = AppStrings.cameraNotFound;
        });
        return;
      }

      // Ưu tiên camera sau (Back Camera)
      final backCamera = cameras.firstWhere(
        (c) => c.lensDirection == CameraLensDirection.back,
        orElse: () => cameras.first,
      );

      final controller = CameraController(
        backCamera,
        ResolutionPreset.medium,
        enableAudio: false,
      );

      _controller = controller;
      await controller.initialize();

      if (!mounted) return;
      setState(() {
        _isCameraInitialized = true;
        _statusMessage = null;
      });
    } on CameraException catch (e) {
      debugPrint('[CameraView] CameraException: ${e.code} - ${e.description}');
      if (!mounted) return;
      setState(() {
        _controller = null;
        _isCameraInitialized = false;
        if (e.code == 'CameraAccessDenied' || e.code == 'CameraAccessDeniedWithoutPrompt') {
          _statusMessage = AppStrings.cameraPermissionDenied;
        } else {
          _statusMessage = AppStrings.cameraErrorGeneric;
        }
      });
    } catch (e) {
      debugPrint('[CameraView] Unexpected camera error: $e');
      if (!mounted) return;
      setState(() {
        _controller = null;
        _isCameraInitialized = false;
        _statusMessage = AppStrings.cameraErrorGeneric;
      });
    }
  }

  Future<void> _toggleFlash() async {
    if (_controller == null || !_isCameraInitialized) {
      return;
    }

    try {
      final newFlashState = !_isFlashOn;
      await _controller!.setFlashMode(
        newFlashState ? FlashMode.torch : FlashMode.off,
      );
      if (!mounted) return;
      setState(() {
        _isFlashOn = newFlashState;
      });
    } catch (e) {
      debugPrint('[CameraView] Toggle flash error: $e');
      // Giữ nguyên trạng thái hiển thị của đèn flash khi gặp lỗi
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(AppStrings.flashError),
          duration: Duration(seconds: 1),
        ),
      );
    }
  }

  Future<void> _onCapture() async {
    // Nếu có camera thật, thực hiện chụp ảnh
    if (_controller != null && _isCameraInitialized) {
      try {
        await _controller!.takePicture();
      } catch (e) {
        debugPrint('[CameraView] takePicture error: $e');
      }
    }

    if (!mounted) return;

    // Kích hoạt luồng Clarification Dialog & ResultCard (Nhiệm vụ 2)
    // barrierDismissible = false: Bắt buộc người dùng trả lời câu hỏi trạng thái sạch/bẩn
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => ClarificationDialog(
        itemName: AppStrings.sampleItemTetraPak,
        onStateSelected: (state) {
          if (!mounted) return;
          setState(() {
            if (state == PhysicalState.clean) {
              _currentResult = ResultCard(
                itemName: AppStrings.sampleItemTetraPakClean,
                stream: WasteStream.recyclable,
                instructions: AppStrings.sampleInstructionsClean,
                onClose: () => setState(() => _currentResult = null),
              );
            } else {
              _currentResult = ResultCard(
                itemName: AppStrings.sampleItemTetraPakDirty,
                stream: WasteStream.residualWaste,
                instructions: AppStrings.sampleInstructionsDirty,
                onClose: () => setState(() => _currentResult = null),
              );
            }
          });
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: const Text(AppStrings.appName),
        centerTitle: true,
      ),
      body: Stack(
        fit: StackFit.expand,
        children: [
          // 1. Lớp hiển thị Camera Preview (hoặc Mock HUD khi không có phần cứng)
          if (_isCameraInitialized && _controller != null)
            CameraPreview(_controller!)
          else
            Container(
              color: Colors.black87,
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Text(
                    _statusMessage ?? AppStrings.cameraPrompt,
                    textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white70, fontSize: 16),
                  ),
                ),
              ),
            ),

          // 2. Khung ngắm Viewfinder HUD (Viền tương phản cao, bóng đổ nhẹ chống chói trên vật sáng)
          Center(
            child: Container(
              width: MediaQuery.of(context).size.width * 0.75,
              height: MediaQuery.of(context).size.width * 0.75,
              decoration: BoxDecoration(
                border: Border.all(color: Colors.white, width: 2.5),
                borderRadius: BorderRadius.circular(24),
                boxShadow: const [
                  BoxShadow(
                    color: Colors.black38,
                    blurRadius: 8,
                    spreadRadius: 1,
                  ),
                ],
              ),
            ),
          ),

          // 3. Chỉ dẫn chữ to cho người cao tuổi (WCAG 2.1 AA)
          Positioned(
            top: 24,
            left: 20,
            right: 20,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 16),
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(12),
              ),
              child: const Text(
                AppStrings.cameraPrompt,
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),

          // 4. Thẻ kết quả phân loại rác
          if (_currentResult != null)
            Positioned(
              bottom: 130,
              left: 16,
              right: 16,
              child: _currentResult!,
            ),

          // 5. Cụm điều khiển ở đáy màn hình theo Wireframe HCI
          Positioned(
            bottom: 30,
            left: 24,
            right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                // Nút Flash (duy nhất ở cụm điều khiển dưới)
                Container(
                  decoration: const BoxDecoration(
                    color: Colors.black45,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    iconSize: 28,
                    icon: Icon(
                      _isFlashOn ? Icons.flash_on : Icons.flash_off,
                      color: _isFlashOn ? Colors.yellow : Colors.white,
                    ),
                    tooltip: AppStrings.cameraFlash,
                    onPressed: _toggleFlash,
                  ),
                ),

                // Nút chụp to ở giữa (HCI Accessibility >= 72dp)
                SizedBox(
                  width: 76,
                  height: 76,
                  child: FloatingActionButton(
                    backgroundColor: AppColors.foodWaste,
                    elevation: 6,
                    tooltip: AppStrings.captureButtonTooltip,
                    onPressed: _onCapture,
                    shape: const CircleBorder(),
                    child: const Icon(Icons.camera_alt, color: Colors.white, size: 38),
                  ),
                ),

                // Nút trợ năng / Giọng nói (Voice ASR)
                Container(
                  decoration: const BoxDecoration(
                    color: Colors.black45,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    iconSize: 28,
                    icon: const Icon(Icons.mic, color: Colors.white),
                    tooltip: AppStrings.voiceInputTooltip,
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text(AppStrings.voiceFeatureNotice),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
