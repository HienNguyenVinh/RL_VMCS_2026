# PROCON Server Connection & Match Monitoring Guide — PTIT PROCON 2026

This guide provides step-by-step instructions for:

1. Logging in with official team credentials.
2. Retrieving your team's **API token**.
3. Creating or joining test matches.
4. Connecting your bot via **HTTP Polling** or **WebSocket**.
5. Dispatching agent role assignments and multi-step action plans.
6. Monitoring live match telemetry on the official web dashboard.
7. Diagnosing and resolving common network, protocol, and rate-limit errors.

> **Official Server Base URL:**  
> `https://procon.ptit.edu.vn`

---

## 1. Team Authentication & Web Login

To access match configurations, tokens, and live visualizers, log into the official PTIT PROCON competition platform:

### Team Credentials
| Field | Value | Notes |
|---|---|---|
| **Portal URL** | `https://procon.ptit.edu.vn` | Official competition web server |
| **Username** | `team022` | Official team account ID |
| **Password** | `11aaAA@@` | Team login password |

### Login Steps:
1. Navigate to `https://procon.ptit.edu.vn` in your browser.
2. Click **Đăng nhập** (Sign In) in the upper navigation bar.
3. Enter username: `team022` and password: `11aaAA@@`.
4. Upon successful login, you will gain access to **Trận của tôi** (My Matches) and the API Token management console.

---

## 2. Required Connection Parameters

At minimum, your bot requires the following 3 variables:

```text
BASE_URL = https://procon.ptit.edu.vn
MATCH_ID = <Match Identifier, e.g. m-32744>
TOKEN    = <Team API Bearer Token>
```

> [!CAUTION]
> **Never commit your actual token directly to source control (Git/GitHub).**  
> Always supply credentials using environment variables or a local `.env` file (which is excluded by `.gitignore`).

### Setting Environment Variables

#### Local `.env` file (Recommended):
Copy `.env.example` to `.env`:
```env
PROCON_BASE_URL=https://procon.ptit.edu.vn
PROCON_MATCH_ID=m-32744
PROCON_TOKEN=bot-your_bearer_token_here
```

#### Linux / macOS Bash:
```bash
export PROCON_BASE_URL="https://procon.ptit.edu.vn"
export PROCON_MATCH_ID="m-32744"
export PROCON_TOKEN="bot-your_bearer_token_here"
```

#### Windows PowerShell:
```powershell
$env:PROCON_BASE_URL="https://procon.ptit.edu.vn"
$env:PROCON_MATCH_ID="m-32744"
$env:PROCON_TOKEN="bot-your_bearer_token_here"
```

---

## 3. Retrieving Your Team's API Token

On the PTIT PROCON web portal:

1. Log into your account (`team022`).
2. Open the **Trận của tôi** (My Matches) tab.
3. Scroll down to **Token API của đội (dùng chung mọi trận)** (Team API Tokens).
4. Copy an existing token or click **Tạo token mới** (Generate New Token).
5. Store the token securely in your local `.env` file.

The server expects this token in the HTTP Authorization header:
```http
Authorization: Bearer <token>
```

Example:
```http
Authorization: Bearer bot-34d7632cb475ab0680eac8
```

> [!TIP]
> A team can generate multiple unique tokens (e.g., dedicated tokens for different testing machines or development branches) and revoke old tokens independently if compromised.

---

## 4. Creating a Test Match

Within the **Trận của tôi** (My Matches) tab, three match types are available:

### Option A — Pre-Match Bot Verification (Kiểm tra bot trước trận)
Select:
**Kiểm tra bot trước trận → Bắt đầu kiểm tra**

This launches a lightweight test match with production timing constraints to verify:
- API token validity
- HTTP endpoint protocol compliance
- Decision latency (< 1000 ms)
- JSON request and action formatting

*This is the recommended first step whenever testing new code.*

---

### Option B — Practice Match Against AI (Luyện tập với máy)
Under **Luyện tập với máy**:
1. Select difficulty level.
2. Select number of opponent bots.
3. Set match duration (number of days).
4. Choose map size (e.g., 8×8, 10×10, 16×16).
5. Open **Nâng cao** (Advanced Settings) to adjust:
   - Steps per day (`daySteps`)
   - Turn response timeout (ms)
   - Agents per team
   - Fuel limit & starting conditions
6. Click **Tạo trận luyện tập** (Create Practice Match).

The generated match ID (e.g., `m-32743`) will immediately appear in your match list.

---

### Option C — Matchmaking Against Another Team (Tìm đối thủ thật)
Select:
**Tìm đối thủ thật** (Find Real Opponent)

Once matchmaking succeeds, the match will appear in the active match list for both teams.

---

## 5. Live Match Visualizer

To observe your bot in real time:

1. Open `https://procon.ptit.edu.vn` and log in with `team022`.
2. Navigate to **Trận của tôi** (My Matches).
3. Find your active match by ID and click to open the visualizer interface.
4. Keep the browser page open while your bot runs in the terminal to observe:
   - Agent positions on the hex grid
   - Fuel gauge levels
   - Collected Udon spot scores
   - Traffic density changes
5. When the match concludes, final scores and game replays are displayed directly on that page.

```text
+-----------------------+           +-----------------------------+
|   Terminal running    | <=======> |   Browser with live visual  |
|   run_match.py / main |           |   https://procon.ptit.edu.vn|
+-----------------------+           +-----------------------------+
```

---

## 6. Communication Protocols: HTTP Polling vs. WebSocket

| Protocol | Base URL / Path | Characteristics |
|---|---|---|
| **HTTP Polling** | `/api/v1/matches/{id}/...` | Simple request-response loop; easiest to debug; recommended |
| **WebSocket** | `/ws/v1/matches/{id}?token=...` | Persistent bi-directional socket; server pushes turn states |

---

## 7. HTTP Polling Protocol Specification

Base API path for a match:
```text
https://procon.ptit.edu.vn/api/v1/matches/{MATCH_ID}
```

Required Headers:
```http
Authorization: Bearer <TOKEN>
Content-Type: application/json
```

### Endpoints Lifecycle:
| Step | Action | Method | Endpoint | Description |
|---|---|:---:|---|---|
| 1 | Fetch Setup | `GET` | `/setup` | Map dimensions, terrain, obstacles, fuel limits |
| 2 | Role Assignment | `POST` | `/assignment` | Assign agent roles (Patrol vs. Refuel) |
| 3 | Await Start | `GET` | `/start` | Poll until match begins (handles `HTTP 425`) |
| 4 | Fetch Day State | `GET` | `/state` | Agent coordinates, current fuel, spots, traffic |
| 5 | Submit Actions | `POST` | `/actions` | Daily movement and standby plan for all agents |
| 6 | Retrieve Results| `GET` | `/result` | Final scores, winner, and telemetry statistics |

---

## 8. Quick Connectivity Check with `curl`

Define environment variables:
```bash
BASE="https://procon.ptit.edu.vn"
MATCH_ID="m-32744"
TOKEN="your_token_here"
```

### Fetch Match Setup:
```bash
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/matches/$MATCH_ID/setup"
```

### Fetch Daily State:
```bash
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/matches/$MATCH_ID/state"
```

### Fetch Final Result:
```bash
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/matches/$MATCH_ID/result"
```

---

## 9. Minimal Python Client

You can test connectivity using standard Python libraries without third-party dependencies:

```python
"""connection_test.py — Minimal PROCON connectivity smoke script."""
import json
import os
import urllib.request
import urllib.error

BASE = os.getenv("PROCON_BASE_URL", "https://procon.ptit.edu.vn")
MATCH_ID = os.environ["PROCON_MATCH_ID"]
TOKEN = os.environ["PROCON_TOKEN"]

API = f"{BASE}/api/v1/matches/{MATCH_ID}"


def call(method: str, path: str, body: dict = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None

    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            raw = response.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.read().decode('utf-8', errors='replace')}")
        raise


if __name__ == "__main__":
    setup = call("GET", "/setup")
    print("Match Setup Loaded Successfully:")
    print(json.dumps(setup, indent=2))
```

Run:
```bash
python connection_test.py
```

---

## 10. Understanding `setup` and Hex Grid Indexing

The `setup` payload contains:
- `daySteps`: Number of actions per day per agent.
- `width`, `height`: Grid dimensions $W \times H$.
- `cells`: 1D array representing cell properties.
- `spots`: Udon spots with position and score capacity.
- `fuelLimits`: Maximum fuel limits by agent type.

### 1D Cell Index Calculation:
Given row $r$ and column $c$ on a grid of width $W$:
$$\text{index} = r \times W + c$$

Conversely:
$$r = \lfloor \text{index} / W \rfloor, \quad c = \text{index} \bmod W$$

---

## 11. Agent Role Assignment (`POST /assignment`)

Immediately following `/setup`, submit an assignment array specifying the type of each agent:
- `0`: **Patrol Agent** (Xe tuần tra — collects Udon points, consumes fuel per movement).
- `1`: **Refuel Agent** (Xe tiếp nhiên liệu — high capacity, transfers fuel to co-located patrol agents).

For example, with 3 agents (2 Patrol, 1 Refuel):
```json
[0, 0, 1]
```

```python
assignment = [0, 0, 1]
call("POST", "/assignment", assignment)
```

> [!IMPORTANT]
> The length of the assignment array must exactly match the number of agents allocated to your team in `setup`. Role assignments remain fixed for the duration of the match.

---

## 12. Awaiting Match Start & Handling `HTTP 425 Too Early`

When querying `/start`, the server may return `HTTP 425` if the match is pending:

```python
import time
import urllib.error

print("Waiting for match start...")
while True:
    try:
        start_data = call("GET", "/start")
        print("Match started successfully!")
        break
    except urllib.error.HTTPError as e:
        if e.code == 425:
            time.sleep(0.5)
            continue
        raise
```

---

## 13. Parsing Daily Game State (`GET /state`)

Each day, call `GET /state` to retrieve dynamic game data:
- `day`: Current day index.
- `agents`: List of your team's agents (`kind`, `pos`, `fuel`, `score`).
- `others`: Observed enemy agent coordinates.
- `traffics`: Array of traffic density modifiers per cell.

---

## 14. Action Plan Formatting & Hex Directions

Actions must be submitted as a **list of lists** (one list of actions per agent).

### Hex Direction Enums:
| Value | Movement Direction |
|:---:|---|
| `0` | Up-Left (Tây Bắc) |
| `1` | Up-Right (Đông Bắc) |
| `2` | Right (Đông) |
| `3` | Down-Right (Đông Nam) |
| `4` | Down-Left (Tây Nam) |
| `5` | Left (Tây) |
| `-1` | **STAY** (Đứng yên 1 bước) |

### Format Example:
For 2 agents with `daySteps = 3`:
```json
[
  [2, 2, -1],
  [0, 1, 5]
]
```
- **Agent 0**: Moves Right twice, then stands still on step 3.
- **Agent 1**: Moves Up-Left, Up-Right, then Left.

> [!NOTE]
> If an agent finishes its path before `daySteps`, pad the remaining steps with `-1` (`Direction.STAY`).

---

## 15. Submitting Actions (`POST /actions`)

```python
actions = [
    [2, 2, -1],
    [0, 1, 5],
    [-1, -1, -1],
]

response = call("POST", "/actions", actions)
print("Server response:", response)
```

---

## 16. Complete Autonomous Bot Lifecycle

```python
# 1. Fetch initial configuration
setup = call("GET", "/setup")

# 2. Assign agent roles
call("POST", "/assignment", [0, 0, 1])

# 3. Wait for start
wait_for_start()

# 4. Daily game loop
while True:
    state = call("GET", "/state")
    
    # Hierarchical planning: MARL allocates targets, DP plans route
    plan = strategy.plan_day(state, setup.daySteps)
    
    response = call("POST", "/actions", plan)
    if response.get("finished", False):
        break
    time.sleep(0.25)

# 5. Retrieve final match report
results = call("GET", "/result")
print("Match complete:", results)
```

---

## 17. Polling Rate Limiting (`HTTP 429`)

The official server enforces a minimum polling interval:
$$\text{Polling Interval} \ge 200\text{ ms}$$

If requests are sent faster than 200 ms, the server will return `HTTP 429 Too Many Requests`.

Always maintain a safe delay:
```python
time.sleep(0.25)  # 250 ms safe buffer
```

---

## 18. Recommended Debugging Flowchart

```text
[1] Log in with team022 / 11aaAA@@
        │
        ▼
[2] Verify active API Bearer Token
        │
        ▼
[3] Confirm Match ID in "Trận của tôi"
        │
        ▼
[4] GET /setup returns valid 200 JSON
        │
        ▼
[5] POST /assignment matches agent count
        │
        ▼
[6] GET /start resolves past HTTP 425
        │
        ▼
[7] GET /state returns day and agent data
        │
        ▼
[8] Action arrays validated (length <= daySteps, directions in [-1, 0..5])
        │
        ▼
[9] POST /actions returns { status: "accepted" }
        │
        ▼
[10] Live UI reflects movements in real time
        │
        ▼
[11] GET /result prints final scores
```

---

## 19. Troubleshooting & Common Error Codes

### `HTTP 401 Unauthorized`
- Missing or malformed `Authorization: Bearer <TOKEN>` header.
- Token expired or revoked on the web portal.

### `HTTP 425 Too Early`
- Match has not started yet. Implement exponential or linear polling backoff (`time.sleep(0.5)`).

### `HTTP 429 Too Many Requests`
- Polling frequency exceeded 200 ms. Increase interval to `250 ms` – `500 ms`.

### Action Plan Rejected
- Action direction contains invalid integer (must be `-1` or `0..5`).
- Length of action list does not equal `daySteps`.
- Number of agent plans does not match team agent count.
- Vehicle attempted to enter impassable terrain (`TerrainType.POND`).
- Insufficient fuel for planned movements.

---

## 20. Pre-Match Checklist

Before initiating official competition matches:

- [ ] Logged into `https://procon.ptit.edu.vn` with `team022`.
- [ ] Valid API Bearer Token copied into local `.env`.
- [ ] `.env` confirmed excluded by `.gitignore` (no secrets pushed).
- [ ] `MATCH_ID` updated to match tournament assignment.
- [ ] `GET /setup` tested and verified.
- [ ] Agent count in `assignment` validated.
- [ ] Polling delay set to $\ge 250\text{ ms}$.
- [ ] Decision latency verified under 500 ms (safety limit < 950 ms).
- [ ] Live visualizer page opened in browser for real-time monitoring.
- [ ] `python run_match.py -m <MATCH_ID>` launched and synchronized.
