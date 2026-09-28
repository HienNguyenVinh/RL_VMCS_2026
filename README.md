# PTIT PROCON 2026 — Dynamic Programming & Multi-Agent RL Bot

## Hybrid Dynamic Programming & Multi-Agent Reinforcement Learning for Cooperative Patrol and Refueling

Dự án phát triển bot thi đấu cho giải **PTIT PROCON 2026** dựa trên kiến trúc phân cấp hai tầng (**Hierarchical Architecture**):

> **Multi-Agent RL quyết định “agent nào làm nhiệm vụ nào” $\longrightarrow$ Dynamic Programming quyết định “đi đến mục tiêu bằng đường nào”.**

---

## 1. Kiến trúc tổng thể

```text
                 PROCON SERVER
                      │
                      ▼
                 Current State
          (Map, Traffic, Fuel, Spots)
                      │
                      ▼
          +-------------------------+
          | Multi-Agent Task Layer  |
          | Independent Q-Learning  |  <--- Phân công mục tiêu vĩ mô (Macro-Task)
          +-------------------------+       tránh xung đột, tối ưu team reward
                      │
            Target / Task assignment
                      │
                      ▼
          +-------------------------+
          | Dynamic Planning Layer  |
          | Value / Policy Iteration|  <--- Lập kế hoạch lộ trình tối ưu trên Hex Grid
          +-------------------------+       có xét chi phí địa hình & giao thông
                      │
               Route / Directions
                      │
                      ▼
              POST /actions
                      │
                      ▼
                 PROCON SERVER
```

---

## 2. Cấu trúc thư mục

```text
procon/
│
├── README.md                          # Tài liệu hướng dẫn tổng quan và vận hành
├── requirements.txt                   # Danh sách thư viện phụ thuộc
├── pyproject.toml                     # Cấu hình code format (ruff) và pytest
├── .gitignore                         # Loại bỏ file tạm, virtualenv và bảo mật API token
├── .env.example                       # Mẫu cấu hình biến môi trường
├── GIT_STRATEGY.md                    # Quy định nhánh git và commit message chuẩn
│
├── config/                            # Quản lý cấu hình YAML
│   ├── __init__.py
│   └── default.yaml                   # Cấu hình mặc định cho server, DP, MARL
│
├── client/                            # Giao tiếp với PROCON server
│   ├── __init__.py
│   ├── http_client.py                 # Client HTTP polling với cơ chế retry & error handling
│   └── protocol.py                    # Khai báo cấu trúc dữ liệu, enum hướng, agent types
│
├── env/                               # Mô phỏng môi trường và biểu diễn Hex Grid
│   ├── __init__.py
│   ├── hex_grid.py                    # Hệ tọa độ lục giác (6 hướng, offset to cube, khoảng cách)
│   ├── state.py                       # Trạng thái game, Udon spot, agent
│   ├── simulator.py                   # Simulator chạy offline mô phỏng di chuyển và nhặt udon
│   └── reward.py                      # Hàm phần thưởng (shared reward + conflict penalty)
│
├── planner/                           # Tầng quy hoạch động (Dynamic Programming)
│   ├── __init__.py
│   ├── policy_evaluation.py           # Iterative Policy Evaluation
│   ├── policy_iteration.py            # Policy Iteration
│   └── value_iteration.py             # Value Iteration
│
├── marl/                              # Tầng học tăng cường đa tác nhân (Multi-Agent RL)
│   ├── __init__.py
│   ├── q_agent.py                     # Tabular Q-Learning Agent (epsilon-greedy)
│   ├── iql.py                         # Independent Q-Learning coordinator
│   ├── task_allocator.py              # Bộ phân công nhiệm vụ vĩ mô
│   └── state_encoder.py               # Discretize không gian trạng thái cho tabular Q
│
├── strategy/                          # Các chiến lược điều khiển
│   ├── __init__.py
│   ├── greedy.py                      # Baseline tham lam (chọn đích gần nhất)
│   ├── dp_only.py                     # Chiến lược thuần DP
│   └── hybrid.py                      # Chiến lược phân cấp kết hợp MARL + DP
│
├── experiments/                       # Thí nghiệm & benchmark
│   ├── __init__.py
│   ├── run_dp.py                      # So sánh Value Iteration vs Policy Iteration
│   ├── run_marl.py                    # Thí nghiệm train Independent Q-Learning offline
│   ├── run_hybrid.py                  # Benchmark chiến lược Hybrid so với Baseline
│   ├── experiment_logger.py           # Ghi nhận log thí nghiệm vào CSV & JSON
│   ├── experiment_log.md              # Bảng theo dõi kết quả thí nghiệm
│   └── configs/                       # Cấu hình các kịch bản sweep
│       ├── dp_baseline.yaml
│       ├── marl_iql.yaml
│       └── hybrid_default.yaml
│
├── plots/                             # Thư mục lưu biểu đồ kết quả
│   └── .gitkeep
│
├── tests/                             # Unit tests
│   ├── __init__.py
│   ├── test_hex_grid.py               # Kiểm tra chuyển đổi tọa độ và láng giềng hex
│   ├── test_dp.py                     # Kiểm tra sự hội tụ của Value/Policy Iteration
│   ├── test_qlearning.py              # Kiểm tra Bellman update và epsilon decay
│   └── test_connection.py            # Kiểm tra URL client và parse protocol
│
└── main.py                            # Điểm khởi chạy chính của hệ thống
```

---

## 3. Cài đặt và chuẩn bị môi trường

### Yêu cầu
- Python 3.10+ (Đã kiểm thử trên Python 3.13)
- Git

### Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Cấu hình biến môi trường

Sao chép `.env.example` thành `.env` và điền token của đội:

```bash
cp .env.example .env
```

Nội dung `.env`:
```env
PROCON_BASE_URL=https://procon.ptit.edu.vn
PROCON_MATCH_ID=your_match_id_here
PROCON_TOKEN=your_team_token_here
PROCON_POLL_INTERVAL=1.0
PROCON_REQUEST_TIMEOUT=5.0
PROCON_LOG_LEVEL=INFO
```

> [!CAUTION]
> **Tuyệt đối không commit file `.env` lên Git!** File `.env` đã được cấu hình trong `.gitignore`.

---

## 4. Hướng dẫn chạy chương trình

### Chạy kiểm tra hệ thống (Demo mode)

```bash
python main.py --mode demo
```

### Kiểm tra tính toàn vẹn của các module (Imports check)

```bash
python main.py --check-imports
```

### Chạy thí nghiệm Dynamic Programming (Value Iteration vs Policy Iteration)

```bash
python main.py --mode dp
# hoặc:
python experiments/run_dp.py
```

### Chạy huấn luyện Multi-Agent RL (IQL) Offline

```bash
python main.py --mode marl
# hoặc:
python experiments/run_marl.py
```

### Chạy Benchmark Baseline Path Planning (BFS vs Dijkstra - Phase 3)

```bash
python main.py --mode baseline
# hoặc:
python experiments/run_baseline_comparison.py
```

### Chạy so sánh hiệu quả Hybrid MARL+DP vs Baseline

```bash
python main.py --mode hybrid
# hoặc:
python experiments/run_hybrid.py
```

### Chạy Smoke Test kết nối server (Tất cả agent đứng yên - Phase 1)

Chạy kiểm thử với local mock server (mô phỏng toàn bộ chu trình match):
```bash
python main.py --mode smoke_test --mock
```

Chạy với PROCON server thật (sau khi điền token và match ID vào `.env`):
```bash
python main.py --mode smoke_test
```

### Chạy bot thi đấu trên PROCON server

```bash
python main.py --mode server
```

### Chạy unit tests

```bash
python -m unittest discover tests
```

---

## 5. Tiến độ thực hiện các Phase

- [x] **PHASE 0 — Khởi tạo project**
  - [x] Khởi tạo Git repository
  - [x] Tạo `README.md`
  - [x] Tạo `.gitignore` bảo vệ token
  - [x] Tạo `requirements.txt`
  - [x] Tạo `.env.example`
  - [x] Tạo cấu trúc thư mục đầy đủ cho client, env, planner, marl, strategy, experiments, tests
  - [x] Thống nhất format code (`pyproject.toml`)
  - [x] Tạo branch strategy (`GIT_STRATEGY.md`)
  - [x] Tạo bảng log thí nghiệm (`experiments/experiment_log.md`)
  - [x] Kiểm thử toàn bộ module và `main.py`
- [x] **PHASE 1 — Kết nối server PROCON**
  - [x] Triển khai `ProconHttpClient` chuẩn protocol PROCON 2026
  - [x] Triển khai rate limiting (polling rate $\ge 200\text{ ms}$)
  - [x] Xử lý lỗi `HTTP 425 Too Early` (chờ trận bắt đầu)
  - [x] Xử lý lỗi `HTTP 429 Too Many Requests` (backoff & retry)
  - [x] Xử lý lỗi `HTTP 401 Unauthorized`
  - [x] Xác thực kế hoạch hành động (`validate_action_plan`)
  - [x] Triển khai smoke test bot (các agent đứng yên `[-1] * day_steps`)
  - [x] Triển khai `MockProconServer` phục vụ kiểm thử tự động
  - [x] Triển khai `MatchRunner` điều phối toàn bộ chu trình trận đấu
  - [x] Kiểm thử end-to-end thành công không lỗi
- [x] **PHASE 2 — Xây Offline Environment & Hex Grid**
  - [x] Chọn và chuẩn hóa hệ tọa độ lục giác (even-r offset & Cube coordinates)
  - [x] Triển khai đầy đủ 6 hướng láng giềng và kiểm tra ranh giới bản đồ
  - [x] Nhận diện và xử lý các ô cản (`TerrainType.POND` không thể đi vào)
  - [x] Thiết lập chi phí di chuyển và tiêu thụ nhiên liệu theo đúng luật PROCON 2026 (Đồng bằng, Núi, Ao, Đường theo cấp độ giao thông)
  - [x] Phân loại thuộc tính tác nhân: vị trí, vai trò (Patrol vs Refuel), nhiên liệu, kiểm tra `valid_actions`
  - [x] Triển khai simulator offline chuẩn Gym API (`reset()`, `step()`)
  - [x] Kiểm thử 100 bước di chuyển offline không lỗi
  - [x] Bộ unit test toàn diện cho map, movement, fuel, và collision
- [x] **PHASE 3 — Baseline Path Planning (BFS & Dijkstra)**
  - [x] Triển khai BFS tìm đường tối thiểu số bước nhảy (minimum hops)
  - [x] Triển khai Dijkstra tìm đường tối ưu chi phí di chuyển (minimum movement cost)
  - [x] Tích hợp chi phí địa hình và mức độ giao thông (Đồng bằng, Núi, Ao, Đường)
  - [x] Xử lý tránh ô cản (Ao - Pond) và nhận diện mục tiêu không thể tiếp cận (unreachable)
  - [x] Ràng buộc hạn mức nhiên liệu cho xe tuần tra (fuel constraints)
  - [x] Thu thập và đo lường đầy đủ 4 chỉ số: Route length, Movement cost, Runtime, Fuel consumption
  - [x] Kiểm thử tự tính bằng tay (hand-calculated) xác thực tính tối ưu toán học
  - [x] Bộ unit test chuyên biệt `test_baseline_planners.py` đạt 100% Pass
- [x] **PHASE 4 — Dynamic Programming (Gridworld / MDP)**
  - [x] Thiết lập mô hình MDP chuẩn: Trạng thái, Hành động, Chuyển trạng thái, Phần thưởng, Terminal states
  - [x] Triển khai Iterative Policy Evaluation với Bellman expectation update
  - [x] Triển khai Policy Iteration với cơ chế kiểm tra tính hội tụ / chính sách ổn định
  - [x] Triển khai Value Iteration với Bellman optimality backup và trích xuất lộ trình (tránh loop)
  - [x] Thí nghiệm so sánh VI vs PI vs Dijkstra, khảo sát ảnh hưởng của discount factor $\gamma$
  - [x] Vẽ và lưu biểu đồ hội tụ Bellman sweep (`plots/dp_convergence.png`)
  - [x] Độ tương đồng chính sách tối ưu giữa VI và PI đạt **100%**
- [x] **PHASE 5 — Single-Agent Q-Learning**
  - [x] Khởi tạo Q-table, chiến lược $\epsilon$-greedy, decay exploration
  - [x] Cập nhật Temporal Difference (TD update) và episode loop
  - [x] Lưu và nạp trọng số Q-table (`save` / `load` JSON)
  - [x] Đánh giá trên nhiều seed ngẫu nhiên
  - [x] Agent học vượt trội so với Random Baseline (+60.07 điểm)
  - [x] Vẽ và lưu learning curve (`plots/single_agent_qlearning.png`)
- [x] **PHASE 6 — Multi-Agent RL cho phân công task (MARL / IQL)**
  - [x] Kiến trúc Independent Q-Learning (IQL): mỗi agent sở hữu Q-table riêng
  - [x] Mã hóa không gian trạng thái đa tác nhân (vị trí, cụm nhiên liệu, khoảng cách đích, hành động của đồng đội)
  - [x] Cơ chế phát hiện xung đột và áp dụng phạt xung đột (Conflict Penalty)
  - [x] Thí nghiệm so sánh: IQL có phạt xung đột vs IQL thuần vs Random Baseline
  - [x] Giảm thiểu tỷ lệ tranh chấp mục tiêu và nâng cao điểm số toàn đội
  - [x] Vẽ và lưu đồ thị hội tụ phần thưởng và đồ thị giảm thiểu xung đột (`plots/marl_coordination_curve.png`)
- [ ] **PHASE 7 — Kết hợp MARL + DP (Hierarchical Strategy)**
- [ ] **PHASE 8 — Fuel / Refueling & Tournament Experiments**
