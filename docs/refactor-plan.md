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
- [x] Chủ dự án đã lưu và push giai đoạn 1: commit `2c201da` (`gd1`); HEAD và origin/main cùng mốc khi bắt đầu giai đoạn 2.

Môi trường agent chỉ đọc metadata `.git`; chủ dự án trực tiếp commit/push bằng tài khoản Windows. Việc đồng bộ giai đoạn 1 đã được xác nhận trước khi sửa tiếp.

## Giai đoạn 2 — tách backend

- [x] Bắt đầu từ commit sạch `2c201da`, sao lưu tại `.runtime/backups/snapshot-20261117T010919145734Z/` (312 số đo, 1 dòng lệnh).
- [x] Tạo factory `create_app(config)` với cấu hình và repository/service riêng cho từng ứng dụng.
- [x] Tách routes web/device/dashboard, xác thực, validation, service và repository SQLite.
- [x] Giữ điểm vào `app.py`, cập nhật launcher dùng factory, giữ đường dẫn template/static hiện tại.
- [x] Các kiểm thử API cũ đạt; bổ sung kiểm thử cách ly ứng dụng, các dạng JSON bất thường và điểm vào chạy web.
- [x] Viết [tài liệu backend](backend-architecture.md) và cập nhật các thay đổi lỗi đầu vào trong hợp đồng API.
- [x] Hoàn tất xác minh cuối: 33 kiểm thử đạt; HTTP thực tế trên database tạm đạt; dữ liệu/cấu hình/firmware/frontend thật không đổi; diff và file đưa lên Git đạt.
- [x] Chủ dự án đã commit/push giai đoạn 2: `c13533c` (`gd2`); HEAD và origin/main cùng mốc khi bắt đầu giai đoạn 3.

Chạy `Chot-giai-doan-2.cmd` bằng tài khoản Windows của chủ dự án để kiểm tra lại, stage đúng các file backend/launcher/kiểm thử/tài liệu, kiểm tra index rồi commit/push. Môi trường agent vẫn chỉ đọc metadata Git; công cụ giai đoạn 1 dành cho mốc cũ.

Kết quả giai đoạn 2: 33 kiểm thử tự động đạt; kiểm tra HTTP thực tế đã xác minh login, SOS, status, LOCATE, bản tin remote và GPS history trên database tạm ở cổng riêng. Server tạm đã dừng. SHA-256 của cấu hình, database, firmware và frontend thật giống trước giai đoạn này; database integrity đạt, 312 số đo.

## Giai đoạn 3 — tách frontend

- [x] Bắt đầu từ commit sạch `c13533c`, sao lưu tại `.runtime/backups/snapshot-20261117T022432738642Z/` (312 số đo, 1 dòng lệnh).
- [x] Chuyển HTML/CSS/JavaScript vào `frontend/`, dùng Jinja base template và ES module trực tiếp trên trình duyệt.
- [x] Tách API, số đo/polling, cảnh báo, vị trí GPS, bản đồ, lịch sử và định dạng dữ liệu.
- [x] Cập nhật đường dẫn tài nguyên của factory; giữ loader tương thích cho URL tài nguyên cũ.
- [x] 36 kiểm thử Python và 17 kiểm thử JavaScript đạt; DOM render khớp bản trước và CSS chỉ đổi định dạng.
- [x] Xử lý polling trùng, lịch sử GPS chậm và phản hồi cũ đến muộn; có kiểm thử hồi quy.
- [x] Cấu hình, database và firmware thật giữ nguyên so với trước giai đoạn này.
- [x] Chủ dự án đã mở lại web, đăng nhập và xác nhận giao diện hiển thị bình thường trên trình duyệt thật. Kiểm tra ảnh tự động bằng Chrome headless bị giới hạn do GPU/process access trong môi trường thử.
- [x] Hoàn tất rà soát cuối: `Kiem-tra.cmd` đạt 36 Python + 17 JavaScript, kiểm tra file đưa lên Git/diff đạt; sao lưu bản mới tại `.runtime/backups/snapshot-20261117T024007321381Z/`.
- [ ] Chủ dự án commit/push giai đoạn 3.

Sau khi xem giao diện bình thường bằng `Chay-web.cmd`, chạy `Chot-giai-doan-3.cmd` để kiểm tra lại và commit/push. Script stage thư mục frontend mới và các file đã đổi, đồng thời stage việc xóa `templates/` và `static/` cũ; có thể chạy lại nếu commit thành công nhưng push chưa xong.

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

## Tiếp theo: giai đoạn 4

- Chọn MongoDB local hoặc cloud theo môi trường chủ dự án muốn vận hành.
- Thiết kế collection/index và repository MongoDB với cùng hợp đồng dữ liệu hiện tại.
- Chạy trên database thử; dữ liệu thật SQLite chỉ chuyển ở giai đoạn 5.

Mỗi giai đoạn kết thúc bằng cập nhật file này, kết quả kiểm tra và commit riêng. Ghi rõ phần chưa hoàn thành để tiếp tục ở phiên sau.
