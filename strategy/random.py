"""Random Strategy (Baseline B0) for PTIT PROCON 2026."""
import random
from typing import List, Optional

from client.protocol import ActionPlan, Direction, validate_action_plan
from env.hex_grid import HexGrid
from env.state import SimulationState


class RandomStrategy:
    """Baseline B0: Random task selection and random valid hex movement."""

    def __init__(self, grid: HexGrid, seed: Optional[int] = None):
        self.grid = grid
        self.rng = random.Random(seed)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Generate random valid actions for each agent for all day_steps."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr_pos = agent.pos
            curr_fuel = agent.fuel

            for _ in range(day_steps):
                valid_moves = [Direction.STAY]
                for d in Direction.all_movements():
                    nxt = self.grid.get_neighbor_index(curr_pos, d)
                    if nxt is not None and self.grid.is_passable(nxt):
                        _, fuel_cost = self.grid.get_movement_cost(curr_pos, nxt, agent.kind)
                        if curr_fuel >= fuel_cost:
                            valid_moves.append(d)

                chosen_dir = self.rng.choice(valid_moves)
                agent_plan.append(chosen_dir.value)

                if chosen_dir != Direction.STAY:
                    nxt = self.grid.get_neighbor_index(curr_pos, chosen_dir)
                    if nxt is not None:
                        _, fuel_cost = self.grid.get_movement_cost(curr_pos, nxt, agent.kind)
                        curr_fuel = max(0, curr_fuel - fuel_cost)
                        curr_pos = nxt

            while len(agent_plan) < day_steps:
                agent_plan.append(Direction.STAY.value)

            plan.append(agent_plan[:day_steps])

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
