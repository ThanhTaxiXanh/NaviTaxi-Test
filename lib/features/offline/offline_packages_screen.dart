import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../platform/android_storage_bridge.dart';
import 'offline_package.dart';

/// User-file PMTiles intake for DEBUG-only local GIS review. Production P0
/// remains blocked even after every hash matches.
class OfflinePackagesScreen extends StatefulWidget {
  const OfflinePackagesScreen({
    super.key,
    this.storage = const AndroidStorageBridge(),
  });

  final AndroidStorageBridge storage;

  @override
  State<OfflinePackagesScreen> createState() => _OfflinePackagesScreenState();
}

class _OfflinePackagesScreenState extends State<OfflinePackagesScreen> {
  late final Future<List<OfflineArchive>> _catalog =
      OfflinePackageCatalog.load();

  List<QuarantinedArchive> _installed = const [];
  bool _busy = false;
  String? _feedback;
  String? _loadingError;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  Future<void> _refresh() async {
    try {
      final records = await widget.storage.listImported();
      if (mounted) {
        setState(() {
          _installed = records;
          _loadingError = null;
        });
      }
    } on PlatformException catch (error) {
      if (mounted) setState(() => _loadingError = error.message ?? error.code);
    } catch (error) {
      if (mounted) setState(() => _loadingError = error.toString());
    }
  }

  Future<void> _perform(Future<String> Function() operation) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _feedback = null;
    });
    try {
      final message = await operation();
      await _refresh();
      if (mounted) setState(() => _feedback = message);
    } on PlatformException catch (error) {
      if (mounted) {
        setState(() => _feedback = 'Lỗi: ${error.message ?? error.code}');
      }
    } catch (error) {
      if (mounted) setState(() => _feedback = 'Lỗi: $error');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _import(OfflineArchive archive) => _perform(() async {
        final result = await widget.storage.importArchive(archive.filename);
        if (result == null) return 'Đã hủy chọn tệp.';
        return result
            ? 'SHA-256 khớp. Bạn có thể mở lớp đường/POI khi quay lại '
                'bản đồ GIS DEBUG. P0 vẫn chưa được duyệt.'
            : 'Không thể xác nhận checksum của dữ liệu.';
      });

  Future<void> _verify(OfflineArchive archive) => _perform(() async {
        final result = await widget.storage.verifyImported(archive.filename);
        return result
            ? 'Dữ liệu trùng khớp SHA-256; kiểm chứng P0 vẫn chưa đạt.'
            : 'Checksum hoặc định dạng không hợp lệ. Không sử dụng tệp này.';
      });

  Future<void> _delete(OfflineArchive archive) async {
    final agreed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Xóa gói cách ly?'),
        content: Text(
          'Xóa tệp ${archive.label} khỏi bộ nhớ ứng dụng? '
          'Không ảnh hưởng đến tệp gốc đã chọn.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Hủy'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Xóa'),
          ),
        ],
      ),
    );
    if (agreed != true) return;
    await _perform(() async {
      final removed = await widget.storage.deleteImported(archive.filename);
      return removed ? 'Đã xóa gói cách ly.' : 'Không thể xóa tệp.';
    });
  }

  Future<void> _showStorageInfo() async {
    try {
      final path = await widget.storage.getOfflineDirectory();
      final bytes = await widget.storage.getAvailableBytes();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Thư mục cách ly: $path\\nCòn trống: ${bytes ~/ (1024 * 1024)} MiB',
          ),
        ),
      );
    } on PlatformException catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.message ?? error.code)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final installed = {for (final file in _installed) file.filename: file};
    return Scaffold(
      appBar: AppBar(
        title: const Text('Dữ liệu bản đồ offline'),
        actions: [
          IconButton(
            tooltip: 'Bộ nhớ cách ly',
            onPressed: _showStorageInfo,
            icon: const Icon(Icons.info_outline),
          ),
        ],
      ),
      body: FutureBuilder<List<OfflineArchive>>(
        future: _catalog,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(child: Text('Không đọc được danh mục: ${snapshot.error}'));
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('P0: CHƯA PHÊ DUYỆT',
                          style: TextStyle(fontWeight: FontWeight.bold)),
                      SizedBox(height: 8),
                      Text(
                        'Chọn đúng tệp PMTiles đã cung cấp. '
                        'Các gói sẽ được kiểm tra SHA-256 và lưu riêng. '
                        'Chỉ màn hình GIS DEBUG được hiển thị đường, '
                        'công trình và POI sau xác minh. '
                        'Bản đồ chính thức vẫn bị chặn P0.',
                      ),
                    ],
                  ),
                ),
              ),
              if (_loadingError != null)
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text('Lỗi lưu trữ: $_loadingError'),
                ),
              if (_feedback != null)
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Text(_feedback!),
                ),
              for (final archive in snapshot.data!)
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(archive.label,
                            style: Theme.of(context).textTheme.titleMedium),
                        Text(
                          '${archive.sizeMiB.toStringAsFixed(1)} MiB • '
                          '${installed.containsKey(archive.filename) ? 'Đã nhập, đang cách ly' : 'Chưa nhập'}',
                        ),
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: [
                            OutlinedButton.icon(
                              onPressed: _busy || installed.containsKey(archive.filename)
                                  ? null
                                  : () => _import(archive),
                              icon: const Icon(Icons.file_open),
                              label: const Text('Chọn tệp'),
                            ),
                            if (installed.containsKey(archive.filename))
                              OutlinedButton.icon(
                                onPressed: _busy ? null : () => _verify(archive),
                                icon: const Icon(Icons.verified_outlined),
                                label: const Text('Kiểm tra'),
                              ),
                            if (installed.containsKey(archive.filename))
                              TextButton.icon(
                                onPressed: _busy ? null : () => _delete(archive),
                                icon: const Icon(Icons.delete_outline),
                                label: const Text('Xóa'),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              const Padding(
                padding: EdgeInsets.all(8),
                child: Text(
                  'Quay lại bản đồ MapLibre GIS sau khi nhập để thấy '
                  'các lớp PMTiles offline. Chưa có tải tự động, '
                  'định tuyến hoặc phát hành bản đồ chính thức. '
                  'Nguồn: © OpenStreetMap contributors / HOT.',
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}
