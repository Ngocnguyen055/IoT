# Test riêng MAX30102: BPM và SpO2

Chân I2C cố định: **SDA = D23**, **SCL = D22**, GND chung với ESP32. Giữ nguồn VCC phù hợp module thực tế; code không thay đổi được nguồn cấp. Ngắt USB và pin trước khi thay dây.

Bản này thay thế tạm thời chương trình trên ESP32 để chỉ đọc MAX30102. Trong lúc test, thiết bị không xử lý SOS, GPS hoặc gửi dữ liệu web.

## Cách nạp và xem

1. Mở MAX30102_BPM_SpO2.ino trong thư mục này bằng Arduino IDE.
2. Chọn ESP32 Dev Module và COM3 (hoặc cổng hiện tại của ESP32).
3. Bấm Upload, sau đó mở Serial Monitor ở 115200 baud.
4. Khi hiện [READY], đặt đầu ngón tay lên phần quang học của cảm biến, giữ tiếp xúc nhẹ và ổn định. Đợi khoảng 10-20 giây để quan sát các dòng [DATA].
5. Gửi ảnh kết quả nếu chưa có số hoặc vẫn báo lỗi.

Đã dùng các thư viện có trên máy: SparkFun MAX3010x Pulse and Proximity Sensor Library, Wire, spo2_algorithm.h. Không cần cài thêm thư viện để dùng bản này.

## Đọc kết quả

- [READY]: thư viện nhận diện được cảm biến và đã gửi cấu hình bật LED đỏ + hồng ngoại.
- [DATA]: dữ liệu RED/IR thô và kết quả BPM/SpO2; in mỗi giây khi cảm biến đang có mẫu.
- COLLECTING: đang thu cửa sổ 100 mẫu (khoảng 4 giây ở cấu hình này).
- HRvalid=1 hoặc SpO2valid=1: thuật toán chấp nhận giá trị tương ứng. Đây không phải xác nhận độ chính xác của phép đo.
- Dấu --: chưa đủ điều kiện hoặc thuật toán chưa cho kết quả hợp lệ; không thay bằng số 0 giả.
- NO_FINGER_OR_LOW_IR: IR dưới ngưỡng nhận diện tham khảo 50000. Nếu đã đặt ngón tay mà vẫn gặp, gửi số RED/IR để kiểm tra trước khi điều chỉnh ngưỡng FINGER_IR_MIN.
- I2C_TIMEOUT/result=5: giao tiếp bị hết thời gian chờ; cần kiểm tra nguồn và dây. Nạp phần mềm khác không đủ để khẳng định khắc phục được nguyên nhân phần cứng.
- SENSOR_NO_ACK/result=2: không có phản hồi từ địa chỉ 0x57.
- MAX30100_ID: mã chip phù hợp MAX30100, cần đối chiếu loại module.
- NO_NEW_SAMPLES: không có mẫu mới; chương trình sẽ thử khởi tạo lại.

Nếu chưa nhận cảm biến, thông báo lỗi lặp mỗi 3 giây. Bản này chỉ dùng đúng SDA23/SCL22, không tự đảo chân.

## Cách lấy mẫu

Cấu hình cảm biến: độ sáng LED 60, lấy trung bình 4, LED đỏ + IR, sample rate 100, pulse width 411, ADC range 4096. Tần số đầu ra là 25 mẫu/giây, khớp thuật toán Maxim trong thư viện. Sau 100 mẫu đầu tiên, cửa sổ trượt được tính lại sau mỗi 25 mẫu mới; không có thao tác mạng 4G làm gián đoạn vòng đọc.

Tham khảo: [Example8_SPO2 của SparkFun](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library/blob/master/examples/Example8_SPO2/Example8_SPO2.ino).

Kiểm tra xong, mở và nạp lại ../ESP32_Firmware/ESP32_Firmware.ino để khôi phục chức năng SOS và kết nối web. Nếu Cloudflare đã đổi địa chỉ, cập nhật SERVER_BASE trước khi nạp lại.
