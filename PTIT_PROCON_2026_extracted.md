# PTIT PROCON 2026 — Thông tin trích xuất từ ảnh

> Nguồn: ảnh chụp màn hình trang **PTIT PROCON 2026** của đội **Mer**.

## 1. Hồ sơ đội

| Trường | Thông tin |
|---|---|
| Tên đội | Mer |
| Học viện | Học viện Công nghệ Bưu chính Viễn thông |
| Số thành viên | 1 |
| Đội trưởng | Nguyễn Vinh Hiển |
| Email | hien1972003@gmail.com |
| Số trận có kết quả | 2 |
| Vô địch | 0 |
| Tổng phản đòn | 0 |
| Tổng loại | 0 |
| Hạng trung bình | 2.00 |

## 2. Kiểm tra bot trước trận

- Trận nhập: `m-32742`
- Token của bot: `m-32742-a-b32726021325`
- Lệnh HTTP hiển thị:
  ```text
  sample-bot -transport http -url https://procon.ptit.edu.vn -match m-32742 -token m-32742-a-b32726021325
  ```
- Các bước kiểm tra:
  1. Bot kết nối & gửi dữ liệu.
  2. Gán loại xe đúng định dạng.
  3. Kế hoạch ngày hợp lệ.
  4. Phản hồi kịp hạn của bản hợp lệ để đo.

## 3. Tìm đối thủ thật (đối với đội)

- Mục đích: đổi khách thay vì bot.
- Yêu cầu: trúng đúng câu hình khi đấu.
- Sau khi ghép xong, hai đội thi đấu trong danh sách.

## 4. Luyện tập với máy

| Thiết lập | Giá trị |
|---|---|
| Độ khó | Khó |
| Số bot đối thủ | 1 |
| Số ngày | 4 |
| Cơ bản đồ | Nhỏ 8×8 |
| Chế độ | Nâng cao |
| Bước/ngày | 30 |
| FPS (ms/ngày) | 5000 |
| Xe/đội | 4 |
| Số quân úp | 0 |
| Số quân ẩn | 4 |
| Mức nhiên liệu | Vừa (2×) |

### Bot luyện tập

- Trận luyện tập: `m-32743`
- Có thể kết nối bằng HTTP hoặc WebSocket.
- Trận bot đã sẵn sàng và bắt đầu ngay khi bot của đội kết nối.
- Thời gian chờ hiển thị: khoảng 5 phút.

## 5. Token API của đội

- Token mặc định: `bot-34d7632cb475ab0680eac8`
- Có thể tạo nhiều token (mỗi máy/bot một token).
- Token được dùng trong header:
  ```text
  Authorization: Bearer <token>
  ```
- Tên token mới: không bắt buộc.
- Có tùy chọn tạo token mới.

### Lệnh mẫu

```text
# HTTP
sample-bot -transport http -url https://procon.ptit.edu.vn -match <MATCH_ID> -token <TOKEN>

# WS
sample-bot -transport ws -url https://procon.ptit.edu.vn -match <MATCH_ID> -token bot-34d7632cb475ab0680eac8
```

## 6. Các trận của đội

| Trận | Đội | Trạng thái | Xem lại | Bản nộp | Token riêng trận | Kết quả |
|---|---|---|---|---|---|---|
| `m-32743` | team-A | setup | — | — | `m-32743-a-40a5bb67eff9` | đang chờ |
| `m-32742` | team-A | setup | — | — | `m-32742-a-b32726021325` | đang chờ |
| `m-1531` | team-A | done | Có | Có | `m-1531-a-9db1bbd1b61a` | #2 · 0 loại · 0 phản |
| `m-0959` | team-A | done | Có | Có | `m-0959-a-e653d38ad213` | #2 · 0 loại · 0 phản |

## 7. Ghi chú

- Ảnh có chứa các **API token/secret** của đội. Không nên công khai các token này trong repository, báo cáo công khai hoặc chat nhóm không cần thiết.
- Một số ký tự nhỏ trong ảnh có thể bị OCR nhận dạng chưa hoàn toàn chính xác; các giá trị token nên được đối chiếu trực tiếp với giao diện trước khi sử dụng.
