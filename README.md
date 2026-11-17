# IoT SOS — Ngọc

Hệ thống thử nghiệm ESP32 gửi SOS, nhịp tim, SpO₂, điện áp/phần trăm pin và GPS qua 4G đến dashboard Flask.

## Chạy trên Windows

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
- `iot_ngoc.sqlite3`: dữ liệu số đo, cảnh báo và lệnh; hiện dùng SQLite.
- `.runtime/backups/`: bản sao lưu riêng trên máy, có cả cấu hình và dữ liệu; được Git bỏ qua.

Backend lấy cấu hình từ biến môi trường hoặc cấu hình riêng trên máy. `Chay-web.cmd` tiếp tục dùng `config.local.json` hiện có. Mã nguồn hiện tại không chứa khóa thực tế; lịch sử commit cũ được giữ nguyên theo lựa chọn của chủ dự án.

## Kiểm tra và sao lưu

Chạy `Kiem-tra.cmd` để kiểm tra API, cấu hình, công cụ sao lưu và các file dự kiến đưa lên Git.

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

## Tài liệu cải tổ

- [Tiến độ và các giai đoạn](docs/refactor-plan.md)
- [Hợp đồng API đang dùng](docs/api-contract.md)
- [Mốc trước cải tổ và khôi phục](docs/baseline.md)

Giai đoạn 1 tạo nền kiểm thử và tài liệu. Backend vẫn dùng Flask/SQLite, frontend vẫn dùng HTML/CSS/JavaScript. Việc chia module và chuyển MongoDB được thực hiện theo các giai đoạn tiếp theo.

Để lưu và đẩy bản giai đoạn 1 đã chuẩn bị lên repo hiện tại, chạy `Chot-giai-doan-1.cmd`. File này kiểm tra phần mềm và index trước khi commit/push, dùng Git đã đăng nhập trên máy chủ dự án. Thông báo thành công có mã commit để xác nhận mốc.
