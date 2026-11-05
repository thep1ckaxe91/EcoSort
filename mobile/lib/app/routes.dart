import 'package:flutter/material.dart';
import '../features/camera/camera_view.dart';

/// Định tuyến ứng dụng EcoSort
class AppRoutes {
  AppRoutes._();

  static const String initial = '/';
  static const String camera = '/camera';
  static const String result = '/result';
  static const String history = '/history';

  static Map<String, WidgetBuilder> get routes => {
        initial: (context) => const CameraView(),
        camera: (context) => const CameraView(),
      };
}

