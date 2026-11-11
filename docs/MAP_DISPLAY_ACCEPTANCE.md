# Tiêu chí nghiệm thu bản đồ NaviTaxi theo sai khác hợp lý

Ngày 11/11/2026: người dùng xác định bản đồ dẫn đường không cần khớp 100% từng đỉnh/diện tích với bản tham chiếu. Tiêu chí chính là cách hiển thị Hoàng Sa, Trường Sa, Biển Đông theo cấu hình Việt Nam của dự án, không có sai lệch lãnh thổ nghiêm trọng chưa được giải quyết.

## Chấp nhận được

- Bản đồ có đủ 34 tỉnh/thành, tên và mã đúng. Hình học hợp lệ, không có biến dạng rõ rệt hoặc gây nhầm ranh giới ở mức zoom hiển thị.
- Nhãn Hoàng Sa, Trường Sa, Biển Đông đúng tiếng Việt, không mất khi phóng to/thu nhỏ, đổi giao diện hoặc sử dụng offline.
- Khác biệt nhỏ do tổng quát hóa hình học có thể chấp nhận nếu có nguồn, giải trình và người rà soát. Không yêu cầu độ trùng khớp polygon 100%, cũng không yêu cầu mọi tọa độ tên đảo/bãi nằm trong polygon hành chính.
- Phân biệt điểm địa danh, đảo/đá/bãi ngầm, đất nổi, đa giác hành chính và đường phân định biển. Không vẽ một vùng đất hoặc đường yêu sách chỉ từ điểm nhãn hay bbox.
- Không thể hiện đường yêu sách bị cấm theo quy tắc dự án hoặc nhãn quản lý hành chính nước ngoài cho Hoàng Sa/Trường Sa. Không suy diễn vùng đặc quyền kinh tế hay biên giới biển không có cơ sở.
- Có bằng chứng nguồn hợp lệ và quyền phân phối lại, kiểm tra style, tile, nhãn, zoom, chế độ sáng/tối, online/offline và ảnh Android.

## 14 vị trí cần giải trình trước khi xét duyệt

Thông tư 33/2024/TT-BTNMT có 183 địa danh điểm trong nhóm Hoàng Sa (50) và Trường Sa (133). Đã kiểm tra: 141 điểm nằm trong đa giác nguồn, 156 điểm trong hoặc cách tối đa 2 km; 14 điểm xa hơn 5 km. Con số này KHÔNG chứng minh có 14 lỗi chủ quyền; nhiều điểm có thể là bãi ngầm, đá, nhãn quần đảo hoặc sai khác tổng quát hóa.

Bốn đảo cần xem kỹ: B48 Đảo Tri Tôn, C123 Đảo An Bang, B15 Đảo Bạch Quy và B3 Đảo Quang Ảnh. Không được miễn kiểm tra chỉ vì mã ZIP thuộc tỉnh Việt Nam. Mỗi trường hợp cần ghi nhận loại đối tượng, bằng chứng và cách hiển thị thích hợp.

Việc đối chiếu theo cách trình bày của dự án không phải kết luận pháp lý quốc tế về các tranh chấp chủ quyền ở Biển Đông.

## Phân biệt nghiệm thu bản đồ và an toàn dẫn đường

| Hạng mục | Tiêu chí | Hiện tại |
| --- | --- | --- |
| Ứng viên GIS | ZIP đúng 34 tỉnh, hình học cơ bản và danh mục địa danh đã kiểm tra | Được sử dụng để phát triển/QA riêng tư |
| Hiển thị lãnh thổ trên bản đồ | Rà soát 14 ngoại lệ, nhãn, tile/style, ảnh Android, nguồn và quyền dùng | Chưa đủ điều kiện phê duyệt |
| Dẫn đường/biển báo/tốc độ | Mạng đường có hướng, hạn chế rẽ, biển báo thực địa, tốc độ theo đoạn và thời điểm, kiểm thử tuyến và GPS | Chưa được kiểm chứng |

Biển báo và tốc độ phải lấy từ dữ liệu có nguồn/phiên bản và cập nhật; khi không chắc chắn phải thể hiện chưa xác minh, không suy đoán một mức tốc độ. Luật Đường bộ 35/2024/QH15 và Luật Trật tự, an toàn giao thông đường bộ 36/2024/QH15 có hiệu lực từ 01/01/2025.

## Kiểm tra bằng mã

    python -m pipeline.map_display_acceptance --output audit-output/map-review.json

Chương trình đọc policy ở assets/manifests/map_display_acceptance_policy.json và kết quả sàng lọc 183 điểm. Nó không dùng ngưỡng polygon trùng 100%; thay vào đó liệt kê các điểm chưa có giải trình, bằng chứng nhãn, ảnh và quyền sử dụng. Có thể nhập chứng cứ đã rà soát qua --review-evidence.

Dù chứng cứ được khai là đủ, công cụ chỉ trả READY_FOR_INDEPENDENT_HUMAN_P0_REVIEW_NOT_APPROVED. Bản thân JSON tự khai không thể phê duyệt phát hành hoặc kích hoạt MapLibre. assets/geo/approved_reference.json tiếp tục pending và map_release.json tiếp tục p0_pass=false.

Giữ riêng các bước kiểm thử dẫn đường; phê duyệt lớp nền không tự chứng nhận biển báo và giới hạn tốc độ.
