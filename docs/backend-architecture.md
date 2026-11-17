# Backend sau giai đoạn 2

Tài liệu dưới ghi lại bước tách backend ban đầu. Bản hiện tại đã có repository MongoDB, model/schema và `.env`; xem [MongoDB Atlas](mongodb-atlas.md) và [model/cấu hình](models-and-configuration.md). Phần Lịch sử bổ sung `alerts.py` dùng chung, `repositories/indexes.py` quản lý index, `alert_page(snapshot, before, after)` cho cả hai repository và `dashboard_snapshot(compact=True)` cho Trang chủ. API mới: `/api/dashboard`, `/api/alerts`, trang HTML `/history`; API thiết bị giữ nguyên. Xem [thiết kế lịch sử](alert-history.md).

## Cấu trúc

```text
app.py                         Điểm vào tương thích: python app.py
run_local.py                   Launcher Windows, mở trình duyệt và đọc cấu hình đã lưu
project_config.py              Cấu hình riêng dùng chung với công cụ chuẩn bị firmware
backend/
  app/
    __init__.py                create_app(config): tạo ứng dụng độc lập
    config.py                  Cấu hình runtime và đường dẫn database
    auth.py                    Xác thực session, khóa thiết bị và mật khẩu
    validation.py              Kiểm tra dữ liệu đầu vào, không phụ thuộc Flask/SQLite
    routes/
      web.py                   Trang đăng nhập, đăng xuất và dashboard HTML
      device.py                API telemetry/command cho ESP32
      dashboard.py             API status/track/command cho trình duyệt
    services/
      monitoring.py            Số đo, thời điểm nhận, trạng thái và lệnh định vị
    repositories/
      sqlite.py                Toàn bộ SQL, schema và transaction
```

Luồng xử lý là route → service → repository. Route đọc HTTP và trả phản hồi; service kiểm tra dữ liệu và điều phối xử lý; repository đọc/ghi SQLite. Các thuật toán firmware và frontend chưa thay đổi ở giai đoạn này.

## Khởi tạo và cấu hình

`backend.app.create_app(config)` tạo một ứng dụng mới. Import package backend không tự mở database. Mỗi ứng dụng có repository/service riêng trong `app.extensions`; không dùng biến database hoặc khóa toàn cục giữa các ứng dụng.

- Khóa/mật khẩu: cấu hình truyền trực tiếp → biến môi trường → `config.local.json`.
- Khi truyền đủ ba trường `ADMIN_PASSWORD`, `DEVICE_KEY`, `SESSION_SECRET`, factory không đọc hoặc tạo cấu hình riêng trên máy. Kiểm thử dùng cách này.
- `SECRET_KEY` của Flask lấy từ `SESSION_SECRET`.
- `DB_PATH`: cấu hình truyền trực tiếp → biến môi trường `DB_PATH` → `iot_ngoc.sqlite3` ở thư mục gốc dự án.
- Đường dẫn tương đối được tính từ thư mục dự án. Dùng file SQLite tạm khi kiểm thử; `:memory:` không được hỗ trợ vì repository mở/đóng kết nối theo thao tác.
- `Chay-web.cmd` tiếp tục dùng cấu hình và database đã có; `run_local.py` truyền chúng vào factory.

`app.py` được giữ như điểm vào tương thích và vẫn cung cấp `app` cho WSGI. Phần triển khai chính nằm trong package backend.

## Giao diện và API

Factory dùng đường dẫn tuyệt đối đến `frontend/templates/` và `frontend/static/` sau giai đoạn 3. URL `/static/...` vẫn được giữ, các thành phần frontend nằm ở thư mục riêng. Xem [cấu trúc frontend](frontend-architecture.md).

Các Blueprint đổi cách tổ chức mã, giữ nguyên URL, phương thức HTTP, JSON và phản hồi văn bản NONE/LOCATE. Xem [hợp đồng API](api-contract.md).

Thay đổi lỗi đầu vào có chủ đích trong giai đoạn 2:

- JSON list/string/number/null hoặc JSON hỏng ở API command trả 400 thay vì có thể gây 500.
- `event` là list/object trả 400 `bad event` thay vì 500.
- Số nguyên quá lớn để chuyển thành float trả 400 thay vì 500.
- Mật khẩu chứa tiếng Việt được so sánh bằng UTF-8, tránh lỗi kiểu dữ liệu trong so sánh constant-time.

## Truy cập dữ liệu và chuẩn bị MongoDB

`SQLiteRepository` hiện cung cấp các thao tác:

- `initialize()`
- `save_reading(reading, timestamp)`
- `pending_command(device_id)`
- `queue_locate(device_id)`
- `dashboard_snapshot()`
- `track_points(device_id, since)`

Lưu bản tin `remote` và đưa lệnh về NONE tiếp tục nằm trong cùng transaction. Đọc lệnh không xóa lệnh. Schema, chỉ mục, giới hạn lịch sử và thứ tự ID giữ nguyên.

MongoDB sẽ có triển khai truy cập dữ liệu riêng ở giai đoạn 4; route và service không cần biết câu lệnh SQL hoặc cách kết nối MongoDB. Chưa thêm thư viện hay dịch vụ database mới trong giai đoạn 2.

## Kiểm thử

Chạy `Kiem-tra.cmd`. Các kiểm thử API từ giai đoạn 1 được giữ nguyên phần xác nhận hành vi; chỉ chuyển phần khởi tạo sang factory và fixture sang repository SQLite.

Kiểm thử bổ sung kiểm tra cách ly database/khóa/session giữa hai ứng dụng, mapping URL, tài nguyên giao diện từ thư mục làm việc khác, các dạng JSON bất thường và cả hai điểm vào chạy web. Các điểm vào dùng factory thật với cấu hình/database tạm; bước mở HTTP server được thay thế trong kiểm thử launcher để không chiếm cổng 5000 đang dùng.
