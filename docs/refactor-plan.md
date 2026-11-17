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

Mốc giai đoạn 2 đã được chủ dự án kiểm tra và commit/push bằng tài khoản Windows. Các script lưu mốc từng giai đoạn được bỏ sau khi hoàn tất cải tổ; các commit vẫn giữ đầy đủ lịch sử.

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
- [x] Chủ dự án đã commit/push giai đoạn 3: `91dc438` (`gd3`); HEAD và origin/main cùng mốc khi bắt đầu giai đoạn 4.

Mốc giai đoạn 3 đã được kiểm tra giao diện và commit/push, gồm frontend mới và việc bỏ `templates/`/`static/` cũ.

## Giai đoạn 4 — MongoDB Atlas

- [x] Chủ dự án chọn MongoDB Atlas; bắt đầu từ commit sạch `91dc438`.
- [x] Sao lưu tại `.runtime/backups/snapshot-20261117T045908415609Z/` (312 số đo, 1 dòng lệnh).
- [x] Cài PyMongo 4.20.0, dnspython 2.9.2 và thư viện kiểm thử qua launcher trên máy chủ dự án.
- [x] Viết repository MongoDB, chọn backend bằng cấu hình; mặc định web vẫn dùng SQLite.
- [x] Giữ ID số/thứ tự/API/null; lưu số đo, cấp ID và xác nhận remote trong transaction.
- [x] Bổ sung kiểm tra cấu hình, lỗi 503, bảo vệ file/URI riêng và kiểm thử cùng hợp đồng API bằng mongomock.
- [x] Chuẩn bị công cụ cấu hình và kiểm tra Atlas thật trên database tạm; [hướng dẫn Atlas](mongodb-atlas.md).
- [x] Kiểm tra cuối bằng `Kiem-tra.cmd --no-pause` đạt: 66 Python + 17 JavaScript, gồm kiểm thử hồi quy tên database tạm sau lỗi giới hạn 38 byte trên Atlas; kiểm tra file đưa lên Git đạt.
- [x] Cấu hình Atlas đã lưu trong `mongodb.local.json` được Git bỏ qua; chủ dự án chạy kiểm tra Atlas thật đạt lúc 12:45 ngày 17/11/2026: 14 kiểm thử, 0 lỗi, gồm rollback transaction; không còn database tạm của lượt kiểm tra.
- [x] Mặc định web vẫn SQLite, 312 số đo; cấu hình web/database/firmware thật giữ nguyên theo SHA-256 sau sửa công cụ kiểm tra.
- [x] Chủ dự án đã commit/push giai đoạn 4: `fe50407` (`gd4`); HEAD và origin/main cùng mốc, thư mục làm việc sạch khi bắt đầu giai đoạn 5.

Chưa đổi backend đang dùng và chưa chuyển dữ liệu thật. Việc này thuộc giai đoạn 5. Kiểm thử mongomock không được ghi nhận thay cho kết quả transaction trên Atlas thật.

Kết quả Atlas đã xác nhận từ `.runtime/atlas-check.json` và `.runtime/atlas-check.log`; các file kết quả và cấu hình riêng không đưa lên Git. Mốc `fe50407` đã được xác nhận trước khi sửa tiếp.

## Giai đoạn 5 — chuyển dữ liệu và bật MongoDB

- [x] Bắt đầu từ commit sạch `fe50407`, sao lưu tại `.runtime/backups/snapshot-20261117T055041789848Z/` (312 số đo, 1 dòng lệnh).
- [x] Đọc SQLite ở chế độ chỉ đọc; giữ ID/thời gian/null/0 và sequence kể cả ID đã xóa.
- [x] Viết migration trong transaction, chạy lại không trùng, nhận bản chuyển dở khớp và dừng nếu xung đột.
- [x] Đối chiếu toàn bộ số đo/lệnh, counter, dashboard, GPS và API web trước khi đổi cấu hình.
- [x] Bổ sung sao lưu, chặn khi web đang chạy/nguồn hoặc cấu hình vừa đổi; chỉ bật MongoDB sau khi đạt.
- [x] Chuẩn bị kiểm thử Atlas tạm, launcher chuyển dữ liệu, kiểm tra backend sau chuyển và tài liệu [migration](mongodb-migration.md).
- [x] `Kiem-tra.cmd --no-pause` đạt: 84 ca Python (83 đạt, 1 rollback dành cho Atlas thật), 17 JavaScript đạt; kiểm tra 103 file dự kiến đưa lên Git đạt. SHA-256 của cấu hình web/Atlas, SQLite và firmware thật giữ nguyên; web đã dừng trước bước chuyển thật.
- [x] Chủ dự án chạy 10 kiểm thử migration trên Atlas thật, gồm rollback: 10 đạt, 0 lỗi, database tạm đã dọn; xác nhận từ `.runtime/migration-check.json`.
- [x] Chuyển đủ 312 số đo và 1 dòng lệnh vào `iot_sos`, counter 312; dashboard/GPS/API khớp, đã bật MongoDB lúc 13:04 ngày 17/11/2026. Xác nhận từ `.runtime/migration-report.json` với `ok=true`, `state=mongodb_enabled`.
- [x] Chủ dự án mở lại web và xác nhận giao diện hiển thị ổn sau khi đổi backend sang MongoDB, bổ sung model/schema và chuyển cấu hình sang `.env`.
- [x] Chủ dự án đã commit/push giai đoạn 5: `da4fb2e` (`gd5`); HEAD và origin/main cùng mốc, thư mục làm việc sạch trước khi bắt đầu giai đoạn 6.

Bổ sung theo yêu cầu trước giai đoạn 6:

- [x] Tách model Reading/DeviceCommand/ReadingCounter và dùng chung định nghĩa trường/range với validation, repository và schema.
- [x] Viết `scripts.init_db` cùng launcher để tạo collections/index/counter, đối chiếu dữ liệu cũ và gắn validators; chạy lại không xóa dữ liệu.
- [x] Cài python-dotenv 1.2.4, bổ sung `.env.example`, chuyển cấu hình riêng hiện có sang `.env`; giá trị hiệu lực của mật khẩu/khóa/URI/database khớp trước chuyển. JSON cũ, SQLite và firmware giữ nguyên SHA-256.
- [x] Kiểm tra cục bộ trước đổi cấu hình: 98 ca Python (97 đạt, 1 dành cho rollback Atlas), 17 JavaScript đạt. Đã xác nhận 312 số đo và 1 lệnh trong bản SQLite giữ lại khớp model.
- [x] Kiểm tra lại sau khi `.env` là cấu hình chính: 98 ca Python (97 đạt, 1 dành cho rollback Atlas), 17 JavaScript đạt; 118 file dự kiến đưa lên Git đạt, diff không lỗi khoảng trắng.
- [x] Chủ dự án chạy `Khoi-tao-MongoDB.cmd`: cả hai kiểm thử schema trên Atlas thật đạt, không còn database tạm; đã gắn validators cho `iot_sos`. Báo cáo xác nhận 312 readings, 1 commands, 1 counters, counter 312; dữ liệu cũ được giữ. Xác nhận từ `.runtime/db-init-report.json` và `.runtime/schema-check.json`.

Chủ dự án đã chạy `Chuyen-sang-MongoDB.cmd` thành công; bản sao lưu trước chuyển nằm tại `.runtime/backups/snapshot-20261117T060445234271Z/`. Web hiện dùng `iot_sos` trên Atlas; bản SQLite vẫn giữ lại. Giao diện đã được xác nhận ổn và giai đoạn 5 đã lưu tại `da4fb2e`.

## Giai đoạn 6 — thử thiết bị thật và hoàn thiện hướng dẫn

- [x] Bắt đầu từ commit sạch `da4fb2e`, sao lưu tại `.runtime/backups/snapshot-20261117T142643521657Z/`.
- [x] Xác nhận web đang chạy, thiết bị đã được cắm lại, COM3, khóa firmware khớp cấu hình web và tunnel mới được chuẩn bị.
- [x] Chủ dự án Upload firmware với header mới thành công; xác nhận hash và reset qua RTS.
- [x] Tạo công cụ quan sát qua API, mốc ban đầu ID 312; chỉ tính bản tin mới đúng thiết bị, không gửi số đo giả vào database ứng dụng.
- [x] Cập nhật hướng dẫn chạy theo `.env`/Atlas và viết [hướng dẫn kiểm thử thiết bị](device-verification.md).
- [x] Kiểm tra cục bộ đạt: 102 ca Python (101 đạt, 1 rollback dành cho Atlas thật), 17 JavaScript đạt; kiểm tra 123 file dự kiến đưa lên Git đạt. Các kiểm thử mới bảo đảm dữ liệu cũ và bản ghi thiết bị khác không làm báo cáo phần cứng đạt nhầm.
- [x] Quan sát 21 bản tin mới ID 313–333 từ thiết bị thật: có SOS, cảnh báo high_bpm, BPM/SpO₂, điện áp và phần trăm pin; dữ liệu được nhận qua API web.
- [x] Xác nhận vòng lệnh LOCATE → remote → NONE từ thiết bị thật; có bản ghi yêu cầu trong `.runtime/device-command-request.json` và phản hồi trong `.runtime/device-check.json`.
- [ ] GPS ngoài trời và vị trí/lịch sử GPS mới: chủ dự án chủ động hẹn thử sau vì đang ở trong phòng. Được ghi riêng là deferred, không ngăn chốt phạm vi thử trong phòng và không được ghi là đã có GPS fix.
- [x] Chủ dự án dừng/mở lại web, đăng nhập và xác nhận sự kiện SOS vừa thử cùng lịch sử cũ vẫn đầy đủ; API sau mở lại tiếp tục nhận bản tin mới.
- [x] Báo cáo thử trong phòng đạt theo phạm vi chủ dự án chấp nhận: `.runtime/device-check.json`, scope `indoor_gps_deferred`, 28 bản tin mới ID 313–340, SOS ID 319, remote ID 328, lệnh chờ NONE. Cờ GPS fix vẫn false.
- [x] Kiểm tra cuối đạt: 103 ca Python (102 đạt, 1 rollback dành cho Atlas thật), 17 JavaScript đạt; kiểm tra 123 file dự kiến đưa lên Git đạt.
- [x] Chủ dự án đã commit/push giai đoạn 6: `d6d42df` (`gd6`); HEAD và origin/main cùng mốc, thư mục làm việc sạch trước lượt dọn dẹp. GPS ngoài trời vẫn được hẹn thử riêng sau.

## Dọn dẹp sau cải tổ

- Bỏ các script commit/push một lần của sáu giai đoạn và hướng dẫn gốc đã được thay thế.
- Cài thư viện web bằng `Cai-dat.cmd`; thư viện kiểm thử bổ sung bằng `Cai-thu-vien-kiem-thu.cmd`. Installer riêng cho dotenv được bỏ vì đã có trong requirements chính.
- Dọn bytecode, kết quả biên dịch, log cài đặt/kiểm thử cũ và thư mục fixture còn sót. Giữ báo cáo xác minh có ích, cấu hình riêng, dữ liệu, Cloudflare và các bản sao lưu.

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

## Phần còn hẹn thử

- Thử trong phòng đã đạt và giai đoạn 6 đã lưu tại `d6d42df`.
- Chủ dự án sẽ thử GPS ngoài trời sau; phần đó còn được ghi là chưa xác nhận.

Mỗi giai đoạn kết thúc bằng cập nhật file này, kết quả kiểm tra và commit riêng. Ghi rõ phần chưa hoàn thành để tiếp tục ở phiên sau.
