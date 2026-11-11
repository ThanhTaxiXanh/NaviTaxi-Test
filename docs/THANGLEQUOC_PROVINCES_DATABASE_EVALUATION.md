# Đánh giá tích hợp thanglequoc/vietnamese-provinces-database cho NaviTaxi

Ngày đánh giá: 2026-11-11. **Kết luận: CÓ THỂ TÍCH HỢP cho dữ liệu hành chính và tìm địa chỉ; chưa được thay thế nền bản đồ P0 hoặc mạng đường dẫn đường.**

## Phiên bản đã xem trực tiếp

- Repository: https://github.com/thanglequoc/vietnamese-provinces-database
- Nhánh: `master`, revision đã kiểm tra: `8b78ba5118715e1fa81769286724db79346abf52`.
- Release: `v5.2.0` (2026-09-21); `json/vn_provinces_metadata.json` ghi `DatasetVersion=v5.2.0`, `LatestDecree=388/NQ-UBTVQH16`, `GeneratedAt=2026-09-20T13:13:17Z`.
- License [MIT](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/LICENSE) của repository. Khi sao chép/phân phối tài liệu thuộc MIT cần lưu notice và copyright tác giả. **Không suy ra tự động quyền tái phân phối mọi hình học GIS từ bên thứ ba**.
- README nêu danh mục tỉnh/xã xuất phát từ API Tổng cục/ Cục Thống kê, nhưng nguồn hình học GIS xuất phát từ `sapnhap.bando.com.vn`, Bản đồ tham chiếu đơn vị hành chính do Nhà xuất bản Tài nguyên Môi trường và Bản đồ Việt Nam công bố. Cần kiểm tra quyền/tư cách cấp phép riêng của nguồn hình học trước khi nhúng bản phát hành.

## Kiểm tra dữ liệu thực, không chỉ README

- `json/vn_only_simplified_json_generated_data_vn_units_minified.json`: parse thành công, **34 mã tỉnh khác nhau, 3.321 mã xã/phường khác nhau**, không thấy ward nào tham chiếu sai mã tỉnh.
- **34/34 mã tỉnh trùng** với roster `assets/geo/province34_names_2025.json` của NaviTaxi. So chuỗi có hai biến thể chính tả `Thanh Hóa/Thanh Hoá` và `Khánh Hòa/Khánh Hoà`; xử lý so tên có chủ ý, không sửa mã hành chính.
- Cập nhật `Thành phố Bắc Ninh` (`24`), `Thành phố Đồng Nai` (`75`), `Thành phố Quảng Ninh` (`22`). Đã đối chiếu riêng các nghị quyết thành lập thành phố qua cổng Chính phủ: 39/2026/QH16, 30/2026/QH16 và 36/2026/QH16. Bộ roster 2025 có thể chưa phản ánh cấp hành chính mới.
- Thực tế có **34 GeoJSON cấp tỉnh và 3.321 cấp xã/phường** trong `json/geojson/`, kèm ZIP `json/vn_provinces_wards_geojson.zip`. Định dạng `FeatureCollection` mỗi tệp một `Feature`, `MultiPolygon` EPSG:4326.
- Có mã `20333` = **Đặc khu Hoàng Sa**, liên kết tỉnh `48` (Đà Nẵng); mã `22736` = **Đặc khu Trường Sa**, liên kết tỉnh `56` (Khánh Hòa). Repo cũng cung cấp hai GeoJSON riêng: `json/geojson/48_da_nang/wards/20333_hoang_sa.geojson` và `json/geojson/56_khanh_hoa/wards/22736_truong_sa.geojson`.
- Kiểm tra hai GeoJSON tỉnh: Đà Nẵng có **53 thành phần MultiPolygon**, bbox `[107.208588,14.953287,112.736122,17.120279]`; Khánh Hòa có **164 thành phần**, bbox `[108.549378,7.183812,117.827998,12.869092]`.
- Kiểm tra sơ bộ điểm-vào-đa-giác cho **bốn tọa độ đảo** từ danh mục tham chiếu TT33/2024 (so số liệu VN-2000 với geometry WGS84, *chưa có phép chuyển datum được thẩm định*): **Bạch Quy và An Bang** nằm trong đa giác tỉnh tương ứng; **Tri Tôn và Quang Ảnh** không nằm trong. Cùng kết quả cho hai lớp đặc khu. Đây chỉ là kiểm tra điểm gần đúng; chưa đối chiếu tất cả 183 vị trí, không chứng nhận polygon pháp lý.

## Đề xuất chức năng NaviTaxi

| Ứng dụng | Quyết định | Dữ liệu |
| --- | --- | --- |
| Gợi ý địa chỉ và lọc tên tỉnh, phường/xã khi nhập điểm đón-trả | **NÊN** | JSON `vn_only_simplified...` hoặc bản full có code và `ProvinceCode` |
| Chọn hành chính theo mã trong hồ sơ/hoá đơn taxi | **NÊN** | mã tỉnh 2 ký tự, mã xã 5 ký tự; cập nhật theo version |
| Giao diện tên tỉnh thành mới năm 2026 | **NÊN** | `FullName` từ v5.2.0; giữ đối chiếu mã |
| MapLibre lớp địa giới tỉnh và xã/phường | **CHỈ QA** | GeoJSON; phải kiểm tra source license, topological geometry, ảnh và offline |
| Hình học đảo/đá/bãi và ranh giới biển | **KHÔNG tự duyệt** | 2/4 điểm đảo ví dụ chưa được cả hai lớp tỉnh/đặc khu bao phủ; phân loại và geometry chưa đủ |
| Định tuyến taxi / đường 1 chiều / cấm rẽ | **KHÔNG phù hợp** | repo không cung cấp đồ thị đường |
| Giới hạn tốc độ và biển báo | **KHÔNG phù hợp** | repo không cung cấp dữ liệu biển báo/tốc độ theo đoạn đường và hiệu lực |

## Phương án tích hợp an toàn

1. **Ghim release `v5.2.0`**, không tải trực tiếp `master` trong ứng dụng; ghi SHA-256 bản JSON, `DatasetVersion`, `LatestDecree`, ngày tải. Để nâng cấp trong tương lai phải chạy diff và đối chiếu tài liệu quy phạm có hiệu lực.
2. Chỉ nhập trường cần cho address lookup: `Code`, `FullName`, `ProvinceCode` của xã, loại `Phường/Xã/Đặc khu`, metadata nguồn. Không tạo vị trí GPS giả từ mã hành chính, `postalCode` hay tâm bbox.
3. Áp dụng chuẩn Unicode tiếng Việt cho tìm kiếm có dấu/không dấu và tra cứu alias, nhưng giữ tên hiển thị chính thức. Ưu tiên mã hành chính khi liên kết với nguồn NaviTaxi khác.
4. Đóng gói JSON offline gọn trong app (tệp minified khoảng **0,29 MB** ở bản kiểm tra); nếu cần geospatial reverse-lookup mới chuyển GeoJSON sang kho SQLite/GeoPackage/vector tiles sau rà soát.
5. Hai tệp đặc khu và tất cả địa giới ngoài khơi nằm trong **quarantine GIS**. Không dùng chúng để thay `approved_reference.json`, không chuyển `map_release.p0_pass=true`, không tự tô polygon hành chính thành đất nổi và không suy diễn đường biên giới biển.
6. Chỉ khi đã kiểm tra provenance/license GIS bên thứ ba, overlay hình học với nguồn hiện hữu, 183 địa danh, các điểm đảo chưa có polygon, ảnh Android/zoom/offline, mới đề xuất xem xét lớp hiển thị P0. Cổng kiểm tra an toàn giao thông/biển báo/tốc độ cần độc lập.

## Tài liệu kiểm chứng

- Repo & README: https://github.com/thanglequoc/vietnamese-provinces-database và https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/README_vi.md
- [Dữ liệu JSON địa danh](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/json/vn_only_simplified_json_generated_data_vn_units_minified.json)
- [GIS instructions](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/docs/gis/README.md)
- [GeoJSON Đà Nẵng](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/json/geojson/48_da_nang/48_da_nang.geojson)
- [GeoJSON Khánh Hòa](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/json/geojson/56_khanh_hoa/56_khanh_hoa.geojson)
- [Đặc khu Hoàng Sa](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/json/geojson/48_da_nang/wards/20333_hoang_sa.geojson)
- [Đặc khu Trường Sa](https://github.com/thanglequoc/vietnamese-provinces-database/blob/master/json/geojson/56_khanh_hoa/wards/22736_truong_sa.geojson)
- Nghị quyết Bắc Ninh: https://vanban.chinhphu.vn/?docid=219328&pageid=27160
- Nghị quyết Quảng Ninh: https://vanban.chinhphu.vn/?classid=1&docid=219325&orggroupid=1&pageid=27160
- Nghị quyết Đồng Nai: https://vanban.chinhphu.vn/?docid=218009&pageid=27160

**Kết luận vận hành:** nguồn dữ liệu hành chính `v5.2.0` là ứng viên đáng đưa vào bộ tìm địa chỉ của NaviTaxi; GIS dùng bổ trợ đối chiếu và chế độ kiểm duyệt. **Không nhập hình học/sơ đồ từ đây trực tiếp vào APK P0 đang phát hành.** Bản đồ đường, biển báo, giới hạn tốc độ và dẫn đường phải lấy từ các nguồn chuyên đề khác.
