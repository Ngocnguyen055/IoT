# Kiểm tra riêng cảm biến nhịp tim

Bản này chỉ kiểm tra kết nối và dữ liệu thô của cảm biến. Trong lúc chạy bản test, ESP32 tạm thời không xử lý SOS, GPS hay gửi dữ liệu lên web. Không cần đổi dây trước khi chạy test.

1. Mở KiemTra_MAX3010x.ino trong Arduino IDE.
2. Chọn ESP32 Dev Module, COM3, bấm Upload.
3. Mở Serial Monitor, chọn 115200 baud. Nếu chưa thấy log, bấm EN. Kết quả lỗi sẽ lặp lại mỗi 5 giây; dữ liệu thô sẽ lặp mỗi giây khi nhận cảm biến.
4. Gửi các dòng [TEST], [I2C], [CHIP], [RESULT] và [RAW] để đối chiếu.

Ý nghĩa:

- NO_ACK: không giao tiếp được với địa chỉ 0x57 trên cặp chân đang thử; có thể do dây, nguồn, chân tín hiệu, cảm biến hoặc đường I2C.
- ID_MAX30100: đọc được mã chip 0x11, phù hợp MAX30100. Thư viện của firmware chính đang dùng yêu cầu mã 0x15.
- SENSOR_OK: thư viện nhận được chip và đã gửi cấu hình bật LED đỏ + hồng ngoại. Dữ liệu thô và nguồn LED vẫn cần được kiểm tra.
- Nếu chỉ SENSOR_OK ở SDA=D22, SCL=D23: kết nối hiện tại đảo so với cặp chân trong firmware chính. Cần đối chiếu nhãn chân trước khi sửa dây hoặc cấu hình.

Kết quả NO_ACK không đủ để kết luận cảm biến hỏng. Nguồn cấp phải đúng với module thực tế; không suy ra điện áp VIN từ thông số của chip trần. Ngắt USB và nguồn pin trước khi đổi dây.

Sau khi kiểm tra, nạp lại ../ESP32_Firmware/ESP32_Firmware.ino để khôi phục SOS và gửi dữ liệu web. Giữ Cloudflare chạy; nếu đã mở tunnel mới, cần dùng bản firmware được cập nhật URL mới.

Tham khảo:

- [Mã thư viện SparkFun, kiểm tra Part ID và cấu hình LED](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library/blob/master/src/MAX30105.cpp).
- [Datasheet MAX30100, thanh ghi Part ID 0xFF](https://www.analog.com/media/en/technical-documentation/data-sheets/max30100.pdf).
