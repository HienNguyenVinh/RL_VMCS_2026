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

### Chạy so sánh hiệu quả Hybrid MARL+DP vs Baseline

```bash
python main.py --mode hybrid
# hoặc:
python experiments/run_hybrid.py
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
- [ ] **PHASE 1 — Kết nối server PROCON**
- [ ] **PHASE 2 — Biểu diễn Hex Grid và bài toán MDP**
- [ ] **PHASE 3 — Dynamic Programming Planner**
- [ ] **PHASE 4 — Offline Multi-Agent RL cho phân công task**
- [ ] **PHASE 5 — Tích hợp Hybrid MARL + DP**
- [ ] **PHASE 6 — Kết nối bot hybrid với server PROCON**
- [ ] **PHASE 7 — Thí nghiệm, ablation study và baseline**
- [ ] **PHASE 8 — Đóng gói, viết báo cáo và chuẩn bị demo**
