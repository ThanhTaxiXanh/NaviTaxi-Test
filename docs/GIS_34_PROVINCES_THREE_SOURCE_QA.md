# Đối chiếu 3 nguồn GIS 34 tỉnh, thành (11/11/2026)

**REVIEW_REQUIRED_NOT_P0. Không có nguồn nào trong phép so sánh này cấp quyền phát hành.**

## Nguồn

1. ZIP của người dùng từ gis.vn theo thông tin người dùng: 34 GeoJSON, SHA-256 `51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd`. Nhà cung cấp chưa xác nhận trực tiếp ngày công bố, bản quyền và quyền phân phối lại.
2. Ảnh `IMG_4448.png` người dùng gửi: chú thích Cục Đo đạc, Bản đồ và Thông tin địa lý Việt Nam, tháng 6/2025, tỷ lệ 1:9.000.000, SHA-256 `23153838a0214ad7f1526eed9d7bc74a1557cf0fe437ea2ddb088be43ac49fea`. Bản raster có nhãn Hoàng Sa/Trường Sa nhưng chưa georeference, không dùng để xác nhận từng đỉnh ranh giới.
3. GitHub `nguyenduy1133/Free-GIS-Data`, file sau năm 2025 `Provinces.geojson` tại commit `ccb9f4ae992418bfeefd06da1eb42d0249632176`, 15.927.181 byte, SHA-256 `d8a06b4d3a0e5612ec3319afed4c75ff7ffc46e6ffd82e9e40df24090133a664`. README cho biết dùng công khai và yêu cầu ghi nguồn, song cũng có tuyên bố miễn trừ độ chính xác; repo không khai báo giấy phép SPDX chính thức.

Đường dẫn tham khảo: https://github.com/nguyenduy1133/Free-GIS-Data
Quy trình: https://github.com/ThanhTaxiXanh/NaviTaxi-Test/actions/runs/42948888241
Trang thông báo chính thức về bản đồ 34 tỉnh tháng 6/2025: https://dosmvn.mae.gov.vn/tin-tuc--su-kien/ban-do-hanh-chinh-chi-tiet-34-tinh-thanh-moi-cua-viet-nam-2110.htm

Metadata `Provinces.xml` của GitHub ghi nguồn xử lý ArcGIS `JoinField` ngày 17/06/2025. Việc ghi nguồn này không xác thực dữ liệu vector đã được phê duyệt.

## Đối chiếu ảnh và ZIP

- Theo ngưỡng trọng tâm kinh độ >110°Đ, Đà Nẵng có 18 polygon ngoài khơi nằm trong `[111.45145,16.00768,112.77734,17.12112]`, phù hợp về vùng với cụm tên Hoàng Sa trên ảnh.
- Theo ngưỡng >111°Đ, Khánh Hòa có 297 polygon ngoài khơi trong `[111.45269,6.93106,117.39326,11.73241]`, phù hợp về vùng với cụm tên Trường Sa trên ảnh.
- Một số polygon có diện tích trên 100 km², lớn nhất khoảng 120,24 km² ở nhóm Đà Nẵng và 316,08 km² ở nhóm Khánh Hòa. **Không coi những polygon này là đất đảo vật lý hoặc đường biển pháp lý.**
- Ảnh raster tỷ lệ 1:9 triệu không có phép quy chiếu để xác nhận từng hình học, đỉnh, đường biển, hoặc phép đối chiếu pixel chính xác.

## ZIP với GeoJSON GitHub: đã kiểm tra trực tiếp bằng CI

- GitHub có 34 feature. 33/34 tên được ghép duy nhất; 22/33 vùng bao có IoU hộp bao >=0,99; 25/33 diện tích trắc địa lệch <=1%. Không hiểu chỉ số IoU của hộp bao thành IoU đa giác.
- **Lỗi nguồn GitHub:** feature index 9 và 19 đều có `TinhThanh=Lạng Sơn`, nhưng thiếu tên `Đồng Tháp`. Feature 9 có bbox `[105.18517,10.13450,106.82253,10.97339]`, thuộc khu vực Đồng Tháp theo dữ liệu người dùng, không thuộc khu vực Lạng Sơn. File tham khảo có bất thường thuộc tính/liên kết dữ liệu rõ ràng.
- TP.HCM: giới hạn phía nam GitHub là 10,32029°B, nhưng ZIP người dùng đạt 8,57751°B. Có khác biệt lớn về hình học khu vực đảo phía nam.
- Khánh Hòa: GitHub đạt 117,81734°Đ và 7,39143°B; ZIP đạt 117,39326°Đ và 6,93106°B, khác biệt ngoài khơi.
- Đà Nẵng: GitHub 36 thành phần polygon, ZIP 32, vùng bao gần trùng nhau.
- Khánh Hòa và Cà Mau trong ZIP còn có độ lệch lớn khi so diện tích hình học với thuộc tính `dtich_km2`; cần xác nhận định nghĩa diện tích của nhà cung cấp.

**Kết luận:** Giữ ZIP của người dùng là dữ liệu ứng viên ưu tiên cho phát triển; không thay bằng repo GitHub, không suy ranh giới từ ảnh. Hai nguồn vector có thể có cùng tổ tiên dữ liệu, nên sự gần trùng khớp không phải chứng minh GIS chính thức. Luôn giữ `assets/geo/approved_reference.json` ở `pending`, `P0=BLOCKED`, MapLibre chưa kích hoạt ranh giới.

Kiểm tra có thể tái lập bằng `python -m pipeline.compare_public_gis_reference`. Chỉ lưu thống kê/metadata, không commit hình học ZIP hoặc bản gốc từ GitHub.
