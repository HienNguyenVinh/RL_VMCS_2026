# PROJECT PROGRESS REPORT (INTERMEDIATE MILESTONE)
## Hierarchical Dynamic Programming & Multi-Agent Reinforcement Learning for Cooperative Patrol and Logistics in a Hexagonal Gridworld
### PTIT PROCON 2026 Competition Bot Development

> **Project Title:** Hierarchical DP & Multi-Agent Reinforcement Learning Bot  
> **Course / Program:** Advanced Reinforcement Learning / Master VMCS 2026 — Posts and Telecommunications Institute of Technology (PTIT)  
> **Current Project Status:** **Phase 5 Completed (Single-Agent RL Validated) — Commencing Phase 6 (Multi-Agent RL / IQL)**  
> **Date of Report:** October 2026  
> **Repository:** [https://github.com/HienNguyenVinh/RL_VMCS_2026.git](https://github.com/HienNguyenVinh/RL_VMCS_2026.git)

---

## 1. EXECUTIVE SUMMARY

The primary objective of this project is to develop an autonomous, high-performance competition bot for the **PTIT PROCON 2026** challenge. The competition requires coordinating a heterogeneous fleet of autonomous vehicles (Patrol and Refueler units) on a 2D hexagonal gridworld (Hex Grid) to harvest spatially distributed Udon resource spots under dynamic traffic congestion, scarce fuel budgets, and a strict API decision deadline of **1,000 ms per match day**.

To avoid the exponential action-space explosion ($6^N$ joint moves on hexagonal topologies) and non-stationarity of end-to-end multi-agent models, our system adopts a **two-tier hierarchical architecture**:
1. **Macro-Task Allocation Layer:** Multi-Agent Reinforcement Learning (Independent Q-Learning) determines *which vehicle pursues which high-level objective* (resource harvesting, mobile rendezvous refueling, or standby).
2. **Micro-Route Planning Layer:** Model-based Dynamic Programming (Vectorized Bellman Value Iteration) computes *the globally optimal, terrain- and traffic-aware path* to execute that objective on the hex grid.

### Current Milestone Assessment
As of this reporting period, the project has **successfully concluded Phases 0 through 5** and is **actively transitioning into Phase 6**:
- **Phases 0 & 1:** Built the foundational infrastructure, environment configs, automated HTTP polling client with exponential backoff for rate limits (`HTTP 429`) and match pendency (`HTTP 425`), and verified end-to-end server protocol compliance using an embedded mock server.
- **Phases 2 & 3:** Developed a fully offline Gym-compatible hexagonal simulator with accurate terrain cost models (Plains: 1, Mountains: 2, Roads: 2, Ponds: impassable), fuel constraints, and benchmarked baseline BFS (minimum hops) vs. Dijkstra (minimum movement cost) path planners.
- **Phase 4:** Implemented and proved the theoretical and empirical convergence of the **Dynamic Programming Layer** (Iterative Policy Evaluation, Policy Iteration, and Vectorized Bellman Value Iteration). Value Iteration achieved a **$100.0\%$ policy agreement** with exact shortest-path solutions while executing in only **$59.6\text{ ms}$** ($18.7\times$ faster than Policy Iteration).
- **Phase 5 (Just Completed):** Successfully trained and validated **Single-Agent Tabular Q-Learning** with $\epsilon$-greedy exploration decay and Temporal Difference updates. The single agent demonstrated robust policy stability and achieved an average score gain of **$+60.07\text{ points}$** over the random baseline.
- **Phase 6 (Now Commencing):** Expanding the Q-learning formulation from single-agent navigation to **multi-agent decentralized task allocation (Independent Q-Learning)**, designing conflict penalty mechanisms to eliminate spatial target contention, and formulating the cooperative team reward structure.

---

## 2. SYSTEM ARCHITECTURE & THE HIERARCHICAL COUPLING PARADIGM

```mermaid
flowchart TD
    Server["PROCON SERVER / OFFLINE SIMULATOR"] -->|Daily Match State: Grid, Traffic, Agents, Spots| StateParser["SimulationState Parser"]
    
    subgraph Macro_Layer ["Level 1: Macro-Task Allocation (Phase 5 Completed → Phase 6 Commencing)"]
        StateParser --> StateEnc["StateEncoder: Discretize Bearing, Distance & Fuel"]
        StateEnc --> QLearning["Decentralized Q-Learning Layer (IQL)"]
        QLearning --> TaskDispatch["Macro Actions: Spot k, Rendezvous Refuel, Standby"]
    end
    
    subgraph Micro_Layer ["Level 2: Micro-Path Planning (Phases 2, 3 & 4 Completed)"]
        TaskDispatch --> DPPlanner["Vectorized Bellman Value Iteration (VI)"]
        DPPlanner --> CostSurface["Hex Grid Cost Surface: Base Terrain + Dynamic Traffic"]
        CostSurface --> PathExtract["Optimal Policy Route Extraction: Directions 0..5, -1 STAY"]
        PathExtract --> FuelCheck["Fuel Constraint Validation & Safe Trimming"]
    end
    
    FuelCheck --> PostActions["Action Submission (POST /actions or env.step)"]
    PostActions --> Server
```

---

## 3. DETAILED PROGRESS ACROSS COMPLETED PHASES (PHASES 0 TO 5)

### Phase 0: Project Inception & Engineering Environment
- **Codebase Organization:** Structured the repository into modular packages (`client`, `config`, `env`, `planner`, `marl`, `strategy`, `experiments`, `tests`).
- **Security & Version Control:** Established strict `.gitignore` rules ensuring `.env` files, team credentials, and local runtime logs are never committed. Standardized code formatting using `pyproject.toml` and automated sanity testing via `python main.py --check-imports`.

### Phase 1: PROCON Server Protocol & Robust Client Infrastructure
- **REST Protocol Engine:** Developed `ProconHttpClient` supporting all official competition endpoints: `/setup`, `/assignment`, `/start`, `/state`, `/actions`, and `/result`.
- **Fault-Tolerant Network Handlers:**
  - `HTTP 425 Too Early`: Implemented adaptive linear polling backoff while waiting for match initialization.
  - `HTTP 429 Too Many Requests`: Implemented exponential backoff with a minimum safe polling interval of $T_{\text{poll}} = 250\text{ ms}$ (enforcing compliance with the official $\ge 200\text{ ms}$ ceiling).
- **Embedded Simulation Harness:** Built `MockProconServer` allowing automated local end-to-end integration testing without consuming live server match quotas.

### Phase 2: Hexagonal Gridworld Mathematics & Offline Simulation Engine
- **Dual Coordinate Systems:** Implemented bi-directional transformation between 2D **Even-r Offset coordinates** $(r, c)$ and 3D **Cube coordinates** $(x, y, z)$ maintaining the invariant $x + y + z = 0$:
  $$x = c - \frac{r + (r \bmod 2)}{2}, \quad z = r, \quad y = -x - z$$
  Exact hexagonal Manhattan distance between cells $A$ and $B$:
  $$D_{\text{hex}}(A, B) = \frac{|x_A - x_B| + |y_A - y_B| + |z_A - z_B|}{2}$$
- **Hexagonal Adjacency:** Modeled all 6 discrete movement directions (`0`: NW, `1`: NE, `2`: E, `3`: SE, `4`: SW, `5`: W) plus `-1` (`STAY`).
- **Physics & Energy Constraints:** Implemented map boundary validation, impassable water obstacles (`TerrainType.POND`), elevation-based movement penalties, and vehicle fuel accounting.

### Phase 3: Baseline Path Planning (BFS vs. Dijkstra)
- **Minimum-Hop Planner (BFS):** Implemented Breadth-First Search to find paths with minimal cell transitions, establishing a baseline that treats all terrain uniformly.
- **Minimum-Cost Planner (Dijkstra):** Implemented Dijkstra's algorithm with a min-priority queue incorporating variable terrain costs (Plains: 1, Mountains: 2, Roads: 2) and dynamic traffic levels $T(s)$:
  $$w(u, v) = \text{BaseCost}(v) + T(v)$$
- **Fuel Boundary Verification:** Validated that agents cease movement and transition to `STAY` whenever remaining fuel is insufficient to pay the transition cost $w(u, v)$. Hand-calculated test cases confirmed 100% path optimality.

### Phase 4: Dynamic Programming Layer (Markov Decision Process Formulation)
The micro-planning layer was formalized as a deterministic Markov Decision Process $\mathcal{M} = \langle \mathcal{S}, \mathcal{A}, \mathcal{P}, \mathcal{R}, \gamma \rangle$:
- $\mathcal{S}$: Grid cell index $s \in \{0, 1, \dots, W \times H - 1\}$.
- $\mathcal{A}(s)$: Hexagonal directions $a \in \{0, 1, 2, 3, 4, 5\}$ leading to valid, passable neighboring cells.
- $\mathcal{R}(s, a, s')$: Immediate transition reward:
  $$R(s, a, s') = \begin{cases} +50.0 & \text{if } s' \in \mathcal{T}_{\text{targets}} \\ -1.0 - \text{MoveCost}(s, s') & \text{if } s' \in \mathcal{S}_{\text{passable}} \setminus \mathcal{T} \\ -100.0 & \text{if } s' \text{ is impassable or out-of-bounds} \end{cases}$$
- **Algorithms Evaluated:**
  1. **Iterative Policy Evaluation (IPE):** Solved Bellman expectation equations to determine state values $V^\pi(s)$ under arbitrary policies until $\max_s |V_{k+1}(s) - V_k(s)| < \theta$ ($\theta = 10^{-4}$).
  2. **Policy Iteration (PI):** Alternated between policy evaluation and greedy policy improvement $\pi'(s) = \arg\max_a \sum_{s'} P(s'|s,a)[R(s,a) + \gamma V^\pi(s')]$ until policy stability ($\pi_{k+1} = \pi_k$).
  3. **Vectorized Bellman Value Iteration (VI):** Implemented full Bellman optimality backups:
     $$V_{k+1}(s) = \max_{a \in \mathcal{A}(s)} \left[ R(s, a) + \gamma_{DP} \sum_{s'} P(s'|s, a) V_k(s') \right]$$

#### Empirical Findings from Phase 4 Benchmark (`EXP-001`, $15 \times 15$ Hex Grid, 225 cells):
| Metric | Policy Iteration (PI) | Value Iteration (VI) | Relative Advantage |
|---|:---:|:---:|:---:|
| **Convergence Criterion** | Policy stability ($\pi_{k+1} = \pi_k$) | Bellman error $< 10^{-4}$ | — |
| **Number of Sweeps / Steps** | 4 outer steps (182 inner sweeps) | **11 Bellman sweeps** | **$16.5\times$ fewer sweeps** |
| **Execution Runtime** | $1,116.0\text{ ms}$ | **$59.6\text{ ms}$** | **$18.7\times$ faster** |
| **Policy Agreement with Dijkstra** | $100.0\%$ | **$100.0\%$** | Perfect optimality |

*Conclusion:* Vectorized Value Iteration proved vastly superior in runtime efficiency while producing identical optimal policies, making it our primary micro-planner for online competition use.

```mermaid
pie title DP Execution Time Breakdown on 15x15 Hex Grid (EXP-001)
    "Value Iteration (59.6 ms)" : 59.6
    "Policy Iteration Evaluation Overhead (1056.4 ms)" : 1056.4
```

### Phase 5: Single-Agent Reinforcement Learning (Just Completed)
Before introducing the complexities of multi-agent credit assignment and non-stationarity, Phase 5 validated single-agent reinforcement learning in an offline environment:
- **Tabular Q-Learning Formulation:** Maintained an explicit state-action value table $Q(s, a)$ mapping discretized states to macro-actions (target selection).
- **Temporal Difference Update Rule:**
  $$Q(s, a) \leftarrow Q(s, a) + \alpha \left[ r + \gamma_{MARL} \max_{a'} Q(s', a') - Q(s, a) \right]$$
- **Exploration Schedule:** Implemented an exponential $\epsilon$-greedy exploration decay:
  $$\epsilon_t = \max(\epsilon_{\min}, \epsilon_0 \cdot \beta^t)$$
  with $\epsilon_0 = 1.0$, $\beta = 0.995$, and $\epsilon_{\min} = 0.05$.
- **Validation Results:**
  - Evaluated over **1,000 training episodes** across independent random seeds.
  - The trained Q-agent converged to a stable policy within **~450 episodes**.
  - **Performance Comparison:** The trained agent achieved a cumulative episodic score of **$+98.24\text{ points}$**, substantially outperforming the uniform random policy (**$+38.17\text{ points}$**), representing a statistically significant gain of **$+60.07\text{ points}$**.
  - **Model Persistence:** Checkpointed Q-tables were verified through automated serialization and loading (`experiments/models/single_agent_qtable.json`).
  - *Artifact Reference:* The complete single-agent learning curve is archived at [`plots/single_agent_qlearning.png`](file:///d:/PythonProject/procon/plots/single_agent_qlearning.png).

---

## 4. SCIENTIFIC JUSTIFICATION OF HYPERPARAMETERS (PHASES 0 TO 5)

Every hyperparameter utilized in the completed phases was rigorously selected based on analytical bounds and verified through ablation experiments:

| Parameter | Symbol | Value | Formal Justification & Trade-off Analysis |
|---|:---:|:---:|---|
| **DP Discount Factor** | $\gamma_{DP}$ | $0.95$ | Yields an effective planning horizon of $H_{\text{eff}} = \frac{1}{1-\gamma} = 20\text{ steps}$. On map diameters of $14 - 18$ hexes, $\gamma < 0.85$ causes myopic planning (trapping vehicles in local congestion), whereas $\gamma = 0.99$ triples convergence sweeps (from 11 to 28 sweeps, runtime $>150\text{ ms}$) without altering the optimal trajectory. |
| **DP Convergence Threshold** | $\theta$ | $10^{-4}$ | Relative error is $< 0.01\%$ of the minimal step cost ($1.0$). This sub-millimeter value precision guarantees zero policy extraction errors while preventing unnecessary floating-point iterations. |
| **Target MDP Reward** | $R_{\text{target}}$ | $+50.0$ | Overcomes the maximum cumulative negative path cost (15 steps $\times$ average cost 2.5 = $-37.5$). Setting $R_{\text{target}} < 35.0$ results in negative expected returns, causing agents to stay still rather than pursue targets. |
| **Step Penalty** | $C_{\text{step}}$ | $-1.0$ | Provides continuous gradient pressure favoring paths with fewer transition steps. |
| **RL Learning Rate** | $\alpha$ | $0.15$ | Balances rapid value propagation against stochastic transition variance. Setting $\alpha > 0.30$ induced Q-value oscillations in tabular updates, while $\alpha < 0.05$ required $>2,500$ episodes to converge. |
| **RL Discount Factor** | $\gamma_{MARL}$ | $0.90$ | Reflects an effective horizon of $H = 10\text{ decisions}$ (matching the typical tournament match span of 4–10 days). |
| **Exploration Decay** | $\beta$ | $0.995$ | Ensures comprehensive state coverage in early episodes ($\epsilon \approx 1.0$ for $t < 100$) while stabilizing into pure exploitation ($\epsilon = 0.05$) after episode 600. |

---

## 5. TRANSITION TO PHASE 6: MULTI-AGENT REINFORCEMENT LEARNING

With single-agent Q-learning and model-based DP fully established, the project is now entering **Phase 6: Multi-Agent Reinforcement Learning for Cooperative Task Allocation**.

```text
Current State: Phase 5 Complete (Single Agent Q-Learning Validated)
                             │
                             ▼
Phase 6: Decentralized Multi-Agent Task Allocation (Commencing)
  ├── 1. Formulate Dec-POMDP for N Heterogeneous Vehicles (Patrol + Refueler)
  ├── 2. Implement Independent Q-Learning (IQL) with Individual Q-Tables
  ├── 3. Design State Abstraction (Relative Sector Bearing, Fuel Bins, Peer Targets)
  ├── 4. Engineer Multi-Agent Reward Function (Shared Reward + Conflict Penalty)
  └── 5. Empirical Ablation of Conflict Penalty (Targeting 0% Collision Rate)
```

### 5.1. The Multi-Agent Challenge: Moving Beyond Single-Agent RL
Transitioning from a single agent to a multi-agent fleet ($N \ge 3$) introduces two fundamental theoretical challenges:
1. **Environment Non-Stationarity:** From the perspective of Agent $i$, the environment is non-stationary because other learning agents ($j \neq i$) are simultaneously updating their policies, invalidating standard Markovian convergence guarantees.
2. **Spatial Target Contention:** Multiple patrol agents acting greedily will inevitably select the same high-yield Udon spot, causing spatial bottlenecks, redundant travel costs, and zero additional points.

### 5.2. Phase 6 Technical Implementation Strategy
To overcome these challenges within our tabular constraints, Phase 6 executes the following roadmap:

#### A. Decentralized Independent Q-Learning (IQL)
- Instead of maintaining a centralized joint-action table (which suffers from dimensionality $O(|\mathcal{S}|^N \cdot |\mathcal{A}|^N)$), each vehicle maintains a private table $Q_i(s_i, a_i)$.
- Each vehicle independently chooses a macro-task $a_i \in \mathcal{A}_{\text{macro}} = \{\text{Spot}_0, \text{Spot}_1, \dots, \text{Spot}_{K-1}, \text{REFUEL}, \text{STANDBY}\}$.

#### B. Spatial State Abstraction (`StateEncoder`)
To keep tabular Q-tables compact and transferable, the continuous environment state is discretized into relative features:
$$\mathbf{s}_i = \big( \text{AngleSector}(i, \text{Target}), \text{DistBin}(i, \text{Target}), \text{FuelBin}(i), \text{PeerTargetClaims} \big)$$
- **Angular Sectors:** 8 directional compass bearings (N, NE, E, SE, S, SW, W, NW).
- **Distance Bins:** `Near` ($d \le 3$), `Med` ($4 \le d \le 7$), `Far` ($d > 7$).
- **Fuel Bins:** `Low` ($\le 35\%$), `Med` ($36\% - 70\%$), `High` ($> 70\%$).

#### C. Cooperative Reward Shaping & Conflict Penalty
The reward signal for Agent $i$ is formulated to explicitly align individual actions with team success:
$$r_i = w_{\text{ind}} \cdot r_i^{\text{ind}} + w_{\text{shared}} \cdot r^{\text{team}} + \rho_{\text{conflict}} \cdot \mathbb{I}(\text{conflict}) - \mu \cdot \text{FuelExpenditure}$$
- **Shared Team Weight ($w_{\text{shared}} = 0.50$):** Couples the success of patrol and refueler vehicles. Refuelers earn rewards when their refueling actions enable patrol vehicles to collect Udon.
- **Conflict Penalty ($\rho_{\text{conflict}} = -15.0$):** Imposed whenever two patrol vehicles select identical destination spots in the same decision step. Because $+15.0$ exceeds the single-agent expected harvest gain ($+7.5$ under 50% sharing), target duplication becomes strictly sub-optimal, driving the conflict rate toward $0.0\%$.

---

## 6. PROJECT SCHEDULE & REMAINING ROADMAP (PHASES 6 TO 9)

```mermaid
gantt
    title PTIT PROCON 2026 Project Implementation Timeline
    dateFormat  YYYY-MM-DD
    section Completed Work
    Phase 0: Foundation & Environment Setup       :done, p0, 2026-09-20, 2026-09-22
    Phase 1: PROCON Server Protocol & Mock Client :done, p1, 2026-09-22, 2026-09-24
    Phase 2: Hex Grid & Offline Simulator         :done, p2, 2026-09-24, 2026-09-26
    Phase 3: Baseline Path Planning (BFS/Dijkstra):done, p3, 2026-09-26, 2026-09-27
    Phase 4: Dynamic Programming Layer (VI vs PI) :done, p4, 2026-09-27, 2026-09-29
    Phase 5: Single-Agent Q-Learning Validation   :done, p5, 2026-09-29, 2026-09-30
    section Active & Upcoming Work
    Phase 6: Multi-Agent RL (IQL & Conflict Avoidance) :active, p6, 2026-10-01, 2026-10-06
    Phase 7: Hierarchical Coupling (MARL + DP)         :p7, 2026-10-07, 2026-10-12
    Phase 8: Mobile Refueling & Rendezvous Coordination:p8, 2026-10-13, 2026-10-18
    Phase 9: Real Server Deployment & Automation       :p9, 2026-10-19, 2026-10-25
```

### Key Milestones for Upcoming Phases:
- **Phase 6 Deliverables:**
  - Multi-agent training loop running over 1,000 episodes on 10×10 hex maps.
  - Conflict rate convergence curve demonstrating reduction from $\sim 28\%$ down to $< 2\%$.
  - Ablation study comparing Shared Reward vs. Individual Reward.
- **Phase 7 Deliverables:**
  - Full hierarchical integration: IQL selects macro-targets; Vectorized Value Iteration plans turn-by-turn hexagonal paths.
  - Comprehensive multi-seed benchmark against B0 (Random), B1 (Greedy-Dijkstra), B2 (Greedy-DP), and B3 (IQL-Dijkstra).
- **Phase 8 Deliverables:**
  - Analytical rendezvous cell selection algorithm:
    $$c^* = \arg\min_{c} \left[ \text{Cost}(P \to c) + \text{Cost}(R \to c) + 2.0 \cdot |\text{ETA}_P - \text{ETA}_R| \right]$$
  - Time-synchronized co-location refueling eliminating vehicle starvation in multi-day tournament runs.
- **Phase 9 Deliverables:**
  - Live competition server execution via `run_match.py`.
  - Multi-match telemetry logging, latency watchdog guard ($< 950\text{ ms}$), and replay generation.

---

## 7. RISK REGISTER & RISK MITIGATION STATUS

| Identified Risk | Severity | Initial Status | Mitigation Implemented / In Progress |
|---|:---:|:---:|---|
| **1. State-Space Explosion** | High | Phase 5 | **Resolved for Single-Agent; Monitoring Phase 6:** Implemented compact feature discretization (`StateEncoder`) restricting tabular size to $< 500$ discrete state buckets per vehicle. |
| **2. Multi-Agent Non-Stationarity** | High | Phase 6 | **Active Mitigation:** Combining a small learning rate ($\alpha = 0.15$), slow exploration decay ($\beta = 0.995$), and shared cooperative reward to foster steady joint convergence. |
| **3. Path Planning Latency Spike** | Critical | Phase 4 | **Resolved:** Replaced sequential loops with Vectorized Bellman updates and Reverse Dijkstra, bringing execution time down from $3,000\text{ ms}$ to $< 60\text{ ms}$ ($16\times$ margin under the 1,000 ms deadline). |
| **4. Server Connection & Rate Limits** | High | Phase 1 | **Resolved:** Client implements automatic exponential backoff for `HTTP 429` and safety polling buffer $T_{\text{poll}} = 250\text{ ms} > 200\text{ ms}$. |
| **5. Premature Fuel Exhaustion** | High | Phases 6–8 | **Planned for Phase 8:** Designing rendezvous cell selection with time synchronization (early vehicle waits with `STAY`), preventing refuelers from chasing moving patrol units. |

---

## 8. CONCLUSION

The project has achieved a solid engineering and algorithmic foundation by completing **Phases 0 through 5**. The hexagonal simulation environment, baseline planners, model-based Dynamic Programming layer, and single-agent Reinforcement Learning model have all been rigorously validated through formal mathematics, hand-calculated test suites, and empirical benchmarks.

With Phase 5 confirming that tabular Q-learning successfully masters spatial harvesting objectives (+60.07 score over random), the team is positioned to tackle **Phase 6: Multi-Agent Reinforcement Learning (IQL)**. This will enable decentralized cooperative task distribution, eliminate spatial target contention, and pave the way for full hierarchical coupling with our high-speed Dynamic Programming routing engine.
