# Kế hoạch cải tổ IoT SOS

Ngày ghi nhận: 17/11/2026. Mốc trước cải tổ: `1fc3c32`.

## Giai đoạn 1 — chốt bản hoạt động

- [x] Xác nhận commit đầu và thư mục làm việc sạch trước khi sửa.
- [x] Sao lưu mã, cấu hình và SQLite; integrity đạt, 312 số đo tại mốc sao lưu.
- [x] Ghi nhận 13 kiểm thử HTTP trên bản cũ trước khi thay cấu hình.
- [x] Tách mật khẩu/khóa ra cấu hình local; giữ giá trị đang dùng trên máy.
- [x] Tạo header firmware local và cập nhật công cụ kết nối; giữ ID/khóa/URL hiện tại.
- [x] Bổ sung kiểm thử cấu hình, sao lưu và kiểm tra file trước khi đưa vào Git.
- [x] Viết hợp đồng API, hướng dẫn chạy, sao lưu và khôi phục.
- [x] Chạy xác minh cuối cùng: 24 kiểm thử đạt; firmware host tests và biên dịch object ESP32 đạt; kiểm tra file đưa lên Git đạt.
- [ ] Lưu commit/tag giai đoạn 1; đồng bộ GitHub khi kết nối cho phép.

Phần mã và kiểm tra đã sẵn sàng. Môi trường agent chỉ được đọc metadata `.git`, nên lệnh stage bị chặn ở `index.lock`; HTTPS tới GitHub cũng bị chặn. Chủ dự án chạy `Chot-giai-doan-1.cmd` bằng tài khoản Windows bình thường để kiểm tra lại, stage đúng các file giai đoạn 1, kiểm tra index, commit và push. Script dừng nếu kiểm tra lỗi; nếu commit đã có mà push lỗi, có thể chạy lại để tiếp tục push.

## Lộ trình tiếp theo

| Giai đoạn | Công việc | Điều kiện hoàn thành |
|---|---|---|
| 2 | Tách Flask thành khởi tạo ứng dụng, cấu hình, xác thực, routes, services và repositories; tiếp tục SQLite | Các kiểm thử API hiện có đạt; launcher vẫn chạy được |
| 3 | Tách frontend thành gọi API, số đo, cảnh báo, bản đồ và lịch sử | Giao diện và hành vi sử dụng được kiểm tra lại |
| 4 | Chọn MongoDB local/cloud, thiết kế dữ liệu/index và viết repository MongoDB trên database thử | Các kiểm thử nghiệp vụ đạt với MongoDB |
| 5 | Viết công cụ chuyển SQLite → MongoDB, giữ ID/thời gian/null, có đối chiếu và chống trùng | Chuyển thử thành công, chạy lại không nhân bản dữ liệu |
| 6 | Thử với ESP32 thật, cập nhật launcher/hướng dẫn và chốt bản mới | SOS, số đo, lệnh định vị và lịch sử hoạt động xuyên suốt |

Firmware sẽ được chia module trong một đợt riêng sau khi web/database ổn định. Giai đoạn 1 chỉ thay cách cấp cấu hình firmware.

## Các quyết định đã chốt

- Giữ Flask; chưa thêm Node.js hoặc framework frontend trong giai đoạn 1.
- Giữ URL API, dạng JSON, đơn vị và phản hồi văn bản NONE/LOCATE cho ESP32.
- Tiếp tục sử dụng database thật hiện tại đến giai đoạn chuyển dữ liệu.
- Cấu hình thực tế và database không theo dõi trong Git; mẫu cấu hình được theo dõi.
- Kiểm thử phần mềm dùng dữ liệu tạm, không tạo số đo giả trong database đang dùng.
- Chủ dự án đã tự push commit đầu và chấp nhận giữ lịch sử đó; không tự viết lại lịch sử hay đổi khóa.

## Kết quả xác minh giai đoạn 1

- `Kiem-tra.cmd --no-pause`: đạt; 24 kiểm thử API/cấu hình/sao lưu/kiểm tra repository.
- `tests/check_firmware.py`: kiểm thử URL, UART chia nhỏ, hàng đợi, chờ modem và bảng pin đạt; biên dịch object ESP32 đạt.
- SHA-256 của `config.local.json` và `iot_ngoc.sqlite3` giống trước cải tổ; database integrity đạt, 312 số đo.
- ID/khóa/URL firmware trong header local giống trước cải tổ. Tất cả dòng firmware khác giữ nguyên so với snapshot.
- Chưa thử lại trên phần cứng sau thay đổi cách cấp cấu hình; phần thử thiết bị nằm ở giai đoạn 6.
- Kết nối HTTPS tới GitHub từ môi trường thực thi hiện bị chặn; cần xác nhận riêng việc đồng bộ remote.

## Điểm cần xử lý ở giai đoạn 2

- Tạo `create_app()` và cho kiểm thử truyền cấu hình/database trực tiếp.
- Tách validation, xử lý đầy đủ các kiểu JSON bất thường đã ghi trong tài liệu API.
- Giữ repository SQLite sau lớp truy cập riêng để chuẩn bị MongoDB.
- Tách nhóm API thiết bị, API dashboard và trang đăng nhập.
- Di chuyển file theo từng phần, kiểm tra lại các launcher và đường dẫn template/static.

Mỗi giai đoạn kết thúc bằng cập nhật file này, kết quả kiểm tra và commit riêng. Ghi rõ phần chưa hoàn thành để tiếp tục ở phiên sau.
