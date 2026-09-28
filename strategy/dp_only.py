"""DP-Only Strategy for PTIT PROCON 2026."""
from typing import Dict, List, Optional

from client.protocol import ActionPlan, Direction, validate_action_plan
from env.hex_grid import HexGrid
from env.state import SimulationState
from planner.value_iteration import ValueIteration


class DPOnlyStrategy:
    """Strategy using Value Iteration to compute optimal paths to target set."""

    def __init__(self, grid: HexGrid, gamma: float = 0.95):
        self.grid = grid
        self.gamma = gamma
        self.planner = ValueIteration(grid, gamma=gamma)

    def plan_day(
        self,
        sim_state: SimulationState,
        day_steps: int,
        targets: Optional[List[int]] = None,
    ) -> ActionPlan:
        """Run Value Iteration for targets and extract day action plan with fuel checks and padding."""
        if targets is None:
            targets = [
                s.pos
                for s in sim_state.spots
                if s.current_stock > 0 and self.grid.is_passable(s.pos)
            ]

        if not targets:
            # No reachable targets; all stay
            return [[Direction.STAY.value] * day_steps for _ in range(len(sim_state.agents))]

        policy, _, _ = self.planner.plan(targets)

        plan: ActionPlan = []
        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr = agent.pos
            curr_fuel = agent.fuel

            for _ in range(day_steps):
                action = policy.get(curr, Direction.STAY)
                if action == Direction.STAY:
                    agent_plan.append(Direction.STAY.value)
                    continue

                nxt = self.grid.get_neighbor_index(curr, action)
                if nxt is not None and self.grid.is_passable(nxt):
                    _, f_cost = self.grid.get_movement_cost(curr, nxt, agent.kind)
                    if curr_fuel >= f_cost:
                        agent_plan.append(action.value)
                        curr_fuel -= f_cost
                        curr = nxt
                    else:
                        agent_plan.append(Direction.STAY.value)
                else:
                    agent_plan.append(Direction.STAY.value)

            while len(agent_plan) < day_steps:
                agent_plan.append(Direction.STAY.value)

            plan.append(agent_plan[:day_steps])

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
