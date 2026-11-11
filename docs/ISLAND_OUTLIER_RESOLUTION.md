# Giải trình 14 vị trí địa danh biển đảo ngoài đa giác GeoJSON

**Trạng thái: 14/14 đã được phân loại và kiểm tra tọa độ; CHƯA phê duyệt hình học đất nổi hoặc ranh giới biển.**

## Kết quả xác minh

Phụ lục chính thức Thông tư 33/2024/TT-BTNMT cung cấp *tọa độ địa danh* VN-2000. Không phải polygon đảo hoặc đường biên. Kiểm tra lại 14 vị trí với 34 GeoJSON người dùng bằng phép chiếu azimuthal equidistant cục bộ để tính khoảng cách mét; kết quả gần như trùng cách đo cũ, trừ vài vị trí điều chỉnh dưới 0,3 km. Kết quả số liệu theo CSV/JSON lưu ngoài Git (để tránh phân phối hình học nguồn chưa cấp phép).

| Loại theo tên chính thức | Số điểm | Hướng xử lý |
| --- | ---: | --- |
| **Đảo** | 4 | Tọa độ được nguồn thứ hai kiểm tra độc lập; vẫn thiếu đường bao đất nổi |
| **Đá hoặc bãi cạn/bãi** | 6 | Có điểm địa danh; độ nổi/cách thể hiện địa vật và polygon chưa xác minh |
| **Bãi ngầm** | 3 | Không được mong đợi có đa giác đất nổi; chỉ là địa danh/đối tượng dưới mặt biển |
| **Điểm nhãn quần đảo** | 1 | Điểm đặt tên vùng, không phải đất đảo |

## Bốn đảo có đối chứng vị trí độc lập

| Mã | Địa danh | Nguồn tọa độ thứ hai | Độ lệch vị trí so với điểm TT33 | Cách đa giác tỉnh gần nhất |
| --- | --- | --- | ---: | ---: |
| B48 | Đảo Tri Tôn | Cổng thông tin Đà Nẵng, phút thập phân | ~0,128 km | ~58,950 km |
| B15 | Đảo Bạch Quy | Cổng thông tin Đà Nẵng, phút thập phân | ~0 km | ~17,711 km |
| B3 | Đảo Quang Ảnh | Cổng thông tin Đà Nẵng, phút thập phân | ~0,836 km | ~7,013 km |
| C123 | Đảo An Bang | AMTI/CSIS GPS và thông báo cơ quan hàng hải địa phương | ~0,240 km (AMTI) | ~38,770 km |

Tọa độ tại trang Đà Nẵng được thể hiện theo **phút thập phân**: ví dụ `15°47,2′` không phải `15°47′02″`; quy đổi đúng là `15°47′12″`. Số liệu tọa độ PDF là VN-2000 trong khi nguồn thứ hai có thể ở hệ khác, nên chỉ dùng để kiểm chứng vị trí cấp vùng, không làm ranh giới địa chính.

Tham khảo chính thức:
- https://mae.gov.vn/noidung/Lists/VBQPPL/Attachments/514/1_DanhMuc_TT_DiaDanh_BanHanh.pdf
- https://soyte.danang.gov.vn/web/dng/-/ubnd-huy%E1%BB%87n-ho%C3%A0ng-sa
- https://cangvuhanghainhatrang.gov.vn/index.aspx?id=1801&page=detail
- Nguồn nghiên cứu độc lập (không phải cơ quan phê duyệt Việt Nam): https://amti.csis.org/amboyna-cay/

## Không có phép hợp thức hóa giả

1. **Không tự đắp đảo/đá** thành vùng đất chỉ vì có tọa độ. Bốn đảo có điểm tọa độ đáng tin cậy nhưng GeoJSON gốc không có đường bao phủ điểm tương ứng.
2. **Không lấy đa giác tỉnh làm đường bờ đất nổi**. Vùng ngoài khơi có thể là đa giác hành chính tổng quát hóa.
3. Đối với sáu đá/bãi, tên và tọa độ được PDF ghi, nhưng chưa có dữ liệu bathymetry/đất nổi chuyên đề để biết loại hình cần tô trong MapLibre.
4. Phụ lục có tọa độ hệ VN-2000; báo cáo QA giữ bản gốc và tạo gói điểm **GeoPackage EPSG:4756**. Không gán nhầm VN-2000 thành GeoJSON WGS84. Chỉ dùng bản đồ điểm khi đã có phép biến đổi tọa độ được duyệt.
5. Chưa xác minh giấy phép phân phối bộ GeoJSON 34 tỉnh; không commit geometry hoặc đóng gói trong APK.
6. Các nhãn Hoàng Sa/Trường Sa/Biển Đông vẫn cần kiểm thử hiển thị MapLibre trên Android ở các mức zoom, sáng/tối, online/offline.

## Tái lập

```bash
python -m pipeline.official_island_point_catalog --pdf /path/to/phu-luc-tt33.pdf --points-output audit-output/tt33-points.json
pip install -r pipeline/requirements-review-gpkg.txt
python -m pipeline.resolve_island_reference_gaps '/path/to/GeoJSON 34 Tinh VN.zip' audit-output/tt33-points.json --output-dir audit-output/outlier-review
```

Đầu ra gồm `point_classification.json` và `island_reference_points_VN2000_REVIEW_ONLY.gpkg` với EPSG:4756. Chỉ được phép dùng cho QA, không tự động bật MapLibre.

**Kết luận cụ thể:** Những trường hợp bãi ngầm và điểm nhãn vùng được giải trình vì không cần polygon đất nổi; bốn đảo có nguồn xác nhận tọa độ cấp vùng; sáu đá/bãi được phân loại. Tuy nhiên **không một đa giác đất đảo hay đường biển nào được cấp phê duyệt từ phép đối chiếu điểm**. Các lớp hiển thị vẫn P0 BLOCKED.

