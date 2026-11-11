# Tiếp nhận vector địa giới chính thức cho NaviTaxi

**Trạng thái hiện tại:** Chưa có bộ vector ranh giới hành chính 34 tỉnh/thành năm 2025 hoặc vector ranh giới biển được cấp quyền sử dụng và xác nhận nguồn. Phép kiểm tra 183 điểm trong Thông tư 33/2024 chỉ kiểm tra vị trí tên địa danh; KHÔNG kiểm tra được từng cạnh polygon.

## Nguồn cần làm việc

- Cục Đo đạc, Bản đồ và Thông tin địa lý Việt Nam (DOSMVN), trang thông tin bản đồ hành chính 34 tỉnh tháng 6/2025: https://dosmvn.mae.gov.vn/tin-tuc--su-kien/ban-do-hanh-chinh-chi-tiet-34-tinh-thanh-moi-cua-viet-nam-2110.htm
- Hệ thống quản lý cơ sở dữ liệu địa giới hành chính: https://thongtin.diagioi.gov.vn/trangchu.aspx
- Tài liệu dịch vụ WFS của hệ thống: https://thongtin.diagioi.gov.vn/docs/files/code/REST_API/wfs-js.html
- Tài liệu WMS và tích hợp map: https://thongtin.diagioi.gov.vn/docs/files/code/REST_API/wms-js.html ; https://thongtin.diagioi.gov.vn/docs/files/code/JavaScript_API/map-js.html
- Thông tư 33/2024/TT-BTNMT và Phụ lục B/C với 183 vị trí Hoàng Sa và Trường Sa: https://mae.gov.vn/noidung/Lists/VBQPPL/Attachments/514/1_DanhMuc_TT_DiaDanh_BanHanh.pdf

## Phạm vi kiểm chứng của tài liệu WFS

Tài liệu website hiện còn truy cập được có ví dụ **GetFeature** cho WFS 2.0.0 và định dạng GeoJSON/GML, cùng tên lớp tham khảo `kgtinh_diaphan`. Tuy nhiên, ví dụ URL sử dụng máy chủ cũ và lớp mã trước sáp nhập; phần hướng dẫn JavaScript còn ví dụ `token: 'your api key'`. **Không có bằng chứng rằng endpoint hiện hoạt động, cho phép tải không cần tài khoản, có đủ 34 tỉnh năm 2025, hoặc được phép dùng thương mại/offline.**

Tuyệt đối không vượt qua đăng nhập/API key, không quét dữ liệu từ dịch vụ thiếu quyền truy cập. Việc bản đồ có thể xem công khai không đồng nghĩa được phép tải vector về để nhúng APK.

## Dữ liệu phải yêu cầu hoặc được cấp phép

1. SHP/GeoPackage/GML/WFS chính thức của 34 địa phận hành chính tỉnh/thành sau sáp nhập (kèm ngày hiệu lực, mã tỉnh, tên đơn vị, phiên bản, CRS và bộ tham số đổi VN-2000 -> WGS84).
2. Dữ liệu riêng phân biệt **đa giác hành chính**, **đường bờ/đất nổi**, **đảo/đá/bãi cạn/bãi ngầm** và **đường biên giới quốc gia**. Không sử dụng một lớp tỉnh tổng quát hóa để tô đất hoặc giả định là ranh giới biển.
3. Dữ liệu pháp lý ranh giới biển, nếu có quyền hiển thị và cơ sở điều ước/luật được cơ quan có thẩm quyền chỉ định. Không suy diễn vùng biển từ bbox, centroid hoặc điểm nhãn.
4. Tài liệu nguồn có dấu xác nhận hoặc phiên bản xác minh được, điều khoản cấp phép cho ứng dụng di động, offline, phân phối và tái phân phối; yêu cầu ghi nguồn nếu có.

## Quy trình đối chiếu sau khi được cấp vector

- Kiểm tra SHA-256 nguồn, hệ tọa độ, epoch datum, schema và số tên/mã tỉnh theo Quyết định 19/2025/QĐ-TTg.
- Chuẩn hóa cả hai bộ vào cùng CRS bằng phép biến đổi VN-2000 hợp lệ; bảo quản cả bản gốc và metadata của phép chuyển hệ.
- So sánh hình học từng tỉnh với ZIP người dùng: `is_valid`, `covers`, diện tích sai khác đối xứng, khoảng cách biên Hausdorff theo hệ tọa độ mét, topological gaps/overlaps, phần hải đảo rời xa bờ và các đoạn biên có sai lệch.
- Đối chiếu 183 tọa độ đảo/bãi theo phụ lục TT33, nhưng phân loại riêng tên đảo, đá, bãi ngầm và nhãn vùng. Đối chiếu đường bao với lớp chuyên đề được chính thức xác nhận, không chỉ với tọa độ tên.
- Thẩm định phong cách MapLibre, mức zoom, đa ngôn ngữ, nhãn Hoàng Sa/Trường Sa/Biển Đông, dữ liệu offline và ảnh Android rồi mới cân nhắc P0.

## Kết quả xác minh hiện tại

**183/183 vị trí danh mục đã được rà soát với ZIP của người dùng**, 141 nằm trong MultiPolygon và 14 cách >5 km. Các điểm này có thể chỉ ra dữ liệu thiếu/khác loại hình học, chưa chứng minh rằng bản đồ nguồn sai pháp lý. Các ranh giới đa giác chính thức và ranh giới biển **chưa được đối chiếu** vì chưa có bộ GIS vector có thẩm quyền, ngày hiệu lực 2025 và quyền phân phối phù hợp.

Giữ `assets/geo/approved_reference.json` ở `pending`, `P0=BLOCKED`. Không đóng gói ranh giới chưa được phê duyệt vào MapLibre.
