# Mốc trước cải tổ và sao lưu

## Mốc đã ghi nhận

- Chủ dự án xác nhận hệ thống đã nhận đủ số đo, pin và sự kiện SOS trước khi cải tổ.
- Commit trước cải tổ: `1fc3c32` (`first commit`), tại repo `Ngocnguyen055/IoT`.
- Sao lưu trước lần lỗi môi trường: `.runtime/backups/phase1-20261117-015308/`.
- Sao lưu lại sau khi khôi phục quyền owner `.git`: `.runtime/backups/phase1-resume-20261117-021656/`.
- Cả hai bản sao lưu SQLite đã kiểm tra integrity đạt và có 312 bản ghi tại thời điểm sao lưu. Chúng ở trên máy, được Git bỏ qua.

Mỗi bản gồm thư mục `files/` chứa mã/cấu hình, file database riêng và manifest. Cấu hình riêng có chứa khóa thực tế; giữ các bản sao lưu cùng dữ liệu trên máy của chủ dự án.

## Tạo bản sao lưu mới

Tại thư mục dự án:

```powershell
.venv\Scripts\python.exe scripts\backup_project.py
```

Script tạo thư mục mới trong `.runtime/backups/`, sao chép mã và cấu hình riêng, dùng SQLite backup API để tạo database nhất quán và kiểm tra integrity. Manifest ghi mã commit nếu đọc được, SHA-256 của file, số dòng readings/commands và thời điểm UTC. Thư viện, runtime, Git metadata và log được bỏ qua.

## Khôi phục khi cần

1. Dừng web và tunnel bằng Ctrl+C ở hai cửa sổ đang chạy.
2. Sao lưu trạng thái hiện tại trước khi khôi phục, bằng script trên hoặc chép ra thư mục dự phòng.
3. Chọn đúng snapshot. Chép các file cần khôi phục từ `snapshot/files/` về đúng đường dẫn tương đối trong dự án; chép `snapshot/iot_ngoc.sqlite3` về thư mục gốc nếu cần phục hồi dữ liệu.
4. Khôi phục `config.local.json` cùng phiên bản khóa phù hợp với thiết bị. Snapshot cũ có thể chứa cấu hình trực tiếp trong `.ino`; snapshot mới dùng `device_config.local.h`.
5. Chạy kiểm thử phần mềm, rồi mở web. Nếu tạo tunnel mới, chuẩn bị và nạp lại firmware bằng quy trình thông thường.

Việc quay về commit Git chỉ phục hồi mã được theo dõi; cấu hình riêng, header riêng và database được phục hồi từ snapshot. Cần có cả hai để tái tạo đầy đủ trạng thái chạy.

## Phạm vi giai đoạn 1

- Mật khẩu/khóa hiện có trên máy được giữ nguyên; chỉ chuyển chỗ đọc vào cấu hình riêng.
- Các hằng cấu hình firmware được chuyển sang header local, giữ nguyên giá trị ID/khóa/URL tại thời điểm tách.
- Thuật toán cảm biến, ngưỡng cảnh báo, giao diện, API và cơ sở dữ liệu thật giữ nguyên hành vi.
- Kiểm thử API dùng SQLite tạm; kiểm tra firmware chỉ biên dịch object, không flash thiết bị.
- Việc tách khóa trong bản hiện tại không sửa lịch sử Git đã được chủ dự án tự push. Không tự đổi khóa hoặc viết lại lịch sử trong giai đoạn này.
