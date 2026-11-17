# IoT SOS — Ngọc

Hệ thống thử nghiệm ESP32 gửi SOS, nhịp tim, SpO₂, điện áp/phần trăm pin và GPS qua 4G đến dashboard Flask.

## Chạy trên Windows

Dự án hiện dùng Python 3.11 trở lên, đã kiểm tra trên Python 3.12.14.

1. Lần đầu, chạy `Cai-dat.cmd` để tạo môi trường Python và cài thư viện.
2. Chạy `Chay-web.cmd`. Mở `http://127.0.0.1:5000`, dùng mật khẩu hiển thị trong cửa sổ chạy web.
3. Khi cần kết nối thiết bị thật, chạy thêm `Ket-noi-thiet-bi.cmd`.
4. Script tạo `firmware/ESP32_Firmware/device_config.local.h` với địa chỉ tunnel và khóa khớp với web.
5. Mở `firmware/ESP32_Firmware/ESP32_Firmware.ino` bằng Arduino IDE, chọn ESP32 Dev Module/cổng USB thực tế rồi Upload.

Giữ cửa sổ web và tunnel mở khi sử dụng. Quick Tunnel có thể đổi địa chỉ sau mỗi lần mở; cần chuẩn bị và nạp lại firmware khi địa chỉ đổi. Hướng dẫn chi tiết: [Huong-dan-chay-web.md](Huong-dan-chay-web.md).

## Cấu hình và dữ liệu trên máy

- `config.local.json`: được tạo tự động ở lần chạy đầu, giữ mật khẩu web, khóa thiết bị và khóa phiên. Bản đã có được giữ nguyên.
- `config.example.json`: mô tả các trường cấu hình; các giá trị trống chỉ là mẫu, không thay cho file cấu hình đang dùng.
- `device_config.local.h`: cấu hình thực tế để biên dịch ESP32, do script kết nối tạo; được Git bỏ qua.
- `device_config.example.h`: ví dụ để đọc cấu trúc, không cần sửa để chạy bộ launcher.
- `mongodb.local.json`: kết nối Atlas riêng trên máy, được Git bỏ qua.
- `.env`: cấu hình chính sau khi chạy `python -m scripts.configure_env`; giữ nguyên mật khẩu/khóa/database từ cấu hình cũ và được Git bỏ qua. `.env.example` là mẫu.
- `iot_ngoc.sqlite3`: dữ liệu SQLite ban đầu; được giữ lại sau khi chuyển sang Atlas.
- `.runtime/backups/`: bản sao lưu riêng trên máy, có cả cấu hình và dữ liệu; được Git bỏ qua.

Web và tunnel lấy cấu hình theo thứ tự biến môi trường, `.env`, rồi JSON cũ cho các giá trị còn thiếu. Mã nguồn hiện tại không chứa khóa thực tế; lịch sử commit cũ được giữ nguyên theo lựa chọn của chủ dự án. Xem [model, schema và cấu hình](docs/models-and-configuration.md).

Khởi tạo collections/index/validators bằng `.venv\Scripts\python.exe -m scripts.init_db` hoặc `Khoi-tao-MongoDB.cmd`; không phải chạy lại migration dữ liệu.

## Kiểm tra và sao lưu

Lần đầu chạy bộ kiểm thử, dùng `Cai-thu-vien-kiem-thu.cmd` để cài các gói trong `requirements-test.txt`. Sau đó chạy `Kiem-tra.cmd` để kiểm tra API, cấu hình, công cụ sao lưu và các file dự kiến đưa lên Git. `Cai-dat.cmd` cài các thư viện cần cho web, gồm Flask, PyMongo và python-dotenv.

Các lệnh tương đương từ PowerShell tại thư mục dự án:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.venv\Scripts\python.exe scripts\check_repository.py
.venv\Scripts\python.exe scripts\backup_project.py
```

Các kiểm thử dùng SQLite và cấu hình tạm trong `.runtime`, không gửi dữ liệu giả vào database đang dùng. Kiểm tra firmware trên máy đã có g++ và bộ công cụ ESP32/Arduino:

```powershell
.venv\Scripts\python.exe tests\check_firmware.py
```

Lệnh firmware chạy kiểm thử trên máy tính và biên dịch ra object ESP32; không nạp thiết bị. Thử với phần cứng thật là bước riêng.

Từ giai đoạn 3, `Kiem-tra.cmd` chạy thêm kiểm thử JavaScript bằng Node.js có sẵn trên máy. Không có thư viện npm cần cài. Node.js phục vụ kiểm thử; chạy web vẫn chỉ cần Python và các thư viện trong `requirements.txt`.

Kết nối Atlas được cấu hình bằng `Tao-cau-hinh-MongoDB.cmd`, kiểm tra thật bằng `Kiem-tra-MongoDB.cmd`. Nếu còn dùng SQLite và cần chuyển dữ liệu, dừng web/thiết bị rồi chạy `Chuyen-sang-MongoDB.cmd`; xem [hướng dẫn chuyển dữ liệu](docs/mongodb-migration.md). Máy này đã chuyển thành công sang Atlas.

## Tài liệu cải tổ

- [Tiến độ và các giai đoạn](docs/refactor-plan.md)
- [Hợp đồng API đang dùng](docs/api-contract.md)
- [Mốc trước cải tổ và khôi phục](docs/baseline.md)
- [Cấu trúc backend sau giai đoạn 2](docs/backend-architecture.md)
- [Cấu trúc frontend sau giai đoạn 3](docs/frontend-architecture.md)
- [MongoDB Atlas và cách kiểm tra kết nối](docs/mongodb-atlas.md)
- [Chuyển dữ liệu và bật MongoDB cho web](docs/mongodb-migration.md)
- [Model, lệnh init-db và cấu hình .env](docs/models-and-configuration.md)
- [Thử thiết bị thật và đối chiếu dữ liệu mới](docs/device-verification.md)

Backend nằm trong `backend/app/`, frontend trong `frontend/`, firmware chính trong `firmware/ESP32_Firmware/`. `app.py` giữ điểm vào chạy Python tương thích; cấu hình chính của máy này là `.env`, database là MongoDB Atlas. Các sketch chẩn đoán cảm biến trong `firmware/` được giữ để xử lý lỗi phần cứng.

Sáu giai đoạn cải tổ đã được lưu trên Git, mốc cuối là `d6d42df`. Các script commit/push riêng từng giai đoạn đã được bỏ sau khi hoàn tất; dùng Git hoặc Source Control của VS Code để lưu thay đổi tiếp theo. Lượt thử trong phòng đã đạt, GPS ngoài trời được chủ dự án hẹn thử sau. Chi tiết ở `docs/refactor-plan.md`.
