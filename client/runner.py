"""Match Runner orchestrating full lifecycle with PROCON server."""
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from client.http_client import ProconHttpClient
from client.protocol import (
    ActionPlan,
    AgentKind,
    MatchResult,
    MatchSetup,
    MatchState,
    create_idle_action_plan,
)

logger = logging.getLogger(__name__)


class MatchRunner:
    """Manages the full lifecycle of a PROCON 2026 match:
    1. GET /setup
    2. POST /assignment
    3. GET /start (handling HTTP 425)
    4. Loop: GET /state -> plan actions -> POST /actions
    5. GET /result
    """

    def __init__(
        self,
        client: ProconHttpClient,
        strategy_fn: Optional[Callable[[MatchSetup, MatchState], ActionPlan]] = None,
        patrol_ratio: float = 0.67,  # Default ratio of patrol agents vs refuel
        max_days: int = 50,
        poll_interval: float = 0.5,
    ):
        self.client = client
        self.strategy_fn = strategy_fn
        self.patrol_ratio = patrol_ratio
        self.max_days = max_days
        self.poll_interval = poll_interval

    def default_role_assignment(self, num_agents: int) -> List[int]:
        """Compute default role assignment (0: Patrol, 1: Refuel)."""
        num_patrol = max(1, round(num_agents * self.patrol_ratio))
        # Ensure at least 1 refuel if there are 3 or more agents
        if num_agents >= 3 and num_patrol == num_agents:
            num_patrol = num_agents - 1

        assignment = [AgentKind.PATROL.value] * num_patrol + [
            AgentKind.REFUEL.value
        ] * (num_agents - num_patrol)
        return assignment

    def run(self) -> Dict[str, Any]:
        """Execute complete match cycle."""
        logger.info(f"=== Starting PROCON Match Runner: {self.client.match_id} ===")

        # Step 1: GET /setup
        setup = self.client.get_setup()
        logger.info(
            f"[Phase 1] Setup: Map {setup.width}x{setup.height}, {setup.num_agents} agents, {setup.day_steps} steps/day"
        )

        # Step 2: POST /assignment
        assignment = self.default_role_assignment(setup.num_agents)
        logger.info(f"[Phase 1] Assigning roles: {assignment}")
        self.client.post_assignment(assignment)

        # Step 3: GET /start (wait past 425)
        logger.info("[Phase 1] Waiting for match start...")
        self.client.wait_for_start(poll_interval=self.poll_interval)

        # Step 4: Game loop
        day_counter = 0
        last_day = -1
        match_finished = False

        while not match_finished and day_counter < self.max_days:
            # Poll state
            try:
                state = self.client.get_state()
            except Exception as e:
                logger.warning(f"Error fetching state: {e}. Checking if match has concluded...")
                break

            if state.day == last_day:
                # Same day still processing on server, wait and poll again
                time.sleep(self.poll_interval)
                continue

            last_day = state.day
            day_counter += 1
            logger.info(f"[Day {state.day}] Agents active: {len(state.agents)}")

            # Generate action plan
            if self.strategy_fn is not None:
                actions = self.strategy_fn(setup, state)
            else:
                # Default Smoke Test Strategy: all agents stay still
                actions = create_idle_action_plan(setup.num_agents, setup.day_steps)

            # Submit actions
            try:
                resp = self.client.post_actions(actions, setup=setup)
                if resp.get("finished", False) or resp.get("status") == "finished":
                    logger.info("Server reported match completion in actions response.")
                    match_finished = True
                    break
            except Exception as e:
                logger.error(f"Error posting actions: {e}")
                # Check if match concluded
                break

            time.sleep(self.poll_interval)

        # Step 5: GET /result
        logger.info("[Phase 1] Fetching match result...")
        try:
            result = self.client.get_result()
            logger.info(f"[Phase 1] Match Complete! Result: {result.raw}")
            return {
                "match_id": self.client.match_id,
                "days_played": day_counter,
                "result": result,
                "success": True,
            }
        except Exception as e:
            logger.warning(f"Could not fetch final result: {e}")
            return {
                "match_id": self.client.match_id,
                "days_played": day_counter,
                "result": None,
                "success": True,
            }
