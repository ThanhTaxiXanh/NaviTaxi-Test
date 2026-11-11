# Tiếp nhận dữ liệu 34 tỉnh/thành vào NaviTaxi (ứng viên gis.vn)

**Trạng thái: chờ tệp từ nhà cung cấp, không được tự phê duyệt.** Môi trường này không thể mở `gis.vn` hoặc xác minh được trang có link tải, phiên bản, quyền tái sử dụng dữ liệu hay không. Không được coi tên miền là chứng cứ dữ liệu chính thức.

## Bước nhập dữ liệu

1. Trên trình duyệt, kiểm tra rõ nhà phát hành, ngày công bố, phiên bản địa giới, nguồn GIS, phương thức cấp phép và khả năng sử dụng offline/redistribute; tải tệp bằng chức năng công khai hoặc giấy phép hợp lệ. Không lấy trộm tile hoặc vượt cơ chế bảo vệ.
2. Ưu tiên GeoPackage (.gpkg) hoặc GeoJSON (.geojson). Nếu chỉ có SHP, phải có đủ .shp, .dbf, .shx, .prj; có thể chuyển bằng GDAL. Không suy đoán CRS nếu thiếu .prj.
3. Chuyển bản sao làm việc sang GeoJSON lon/lat WGS84 (EPSG:4326), ví dụ:

```bash
ogr2ogr -f GeoJSON -t_srs EPSG:4326 /tmp/34_provinces_wgs84.geojson /path/to/source.gpkg
python3 -m pipeline.province34_intake /tmp/34_provinces_wgs84.geojson --name-field name --source-url 'https://gis.vn/...' --publisher 'Nguồn do người dùng xác minh' --report audit-output/gisvn-34-provinces.json
```

Thay `--name-field` bằng tên trường thực tế, ví dụ `TEN_TINH`, nếu tệp dùng trường khác. Trình kiểm chứng chỉ nhận **đúng 34 đối tượng Polygon/MultiPolygon** với 34 tên không trùng nhau. Nếu dữ liệu tách một tỉnh ra nhiều feature, gộp có kiểm chứng trước khi nhập.

4. Báo cáo gồm SHA-256 của tệp gốc và GeoJSON bên trong, tổng đỉnh, hệ tọa độ lon/lat, vùng bao WGS84 và kiểm tra hình học cơ bản. Nếu có Shapely, chương trình kiểm tra polygon hợp lệ; nếu không, phần topology được ghi rõ `NOT_CHECKED`.
5. Để dùng trong ứng dụng, cần đối chiếu với dữ liệu có thẩm quyền, kiểm tra giấy phép, duyệt nhãn Hoàng Sa, Trường Sa, Biển Đông, rồi mới biên dịch MVT/PMTiles và kiểm thử Android. **Chương trình không tự bật nguồn MapLibre và không tự sửa `approved_reference.json`.**

## Những điều trình kiểm tra không xác nhận

- Có chính xác 34 tỉnh không đồng nghĩa với đường biên đúng phiên bản mới nhất.
- Một lớp tỉnh không mặc nhiên có đầy đủ đảo, bãi đá, ranh giới quốc gia hoặc ranh giới biển.
- Hình học polygon hợp lệ không chứng minh chủ quyền, căn cứ pháp lý hoặc quyền phát hành.
- Nguồn URL được ghi theo lời khai người dùng, chưa được truy cập hoặc chứng thực tự động.

Giữ dữ liệu tải về trong thư mục riêng, không commit lên GitHub cho đến khi được cấp phép. Mọi kết quả có `p0_status = BLOCKED` và `maplibre_activation_allowed = false`.

