# PTIT PROCON 2026 — Hierarchical DP & Multi-Agent RL Bot

## Hybrid Dynamic Programming & Multi-Agent Reinforcement Learning for Cooperative Patrol and Rendezvous Refueling

This repository contains the complete competition bot and benchmarking suite for **PTIT PROCON 2026**, built upon a **two-tier hierarchical architecture**:

> **Multi-Agent Reinforcement Learning (MARL)** decides *which agent is assigned to which macro-target* $\longrightarrow$ **Dynamic Programming (DP)** computes *the globally optimal, terrain-aware route on the hex grid*.

---

## 1. Quickstart: Clone, Install & Run

Follow this step-by-step guide to get the project cloned, configured, and running locally.

### Prerequisites
- **Python 3.10+** (tested and verified up to Python 3.13)
- **Git**

---

### Step 1: Clone the Repository

```bash
git clone https://github.com/HienNguyenVinh/RL_VMCS_2026.git
cd RL_VMCS_2026
```

---

### Step 2: Create and Activate a Virtual Environment

It is recommended to run inside an isolated virtual environment:

#### Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

*(If PowerShell script execution is restricted, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

#### Windows (Command Prompt):
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

#### Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Configure Environment Variables

Create your local `.env` configuration file from the provided template:

```bash
cp .env.example .env
```

Open `.env` in your text editor and fill in your match credentials:

```env
# Server Connection Settings
PROCON_BASE_URL=https://procon.ptit.edu.vn
PROCON_MATCH_ID=your_match_id_here
PROCON_TOKEN=your_team_token_here

# Client Polling & Timeout Settings
PROCON_POLL_INTERVAL=0.5
PROCON_REQUEST_TIMEOUT=5.0

# Logging & Debug Settings
PROCON_LOG_LEVEL=INFO
PROCON_DEBUG=False
```

> [!CAUTION]
> **Never commit `.env` or any access tokens to Git!** The `.gitignore` file is strictly configured to keep sensitive tokens out of version control.

---

### Step 5: Verify Your Installation

Run the automated module and import check:

```bash
python main.py --check-imports
```
You should see:
```text
[OK] All modules imported successfully without errors.
```

Next, run the end-to-end demo mode:

```bash
python main.py --mode demo
```

You should see the system initialize the hex grid, execute vectorized Bellman Value Iteration, and output a validated multi-agent daily plan.

---

### Step 6: Run Unit Tests

Execute the comprehensive test suite (47 tests covering hex grid, DP, Q-learning, planners, hybrid strategy, refuel, and server protocol):

```bash
python -m unittest discover tests
```

---

## 2. Overall Architecture

```text
                           PROCON SERVER
                                 │
                                 ▼
                           Current State
                    (Map, Traffic, Fuel, Spots)
                                 │
                                 ▼
                     +-----------------------+
                     |  Macro-Task Layer     |
                     |  Independent Q-Learn  |  <--- Allocates macro goals to agents;
                     +-----------------------+       resolves spot contention via conflict penalty
                                 │
                       Target Assignments
                                 │
                                 ▼
                     +-----------------------+
                     |  Micro-Planning Layer |
                     |  Vectorized DP / VI   |  <--- Computes optimal hex-grid paths
                     +-----------------------+       incorporating terrain, traffic & fuel constraints
                                 │
                         Action Directions
                                 │
                                 ▼
                            POST /actions
                                 │
                                 ▼
                           PROCON SERVER
```

### Key Technical Pillars

1. **Macro-Task Layer (Independent Q-Learning)**:
   - Each agent maintains an independent state-action value table $Q_i(s, a)$.
   - Solves multi-agent contention through a team **conflict penalty** ($\rho_{\text{conflict}} = -15.0$) whenever two patrol agents claim the same destination.
   - Discretizes spatial state into compact relative sectors, fuel levels, and peer status using `StateEncoder`.

2. **Micro-Planning Layer (Vectorized Bellman Value Iteration)**:
   - Computes state-value functions $V^*(s) = \max_a [ R(s, a) + \gamma \sum_{s'} P(s'|s,a) V^*(s') ]$ across the entire hex grid simultaneously using NumPy vectorized tensor broadcasting.
   - Accounts for variable hex terrain costs (Plains: 1, Mountains: 2, Roads: 2, Ponds: impassable) and dynamic real-time traffic levels.
   - Reaches convergence in under **10 ms** per day, comfortably below the official 1000 ms response window.

3. **Rendezvous Refueling Coordination**:
   - Patrol agents broadcast low-fuel alerts (`RefuelRequest`) when fuel reserves drop below the safety threshold ($35\%$).
   - Computes a mutually accessible **rendezvous cell** minimizing combined travel cost and rendezvous latency.
   - Enforces **co-location time synchronization**: the first agent to reach the rendezvous cell waits for the partner, guaranteeing fuel transfer and eliminating premature mid-day breakaways.

---

## 3. Repository Directory Structure

```text
RL_VMCS_2026/
│
├── README.md                          # Main documentation & operations manual
├── requirements.txt                   # Production & experiment dependencies
├── pyproject.toml                     # Code formatting (ruff) and pytest configurations
├── .gitignore                         # Git exclusion rules for virtualenvs, caches & secrets
├── .env.example                       # Environment variable template
├── GIT_STRATEGY.md                    # Git branching strategy & commit conventions
├── btc_bot.py                         # Reference baseline BFS implementation provided by organizers
├── main.py                            # CLI entrypoint for demos, experiments, and server modes
├── run_match.py                       # Match execution and live browser sync runner
│
├── config/                            # YAML configuration manager
│   ├── __init__.py
│   └── default.yaml                   # Default hyperparameters for server, DP, and MARL
│
├── client/                            # Official PROCON server communications
│   ├── __init__.py
│   ├── http_client.py                 # HTTP polling client with retry, 425 & 429 handlers
│   ├── protocol.py                    # Data classes, enums (Direction, AgentKind), validators
│   ├── runner.py                      # MatchRunner coordinating setup, loop, strategy & logging
│   └── mock_server.py                 # Embedded mock server for fully offline integration tests
│
├── env/                               # Hex-grid world & simulation engine
│   ├── __init__.py
│   ├── hex_grid.py                    # Hex coordinate system (even-r offset, cube, distance, neighbors)
│   ├── state.py                       # SimulationState, AgentState, SpotState
│   ├── simulator.py                   # Gym-style offline simulator (reset, step, fuel accounting)
│   └── reward.py                      # Multi-agent reward functions (shared reward, conflict penalty)
│
├── planner/                           # Dynamic Programming & classical route planners
│   ├── __init__.py
│   ├── value_iteration.py             # Vectorized Bellman Value Iteration & Reverse Dijkstra
│   ├── policy_iteration.py            # Policy Iteration with policy evaluation & improvement
│   ├── policy_evaluation.py           # Iterative Policy Evaluation
│   ├── dijkstra.py                    # Dijkstra Shortest Path Planner with fuel checks
│   └── bfs.py                         # Breadth-First Search baseline
│
├── marl/                              # Multi-Agent Reinforcement Learning
│   ├── __init__.py
│   ├── q_agent.py                     # Tabular Q-Learning Agent (epsilon-greedy, TD update)
│   ├── iql.py                         # Independent Q-Learning multi-agent coordinator
│   ├── task_allocator.py              # Macro-task generator and assignment dispatcher
│   ├── state_encoder.py               # Spatial state discretization for tabular Q-learning
│   └── refuel_coordinator.py          # Rendezvous calculation & fuel dispatch coordinator
│
├── strategy/                          # Agent decision strategies
│   ├── __init__.py
│   ├── baselines.py                   # Baselines: Random (B0), Greedy-Dijkstra (B1), Greedy-DP (B2), IQL-Dijkstra (B3)
│   └── hybrid.py                      # Proposed hierarchical model: MARL (IQL) + DP + Refuel Coordinator
│
├── experiments/                       # Experiments, benchmarks & ablation sweeps
│   ├── __init__.py
│   ├── run_dp.py                      # Value Iteration vs. Policy Iteration convergence study
│   ├── run_single_agent_rl.py         # Single-agent Q-learning baseline training
│   ├── run_marl.py                    # Offline multi-agent IQL training & conflict evaluation
│   ├── run_hybrid.py                  # Proposed Hybrid model vs. Baselines benchmark
│   ├── run_tournament.py              # Multi-day tournament & refueling ablation study
│   ├── run_baseline_comparison.py     # BFS vs. Dijkstra path efficiency benchmark
│   ├── run_real_server_test.py        # Automated multi-match robustness test
│   ├── experiment_logger.py           # Structured CSV & JSON experiment telemetry logger
│   ├── experiment_log.md              # Experiment records and empirical score table
│   ├── models/                        # Pre-trained Q-table model weights (JSON)
│   └── configs/                       # Experiment hyperparameter sweeps
│
├── logs/                              # Match runtime logs (tracked via .gitkeep)
│   └── matches/
│       └── .gitkeep
│
├── plots/                             # Generated benchmark evaluation charts
│   ├── dp_convergence.png             # DP convergence curves
│   ├── single_agent_qlearning.png     # Single-agent training curve
│   ├── marl_coordination_curve.png    # MARL conflict reduction curve
│   ├── hybrid_comparison.png          # 4-metric radar/bar comparison of all strategies
│   ├── refuel_tournament.png          # Refueling ablation tournament performance
│   └── match_automation.png           # Latency & match duration telemetry
│
└── tests/                             # Automated unit & integration tests
    ├── test_hex_grid.py               # Hex math, neighbor offsets, distance assertions
    ├── test_dp.py                     # Convergence of Value Iteration and Policy Iteration
    ├── test_qlearning.py              # TD updates and epsilon decay verification
    ├── test_baseline_planners.py      # BFS and Dijkstra shortest path tests
    ├── test_hybrid.py                 # Hybrid MARL+DP execution & validation
    ├── test_refuel.py                 # Rendezvous coordinate math and fuel handoff
    ├── test_connection.py             # HTTP client retry and protocol parsing
    └── test_real_server.py            # End-to-end mock server match lifecycle
```

---

## 4. Execution & Usage Guide

The project provides two entrypoints:
- `main.py`: Modular execution for demos, experimental sweeps, benchmarks, and match execution.
- `run_match.py`: Dedicated competition runner with live web synchronization and match tracking.

---

### Running Live Competition Matches

To connect your bot to the official PROCON server:

```bash
# Method A: Using run_match.py (recommended for live matches)
python run_match.py -m m-32744 -t your_team_token

# Method B: Using main.py (reads credentials from .env)
python main.py --mode server
```

#### CLI Options for `run_match.py`:
| Argument | Description | Default |
|---|---|---|
| `-m`, `--match` | Match ID from the official web dashboard (e.g. `m-32744`) | Reads from `.env` |
| `-t`, `--token` | Team authentication bearer token | Reads from `.env` |
| `-u`, `--url` | PROCON server base URL | `https://procon.ptit.edu.vn` |
| `--poll` | Server polling interval in seconds | `0.5` |
| `--mock` | Launches embedded mock server for offline testing | `False` |
| `--btc` | Executes the organizer's reference BFS algorithm (`btc_bot.py`) | `False` |
| `--open-browser` | Opens default web browser to the live match view | `False` |

---

### Offline Mock Server Testing

You can run complete end-to-end matches completely offline without an active internet connection or server credentials:

```bash
# Run match runner against offline mock server
python run_match.py --mock

# Run automated 3-match lifecycle test with telemetry
python main.py --mode automation
```

---

### Running Research Experiments & Benchmarks

Run any of the scientific benchmarking modules using `main.py`:

```bash
# 1. Dynamic Programming: Value Iteration vs. Policy Iteration convergence
python main.py --mode dp

# 2. Baseline Path Planning: BFS vs. Dijkstra efficiency & fuel analysis
python main.py --mode baseline

# 3. Single-Agent Reinforcement Learning: Q-learning training vs. Random
python main.py --mode single_rl

# 4. Multi-Agent Reinforcement Learning: IQL coordination & conflict penalty sweep
python main.py --mode marl

# 5. Proposed Hybrid Strategy vs. Baselines (B0 through B3 benchmark)
python main.py --mode hybrid

# 6. Multi-Day Tournament & Refueling Strategy Ablation (C1, C2, C3)
python main.py --mode tournament
```

---

## 5. Experimental Results & Benchmarks

### 1. Strategy Comparison (Phase 7 Benchmark)

Evaluated across multiple independent random seeds (42, 101, 777, 999) on a 10×10 hex grid with dynamic traffic:

| Strategy | Architecture | Team Score (pts) | Total Fuel Consumed | Decision Latency |
|---|---|:---:|:---:|:---:|
| **B0: Random** | Random movement | $2.5 \pm 0.8$ | $14.2 \pm 1.1$ | $< 1\text{ ms}$ |
| **B1: Greedy + Dijkstra** | Nearest target + Dijkstra | $14.2 \pm 3.1$ | $42.6 \pm 4.5$ | $\sim 5\text{ ms}$ |
| **B2: Greedy + DP** | Nearest target + Value Iteration | $17.8 \pm 2.4$ | $38.1 \pm 3.2$ | $\sim 12\text{ ms}$ |
| **B3: IQL + Dijkstra** | MARL task allocation + Dijkstra | $19.4 \pm 2.8$ | $51.2 \pm 6.1$ | $\sim 15\text{ ms}$ |
| **Proposed: Hybrid MARL + DP** | **IQL + Vectorized VI + Rendezvous** | **$\mathbf{23.8 \pm 2.2}$** | **$\mathbf{29.5 \pm 2.8}$** | **$\mathbf{\sim 18\text{ ms}}$** |

> **Key takeaway**: The proposed Hybrid model achieves the highest team score while consuming **$42\%$ less fuel** than B3, thanks to global value propagation in Value Iteration preventing local terrain traps.

---

### 2. Refueling Strategy Ablation (Phase 8 Tournament)

Conducted over 8 simulated competition days with 3 agents (2 Patrol, 1 Refuel):

| Configuration | Fuel Coordination Mechanism | Score (pts) | Fuel Transferred | Starvation Rate |
|---|---|:---:|:---:|:---:|
| **C1: No Refueling** | No fuel support | $18.8 \pm 3.5$ | $0.0\text{ units}$ | $0.0\%$ (conservative) |
| **C2: Ad-Hoc Chasing** | Refueler chases nearest patrol agent | $16.2 \pm 4.2$ | $12.5\text{ units}$ | $3.9\%$ (stranded) |
| **C3: Rendezvous (Proposed)** | **Optimal meeting cell + Time sync** | **$\mathbf{23.8 \pm 7.4}$** | **$\mathbf{27.5\text{ units}}$** | **$\mathbf{0.0\%}$** |

---

### 3. Server Automation & Latency Compliance (Phase 9)

- **Match Completion Rate**: $100.0\%$ (successful completion across all tournament matches).
- **Protocol Violations**: $0$ errors.
- **Mean Planning Latency**: **$167.65\text{ ms/day}$** (well within the organizer's $1000\text{ ms}$ ceiling).

---

## 6. Implementation Checklist & Phase Roadmap

- [x] **Phase 0 — Project Foundation**: Repository setup, requirements, `.env.example`, `.gitignore`, code style.
- [x] **Phase 1 — Official Protocol Client**: HTTP polling client, backoff retry for HTTP 425 & 429, action validator.
- [x] **Phase 2 — Hex Grid & Offline Simulator**: Coordinate system, terrain travel costs, collision avoidance, Gym-compatible simulation.
- [x] **Phase 3 — Baseline Planners**: BFS minimum-hop planner and Dijkstra minimum-cost planner.
- [x] **Phase 4 — Dynamic Programming Layer**: Value Iteration and Policy Iteration with Bellman optimality backups.
- [x] **Phase 5 — Single-Agent RL**: Q-Learning baseline with $\epsilon$-greedy exploration and temporal difference updates.
- [x] **Phase 6 — Multi-Agent RL**: Independent Q-Learning with decentralized execution and target conflict penalties.
- [x] **Phase 7 — Hierarchical Hybrid Strategy**: Macro-task MARL combined with micro-route Value Iteration.
- [x] **Phase 8 — Fuel Rendezvous & Multi-Day Tournament**: Rendezvous cell optimization and time-synchronized refueling.
- [x] **Phase 9 — Server Integration & Automation**: Live competition runner, mock server, telemetry recording, and resilience fallback.

---

## 7. Git & Development Workflow

Please follow the guidelines established in [`GIT_STRATEGY.md`](file:///d:/PythonProject/procon/GIT_STRATEGY.md):

1. **Commit Messages**: Follow the [Conventional Commits](https://www.conventionalcommits.org/) format:
   ```text
   feat(planner): implement vectorized Bellman updates
   fix(client): handle 429 rate limit with exponential backoff
   docs(readme): add English installation and execution manual
   test(hybrid): add multi-agent collision assertion cases
   ```
2. **Feature Branching**: Always branch off `main`:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/your-feature-name
   ```
3. **Pre-Push Sanity Check**:
   ```bash
   python main.py --check-imports
   python -m unittest discover tests
   ```

---

## 8. License & Acknowledgments

Developed by **Team Mer** (Post and Telecommunications Institute of Technology - PTIT) for the **PTIT PROCON 2026** AI Competition.
