"""DP-Only Strategy for PTIT PROCON 2026."""
from typing import Dict, List
from client.protocol import ActionPlan, Direction
from env.hex_grid import HexGrid
from env.state import SimulationState
from planner.value_iteration import ValueIteration


class DPOnlyStrategy:
    """Strategy using Value Iteration to compute optimal paths to assigned targets."""

    def __init__(self, grid: HexGrid, gamma: float = 0.95):
        self.grid = grid
        self.gamma = gamma
        self.planner = ValueIteration(grid, gamma=gamma)

    def plan_day(
        self, sim_state: SimulationState, day_steps: int, targets: List[int]
    ) -> ActionPlan:
        """Run Value Iteration for targets and extract day action plan."""
        # Run Value Iteration toward target set
        policy, _, _ = self.planner.plan(targets)

        plan: ActionPlan = []
        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr = agent.pos

            for _ in range(day_steps):
                action = policy.get(curr, Direction.STAY)
                agent_plan.append(action.value)
                nxt = self.grid.get_neighbor_index(curr, action)
                if nxt is not None:
                    curr = nxt

            plan.append(agent_plan)

        return plan
