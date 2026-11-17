# Nạp firmware bằng Arduino IDE

Website đã có cấu hình riêng trong dự án. Để nhận dữ liệu từ thiết bị, cần nạp bản firmware đã cập nhật địa chỉ Cloudflare.

## 1. Cài hỗ trợ ESP32

1. Trong Arduino IDE chọn **File → Preferences…**.
2. Tìm ô **Additional boards manager URLs**, thêm địa chỉ bên dưới. Nếu ô đã có địa chỉ khác, thêm dòng mới thay vì xóa địa chỉ cũ:

   https://espressif.github.io/arduino-esp32/package_esp32_index.json

3. Bấm **OK**.
4. Chọn **Tools → Board → Boards Manager…**. Gõ **esp32** trong ô tìm kiếm.
5. Tìm **esp32 by Espressif Systems**, bấm **Install** và chờ hoàn tất. Nếu đã hiện **Installed** thì không cần cài lại.

Nguồn: [hướng dẫn chính thức của Espressif](https://docs.espressif.com/projects/arduino-esp32/en/latest/installing.html).

## 2. Chọn board và cổng

1. Chọn **Tools → Board → esp32 → ESP32 Dev Module**.
2. Chọn **Tools → Port** và chọn cổng của ESP32 đang cắm. Trên máy Ngọc hiện là **COM3**; máy khác hoặc cổng USB khác có thể có số COM khác.

Đây là board theo chú thích trong mã firmware do người làm sản phẩm cung cấp.

## 3. Cài thư viện cảm biến

Chọn **Sketch → Include Library → Manage Libraries…**. Lần lượt tìm và cài:

| Tìm kiếm | Chọn thư viện |
| --- | --- |
| TinyGPSPlus | TinyGPSPlus, tác giả Mikal Hart |
| MAX3010x | SparkFun MAX3010x Pulse and Proximity Sensor Library |
| Adafruit INA219 | Adafruit INA219 |

Nếu được hỏi cài thêm thư viện phụ thuộc, chọn **Install All**.

Nguồn: [TinyGPSPlus](https://github.com/mikalhart/TinyGPSPlus), [SparkFun MAX3010x](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library), [Adafruit INA219](https://github.com/adafruit/Adafruit_INA219).

## 4. Mở đúng file và nạp

1. Đảm bảo web và cửa sổ Cloudflare vẫn đang chạy.
2. Chọn **File → Open…**, trong thư mục repo đã clone mở **firmware\ESP32_Firmware\ESP32_Firmware.ino**.
3. Kiểm tra board **ESP32 Dev Module** và cổng của ESP32 đang cắm.
4. Bấm nút hình **mũi tên sang phải** ở góc trên bên trái, cạnh nút dấu tích. Đây là nút **Upload**.
5. Chờ biên dịch và nạp hoàn tất. Nếu có lỗi, giữ nguyên thông báo trong bảng Output để xem dòng lỗi cụ thể.

Nếu báo thiếu file .h, đối chiếu phần thư viện ở bước 3. Nếu nạp dừng ở Connecting, một số board cần giữ nút BOOT trong lúc kết nối theo hướng dẫn Espressif.

## 5. Kiểm tra thiết bị gửi dữ liệu

1. Chọn **Tools → Serial Monitor**, đặt tốc độ **115200 baud**.
2. Chờ thiết bị đăng ký mạng 4G. Khi gửi thành công, mã firmware in ra **[UPLOAD] OK**.
3. Mở http://127.0.0.1:5000 và đăng nhập bằng mật khẩu hiển thị ở cửa sổ web, tương ứng `ADMIN_PASSWORD` trong `.env`.
4. Kiểm tra chỉ số, sau đó bấm nút SOS trên thiết bị và xem **Cảnh báo & sự kiện**.

Lệnh yêu cầu định vị cần thiết bị đang có mạng; để trả tọa độ thì GPS phải bắt được vệ tinh. Thiết bị vẫn có thể phản hồi lệnh với tọa độ trống khi chưa có GPS fix. Nếu không có dữ liệu, nội dung Serial Monitor sẽ giúp phân biệt lỗi cảm biến, mạng 4G và gửi HTTPS.
