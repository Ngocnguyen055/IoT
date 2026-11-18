# IoT SOS — Ngọc

Hệ thống thử nghiệm ESP32 gửi SOS, nhịp tim, SpO₂, điện áp/phần trăm pin và GPS qua 4G đến dashboard Flask.

Thanh điều hướng có **Trang chủ** (số đo trực tiếp và 8 sự kiện mới nhất) và **Lịch sử** (20 sự kiện mỗi trang, nút Trước/Sau). Lịch sử gồm SOS, cảnh báo nhịp tim/SpO₂ và phản hồi định vị; không liệt kê các bản tin định kỳ. Chọn **Về mới nhất** để cập nhật sự kiện mới khi đang xem lịch sử. Xem [cách phân trang và kiểm tra truy vấn](docs/alert-history.md).

Bấm một sự kiện để xem tọa độ đã lưu của nó: điểm màu cam trên bản đồ tách riêng khỏi ghim vị trí mới nhất. Sự kiện thiếu GPS được thông báo rõ, không thay bằng vị trí hiện tại. Có thể mở từ cả danh sách Trang chủ và bảng Lịch sử.

## Clone và chạy lần đầu trên Windows

Dự án cần Python 3.11 trở lên, đã kiểm tra trên Python 3.12.14. Máy cần Internet để cài thư viện. Kiểm tra `python --version` trước; nếu chưa có Python, cài từ [python.org](https://www.python.org/downloads/windows/). Các lệnh dưới chạy trong PowerShell; cần Git để dùng `git clone`.

### Chạy thử giao diện

```powershell
git clone https://github.com/Ngocnguyen055/IoT.git
cd IoT
.\Cai-dat.cmd
.\Chay-web.cmd
```

Đợi `CAI DAT XONG` ở bước cài đặt. Khi web mở, vào <http://127.0.0.1:5000> và dùng mật khẩu ở dòng `Mat khau dang nhap` trong cửa sổ web.

Trên repo mới chưa có cấu hình riêng, ứng dụng tự tạo mật khẩu/khóa trong `config.local.json` và database SQLite trống. Luồng này chưa cần tạo `.env`, tài khoản Atlas hoặc thiết bị ESP32. Web chưa có số đo sẽ hiển thị trạng thái chưa nhận dữ liệu; đây là kết quả mong đợi.

`.env`, mật khẩu, URI Atlas, database thật và header cấu hình ESP32 được Git bỏ qua. Clone repo chỉ lấy mã nguồn và các file mẫu, không lấy cấu hình hay lịch sử số đo của máy người khác.

### Dùng MongoDB Atlas

Sau khi đã chạy thử ở trên:

1. Dừng web bằng Ctrl+C.
2. Chuẩn bị cluster/database user và cho phép IP máy trong Atlas theo [hướng dẫn Atlas](docs/mongodb-atlas.md).
3. Chạy `Tao-cau-hinh-MongoDB.cmd`, nhập URI Atlas và tên database của môi trường bạn muốn dùng.
4. Chạy `.venv\Scripts\python.exe -m scripts.configure_env` để tạo `.env` từ các giá trị vừa được sinh/lưu. Mật khẩu và khóa đã có được giữ nguyên.
5. Mở `.env`, đặt `DATABASE_BACKEND=mongodb`. Các trường `MONGODB_URI`, `MONGODB_DATABASE` và `MONGODB_TIMEOUT_MS` đã được công cụ điền.
6. Chạy `Khoi-tao-MongoDB.cmd`, đợi `KHOI TAO MONGODB DAT`, rồi mở lại `Chay-web.cmd`.

Với repo mới và database Atlas mới, dùng bước khởi tạo này. `Chuyen-sang-MongoDB.cmd` dành cho máy đã có dữ liệu SQLite cần chuyển; xem [hướng dẫn migration](docs/mongodb-migration.md).

### Kết nối thiết bị thật

1. Giữ web đang chạy, cấp nguồn thiết bị và module 4G như cấu hình phần cứng của dự án.
2. Chạy `Ket-noi-thiet-bi.cmd`, đợi địa chỉ Cloudflare và dòng `DA CHUAN BI FIRMWARE`. Script tự tạo header với URL/khóa khớp web trên máy này.
3. Mở lại `firmware/ESP32_Firmware/ESP32_Firmware.ino` bằng Arduino IDE, chọn ESP32 Dev Module và cổng USB thực tế rồi Upload. Cài board/thư viện theo [hướng dẫn Arduino](firmware/Huong-dan-Arduino.md).

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

Sau khi cập nhật tính năng Lịch sử, dừng web/thiết bị và chạy `Kiem-tra-lich-su.cmd` để kiểm tra phân trang cùng `explain` trên Atlas. Công cụ dùng database tạm riêng, dọn dữ liệu thử rồi bổ sung index cho database ứng dụng. Chạy xong mở lại `Chay-web.cmd`; thay đổi này không cần nạp firmware.

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
- [Trang chủ, lịch sử cảnh báo và hiệu năng truy vấn](docs/alert-history.md)

Backend nằm trong `backend/app/`, frontend trong `frontend/`, firmware chính trong `firmware/ESP32_Firmware/`. `app.py` giữ điểm vào chạy Python tương thích; cấu hình chính của máy này là `.env`, database là MongoDB Atlas. Các sketch chẩn đoán cảm biến trong `firmware/` được giữ để xử lý lỗi phần cứng.

Sáu giai đoạn cải tổ đã được lưu trên Git, mốc cuối là `d6d42df`. Các script commit/push riêng từng giai đoạn đã được bỏ sau khi hoàn tất; dùng Git hoặc Source Control của VS Code để lưu thay đổi tiếp theo. Lượt thử trong phòng đã đạt, GPS ngoài trời được chủ dự án hẹn thử sau. Chi tiết ở `docs/refactor-plan.md`.
