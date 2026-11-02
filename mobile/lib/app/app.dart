import 'package:flutter/material.dart';
import '../core/constants/app_strings.dart';
import 'routes.dart';
import 'theme.dart';

/// Ứng dụng EcoSort
class EcoSortApp extends StatelessWidget {
  const EcoSortApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppStrings.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      initialRoute: AppRoutes.initial,
      routes: AppRoutes.routes,
    );
  }
}

