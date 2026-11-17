# Hợp đồng API — mốc giai đoạn 1

Ghi nhận hành vi của commit `1fc3c32`, ngày 17/11/2026. Dùng làm chuẩn khi tách backend và thay cơ sở dữ liệu. API giữ cùng origin với trang web; firmware chỉ gọi hai endpoint `/api/device/*`.

## Xác thực và trang web

| Yêu cầu | Hành vi hiện tại |
|---|---|
| `GET /login` | HTML đăng nhập, HTTP 200 |
| `POST /login` | Form field `password`; đúng: tạo session admin và redirect `/` (302); sai: HTML lỗi, 401 |
| `POST /logout` | Xóa session và redirect `/login` (302) |
| `GET /` | Có session: dashboard HTML 200; chưa đăng nhập: redirect `/login` |
| API dành cho admin | Thiếu session: 401, `{"error":"login required"}` |
| API dành cho thiết bị | Header `X-Device-Key`; sai/thiếu: 401, `{"error":"device unauthorized"}` |

## `POST /api/device/telemetry`

Thiết bị gửi JSON object, dùng xác thực bằng khóa thiết bị. Ví dụ dữ liệu hoàn toàn giả để mô tả cấu trúc:

```json
{
  "device_id": "ngoc-01",
  "event": "button",
  "lat": null,
  "lon": null,
  "gps_satellites": 0,
  "bpm": 72,
  "spo2": 98,
  "battery_pct": 80.4,
  "battery_voltage": 4.004,
  "current_ma": 0.6
}
```

| Trường | Hành vi/giới hạn hiện tại |
|---|---|
| `device_id` | Chuỗi sau khi chuyển kiểu; độ dài 1–64; thiếu bị từ chối |
| `event` | `telemetry` (mặc định), `button`, `high_bpm`, `low_spo2`, `remote` |
| `lat`, `lon` | Cùng có giá trị hoặc cùng null; vĩ độ −90…90, kinh độ −180…180 |
| `gps_satellites` | 0…100 |
| `bpm` | 0…300 |
| `spo2`, `battery_pct` | 0…100 |
| `battery_voltage` | 0…100 V; đây là giới hạn API hiện tại, không phải thang pin LiPo |
| `current_ma` | −10000…10000 mA |

Các chỉ số không gửi hoặc gửi null được lưu thành null; số 0 được giữ nguyên. Hiện API chuyển chuỗi số hợp lệ thành số. NaN/Infinity và giá trị ngoài giới hạn bị từ chối. Trường lạ được bỏ qua.

- Thành công: HTTP 200, `{"ok":true}`.
- JSON sai dạng hoặc trường không hợp lệ: HTTP 400, `{"error":"..."}`.
- `ts` do backend gán bằng thời điểm nhận, đơn vị Unix giây; giá trị `ts` do thiết bị gửi không được dùng.
- ID số tăng dần do cơ sở dữ liệu cấp.
- `event=remote` được lưu thành công sẽ đưa lệnh của thiết bị đó về `NONE` trong cùng transaction.

## `GET /api/device/command?device_id=ngoc-01`

Dùng khóa thiết bị. HTTP 200, `Content-Type: text/plain`, thân phản hồi là chính xác `NONE` hoặc `LOCATE`.

Lệnh chưa có trả `NONE`. Việc đọc lệnh không xóa lệnh; backend tiếp tục trả `LOCATE` cho đến khi nhận thành công bản tin `event=remote` của cùng thiết bị. Thiết bị có thể gửi bản tin định kỳ trong lúc lệnh vẫn chờ.

## `POST /api/command`

Dùng session admin. JSON:

```json
{"device_id":"ngoc-01","command":"LOCATE"}
```

`device_id` mặc định là `ngoc-01`, dài 1–64 ký tự sau chuyển kiểu. Hiện chỉ hỗ trợ `LOCATE`. Gọi lặp sẽ cập nhật một dòng lệnh của cùng thiết bị.

- Thành công: 200, `{"ok":true,"message":"Đã xếp lệnh; chờ thiết bị kết nối"}`.
- Lệnh hoặc ID không hợp lệ: 400, `{"error":"..."}`.

## `GET /api/status`

Dùng session admin. JSON chứa:

- `latest`: số đo có ID lớn nhất, hoặc null.
- `history`: tối đa 150 số đo, ID giảm dần.
- `last_location`: vị trí hợp lệ gần nhất theo ID, gồm `device_id`, `lat`, `lon`, `ts`; có thể cũ hơn phạm vi `history`, hoặc null.
- `alerts`: tối đa 20 dòng có `event != telemetry`, ID giảm dần.
- `commands`: các dòng `device_id`, `cmd` đang lưu, gồm cả `NONE`.
- `now`: Unix giây của backend.

Một dòng số đo có các trường `id`, `device_id`, `ts`, `event`, `lat`, `lon`, `gps_satellites`, `bpm`, `spo2`, `battery_pct`, `battery_voltage`, `current_ma`.

Endpoint này hiện tổng hợp tất cả thiết bị; không có bộ lọc `device_id`. Frontend tải lại mỗi 5 giây và coi bản tin cũ hơn 90 giây là có thể ngoại tuyến. Mốc này là hành vi giao diện, không phải phản hồi lỗi của API.

## `GET /api/track?device_id=ngoc-01&hours=24`

Dùng session admin. `device_id` mặc định `ngoc-01`, dài 1–64; `hours` là số nguyên 1–168, mặc định 24. Sai tham số trả HTTP 400.

HTTP 200:

```json
{"device_id":"ngoc-01","hours":24,"points":[]}
```

Chỉ lấy các dòng có đủ lat/lon, đúng thiết bị, `ts >= now - hours*3600`. Lấy tối đa 1000 dòng có ID lớn nhất rồi trả theo ID tăng dần. Mỗi điểm gồm `id`, `ts`, `lat`, `lon`, `gps_satellites`, `event`. Không có GPS trả mảng rỗng.

## Lưu ý cho giai đoạn sau

- API hiện tập trung một thiết bị; cần thiết kế bộ lọc status khi mở rộng nhiều thiết bị.
- Một số dạng JSON bất thường chưa được xử lý đầy đủ: ví dụ JSON list không rỗng ở `/api/command`, hoặc `event` là list/object. Cần bổ sung kiểm tra kiểu ở giai đoạn backend, kèm kiểm thử và ghi nhận thay đổi lỗi 500 → 400.
- Lệnh chưa có ID/ack riêng; quy tắc hiện tại là bản tin `remote` thành công xóa lệnh đang chờ.
- Khi chuyển MongoDB cần giữ ID/thứ tự, Unix giây, null, số 0, đơn vị và các phản hồi xác thực/lệnh ở trên.
