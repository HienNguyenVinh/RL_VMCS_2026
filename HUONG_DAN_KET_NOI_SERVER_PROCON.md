# Hướng dẫn kết nối server và xem trận đấu — PTIT PROCON 2026

Tài liệu này hướng dẫn cách:

1. Lấy **API token** của đội.
2. Tạo hoặc tìm một trận để test.
3. Kết nối bot với server bằng **HTTP polling**.
4. Kết nối bằng **WebSocket**.
5. Gửi loại tác nhân và kế hoạch di chuyển.
6. Theo dõi / xem trận đấu của đội trên giao diện web.
7. Xử lý một số lỗi kết nối thường gặp.

> Base URL theo tài liệu của PROCON:
>
> `https://procon.ptit.edu.vn`

---

## 1. Các thông tin cần có

Bot cần tối thiểu:

```text
BASE_URL = https://procon.ptit.edu.vn
MATCH_ID = ID của trận đấu
TOKEN    = API token của đội
```

Không ghi token thật trực tiếp vào source code nếu source được đưa lên Git/GitHub.

Nên sử dụng biến môi trường:

```bash
export PROCON_TOKEN="your_token_here"
export PROCON_MATCH_ID="your_match_id_here"
```

Windows PowerShell:

```powershell
$env:PROCON_TOKEN="your_token_here"
$env:PROCON_MATCH_ID="your_match_id_here"
```

---

# 2. Lấy API token của đội

Trên trang PTIT PROCON:

1. Đăng nhập tài khoản của đội.
2. Mở tab **Trận của tôi**.
3. Kéo xuống mục **Token API của đội (dùng chung mọi trận)**.
4. Chọn một token đã có hoặc tạo token mới.
5. Sao chép token và lưu lại để bot sử dụng.

Server sử dụng token theo HTTP header:

```http
Authorization: Bearer <token>
```

Ví dụ:

```http
Authorization: Bearer bot-xxxxxxxxxxxxxxxx
```

> Một đội có thể tạo nhiều token, ví dụ mỗi máy hoặc mỗi bot dùng một token riêng và có thể thu hồi riêng khi cần.

---

# 3. Tạo một trận để test

Trong tab **Trận của tôi**, có ba cách phù hợp để test bot.

## Cách A — Kiểm tra bot trước trận

Chọn:

**Kiểm tra bot trước trận → Bắt đầu kiểm tra**

Mục đích là chạy một trận nháp nhỏ với thời gian phản hồi giống trận thật để kiểm tra:

- token;
- giao thức API;
- tốc độ bot;
- format request/response.

Đây là lựa chọn nên dùng đầu tiên khi mới viết bot.

---

## Cách B — Luyện tập với máy

Trong phần **Luyện tập với máy**:

1. Chọn độ khó.
2. Chọn số bot đối thủ.
3. Chọn số ngày.
4. Chọn cỡ bản đồ.
5. Nếu cần, mở phần **Nâng cao** để chỉnh:
   - bước/ngày;
   - thời gian phản hồi;
   - số xe/đội;
   - số quán udon;
   - số chuỗi udon;
   - mức nhiên liệu.
6. Nhấn **Tạo trận luyện tập**.

Sau khi tạo, trận sẽ xuất hiện trong danh sách trận của đội.

---

## Cách C — Đấu với đội khác

Chọn:

**Tìm đối thủ thật**

Sau khi ghép thành công, cả hai đội sẽ thấy trận trong danh sách bên dưới của trang **Trận của tôi**.

---

# 4. Xem trận đấu của mình trên website

Cách đơn giản nhất để theo dõi trận:

1. Mở `https://procon.ptit.edu.vn`.
2. Đăng nhập.
3. Chọn tab **Trận của tôi**.
4. Tìm trận vừa tạo hoặc vừa được ghép.
5. Chọn trận trong danh sách để mở giao diện theo dõi trận.
6. Trong lúc bot đang chạy, có thể giữ trang trận mở để quan sát trạng thái theo từng ngày.
7. Khi trận kết thúc, xem kết quả của trận tại cùng khu vực trận đấu.

Nếu đang debug bot, nên mở đồng thời:

```text
Terminal chạy bot
        +
Trình duyệt mở trận đấu
```

để đối chiếu action bot gửi lên với trạng thái hiển thị trên server.

---

# 5. Hai cách kết nối bot

PROCON cung cấp hai cách kết nối:

| Cách | Endpoint | Đặc điểm |
|---|---|---|
| HTTP polling | `/api/v1/matches/{id}/...` | Đơn giản nhất, chủ động gọi API |
| WebSocket | `/ws/v1/matches/{id}?token=...` | Server đẩy state, bot giữ kết nối |

Khi mới triển khai, nên bắt đầu bằng **HTTP polling**.

---

# 6. HTTP polling

Base API của một trận:

```text
https://procon.ptit.edu.vn/api/v1/matches/{MATCH_ID}
```

Header:

```http
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

Các endpoint theo tài liệu:

| Thao tác | Method | Endpoint |
|---|---:|---|
| Lấy cấu hình | GET | `/api/v1/matches/{id}/setup` |
| Gán loại tác nhân | POST | `/api/v1/matches/{id}/assignment` |
| Chờ bắt đầu | GET | `/api/v1/matches/{id}/start` |
| Lấy state ngày | GET | `/api/v1/matches/{id}/state` |
| Gửi hành động | POST | `/api/v1/matches/{id}/actions` |
| Lấy kết quả | GET | `/api/v1/matches/{id}/result` |

---

# 7. Test kết nối nhanh bằng curl

Đặt:

```bash
BASE="https://procon.ptit.edu.vn"
MATCH_ID="your_match_id"
TOKEN="your_token"
```

## Lấy setup

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/matches/$MATCH_ID/setup"
```

Nếu token và `MATCH_ID` đúng, server sẽ trả về JSON cấu hình trận.

---

## Lấy state hiện tại

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/matches/$MATCH_ID/state"
```

---

## Lấy kết quả

```bash
curl \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/matches/$MATCH_ID/result"
```

---

# 8. Python client tối thiểu

Có thể bắt đầu bằng thư viện chuẩn của Python, không cần cài `requests`.

Tạo file:

```text
connection_test.py
```

```python
import json
import os
import urllib.request
import urllib.error

BASE = "https://procon.ptit.edu.vn"
MATCH_ID = os.environ["PROCON_MATCH_ID"]
TOKEN = os.environ["PROCON_TOKEN"]

API = f"{BASE}/api/v1/matches/{MATCH_ID}"


def call(method, path, body=None):
    data = None

    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            raw = response.read()

            if not raw:
                return None

            return json.loads(raw)

    except urllib.error.HTTPError as e:
        print("HTTP error:", e.code)
        print(e.read().decode("utf-8", errors="replace"))
        raise


setup = call("GET", "/setup")

print(json.dumps(setup, indent=2, ensure_ascii=False))
```

Chạy:

```bash
python connection_test.py
```

Nếu in được JSON của `setup`, bot đã kết nối được với server.

---

# 9. Dữ liệu `setup`

Theo tài liệu challenge, khi lấy setup cần chú ý các trường như:

```text
daySteps
map
cells
spots
agents
fuelLimits
```

Trong đó bản đồ được biểu diễn dạng lưới phẳng.

Nếu:

```text
width = W
row   = r
col   = c
```

thì chỉ số cell được tính:

```text
index = r * W + c
```

Không nên giả định `cells` đã được server cung cấp dưới dạng danh sách hàng/cột 2 chiều.

---

# 10. Gán loại tác nhân

Sau khi nhận setup, đội gửi loại cho các agent.

Theo tài liệu:

```text
0 = xe tuần tra
1 = xe tiếp nhiên liệu
```

Ví dụ có 4 agent:

```json
[0, 0, 1, 1]
```

Gửi:

```python
assignment = [0, 0, 1, 1]

call(
    "POST",
    "/assignment",
    assignment
)
```

> Số lượng phần tử phải khớp số agent của trận.

Loại agent được chọn ở đầu trận và sau đó không đổi.

---

# 11. Chờ trận bắt đầu

Có thể gọi:

```python
call("GET", "/start")
```

Tài liệu lưu ý endpoint `/start` có thể trả:

```text
HTTP 425
```

khi trận **chưa tới giờ / chưa bắt đầu**.

Trong trường hợp này, đợi rồi thử lại thay vì coi đó là lỗi logic của bot.

Ví dụ:

```python
import time
import urllib.error

while True:
    try:
        start_data = call("GET", "/start")
        print("Match started")
        break

    except urllib.error.HTTPError as e:
        if e.code == 425:
            time.sleep(0.5)
            continue

        raise
```

---

# 12. Nhận state của từng ngày

Trong vòng lặp trận:

```python
state = call("GET", "/state")
```

State ngày có thể chứa thông tin như:

```text
day
agents
others
traffics
```

Agent có các dữ liệu cần thiết để ra quyết định như:

```text
kind
pos
fuel
```

Bot sử dụng state này để:

1. cập nhật môi trường;
2. chạy thuật toán phân công;
3. chạy planner;
4. tạo action cho từng agent;
5. gửi kế hoạch lên server.

---

# 13. Format kế hoạch di chuyển

Mỗi ngày bot gửi một **mảng của các mảng**.

Mỗi agent có một chuỗi action.

Direction theo tài liệu:

```text
0 = trên-trái
1 = trên-phải
2 = phải
3 = dưới-phải
4 = dưới-trái
5 = trái
```

Ngoài ra:

```text
-1 = đứng yên trong 1 bước
```

Ví dụ:

```json
[
  [-1, 5],
  [0, 1, -1]
]
```

Ý nghĩa:

```text
Agent 0:
    đứng yên 1 bước
    sau đó đi hướng 5

Agent 1:
    đi hướng 0
    đi hướng 1
    đứng yên 1 bước
```

Tổng số bước của kế hoạch cho một agent không được vượt quá `daySteps`.

Nếu thiếu bước có thể bổ sung `-1` để agent đứng yên.

---

# 14. Gửi action

Ví dụ:

```python
actions = [
    [-1, 5],
    [0, 1, -1],
]

result = call(
    "POST",
    "/actions",
    actions
)

print(result)
```

Nếu trận có 4 agent thì phải gửi kế hoạch tương ứng cho đủ các agent của đội theo format mà server yêu cầu.

---

# 15. Vòng lặp bot cơ bản

Cấu trúc tối thiểu:

```python
setup = call("GET", "/setup")

assignment = choose_agent_types(setup)

call(
    "POST",
    "/assignment",
    assignment
)

wait_until_start()

while True:

    state = call("GET", "/state")

    actions = plan_actions(
        setup,
        state
    )

    action_result = call(
        "POST",
        "/actions",
        actions
    )

    if match_finished(action_result):
        break

result = call("GET", "/result")
```

Với project DP + MARL của nhóm, phần:

```python
actions = plan_actions(setup, state)
```

có thể triển khai thành:

```text
state
  │
  ▼
Multi-Agent RL
  │
  ├─ Agent 0 → Target A
  ├─ Agent 1 → Target B
  └─ Agent 2 → Refuel task
  │
  ▼
Dynamic Programming / route planner
  │
  ▼
direction 0..5
  │
  ▼
POST /actions
```

---

# 16. Không poll server quá nhanh

Theo tài liệu:

```text
poll >= 200 ms
```

Nếu gửi request quá nhanh có thể nhận:

```text
HTTP 429
```

Do đó nên có khoảng nghỉ giữa các lần polling:

```python
import time

time.sleep(0.2)
```

Có thể dùng lớn hơn một chút, ví dụ:

```python
time.sleep(0.25)
```

để tránh chạm rate limit do sai số thời gian.

Khi nhận `HTTP 429`, chờ rồi thử lại.

---

# 17. WebSocket

WebSocket có dạng được tài liệu mô tả:

```text
ws://.../ws/v1/matches/{id}?token=<token>
```

Phía server đẩy các frame theo thứ tự logic:

```text
setup
  ↓
bot gửi loại agent
  ↓
day_state
  ↓
bot gửi kế hoạch
  ↓
day_state
  ↓
bot gửi kế hoạch
  ↓
...
  ↓
result
```

Mỗi frame là một JSON message.

Tài liệu lưu ý message **không có trường `type` để phân biệt**, vì vậy client cần theo dõi đang ở giai đoạn nào của protocol để giải mã đúng message.

Với project đầu tiên, HTTP polling dễ debug hơn. Chỉ nên chuyển sang WebSocket khi phiên bản HTTP đã chạy ổn định.

---

# 18. Luồng debug khuyến nghị

Khi bot chưa chạy được, kiểm tra lần lượt:

```text
[1] Login website được?
        ↓
[2] Có API token?
        ↓
[3] Có trận trong "Trận của tôi"?
        ↓
[4] Có MATCH_ID đúng?
        ↓
[5] GET /setup trả JSON?
        ↓
[6] POST /assignment thành công?
        ↓
[7] /start đã qua trạng thái 425?
        ↓
[8] GET /state trả state?
        ↓
[9] Action có đúng format?
        ↓
[10] POST /actions thành công?
        ↓
[11] Theo dõi thay đổi trên giao diện trận
        ↓
[12] GET /result khi trận kết thúc
```

Không nên debug thuật toán RL trước khi các bước `[1] → [10]` hoạt động ổn định.

---

# 19. Một bot "smoke test" nên làm gì?

Trước khi tích hợp Dynamic Programming hoặc Multi-Agent RL, hãy viết một bot cực đơn giản.

Ví dụ:

```text
Mỗi ngày:
    tất cả agent đứng yên
```

Kế hoạch:

```python
actions = [
    [-1] * day_steps
    for _ in range(number_of_agents)
]
```

Mục đích không phải để thắng.

Mục đích là xác nhận toàn bộ pipeline:

```text
Token
→ setup
→ assignment
→ start
→ state
→ actions
→ result
```

chạy chính xác.

Sau đó mới thay `plan_actions()` bằng thuật toán thật.

---

# 20. Các lỗi thường gặp

## `401 Unauthorized`

Kiểm tra:

```text
Authorization: Bearer <token>
```

và token có còn hiệu lực hay không.

---

## `425`

Trận chưa bắt đầu hoặc chưa đến thời điểm có thể bắt đầu.

Chờ rồi thử lại.

---

## `429`

Bot polling quá nhanh.

Đảm bảo khoảng cách giữa các lần poll tối thiểu khoảng:

```text
200 ms
```

---

## Action bị từ chối

Kiểm tra:

- direction có thuộc `0..5` hoặc `-1`;
- số agent có đúng;
- tổng bước không vượt `daySteps`;
- action có đi qua ô không hợp lệ hay không;
- nhiên liệu có đủ hay không;
- JSON có đúng format hay không.

Một agent có kế hoạch sai có thể làm lượt bị từ chối, vì vậy nên validate action trước khi gửi.

---

# 21. Cấu trúc code nên dùng

```text
procon-bot/
│
├── main.py
│
├── config.py
│
├── client/
│   ├── http_client.py
│   └── websocket_client.py
│
├── env/
│   ├── map.py
│   ├── state.py
│   └── rules.py
│
├── planner/
│   ├── value_iteration.py
│   └── policy_iteration.py
│
├── marl/
│   ├── agent.py
│   └── task_allocator.py
│
├── strategy/
│   └── hybrid.py
│
└── tests/
    ├── test_connection.py
    ├── test_map.py
    └── test_actions.py
```

Trong giai đoạn đầu chỉ cần:

```text
main.py
client/http_client.py
tests/test_connection.py
```

Sau khi kết nối server ổn định mới thêm DP/MARL.

---

# 22. Checklist trước trận

```text
[ ] Login được PROCON
[ ] Có API token
[ ] Không commit token lên Git
[ ] Có MATCH_ID
[ ] GET /setup hoạt động
[ ] Assignment đúng số agent
[ ] Xử lý HTTP 425
[ ] Poll >= 200 ms
[ ] Xử lý HTTP 429
[ ] Parse /state thành công
[ ] Action chỉ chứa -1 hoặc 0..5
[ ] Mỗi plan không vượt daySteps
[ ] Validate fuel
[ ] Validate cell kế tiếp
[ ] POST /actions thành công
[ ] Mở "Trận của tôi" để theo dõi trận
[ ] GET /result hoạt động
```

---

# 23. Luồng làm việc đề xuất cho project

Trong quá trình phát triển:

```text
Tạo trận luyện tập
        ↓
Lấy MATCH_ID
        ↓
Chạy connection_test.py
        ↓
Chạy bot đứng yên
        ↓
Mở trận trên website để quan sát
        ↓
Thêm parser map + state
        ↓
Thêm Dynamic Programming
        ↓
Thêm MARL task allocation
        ↓
Thêm refuel / traffic / reward
        ↓
Kiểm tra bot trước trận
        ↓
Đấu luyện tập nhiều seed/config
        ↓
Đấu đội thật
```

Nguyên tắc quan trọng:

> **Kết nối server và protocol phải chạy ổn trước; thuật toán thông minh thêm sau.**

Điều này giúp tách lỗi API khỏi lỗi thuật toán và làm project dễ debug hơn rất nhiều.
