import 'package:flutter/material.dart';

import 'admin_catalog.dart';

/// Offline administrative name search. Returns a location only if a real
/// GIS-derived review label anchor exists; never invent a GPS location.
class AdminSearchDelegate extends SearchDelegate<AdminPlace?> {
  AdminSearchDelegate(this.catalog)
      : super(searchFieldLabel: 'Tìm tỉnh, xã, phường, đặc khu');

  final AdminCatalog catalog;

  @override
  List<Widget> buildActions(BuildContext context) => [
        IconButton(
          tooltip: 'Xóa tìm kiếm',
          onPressed: () => query = '',
          icon: const Icon(Icons.clear),
        ),
      ];

  @override
  Widget buildLeading(BuildContext context) => IconButton(
        tooltip: 'Quay lại bản đồ',
        onPressed: () => close(context, null),
        icon: const Icon(Icons.arrow_back),
      );

  @override
  Widget buildSuggestions(BuildContext context) => _results(context);

  @override
  Widget buildResults(BuildContext context) => _results(context);

  Widget _results(BuildContext context) {
    final matches = catalog.search(query);
    if (matches.isEmpty) {
      return const Center(child: Text('Không tìm thấy địa danh phù hợp.'));
    }
    return ListView.builder(
      itemCount: matches.length,
      itemBuilder: (context, index) {
        final place = matches[index];
        final province = catalog.provinceName(place.provinceCode);
        return ListTile(
          leading: Icon(
            place.isProvince ? Icons.location_city : Icons.place_outlined,
          ),
          title: Text(place.name),
          subtitle: Text(
            place.isProvince
                ? 'Tỉnh/thành • mã ${place.code}'
                : '$province • mã ${place.code}',
          ),
          trailing: place.hasAnchor
              ? const Icon(Icons.my_location, size: 18)
              : const Icon(Icons.info_outline, size: 18),
          onTap: () {
            if (place.hasAnchor) {
              close(context, place);
            } else {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text(
                    'Đã có tên hành chính, chưa có điểm đặt nhãn được kiểm tra '
                    'cho địa danh này trong bản build hiện tại.',
                  ),
                ),
              );
            }
          },
        );
      },
    );
  }
}
