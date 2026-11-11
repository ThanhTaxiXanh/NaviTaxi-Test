# GeoPackage kiểm định 34 tỉnh, thành (không phải bản đồ phát hành)

Mã: `pipeline/province34_review_gpkg.py`. Nhận ZIP người dùng gửi gồm 34 GeoJSON một-tỉnh-một-file, kiểm tra SHA-256 nguồn, mã/tên tỉnh và tính hợp lệ MultiPolygon; xuất ra **GeoPackage** để kiểm tra trong QGIS.

**Gói này là dữ liệu hành chính ứng viên, không phải lớp đất nổi vật lý và KHÔNG được tự động gắn vào MapLibre.**

## Cách tạo lại

```bash
pip install -r pipeline/requirements-review-gpkg.txt
python -m pipeline.province34_review_gpkg 'GeoJSON 34 Tinh VN.zip' --require-sha256 51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd --output audit-output/NaviTaxi_34_Tinh_GIS_REVIEW_ONLY.gpkg --manifest audit-output/province34-gpkg-manifest.json
```

File nguồn người dùng **không lưu trong GitHub**. Gói review sinh ra cũng không được đưa vào Flutter assets hoặc GitHub public trước khi xác nhận điều kiện sử dụng. `audit-output/` đã nằm trong `.gitignore`.

## Hai lớp GIS

- `province34_review` (34 MultiPolygon): giữ toàn bộ hình học gốc, mã tên đơn vị, SHA-256 từng GeoJSON và trạng thái `QUARANTINE_NOT_P0`. Bản xuất được mở lại và kiểm tra Shapely `equals()` không thay đổi hình học.
- `offshore_components_REVIEW_ONLY` (315 Polygon trong ZIP đã gửi): chỉ sao chép các thành phần của Đà Nẵng có trọng tâm trên 110°Đ và Khánh Hòa trên 111°Đ. **Đây là bộ lọc thô bằng kinh độ**, không được coi các polygon là đảo, đặc khu có ranh giới chính thức hoặc quyền tài phán biển.

## Kết quả lần chạy từ ZIP của người dùng

- ZIP đầu vào SHA-256 `51779d2585600ec053827a60890ba61cd2192f19b5ee153d38be18a2611d24cd`.
- 34 tỉnh và 315 thành phần ngoài khơi, gồm 18 từ Đà Nẵng và 297 từ Khánh Hòa.
- Đà Nẵng có 10 polygon vùng xa bờ >25 km², 2 polygon >100 km²; lớn nhất ~120,24 km².
- Khánh Hòa có 30 polygon vùng xa bờ >25 km², 6 polygon >100 km²; lớn nhất ~316,08 km².
- GeoPackage riêng tư xuất ra ~22,5 MB, WGS84, hai lớp, đạt đối chiếu hình học vòng lặp (roundtrip).

Không gọi những diện tích này là diện tích đất đảo nổi. Chúng có thể biểu thị phạm vi hành chính được tổng quát hóa hay bản đồ nguồn đã biên tập. Việc đối chiếu từng đảo/bãi, ngày xuất, giấy phép và xác minh cơ quan nhà nước chưa xong.

**Chốt chặn:** `p0_pass=false`, `maplibre_activation_allowed=false`, không chỉnh sửa `approved_reference.json` và không kích hoạt nguồn bản đồ chưa được kiểm duyệt.

## Kiểm thử

Workflow `Quarantined GeoPackage review tool` chạy bộ thử synthetic để xác nhận ghi/đọc GeoPackage và chốt chặn. Bộ synthetic hoàn toàn giả lập, không đại diện một ranh giới thật.
