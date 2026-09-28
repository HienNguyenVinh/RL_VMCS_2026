# Bảng Log Thí Nghiệm — DP-MARL PTIT PROCON 2026

Bảng ghi chép và theo dõi toàn bộ các lần chạy thí nghiệm, đánh giá thuật toán và so sánh hiệu quả giữa các chiến lược.

## 1. Bảng tóm tắt thí nghiệm

| Run ID | Ngày thực hiện | Thuật toán / Chiến lược | Bản đồ & Seed | Tham số chính (`gamma`, `alpha`, `eps`, ...) | Tổng Điểm (Score) | Số bước hoàn thành | Tỷ lệ va chạm / lỗi | Thời gian tính / bước | Ghi chú & Plot |
|---|---|---|---|---|---|---|---|---|---|
| `EXP-000` | 2026-09-28 | Baseline Greedy | 15x15 (Seed 42) | Greedy threshold=1.0 | TBD | TBD | TBD | TBD | Test pipeline Phase 0 |
| `EXP-001` | - | DP Only (Value Iteration) | 15x15 (Seed 42) | $\gamma=0.95, \theta=1e-4$ | - | - | - | - | Chạy đánh giá DP |
| `EXP-002` | - | Pure MARL (IQL) | 15x15 (Seed 42) | $\alpha=0.1, \gamma=0.9, \epsilon=0.1$ | - | - | - | - | Chạy đánh giá MARL |
| `EXP-003` | - | Hybrid MARL + DP | 15x15 (Seed 42) | IQL + Value Iteration | - | - | - | - | Mô hình hoàn chỉnh |

---

## 2. Chi tiết các đợt thí nghiệm

### Run: EXP-000 (Sanity Check)
- **Mục tiêu:** Kiểm tra cấu trúc pipeline, hàm log dữ liệu, xuất file metric và biểu đồ.
- **Kết quả:** Pipeline khởi tạo thành công ở Phase 0.
- **Đánh giá:** Sẵn sàng cho Phase 1 & Phase 2.

---

## 3. Tiêu chí đánh giá chính (Evaluation Metrics)

1. **Tổng điểm Udon thu thập được (Team Udon Score):** Tổng giá trị udon các tác nhân mang về trong trận.
2. **Chi phí năng lượng / Quản lý nhiên liệu (Fuel Efficiency):** Tỷ lệ xe không bị hết năng lượng giữa chừng.
3. **Mức độ phối hợp & tránh xung đột (Collision / Redundancy Rate):** Số lần 2 xe tranh chấp cùng một mục tiêu hoặc cùng ô di chuyển.
4. **Thời gian suy luận (Latency per step):** Thời gian tính toán cho mỗi bước di chuyển, phải tuân thủ giới hạn thời gian phản hồi của PROCON server (< 1000ms).
5. **Tốc độ hội tụ của DP & RL:** Số vòng lặp Bellman sweep để hội tụ Value Iteration; số episode để MARL đạt reward ổn định.
