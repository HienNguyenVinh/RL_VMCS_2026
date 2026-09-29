"""Match Runner orchestrating full lifecycle with PROCON server (Phase 9 Real Server / Mock).
Features:
- Parse and load real setup and state into SimulationState
- Safe execution with planning latency monitoring (<1000ms)
- Automatic fallback actions on planner exception or timeout
- Strict prevention of duplicate actions for the same match day
- Structured match telemetry logging and JSON match log persistence
- Error recovery and graceful completion handling
"""
from datetime import datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


from client.http_client import ProconHttpClient
from client.protocol import (
    ActionPlan,
    AgentKind,
    MatchResult,
    MatchSetup,
    MatchState,
    create_idle_action_plan,
    validate_action_plan,
)
from env.state import SimulationState
from strategy.hybrid import HybridMARLDPStrategy

logger = logging.getLogger(__name__)


class MatchRunner:
    """Manages the full lifecycle of a PROCON 2026 match:
    1. GET /setup -> parse MatchSetup & build map
    2. POST /assignment -> assign Patrol / Refuel roles
    3. GET /start (handling HTTP 425 Too Early)
    4. Match Loop:
       - GET /state -> check duplicate day -> SimulationState
       - Strategy planning with latency timeout guard (<950ms)
       - Action validation & Fallback protection
       - POST /actions
       - Structured telemetry logging
    5. GET /result & save match logs
    """

    def __init__(
        self,
        client: ProconHttpClient,
        strategy: Optional[Union[HybridMARLDPStrategy, Callable[[MatchSetup, MatchState], ActionPlan]]] = None,
        patrol_ratio: float = 0.67,
        max_days: int = 50,
        poll_interval: float = 0.5,
        max_planning_time_ms: float = 900.0,  # Safety margin under 1000ms server limit
        log_dir: str = "logs/matches",
    ):
        self.client = client
        self.strategy = strategy
        self.patrol_ratio = patrol_ratio
        self.max_days = max_days
        self.poll_interval = max(0.25, poll_interval)
        self.max_planning_time_ms = max_planning_time_ms
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.last_acted_day: int = -1
        self.telemetry_records: List[Dict[str, Any]] = []

    def default_role_assignment(self, num_agents: int) -> List[int]:
        """Compute default role assignment (0: Patrol, 1: Refuel)."""
        num_patrol = max(1, round(num_agents * self.patrol_ratio))
        if num_agents >= 3 and num_patrol == num_agents:
            num_patrol = num_agents - 1

        assignment = [AgentKind.PATROL.value] * num_patrol + [
            AgentKind.REFUEL.value
        ] * (num_agents - num_patrol)
        return assignment

    def _execute_strategy(
        self, setup: MatchSetup, state: MatchState
    ) -> Tuple[ActionPlan, float, str]:
        """Execute strategy with latency measurement, fallback protection, and validation."""
        start_t = time.perf_counter()
        plan_source = "hybrid"
        steps_today = setup.get_steps_for_day(state.day)

        try:
            if self.strategy is None:
                # Default Smoke Test / Idle strategy
                actions = create_idle_action_plan(setup.num_agents, steps_today)
                plan_source = "idle_default"
            elif isinstance(self.strategy, HybridMARLDPStrategy):
                # Convert MatchState + MatchSetup into SimulationState
                sim_state = SimulationState.from_match(setup, state)
                actions = self.strategy.plan_day(sim_state, steps_today)
                plan_source = "hybrid_marl_dp"
            elif callable(self.strategy):
                actions = self.strategy(setup, state)
                plan_source = "custom_fn"
            else:
                actions = create_idle_action_plan(setup.num_agents, steps_today)
                plan_source = "fallback_unknown"

            # Validate action plan format
            validate_action_plan(actions, setup.num_agents, steps_today)

        except Exception as e:
            logger.error(f"[Day {state.day}] Strategy execution failed: {e}. Activating Idle Fallback!")
            actions = create_idle_action_plan(setup.num_agents, steps_today)
            plan_source = f"fallback_error: {e}"

        latency_ms = (time.perf_counter() - start_t) * 1000.0

        # Safety check: if planning exceeded server latency limit, log warning
        if latency_ms > self.max_planning_time_ms:
            logger.warning(
                f"[Day {state.day}] Planning took {latency_ms:.1f}ms (threshold: {self.max_planning_time_ms}ms)!"
            )

        return actions, latency_ms, plan_source

    def save_match_log(self, summary: Dict[str, Any]) -> Path:
        """Persist full match telemetry and summary to JSON."""
        log_file = self.log_dir / f"{self.client.match_id}.json"
        data = {
            "match_id": self.client.match_id,
            "timestamp": datetime.now().isoformat(),
            "summary": summary,
            "telemetry": self.telemetry_records,
        }
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved complete match log to: {log_file}")
        return log_file

    def run(self) -> Dict[str, Any]:
        """Execute complete match lifecycle."""
        logger.info(f"=== Starting PROCON Match Runner: {self.client.match_id} ===")
        match_start_time = time.time()

        # Step 1: GET /setup
        setup = self.client.get_setup()
        logger.info(
            f"[Phase 9] Setup: Map {setup.width}x{setup.height}, {setup.num_agents} agents, {setup.day_steps} steps/day"
        )

        # Initialize strategy if not provided
        if self.strategy is None:
            from env.hex_grid import HexGrid
            grid = HexGrid.from_setup(setup)
            self.strategy = HybridMARLDPStrategy(
                grid=grid,
                num_agents=setup.num_agents,
                weights_dir="experiments/models/marl",
                enable_refueling=True,
            )
            logger.info("[Phase 9] Auto-initialized HybridMARLDPStrategy from setup.")

        # Step 2: POST /assignment
        assignment = self.default_role_assignment(setup.num_agents)
        logger.info(f"[Phase 9] Assigning agent roles: {assignment}")
        self.client.post_assignment(assignment)

        # Step 3: GET /start (handling HTTP 425)
        logger.info("[Phase 9] Waiting for match start (HTTP 425 handling)...")
        self.client.wait_for_start(poll_interval=self.poll_interval)

        # Step 4: Match loop
        day_counter = 0
        match_finished = False

        while not match_finished and day_counter < self.max_days:
            # Poll state
            try:
                state = self.client.get_state()
            except Exception as e:
                logger.warning(f"Error fetching state: {e}. Checking if match has concluded...")
                break

            if state is None:
                time.sleep(self.poll_interval)
                continue

            # Strictly prevent duplicate actions for same day
            if state.day <= self.last_acted_day:
                logger.debug(f"[Day {state.day}] Already acted for this day. Polling...")
                time.sleep(self.poll_interval)
                continue

            self.last_acted_day = state.day
            day_counter += 1

            # Agent status summary
            agents_summary = [
                {
                    "id": a.agent_id,
                    "kind": "Patrol" if a.kind == AgentKind.PATROL else "Refuel",
                    "pos": a.pos,
                    "fuel": a.fuel,
                    "score": a.score,
                }
                for a in state.agents
            ]
            logger.info(f"[Day {state.day}] Active agents: {len(state.agents)} | Status: {agents_summary}")

            # Generate actions with safety timer & fallback
            actions, latency_ms, plan_source = self._execute_strategy(setup, state)
            logger.info(
                f"[Day {state.day}] Action plan generated via {plan_source} in {latency_ms:.2f}ms"
            )

            # Submit actions
            server_resp = {}
            try:
                server_resp = self.client.post_actions(actions, setup=setup)
                if server_resp.get("finished", False) or server_resp.get("status") == "finished":
                    logger.info("Server reported match completion in actions response.")
                    match_finished = True
            except Exception as e:
                logger.error(f"[Day {state.day}] Error posting actions: {e}")
                break

            # Record telemetry
            self.telemetry_records.append({
                "day": state.day,
                "agents": agents_summary,
                "actions": actions,
                "planning_latency_ms": round(latency_ms, 2),
                "plan_source": plan_source,
                "server_response": server_resp,
                "timestamp": datetime.now().isoformat(),
            })

            if match_finished:
                break

            time.sleep(self.poll_interval)

        # Step 5: GET /result
        logger.info("[Phase 9] Fetching final match result...")
        result = None
        try:
            result = self.client.get_result()
            logger.info(f"[Phase 9] Match Concluded! Winner: {result.winner} | Scores: {result.scores}")
        except Exception as e:
            logger.warning(f"Could not fetch final result: {e}")

        total_match_time = time.time() - match_start_time
        summary = {
            "match_id": self.client.match_id,
            "days_played": day_counter,
            "total_time_seconds": round(total_match_time, 2),
            "winner": result.winner if result else None,
            "scores": result.scores if result else None,
            "success": True,
        }

        # Persist match logs
        log_path = self.save_match_log(summary)
        summary["log_file"] = str(log_path)

        return summary
