import 'package:flutter/material.dart';
import 'province34_review.dart';

/// No GeoPackage, GeoJSON or PMTiles is loaded by this screen.
class GisReviewScreen extends StatefulWidget {
  const GisReviewScreen({super.key});
  @override
  State<GisReviewScreen> createState() => _GisReviewScreenState();
}

class _GisReviewScreenState extends State<GisReviewScreen> {
  late final Future<Province34Review> _report = Province34Review.load();

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Kiểm định GIS 34 tỉnh')),
    body: FutureBuilder<Province34Review>(
      future: _report,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return const Center(child: Padding(
            padding: EdgeInsets.all(20),
            child: Text('Không xác minh được báo cáo GIS. Bản đồ vẫn bị chặn.'),
          ));
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final report = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            const Card(child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('P0: CHƯA ĐẠT',
                       style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 8),
                  Text('Dữ liệu nguồn đang được kiểm duyệt. '
                       'Đây là báo cáo QA, không phải bản đồ được phê duyệt.'),
                ],
              ),
            )),
            const SizedBox(height: 12),
            Card(child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('GeoPackage kiểm tra dữ liệu',
                       style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text('Đã kiểm tra: ${report.provinceCount}/34 tỉnh/thành'),
                  Text('Thành phần xa bờ cần rà soát: ${report.offshoreCount}'),
                  const Text('Hình học trong gói rà soát đã đối chiếu trùng với nguồn.'),
                  const SizedBox(height: 8),
                  const Text(
                    'APK chỉ chứa báo cáo thống kê. GeoPackage chưa được đóng gói '
                    'hoặc kích hoạt trong MapLibre.',
                    style: TextStyle(fontSize: 12),
                  ),
                ],
              ),
            )),
            const SizedBox(height: 8),
            for (final region in report.reviewRegions)
              Card(child: ListTile(
                leading: const Icon(Icons.layers_outlined),
                title: Text('${region.name} (mã ${region.code})'),
                subtitle: Text(
                  '${region.count} đa giác xa bờ; '
                  '${region.largeCount} vùng trên 25 km²'
                ),
              )),
            const SizedBox(height: 12),
            Card(child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Đối chiếu địa danh Hoàng Sa và Trường Sa',
                       style: Theme.of(context).textTheme.titleMedium),
                  const SizedBox(height: 8),
                  Text('Thông tư 33/2024: '
                       '${report.officialPointReview.total} vị trí đã kiểm tra '
                       '(Hoàng Sa ${report.officialPointReview.hoangSa}, '
                       'Trường Sa ${report.officialPointReview.truongSa}).'),
                  Text('Trong hoặc cách đa giác ≤2 km: '
                       '${report.officialPointReview.within2km}/183'),
                  Text('Điểm cách trên 5 km đã phân loại: '
                       '${report.officialPointReview.flaggedOver5km}'),
                  Text('Đảo có tọa độ đối chứng: '
                       '${report.officialPointReview.independentIslandPoints}'),
                  Text('Còn thiếu đường bao của '
                       '${report.officialPointReview.namedIslandOutlinesMissing} '
                       'đảo, và chưa phân loại đất nổi cho '
                       '${report.officialPointReview.reefExposureUnknown} đá/bãi.'),
                  const SizedBox(height: 6),
                  const Text(
                    'Phép chuyển VN-2000 sang WGS84 dùng ngoài khơi '
                    'chưa được phê duyệt. Tọa độ địa danh không phải '
                    'đường bao đảo hoặc ranh giới biển.',
                    style: TextStyle(fontSize: 12),
                  ),
                ],
              ),
            )),
            const SizedBox(height: 12),
            Text('Cần hoàn thiện',
                 style: Theme.of(context).textTheme.titleMedium),
            for (final check in report.remainingChecks)
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.pending_actions_outlined),
                title: Text(check),
              ),
            const Divider(),
            SelectableText(
              'SHA-256 ZIP: ${report.sourceSha256}\n'
              'SHA-256 GeoPackage: ${report.packageSha256}',
              style: const TextStyle(fontSize: 11),
            ),
            const SizedBox(height: 12),
            const Text(
              'Các đa giác hành chính xa bờ chưa được xác nhận là '
              'đất đảo nổi hoặc đường phân định biển.',
              style: TextStyle(fontSize: 12),
            ),
          ],
        );
      },
    ),
  );
}
