# Tiếp nhận dữ liệu 34 tỉnh/thành vào NaviTaxi (ứng viên gis.vn)

**Trạng thái: chờ GeoJSON gốc từ nhà cung cấp, không được tự phê duyệt.** Ngày 11/11/2026 đã truy cập được trang công khai `https://gis.vn/don-vi-hanh-chinh-viet-nam` bằng trình đọc HTML và trình duyệt CI. Trang có nút GeoJSON rõ ràng cho **Việt Nam (tỉnh thành) - 34**. Tuy nhiên, không có liên kết tải trực tiếp trong HTML; trình duyệt chưa lấy được tệp nguồn do nút không hiển thị tại trạng thái trang mặc định. Chưa tìm thấy quyền tái sử dụng hoặc công bố phiên bản đủ để xác minh. Không được coi tên miền hay việc có nút tải là chứng cứ bản đồ chính thức.

## Bước nhập dữ liệu

1. Mở https://gis.vn/don-vi-hanh-chinh-viet-nam, chọn **sau sáp nhập / 34 tỉnh**, ở dòng **Việt Nam (tỉnh thành) - 34** chọn **GeoJSON**. Không chọn bộ phường/xã 34 hoặc tỉnh/thành 63. Nếu giao diện yêu cầu đăng nhập, chỉ dùng tài khoản của bạn; không chia sẻ thông tin đăng nhập. Trên trình duyệt, kiểm tra rõ nhà phát hành, ngày công bố, phiên bản địa giới, nguồn GIS, phương thức cấp phép và khả năng sử dụng offline/redistribute; tải tệp bằng chức năng công khai hoặc giấy phép hợp lệ. Không lấy trộm tile hoặc vượt cơ chế bảo vệ.
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


## Kiểm tra tên 34 tỉnh/thành với danh mục Chính phủ

Sau bước tiếp nhận GeoJSON, so sánh 34 tên với **Quyết định 19/2025/QĐ-TTg**
(danh mục/mã cấp tỉnh có hiệu lực từ 01/07/2025):

```bash
python -m pipeline.province34_intake /path/to/provinces.geojson --name-field name --report audit-output/34provinces-intake.json
python -m pipeline.province34_name_review audit-output/34provinces-intake.json
```

Tệp tham chiếu chỉ ghi **34 tên và mã đơn vị**, không chứa ranh giới.
Kiểm tra này chỉ phát hiện tên sai hoặc lỗi thời, **không chứng minh hình học
ranh giới, quyền tái sử dụng dữ liệu gis.vn, địa giới biển đảo hay P0 PASS**.

## Biên bản thử tải trực tiếp ngày 11/11/2026

- HTML của gis.vn trả về HTTP 200. Nút xuất 34 tỉnh gọi hàm public `taigeojson_tong_tuheader_SAUSAPNHAP('TONG_VN_TINHTHANH', ...)`.
- Trình duyệt Chromium tự động trên GitHub Actions mở đúng trang, thấy tên trang và 1 nút GeoJSON cấp tỉnh. Tuy nhiên nút có trạng thái `visible=false`, giao diện hiển thị `Chưa đăng nhập` và không có sự kiện tải trong phiên này. Không có tệp GeoJSON tải thành công.
- Workflow `GIS.vn official public GeoJSON button probe` chỉ lưu `inspection.json`, **không lưu hoặc công bố dữ liệu chưa rõ quyền tái sử dụng**.
- Danh mục 34 tỉnh được đối chiếu bằng **tên và mã** theo Quyết định 19/2025/QĐ-TTg (nguồn: https://baochinhphu.vn/chi-dao-dieu-hanh-cua-chinh-phu-thu-tuong-chinh-phu-ngay-4-7-2025-1-102250704190956567.htm). Đây chỉ là kiểm tra tên và mã, không thay thế ranh giới GIS chính thức.
- Do chưa có tệp tải và chưa xác minh điều khoản cấp phép, **không đưa GeoJSON vào tài sản Flutter và không bật MapLibre**.

## Kiểm tra ZIP thực tế người dùng cung cấp ngày 11/11/2026

Người dùng đã gửi `GeoJSON 34 Tinh VN.zip` (SHA-256
`51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd`).
Tệp chứa **34 GeoJSON riêng biệt**, mỗi tệp một MultiPolygon tỉnh/thành,
cộng 34 tệp `__MACOSX` chỉ chứa metadata. Không có lỗi ZIP CRC.
Bộ nhập `pipeline.province34_intake` nay đọc trực tiếp kiểu ZIP này mà
không giải nén ra đĩa. Trường tên mặc định tự chọn `ten_tinh` khi nhập ZIP
34 GeoJSON của nhà cung cấp, không giả định trường `name`.

QA độc lập đã kiểm tra 1.312.216 tọa độ đỉnh trên 2.707 vòng polygon.
34 tên/mã khớp danh mục Chính phủ 2025; Shapely xác nhận 34 hình học hợp lệ,
không thấy vùng chồng diện tích đáng kể giữa các đơn vị.

**Cảnh báo định lượng:** diện tích trắc địa WGS84 tính từ hình học Khánh Hòa
là khoảng **11.954 km²**, nhưng thuộc tính `dtich_km2` ghi **8.556,10 km²**
(chênh +39,71%); Cà Mau là khoảng **7.586 km²** so với thuộc tính
**6.310,45 km²** (+20,22%). Các thành phần polygon xa bờ của Đà Nẵng và
Khánh Hòa có những vùng đơn lẻ từ hàng chục đến hơn 300 km². Chúng có thể
biểu diễn vùng hành chính/đảo theo cách tổng quát hóa; **không được coi
là diện tích đất đảo thật hoặc ranh giới biển đã xác minh**.

Báo cáo metadata kiểm định (không chứa hình học gốc) được lưu ở
`docs/audits/2026-11-11-user-province34-zip-summary.json`.
Tệp GeoJSON gốc và bản ghép **không được commit lên Git** vì chưa xác minh
được ngày công bố, căn cứ và quyền phân phối lại từ gis.vn.
Chốt chặn bản đồ **P0 BLOCKED** và không kích hoạt nguồn MapLibre.

Chạy bằng lệnh:

```bash
python -m pipeline.province34_intake 'GeoJSON 34 Tinh VN.zip' --report audit-output/gisvn-34-source.json
python -m pipeline.province34_name_review audit-output/gisvn-34-source.json
```
