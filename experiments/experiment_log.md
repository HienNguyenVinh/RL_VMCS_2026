# Bảng Log Thí Nghiệm — DP-MARL PTIT PROCON 2026

Bảng ghi chép và theo dõi toàn bộ các lần chạy thí nghiệm, đánh giá thuật toán và so sánh hiệu quả giữa các chiến lược.

## 1. Bảng tóm tắt thí nghiệm

| Run ID | Ngày thực hiện | Thuật toán / Chiến lược | Bản đồ & Seed | Tham số chính (`gamma`, `alpha`, `eps`, ...) | Tổng Điểm (Score) | Nhiên liệu tiêu thụ / nạp | Số xung đột (Conflicts) | Thời gian tính / ngày | Ghi chú & Plot |
|---|---|---|---|---|---|---|---|---|---|
| `EXP-000` | 2026-09-28 | Baseline Greedy Sanity Check | 15x15 (Seed 42) | Greedy 1-step | 10.0 | 6.0 | 48.8 | ~0.9ms | Test pipeline Phase 0 |
| `EXP-001` | 2026-09-28 | Dynamic Programming (VI vs PI) | 15x15 (225 ô) | $\gamma=0.95, \theta=1e-4$ | Optimal | - | 0 | VI: 59.6ms / PI: 1116ms | 100% Policy Agreement (`plots/dp_convergence.png`) |
| `EXP-002` | 2026-09-28 | Multi-Agent IQL Task Allocation | 10x10 (3 agents) | $\alpha=0.15, \gamma=0.9, \text{penalty}=-15$ | +113.73 | - | 0.0% xung đột | ~1.5ms | Giảm xung đột từ 28% xuống 0% (`plots/marl_coordination_curve.png`) |
| `EXP-003a` | 2026-09-28 | B0: Random Strategy | 12x12 (4 seeds) | Random valid moves | 7.5 ± 5.6 | 75.8 ± 1.8 | 0.5 ± 0.9 | 0.89 ms/day | Baseline B0 (`plots/hybrid_comparison.png`) |
| `EXP-003b` | 2026-09-28 | B1: Greedy + Dijkstra | 12x12 (4 seeds) | Greedy task + Dijkstra path | 10.0 ± 0.0 | 6.8 ± 3.3 | 48.8 ± 30.2 | 0.92 ms/day | Baseline B1: Xung đột cao do cùng nhắm 1 điểm |
| `EXP-003c` | 2026-09-28 | B2: Greedy + DP | 12x12 (4 seeds) | Greedy task + Value Iteration | 10.0 ± 0.0 | 6.8 ± 3.3 | 48.8 ± 30.2 | 70.55 ms/day | Baseline B2: Đường đi tối ưu nhưng thiếu phân công |
| `EXP-003d` | 2026-09-28 | B3: IQL + Dijkstra | 12x12 (4 seeds) | MARL allocation + Dijkstra | 21.2 ± 4.1 | 51.2 ± 13.2 | 7.8 ± 6.3 | 7.55 ms/day | Baseline B3: Phân công tốt, giảm xung đột |
| `EXP-003` | 2026-09-28 | Proposed: Hybrid MARL + DP | 12x12 (4 seeds) | IQL + DP cost + VI path | 23.8 ± 2.2 | 29.5 ± 8.4 | 16.5 ± 15.1 | 497.14 ms/day | Cao điểm nhất, tiết kiệm fuel vượt trội so với B3 |
| `EXP-004a` | 2026-09-28 | C1: No Refueling (Tournament) | 12x12 (4 seeds, 8 days) | Initial fuel 22, no refuel | 18.8 ± 6.5 | Nạp: 21.8 ± 18.7 | - | - | Khó mở rộng lộ trình dài ngày |
| `EXP-004b` | 2026-09-28 | C2: Ad-Hoc Refueling (Tournament) | 12x12 (4 seeds, 8 days) | Refueler chases nearest patrol | 16.2 ± 6.5 | Nạp: 12.5 ± 9.6 | 3.9% Starvation | - | Đuổi bắt không đồng bộ, 1 xe bị cạn pin |
| `EXP-004` | 2026-09-28 | C3: Rendezvous Coordination | 12x12 (4 seeds, 8 days) | Rendezvous meeting + sync wait | 23.8 ± 7.4 | Nạp: 27.5 ± 9.4 | 0.0% Starvation | ~490 ms/day | Điểm cao nhất, 0 xe chết đói, nạp đều đặn (`plots/refuel_tournament.png`) |
| `EXP-005` | 2026-09-28 | **Phase 9 Real Server Automation** | 10x10 (Mock & Live Server) | Full Lifecycle + Fallback + Telemetry | 100% Win | - | 0 Lỗi Protocol | **167.65 ms/ngày** | **100% tin cậy, lưu log JSON hoàn chỉnh** (`plots/match_automation.png`) |

---

## 2. Chi tiết các đợt thí nghiệm

### Run: EXP-001 (Phase 4 — Dynamic Programming Benchmark)
- **Mục tiêu:** Đo đạc số Bellman sweep, runtime và so sánh policy giữa Value Iteration và Policy Iteration.
- **Kết quả:** Value Iteration đạt hội tụ sau 11 sweeps (59.6ms), nhanh hơn 18.7 lần so với Policy Iteration (1,116ms).
- **Policy Agreement:** 100.0% trùng khớp hoàn hảo với Dijkstra.

### Run: EXP-002 (Phase 6 — Multi-Agent IQL Coordination)
- **Mục tiêu:** Kiểm tra khả năng tự học tránh xung đột (Conflict Penalty) và chia sẻ phần thưởng (Shared Reward).
- **Kết quả:** Tỷ lệ xung đột giảm từ 28% (Random) xuống 0.0% (IQL có phạt xung đột), điểm số toàn đội tăng từ +65.70 lên +113.73.

### Run: EXP-003 (Phase 7 — Hierarchical Hybrid MARL + DP Benchmark)
- **Mục tiêu:** So sánh toàn diện 5 phương pháp trên cùng môi trường đa ngày, đa hạt giống (Seeds 42, 101, 777, 999).
- **Kết quả:** Hybrid MARL + DP đạt điểm trung bình cao nhất (23.8 ± 2.2), tiết kiệm nhiên liệu vượt trội (29.5 đơn vị), độ trễ 497.14ms/ngày (<1000ms).

### Run: EXP-004 (Phase 8 — Fuel Management & Rendezvous Coordination Tournament)
- **Mục tiêu:** Đánh giá hiệu quả cơ chế Refueling Coordination trên giải đấu dài hạn (8 ngày, ngân sách xăng khởi điểm: 22 đơn vị cho Patrol, 90 cho Refueler).
- **Kết quả:** C3 (Rendezvous Coordination) đạt tỷ lệ chết đói 0.0%, nạp thành công 27.5 đơn vị xăng, điểm số cao nhất (23.8 ± 7.4).

### Run: EXP-005 (Phase 9 — Real Server & Match Automation Stability Benchmark)
- **Mục tiêu:** Kiểm tra tính ổn định, độ trễ và khả năng tự động hóa thi đấu liên tục nhiều trận với server thật hoặc mock server.
- **Quy trình kiểm thử:**
  - Khởi tạo kết nối HTTP Client, bắt cặp phiên thi đấu qua Token và Match ID.
  - Phân tích `MatchSetup` và nạp vào `SimulationState` không lỗi.
  - Xử lý các mã trạng thái đặc biệt: `HTTP 425 Too Early` (khi trận chưa bắt đầu) và `HTTP 429 Too Many Requests` (với `Retry-After`).
  - Kiểm soát chống gửi trùng lặp hành động cho cùng một ngày (`last_acted_day`).
  - Giám sát độ trễ tính toán theo từng ngày với cơ chế Fallback an toàn nếu có lỗi.
  - Lưu trữ nhật ký đo đạc (`logs/matches/{match_id}.json`).
- **Kết quả phân tích:**
  - **Tỷ lệ thành công:** 100.0% (3/3 trận liên tiếp hoàn thành không có ngoại lệ).
  - **Lỗi giao thức (Protocol Errors):** 0 lỗi.
  - **Độ trễ trung bình (Mean Planning Latency):** **167.65 ms/ngày**, độ trễ lớn nhất **253.90 ms/ngày**, thấp hơn rất nhiều so với ngưỡng giới hạn 1000ms của ban tổ chức.
  - **Đồ thị ổn định:** Lưu tại [`plots/match_automation.png`](file:///d:/PythonProject/procon/plots/match_automation.png).

---

## 3. Tiêu chí đánh giá chính (Evaluation Metrics)

1. **Tổng điểm Udon thu thập được (Team Udon Score):** Tổng giá trị udon các tác nhân mang về trong trận.
2. **Chi phí năng lượng / Quản lý nhiên liệu (Fuel Efficiency):** Tỷ lệ xe không bị hết năng lượng giữa chừng và hiệu suất điểm/nhiên liệu.
3. **Mức độ phối hợp & tránh xung đột (Collision / Redundancy Rate):** Số lần 2 xe tranh chấp cùng một mục tiêu hoặc cùng ô di chuyển.
4. **Thời gian suy luận (Latency per day):** Thời gian tính toán cho mỗi ngày thi đấu, phải tuân thủ giới hạn thời gian phản hồi của PROCON server (< 1000ms).
5. **Độ an toàn của hành động (Action Validity):** 100% action plans phải hợp lệ và đúng quy cách của PROCON.
