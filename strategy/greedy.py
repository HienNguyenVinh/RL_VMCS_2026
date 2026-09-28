"""Greedy Baseline Strategies for PTIT PROCON 2026."""
from typing import Dict, List, Optional

from client.protocol import ActionPlan, AgentKind, Direction, validate_action_plan
from env.hex_grid import HexCoord, HexGrid
from env.state import SimulationState
from planner.dijkstra import DijkstraPlanner
from planner.value_iteration import ValueIteration


class GreedyStrategy:
    """Baseline strategy: agents greedily step towards the nearest available target."""

    def __init__(self, grid: HexGrid):
        self.grid = grid

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Generate greedy step plan for all agents for the day."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr_pos = agent.pos
            curr_fuel = agent.fuel

            # Find nearest spot with stock
            nearest_target = curr_pos
            min_dist = float("inf")
            curr_coord = HexCoord.from_index(curr_pos, self.grid.width)

            for spot in sim_state.spots:
                if spot.current_stock > 0 and self.grid.is_passable(spot.pos):
                    s_coord = HexCoord.from_index(spot.pos, self.grid.width)
                    dist = curr_coord.distance_to(s_coord)
                    if dist < min_dist:
                        min_dist = dist
                        nearest_target = spot.pos

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
                    if nxt is not None and self.grid.is_passable(nxt.to_index(self.grid.width)):
                        nxt_idx = nxt.to_index(self.grid.width)
                        _, f_cost = self.grid.get_movement_cost(curr_pos, nxt_idx, agent.kind)
                        if curr_fuel >= f_cost:
                            dist = nxt.distance_to(target_coord)
                            if dist < best_dist:
                                best_dist = dist
                                best_dir = d

                agent_plan.append(best_dir.value)
                if best_dir != Direction.STAY:
                    nxt_idx = self.grid.get_neighbor_index(curr_pos, best_dir)
                    if nxt_idx is not None:
                        _, f_cost = self.grid.get_movement_cost(curr_pos, nxt_idx, agent.kind)
                        curr_fuel = max(0, curr_fuel - f_cost)
                        curr_pos = nxt_idx

            while len(agent_plan) < day_steps:
                agent_plan.append(Direction.STAY.value)

            plan.append(agent_plan[:day_steps])

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan


class GreedyDijkstraStrategy:
    """Baseline B1: Greedy task allocation + Dijkstra minimum-cost path planning."""

    def __init__(self, grid: HexGrid):
        self.grid = grid
        self.dijkstra = DijkstraPlanner(grid)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps for all agents using Greedy target selection and Dijkstra routes."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr_pos = agent.pos
            curr_fuel = agent.fuel

            # 1. Greedy target selection
            target_pos = curr_pos
            if agent.kind == AgentKind.PATROL:
                active_spots = [s for s in sim_state.spots if s.current_stock > 0 and self.grid.is_passable(s.pos)]
                if active_spots:
                    curr_coord = HexCoord.from_index(curr_pos, self.grid.width)
                    active_spots.sort(key=lambda s: curr_coord.distance_to(HexCoord.from_index(s.pos, self.grid.width)))
                    target_pos = active_spots[0].pos
            else:
                patrols = [p for p in sim_state.agents if p.kind == AgentKind.PATROL]
                if patrols:
                    curr_coord = HexCoord.from_index(curr_pos, self.grid.width)
                    patrols.sort(key=lambda p: curr_coord.distance_to(HexCoord.from_index(p.pos, self.grid.width)))
                    target_pos = patrols[0].pos

            # 2. Dijkstra path planning
            if target_pos != curr_pos:
                path_res = self.dijkstra.plan(
                    start_index=curr_pos,
                    target_indices=target_pos,
                    agent_kind=agent.kind,
                    fuel_limit=curr_fuel,
                )
                if path_res.reachable and path_res.actions:
                    for act in path_res.actions:
                        nxt_pos = self.grid.get_neighbor_index(curr_pos, act)
                        if nxt_pos is not None:
                            _, f_cost = self.grid.get_movement_cost(curr_pos, nxt_pos, agent.kind)
                            if curr_fuel >= f_cost:
                                agent_plan.append(act.value)
                                curr_fuel -= f_cost
                                curr_pos = nxt_pos
                            else:
                                break

            # 3. Pad remaining steps with STAY (-1)
            while len(agent_plan) < day_steps:
                agent_plan.append(Direction.STAY.value)

            plan.append(agent_plan[:day_steps])

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan


class GreedyDPStrategy:
    """Baseline B2: Greedy task allocation + Value Iteration route planning."""

    def __init__(self, grid: HexGrid, gamma: float = 0.95):
        self.grid = grid
        self.planner = ValueIteration(grid, gamma=gamma)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps for all agents using Greedy target selection and DP routes."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            agent_plan: List[int] = []
            curr_pos = agent.pos
            curr_fuel = agent.fuel

            # Greedy target selection
            target_pos = curr_pos
            if agent.kind == AgentKind.PATROL:
                active_spots = [s for s in sim_state.spots if s.current_stock > 0 and self.grid.is_passable(s.pos)]
                if active_spots:
                    curr_coord = HexCoord.from_index(curr_pos, self.grid.width)
                    active_spots.sort(key=lambda s: curr_coord.distance_to(HexCoord.from_index(s.pos, self.grid.width)))
                    target_pos = active_spots[0].pos
            else:
                patrols = [p for p in sim_state.agents if p.kind == AgentKind.PATROL]
                if patrols:
                    curr_coord = HexCoord.from_index(curr_pos, self.grid.width)
                    patrols.sort(key=lambda p: curr_coord.distance_to(HexCoord.from_index(p.pos, self.grid.width)))
                    target_pos = patrols[0].pos

            if target_pos != curr_pos:
                policy, _, _ = self.planner.plan([target_pos])
                path, actions, reached = self.planner.extract_route(
                    start=curr_pos, target_indices=[target_pos], policy=policy, max_steps=day_steps
                )
                for act in actions:
                    nxt = self.grid.get_neighbor_index(curr_pos, act)
                    if nxt is not None:
                        _, f_cost = self.grid.get_movement_cost(curr_pos, nxt, agent.kind)
                        if curr_fuel >= f_cost:
                            agent_plan.append(act.value)
                            curr_fuel -= f_cost
                            curr_pos = nxt
                        else:
                            break

            while len(agent_plan) < day_steps:
                agent_plan.append(Direction.STAY.value)

            plan.append(agent_plan[:day_steps])

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
