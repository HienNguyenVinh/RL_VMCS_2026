# PROPOSAL MINI-PROJECT

## Hybrid Dynamic Programming & Multi-Agent Reinforcement Learning for Cooperative Patrol and Refueling in PTIT PROCON 2026

**Tên ngắn:** **DP-MARL HEXUDON**  
**Bối cảnh:** PTIT PROCON 2026 – bài toán tối ưu hành trình trên bản đồ lục giác, thu thập udon, quản lý nhiên liệu và phối hợp nhiều tác nhân  
**Hướng kết hợp:**

1. **Dynamic Programming for Gridworld** – dùng Value Iteration / Policy Iteration để tính giá trị và đường đi chi phí thấp trên Hex Grid với địa hình, giao thông và nhiên liệu.
2. **Multi-Agent Reinforcement Learning for Cooperative Task Allocation** – dùng Independent Q-Learning để học cách phân công điểm đến và nhiệm vụ tiếp nhiên liệu giữa nhiều tác nhân.

---

## 1. Tóm tắt đề xuất

PTIT PROCON 2026 có thể được xem như một bài toán **multi-agent sequential decision-making trên Hex Grid**. Mỗi đội điều khiển nhiều tác nhân thuộc hai loại: **xe tuần tra** và **xe tiếp nhiên liệu**. Xe tuần tra cần di chuyển đến các điểm đích để thu thập udon; xe tiếp nhiên liệu có vai trò hỗ trợ duy trì khả năng hoạt động của xe tuần tra. Chi phí di chuyển phụ thuộc địa hình và trạng thái giao thông, trong khi trạng thái ngày kế tiếp chịu ảnh hưởng từ lưu lượng của ngày trước.

Đề xuất này xây dựng một kiến trúc **phân cấp hai tầng**:

- **Tầng 1 – MARL / Task Allocation:** mỗi tác nhân học cách chọn *nhiệm vụ vĩ mô* như “đi đến điểm udon A”, “hỗ trợ xe tuần tra B”, hoặc “đứng chờ”.
- **Tầng 2 – Dynamic Programming / Route Planning:** sau khi nhiệm vụ được chọn, bộ lập kế hoạch DP tính đường đi tối ưu hoặc gần tối ưu tới mục tiêu trên bản đồ lục giác của ngày hiện tại.

Ý tưởng chính là tách hai khó khăn khác nhau:

- **“Đi đâu?”** → học bằng Multi-Agent RL.
- **“Đi như thế nào?”** → giải bằng Dynamic Programming với mô hình bản đồ đã biết.

Cách tiếp cận này tránh việc buộc Q-Learning phải học đồng thời cả phân công nhiệm vụ lẫn từng bước di chuyển trên một không gian hành động rất lớn. Đồng thời, nó cho phép kiểm tra riêng tác động của **Value Iteration / Policy Iteration**, **shared reward**, **conflict penalty**, **exploration** và **phối hợp tiếp nhiên liệu**.

---

## 2. Động cơ nghiên cứu

Trong challenge, một chiến lược chỉ dựa trên đường đi ngắn nhất là chưa đủ vì nhiều xe có thể:

- cùng chọn một điểm đến gây trùng lặp nhiệm vụ;
- cùng tập trung vào một loại udon dù đội cần đa dạng hóa loại udon;
- cạnh tranh lượng udon tồn kho tại cùng một điểm;
- chọn lộ trình khiến xe tuần tra thiếu nhiên liệu giữa ngày;
- bỏ qua cơ hội bố trí xe tiếp nhiên liệu tại vị trí thuận lợi;
- chọn đường có chi phí cao khi trạng thái đường chuyển từ thông thoáng sang đông đúc hoặc ùn tắc.

Ngược lại, nếu sử dụng thuần Multi-Agent RL ở cấp độ từng bước di chuyển, không gian trạng thái–hành động sẽ tăng mạnh theo:

- kích thước bản đồ;
- số tác nhân;
- lượng nhiên liệu;
- trạng thái giao thông;
- số điểm udon;
- trạng thái kho;
- số bước còn lại trong ngày.

Do đó, đề xuất sử dụng **DP như một bộ giải cấu trúc thấp cấp** và **MARL như một bộ điều phối cao cấp**.

---

## 3. Liên hệ trực tiếp với yêu cầu môn Advanced Reinforcement Learning

Proposal kết hợp hai mini-project trong tài liệu môn học:

### 3.1. Dynamic Programming for Gridworld

Thành phần DP sẽ:

- biểu diễn bản đồ Hex Grid dưới dạng MDP;
- triển khai **Iterative Policy Evaluation**;
- triển khai **Policy Iteration**;
- triển khai **Value Iteration**;
- so sánh số Bellman sweeps, thời gian hội tụ và policy thu được;
- khảo sát ảnh hưởng của `gamma` và chi phí giao thông.

### 3.2. Multi-Agent RL for Cooperative Task Allocation

Thành phần MARL sẽ:

- sử dụng nhiều learning agents trong cùng môi trường;
- triển khai **Independent Q-Learning (IQL)**;
- nghiên cứu khả năng tự hình thành phối hợp mà không cần giao tiếp trực tiếp;
- so sánh **shared team reward** và **individual reward**;
- nghiên cứu ảnh hưởng của conflict penalty và exploration tới phối hợp;
- phân tích tính không ổn định do các agent khác cũng đang học đồng thời.

Không sử dụng MAPPO, QMIX hoặc các kiến trúc MARL phức tạp trong phần cốt lõi để giữ đúng phạm vi một mini-project có thể hoàn thành và phân tích rõ ràng.

---

## 4. Mô hình hóa challenge PTIT PROCON 2026

### 4.1. Bản đồ Hex Grid

Bản đồ gồm các ô lục giác; mỗi ô có tối đa **6 láng giềng**. Một lệnh di chuyển có thể chọn một trong sáu hướng:

```text
0 = trên-trái
1 = trên-phải
2 = phải
3 = dưới-phải
4 = dưới-trái
5 = trái
```

Bản đồ có các loại địa hình chính:

| Loại ô | Số bước di chuyển | Nhiên liệu xe tuần tra |
|---|---:|---:|
| Đồng bằng | 2 | 1 |
| Núi | 3 | 2 |
| Ao | Không đi được | – |
| Đường – thông thoáng | 1 | 2 |
| Đường – đông đúc | 2 | 2 |
| Đường – ùn tắc | 4 | 2 |

Chi phí được tính theo **ô hiện tại / ô nguồn** khi tác nhân bắt đầu lệnh di chuyển.

### 4.2. Giao thông

Trạng thái đường có thể là:

- thông thoáng;
- đông đúc;
- ùn tắc.

Trạng thái giao thông trong một ngày được cố định sau khi máy chủ cập nhật đầu ngày. Vì vậy, với một `day_state` đã nhận, bài toán lập đường trong ngày có thể xem là một MDP có transition/cost đã biết.

Ở mức liên ngày, giao thông phụ thuộc vào lưu lượng trước đó, do đó chiến lược của ngày hiện tại có thể tác động gián tiếp đến chi phí di chuyển của các ngày sau.

### 4.3. Điểm udon

Các điểm đến nằm trên một số ô hợp lệ. Mỗi điểm:

- thuộc một chuỗi / loại udon;
- có lượng tồn kho giới hạn trong ngày;
- xe tuần tra thu udon khi ghé điểm;
- cùng một xe chỉ được lợi từ lần ghé đầu tiên tại một điểm trong ngày;
- kho được bổ sung lại vào đầu ngày theo luật challenge.

Điều này biến việc chọn mục tiêu thành một bài toán **task allocation có tài nguyên hữu hạn**.

### 4.4. Hai loại tác nhân

#### Xe tuần tra

- có nhiên liệu hữu hạn;
- tiêu thụ nhiên liệu khi di chuyển;
- thu udon tại điểm đến;
- nếu hết nhiên liệu hoặc không đủ nhiên liệu cho lệnh tiếp theo thì kế hoạch có thể trở nên không hợp lệ.

#### Xe tiếp nhiên liệu

- không thu udon;
- có vai trò hỗ trợ xe tuần tra;
- di chuyển mà không chịu ràng buộc nhiên liệu như xe tuần tra;
- khi phối hợp đúng vị trí/thời điểm với xe tuần tra có thể nạp lại nhiên liệu cho xe tuần tra.

### 4.5. Quyết định theo ngày

Mỗi ngày có một số bước giới hạn `daySteps`.

Quy trình điều khiển được xem như:

1. nhận `day_state` từ server;
2. quan sát vị trí, fuel, trạng thái đường, điểm đến và các thông tin liên quan;
3. phân công macro-task cho từng agent;
4. dùng DP để tạo route;
5. chuyển route thành kế hoạch hành động hợp lệ;
6. gửi kế hoạch ngày;
7. nhận trạng thái ngày kế tiếp và lặp lại.

---

## 5. Câu hỏi nghiên cứu

### RQ1 – Dynamic Programming

**Value Iteration và Policy Iteration khác nhau như thế nào khi lập đường trên Hex Grid có chi phí địa hình/giao thông?**

Các chỉ số:

- Bellman sweeps;
- policy-improvement iterations;
- thời gian tính toán;
- tổng số bước di chuyển;
- tổng fuel tiêu thụ;
- tỷ lệ trạng thái có cùng hành động tối ưu.

### RQ2 – Multi-Agent Coordination

**Independent Q-Learning có học được cách giảm trùng lặp mục tiêu giữa nhiều xe tuần tra không?**

Các chỉ số:

- target-conflict rate;
- duplicate-visit rate;
- số task hoàn thành;
- số loại udon thu được;
- tổng udon.

### RQ3 – Shared vs Individual Reward

**Shared team reward có tạo ra phối hợp tốt hơn individual reward trong bài toán thu thập udon không?**

### RQ4 – Refueling Coordination

**Agent tiếp nhiên liệu có học được thời điểm và vị trí hỗ trợ có ích cho xe tuần tra không?**

### RQ5 – Hybrid Architecture

**Kết hợp MARL task allocation + DP route planning có hiệu quả hơn các baseline chỉ dùng planning hoặc chỉ dùng RL không?**

### RQ6 – Exploration

**Giá trị epsilon ảnh hưởng thế nào tới tốc độ hình thành phối hợp và độ ổn định của Independent Q-Learning?**

---

## 6. Kiến trúc đề xuất

```text
                    +---------------------------+
                    |      PROCON Day State     |
                    | map, traffic, stock, fuel |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    | Feature / State Encoder   |
                    +-------------+-------------+
                                  |
                                  v
             +-----------------------------------------+
             |   Multi-Agent Independent Q-Learning    |
             |       Cooperative Task Allocation       |
             +-----------+-----------------+-----------+
                         |                 |
                    Task agent 0      Task agent i
                         |                 |
                         v                 v
             +-----------------------------------------+
             | Dynamic Programming Route Planner       |
             | Value Iteration / Policy Iteration      |
             +-------------------+---------------------+
                                 |
                                 v
                    +---------------------------+
                    | Route -> Action Plan      |
                    | directions / wait actions |
                    +-------------+-------------+
                                  |
                                  v
                    +---------------------------+
                    |   Simulator / PROCON API  |
                    +---------------------------+
```

### 6.1. Ý nghĩa của hai tầng

**MARL không quyết định từng bước trái/phải.** MARL chỉ quyết định nhiệm vụ ở mức cao.

Ví dụ:

```text
Patrol-0 -> Visit checkpoint C7
Patrol-1 -> Visit checkpoint C3
Refuel-2 -> Support Patrol-0
Patrol-3 -> Visit checkpoint C11
```

Sau đó DP mới tìm chuỗi hành động cụ thể để đi đến C7, C3, điểm rendezvous hoặc C11.

---

## 7. Tầng Dynamic Programming

## 7.1. MDP cho route planning

Với một mục tiêu cố định `g`, ta định nghĩa:

```text
M_DP = <S, A, P, R, gamma>
```

### State

Phiên bản cơ bản:

```text
s = current_cell
```

Phiên bản có fuel:

```text
s = (current_cell, fuel_bin)
```

Nếu cần ràng buộc thời gian trong ngày:

```text
s = (current_cell, fuel_bin, remaining_step_bin)
```

Để giữ state space nhỏ, thí nghiệm chính ưu tiên `(cell, fuel_bin)` và kiểm tra `daySteps` bằng feasibility filter.

### Action

```text
A = {0, 1, 2, 3, 4, 5}
```

Action không hợp lệ nếu:

- ra ngoài bản đồ;
- đi vào ao;
- không đủ fuel;
- vượt quá số bước còn lại.

### Transition

Trong một ngày cố định:

```text
P(s' | s, a) = 1
```

cho transition hợp lệ, vì route planner sử dụng map/traffic đã biết của ngày hiện tại.

Có thể thêm một thí nghiệm mở rộng với stochastic transition để kiểm tra độ bền của policy.

### Reward của DP

Một reward dạng cost-minimization:

```text
r_DP(s, a, s') =
    + R_goal                        nếu s' = target
    - beta_step * step_cost(s)
    - beta_fuel * fuel_cost(s)
    - beta_invalid                 nếu action không hợp lệ
```

Ví dụ ban đầu:

```text
R_goal       = +50
beta_step    = 1.0
beta_fuel    = 2.0
beta_invalid = 50
```

Các giá trị này chỉ là cấu hình khởi tạo; báo cáo sẽ có sensitivity analysis.

---

## 7.2. Value Iteration

Bellman optimality update:

```text
V_{k+1}(s) = max_a [ R(s,a) + gamma * sum_s' P(s'|s,a)V_k(s') ]
```

Dừng khi:

```text
max_s |V_{k+1}(s) - V_k(s)| < theta
```

Policy:

```text
pi*(s) = argmax_a [ R(s,a) + gamma * sum_s' P(s'|s,a)V*(s') ]
```

### Vai trò trong hệ thống hybrid

Với mỗi target quan trọng, Value Iteration có thể sinh:

- cost-to-go;
- route tốt nhất;
- ước lượng chi phí tới target;
- feature cho tầng MARL.

Thay vì chỉ truyền khoảng cách hình học, MARL nhận **DP cost-to-go**, phản ánh cả núi, đường và traffic.

---

## 7.3. Policy Iteration

Policy Iteration gồm:

1. policy evaluation;
2. policy improvement;
3. lặp đến khi policy ổn định.

Trong proposal, Policy Iteration chủ yếu dùng để:

- so sánh với Value Iteration;
- kiểm chứng policy;
- phân tích số vòng policy improvement;
- đo tác động của `gamma`.

Value Iteration sẽ được ưu tiên trong agent online nếu thời gian tính toán tốt hơn trên các instance thử nghiệm.

---

## 8. Tầng Multi-Agent Reinforcement Learning

## 8.1. Cooperative Markov Game

Ta biểu diễn phần phân công nhiệm vụ như một cooperative Markov game:

```text
G = <N, S, {A_i}, P, R_team, gamma>
```

Trong đó:

- `N`: số agent của đội;
- `S`: trạng thái môi trường ở mức macro;
- `A_i`: macro-action của agent i;
- `R_team`: shared reward;
- `P`: transition qua simulator/challenge;
- `gamma`: discount factor.

---

## 8.2. Observation của mỗi agent

Để tránh state space quá lớn, observation được nén thành feature rời rạc.

### Cho xe tuần tra

```text
obs_i = (
    position_region,
    fuel_bin,
    remaining_steps_bin,
    nearest_task_1_cost_bin,
    nearest_task_2_cost_bin,
    target_stock_bin,
    target_type_seen_flag,
    refuel_distance_bin,
    teammate_target_summary
)
```

### Cho xe tiếp nhiên liệu

```text
obs_i = (
    position_region,
    patrol_0_fuel_bin,
    patrol_1_fuel_bin,
    patrol_0_dp_distance_bin,
    patrol_1_dp_distance_bin,
    remaining_steps_bin
)
```

**Lưu ý:** `dp_distance` không phải khoảng cách Manhattan; đó là chi phí tới mục tiêu do DP tính trên Hex Grid.

---

## 8.3. Macro-action space

### Xe tuần tra

Thay vì chọn trực tiếp 6 hướng, agent chọn trong `K` candidate tasks gần/tốt nhất:

```text
A_patrol = {
    VISIT_TARGET_1,
    VISIT_TARGET_2,
    ...,
    VISIT_TARGET_K,
    REQUEST_REFUEL,
    IDLE
}
```

### Xe tiếp nhiên liệu

```text
A_refuel = {
    SUPPORT_PATROL_0,
    SUPPORT_PATROL_1,
    ...,
    IDLE
}
```

Nếu có 4 xe nhưng chỉ 2 xe tuần tra, action space vẫn nhỏ.

Candidate tasks được lọc bằng:

- DP cost-to-go;
- fuel feasibility;
- số bước còn lại;
- stock;
- loại udon chưa thu;
- assignment hiện tại của đồng đội.

---

## 8.4. Independent Q-Learning

Mỗi agent giữ Q-table riêng:

```text
Q_i(o_i, a_i) <- Q_i(o_i, a_i)
    + alpha * [r_i + gamma * max_a' Q_i(o'_i, a') - Q_i(o_i, a_i)]
```

Chính sách khám phá:

```text
epsilon-greedy
```

Schedule gợi ý:

```text
epsilon_start = 1.0
epsilon_end   = 0.05
epsilon_decay = 0.995
alpha         = 0.1
gamma         = 0.95
```

Đây là bộ giá trị ban đầu để thử nghiệm, không coi là tối ưu mặc định.

---

## 9. Reward design

Challenge sử dụng mục tiêu có tính **ưu tiên nhiều tầng**. Do Q-Learning cần scalar reward, proposal tách:

1. **reward để huấn luyện**;
2. **official metrics để đánh giá cuối cùng**.

### 9.1. Shared reward đề xuất

```text
r_team =
    w_type       * delta_new_udon_type
  + w_unique     * delta_unique_checkpoint_today
  + w_udon       * delta_udon
  - lambda_dup   * duplicate_assignment
  - lambda_empty * visit_empty_stock
  - lambda_fuel  * fuel_risk
  - lambda_fail  * invalid_plan
  - lambda_step  * normalized_step_cost
```

Trong đó:

- `delta_new_udon_type`: lần đầu đội thu được một loại udon mới trong trận;
- `delta_unique_checkpoint_today`: điểm mới được thu trong ngày;
- `delta_udon`: số phần udon nhận thêm;
- `duplicate_assignment`: hai patrol agent cùng được giao một task khi không cần thiết;
- `visit_empty_stock`: đến điểm đã hết stock;
- `fuel_risk`: kết thúc route ở mức fuel nguy hiểm hoặc gây kẹt agent;
- `invalid_plan`: kế hoạch không hợp lệ;
- `normalized_step_cost`: chi phí thời gian di chuyển.

### 9.2. Conflict penalty

`duplicate_assignment` là **penalty phục vụ học phối hợp**, không phải một luật phạt trực tiếp của challenge.

Mục đích là kiểm tra câu hỏi của MARL task allocation:

> Khi hai agent đều có thể chọn cùng một task, shared reward và conflict penalty có giúp chúng tự học cách phân chia nhiệm vụ không?

### 9.3. Individual reward baseline

Một baseline dùng reward cá nhân:

```text
r_i = udon_collected_by_i - movement_cost_i
```

Sau đó so sánh với shared team reward để xem reward nào tạo phối hợp tốt hơn.

---

## 10. Official evaluation tuple

Không chỉ dùng episodic return. Agent phải được đánh giá theo thứ tự ưu tiên của challenge:

```text
Score = (
    number_of_distinct_udon_types,
    total_daily_unique_udon,
    total_udon,
    -response_time
)
```

So sánh hai chiến lược bằng **lexicographic comparison** trên tuple này.

Điều này quan trọng vì một reward scalar có thể cho điểm học cao nhưng không phản ánh đúng thứ tự ưu tiên của luật thi.

---

## 11. Thuật toán hybrid

### 11.1. Training loop

```text
for episode in range(NUM_EPISODES):
    state = env.reset()

    while not done:
        # 1. Tính DP cost-to-go cho các task có khả năng chọn
        dp_features = planner.compute_costs(state)

        # 2. Mỗi agent tạo observation cục bộ
        observations = encoder(state, dp_features)

        # 3. Independent Q-Learning chọn macro-task
        macro_actions = [
            agent_i.select_action(obs_i)
            for each agent_i
        ]

        # 4. Resolve/validate assignment
        assignments = allocator.validate(macro_actions, state)

        # 5. DP tạo đường đi cụ thể
        routes = planner.plan(assignments, state)

        # 6. Chuyển route thành action plan của challenge
        plans = route_encoder(routes, state.daySteps)

        # 7. Simulator thực thi
        next_state, rewards, done, info = env.step(plans)

        # 8. Cập nhật Q-table
        for each agent_i:
            agent_i.update(obs_i, action_i, reward_i, next_obs_i)

        state = next_state
```

### 11.2. Online challenge loop

```text
GET setup
POST assignment

for each day:
    GET state
    compute DP tables
    choose macro tasks using learned Q tables
    build valid routes
    POST actions

GET result
```

Hệ thống cần cache DP result cho các target trong cùng một ngày để giảm thời gian phản hồi.

---

## 12. Baselines

Để chứng minh giá trị của từng thành phần, proposal sử dụng ít nhất bốn cấu hình.

### B0 – Random Allocation + Shortest Feasible Route

- chọn target ngẫu nhiên;
- route theo heuristic đơn giản;
- không học phối hợp.

### B1 – Greedy + Dynamic Programming

- mỗi patrol chọn target có DP cost nhỏ nhất;
- tránh target đã được agent khác chọn bằng rule thủ công;
- không có RL.

Đây là baseline mạnh cho câu hỏi: **MARL có thực sự cần thiết không?**

### B2 – MARL Allocation + Naive Routing

- IQL chọn task;
- đường đi dùng BFS / greedy không xét đầy đủ cost giao thông và fuel.

Đây là ablation cho thành phần DP.

### B3 – Proposed Hybrid: IQL + DP

- IQL chọn task;
- Value Iteration / Policy Iteration lập route;
- shared reward;
- phối hợp refuel.

### B4 – Hybrid + Individual Reward

- giống B3 nhưng reward riêng;
- dùng để đánh giá vai trò của shared team reward.

---

## 13. Thiết kế thí nghiệm

## Experiment 1 – Value Iteration vs Policy Iteration

### Mục tiêu

Đo hiệu năng DP trên bản đồ lục giác với nhiều trạng thái traffic.

### Biến độc lập

- `gamma ∈ {0.90, 0.95, 0.99}`;
- map nhỏ và vừa;
- tỷ lệ núi / đường / ao;
- traffic profile;
- target distance.

### Metrics

- Bellman sweeps;
- policy improvement steps;
- runtime;
- route step cost;
- fuel cost;
- policy agreement.

### Kỳ vọng cần kiểm chứng

Hai thuật toán nên tìm policy tương đương hoặc gần tương đương khi hội tụ; khác biệt chính nằm ở số vòng update và runtime.

---

## Experiment 2 – Emergent Coordination with IQL

### Cấu hình

Bắt đầu với môi trường nhỏ:

```text
2 patrol agents
4–8 candidate tasks
1 day / short episodes
```

Sau đó mở rộng:

```text
2 patrol agents + 1 refuel agent
nhiều ngày
traffic thay đổi theo ngày
```

### So sánh

- shared reward;
- individual reward;
- conflict penalty thấp/vừa/cao;
- epsilon decay nhanh/chậm.

### Metrics

- conflict rate;
- overlap ratio;
- task coverage;
- total reward;
- distinct udon types;
- learning stability across seeds.

---

## Experiment 3 – Hybrid Ablation

So sánh:

```text
B0 Random
B1 Greedy + DP
B2 MARL + Naive Route
B3 MARL + DP
```

### Mục tiêu

Tách đóng góp của:

- task allocation;
- route planning;
- shared reward.

### Metrics chính

```text
Distinct udon types
Daily unique checkpoints
Total udon
Invalid action rate
Fuel failure rate
Mean movement cost
Mean planning time
```

---

## Experiment 4 – Refueling Coordination

### Scenario

Tạo các episode trong đó một số điểm có reward cao nhưng ở xa, khiến patrol cần support từ refuel agent.

### So sánh

- không có refuel planning;
- refuel bằng heuristic nearest-patrol;
- refuel bằng IQL macro-task.

### Metrics

- số lần patrol phải dừng do thiếu nhiên liệu;
- số lần refuel thành công;
- udon thu thêm nhờ refuel;
- detour cost của refuel agent;
- tỷ lệ rendezvous thất bại.

---

## 14. Số lần chạy và tính tái lập

Mỗi cấu hình stochastic nên chạy với nhiều seed độc lập.

Đề xuất:

```text
5–10 seeds / configuration
```

Báo cáo:

- mean;
- standard deviation;
- confidence interval nếu đủ số mẫu;
- learning curves có dải biến thiên.

Mỗi experiment lưu:

```text
seed
hyperparameters
map_id
traffic configuration
agent assignment
reward configuration
result metrics
```

---

## 15. Các biểu đồ / kết quả cần có

### DP

- heatmap giá trị `V(s)` trên Hex Grid;
- visualization optimal policy;
- Bellman residual theo iteration;
- số sweeps tới convergence;
- VI vs PI runtime.

### MARL

- episodic team reward;
- conflict rate theo episode;
- unique-task coverage;
- epsilon schedule;
- shared vs individual reward.

### Challenge-level

- số loại udon theo ngày;
- tổng udon tích lũy;
- fuel trajectory của từng patrol;
- route map của từng agent;
- traffic state theo ngày;
- response/planning time.

---

## 16. Giả thuyết nghiên cứu

### H1

**DP cost-to-go** sẽ tốt hơn khoảng cách hình học/BFS trong các bản đồ có núi và đường ùn tắc vì chi phí thực tế không tỷ lệ trực tiếp với số ô.

### H2

**Shared team reward** sẽ giảm tỷ lệ hai agent chọn cùng một nhiệm vụ so với individual reward.

### H3

IQL có thể hình thành một mức phối hợp hữu ích mà không cần communication protocol tường minh, nhưng learning curve sẽ có variance lớn hơn single-agent learning.

### H4

Conflict penalty quá nhỏ sẽ không đủ ngăn task duplication; conflict penalty quá lớn có thể làm policy quá bảo thủ.

### H5

Kiến trúc hybrid sẽ có sample efficiency tốt hơn một agent học trực tiếp hành động di chuyển từng bước vì DP loại bỏ phần search đường đi khỏi bài toán học.

Các giả thuyết trên là **nội dung cần kiểm chứng bằng thí nghiệm**, không được coi là kết quả có sẵn.

---

## 17. Phạm vi triển khai

Để phù hợp mini-project, triển khai theo ba mức.

### Core scope – bắt buộc

- Hex Grid simulator;
- chi phí địa hình và giao thông;
- Value Iteration;
- Policy Iteration;
- Independent Q-Learning;
- 2 learning agents;
- nhiều task;
- shared vs individual reward;
- Greedy+DP baseline;
- Hybrid IQL+DP;
- nhiều random seeds.

### Challenge extension

- 4 agents;
- patrol + refuel roles;
- fuel;
- stock;
- nhiều ngày;
- traffic update;
- API adapter.

### Không nằm trong core scope

- MAPPO;
- QMIX;
- graph neural network;
- deep Q-network cho joint action space;
- opponent modeling phức tạp;
- end-to-end neural path planning.

---

## 18. Giới hạn mô hình

1. **Independent Q-Learning gặp non-stationarity** vì mỗi agent quan sát môi trường trong khi policy của agent khác cũng thay đổi.
2. **State discretization làm mất thông tin**, đặc biệt khi map lớn.
3. **Reward shaping có thể lệch official objective**, vì challenge dùng thứ tự ưu tiên nhiều tiêu chí.
4. **DP giả định biết cost trong ngày**, phù hợp với `day_state`, nhưng không dự đoán hoàn hảo traffic của các ngày sau.
5. **Task allocation dạng macro-action** có thể bỏ lỡ chiến lược cần đổi mục tiêu giữa ngày.
6. **Q-table khó scale** khi tăng mạnh số candidate task hoặc số agent.
7. Simulator tự xây cần được kiểm tra cẩn thận để không khác luật challenge.

---

## 19. Kế hoạch triển khai mã nguồn

```text
procon-dp-marl/
|
+-- README.md
+-- requirements.txt
+-- configs/
|   +-- default.yaml
|   +-- experiments.yaml
|
+-- src/
|   +-- env/
|   |   +-- hex_grid.py
|   |   +-- procon_simulator.py
|   |   +-- traffic.py
|   |   +-- rewards.py
|   |
|   +-- planning/
|   |   +-- value_iteration.py
|   |   +-- policy_iteration.py
|   |   +-- dp_route_planner.py
|   |
|   +-- marl/
|   |   +-- iql_agent.py
|   |   +-- task_encoder.py
|   |   +-- allocator.py
|   |
|   +-- hybrid/
|   |   +-- hybrid_controller.py
|   |   +-- route_encoder.py
|   |
|   +-- api/
|       +-- procon_client.py
|
+-- experiments/
|   +-- exp1_dp_comparison.py
|   +-- exp2_iql_coordination.py
|   +-- exp3_hybrid_ablation.py
|   +-- exp4_refuel.py
|
+-- notebooks/
|   +-- visualize_values.ipynb
|   +-- analyze_results.ipynb
|
+-- results/
    +-- raw/
    +-- figures/
    +-- tables/
```

---

## 20. Pseudocode cho DP route planner

```python
def value_iteration(states, actions, transition, reward, gamma=0.95, theta=1e-6):
    V = {s: 0.0 for s in states}

    while True:
        delta = 0.0
        new_V = V.copy()

        for s in states:
            q_values = []
            for a in valid_actions(s):
                s_next = transition(s, a)
                q = reward(s, a, s_next) + gamma * V[s_next]
                q_values.append(q)

            new_V[s] = max(q_values) if q_values else 0.0
            delta = max(delta, abs(new_V[s] - V[s]))

        V = new_V
        if delta < theta:
            break

    policy = extract_greedy_policy(V)
    return V, policy
```

---

## 21. Pseudocode cho Independent Q-Learning

```python
class IQLAgent:
    def __init__(self, alpha=0.1, gamma=0.95, epsilon=1.0):
        self.Q = defaultdict(lambda: np.zeros(NUM_MACRO_ACTIONS))
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

    def act(self, obs, valid_actions):
        if np.random.rand() < self.epsilon:
            return random.choice(valid_actions)

        q = self.Q[obs]
        return max(valid_actions, key=lambda a: q[a])

    def update(self, obs, action, reward, next_obs, next_valid_actions):
        best_next = max(self.Q[next_obs][a] for a in next_valid_actions)
        td_target = reward + self.gamma * best_next
        td_error = td_target - self.Q[obs][action]
        self.Q[obs][action] += self.alpha * td_error
```

---

## 22. Lập kế hoạch 25 giờ

| Giai đoạn | Công việc | Thời lượng dự kiến |
|---|---|---:|
| 1 | Đọc luật, chuẩn hóa Hex Grid, simulator tối thiểu | 3 h |
| 2 | Value Iteration + Policy Iteration | 4 h |
| 3 | Test và visualization DP | 2 h |
| 4 | Task abstraction + state discretization | 2 h |
| 5 | Independent Q-Learning | 4 h |
| 6 | Hybrid controller DP + MARL | 3 h |
| 7 | Baseline + ablation experiments | 3 h |
| 8 | Phân tích kết quả và vẽ biểu đồ | 2 h |
| 9 | Hoàn thiện report / demo | 2 h |
| **Tổng** |  | **25 h** |

---

## 23. Deliverables

### 23.1. Technical Report

Báo cáo 7–10 trang theo cấu trúc:

1. Application context and problem statement
2. MDP / Markov Game formulation
3. Methodology
4. Experimental setup
5. Results
6. Discussion and application interpretation
7. Conclusion

### 23.2. Source Code

- simulator;
- DP algorithms;
- IQL agents;
- hybrid controller;
- experiment scripts;
- config files;
- instructions chạy lại experiment.

### 23.3. Oral Presentation

Gợi ý 15 phút:

```text
3 phút  : Challenge + RL formulation
4 phút  : Hybrid DP + MARL method
5 phút  : Experiments + plots
3 phút  : Discussion + limitations + demo
```

---

## 24. Tiêu chí thành công

Project được xem là thành công nếu:

1. **Value Iteration và Policy Iteration** chạy đúng và sinh policy hợp lý trên Hex Grid;
2. có so sánh định lượng rõ ràng giữa hai phương pháp DP;
3. **Independent Q-Learning** học được policy phân công task tốt hơn random baseline;
4. có phân tích shared vs individual reward;
5. hybrid controller sinh được kế hoạch hợp lệ với fuel/daySteps;
6. Hybrid IQL+DP được so sánh với Greedy+DP và MARL+naive routing;
7. kết quả được báo cáo trên nhiều random seeds;
8. giải thích được hành vi học được trong bối cảnh PROCON, không chỉ trình bày learning curve.

---

## 25. Đóng góp học thuật / kỹ thuật kỳ vọng

Đóng góp của mini-project không nằm ở việc tạo một thuật toán MARL mới, mà ở việc **thiết kế và kiểm chứng một decomposition hợp lý cho bài toán challenge thực tế**:

> **Cooperative MARL chịu trách nhiệm phân công nhiệm vụ, trong khi model-based Dynamic Programming chịu trách nhiệm tối ưu đường đi.**

Qua đó, project có thể trả lời ba câu hỏi có giá trị:

1. Khi mô hình chuyển trạng thái cấp thấp đã biết, có nên học cả navigation bằng RL hay nên giải bằng planning?
2. Independent learners có thể phối hợp được đến mức nào khi cùng chia sẻ mục tiêu đội nhưng không giao tiếp trực tiếp?
3. Việc đưa DP cost-to-go vào observation của MARL có giúp task allocation phản ánh đúng địa hình, traffic và fuel hơn khoảng cách hình học hay không?

---

## 26. Tên đề tài đề xuất cho báo cáo

### Tiếng Anh

**Hybrid Dynamic Programming and Multi-Agent Reinforcement Learning for Cooperative Task Allocation and Route Planning in a Hexagonal Gridworld**

### Tiếng Việt

**Kết hợp Quy hoạch Động và Học Tăng cường Đa Tác nhân cho Phân công Nhiệm vụ và Lập đường trên Bản đồ Lục giác PTIT PROCON 2026**

---

## 27. Nguồn cơ sở của proposal

Proposal này được xây dựng dựa trên:

- luật và API của PTIT PROCON 2026 do người dùng cung cấp qua các ảnh chụp `procon.ptit.edu.vn_rules.png`, `procon.ptit.edu.vn_docs.png`, `procon.ptit.edu.vn_team.png`;
- tài liệu **Advanced Reinforcement Learning – Mini-Projects, Master VMCS / PTIT 2026**;
- đặc biệt là **Mini-Project 1 – Dynamic Programming for Gridworld** và **Mini-Project 7 – Multi-Agent Reinforcement Learning for Cooperative Task Allocation**.

---

## 28. Kết luận

Đề tài **DP-MARL HEXUDON** biến PTIT PROCON 2026 thành một môi trường nghiên cứu RL có cấu trúc rõ ràng và vừa sức cho mini-project:

- **DP** giải quyết navigation có model;
- **IQL** giải quyết cooperative task allocation không có policy phối hợp sẵn;
- **shared reward** khuyến khích mục tiêu đội;
- **refueling** tạo bài toán phối hợp tài nguyên thực tế;
- **traffic + terrain** tạo biến thiên chi phí đường đi;
- **official challenge metrics** cung cấp tiêu chí đánh giá gần thực tế hơn chỉ episodic reward.

Phạm vi này đủ để có một implementation chạy được, thí nghiệm có kiểm soát, ablation rõ ràng và phần phân tích đúng tinh thần của môn Advanced Reinforcement Learning.
