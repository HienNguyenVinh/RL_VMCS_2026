"""Baseline Strategies for PTIT PROCON 2026.

Consolidates all comparison baselines and ablation models:
- B0: RandomStrategy (Random allocation + random/heuristic step)
- B1: GreedyDijkstraStrategy (Greedy target allocation + Dijkstra route planning)
- B2: GreedyDPStrategy (Greedy target allocation + Value Iteration DP route planning)
- B3: IQLDijkstraStrategy (MARL IQL task allocation + Dijkstra route planning)
- GreedyStrategy (Pure greedy step-by-step heuristic)
- DPOnlyStrategy (Pure DP planning without task allocation layer)
"""
from pathlib import Path
import random
from typing import Any, Dict, List, Optional, Union

from client.protocol import ActionPlan, AgentKind, Direction, validate_action_plan
from env.hex_grid import HexCoord, HexGrid
from env.state import SimulationState
from marl.iql import IndependentQLearning
from marl.state_encoder import StateEncoder
from marl.task_allocator import TaskAllocator
from planner.dijkstra import DijkstraPlanner
from planner.value_iteration import ValueIteration


class RandomStrategy:
    """Baseline B0: Randomly picks targets and movements."""

    def __init__(self, grid: HexGrid, seed: Optional[int] = None):
        self.grid = grid
        self.rng = random.Random(seed)

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Generate random movement plan for all agents."""
        plan: ActionPlan = []
        all_actions = Direction.all_movements()

        for agent in sim_state.agents:
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            raw_actions: List[int] = []
            curr_pos = agent.pos

            for _ in range(day_steps):
                valid_dirs = []
                for d in all_actions:
                    nxt = self.grid.get_neighbor_index(curr_pos, d)
                    if nxt is not None and self.grid.is_passable(nxt):
                        valid_dirs.append(d)

                if not valid_dirs:
                    break

                chosen_dir = self.rng.choice(valid_dirs)
                raw_actions.append(chosen_dir.value)
                nxt_idx = self.grid.get_neighbor_index(curr_pos, chosen_dir)
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


class GreedyStrategy:
    """Baseline: Agents greedily step towards the nearest available target."""

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


class DPOnlyStrategy:
    """Ablation: Value Iteration to compute optimal paths to target set without RL allocation."""

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


class IQLDijkstraStrategy:
    """Baseline B3: MARL (IQL) task allocation + Dijkstra minimum-cost path planning."""

    def __init__(
        self,
        grid: HexGrid,
        num_agents: int = 3,
        weights_dir: Optional[Union[str, Path]] = "experiments/models/marl",
        evaluation_mode: bool = True,
    ):
        self.grid = grid
        self.num_agents = num_agents
        self.encoder = StateEncoder()
        self.allocator = TaskAllocator()
        self.dijkstra_planner = DijkstraPlanner(grid)
        self.last_assignments: Dict[int, int] = {}

        self.marl_coordinator = IndependentQLearning(
            num_agents=num_agents,
            conflict_penalty=-15.0,
            shared_weight=0.5,
        )

        if weights_dir is not None:
            w_path = Path(weights_dir)
            if w_path.exists():
                self.marl_coordinator.load(w_path)

        if evaluation_mode:
            for q_agent in self.marl_coordinator.agents.values():
                q_agent.epsilon = 0.0

    def plan_day(self, sim_state: SimulationState, day_steps: int) -> ActionPlan:
        """Plan day steps using IQL task allocation and Dijkstra path planning."""
        if hasattr(sim_state, "traffics") and sim_state.traffics is not None:
            self.grid.update_traffics(sim_state.traffics)

        chosen_tasks = self.marl_coordinator.select_macro_tasks(sim_state)
        plan: ActionPlan = []

        for agent in sim_state.agents:
            a_id = agent.agent_id
            if agent.kind == AgentKind.REFUEL:
                plan.append([-day_steps])
                continue

            macro_task, _, _ = chosen_tasks[a_id]
            target_pos = macro_task.target_pos

            primary_target = target_pos
            if macro_task.task_type == "STANDBY" or primary_target == agent.pos or not self.grid.is_passable(primary_target):
                other_spots = [
                    s.pos for s in sim_state.spots
                    if s.pos != agent.pos and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if other_spots:
                    agent_coord = HexCoord.from_index(agent.pos, self.grid.width)
                    other_spots.sort(key=lambda p: agent_coord.distance_to(HexCoord.from_index(p, self.grid.width)))
                    primary_target = other_spots[0]
                else:
                    plan.append([-day_steps])
                    continue

            path_res = self.dijkstra_planner.plan(
                start_index=agent.pos,
                target_indices=primary_target,
                agent_kind=agent.kind,
                fuel_limit=agent.fuel,
            )

            route_actions: List[int] = []
            curr_chain_pos = agent.pos
            if path_res.reachable and path_res.actions:
                route_actions = [a.value if hasattr(a, "value") else int(a) for a in path_res.actions]
                curr_chain_pos = path_res.path[-1]

            # Multi-spot chaining
            chain_visited = {agent.pos, curr_chain_pos}
            while len(route_actions) < day_steps:
                next_candidates = [
                    s.pos for s in sim_state.spots
                    if s.pos not in chain_visited and s.current_stock > 0 and self.grid.is_passable(s.pos)
                ]
                if not next_candidates:
                    break
                next_res = self.dijkstra_planner.plan(
                    start_index=curr_chain_pos,
                    target_indices=next_candidates,
                    agent_kind=agent.kind,
                    fuel_limit=agent.fuel,
                )
                if not next_res.reachable or not next_res.actions:
                    break
                route_actions.extend([a.value if hasattr(a, "value") else int(a) for a in next_res.actions])
                curr_chain_pos = next_res.path[-1]
                chain_visited.add(curr_chain_pos)

            agent_plan = self.grid.format_agent_actions(
                start_pos=agent.pos,
                actions=route_actions,
                agent_kind=agent.kind,
                day_steps=day_steps,
                fuel=agent.fuel,
            )
            plan.append(agent_plan)

        validate_action_plan(plan, len(sim_state.agents), day_steps)
        return plan
