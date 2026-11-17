# Thử thiết bị thật — giai đoạn 6

## Chuẩn bị

- Máy chạy web có Internet và kết nối được Atlas; đã hoàn tất migration/model/schema.
- Thiết bị giữ nguyên cách đấu dây và nguồn như bản đã hoạt động. Cấp nguồn ESP32 và module 4G; SIM có dữ liệu, antenna đã nối như trước.
- Chạy `Chay-web.cmd`, đăng nhập. Sau đó chạy `Ket-noi-thiet-bi.cmd`, giữ cả hai cửa sổ mở.
- Đợi địa chỉ tunnel và dòng `DA CHUAN BI FIRMWARE`. Mở lại sketch `firmware/ESP32_Firmware/ESP32_Firmware.ino` để IDE nhận header mới, chọn đúng board/cổng rồi Upload.
- Mở Serial Monitor ở 115200 baud để xem `[SENSORS]`, `[STATE]` và kết quả `[HTTPS]`.

Khóa web và firmware được lấy cùng cấu hình `.env`. Tunnel mới làm thay đổi header local; main firmware không đổi chỉ vì chuyển backend sang MongoDB.

## Ghi nhận dữ liệu mới

Trước khi thử, lưu mốc ID hiện tại:

```powershell
.venv\Scripts\python.exe -m scripts.check_device --start
```

Sau mỗi thao tác, đọc dữ liệu thực đã tới web:

```powershell
.venv\Scripts\python.exe -m scripts.check_device
```

Có thể bấm đúp `Kiem-tra-thiet-bi.cmd` để đọc tiến độ. Các lệnh chỉ đăng nhập và đọc API, không gửi bản tin giả. Báo cáo riêng nằm trong `.runtime/device-check.json`, mốc bắt đầu ở `.runtime/device-check-baseline.json`.

Chỉ các dòng đúng thiết bị, ID lớn hơn mốc và timestamp sau lúc bắt đầu được tính. Các dòng SOS/số đo cũ không làm bài thử đạt. Báo cáo tích lũy những gì đã quan sát của cùng một lượt thử; trạng thái dữ liệu mới nhất vẫn được kiểm tra riêng.

## Các bước thử

1. **Đường truyền:** chờ firmware báo POST `/api/device/telemetry => 200`, web nhận bản tin có ID/thời gian mới. Chu kỳ danh nghĩa là 15 giây; tác vụ modem/mạng có thể làm lâu hơn.
2. **SOS:** bấm nút SOS một lần, đối chiếu `[SOS] Button press detected`, upload thành công và sự kiện mới “Nhấn nút SOS” trên web.
3. **Số đo:** đặt ngón tay như cách đã đo thành công, giữ ổn định và chờ đủ cửa sổ đo/upload. Xác nhận BPM, SpO₂, điện áp và phần trăm pin đã nhận trong các bản tin mới; null và 0 tiếp tục được phân biệt.
4. **Lệnh từ web:** bấm “Yêu cầu định vị”, chờ thiết bị nhận LOCATE rồi gửi sự kiện remote. Lệnh chờ phải trở lại NONE sau upload thành công.
5. **GPS:** xác nhận có lat/lon mới từ thiết bị, marker/lịch sử đường đi hiển thị và tọa độ trong bản tin khớp với web. Sự kiện remote có GPS=null chứng minh luồng lệnh đã chạy, còn vị trí GPS chưa được xác nhận.
6. **Lưu trữ:** dữ liệu mới vẫn hiện sau khi dừng/mở lại web. Không cần đóng tunnel nếu giữ nguyên lượt kết nối; nếu tunnel đổi URL cần cập nhật header và Upload lại.

Không thay ngưỡng hay tạo số đo giả để ép cảnh báo sinh lý. Cảnh báo high_bpm/low_spo2 đã có kiểm thử phần mềm; ghi nhận riêng nếu chúng xuất hiện trong lượt thử thật.

Hàng đợi sự kiện hiện nằm trong RAM của ESP32. Không dùng việc cắt nguồn khi cảnh báo chưa gửi làm phép thử bảo đảm lưu SOS; hàng đợi này chưa phải lưu trữ bền vững.

## Lỗi thường gặp

| Dấu hiệu | Kiểm tra |
|---|---|
| Không có bản tin mới | Hai cửa sổ web/tunnel, URL firmware và log HTTP gần nhất |
| HTTP 401 | Header local có DEVICE_KEY khớp cấu hình web, đã Upload bản mới |
| SIM not inserted/CPIN chưa READY | SIM và nguồn module 4G theo cách đã chạy ổn |
| MAX=MISSING | Nguồn, dây và kết nối cảm biến; không kết luận là lỗi giao diện |
| Có remote nhưng tọa độ trống | GPS chưa có fix; xem satellites/lat/lon trên log |
| API HTTP 503 | Kết nối Atlas/IP cho phép và database user |

## Chốt mốc

Giai đoạn 6 đã được commit/push tại `d6d42df`. Khi cần xác minh lại, chạy `Kiem-tra.cmd` và các lệnh sau rồi lưu thay đổi bằng Git. Báo cáo chứa dữ liệu thực nhưng được Git bỏ qua.

```powershell
.venv\Scripts\python.exe -m scripts.check_device --require-complete
.venv\Scripts\python.exe -m scripts.check_active_mongodb
.venv\Scripts\python.exe -m scripts.init_db --check
```

Chủ dự án đã yêu cầu để lượt thử GPS ngoài trời sang sau vì hiện thiết bị ở trong phòng. Quyết định này được ghi trong báo cáo bằng `--defer-gps`; việc chốt lượt thử trong phòng vẫn yêu cầu SOS, BPM/SpO₂, pin, bản tin mới và vòng lệnh LOCATE hoàn tất. Cờ `gps_fix_received` vẫn giữ false đến khi có tọa độ thật, và phạm vi được ghi là `indoor_gps_deferred`.

## Tiến độ của lượt thử hiện tại

- Đã xác nhận commit giai đoạn 5 `da4fb2e`, sạch và khớp origin/main trước khi sửa.
- Sao lưu đầu giai đoạn: `.runtime/backups/snapshot-20261117T142643521657Z/`.
- Đã mở web, xác nhận khóa firmware khớp web, máy nhận COM3 và tunnel mới được chuẩn bị.
- Mốc ban đầu: ID 312. Đã quan sát ID 313–333 có SOS, cảnh báo high_bpm, BPM/SpO₂, điện áp và phần trăm pin từ thiết bị thật.
- Lệnh LOCATE được gửi qua API web, thiết bị đã gửi sự kiện remote và lệnh chờ trở về NONE.
- GPS vẫn 0 vệ tinh, lat/lon=null; chủ dự án sẽ thử ngoài trời sau. Không ghi nhận GPS đã hoạt động từ bản tin remote không có tọa độ.
- Mốc xác minh cuối: 28 bản tin mới, ID 313–340; SOS ID 319, phản hồi remote ID 328, lệnh chờ NONE. Phạm vi `indoor_gps_deferred` đạt, GPS fix vẫn false.
- Chủ dự án đã dừng/mở lại web và xác nhận sự kiện SOS vừa thử cùng lịch sử cũ vẫn đầy đủ; bản tin mới tiếp tục được nhận sau mở lại.
