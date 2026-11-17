# MongoDB Atlas — giai đoạn 4

## Trạng thái và phạm vi

Web đang dùng SQLite như trước. Giai đoạn 4 bổ sung repository MongoDB và kiểm tra trên database tạm; dữ liệu thật được chuyển ở giai đoạn 5. Driver Python đã được cài bằng `Cai-thu-vien-MongoDB.cmd`.

Đã xác nhận kết nối Atlas thật ngày 17/11/2026: 14 kiểm thử đạt, gồm hợp đồng API và rollback transaction; các database thử của lượt kiểm tra đã được dọn sạch. Kết quả chi tiết lưu trên máy trong `.runtime/atlas-check.json` và `.runtime/atlas-check.log`.

## 1. Chuẩn bị Atlas

Nếu đã có cluster phù hợp, dùng cluster đó và chuyển đến phần kết nối. Nếu chưa có, đăng nhập [MongoDB Atlas](https://cloud.mongodb.com), chọn hoặc tạo project, tạo cluster và chọn **Free / M0**. Đây là loại cluster dành cho phát triển/thử nghiệm theo [hướng dẫn tạo Free cluster](https://www.mongodb.com/docs/atlas/tutorial/deploy-free-tier-cluster/).

Tạo **database user** cho ứng dụng. Tài khoản này khác tài khoản đăng nhập website Atlas. Lượt kiểm tra cần quyền đọc/ghi và tạo/xóa collection trong các database thử do công cụ tự sinh; có thể dùng quyền `readWriteAnyDatabase` trong project thử nghiệm của bạn. Xem [database users](https://www.mongodb.com/docs/atlas/security-add-mongodb-users/).

Trong **Network Access**, thêm địa chỉ IP hiện tại của máy chạy web, thường qua nút **Add Current IP Address**. Atlas chỉ chấp nhận kết nối từ IP được cho phép; nếu mạng gia đình đổi IP cần cập nhật lại. Xem [IP Access List](https://www.mongodb.com/docs/atlas/security/ip-access-list/).

## 2. Lưu chuỗi kết nối trên máy

1. Trong cluster, chọn **Connect → Drivers**, chọn Python và sao chép chuỗi `mongodb+srv://...` do Atlas cung cấp.
2. Bấm đúp `Tao-cau-hinh-MongoDB.cmd` trong dự án.
3. Dán URI vào cửa sổ. Nội dung được ẩn khi nhập/dán; bạn vẫn có thể dùng Ctrl+V rồi Enter.
4. Nếu URI có `<db_password>`, công cụ hỏi mật khẩu database user và tự mã hóa ký tự đặc biệt. Nếu có placeholder username, công cụ hỏi thêm username.
5. Tên database ứng dụng có thể để mặc định `iot_sos`.

Cấu hình được lưu ở `mongodb.local.json`, được Git bỏ qua. File `mongodb.example.json` chỉ mô tả cấu trúc. Cấu hình cũ được sao lưu trước khi ghi lại. Công cụ cấu hình không đổi backend mà web đang dùng.

## 3. Kiểm tra Atlas thật

Bấm đúp `Kiem-tra-MongoDB.cmd`.

Công cụ chạy 13 kiểm thử API hiện có và một kiểm thử rollback transaction. Nó tạo database riêng dạng `sosv_<mã-ngẫu-nhiên>_<số>`, với tên ngắn hơn giới hạn 38 byte của Atlas, dùng số đo giả và thông tin đăng nhập thử. Sau mỗi ca, chỉ xóa ba collection do chính lượt thử tạo trong database đó. Database ứng dụng đã chọn và file SQLite thật không được dùng để ghi số đo thử.

Thành công hiển thị **ATLAS KIEM TRA DAT**. Kết quả kỹ thuật nằm ở:

- `.runtime/atlas-check.log`: tiến độ và kết quả kiểm thử.
- `.runtime/atlas-check.json`: kết quả tổng hợp, không ghi URI/mật khẩu.

Các database thử được dọn sau kiểm tra; database ứng dụng `iot_sos` sẽ nhận dữ liệu thật ở giai đoạn 5. Chuỗi Atlas chỉ dùng ở backend; ESP32 tiếp tục gửi HTTPS về web Flask như trước.

Nếu lỗi, kiểm tra cluster đã sẵn sàng, IP máy đã được cho phép, mật khẩu là của database user và quyền đọc/ghi đúng. Công cụ không tắt kiểm tra TLS khi kết nối lỗi.

Khi sẵn sàng chốt giai đoạn 4, có thể chạy `Chot-giai-doan-4.cmd`. File sẽ chạy kiểm tra cục bộ và Atlas, rồi commit/push sau khi đạt. Nếu kiểm tra riêng đã đạt nhưng muốn tránh chạy lặp, bạn có thể tự commit/push các thay đổi qua Git như các giai đoạn trước.

## Thiết kế lưu trữ

| Collection | Khóa/chức năng |
|---|---|
| `readings` | `_id` là ID số tăng dần; API xuất thành `id`, giữ Unix giây, đơn vị và null như SQLite |
| `commands` | `_id` là device_id; `cmd` là LOCATE/NONE |
| `counters` | Một dòng `_id=readings`, giữ số ID mới nhất |

Repository dùng collection thông thường để giữ ID và transaction hiện có. `_id` có chỉ mục duy nhất; thêm chỉ mục `(device_id, ts)` và `(device_id, _id giảm dần)` cho truy vấn lịch sử/thứ tự.

Lưu số đo, cấp ID và xác nhận lệnh remote nằm trong cùng transaction. Atlas dùng replica set hỗ trợ transaction; repository từ chối máy chủ standalone thiếu hỗ trợ này. API tiếp tục trả NONE/LOCATE dưới dạng plain text và giữ schema JSON hiện tại. Lỗi lưu trữ trả HTTP 503 `database unavailable`, không đưa chuỗi kết nối vào phản hồi. Xem [PyMongo transactions](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/crud/transactions/).

Kết nối được dùng chung theo vòng đời ứng dụng với pool giới hạn; không đóng client sau từng HTTP request. Luồng ghi có giới hạn thời gian tổng thể 10 giây qua PyMongo timeout context.

## Cấu hình backend sau khi chuyển dữ liệu

Giai đoạn 4 chưa bật các giá trị này cho web đang dùng. Factory đã hỗ trợ:

- `DATABASE_BACKEND`: `sqlite` (mặc định) hoặc `mongodb`.
- `MONGODB_URI`, `MONGODB_DATABASE`, `MONGODB_TIMEOUT_MS`: truyền trực tiếp, qua biến môi trường, hoặc đọc từ `mongodb.local.json` khi chọn MongoDB.
- Cấu hình truyền trực tiếp có ưu tiên cao hơn biến môi trường, sau đó đến cấu hình riêng trên máy.

Khi MongoDB được chọn mà thiếu driver/cấu hình/kết nối hợp lệ, ứng dụng báo lỗi; không âm thầm chuyển sang database khác. Việc chuyển dữ liệu và bật backend mới được thực hiện ở giai đoạn 5.

## Giới hạn kiểm thử mô phỏng

`Kiem-tra.cmd` chạy cả hợp đồng API bằng mongomock để kiểm tra truy vấn, ID, null/0, giới hạn lịch sử và lệnh. Mongomock không triển khai session/transaction, nên kiểm thử rollback và kết nối thực tế phải chạy bằng `Kiem-tra-MongoDB.cmd` trên Atlas thật trước khi chốt giai đoạn 4.
