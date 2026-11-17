# Model, schema và cấu hình

## Các model

Các model dùng dataclass Python, nằm trong `backend/app/models/`. PyMongo tiếp tục đảm nhiệm kết nối và transaction.

Đã xác nhận khởi tạo trên Atlas thật ngày 17/11/2026: hai kiểm thử schema đạt; `iot_sos` giữ đủ 312 số đo, 1 lệnh và 1 bộ đếm tại mốc khởi tạo.

| Model | Collection | Nội dung |
|---|---|---|
| `Reading` | `readings` | ID số nguyên, device_id, Unix timestamp, event, GPS và số đo |
| `DeviceCommand` | `commands` | Một lệnh NONE/LOCATE trên mỗi thiết bị |
| `ReadingCounter` | `counters` | Bộ đếm ID số đo tăng dần |

`Reading` có các phương thức chuyển từ document MongoDB sang model, xuất document và xuất JSON cho API. API tiếp tục dùng `id`; MongoDB tiếp tục dùng `_id` số nguyên đã chuyển từ SQLite. Các giá trị null và số 0 vẫn khác nhau.

Các sự kiện hợp lệ và khoảng giá trị nằm cùng model Reading. Validation HTTP sử dụng các định nghĩa này; repository dùng model khi ghi và đọc dữ liệu. Model cũng cung cấp JSON Schema cho MongoDB.

## Một lệnh khởi tạo database

Trong PowerShell tại thư mục dự án:

```powershell
.venv\Scripts\python.exe -m scripts.init_db
```

Hoặc bấm đúp `Khoi-tao-MongoDB.cmd`. Dừng web trước khi chạy.

Lệnh đọc cấu hình hiện tại, chạy hai kiểm thử schema trên database Atlas tạm, rồi khởi tạo database đã chọn. Nó tạo rõ cả ba collections, index phục vụ truy vấn và counter ban đầu. Với collections đã có, nó kiểm tra toàn bộ document trước khi gắn validator `strict/error`; dữ liệu sai sẽ làm lệnh dừng để kiểm tra, không tự sửa số đo.

Chạy lại giữ nguyên số đo, lệnh và các ID; counter không giảm. Validator khác đang tồn tại sẽ được giữ và báo cần migration schema riêng. Lệnh không xóa database/collection ứng dụng.

Gắn validator vào collection cũ dùng `collMod`, cần quyền `dbAdmin` trên database ứng dụng (ví dụ `iot_sos`) ngoài quyền đọc/ghi. Nếu Atlas báo mã 13, bổ sung role này cho database user trong Database Access rồi chạy lại. Web chạy bình thường không tự thay đổi validators. Tham khảo [MongoDB collMod](https://www.mongodb.com/docs/manual/reference/command/collmod/).

Chỉ kiểm tra schema/index/data hiện có, không ghi database:

```powershell
.venv\Scripts\python.exe -m scripts.init_db --check
```

Kết quả lưu trong `.runtime/db-init-report.json`, log ở `.runtime/db-init.log`. Kết quả hai kiểm thử Atlas tạm lưu riêng trong `.runtime/schema-check.json`. Metadata trước thay đổi lưu dưới `.runtime/db-schema-before-*.json`.

Kiểm thử cục bộ kiểm tra model và trình tự khởi tạo. Quy tắc JSON Schema được kiểm tra bằng MongoDB thật: chấp nhận số 0/null, chặn sự kiện lạ, giá trị ngoài khoảng, boolean thay số và tọa độ thiếu một vế. Số đo thử chỉ ghi vào database tạm có tên riêng.

## File .env

`.env` là cấu hình chính trên máy sau khi chuyển. `.env.example` là mẫu đưa lên Git; `.env` và các bản tạm được Git bỏ qua.

Chuyển cấu hình JSON hiện có sang `.env`, giữ nguyên khóa/mật khẩu/database:

```powershell
.venv\Scripts\python.exe -m scripts.configure_env
```

Công cụ sao lưu trước khi tạo. Nếu `.env` đã có, nó giữ nguyên file để bảo toàn chỉnh sửa. Các file JSON cũ vẫn được giữ làm cấu hình tương thích; không đồng bộ hai chiều.

Thứ tự ưu tiên:

1. Cấu hình truyền trực tiếp vào factory.
2. Biến môi trường của tiến trình Windows/server.
3. File `.env` trong thư mục dự án.
4. File JSON cũ cho các giá trị còn thiếu.

Nếu server đã cấp đầy đủ ba khóa đăng nhập qua biến môi trường, cấu hình ứng dụng không đọc `.env`/JSON trên máy. Các kiểm thử cung cấp cấu hình trực tiếp để cách ly dữ liệu thật.

`python-dotenv` đọc file mà không thay đổi `os.environ`. Nội dung `${...}` trong mật khẩu được coi là ký tự literal, không nội suy biến. Web, công cụ tunnel và các lệnh MongoDB dùng cùng cách đọc cấu hình.

Các trường thường dùng: `ADMIN_PASSWORD`, `DEVICE_KEY`, `SESSION_SECRET`, `DEVICE_ID`, `DATABASE_BACKEND`, `MONGODB_URI`, `MONGODB_DATABASE`, `MONGODB_TIMEOUT_MS`. `DB_PATH` có thể đặt khi dùng SQLite.

Sau khi có `.env`, công cụ cấu hình MongoDB cập nhật file này; công cụ chuyển dữ liệu cũng cập nhật backend trong `.env`. Cấu hình riêng và URI không được in vào báo cáo hoặc đưa lên Git.
