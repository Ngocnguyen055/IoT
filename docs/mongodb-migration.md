# Chuyển dữ liệu SQLite sang MongoDB Atlas — giai đoạn 5

## Chạy trên máy đang giữ dữ liệu thật

1. Giữ thiết bị tắt để ngừng gửi số đo.
2. Dừng web bằng Ctrl+C trong cửa sổ chạy web, hoặc bấm đúp `Dung-web.cmd`. Dừng cả cửa sổ tunnel nếu còn mở.
3. Bấm đúp `Chuyen-sang-MongoDB.cmd`. Không cần sửa URI hay nhập lại mật khẩu đã lưu.
4. Công cụ chạy 10 kiểm thử chuyển dữ liệu trên database Atlas tạm, gồm lỗi giữa transaction và chạy lại không trùng. Nếu đạt, nó sao lưu rồi chuyển dữ liệu thật.
5. Đợi dòng **DA CHUYEN SANG MONGODB**. Nếu báo lỗi, giữ cửa sổ để xem thông báo; kết quả nằm trong `.runtime/migration.log` và `.runtime/migration-report.json`.
6. Chạy `Chay-web.cmd`, đăng nhập và kiểm tra lịch sử/cảnh báo/các số đo cũ. Giai đoạn 6 sẽ thử lại thiết bị thật và địa chỉ tunnel.

Môi trường agent bị giới hạn mạng nên lượt Atlas thật cần chạy bằng launcher trên Windows của chủ dự án. Công cụ không yêu cầu quyền administrator.

## Trình tự và điều kiện đổi backend

- Yêu cầu cổng web 5000 đã dừng trước khi bắt đầu và trước khi đổi cấu hình.
- Sao lưu mã, SQLite nhất quán, `config.local.json` và `mongodb.local.json` vào `.runtime/backups/snapshot-.../`. Bản sao lưu có manifest và kiểm tra integrity SQLite.
- Đọc SQLite bằng `mode=ro`, giữ nguyên ID, Unix timestamp, null, số 0, số đo và lệnh NONE/LOCATE. Giữ cả `sqlite_sequence` để ID đã xóa không bị dùng lại.
- So sánh toàn bộ số đo/lệnh đang có ở Atlas. Chỉ nhận database trống hoặc bản chuyển dở có các bản ghi khớp. Nếu có ID, giá trị hay lệnh xung đột, dừng trước khi nhập; không ghi đè số đo/lệnh đang có.
- Chèn các bản ghi còn thiếu và tăng counter trong cùng transaction. Lỗi giữa chừng sẽ rollback; chạy lại bản chuyển khớp không tạo trùng. Counter chỉ tăng, không giảm.
- Đối chiếu từng bản ghi, số lượng, counter, dữ liệu dashboard và lịch sử GPS; kiểm tra đăng nhập và đọc `/api/status` qua ứng dụng Flask dùng MongoDB. Không gửi bản tin giả vào database thật.
- Đọc lại SQLite và xác nhận nội dung chưa thay đổi trong lúc chuyển. Kiểm tra file cấu hình web cũng chưa bị sửa.
- Sau khi mọi bước đạt, ghi `DATABASE_BACKEND: mongodb` vào `config.local.json` bằng thay thế file tạm. Mật khẩu/khóa và các trường cấu hình khác được giữ nguyên. URI tiếp tục nằm trong cấu hình riêng được Git bỏ qua.

Nguồn SQLite và firmware được giữ lại. ESP32 tiếp tục gửi cùng API HTTPS, không kết nối trực tiếp đến Atlas.

## Chạy lại và xử lý lỗi

Khi chưa bật MongoDB, có thể chạy lại `Chuyen-sang-MongoDB.cmd` sau khi sửa lỗi mạng/quyền truy cập. Các bản ghi đã nhập khớp sẽ được giữ và không nhân đôi. Nếu báo xung đột, kiểm tra trước khi sửa dữ liệu; công cụ không tự xóa database hay ghi đè để ép chuyển.

Khi MongoDB đã được bật, chạy lại launcher chỉ kiểm tra backend đang hoạt động, không nhập lại bản SQLite cũ. Dữ liệu mới tiếp tục được lưu ở Atlas.

SQLite lưu lịch sử đến thời điểm chuyển; các số đo nhận sau đó chỉ nằm trên Atlas. Nếu cần quay lại SQLite, dừng web, giữ/sao lưu dữ liệu mới trên Atlas và đối chiếu trước khi đổi `DATABASE_BACKEND` về `sqlite`. Không coi bản SQLite cũ là bản sao của các số đo nhận sau chuyển đổi. Cấu hình nguyên bản và database trước chuyển nằm trong đường dẫn `backup` của báo cáo.

## Kết quả và chốt mốc

- `.runtime/migration.log`: tiến trình kiểm tra và chuyển đổi.
- `.runtime/migration-check.json`: 10 kiểm thử chuyển đổi trên Atlas tạm.
- `.runtime/migration-report.json`: số bản ghi, checksum nội dung nguồn, counter, đường dẫn sao lưu và trạng thái `mongodb_enabled` khi thành công.
- `.runtime/mongodb-active-check.json`: kết quả kiểm tra backend sau chuyển đổi.

Để chỉ thử việc chuyển đổi trên database tạm, dùng `Kiem-tra-chuyen-du-lieu.cmd`; lệnh này không đổi backend hay dữ liệu ứng dụng.

Sau khi kiểm tra giao diện, chạy `Kiem-tra.cmd` và `.venv\Scripts\python.exe -m scripts.check_active_mongodb` để xác nhận backend cùng các số đo đã chuyển còn nguyên, rồi commit/push bằng Git. Kiểm tra sau chuyển cho phép có số đo mới và lệnh đã thay đổi theo hoạt động thật.

Phần lõi nằm trong `backend/app/migrations/sqlite_to_mongodb.py`. Công cụ điều phối, sao lưu và đổi cấu hình nằm trong `scripts/migrate_mongodb.py`; migration không tự chạy lúc khởi động web.
