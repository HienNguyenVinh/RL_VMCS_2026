"""Greedy Baseline Strategy for PTIT PROCON 2026."""
from typing import Dict, List
from client.protocol import ActionPlan, Direction
from env.hex_grid import HexCoord, HexGrid
from env.state import SimulationState


class GreedyStrategy:
    """Baseline strategy: agents greedily head towards the nearest available target."""

    def __init__(self, grid: HexGrid):
        self.grid = grid

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Generate greedy step plan for all agents for the day."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr_pos = agent.pos

            # Find nearest spot with stock
            nearest_target = curr_pos
            min_dist = float("inf")
            curr_coord = HexCoord.from_index(curr_pos, self.grid.width)

            for spot in sim_state.spots:
                if spot.current_stock > 0:
                    s_coord = HexCoord.from_index(spot.pos, self.grid.width)
                    dist = curr_coord.distance_to(s_coord)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_target = spot.pos

            # Greedily move toward nearest target
            target_coord = HexCoord.from_index(nearest_target, self.grid.width)
            for _ in range(day_steps):
                curr_c = HexCoord.from_index(curr_pos, self.grid.width)
                if curr_c == target_coord:
                    agent_plan.append(Direction.STAY.value)
                    continue

                best_dir = Direction.STAY
                best_dist = curr_c.distance_to(target_coord)

                for d in Direction.all_movements():
                    nxt = self.grid.get_neighbor(curr_c.row, curr_c.col, d)
                    if nxt is not None:
                        dist = nxt.distance_to(target_coord)
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d

                agent_plan.append(best_dir.value)
                nxt_idx = self.grid.get_neighbor_index(curr_pos, best_dir)
                if nxt_idx is not None:
                    curr_pos = nxt_idx

            plan.append(agent_plan)

        return plan
