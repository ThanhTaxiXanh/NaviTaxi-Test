# VN-2000 → WGS84: giới hạn phép chuyển tọa độ ngoài khơi

**Kiểm tra ngày 11/11/2026** đối với 183 điểm biển đảo trong Phụ lục Thông tư 33/2024/TT-BTNMT. Sử dụng thông tin EPSG/PROJ trong `pyproj 3.7.2`. Không có phép chuyển hệ nào trong kiểm tra này được phê duyệt dùng ngoài khơi.

## Kết quả quan trọng

Hai phép chuyển được thư viện nhận diện: `VN-2000 to WGS 84 (2)` và `VN-2000 to WGS 84 (1)`. Cả hai ghi `scope: Academic research, not officially adopted` và phạm vi sử dụng là **trên đất liền** hoặc vùng **Đồng bằng sông Cửu Long**. **0/183 điểm Hoàng Sa/Trường Sa nằm trong vùng sử dụng công bố của cả hai phép chuyển.**

Dùng chúng ngoài vùng chỉ để đo *độ nhạy toán học*, tọa độ dịch khoảng **223–226 m**. Vì 14 điểm đang sàng lọc cách đa giác gần nhất ít nhất gần **6,99 km**, một dịch chuyển nhỏ như vậy không giải thích các sai khác này. **Cả 14 điểm vẫn vượt ngưỡng sàng lọc 5 km**. Điều này không đồng nghĩa tất cả 14 là lỗi: bãi ngầm, điểm nhãn vùng và các đảo/đá thiếu hình học vẫn cần phân loại riêng.

**Cảnh báo:** độ chính xác danh nghĩa 1 m do EPSG ghi chỉ có ý nghĩa *trong vùng áp dụng*, không chứng minh độ chính xác ngoài khơi. Không dùng kết quả này để xuất các điểm đã “chuyển WGS84 chính thức”, tạo đất đảo hoặc phê duyệt ranh giới.

## Tái lập

Tạo JSON 183 điểm từ PDF và chạy:

```bash
python -m pip install pyproj==3.7.2
python -m pipeline.official_island_point_catalog --pdf /path/to/source.pdf --points-output audit-output/official-points.json
python -m pipeline.vn2000_datum_scope_audit audit-output/official-points.json --output audit-output/datum-scope-qa.json
```

Workflow `Official 2024 island point reference QA` tạo lại báo cáo từ nguồn chính thức (không đưa tọa độ đã chuyển sai vào ứng dụng). Báo cáo được chốt trong `docs/audits/2026-11-11-vn2000-datum-offshore-scope.json`.

**Muốn hoàn tất P0**, cần có phương pháp chuyển VN-2000 sang WGS84 **được chấp nhận cho vùng ngoài khơi**, hoặc nguồn địa danh WGS84 được bên có thẩm quyền xác nhận, sau đó thử nghiệm nhãn/style/render thực tế. P0 tiếp tục BLOCKED.
