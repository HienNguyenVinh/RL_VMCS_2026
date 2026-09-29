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
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            raw_actions: List[int] = []
            curr_pos = agent.pos
            curr_coord = HexCoord.from_index(curr_pos, self.grid.width)

            # Find nearest spot with stock
            nearest_target = curr_pos
            min_dist = float("inf")

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
                    break

                best_dir = Direction.STAY
                best_dist = curr_c.distance_to(target_coord)

                for d in Direction.all_movements():
                    nxt = self.grid.get_neighbor(curr_c.row, curr_c.col, d)
                    if nxt is not None and self.grid.is_passable(nxt.to_index(self.grid.width)):
                        nxt_idx = nxt.to_index(self.grid.width)
                        dist = nxt.distance_to(target_coord)
                        if dist < best_dist:
                            best_dist = dist
                            best_dir = d

                if best_dir == Direction.STAY:
                    break

                raw_actions.append(best_dir.value)
                nxt_idx = self.grid.get_neighbor_index(curr_pos, best_dir)
                if nxt_idx is not None:
                    curr_pos = nxt_idx
                else:
                    break

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


class GreedyDijkstraStrategy:
    """Baseline B1: Greedy task allocation + Dijkstra minimum-cost path planning."""

    def __init__(self, grid: HexGrid):
        self.grid = grid
        self.dijkstra = DijkstraPlanner(grid)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps for all agents using Greedy target selection and Dijkstra routes."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            curr_pos = agent.pos

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
            raw_actions: List[int] = []
            if target_pos != curr_pos:
                path_res = self.dijkstra.plan(
                    start_index=curr_pos,
                    target_indices=target_pos,
                    agent_kind=agent.kind,
                    fuel_limit=agent.fuel,
                )
                if path_res.reachable and path_res.actions:
                    raw_actions = [a.value if hasattr(a, "value") else int(a) for a in path_res.actions]

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


class GreedyDPStrategy:
    """Baseline B2: Greedy task allocation + Value Iteration route planning."""

    def __init__(self, grid: HexGrid, gamma: float = 0.95):
        self.grid = grid
        self.planner = ValueIteration(grid, gamma=gamma)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps for all agents using Greedy target selection and DP routes."""
        plan: ActionPlan = []

        for agent in sim_state.agents:
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            curr_pos = agent.pos

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

            raw_actions: List[int] = []
            if target_pos != curr_pos:
                policy, _, _ = self.planner.plan([target_pos])
                path, actions, reached = self.planner.extract_route(
                    start=curr_pos, target_indices=[target_pos], policy=policy, max_steps=day_steps
                )
                if reached and actions:
                    raw_actions = [a.value if hasattr(a, "value") else int(a) for a in actions]

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
