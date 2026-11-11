# Đối chiếu 183 tọa độ địa danh Hoàng Sa/Trường Sa với GeoJSON 34 tỉnh

**Kết quả: Hoàn tất kiểm tra khoảng cách điểm, KHÔNG chứng nhận ranh giới chính thức. P0 BLOCKED.**

## Nguồn và phương pháp

- Phụ lục Thông tư **33/2024/TT-BTNMT**, phần B Hoàng Sa (50 dòng) và C Trường Sa (133 dòng). Bản PDF từ cổng của Bộ: https://mae.gov.vn/noidung/Lists/VBQPPL/Attachments/514/1_DanhMuc_TT_DiaDanh_BanHanh.pdf
- PDF SHA-256: `acde9b561eca24312b81efdcb36a22a8fc74e2dcb431f6c206199ef72c98e841`.
- ZIP người dùng cung cấp (34 GeoJSON): SHA-256 `51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd`. Không commit dữ liệu hình học gốc vì chưa xác minh quyền phát hành.
- PDF ghi tọa độ **VN-2000**; GeoJSON dùng **WGS84**. Mã kiểm tra so sánh giá trị số chưa áp dụng bộ tham số chuyển datum có chứng thực. Khoảng cách chỉ là khoảng cách rà soát, không phải đo đạc pháp lý.
- Tính điểm trong đa giác hoặc khoảng cách geodesic gần đúng tới thành phần MultiPolygon gần nhất. Không thay polygon bằng đảo nổi.

## Kết quả

| Vùng và lớp GeoJSON | Danh mục | Điểm trong polygon | Trong hoặc cách ≤2 km | Cách >5 km |
|---|---:|---:|---:|---:|
| Hoàng Sa, Đà Nẵng (mã 48) | 50 | 34 | 36 | 7 |
| Trường Sa, Khánh Hòa (mã 56) | 133 | 107 | 120 | 7 |
| **Tổng** | **183** | **141** | **156** | **14** |

11/183 địa danh cách xa hơn 10 km. **Hai điểm B50/C133 là điểm đặt nhãn quần đảo, không nhất thiết nằm trên đất nổi**. Các đá, bãi cạn và bãi ngầm cũng không mặc nhiên tương ứng với vùng đất.

## Những vị trí cách polygon trên 5 km (xếp xa nhất trước)

| Mã | Địa danh trong phụ lục | Khoảng cách gần đúng | Loại cảnh báo |
|---|---|---:|---|
| C128 | Đá Vĩnh Tường | 73.697 km | Đá/bãi, kiểm tra phân loại |
| B48 | Đảo Tri Tôn | 58.950 km | Đảo, rà soát ưu tiên |
| C131 | Đá Đồng Thanh | 56.124 km | Đá/bãi, kiểm tra phân loại |
| C129 | Bãi ngầm Nguyệt Xương | 46.937 km | Bãi ngầm, không mặc nhiên là đất |
| B49 | Bãi ngầm Ốc Tai Voi | 38.939 km | Bãi ngầm, không mặc nhiên là đất |
| C123 | Đảo An Bang | 38.770 km | Đảo, rà soát ưu tiên |
| C71 | Đá Núi Mon | 25.563 km | Đá/bãi, kiểm tra phân loại |
| B39 | Bãi cạn Gò Nổi | 21.496 km | Đá/bãi, kiểm tra phân loại |
| B50 | Quần đảo Hoàng Sa (nhãn) | 20.024 km | Điểm nhãn vùng |
| C109 | Đá Châu Viên | 19.323 km | Đá/bãi, kiểm tra phân loại |
| B15 | Đảo Bạch Quy | 17.712 km | Đảo, rà soát ưu tiên |
| B37 | Bãi Thủy Tề Nam nhỏ | 7.985 km | Đá/bãi, kiểm tra phân loại |
| B3 | Đảo Quang Ảnh | 7.013 km | Đảo, rà soát ưu tiên |
| C122 | Bãi ngầm Ngũ Phụng | 6.989 km | Bãi ngầm, không mặc nhiên là đất |

**Điểm cần rà soát ưu tiên:** Đảo Tri Tôn (~58,95 km), Đảo An Bang (~38,77 km), Đảo Bạch Quy (~17,71 km), Đảo Quang Ảnh (~7,01 km). Không được tự sửa vị trí hoặc thêm đất nổi chỉ dựa trên tên và điểm. Mỗi trường hợp phải được kiểm tra nguồn hình học chính thức, phép chuyển hệ tọa độ và tính chất đảo/đá/bãi.

## Ranh giới vẫn chưa được xác minh

Bản đồ hành chính raster/PDF tháng 6/2025 không cung cấp một bộ đa giác GIS có thể so khớp cạnh với cạnh. Danh mục điểm năm 2024 không thay thế ranh giới hành chính 34 tỉnh năm 2025 hoặc đường biên giới biển hợp pháp. Chưa có bộ SHP/GeoPackage/WFS/S-57 được cơ quan có thẩm quyền xác nhận và cấp phép cho việc so sánh hình học đường bao.

Muốn duyệt đầy đủ cần yêu cầu bộ vector chính thức có **chữ ký/xác nhận hoặc metadata nguồn, ngày hiệu lực, hệ tọa độ và phép chuyển datum, danh mục đảo/bãi, đường địa giới có căn cứ pháp lý và giấy phép phân phối lại**. Sau đó mới kiểm tra overlay (hausdorff/buffer/symmetric difference), tính hợp pháp của style/nhãn và Android screenshot zoom/offline.

## Tái lập bằng mã trong repository

```bash
python -m pipeline.official_island_point_catalog --pdf /path/to/phu-luc-TT33-2024.pdf --points-output audit-output/official-bc-points.json
python -m pipeline.verify_official_island_points '/path/to/GeoJSON 34 Tinh VN.zip' audit-output/official-bc-points.json --output audit-output/183-point-qa.json
```

Đầu ra chứa tên và tọa độ điểm công bố cùng khoảng cách tới GeoJSON của người dùng. **Không thay đổi nguồn MapLibre hay `assets/geo/approved_reference.json`; P0 vẫn BLOCKED.**

Người dùng nhận kèm riêng bảng CSV/JSON chi tiết và hai sơ đồ vị trí để mở trong QGIS. Git chỉ lưu metadata, không phân phối lại ZIP GeoJSON người dùng hoặc hình học vector bên thứ ba.

## Nguồn vector địa giới hành chính có thẩm quyền

Có [bản hướng dẫn kiểm tra quyền truy cập WFS, nguồn hình học 34 tỉnh và các bằng chứng cần xin](OFFICIAL_BOUNDARY_SOURCE_ACCESS.md). API chỉ được dùng khi có quyền và xác nhận phiên bản địa giới mới; bản đồ xem được không tự cấp quyền phân phối vector.
