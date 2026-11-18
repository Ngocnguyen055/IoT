# Trang chủ và lịch sử cảnh báo

## Sử dụng

- **Trang chủ** (`/`): số đo trực tiếp, GPS và tối đa 8 sự kiện mới nhất; tiếp tục cập nhật mỗi 5 giây.
- **Lịch sử** (`/history`): 20 sự kiện mỗi trang, mới nhất trước. **Sau →** xem cũ hơn, **← Trước** quay về mới hơn.
- **Về mới nhất**: bắt đầu lại từ các sự kiện mới nhất. Khi đang xem trang cũ, sự kiện vừa nhận không tự đẩy các dòng sang trang khác.

Bảng lịch sử gồm SOS (`button`), nhịp tim cao (`high_bpm`), SpO₂ thấp (`low_spo2`) và phản hồi yêu cầu định vị (`remote`). Các bản tin `telemetry` định kỳ vẫn được lưu như trước, nhưng không xuất hiện trong bảng sự kiện. Số đo, pin và GPS trên mỗi dòng là giá trị được lưu cùng sự kiện đó; thiếu dữ liệu hiển thị `—` hoặc “Chưa có tọa độ”.

Trang Lịch sử không polling. Nó chỉ lấy dữ liệu khi mở trang hoặc bấm nút; khi mạng lỗi, bảng và vị trí trang đang xem được giữ lại. Màn hình nhỏ chuyển điều hướng lên trên và cho phép cuộn ngang bảng.

## Xem vị trí của một sự kiện

Bấm một mục trong **Cảnh báo mới nhất**, hoặc bấm tên sự kiện/tọa độ trong bảng **Lịch sử**. Web mở khung thông tin của sự kiện trên Trang chủ. Liên kết từ Lịch sử có dạng `/?event=<id>#eventLocation`; backend đọc đúng sự kiện theo ID, nên vẫn xem được mục cũ ngoài danh sách Trang chủ.

Nếu có GPS, bản đồ định tâm vào tọa độ đã lưu và đánh dấu **điểm màu cam**, kèm popup tên sự kiện, thời gian, thiết bị và tọa độ. Có thể mở chính vị trí này trên Google Maps. Ghim vị trí mới nhất của thiết bị tiếp tục cập nhật riêng; bản tin mới không tự chuyển khung nhìn khỏi sự kiện đang xem. Đổi nền hoặc tải lại ảnh bản đồ giữ nguyên cả hai loại điểm và hành trình. Bấm **Đóng** để bỏ điểm sự kiện; **Về vị trí hiện tại** vẫn định tâm vào ghim thiết bị.

Nếu sự kiện ghi **Không có GPS fix**, khung thông tin giải thích rằng chưa có tọa độ tại thời điểm đó; không đặt điểm trên bản đồ và không mượn vị trí mới nhất để đại diện cho cảnh báo cũ. Những sự kiện thiếu GPS từ trước sẽ không tự có vị trí sau khi GPS hoạt động trở lại. Không cần nạp firmware hoặc chuyển dữ liệu cho tính năng này.

Chủ dự án đã xác nhận mở đúng thông tin sự kiện ở cả Trang chủ và Lịch sử trên trình duyệt thật ngày 18/11/2026. Tọa độ có GPS, số 0, thiếu GPS và việc giữ điểm sự kiện khi vị trí mới đến đã được kiểm thử bằng dữ liệu mô phỏng; không tạo dữ liệu thử trong database ứng dụng. Thử GPS thiết bị ngoài trời vẫn là bước riêng.

## Vì sao truy vấn không cần quét hết telemetry

Backend dùng danh sách loại sự kiện cụ thể và partial index chỉ chứa các dòng đó. Dù collection có nhiều telemetry, index lịch sử chỉ chứa sự kiện. Phân trang dùng điều kiện ID thay cho bỏ qua hàng chục nghìn dòng bằng `skip`:

```text
Trang đầu: event trong danh sách sự kiện, _id giảm dần, limit 21
Trang cũ:  _id < before và _id <= snapshot, giảm dần, limit 21
Trang mới: _id > after  và _id <= snapshot, tăng dần, limit 21
```

Backend trả 20 dòng; dòng thứ 21 cho biết còn trang kế tiếp. Khi đi ngược, kết quả được đảo lại để bảng luôn mới trước/cũ sau. Một truy vấn tồn tại giới hạn 1 dòng xác định có trang ở hướng còn lại. Không đếm toàn bộ sự kiện ở mỗi request, vì vậy giao diện hiển thị số trang đang xem thay vì tổng số trang.

ID là số nguyên tăng dần được cấp cùng transaction ghi dữ liệu. Snapshot giữ ID mới nhất ở lần mở lịch sử; các bản tin mới có ID cao hơn sẽ chỉ xuất hiện khi bấm Về mới nhất. Đây là mốc phân trang cho dữ liệu được thêm mới, không phải transaction giữ mở trong suốt thời gian duyệt. Nếu sau này thêm tính năng sửa/xóa lịch sử cần xem lại hành vi này.

MongoDB có các index sau trong `readings`:

| Index | Các khóa | Phạm vi |
|---|---|---|
| `_id_` | `_id` | Khóa duy nhất, tất cả số đo |
| `idx_readings_device_ts` | `device_id`, `ts` | Tất cả số đo; giữ tương thích truy vấn cũ |
| `idx_readings_device_id` | `device_id`, `_id` giảm dần | Tất cả số đo; giữ tương thích |
| `idx_readings_alerts_id` | `_id` giảm dần, `event` | Chỉ bốn loại sự kiện |
| `idx_readings_location_id` | `_id` giảm dần, `lat` | Chỉ dòng có cả lat/lon là số |
| `idx_readings_device_location_id` | `device_id`, `_id` giảm dần | Chỉ dòng có cả lat/lon là số |

Hai khóa trong index toàn cục tránh tạo partial index đơn trên `_id` (MongoDB không cho phép partial index của khóa `_id` mặc định). Bộ lọc truy vấn chứa cùng điều kiện của partial index. Truy vấn vị trí cuối cũng dùng index riêng để thiết bị lâu không có GPS không buộc web đi qua toàn bộ telemetry. SQLite dự phòng có index và phân trang tương đương.

Index tăng dung lượng và chi phí ghi. Ba index mới chỉ chứa sự kiện hoặc dòng có tọa độ; không nhân bản toàn bộ telemetry thành collection khác. Chưa có TTL hoặc tự xóa số đo cũ. Số bản tin vẫn tăng theo chu kỳ gửi của thiết bị, nên dung lượng Atlas cần được theo dõi riêng khi chạy lâu dài.

Tham khảo: [MongoDB partial indexes](https://www.mongodb.com/docs/manual/core/index-partial/), [range pagination thay cho skip](https://www.mongodb.com/docs/manual/reference/method/cursor.skip/), [đọc kết quả explain](https://www.mongodb.com/docs/manual/reference/explain-results/).

## Kiểm tra và cập nhật

Không cần sửa `.env`, chuyển dữ liệu, cài thêm thư viện hoặc nạp firmware cho thay đổi này. Trước khi cập nhật đã sao lưu nguồn/cấu hình cục bộ trong `.runtime/backups/`; dữ liệu Atlas đang dùng được giữ nguyên.

1. Dừng web bằng Ctrl+C và tạm tắt thiết bị.
2. Chạy `Kiem-tra.cmd` để kiểm tra phần mềm cục bộ (cần bộ thư viện kiểm thử và Node.js đã có ở máy phát triển).
3. Chạy **`Kiem-tra-lich-su.cmd`**, hoặc:

   ```powershell
   .venv\Scripts\python.exe -m scripts.check_alert_history
   ```

4. Đợi **KIEM TRA LICH SU DAT** rồi mở lại `Chay-web.cmd`. Đăng nhập và thử hai mục Trang chủ/Lịch sử. Nếu trình duyệt còn giao diện cũ, bấm Ctrl+F5.

Công cụ Atlas tạo database ngắn dạng `sos_hist_<mã-ngẫu-nhiên>`, tạo model/index, ghi **10.000 telemetry + 60 sự kiện giả**, rồi kiểm tra API phân trang, đi ngược, snapshot khi thêm sự kiện và truy vấn GPS. Tất cả sự kiện được đặt trước một dải dài telemetry để phép thử phát hiện việc đọc qua bản tin không liên quan.

`explain('executionStats')` được chạy với cùng bộ lọc, sort, hint và limit của ứng dụng. Công cụ từ chối kế hoạch có `COLLSCAN`, sort chặn, hoặc số key/document đọc quá giới hạn cho một trang. Sau khi thử đạt, công cụ bổ sung/đối chiếu index ở database ứng dụng và chạy explain đọc lịch sử thật. Chỉ ba collection do lượt thử tạo trong database tạm được xóa ở bước dọn; không ghi số đo giả vào database ứng dụng.

Kết quả ở `.runtime/history-query-check.log` và `.runtime/history-query-check.json`, không ghi URI/mật khẩu. Thời gian thực tế phụ thuộc Atlas, mạng và lượng cảnh báo; phép thử 10.000 telemetry không phải bằng chứng đã benchmark một triệu bản ghi. Số key/document đọc và kế hoạch truy vấn giúp đánh giá việc dùng đúng index mà không hứa một mức mili giây cố định.

Đã xác nhận lượt Atlas thật ngày **18/11/2026** (giờ Việt Nam): phân trang, snapshot và API đạt. Trang đầu, trang cũ hơn và trang mới hơn đều đọc **21 keys/21 documents**; vị trí cuối đọc **1/1**, thiết bị không có GPS đọc **0/0**. Các kế hoạch dùng `IXSCAN`, không có `COLLSCAN` hoặc sort chặn. Database tạm đã được dọn; index trên database ứng dụng đã được xác minh và explain lịch sử thật cũng đọc **21/21**. Số 21 gồm tối đa 20 dòng hiển thị và một dòng để xác định còn trang tiếp.

Chủ dự án đã mở lại web, tải lại giao diện và xác nhận Trang chủ/Lịch sử hiển thị đúng, các nút Trước/Sau chuyển trang bình thường. Đợt cập nhật đã được kiểm tra phần mềm cục bộ, Atlas thật và giao diện trên trình duyệt.

Khởi động web cũng tạo các index còn thiếu. Nếu kiểm tra Atlas thất bại, xem dòng lỗi trước khi tiếp tục; không chạy lại migration dữ liệu để sửa lỗi index. Các API thiết bị, dữ liệu lịch sử, khóa và firmware được giữ nguyên. `/api/status` cũ vẫn trả 150 số đo/20 sự kiện; trang chủ mới dùng `/api/dashboard` với số đo cuối và 8 sự kiện để giảm dữ liệu tải mỗi 5 giây.
