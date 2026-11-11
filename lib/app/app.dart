import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../features/map/map_screen.dart';
import '../features/map/review_map_screen.dart';

/// Only explicit DEBUG review builds may display unapproved preview shapes.
/// This cannot alter or satisfy the P0 release manifest.
const bool kPreviewReviewRequested = bool.fromEnvironment(
  'NAVITAXI_REVIEW_MODE',
  defaultValue: false,
);

class NaviTaxiApp extends StatelessWidget {
  const NaviTaxiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NaviTaxi Việt Nam',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF0B6A65)),
        useMaterial3: true,
      ),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF54C9B0),
          brightness: Brightness.dark,
        ),
        useMaterial3: true,
      ),
      home: (kDebugMode && kPreviewReviewRequested)
          ? const ReviewMapScreen()
          : const MapScreen(),
    );
  }
}
