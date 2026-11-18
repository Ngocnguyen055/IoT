# Frontend và điều hướng Trang chủ/Lịch sử

## Cấu trúc và cách chạy

```text
frontend/
  templates/
    base.html                    Khung HTML, CSS chung và các block Jinja
    app_layout.html              Thanh điều hướng và khung trang sau đăng nhập
    index.html                   Trang chủ, số đo trực tiếp và 8 sự kiện mới nhất
    history.html                 Bảng lịch sử, 20 sự kiện mỗi trang
    login.html                   Đăng nhập
  static/
    css/style.css                CSS đã định dạng lại, giữ nguyên các quy tắc
    js/
      app.js                     Ghép các thành phần và khởi động dashboard
      api.js                     HTTP, cookie, lỗi và chuyển về đăng nhập khi 401
      dashboard.js               Số đo, trạng thái kết nối, LOCATE và polling
      alerts.js                  Danh sách cảnh báo
      event-location.js          Chọn sự kiện, đọc liên kết lịch sử và hiển thị vị trí đã lưu
      history.js                 Bảng lịch sử và điều khiển phân trang cursor
      location.js                Vị trí GPS cuối, Google Maps và sao chép tọa độ
      map.js                     Leaflet, marker và chia đoạn hành trình
      basemap.js                 Nguồn ảnh nền, đổi nguồn, tải lại và báo lỗi ảnh
      tracking.js                Khoảng lịch sử, ẩn/hiện đường đi và tải điểm GPS
      format.js                  Hiển thị null/0, thời gian và tọa độ hợp lệ
      config.js                  Mốc polling, ngoại tuyến và khoảng cách thời gian
    app.js                       Loader tương thích với URL script cũ
    style.css                    URL CSS cũ chuyển đến CSS mới
  package.json                   Đánh dấu ES module cho kiểm thử Node.js
```

Trình duyệt nạp ES module trực tiếp. Tiếp tục chạy bằng `Chay-web.cmd`, cùng Flask và cùng origin API. Không có bước npm install hoặc build để chạy web. Node.js chỉ phục vụ các kiểm thử JavaScript; máy cải tổ dùng Node.js 24.14.0.

Factory Flask đã chuyển đường dẫn tài nguyên đến `frontend/templates/` và `frontend/static/`. Các API cũ vẫn được giữ. Trang chủ dùng `/api/dashboard` với phản hồi gọn, trang Lịch sử dùng `/api/alerts`. Các URL `/static/app.js` và `/static/style.css` vẫn có loader tương thích cho HTML cũ trong cache.

## Hành vi được giữ

- Polling status mỗi 5 giây; dữ liệu cũ hơn 90 giây báo có thể ngoại tuyến.
- Chỉ số thiếu hiển thị dấu gạch; số 0 vẫn là 0.
- Tên và thứ tự sự kiện, lệnh LOCATE và trạng thái chờ giữ nguyên.
- Dùng vị trí hợp lệ gần nhất; bản tin mới thiếu GPS không xóa vị trí cũ.
- Vị trí trong 300 giây được đánh dấu mới; Google Maps, sao chép tọa độ và về vị trí hiện tại tiếp tục hoạt động.
- Các khoảng lịch sử 1/6/24/72 giờ; mốc ban đầu 24 giờ; đường đi ngắt khi khoảng cách thời gian lớn hơn 120 giây.
- Giữ bộ lọc ẩn/hiện đường đi, điểm bắt đầu và thông báo giới hạn 1000 điểm.

## Các trường hợp được làm rõ khi tách mã

- Yêu cầu status đang chạy được dùng chung khi polling trùng thời điểm.
- Lịch sử GPS tải chậm không giữ lại việc hiển thị nhịp tim/SOS mới.
- Yêu cầu lịch sử cùng lựa chọn được dùng chung khi đang chờ; khi đổi lựa chọn, phản hồi cũ đến muộn không ghi đè lựa chọn mới.
- API trả 401 sẽ chuyển về đăng nhập, áp dụng cho cả status, tracking và LOCATE.
- Trang Lịch sử chỉ đọc API khi mở trang, bấm Trước/Sau hoặc Về mới nhất; không polling. Mỗi trang có tối đa 20 sự kiện. Snapshot ID giữ mốc đang xem khi có sự kiện mới được thêm; xem [chi tiết phân trang](alert-history.md).
- Khi lịch sử đang tải, các nút tạm khóa để tránh gửi yêu cầu trùng. Lỗi mạng giữ nguyên bảng/trang cũ và cho phép thử lại. Nội dung từ API được gán bằng `textContent`.
- Khi thư viện bản đồ không tải được, số đo/cảnh báo và tọa độ vẫn hoạt động; khung bản đồ hiển thị thông báo ngắn.
- Tọa độ null không bị chuyển thành vị trí 0,0; tọa độ 0,0 thật vẫn được chấp nhận.
- Bấm cảnh báo mở vị trí đã lưu của sự kiện; Lịch sử có liên kết về Trang chủ theo ID. Điểm sự kiện màu cam độc lập với ghim GPS mới nhất và đường đi. Thiếu GPS được thông báo rõ, không thay bằng tọa độ hiện tại. Khi đổi lựa chọn hoặc đóng khung, phản hồi đọc sự kiện cũ đến muộn không mở lại/ghi đè lựa chọn mới. Chi tiết ở [vị trí sự kiện](alert-history.md#xem-vị-trí-của-một-sự-kiện).

## Kiểm tra

`Kiem-tra.cmd` chạy kiểm thử Python, kiểm thử JavaScript bằng Node.js và kiểm tra các file dự kiến đưa vào Git.

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.venv\Scripts\python.exe scripts\check_frontend.py
```

Kiểm thử JavaScript không dùng thư viện ngoài: chạy các module thật với fixture DOM/Leaflet và API giả. Chúng kiểm tra render số đo/SOS, polling, LOCATE, GPS, clipboard, lịch sử và phản hồi mạng sai thứ tự. Kiểm thử Python kiểm tra Jinja đã render, các URL cũ và toàn bộ đồ thị import module qua Flask, gồm MIME JavaScript/CSS.

Ở giai đoạn 3 đã đối chiếu DOM/CSS với bản trước khi tách mã. Sau đó giao diện được bổ sung sidebar và trang lịch sử; các kiểm thử tài nguyên kiểm tra cả hai trang, trạng thái điều hướng và toàn bộ đồ thị import module.

Chrome headless không khởi động được trong môi trường thực thi do lỗi GPU/process access. Chủ dự án đã mở lại web, đăng nhập và xác nhận giao diện hiển thị bình thường trên trình duyệt thật. Chưa có ảnh kiểm tra tự động; kiểm thử fixture Leaflet không thay thế việc thử bản đồ thực tế với tọa độ thiết bị khi có mạng.

Sau khi đổi thư mục tài nguyên, dừng tiến trình web cũ bằng Ctrl+C rồi mở lại `Chay-web.cmd` để nạp factory mới.

## Xử lý nền bản đồ trống hoặc mờ

Ngày 18/11/2026, chủ dự án thử ảnh mẫu và xác nhận nguồn `tile.openstreetmap.org` không hiện, còn `tile.openstreetmap.de` hiện được trên cùng máy. Chưa có mã HTTP/lỗi trình duyệt để phân biệt nguyên nhân DNS, kết nối hoặc chặn truy cập. Không kết luận đây là lỗi GPS hoặc MongoDB.

`basemap.js` dùng nguồn dự phòng `.de` làm mặc định (zoom tối đa 18); nguồn chính `.org` dùng URL chuẩn, zoom tối đa 19. Cả hai có attribution hiển thị và chỉ tải các ảnh phục vụ khung nhìn. Chọn **Nền bản đồ** để đổi, hoặc **Tải lại bản đồ** để thử lại. Đổi nguồn/tải lại chỉ tác động lớp nền, không xóa ghim GPS, đường hành trình hoặc dữ liệu đã lưu. Không thêm vòng lặp tự thử lại, proxy ảnh hay tham số phá cache.

Khi ảnh bị lỗi, dòng trạng thái thông báo rõ; sự kiện hoàn tất lượt tải không được xóa lỗi của ảnh vẫn còn thiếu. Khi thư viện Leaflet không tải được, có thông báo riêng và khóa hai điều khiển nền. `ResizeObserver` gọi `invalidateSize` khi khung bản đồ đổi kích thước, đồng thời giữ vị trí nhìn; zoom giới hạn theo nguồn để tránh phóng ảnh quá mức chi tiết được cung cấp.

Kiểm tra thay đổi này: 27 kiểm thử JavaScript (gồm đổi nền, giữ lỗi ảnh, tải lại, giữ marker/hành trình và resize) cùng 3 kiểm thử tài nguyên HTML/import của Flask đã đạt. Chủ dự án đã khởi động lại web, tải lại trang và xác nhận nguồn dự phòng hiển thị rõ đường phố, phóng to/thu nhỏ ổn định trên trình duyệt thật ngày 18/11/2026. Việc thử này xác nhận nền bản đồ; thử hành trình bằng GPS thiết bị ngoài trời vẫn là bước riêng đã hẹn trước.

Nguồn kỹ thuật: [Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html), [OpenStreetMap tile policy và URL chính thức](https://operations.osmfoundation.org/policies/tiles/), [máy chủ nền dự phòng](https://tile.openstreetmap.de/), [định nghĩa OpenStreetMap.DE của leaflet-providers](https://github.com/leaflet-extras/leaflet-providers/blob/master/leaflet-providers.js).
