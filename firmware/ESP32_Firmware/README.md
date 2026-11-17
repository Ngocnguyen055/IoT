# Firmware chính SOS / MAX30102 / 4G

## Bản sửa ngày 17/11/2026

- Ghép URL sau khi bỏ khoảng trắng đầu/cuối và dấu / dư. Bản đã nạp trước đó chứa dấu cách sau tên miền, làm địa chỉ thành ...trycloudflare.com /api/device/telemetry.
- Chờ hết dòng phản hồi HTTPACTION trước khi đọc mã trạng thái. Dữ liệu UART có thể đến thành nhiều phần.
- Tiếp tục đọc MAX30102, GPS, nút SOS và INA219 khi chờ phản hồi AT/HTTPS. Không để thao tác mạng ngắt cửa sổ lấy mẫu nhịp tim.
- Dùng getFIFORed/getFIFOIR để lấy các mẫu theo đúng thứ tự trong bộ đệm. Khi phát hiện mất mẫu, thu lại cửa sổ mới trước khi tính.
- Giữ bản chụp dữ liệu ngay khi xếp cảnh báo vào hàng đợi. Việc bỏ ngón tay sau đó không xóa số đo của cảnh báo đã xếp.
- In trạng thái RED, IR, BPM/SpO2 và cờ valid, điện áp pin, hàng đợi mỗi 5 giây để kiểm tra.

## Nạp đúng bản đã sửa

1. Giữ Chay-web.cmd và Ket-noi-thiet-bi.cmd đang chạy. Không cần mở lại tunnel chỉ để nạp bản sửa này.
2. Đóng cửa sổ Arduino đang giữ bản code cũ, rồi mở lại file ESP32_Firmware.ino tại thư mục này từ ổ đĩa. File modem_protocol.h và device_config.local.h phải ở cùng thư mục.
3. Chọn ESP32 Dev Module và cổng USB của ESP32, bấm Upload.
4. Mở Serial Monitor ở 115200 baud. Bản mới phải có dòng:

       [FIRMWARE] SOS telemetry fix 2026-11-17

   Và dòng [SERVER] phải có tên miền Cloudflare đang dùng, không có khoảng trắng trước đường dẫn API.
5. Đặt ngón tay ổn định lên cảm biến 20-30 giây. Quan sát các dòng [STATE], đặc biệt RED, IR, BPM(valid=...), SpO2(valid=...).
6. Bấm SOS một lần. Kiểm tra [SOS], [EVENT], [HTTPS] POST ... => 200, [UPLOAD] OK rồi đối chiếu sự kiện mới trên web.

Để kiểm tra bản mới, dùng dấu nhận dạng [FIRMWARE] trong Serial Monitor. Nếu chưa có dòng này, nội dung code cũ vẫn đang chạy trên ESP32.

## Phần trăm pin

Web hiển thị đúng battery_pct mà thiết bị gửi. Công thức đang là bảng ước tính cho pin LiPo 1S: điện áp từ 3,0 V trở xuống được quy về 0%; 4,2 V trở lên được quy về 100%. Ví dụ 2,988 V được tính thành 0%, không phải lỗi tải giao diện.

Đây là ước tính dựa trên điện áp, không phải mạch đo dung lượng pin chuyên dụng. Cần đối chiếu điện áp thật tại pin bằng đồng hồ với battery_voltage từ INA219. Nếu hai giá trị khác nhau, cần kiểm tra điểm đo IN+/IN-, GND, dây và sụt áp trên đường nguồn trước khi hiệu chỉnh bảng.

## Kiểm tra phần mềm đã chạy

Từ thư mục dự án:

    .venv\Scripts\python.exe tests\check_firmware.py

Bộ kiểm tra dùng trực tiếp các hàm xử lý phản hồi/hàng đợi từ firmware: URL có khoảng trắng, phản hồi UART chia nhỏ, timeout vẫn phục vụ cảm biến, giữ số đo cảnh báo và bảng pin. Sau đó biên dịch sketch bằng bộ công cụ ESP32 đã cài. Đây là kiểm tra phần mềm; vẫn cần nạp và kiểm tra với phần cứng thực.

Hàng đợi cảnh báo hiện nằm trong RAM, giữ qua lần modem thử kết nối lại nhưng không giữ qua lần mất nguồn/reset ESP32.

## Cấu hình riêng từ giai đoạn 1

`DEVICE_ID`, `DEVICE_KEY` và `SERVER_BASE` nằm trong `device_config.local.h`, được `Ket-noi-thiet-bi.cmd` tạo/cập nhật và Git bỏ qua. `device_config.example.h` là mẫu để đọc, không phải cấu hình được nạp. Trên checkout mới, chạy web và script kết nối để có header thật trước khi biên dịch.

Việc tách header giữ nguyên giá trị cấu hình trên máy tại thời điểm cải tổ. Thuật toán cảm biến và giao thức gửi dữ liệu không thay đổi ở giai đoạn này.

Tham khảo thuật toán: [SparkFun Example8_SPO2](https://github.com/sparkfun/SparkFun_MAX3010x_Sensor_Library/blob/master/examples/Example8_SPO2/Example8_SPO2.ino).
