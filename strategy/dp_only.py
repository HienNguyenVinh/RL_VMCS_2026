"""DP-Only Strategy for PTIT PROCON 2026."""
from typing import Dict, List, Optional

from client.protocol import ActionPlan, AgentKind, Direction, validate_action_plan
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
            return [[-day_steps] for _ in range(len(sim_state.agents))]

        policy, _, _ = self.planner.plan(targets)

        plan: ActionPlan = []
        for agent in sim_state.agents:
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            raw_actions: List[int] = []
            curr = agent.pos
            visited = {curr}

            for _ in range(day_steps):
                action = policy.get(curr, Direction.STAY)
                if action == Direction.STAY:
                    break

                nxt = self.grid.get_neighbor_index(curr, action)
                if nxt is None or nxt in visited or not self.grid.is_passable(nxt):
                    break

                raw_actions.append(action.value)
                visited.add(nxt)
                curr = nxt

            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=raw_actions,
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=agent.fuel,
            )
            plan.append(agent_plan)

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
