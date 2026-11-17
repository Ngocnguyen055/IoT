# Mở web SOS trên máy này

Thư mục dự án: `C:\Projects\IoT`.

1. Lần đầu: bấm đúp **Cai-dat.cmd**, đợi hiện **CAI DAT XONG**. Cần Internet để tải các thư viện Python của dự án.
2. Bấm đúp **Chay-web.cmd**. Một cửa sổ chạy web sẽ mở và trình duyệt tự mở trang <http://127.0.0.1:5000>.
3. Nhập mật khẩu ở dòng **Mat khau dang nhap** trong cửa sổ chạy web. Cấu hình chính hiện nằm trong `.env`, trường `ADMIN_PASSWORD`; các bản cài cũ vẫn đọc được `config.local.json`.
4. Giữ cửa sổ chạy web mở khi sử dụng. Muốn dừng: bấm Ctrl+C trong cửa sổ đó. Lần sau chỉ cần bấm đúp **Chay-web.cmd**.

Có thể dùng **Dung-web.cmd** để dừng web đang chạy nền. Nếu web đã chạy, bấm **Chay-web.cmd** chỉ mở trang web hiện tại.

Nếu chưa nhận bản tin từ thiết bị, trang web sẽ báo **Chưa có dữ liệu từ ESP32** và các chỉ số hiện dấu **—**. Đây là trạng thái bình thường trước khi thiết bị kết nối được.

Máy này hiện dùng Python, Flask và MongoDB Atlas với database `iot_sos`. Thư viện Python nằm trong `.venv`; không cần cài MongoDB server trên máy để dùng Atlas. Bản SQLite cũ vẫn được giữ, còn dữ liệu nhận sau khi chuyển được lưu trên Atlas. Node.js chỉ phục vụ kiểm thử JavaScript.

# Để nhận dữ liệu từ thiết bị thật

Thiết bị hiện dùng SIM 4G để gửi dữ liệu theo đường:

**ESP32 → mạng 4G → địa chỉ Cloudflare → web trên máy tính**.

`127.0.0.1` chỉ dùng để mở web trên chính máy tính này. Không điền địa chỉ đó vào ESP32.

Sau khi web chạy được:

1. Bấm đúp **Ket-noi-thiet-bi.cmd**. File này tải Cloudflare từ kho chính thức, kiểm tra SHA-256 rồi mở tunnel tới web. Không cần quyền quản trị.
2. Đợi hiện địa chỉ `https://...trycloudflare.com`. Script sẽ tạo/cập nhật `firmware\ESP32_Firmware\device_config.local.h` với địa chỉ này và khóa thiết bị. Header riêng này được Git bỏ qua.
3. Mở lại **firmware\ESP32_Firmware\ESP32_Firmware.ino** trong Arduino IDE để nhận header mới, chọn ESP32 Dev Module và cổng COM đang cắm thiết bị rồi Upload.
4. Giữ cả hai cửa sổ chạy web và Cloudflare mở. Mở web, đợi dữ liệu; bấm thử nút SOS trên thiết bị và kiểm tra mục **Cảnh báo & sự kiện**.

Nếu báo chưa có cổng COM, kiểm tra thiết bị đã cắm cáp USB truyền dữ liệu vào máy tính. Nếu không nạp được firmware, cần kiểm tra board, thư viện Arduino và thông báo lỗi cụ thể.

Trong header `device_config.local.h`, ba dòng cần khớp với web là (script tự tạo):

```cpp
const char* DEVICE_ID = "ngoc-01";
const char* DEVICE_KEY = "gia tri DEVICE_KEY trong .env";
const char* SERVER_BASE = "https://dia-chi-moi.trycloudflare.com";
```

Dòng `APN = "v-internet"` là cấu hình mạng SIM, không phải chỗ điền địa chỉ website. Hướng dẫn cũ đã ghép nhầm hai dòng này.

Sau khi sửa firmware cần nạp lại qua USB trong Arduino IDE. Máy tính phải có Internet, web và tunnel đều đang chạy. Quick Tunnel thường đổi địa chỉ sau mỗi lần mở lại; lúc đó cần cập nhật `SERVER_BASE` và nạp lại.

Cloudflare tạo đường truy cập web qua Internet. Mật khẩu và khóa được đọc từ `.env` trên máy này; script tạo header firmware với cùng khóa mà web đang dùng. Các file cấu hình thực tế được Git bỏ qua.

Nguồn tải và cách hoạt động: [Cloudflare Downloads](https://developers.cloudflare.com/tunnel/downloads/), [Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

Theo mã firmware hiện có, thiết bị gửi chỉ số khoảng mỗi 15 giây, còn web tải dữ liệu mỗi 5 giây. Thực tế có thể lâu hơn do mạng 4G. GPS cần bắt được vệ tinh; web chạy được không có nghĩa là GPS đã có vị trí.

# Những file cần giữ

- `.env`: mật khẩu, khóa thiết bị và kết nối Atlas đang dùng.
- `config.local.json`, `mongodb.local.json`: cấu hình tương thích từ trước khi chuyển sang `.env`.
- `iot_ngoc.sqlite3`: bản dữ liệu SQLite trước khi chuyển sang Atlas.
- `.runtime/backups/`: các bản sao lưu riêng trên máy; dữ liệu mới sau chuyển nằm trong Atlas.
- `app.py`, `backend`, `frontend`: điểm vào và mã nguồn backend/frontend hiện tại.

Không cần chạy file `app.cpython-313.pyc`. Hướng dẫn gốc trong repo đã thay các khóa bằng giá trị mẫu; bản sao trước thay đổi nằm trong `.runtime/backups/`.

Chạy `Kiem-tra.cmd` để kiểm tra phần mềm trên database tạm. Tiến độ cải tổ: [docs/refactor-plan.md](docs/refactor-plan.md).

Giai đoạn 3 chuyển tài nguyên sang `frontend/`. Sau khi cập nhật mã, dừng cửa sổ web cũ bằng Ctrl+C rồi mở lại `Chay-web.cmd`; trình duyệt tải dashboard và các module mới từ cùng Flask server.

Hướng dẫn model/schema và lệnh khởi tạo: [docs/models-and-configuration.md](docs/models-and-configuration.md). Các bước thử SOS, số đo, định vị và lưu trữ với thiết bị thật: [docs/device-verification.md](docs/device-verification.md).

Dùng thường ngày: `Chay-web.cmd`, `Ket-noi-thiet-bi.cmd`, `Dung-web.cmd`. Các file `Chot-giai-doan-*.cmd` dùng để lưu mốc phát triển; không cần chạy khi chỉ mở web.
