# PROJECT PLAN & CHECKLIST
## PTIT PROCON 2026 — Dynamic Programming for Gridworld + Multi-Agent RL for Cooperative Task Allocation

> Mục tiêu: xây dựng một bot cho challenge PROCON theo kiến trúc phân cấp:
>
> **Multi-Agent RL quyết định “agent nào làm nhiệm vụ nào” → Dynamic Programming quyết định “đi đến mục tiêu bằng đường nào”.**

---

# 1. Mục tiêu cuối cùng

Project cần đạt được 4 mục tiêu chính:

- [ ] Bot kết nối được với server PROCON và chạy hết một trận.
- [ ] Dynamic Programming tìm được policy / đường đi tốt trên Hex Grid có chi phí khác nhau.
- [ ] Multi-Agent RL học được cách phân công task cho nhiều agent với shared reward / conflict penalty.
- [ ] Hệ thống hybrid MARL + DP được đánh giá bằng thực nghiệm và so sánh với baseline.

---

# 2. Kiến trúc tổng thể

```text
                PROCON SERVER
                     │
                     ▼
                Current State
                     │
                     ▼
         +-------------------------+
         | Multi-Agent Task Layer  |
         | Independent Q-Learning  |
         +-------------------------+
                     │
         Target / Task assignment
                     │
                     ▼
         +-------------------------+
         | Dynamic Planning Layer  |
         | Value / Policy Iteration|
         +-------------------------+
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

# 3. Scope project

## Bắt buộc

- [ ] Parse `setup`.
- [ ] Parse `state`.
- [ ] Biểu diễn Hex Grid.
- [ ] Biểu diễn terrain / movement cost.
- [ ] Implement Iterative Policy Evaluation.
- [ ] Implement Policy Iteration.
- [ ] Implement Value Iteration.
- [ ] Implement Q-Learning cơ bản.
- [ ] Implement Independent Q-Learning cho nhiều agent.
- [ ] Shared reward.
- [ ] Conflict penalty.
- [ ] MARL chọn target/task.
- [ ] DP chọn route.
- [ ] Gửi action hợp lệ lên server.
- [ ] Chạy nhiều seed.
- [ ] Có baseline để so sánh.
- [ ] Có learning curve / convergence curve.
- [ ] Có báo cáo và demo.

## Chưa làm ở phiên bản đầu

- [ ] MAPPO.
- [ ] QMIX.
- [ ] MADDPG.
- [ ] Deep Q-Network.
- [ ] Graph Neural Network.
- [ ] Neural route planner.
- [ ] End-to-end Deep MARL.

> Chỉ mở rộng sang Deep RL nếu phiên bản tabular đã chạy ổn và còn thời gian.

---

# 4. Các milestone chính

| Milestone | Kết quả mong đợi |
|---|---|
| M0 | Repo + cấu trúc project + kết nối server |
| M1 | Offline Hex Grid simulator chạy được |
| M2 | Value Iteration + Policy Iteration chạy đúng |
| M3 | Single-agent Q-Learning chạy đúng |
| M4 | Multi-Agent IQL phân task được |
| M5 | Hybrid MARL + DP chạy offline |
| M6 | Bot hybrid chạy trên server PROCON |
| M7 | Baseline + experiments + plots |
| M8 | Báo cáo + slide + demo |

---

# 5. Kế hoạch theo giai đoạn

---

## PHASE 0 — Khởi tạo project

### Mục tiêu

Tạo môi trường làm việc rõ ràng trước khi viết thuật toán.

### Checklist

- [x] Tạo Git repository.
- [x] Tạo `README.md`.
- [x] Tạo `.gitignore`.
- [x] Tạo `requirements.txt`.
- [x] Không commit API token.
- [x] Tạo file `.env.example`.
- [x] Tạo cấu trúc thư mục.
- [x] Thống nhất format code.
- [x] Tạo branch strategy nếu làm nhóm.
- [x] Tạo bảng log thí nghiệm.

### Cấu trúc đề xuất

```text
procon-dp-marl/
│
├── README.md
├── requirements.txt
├── .gitignore
├── .env.example
│
├── config/
│   └── default.yaml
│
├── client/
│   ├── http_client.py
│   └── protocol.py
│
├── env/
│   ├── hex_grid.py
│   ├── state.py
│   ├── simulator.py
│   └── reward.py
│
├── planner/
│   ├── policy_evaluation.py
│   ├── policy_iteration.py
│   └── value_iteration.py
│
├── marl/
│   ├── q_agent.py
│   ├── iql.py
│   ├── task_allocator.py
│   └── state_encoder.py
│
├── strategy/
│   ├── greedy.py
│   ├── dp_only.py
│   └── hybrid.py
│
├── experiments/
│   ├── run_dp.py
│   ├── run_marl.py
│   ├── run_hybrid.py
│   └── configs/
│
├── plots/
│
├── tests/
│   ├── test_hex_grid.py
│   ├── test_dp.py
│   ├── test_qlearning.py
│   └── test_connection.py
│
└── main.py
```

### Definition of Done

- [x] Chạy được `python main.py`.
- [x] Import module không lỗi.
- [x] Token không xuất hiện trong Git.
- [x] Có README mô tả cách chạy project.

---

## PHASE 1 — Kết nối server PROCON

### Mục tiêu

Đảm bảo protocol hoạt động trước khi thêm thuật toán.

### Checklist

- [x] Lấy API token.
- [x] Tạo trận luyện tập.
- [x] Lấy `MATCH_ID`.
- [x] `GET /setup` thành công.
- [x] Parse JSON setup.
- [x] `POST /assignment` thành công.
- [x] Xử lý `HTTP 425`.
- [x] `GET /state` thành công.
- [x] `POST /actions` thành công.
- [x] `GET /result` thành công.
- [x] Xử lý `HTTP 429`.
- [x] Poll >= 200 ms.
- [x] Log request / response quan trọng.

### Smoke test

Bot đầu tiên chỉ cần:

```text
Tất cả agent đứng yên
```

Ví dụ:

```python
actions = [
    [-1] * day_steps
    for _ in range(num_agents)
]
```

### Definition of Done

- [x] Bot chạy hết một trận mà không crash.
- [x] Có thể mở trận trên website và thấy state thay đổi.
- [x] Không còn lỗi protocol cơ bản.

---

## PHASE 2 — Xây Offline Environment

### Mục tiêu

Có simulator offline để phát triển DP và RL mà không phụ thuộc server.

### Checklist

### Hex Grid

- [x] Chọn coordinate system.
- [x] Implement 6 hướng.
- [x] Implement `get_neighbor(cell, direction)`.
- [x] Validate boundary.
- [x] Validate blocked cell.
- [x] Unit test tất cả 6 hướng.

### Map

- [x] Parse `width`.
- [x] Parse `height`.
- [x] Parse `cells`.
- [x] Convert `row, col -> index`.
- [x] Convert `index -> row, col`.
- [x] Parse terrain.
- [x] Parse roads nếu có.
- [x] Parse spots / udon.
- [x] Parse traffic.

### Agent

- [x] Position.
- [x] Kind.
- [x] Fuel.
- [x] Valid actions.
- [x] Movement cost.

### Simulator API

```python
state = env.reset()

next_state, reward, done, info = env.step(actions)
```

### Definition of Done

- [x] Có thể chạy 100 bước offline không lỗi.
- [x] Transition giống logic challenge.
- [x] Có unit test map / movement / fuel.

---

## PHASE 3 — Baseline Path Planning

### Mục tiêu

Tạo baseline trước khi làm DP.

### Checklist

- [ ] BFS.
- [ ] Dijkstra.
- [ ] Cost function cho terrain.
- [ ] Test shortest path.
- [ ] Test unreachable target.
- [ ] Test blocked cell.
- [ ] Test fuel constraint đơn giản.

### Metrics

- [ ] Route length.
- [ ] Movement cost.
- [ ] Runtime.
- [ ] Fuel consumption.

### Definition of Done

- [ ] Dijkstra tìm đúng minimum-cost path trên map nhỏ.
- [ ] Có test case tự tính bằng tay.

---

## PHASE 4 — Dynamic Programming

### Mục tiêu

Hoàn thành phần Gridworld / MDP.

---

### 4.1 MDP formulation

- [ ] Xác định state `S`.
- [ ] Xác định action `A`.
- [ ] Xác định transition `P`.
- [ ] Xác định reward `R`.
- [ ] Chọn `gamma`.
- [ ] Xác định terminal states.

Ví dụ phiên bản đầu:

```text
State:
    current cell

Action:
    direction 0..5

Reward:
    - movement_cost
    + target_reward

Transition:
    deterministic

Terminal:
    target cell
```

---

### 4.2 Iterative Policy Evaluation

- [ ] Initialize `V(s)`.
- [ ] Implement Bellman expectation update.
- [ ] Implement convergence threshold `theta`.
- [ ] Log Bellman sweeps.
- [ ] Test trên Gridworld nhỏ.

---

### 4.3 Policy Iteration

- [ ] Random initial policy.
- [ ] Policy Evaluation.
- [ ] Policy Improvement.
- [ ] Detect stable policy.
- [ ] Count policy improvement steps.

---

### 4.4 Value Iteration

- [ ] Implement Bellman optimality update.
- [ ] Implement convergence threshold.
- [ ] Extract optimal policy.
- [ ] Extract route từ policy.
- [ ] Detect loop / invalid policy.

---

### 4.5 DP Experiments

So sánh:

- [ ] Policy Iteration.
- [ ] Value Iteration.
- [ ] Dijkstra.

Thay đổi:

- [ ] `gamma`.
- [ ] Map size.
- [ ] Terrain cost.
- [ ] Stochastic transition nếu có extension.
- [ ] Different terminal rewards.

Metrics:

- [ ] Bellman sweeps.
- [ ] Policy improvement steps.
- [ ] Runtime.
- [ ] Final route cost.
- [ ] Convergence delta.

### Definition of Done

- [ ] VI và PI trả policy hợp lý.
- [ ] VI / PI đồng ý về optimal policy trên test nhỏ.
- [ ] Có convergence plot.
- [ ] Có bảng so sánh VI vs PI vs Dijkstra.

---

## PHASE 5 — Single-Agent Q-Learning

### Mục tiêu

Hiểu và kiểm tra Q-Learning trước khi chuyển sang MARL.

### Checklist

- [ ] Q-table.
- [ ] ε-greedy.
- [ ] Learning rate `alpha`.
- [ ] Discount `gamma`.
- [ ] ε decay.
- [ ] Episode loop.
- [ ] TD update.
- [ ] Save Q-table.
- [ ] Load Q-table.
- [ ] Learning curve.
- [ ] Multiple seeds.

### Test task

```text
Một agent
+
2 hoặc 3 target
+
chọn target tốt nhất
```

### Metrics

- [ ] Episodic return.
- [ ] Success rate.
- [ ] Steps to goal.
- [ ] Policy stability.

### Definition of Done

- [ ] Agent học tốt hơn random.
- [ ] Reward trung bình tăng theo training.
- [ ] Kết quả tương đối ổn định qua nhiều seed.

---

## PHASE 6 — Multi-Agent RL

### Mục tiêu

Cho nhiều agent học cách phân công task.

### Phiên bản đầu

```text
2 agents
2–3 tasks
```

### State representation

Không dùng full raw state ngay từ đầu.

Có thể dùng:

```text
agent_position
fuel_bin
distance_to_target_1
distance_to_target_2
task_available
other_agent_assignment
```

### Action space

Ví dụ:

```text
Task A
Task B
Task C
Idle
```

### Checklist Independent Q-Learning

- [ ] Mỗi agent có Q-table riêng.
- [ ] Mỗi agent chọn action bằng ε-greedy.
- [ ] Shared environment.
- [ ] Shared reward.
- [ ] Individual reward option.
- [ ] Conflict detection.
- [ ] Conflict penalty.
- [ ] Episode reset.
- [ ] Multi-seed training.

### Reward

Ví dụ:

```text
+ task completed
+ new udon type
+ useful collection
- duplicate assignment
- movement cost
- fuel risk
- invalid action
```

### Experiment quan trọng

- [ ] Shared reward vs individual reward.
- [ ] Có conflict penalty vs không có.
- [ ] ε cao vs thấp.
- [ ] 2 agents vs nhiều agent hơn.

### Metrics

- [ ] Team return.
- [ ] Conflict rate.
- [ ] Duplicate assignment rate.
- [ ] Tasks completed.
- [ ] Resource efficiency.
- [ ] Coordination success rate.

### Definition of Done

- [ ] Hai agent học tránh chọn cùng task tốt hơn random.
- [ ] Conflict rate giảm sau training.
- [ ] Có learning curve.

---

## PHASE 7 — Kết hợp MARL + DP

### Mục tiêu

Đây là phần chính của project.

### Luồng xử lý

```text
Current state
    │
    ▼
Generate candidate tasks
    │
    ▼
Compute DP cost-to-go
    │
    ▼
Encode MARL observation
    │
    ▼
IQL chooses task
    │
    ▼
DP plans path
    │
    ▼
Convert route -> directions
    │
    ▼
POST /actions
```

### Checklist

- [ ] Tạo candidate tasks.
- [ ] Tính DP cost-to-go đến từng task.
- [ ] Đưa cost-to-go vào observation.
- [ ] MARL chọn assignment.
- [ ] DP tạo route.
- [ ] Convert route sang direction 0..5.
- [ ] Pad bằng `-1` nếu cần.
- [ ] Validate `daySteps`.
- [ ] Validate fuel.
- [ ] Detect impossible target.
- [ ] Fallback strategy khi planner fail.

### Fallback

Nếu MARL / DP không đưa ra action hợp lệ:

```text
1. Greedy nearest valid target
2. Dijkstra
3. Stand still
```

### Definition of Done

- [ ] Hybrid chạy hết episode offline.
- [ ] Không phát sinh invalid action.
- [ ] Hybrid tốt hơn ít nhất một baseline trên một số metric rõ ràng.

---

## PHASE 8 — Fuel / Refueling

### Mục tiêu

Thêm cooperation liên quan đến fuel sau khi core pipeline đã ổn.

### Checklist

- [ ] Fuel consumption model.
- [ ] Low-fuel threshold.
- [ ] Refuel vehicle.
- [ ] Refuel request.
- [ ] Chọn rendezvous cell.
- [ ] Patrol route tới rendezvous.
- [ ] Refuel route tới rendezvous.
- [ ] Check time synchronization.
- [ ] Fallback nếu rendezvous không khả thi.

### Version 1 đơn giản

```text
Nếu Patrol fuel < threshold:
    task = REFUEL
```

Không cần tối ưu rendezvous phức tạp ngay.

### Definition of Done

- [ ] Agent không hết fuel vô lý.
- [ ] Refuel task hoạt động trong simulator.
- [ ] Có metric fuel failure rate.

---

## PHASE 9 — Chạy trên server thật

### Checklist

- [ ] Load setup thật.
- [ ] Load state thật.
- [ ] State encoder không crash.
- [ ] Planner chạy trong time limit.
- [ ] Action format đúng.
- [ ] Logging đầy đủ.
- [ ] Có retry hợp lý.
- [ ] Xử lý `425`.
- [ ] Xử lý `429`.
- [ ] Không gửi duplicate action cho cùng ngày.
- [ ] Có timeout.
- [ ] Có fallback action.
- [ ] Có save match logs.

### Nên log

```text
match_id
day
step
agent_id
state summary
selected task
DP cost
route
action
reward
server response
latency
```

### Definition of Done

- [ ] Bot chạy hết nhiều trận luyện tập liên tiếp.
- [ ] Không lỗi protocol.
- [ ] Latency ổn định.
- [ ] Có log để replay / debug.

---

# 6. Experimental Plan

## Baselines

Tối thiểu nên có 4 cấu hình:

### B0 — Random

```text
Random task
+
Random valid movement
```

- [ ] Implement.

### B1 — Greedy + Dijkstra

```text
Nearest / highest-score task
+
Dijkstra
```

- [ ] Implement.

### B2 — Greedy + DP

```text
Greedy task allocation
+
Value Iteration
```

- [ ] Implement.

### B3 — IQL + Dijkstra

```text
MARL task allocation
+
Dijkstra
```

- [ ] Implement.

### Proposed — IQL + DP

```text
MARL task allocation
+
Dynamic Programming
```

- [ ] Implement.

---

## Main comparison

| Method | Task Allocation | Route Planning |
|---|---|---|
| Random | Random | Random |
| Greedy + Dijkstra | Greedy | Dijkstra |
| Greedy + DP | Greedy | DP |
| IQL + Dijkstra | MARL | Dijkstra |
| IQL + DP | MARL | DP |

### Checklist

- [ ] Cùng map / seed.
- [ ] Cùng số agent.
- [ ] Cùng số ngày.
- [ ] Cùng reward definition.
- [ ] Chạy nhiều independent seeds.
- [ ] Báo mean.
- [ ] Báo std.
- [ ] Lưu raw results.

---

# 7. Research Questions

## RQ1 — DP

**Value Iteration và Policy Iteration khác nhau thế nào về convergence và runtime?**

- [ ] Đo Bellman sweeps.
- [ ] Đo runtime.
- [ ] So policy cuối.

---

## RQ2 — Discount factor

**Gamma ảnh hưởng thế nào tới policy và cost?**

- [ ] γ = 0.5.
- [ ] γ = 0.8.
- [ ] γ = 0.95.
- [ ] γ = 0.99.

---

## RQ3 — Coordination

**Independent Q-Learning có học được cách tránh conflict không?**

- [ ] Plot conflict rate.
- [ ] Plot reward.
- [ ] So random baseline.

---

## RQ4 — Reward structure

**Shared reward có giúp cooperation tốt hơn individual reward không?**

- [ ] Shared reward.
- [ ] Individual reward.
- [ ] Compare conflict.
- [ ] Compare task completion.
- [ ] Compare final team score.

---

## RQ5 — Hybrid architecture

**Đưa DP cost-to-go vào MARL observation có cải thiện task allocation không?**

- [ ] MARL không có DP cost.
- [ ] MARL có DP cost.
- [ ] So team reward.
- [ ] So movement cost.
- [ ] So fuel efficiency.

---

# 8. Metrics

## DP metrics

- [ ] Bellman sweeps.
- [ ] Policy improvement steps.
- [ ] Runtime.
- [ ] Path length.
- [ ] Path cost.
- [ ] Fuel cost.

## MARL metrics

- [ ] Episode return.
- [ ] Team reward.
- [ ] Conflict rate.
- [ ] Duplicate-task rate.
- [ ] Task completion rate.
- [ ] Invalid-action rate.

## Challenge metrics

- [ ] Udon collected.
- [ ] Number of udon types.
- [ ] Unique locations.
- [ ] Fuel failures.
- [ ] Response latency.
- [ ] Final result / ranking metric nếu có.

---

# 9. Hyperparameter checklist

## DP

- [ ] `gamma`.
- [ ] `theta`.
- [ ] terminal reward.
- [ ] movement penalty.

## Q-Learning

- [ ] `alpha`.
- [ ] `gamma`.
- [ ] `epsilon_start`.
- [ ] `epsilon_end`.
- [ ] `epsilon_decay`.
- [ ] number of episodes.

## MARL Reward

- [ ] task reward.
- [ ] conflict penalty.
- [ ] movement cost.
- [ ] fuel penalty.
- [ ] new-type reward.
- [ ] completion bonus.

> Mỗi hyperparameter quan trọng phải có lý do chọn hoặc có experiment hỗ trợ.

---

# 10. Reproducibility checklist

- [ ] Có `requirements.txt`.
- [ ] Có seed.
- [ ] Có config file.
- [ ] Có command chạy experiment.
- [ ] Có raw result.
- [ ] Có script vẽ plot.
- [ ] Có model / Q-table checkpoint nếu cần.
- [ ] Có README.
- [ ] Không cần chỉnh source code để chạy config khác.
- [ ] Có log version/config của từng experiment.

Ví dụ:

```bash
python experiments/run_dp.py \
    --algorithm value_iteration \
    --gamma 0.95 \
    --seed 0
```

```bash
python experiments/run_hybrid.py \
    --episodes 5000 \
    --shared-reward \
    --seed 0
```

---

# 11. Testing checklist

## Unit tests

- [ ] Hex neighbors.
- [ ] Coordinate conversion.
- [ ] Movement cost.
- [ ] Invalid cell.
- [ ] Fuel update.
- [ ] Bellman update.
- [ ] Policy extraction.
- [ ] Q update.
- [ ] ε-greedy.
- [ ] Reward calculation.
- [ ] Action serialization.

## Integration tests

- [ ] Simulator + planner.
- [ ] Simulator + Q-Learning.
- [ ] MARL + DP.
- [ ] HTTP client + strategy.
- [ ] Full match smoke test.

---

# 12. Phân công cho nhóm 2 người

## Member A — Environment + DP + Server

- [ ] Server client.
- [ ] Hex Grid.
- [ ] Simulator.
- [ ] Dijkstra baseline.
- [ ] Policy Evaluation.
- [ ] Policy Iteration.
- [ ] Value Iteration.
- [ ] Route extraction.
- [ ] Server integration.

## Member B — RL + Experiments

- [ ] Single-agent Q-Learning.
- [ ] IQL.
- [ ] State encoder.
- [ ] Reward.
- [ ] Task allocator.
- [ ] Training loop.
- [ ] Evaluation.
- [ ] Plots.

## Làm chung

- [ ] Hybrid integration.
- [ ] Baselines.
- [ ] Experiments.
- [ ] Report.
- [ ] Presentation.
- [ ] Demo.

---

# 13. Kế hoạch thời gian đề xuất

Tài liệu môn dự kiến khoảng 25 giờ / nhóm. Có thể chia như sau:

| Công việc | Giờ |
|---|---:|
| Setup + server connection | 2 |
| Hex Grid + simulator | 3 |
| DP algorithms | 4 |
| Q-Learning + IQL | 4 |
| Hybrid integration | 4 |
| Experiments | 4 |
| Analysis + plots | 2 |
| Report + slides + demo | 2 |
| **Tổng** | **25** |

---

# 14. Day-by-day plan gợi ý

## Session 1

- [ ] Tạo repo.
- [ ] Test server connection.
- [ ] Smoke bot đứng yên.
- [ ] Parse setup.

## Session 2

- [ ] Hex Grid.
- [ ] Map parser.
- [ ] Dijkstra.
- [ ] Unit tests.

## Session 3

- [ ] Policy Evaluation.
- [ ] Policy Iteration.
- [ ] Value Iteration.

## Session 4

- [ ] DP experiments.
- [ ] Convergence plots.

## Session 5

- [ ] Single Q-Learning.
- [ ] ε-greedy.
- [ ] Learning curve.

## Session 6

- [ ] 2-agent IQL.
- [ ] Conflict penalty.
- [ ] Shared reward.

## Session 7

- [ ] MARL + DP integration.
- [ ] DP cost-to-go features.

## Session 8

- [ ] Fuel / refuel logic.
- [ ] Server integration.

## Session 9

- [ ] Baselines.
- [ ] Multi-seed experiments.

## Session 10

- [ ] Analyze results.
- [ ] Final plots.
- [ ] Report.
- [ ] Slides.
- [ ] Demo rehearsal.

---

# 15. Risk register

## Risk 1 — State space quá lớn

### Dấu hiệu

```text
Q-table tăng quá nhanh
training rất chậm
nhiều state chỉ xuất hiện 1 lần
```

### Giải pháp

- [ ] State abstraction.
- [ ] Fuel bin.
- [ ] Distance bin.
- [ ] Chỉ lấy top-K candidate tasks.
- [ ] Region encoding.
- [ ] Giảm số agent ở experiment đầu.

---

## Risk 2 — IQL không ổn định

### Giải pháp

- [ ] Bắt đầu 2 agents.
- [ ] Giảm action space.
- [ ] Shared reward.
- [ ] Conflict penalty rõ ràng.
- [ ] ε decay chậm.
- [ ] Chạy nhiều seed.

---

## Risk 3 — Reward hacking

### Dấu hiệu

Agent có reward cao nhưng challenge performance xấu.

### Giải pháp

- [ ] Tách training reward và evaluation metric.
- [ ] Kiểm tra behavior bằng replay.
- [ ] So với baseline.
- [ ] Giảm reward shaping không cần thiết.

---

## Risk 4 — DP quá chậm

### Giải pháp

- [ ] Cache value function.
- [ ] Chỉ plan trên relevant region.
- [ ] Dùng Dijkstra fallback.
- [ ] Replan khi state thay đổi đáng kể.

---

## Risk 5 — Server/API lỗi

### Giải pháp

- [ ] Offline simulator.
- [ ] Retry.
- [ ] Rate-limit handling.
- [ ] Timeout.
- [ ] Save logs.
- [ ] Safe fallback action.

---

# 16. Báo cáo cuối kỳ checklist

## 1. Application Context

- [ ] Mô tả PROCON challenge.
- [ ] Mô tả cooperative agents.
- [ ] Giải thích vì sao RL phù hợp.
- [ ] Giải thích vì sao DP phù hợp.

## 2. MDP / RL Formulation

- [ ] State.
- [ ] Action.
- [ ] Reward.
- [ ] Transition.
- [ ] Gamma.
- [ ] Terminal condition.
- [ ] Model-based vs model-free.

## 3. Methodology

- [ ] Policy Evaluation.
- [ ] Policy Iteration.
- [ ] Value Iteration.
- [ ] Independent Q-Learning.
- [ ] Hybrid MARL + DP.

## 4. Experimental Setup

- [ ] Environment.
- [ ] Baselines.
- [ ] Hyperparameters.
- [ ] Seeds.
- [ ] Metrics.

## 5. Results

- [ ] DP convergence plot.
- [ ] MARL learning curve.
- [ ] Conflict plot.
- [ ] Baseline comparison table.
- [ ] Hybrid results.

## 6. Discussion

- [ ] Vì sao kết quả như vậy?
- [ ] Non-stationarity.
- [ ] State-space limitation.
- [ ] Reward design limitation.
- [ ] Simulator vs real server gap.

## 7. Conclusion

- [ ] Tóm tắt contribution.
- [ ] Trả lời research questions.
- [ ] Nêu limitation.
- [ ] Future work.

---

# 17. Presentation checklist

## Slide 1 — Problem

- [ ] PROCON challenge.
- [ ] Multi-agent task allocation.
- [ ] Navigation problem.

## Slide 2 — Architecture

- [ ] MARL → DP → actions.

## Slide 3 — MDP

- [ ] S, A, P, R, γ.

## Slide 4 — Dynamic Programming

- [ ] Bellman equation.
- [ ] VI / PI.

## Slide 5 — MARL

- [ ] IQL.
- [ ] Shared reward.
- [ ] Conflict penalty.

## Slide 6 — Hybrid method

- [ ] DP cost-to-go.
- [ ] Task allocation.

## Slide 7 — Experiments

- [ ] Baselines.
- [ ] Metrics.

## Slide 8 — Results

- [ ] Main plots.
- [ ] Comparison table.

## Slide 9 — Discussion

- [ ] Strengths.
- [ ] Limitations.

## Slide 10 — Demo / Conclusion

- [ ] Live/replay demo.
- [ ] Key takeaway.

---

# 18. Demo checklist

Trước khi demo:

- [ ] Token đúng.
- [ ] Match ID đúng.
- [ ] Internet ổn.
- [ ] Bot chạy được.
- [ ] Có fallback demo video / log.
- [ ] Có pretrained Q-table.
- [ ] Có config demo nhỏ.
- [ ] Có script một lệnh để chạy.

Ví dụ:

```bash
python main.py \
    --match-id $PROCON_MATCH_ID \
    --strategy hybrid
```

---

# 19. Definition of Done toàn project

Project được xem là hoàn thành khi:

- [ ] Bot kết nối được server.
- [ ] Bot chạy hết trận.
- [ ] Simulator offline hoạt động.
- [ ] Value Iteration hoạt động.
- [ ] Policy Iteration hoạt động.
- [ ] IQL hoạt động.
- [ ] MARL chọn task.
- [ ] DP chọn route.
- [ ] Hybrid chạy end-to-end.
- [ ] Có ít nhất 3–5 baseline / variant để so sánh.
- [ ] Có multiple seeds.
- [ ] Có mean + variability.
- [ ] Có convergence curve.
- [ ] Có learning curve.
- [ ] Có ablation.
- [ ] Có phân tích, không chỉ show curve.
- [ ] Có source code rõ ràng.
- [ ] Có hướng dẫn reproduce.
- [ ] Có báo cáo.
- [ ] Có slide.
- [ ] Có demo.

---

# 20. Checklist ưu tiên nếu thiếu thời gian

Nếu thời gian gần hết, làm theo thứ tự:

## P0 — Bắt buộc

- [ ] Server connection.
- [ ] Simulator.
- [ ] Value Iteration.
- [ ] Policy Iteration.
- [ ] IQL.
- [ ] Shared reward.
- [ ] Hybrid IQL + DP.
- [ ] Greedy baseline.
- [ ] Multiple seeds.
- [ ] Result plots.
- [ ] Report.

## P1 — Nên có

- [ ] Dijkstra baseline.
- [ ] Individual vs shared reward.
- [ ] Conflict penalty ablation.
- [ ] DP cost-to-go ablation.
- [ ] Fuel constraint.

## P2 — Nếu còn thời gian

- [ ] Refueling rendezvous.
- [ ] Stochastic transitions.
- [ ] WebSocket client.
- [ ] Advanced visualization.
- [ ] More agents.
- [ ] More complex state abstraction.

---

# 21. Checklist công việc tiếp theo

Nếu bắt đầu project ngay bây giờ:

- [ ] **Task 1:** tạo repo và cấu trúc thư mục.
- [ ] **Task 2:** chạy bot đứng yên qua API.
- [ ] **Task 3:** parse `setup` và `state`.
- [ ] **Task 4:** implement Hex Grid.
- [ ] **Task 5:** implement Dijkstra baseline.
- [ ] **Task 6:** implement Value Iteration.
- [ ] **Task 7:** implement Policy Iteration.
- [ ] **Task 8:** test VI / PI trên map nhỏ.
- [ ] **Task 9:** implement Q-Learning single-agent.
- [ ] **Task 10:** chuyển thành 2-agent IQL.
- [ ] **Task 11:** thêm shared reward + conflict penalty.
- [ ] **Task 12:** MARL chọn target.
- [ ] **Task 13:** DP route tới target.
- [ ] **Task 14:** tích hợp full hybrid.
- [ ] **Task 15:** chạy baseline experiments.
- [ ] **Task 16:** chạy nhiều seed.
- [ ] **Task 17:** tổng hợp plot + table.
- [ ] **Task 18:** viết report.
- [ ] **Task 19:** làm slide.
- [ ] **Task 20:** rehearsal demo.

---

> Nguyên tắc triển khai:
>
> **Làm phiên bản nhỏ chạy đúng trước, sau đó mới tăng độ phức tạp.**
>
> Thứ tự ưu tiên:
>
> **Correctness → Reproducibility → Experiments → Optimization → Advanced extensions**
